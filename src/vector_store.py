"""
ChromaDB local vector store (Phase 2).

**Vector search** finds articles whose Titan embeddings are closest to your
query embedding — search by meaning, not just keywords.

Vectors live under `data/vector_db/`. Phase 3 will move this to
Amazon OpenSearch Serverless for scalable hosted search.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

from src import config
from src.embeddings import (
    EmbeddingError,
    create_embedding,
    embedding_text_hash,
    embeddings_configured,
    get_article_embedding_text,
)

logger = logging.getLogger(__name__)

_collection = None


def initialize_vector_store():
    """Open or create the persistent Chroma collection on disk."""
    global _collection
    client = chromadb.PersistentClient(
        path=str(config.VECTOR_DB_PATH),
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={"description": "AI Market Intelligence — Titan embeddings"},
    )
    return _collection


def get_collection():
    global _collection
    if _collection is None:
        return initialize_vector_store()
    return _collection


def count_embedded_articles() -> int:
    try:
        return int(get_collection().count())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not count vector store: %s", exc)
        return 0


def _topics_to_meta(topics: Any) -> str:
    if isinstance(topics, list):
        return ", ".join(str(t).strip() for t in topics if str(t).strip())
    return str(topics or "").strip()


def _article_metadata(article: dict[str, Any], content_hash: str) -> dict[str, str]:
    published = article.get("published_at")
    if hasattr(published, "isoformat"):
        published = published.isoformat()
    return {
        "article_id": str(article.get("id", "")),
        "title": str(article.get("title") or "")[:500],
        "source": str(article.get("source") or ""),
        "url": str(article.get("url") or ""),
        "published_at": str(published or ""),
        "ticker_category": str(article.get("ticker_category") or ""),
        "sentiment": str(article.get("sentiment") or ""),
        "key_topics": _topics_to_meta(article.get("key_topics")),
        "summary": str(article.get("summary") or "")[:2000],
        "why_matters": str(article.get("why_matters") or "")[:1000],
        "content_hash": content_hash,
    }


def _metadata_to_article(meta: dict[str, Any], document: str = "") -> dict[str, Any]:
    topics_raw = meta.get("key_topics") or ""
    topics = [t.strip() for t in str(topics_raw).split(",") if t.strip()]
    return {
        "id": int(meta.get("article_id") or 0) or None,
        "title": meta.get("title") or "Untitled",
        "source": meta.get("source") or "",
        "url": meta.get("url") or "",
        "published_at": meta.get("published_at") or "",
        "ticker_category": meta.get("ticker_category") or "",
        "sentiment": meta.get("sentiment") or "",
        "key_topics": topics,
        "summary": meta.get("summary") or "",
        "why_matters": meta.get("why_matters") or "",
        "embedding_document": document,
    }


def _needs_reembed(col, chroma_id: str, new_hash: str) -> bool:
    try:
        existing = col.get(ids=[chroma_id], include=["metadatas"])
        if not existing["ids"]:
            return True
        meta = (existing["metadatas"] or [{}])[0] or {}
        return meta.get("content_hash") != new_hash
    except Exception:
        return True


def upsert_article_to_vector_store(article: dict[str, Any]) -> tuple[str, str | None]:
    """
    Insert or update one article vector in Chroma.

    Returns (status, error) with status: embedded | skipped | failed
    """
    article_id = article.get("id")
    if article_id is None:
        return "failed", "Article is missing an id."

    if not embeddings_configured():
        return "failed", "Set AWS_REGION and BEDROCK_EMBEDDING_MODEL_ID in `.env`."

    doc_text = get_article_embedding_text(article)
    if not doc_text.strip():
        return "failed", "Article has no text to embed."

    content_hash = embedding_text_hash(doc_text)
    chroma_id = str(article_id)
    col = get_collection()

    try:
        if not _needs_reembed(col, chroma_id, content_hash):
            return "skipped", None

        vector = create_embedding(doc_text)
        col.upsert(
            ids=[chroma_id],
            embeddings=[vector],
            documents=[doc_text],
            metadatas=[_article_metadata(article, content_hash)],
        )
        return "embedded", None
    except EmbeddingError as exc:
        return "failed", str(exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vector upsert failed id=%s: %s", chroma_id, exc)
        return "failed", str(exc)


def sync_sqlite_articles_to_vector_store(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Embed all SQLite articles into the local Chroma vector store."""
    stats = {"embedded": 0, "skipped": 0, "failed": 0, "errors": []}
    if not articles:
        stats["errors"].append("No articles in SQLite. Refresh market news first.")
        return stats

    if not embeddings_configured():
        stats["errors"].append(
            "Bedrock embeddings not configured. Set AWS_REGION and BEDROCK_EMBEDDING_MODEL_ID."
        )
        return stats

    initialize_vector_store()
    for article in articles:
        status, err = upsert_article_to_vector_store(article)
        stats[status] += 1
        if err and len(stats["errors"]) < 5:
            stats["errors"].append(f"Article {article.get('id')}: {err}")

    return stats


# Back-compat alias
sync_sqlite_articles_to_chroma = sync_sqlite_articles_to_vector_store


def build_chroma_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Simple Chroma metadata filter (ticker, sentiment, source).

    Date filters are applied in Python after the query — see `_passes_date_filter`.
    """
    if not filters:
        return None
    clauses: list[dict[str, str]] = []
    if filters.get("ticker_category"):
        clauses.append({"ticker_category": str(filters["ticker_category"])})
    if filters.get("sentiment"):
        clauses.append({"sentiment": str(filters["sentiment"])})
    if filters.get("source"):
        clauses.append({"source": str(filters["source"])})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _passes_date_filter(meta: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if not date_from and not date_to:
        return True
    raw = meta.get("published_at") or ""
    if not raw:
        return True
    try:
        pub = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        pub_date = pub.date()
    except ValueError:
        return True
    if date_from and pub_date < date_from:
        return False
    if date_to and pub_date > date_to:
        return False
    return True


def semantic_search(
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Semantic search: Titan embedding for query → nearest neighbors in Chroma.
    """
    q = (query or "").strip()
    if not q:
        return [], "Enter a search query."

    if count_embedded_articles() == 0:
        return [], "Vector database is empty. Click “Sync Articles to Vector DB” first."

    if not embeddings_configured():
        return [], "Configure AWS Bedrock Titan embeddings (see Vector Database Status tab)."

    try:
        query_vector = create_embedding(q)
    except EmbeddingError as exc:
        return [], str(exc)

    col = get_collection()
    where = build_chroma_where(filters)
    n_fetch = max(top_k * 3, top_k + 5)

    try:
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": n_fetch,
            "include": ["metadatas", "documents", "distances"],
        }
        if where:
            kwargs["where"] = where
        raw = col.query(**kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chroma query failed: %s", exc)
        return [], f"Semantic search failed: {exc}"

    results: list[dict[str, Any]] = []
    ids = raw.get("ids", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    for _id, meta, doc, dist in zip(ids, metas, docs, dists):
        meta = meta or {}
        if not _passes_date_filter(meta, filters):
            continue
        item = _metadata_to_article(meta, doc or "")
        item["relevance_score"] = float(dist) if dist is not None else None
        results.append(item)
        if len(results) >= top_k:
            break

    return results, None
