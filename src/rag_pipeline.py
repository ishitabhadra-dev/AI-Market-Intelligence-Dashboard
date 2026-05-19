"""
RAG pipeline — Retrieval-Augmented Generation with **Amazon Bedrock** (Phase 2).

**RAG** = Retrieve (Chroma + Titan embeddings) → Augment prompt with evidence →
Generate answer with Bedrock (Claude / Nova). **No OpenAI.**

**Citations** list every source so readers can verify claims.
"""

from __future__ import annotations

import logging
from typing import Any

from src.bedrock_client import BedrockError, bedrock_chat_configured, invoke_bedrock_text_model
from src.vector_store import semantic_search

logger = logging.getLogger(__name__)


class RAGError(Exception):
    """User-facing RAG failures."""


def format_citation(article: dict[str, Any]) -> str:
    """Title — Source — Published Date — URL"""
    title = article.get("title") or "Untitled"
    source = article.get("source") or "Unknown source"
    published = article.get("published_at") or "Date unknown"
    if hasattr(published, "strftime"):
        published = published.strftime("%Y-%m-%d")
    url = article.get("url") or ""
    line = f"{title} — {source} — {published}"
    if url:
        line += f" — {url}"
    return line


def _build_context_block(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "(No articles retrieved.)"
    blocks: list[str] = []
    for i, art in enumerate(articles, start=1):
        topics = art.get("key_topics") or []
        topics_str = ", ".join(str(t) for t in topics) if topics else "n/a"
        blocks.append(
            f"""[Source {i}]
Title: {art.get('title', '')}
Source: {art.get('source', '')}
Published: {art.get('published_at', '')}
URL: {art.get('url', '')}
Ticker/Category: {art.get('ticker_category', '')}
Sentiment: {art.get('sentiment', '')}
Topics: {topics_str}
Summary: {art.get('summary', '')}
Why it matters: {art.get('why_matters', '')}"""
        )
    return "\n\n".join(blocks)


def _call_llm(system: str, user: str) -> str:
    if not bedrock_chat_configured():
        raise RAGError(
            "Bedrock chat is not configured. Set AWS_REGION and BEDROCK_CHAT_MODEL_ID in `.env`."
        )
    try:
        return invoke_bedrock_text_model(user, system_prompt=system)
    except BedrockError as exc:
        raise RAGError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bedrock RAG call failed: %s", exc)
        raise RAGError(f"Bedrock request failed: {exc}") from exc


def answer_market_question(
    question: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    RAG Q&A: Titan embedding search → Bedrock grounded answer with citations.
    """
    q = (question or "").strip()
    if not q:
        return {
            "answer": "",
            "retrieved_articles": [],
            "sources_used": [],
            "error": "Please enter a question.",
        }

    articles, search_err = semantic_search(q, filters=filters, top_k=top_k)
    if search_err:
        return {"answer": "", "retrieved_articles": [], "sources_used": [], "error": search_err}

    if not articles:
        return {
            "answer": (
                "There is **not enough evidence** in the local news database to answer this "
                "question. Sync more articles to the vector DB or broaden your filters."
            ),
            "retrieved_articles": [],
            "sources_used": [],
            "error": None,
        }

    context = _build_context_block(articles)
    citations = [format_citation(a) for a in articles]

    system = """You are a careful financial research assistant.
Answer ONLY using the retrieved news sources in the user message.
Do not invent facts, prices, or events.
If evidence is weak or conflicting, say so.

Use these markdown headings exactly:

## 1. Direct Answer
## 2. Supporting Evidence
## 3. Risks / Uncertainty
## 4. Sources Used

Under Sources Used, include every citation line from the user message."""

    user = f"""Question: {q}

Retrieved news sources:
{context}

Citation lines (include all under Sources Used):
{chr(10).join(f"- {c}" for c in citations)}"""

    try:
        answer = _call_llm(system, user)
    except RAGError as exc:
        return {
            "answer": "",
            "retrieved_articles": articles,
            "sources_used": citations,
            "error": str(exc),
        }

    return {
        "answer": answer,
        "retrieved_articles": articles,
        "sources_used": citations,
        "error": None,
    }


def generate_market_brief(
    topic_or_ticker: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    """Citation-backed research brief via semantic search + Bedrock."""
    topic = (topic_or_ticker or "").strip()
    if not topic:
        return {
            "brief": "",
            "retrieved_articles": [],
            "sources_used": [],
            "error": "Enter a ticker, company, sector, or topic.",
        }

    articles, search_err = semantic_search(topic, filters=filters, top_k=top_k)
    if search_err:
        return {"brief": "", "retrieved_articles": [], "sources_used": [], "error": search_err}

    if not articles:
        return {
            "brief": (
                f"There is **not enough evidence** to produce a brief on “{topic}”. "
                "Sync articles to the vector DB and try a broader topic."
            ),
            "retrieved_articles": [],
            "sources_used": [],
            "error": None,
        }

    context = _build_context_block(articles)
    citations = [format_citation(a) for a in articles]

    system = """You are a senior market intelligence analyst.
Use ONLY the retrieved sources. Do not invent data.
If evidence is limited, say so under Risks and Uncertainty.

Use these markdown headings exactly:

## 1. Executive Summary
## 2. Key Developments
## 3. Bullish Signals
## 4. Bearish Signals
## 5. Risks and Uncertainty
## 6. Sources Used

List every citation line under Sources Used. Professional, concise tone."""

    user = f"""Topic / ticker / theme: {topic}

Retrieved news sources:
{context}

Citation lines:
{chr(10).join(f"- {c}" for c in citations)}"""

    try:
        brief = _call_llm(system, user)
    except RAGError as exc:
        return {
            "brief": "",
            "retrieved_articles": articles,
            "sources_used": citations,
            "error": str(exc),
        }

    return {
        "brief": brief,
        "retrieved_articles": articles,
        "sources_used": citations,
        "error": None,
    }
