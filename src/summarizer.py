"""
LLM summarization via **Amazon Bedrock** (invoke_model).

Phase 1 summaries use the same Bedrock chat model as Phase 2 RAG.
Results are cached in SQLite so the same article is not summarized twice.

If Bedrock is configured but the API call fails, we do **not** save demo text
(so you can fix AWS and try again).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.bedrock_client import BedrockError, bedrock_chat_configured, invoke_bedrock_text_model
from src.database import update_llm_fields

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a concise financial news analyst.
Return ONLY valid JSON with these keys:
- bullets: array of exactly 3 short strings (each one bullet point, no numbering prefix)
- sentiment: one of "positive", "negative", "neutral"
- topics: array of 3-6 short topic labels (Title Case, no duplicates)
- why_matters: one sentence explaining market relevance for a busy reader
Do not include markdown fences or commentary outside JSON."""


def bedrock_configured() -> bool:
    return bedrock_chat_configured()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def summarize_article_text(
    title: str,
    *,
    url: str = "",
    ticker_category: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Call Bedrock once for a headline.

    Returns (result_dict, error_message). On success error_message is None.
    """
    if not bedrock_configured():
        return None, "BEDROCK_CHAT_MODEL_ID or AWS_REGION not set in `.env`."

    user = f"Title: {title}\nURL: {url}\nCategory/Ticker hint: {ticker_category or 'n/a'}"
    try:
        raw = invoke_bedrock_text_model(user, system_prompt=SYSTEM_PROMPT)
    except BedrockError as exc:
        return None, str(exc)

    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, f"Model returned invalid JSON: {exc}"

    bullets = data.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = []
    bullets = [str(b).strip() for b in bullets if str(b).strip()][:3]
    while len(bullets) < 3:
        bullets.append("—")

    sentiment = str(data.get("sentiment", "neutral")).lower().strip()
    if sentiment not in ("positive", "negative", "neutral"):
        sentiment = "neutral"

    topics = data.get("topics") or data.get("key_topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip() for t in topics if str(t).strip()][:8]

    why = str(data.get("why_matters", "")).strip() or "Provides context for broader market moves."
    summary_text = "\n".join(f"• {b}" for b in bullets[:3])
    return (
        {
            "summary": summary_text,
            "sentiment": sentiment,
            "key_topics": topics,
            "why_matters": why,
        },
        None,
    )


def offline_placeholder_summary(title: str, ticker_category: str | None) -> dict[str, Any]:
    """Only used when Bedrock is not configured at all."""
    cat = ticker_category or "General"
    summary = "\n".join(
        [
            f"• Headline highlights: {title[:90]}{'…' if len(title) > 90 else ''}",
            "• Add AWS credentials and BEDROCK_CHAT_MODEL_ID in `.env`, then clear summaries.",
            f"• Category / ticker context: {cat}.",
        ]
    )
    return {
        "summary": summary,
        "sentiment": "neutral",
        "key_topics": ["Markets", cat, "Demo Mode"],
        "why_matters": "Demo summary: Bedrock is not configured yet.",
    }


def summarize_and_cache(
    conn,
    article_id: int,
    title: str,
    url: str,
    ticker_category: str | None,
) -> str:
    """
    Summarize one article and save to SQLite.

    Returns status: "live" | "demo" | "failed"
    """
    result, err = summarize_article_text(title, url=url, ticker_category=ticker_category)

    if result is not None:
        update_llm_fields(
            conn,
            article_id,
            summary=result["summary"],
            sentiment=result["sentiment"],
            key_topics=result["key_topics"],
            why_matters=result["why_matters"],
        )
        return "live"

    if bedrock_configured():
        logger.warning("Bedrock failed for article %s: %s", article_id, err)
        return f"failed: {err}"

    result = offline_placeholder_summary(title, ticker_category)
    update_llm_fields(
        conn,
        article_id,
        summary=result["summary"],
        sentiment=result["sentiment"],
        key_topics=result["key_topics"],
        why_matters=result["why_matters"],
    )
    return "demo"
