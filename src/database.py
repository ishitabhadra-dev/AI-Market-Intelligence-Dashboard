"""
SQLite persistence for market news articles and AI-generated fields.

We use a single table `articles` with a unique `url` so the same
story is not ingested twice. Summaries are cached: if `summary` is
non-empty, we skip re-calling the LLM for that row.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import DB_PATH


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """
    Create the database file (if needed) and the `articles` table.

    Extra columns beyond the brief spec store sentiment, topics, and
    "why it matters" from the LLM in Phase 1.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT,
                url TEXT NOT NULL UNIQUE,
                published_at TEXT,
                summary TEXT,
                ticker_category TEXT,
                created_at TEXT NOT NULL,
                sentiment TEXT,
                key_topics TEXT,
                why_matters TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment)"
        )
        conn.commit()


def insert_article(
    conn: sqlite3.Connection,
    *,
    title: str,
    source: str | None,
    url: str,
    published_at: str | None,
    ticker_category: str | None,
    summary: str | None = None,
    sentiment: str | None = None,
    key_topics: list[str] | None = None,
    why_matters: str | None = None,
) -> int | None:
    """
    Insert one article. Returns new row id, or None if `url` already exists.

    `published_at` should be ISO 8601 string when possible.
    """
    topics_json = json.dumps(key_topics or [])
    created = _utc_now_iso()
    try:
        cur = conn.execute(
            """
            INSERT INTO articles (
                title, source, url, published_at, summary, ticker_category,
                created_at, sentiment, key_topics, why_matters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                source,
                url,
                published_at,
                summary,
                ticker_category,
                created,
                sentiment,
                topics_json,
                why_matters,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return None


def update_llm_fields(
    conn: sqlite3.Connection,
    article_id: int,
    *,
    summary: str,
    sentiment: str,
    key_topics: list[str],
    why_matters: str,
) -> None:
    """Persist LLM output for a single article (cache)."""
    conn.execute(
        """
        UPDATE articles
        SET summary = ?, sentiment = ?, key_topics = ?, why_matters = ?
        WHERE id = ?
        """,
        (summary, sentiment, json.dumps(key_topics), why_matters, article_id),
    )
    conn.commit()


def fetch_articles_df(conn: sqlite3.Connection) -> Any:
    """Return all articles as a pandas DataFrame (lazy import)."""
    import pandas as pd

    df = pd.read_sql_query(
        """
        SELECT * FROM articles
        ORDER BY (published_at IS NULL), published_at DESC, id DESC
        """,
        conn,
    )
    if not df.empty and "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    if not df.empty and "key_topics" in df.columns:

        def _topics_cell(val: Any) -> list[str]:
            if isinstance(val, list):
                return [str(t).strip() for t in val if str(t).strip()]
            if isinstance(val, str) and val.strip():
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(t).strip() for t in parsed if str(t).strip()]
                except json.JSONDecodeError:
                    return []
            return []

        df["key_topics"] = df["key_topics"].apply(_topics_cell)
    return df


def clear_all_ai_summaries(conn: sqlite3.Connection) -> int:
    """
    Remove cached summaries so Bedrock can run again.

    Use this after fixing AWS credentials — old "Demo Mode" text stays in SQLite
    until you clear it.
    """
    cur = conn.execute(
        """
        UPDATE articles
        SET summary = NULL, sentiment = NULL, key_topics = '[]', why_matters = NULL
        """
    )
    conn.commit()
    return int(cur.rowcount)


SUMMARY_PENDING_PLACEHOLDER = "_Pending summary…_"


def needs_ai_summary(summary: str | None) -> bool:
    """True when the row still needs Bedrock (matches UI + SQL)."""
    if summary is None:
        return True
    text = str(summary).strip()
    return text == "" or text == SUMMARY_PENDING_PLACEHOLDER


def count_articles_needing_summary(conn: sqlite3.Connection) -> int:
    """How many rows still need a Bedrock summary (no limit)."""
    cur = conn.execute(
        """
        SELECT COUNT(*) FROM articles
        WHERE summary IS NULL
           OR TRIM(summary) = ''
           OR TRIM(summary) = ?
        """,
        (SUMMARY_PENDING_PLACEHOLDER,),
    )
    return int(cur.fetchone()[0])


def article_ids_needing_summary(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    """Rows where we still need an LLM summary."""
    cur = conn.execute(
        """
        SELECT id, title, url, ticker_category
        FROM articles
        WHERE summary IS NULL
           OR TRIM(summary) = ''
           OR TRIM(summary) = ?
        ORDER BY (published_at IS NULL), published_at DESC, id DESC
        LIMIT ?
        """,
        (SUMMARY_PENDING_PLACEHOLDER, limit),
    )
    return list(cur.fetchall())


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    if d.get("key_topics"):
        try:
            d["key_topics"] = json.loads(d["key_topics"])
        except json.JSONDecodeError:
            d["key_topics"] = []
    else:
        d["key_topics"] = []
    return d


def _parse_topics_field(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(t).strip() for t in val if str(t).strip()]
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
        except json.JSONDecodeError:
            return []
    return []


def fetch_all_articles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    Return every article as a plain dict (used by Chroma sync and RAG).

    Phase 2 reads from the same SQLite table Phase 1 writes to.
    """
    cur = conn.execute(
        """
        SELECT * FROM articles
        ORDER BY (published_at IS NULL), published_at DESC, id DESC
        """
    )
    rows = cur.fetchall()
    articles: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["key_topics"] = _parse_topics_field(d.get("key_topics"))
        articles.append(d)
    return articles


def count_articles(conn: sqlite3.Connection) -> int:
    """Fast row count for status panels."""
    cur = conn.execute("SELECT COUNT(*) FROM articles")
    return int(cur.fetchone()[0])
