"""
Text embeddings via **Amazon Titan Text Embeddings** (Phase 2).

**Embeddings** turn text into a list of numbers (a vector). Similar meaning
→ similar vectors. Titan runs on Bedrock — no OpenAI required.

We hash each article's embedding text so unchanged stories are not re-embedded.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from src import config
from src.bedrock_client import (
    BedrockError,
    bedrock_embeddings_configured,
    invoke_titan_embedding_model,
)

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when Titan embeddings cannot be created."""


def embeddings_configured() -> bool:
    """Check model id + region (AWS credentials validated on first API call)."""
    return bedrock_embeddings_configured()


# Back-compat name used in older app versions
def openai_configured() -> bool:
    return embeddings_configured()


def get_article_embedding_text(article: dict[str, Any]) -> str:
    """
    Combine article fields into one string for Titan embedding.

    Missing fields are skipped safely.
    """
    topics = article.get("key_topics") or []
    if isinstance(topics, list):
        topics_str = ", ".join(str(t).strip() for t in topics if str(t).strip())
    else:
        topics_str = str(topics).strip()

    published = article.get("published_at")
    if hasattr(published, "isoformat"):
        published = published.isoformat()
    published_str = str(published or "").strip()

    parts = [
        f"Title: {str(article.get('title') or '').strip()}",
        f"Summary: {str(article.get('summary') or '').strip()}",
        f"Why it matters: {str(article.get('why_matters') or '').strip()}",
        f"Topics: {topics_str}" if topics_str else "",
        f"Source: {str(article.get('source') or '').strip()}",
        f"Published: {published_str}" if published_str else "",
        f"Ticker/Category: {str(article.get('ticker_category') or '').strip()}",
        f"Sentiment: {str(article.get('sentiment') or '').strip()}",
    ]
    return "\n".join(p for p in parts if p and not p.endswith(": "))


def embedding_text_hash(text: str) -> str:
    """Stable hash — skip re-embedding when article text unchanged."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_embedding(text: str) -> list[float]:
    """
    Call Amazon Titan Text Embeddings once.

    Returns a vector (list of floats) for ChromaDB.
    """
    try:
        return invoke_titan_embedding_model(text)
    except BedrockError as exc:
        raise EmbeddingError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("Titan embedding failed: %s", exc)
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc
