"""
Streamlit ↔ React bridge for interactive UI components.

Build the frontend once:
    cd frontend && npm install && npm run build

Dev mode (hot reload):
    cd frontend && npm run dev
    REACT_DEV=1 streamlit run app.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_ROOT = Path(__file__).resolve().parent.parent
_BUILD_DIR = _ROOT / "frontend" / "build"
_DEV_MODE = os.environ.get("REACT_DEV", "").strip() in ("1", "true", "yes")

_component_func = None


def is_react_available() -> bool:
    return _DEV_MODE or (_BUILD_DIR / "index.html").is_file()


def _get_component():
    global _component_func
    if _component_func is not None:
        return _component_func
    if _DEV_MODE:
        _component_func = components.declare_component(
            "mi_react",
            url="http://localhost:3001",
        )
    elif (_BUILD_DIR / "index.html").is_file():
        _component_func = components.declare_component(
            "mi_react",
            path=str(_BUILD_DIR),
        )
    return _component_func


def _call(view: str, *, key: str | None = None, default: Any = None, **kwargs: Any) -> Any:
    comp = _get_component()
    if comp is None:
        return default
    return comp(view=view, key=key, default=default, **kwargs)


def _serialize_pub(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def _parse_topics(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
        except json.JSONDecodeError:
            return [raw] if raw else []
    return []


def article_from_row(row: dict[str, Any], *, rank: int | None = None) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "title": str(row.get("title") or "Untitled"),
        "source": str(row.get("source") or "—"),
        "publishedAt": _serialize_pub(row.get("published_at")),
        "url": str(row.get("url") or ""),
        "sentiment": str(row.get("sentiment") or "n/a"),
        "ticker": str(row.get("ticker_category") or "General"),
        "summary": str(row.get("summary") or ""),
        "whyMatters": str(row.get("why_matters") or ""),
        "topics": _parse_topics(row.get("key_topics")),
        "rank": rank,
    }


def articles_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [article_from_row(r) for r in rows]


def status_bar(
    *,
    bedrock: bool,
    pending: int,
    vector_count: int,
    article_count: int,
    bedrock_label: str | None = None,
    bedrock_kind: str | None = None,
    key: str = "mi_status_bar",
) -> None:
    payload: dict[str, Any] = {
        "bedrock": bedrock,
        "pending": pending,
        "vectorCount": vector_count,
        "articleCount": article_count,
    }
    if bedrock_label:
        payload["bedrockLabel"] = bedrock_label
    if bedrock_kind:
        payload["bedrockKind"] = bedrock_kind
    _call("status_bar", key=key, **payload)


def metrics_grid(
    metrics: list[tuple[str, str | int | float]],
    *,
    key: str,
) -> None:
    payload = [{"label": label, "value": value} for label, value in metrics]
    # Use metricItems (not metrics) to avoid clashing with Streamlit's key= handling
    _call("metrics", key=key, metricItems=payload)


def dashboard_panel(
    sentiment: dict[str, int],
    topics: list[tuple[str, int]],
    *,
    key: str = "dashboard",
) -> None:
    _call(
        "dashboard",
        key=key,
        sentiment=sentiment,
        topics=[{"topic": t, "count": c} for t, c in topics],
    )


def article_feed(
    articles: list[dict[str, Any]],
    *,
    key: str,
    bedrock_configured: bool = False,
    summarize_failed: bool = False,
) -> None:
    _call(
        "article_feed",
        key=key,
        articles=articles,
        bedrockConfigured=bedrock_configured,
        summarizeFailed=summarize_failed,
    )


def rag_results(
    articles: list[dict[str, Any]],
    *,
    title: str = "Search results",
    key: str,
) -> None:
    _call("rag_results", key=key, articles=articles, placeholder=title)


def market_agent(
    *,
    messages: list[dict[str, str]],
    examples: list[str] | None = None,
    answer: str = "",
    sources: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    key: str = "market_agent",
) -> dict[str, Any] | None:
    """Returns ``{action: 'ask', question: '...'}`` when user submits a question."""
    result = _call(
        "market_agent",
        key=key,
        default=None,
        messages=messages,
        examples=examples or [],
        answer=answer,
        sources=sources or [],
        evidence=evidence or [],
        placeholder="Ask about market themes, risks, or sectors…",
    )
    if isinstance(result, dict):
        return result
    return None
