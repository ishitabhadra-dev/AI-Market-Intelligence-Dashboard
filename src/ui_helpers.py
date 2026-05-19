"""
Reusable Streamlit UI — professional market intelligence styling.

Beginners: call `inject_theme()` once at app startup, then use the
card/header helpers so every section looks consistent.
"""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from src import react_ui

# --- Design tokens ---
_SENTIMENT_COLORS = {
    "positive": ("#10b981", "#052e1f"),
    "negative": ("#ef4444", "#3f1212"),
    "neutral": ("#94a3b8", "#1e293b"),
    "n/a": ("#64748b", "#1e293b"),
    "pending": ("#f59e0b", "#422006"),
}


def inject_theme() -> None:
    """Global CSS — fintech-style dark dashboard."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .stApp {
            background: linear-gradient(165deg, #0a0e17 0%, #0f1628 45%, #0a101c 100%);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        h1, h2, h3 { letter-spacing: -0.02em; font-weight: 700 !important; }
        h1 { font-size: 2rem !important; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1322 0%, #0a0f1a 100%);
            border-right: 1px solid rgba(79, 140, 255, 0.15);
        }
        [data-testid="stSidebar"] .block-container { padding-top: 1rem; }
        [data-testid="stMetric"] {
            background: rgba(18, 26, 43, 0.85);
            border: 1px solid rgba(79, 140, 255, 0.12);
            border-radius: 12px;
            padding: 0.75rem 1rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            color: #e8eef7 !important;
        }
        [data-testid="stMetricLabel"] {
            color: #8b9cb8 !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
            border-color: rgba(79, 140, 255, 0.18) !important;
            background: rgba(15, 22, 40, 0.6);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(15, 22, 40, 0.5);
            border-radius: 12px;
            padding: 6px;
            border: 1px solid rgba(79, 140, 255, 0.1);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1rem;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #4f8cff 0%, #3b6fd9 100%);
            border: none;
            font-weight: 600;
            border-radius: 10px;
        }
        .stButton > button {
            border-radius: 10px;
            font-weight: 500;
        }

        /* Custom components */
        .mi-hero {
            background: linear-gradient(135deg, rgba(79,140,255,0.18) 0%, rgba(16,185,129,0.08) 100%);
            border: 1px solid rgba(79, 140, 255, 0.25);
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.25rem;
        }
        .mi-hero h1 {
            margin: 0 0 0.35rem 0;
            font-size: 1.75rem !important;
            color: #f8fafc;
        }
        .mi-hero p {
            margin: 0;
            color: #94a3b8;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .mi-badge {
            display: inline-block;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-right: 0.35rem;
        }
        .mi-card {
            background: rgba(18, 26, 43, 0.9);
            border: 1px solid rgba(79, 140, 255, 0.14);
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 0.85rem;
        }
        .mi-card h3 {
            margin: 0 0 0.5rem 0;
            font-size: 1.05rem !important;
            color: #f1f5f9;
            line-height: 1.35;
        }
        .mi-meta {
            color: #8b9cb8;
            font-size: 0.82rem;
            margin-bottom: 0.65rem;
        }
        .mi-label {
            color: #64748b;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .mi-step {
            display: flex;
            gap: 0.75rem;
            align-items: flex-start;
            margin-bottom: 0.65rem;
        }
        .mi-step-num {
            flex-shrink: 0;
            width: 1.6rem;
            height: 1.6rem;
            border-radius: 50%;
            background: rgba(79, 140, 255, 0.2);
            color: #93c5fd;
            font-weight: 700;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .mi-step-text { color: #cbd5e1; font-size: 0.88rem; line-height: 1.45; }
        .mi-callout {
            background: rgba(79, 140, 255, 0.08);
            border-left: 3px solid #4f8cff;
            padding: 0.75rem 1rem;
            border-radius: 0 10px 10px 0;
            margin: 0.5rem 0 1rem 0;
            color: #cbd5e1;
            font-size: 0.9rem;
        }
        .mi-status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.5rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="mi-hero">
            <h1>AI Market Intelligence Dashboard</h1>
            <p>Ingest financial headlines · Summarize with Amazon Bedrock ·
            Search &amp; research with RAG — all with source citations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(label: str, kind: str = "neutral") -> str:
    fg, bg = _SENTIMENT_COLORS.get(kind.lower(), _SENTIMENT_COLORS["neutral"])
    return (
        f'<span class="mi-badge" style="color:{fg};background:{bg};'
        f'border:1px solid {fg}33;">{label}</span>'
    )


def render_status_pills(*, bedrock: bool, pending: int, vector_count: int, article_count: int) -> None:
    if react_ui.is_react_available():
        react_ui.status_bar(
            bedrock=bedrock,
            pending=pending,
            vector_count=vector_count,
            article_count=article_count,
            key="mi_status_bar",
        )
        return
    pills = [
        badge("Bedrock connected" if bedrock else "Bedrock not configured", "positive" if bedrock else "negative"),
        badge(f"{article_count} articles", "neutral"),
        badge(f"{pending} pending AI" if pending else "All summarized", "pending" if pending else "positive"),
        badge(f"{vector_count} in vector DB", "neutral"),
    ]
    st.markdown(
        '<div class="mi-status-row">' + "".join(pills) + "</div>",
        unsafe_allow_html=True,
    )


def render_quick_start_sidebar() -> None:
    st.markdown("##### Quick start")
    steps = [
        ("Refresh market news", "Pulls headlines into SQLite."),
        ("Summarize ALL pending", "Bedrock writes bullets, sentiment & topics."),
        ("Sync to vector DB", "RAG tab → embed articles with Titan."),
        ("Search or Ask", "Semantic search & cited Q&A."),
    ]
    html = ""
    for i, (title, desc) in enumerate(steps, 1):
        html += f"""
        <div class="mi-step">
            <div class="mi-step-num">{i}</div>
            <div class="mi-step-text"><strong>{title}</strong><br>{desc}</div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


