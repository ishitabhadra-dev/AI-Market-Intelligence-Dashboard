"""
Lightweight analytics over the articles table.

Keeps pandas operations small and readable for the Streamlit dashboard.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

import pandas as pd


def article_count(df: pd.DataFrame) -> int:
    return int(len(df))


def sentiment_distribution(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "sentiment" not in df.columns:
        return {}
    counts = df["sentiment"].fillna("unknown").value_counts().to_dict()
    return {str(k): int(v) for k, v in counts.items()}


def top_topics(df: pd.DataFrame, top_n: int = 12) -> list[tuple[str, int]]:
    """Flatten JSON-like topic lists stored as Python lists in DataFrame."""
    topics: list[str] = []
    if df.empty or "key_topics" not in df.columns:
        return []
    for val in df["key_topics"]:
        if isinstance(val, list):
            topics.extend(str(t).strip() for t in val if str(t).strip())
        elif isinstance(val, str) and val.strip().startswith("["):
            # Should not happen if DB always parses to list — safe guard
            continue
    counts = Counter(topics)
    return counts.most_common(top_n)


def latest_published_timestamp(df: pd.DataFrame) -> datetime | None:
    if df.empty or "published_at" not in df.columns:
        return None
    series = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    if series.dropna().empty:
        return None
    return series.max().to_pydatetime()


def filter_dataframe(
    df: pd.DataFrame,
    *,
    ticker: str | None,
    sentiment: str | None,
    source: str | None,
    date_from,
    date_to,
    search: str | None,
) -> pd.DataFrame:
    """Apply sidebar filters + keyword search."""
    out = df.copy()
    if ticker and "ticker_category" in out.columns:
        out = out[out["ticker_category"].astype(str) == ticker]
    if sentiment and "sentiment" in out.columns:
        out = out[out["sentiment"].astype(str) == sentiment]
    if source and "source" in out.columns:
        out = out[out["source"].astype(str) == source]
    if date_from is not None and "published_at" in out.columns:
        ts = pd.to_datetime(out["published_at"], errors="coerce", utc=True)
        out = out[ts.dt.date >= date_from]
    if date_to is not None and "published_at" in out.columns:
        ts = pd.to_datetime(out["published_at"], errors="coerce", utc=True)
        out = out[ts.dt.date <= date_to]
    q = (search or "").strip().lower()
    if q:
        def _match(row: pd.Series) -> bool:
            title = str(row.get("title", "")).lower()
            summary = str(row.get("summary", "")).lower()
            why = str(row.get("why_matters", "")).lower()
            return q in title or q in summary or q in why

        out = out[out.apply(_match, axis=1)]
    return out


def trending_topic_list(df: pd.DataFrame, top_n: int = 8) -> list[str]:
    return [t for t, _ in top_topics(df, top_n=top_n)]


def build_rag_filters(
    *,
    ticker: str | None = None,
    sentiment: str | None = None,
    source: str | None = None,
    date_from=None,
    date_to=None,
) -> dict[str, Any]:
    """
    Normalize UI filter widgets into a dict for Chroma + post-filters.

    Pass `None` or `"All"` for unused filters.
    """
    filters: dict[str, Any] = {}
    if ticker and ticker != "All":
        filters["ticker_category"] = ticker
    if sentiment and sentiment != "All":
        filters["sentiment"] = sentiment
    if source and source != "All":
        filters["source"] = source
    if date_from is not None:
        filters["date_from"] = date_from
    if date_to is not None:
        filters["date_to"] = date_to
    return filters