def callout(text: str) -> None:
    st.markdown(f'<div class="mi-callout">{text}</div>', unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def metrics_row(items: list[tuple[str, str | int | float]], *, key: str) -> None:
    if react_ui.is_react_available():
        react_ui.metrics_grid(items, key=key)
        return
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def sentiment_bar_chart(dist: dict[str, int]) -> None:
    if not dist:
        st.caption("No sentiment data yet — summarize articles first.")
        return
    chart_df = pd.DataFrame({"Sentiment": list(dist.keys()), "Articles": list(dist.values())})
    st.bar_chart(chart_df.set_index("Sentiment"), color="#4f8cff")


def dashboard_panel(sentiment: dict[str, int], topics: list[tuple[str, int]], *, key: str = "dashboard") -> None:
    """Interactive sentiment chart + topic list (React) or Streamlit fallback."""
    if react_ui.is_react_available():
        react_ui.dashboard_panel(sentiment, topics, key=key)
        return
    c1, c2 = st.columns((2, 1))
    with c1:
        section_header("Sentiment overview")
        sentiment_bar_chart(sentiment)
    with c2:
        section_header("Trending topics")
        if topics:
            for topic, count in topics[:8]:
                st.markdown(f"- **{topic}** — {count}")
        else:
            st.caption("Ingest articles and run AI to populate topics.")


def article_feed(rows: list[dict[str, Any]], *, key: str) -> None:
    """Expandable article cards with instant client-side filter (React)."""
    if react_ui.is_react_available():
        react_ui.article_feed(react_ui.articles_from_rows(rows), key=key)
        return
    for row in rows:
        article_card(row)


def rag_results_panel(rows: list[dict[str, Any]], *, title: str = "Results", key: str) -> None:
    if react_ui.is_react_available():
        articles = react_ui.articles_from_rows(rows)
        for i, a in enumerate(articles):
            a["rank"] = i + 1
        react_ui.rag_results(articles, title=title, key=key)
        return
    for i, row in enumerate(rows, start=1):
        semantic_search_card(row, rank=i)


def _format_pub(pub: Any) -> str:
    if hasattr(pub, "strftime"):
        try:
            if pd.isna(pub):
                return "—"
            return pub.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            return str(pub)
    return str(pub or "—")


def _sentiment_kind(sentiment: str, summary: str) -> str:
    if not summary or "Pending" in summary or summary.strip() == "":
        return "pending"
    return sentiment.lower() if sentiment in ("positive", "negative", "neutral") else "n/a"


def article_card(row: dict[str, Any]) -> None:
    title = html.escape(str(row.get("title", "Untitled")))
    source = html.escape(str(row.get("source", "—")))
    pub = html.escape(_format_pub(row.get("published_at")))
    url = row.get("url", "")
    sentiment = str(row.get("sentiment") or "n/a")
    ticker = html.escape(str(row.get("ticker_category") or "General"))
    summary = row.get("summary") or ""
    is_pending = not summary or summary == "_Pending summary…_"
    why = row.get("why_matters") or ""
    topics = row.get("key_topics") or []
    sent_kind = _sentiment_kind(sentiment, summary)

    with st.container(border=True):
        st.markdown(
            f"""
            <h3 style="margin:0 0 0.5rem 0;font-size:1.05rem;color:#f1f5f9;">{title}</h3>
            <div style="margin-bottom:0.65rem;">
                {badge(sentiment, sent_kind)} {badge(ticker, "neutral")}
                <span style="color:#64748b;font-size:0.82rem;"> {source} · {pub}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if url:
            st.markdown(f"[Read source article]({url})")
        st.markdown('<p class="mi-label">AI Summary</p>', unsafe_allow_html=True)
        if is_pending:
            st.warning("Pending — use **Summarize ALL pending** in the sidebar.")
        else:
            st.markdown(summary)
        if why:
            st.caption(f"**Why it matters:** {why}")
        if topics:
            st.caption("Topics: " + ", ".join(str(t) for t in topics))


def semantic_search_card(row: dict[str, Any], rank: int | None = None) -> None:
    if rank is not None:
        row = {**row, "title": f"#{rank} · {row.get('title', 'Untitled')}"}
    article_card(row)


def render_markdown_block(title: str, body: str) -> None:
    if title:
        st.markdown(f"#### {title}")
    if body:
        with st.container(border=True):
            st.markdown(body)


def citations_block(sources: list[str], title: str = "Sources") -> None:
    if not sources:
        st.caption("No sources available.")
        return
    st.markdown(f"**{title}**")
    for line in sources:
        st.markdown(f"- {line}")


def render_help_page() -> None:
    """Full demo script for presenters."""
    st.markdown("### Demo script (5–10 minutes)")
    callout("Follow these steps in order when presenting to stakeholders or in a class demo.")

    st.markdown(
        """
        | Step | Action | What to say |
        |------|--------|-------------|
        | 1 | Sidebar → **Refresh market news** | "We ingest live financial headlines into a local database." |
        | 2 | **Summarize ALL pending** | "Amazon Bedrock (Claude) turns each story into bullets, sentiment, and topics." |
        | 3 | **Dashboard** tab | "We see sentiment distribution and trending themes across the feed." |
        | 4 | RAG → **Sync Articles to Vector DB** | "Titan embeddings let us search by meaning, not just keywords." |
        | 5 | **Semantic Search** | Try: *AI chip demand* or *Federal Reserve rates* |
        | 6 | **Ask the Market Agent** | Try: *What are bearish signals in tech news?* |
        | 7 | **Generate Research Brief** | Try ticker: *NVDA* or topic: *semiconductors* |
        """
    )

    st.markdown("---")
    st.markdown("### Prerequisites")
    st.markdown(
        """
        - `.env` with `AWS_REGION`, `BEDROCK_CHAT_MODEL_ID` (e.g. `us.anthropic.claude-sonnet-4-6`), `BEDROCK_EMBEDDING_MODEL_ID`
        - AWS credentials via `aws configure` or keys in `.env`
        - IAM: `bedrock:InvokeModel` (e.g. `AmazonBedrockFullAccess`)
        - Run: `pip install -r requirements.txt`
        - **React UI (optional):** `./scripts/build_frontend.sh` then `streamlit run app.py`
        """
    )

    st.markdown("### Troubleshooting")
    st.markdown(
        """
        - **Pending summary…** → Click **Summarize ALL pending** in the sidebar.
        - **Vector DB empty** → RAG tab → **Sync Articles to Vector DB** (after summaries exist).
        - **Bedrock errors** → Check inference profile id starts with `us.` for Claude models.
        - **Slow first run** → Normal; each article = one Bedrock API call.
        """
    )
