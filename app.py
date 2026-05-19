"""
AI Market Intelligence Dashboard — Streamlit entrypoint (Phase 1 + 2).

Run from the project root:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="AI Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src import config
from src.config import is_streamlit_cloud, refresh_streamlit_secrets

refresh_streamlit_secrets()

import pandas as pd

from src import analytics
from src import database as db
from src import embeddings
from src.bedrock_client import aws_configured
from src import news_ingestion
from src import rag_pipeline
from src import summarizer
from src import react_ui
from src import ui_helpers
from src import vector_store

ui_helpers.inject_theme()


@st.cache_resource
def _get_db_connection():
    db.init_db()
    return db.get_connection()


def _ingest_latest(conn, max_items: int) -> tuple[int, str]:
    articles, label = news_ingestion.fetch_latest_news(max_items=max_items)
    new_count = 0
    for item in articles:
        inserted = db.insert_article(
            conn,
            title=item["title"],
            source=item["source"],
            url=item["url"],
            published_at=item.get("published_at"),
            ticker_category=item.get("ticker_category"),
        )
        if inserted is not None:
            new_count += 1
    return new_count, label


def _summarize_pending(conn, batch_limit: int) -> dict[str, int | list[str]]:
    pending = db.article_ids_needing_summary(conn, limit=batch_limit)
    stats: dict[str, int | list[str]] = {
        "processed": 0,
        "live": 0,
        "demo": 0,
        "failed": 0,
        "errors": [],
    }
    for row in pending:
        status = summarizer.summarize_and_cache(
            conn,
            int(row["id"]),
            str(row["title"]),
            str(row["url"]),
            row["ticker_category"],
        )
        stats["processed"] = int(stats["processed"]) + 1
        if status == "live":
            stats["live"] = int(stats["live"]) + 1
        elif status == "demo":
            stats["demo"] = int(stats["demo"]) + 1
        elif isinstance(status, str) and status.startswith("failed:"):
            stats["failed"] = int(stats["failed"]) + 1
            errs = stats["errors"]
            if isinstance(errs, list) and len(errs) < 3:
                errs.append(status.replace("failed: ", "", 1))
    return stats


def _rag_filter_widgets(key_prefix: str, df: pd.DataFrame) -> dict:
    c1, c2, c3 = st.columns(3)
    with c1:
        t_opts = ["All"]
        if not df.empty and "ticker_category" in df.columns:
            t_opts += sorted(df["ticker_category"].dropna().astype(str).unique().tolist())
        rag_ticker = st.selectbox("Ticker / category", t_opts, key=f"{key_prefix}_ticker")
    with c2:
        s_opts = ["All"]
        if not df.empty and "sentiment" in df.columns:
            s_opts += sorted(df["sentiment"].dropna().astype(str).unique().tolist())
        rag_sentiment = st.selectbox("Sentiment", s_opts, key=f"{key_prefix}_sentiment")
    with c3:
        src_opts = ["All"]
        if not df.empty and "source" in df.columns:
            src_opts += sorted(df["source"].dropna().astype(str).unique().tolist())
        rag_source = st.selectbox("Source", src_opts, key=f"{key_prefix}_source")
    d1, d2 = st.columns(2)
    with d1:
        rag_from = st.date_input("From date", value=None, key=f"{key_prefix}_from")
    with d2:
        rag_to = st.date_input("To date", value=None, key=f"{key_prefix}_to")
    return analytics.build_rag_filters(
        ticker=rag_ticker,
        sentiment=rag_sentiment,
        source=rag_source,
        date_from=rag_from if isinstance(rag_from, date) else None,
        date_to=rag_to if isinstance(rag_to, date) else None,
    )


def _render_rag_tab(df: pd.DataFrame, conn) -> None:
    ui_helpers.section_header(
        "RAG Market Research",
        "Semantic search, grounded Q&A, and cited briefs — powered by Titan embeddings + Bedrock.",
    )

    if not aws_configured():
        ui_helpers.callout(
            "Configure AWS in `.env` (`AWS_REGION`, credentials, `BEDROCK_CHAT_MODEL_ID`, "
            "`BEDROCK_EMBEDDING_MODEL_ID`) then restart the app."
        )

    tab_search, tab_ask, tab_brief, tab_vector = st.tabs(
        [
            "Semantic Search",
            "Ask the Market Agent",
            "Research Brief",
            "Vector DB",
        ]
    )

    with tab_search:
        ui_helpers.section_header("Semantic Search", "Find articles by meaning, not just keywords.")
        sem_query = st.text_input(
            "Query",
            placeholder="e.g. AI chip demand, rate cuts, oil supply shocks…",
            key="sem_query",
        )
        sem_top_k = st.slider("Top results", 3, 15, 5, key="sem_top_k")
        rag_filters = _rag_filter_widgets("sem", df)

        if st.button("Search", type="primary", key="sem_btn"):
            if not sem_query.strip():
                st.info("Enter a search phrase.")
            else:
                with st.spinner("Searching vector database…"):
                    hits, err = vector_store.semantic_search(
                        sem_query, filters=rag_filters, top_k=sem_top_k
                    )
                if err:
                    st.error(err)
                elif not hits:
                    st.warning("No matches — sync the vector DB or relax filters.")
                else:
                    st.success(f"Found {len(hits)} article(s).")
                    ui_helpers.rag_results_panel(
                        hits,
                        title=f"Semantic search · {len(hits)} hit(s)",
                        key=f"sem_hits_{sem_query[:40]}",
                    )

    with tab_ask:
        ui_helpers.section_header("Ask the Market Agent", "RAG retrieves evidence, then Bedrock answers.")
        ask_top_k = st.slider("Articles to retrieve", 3, 12, 5, key="ask_top_k")
        ask_filters = _rag_filter_widgets("ask", df)

        examples = [
            "What are bearish signals in recent tech news?",
            "What themes are emerging around AI infrastructure?",
            "Why are semiconductor stocks moving recently?",
        ]

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        if "agent_evidence" not in st.session_state:
            st.session_state.agent_evidence = []
        if "agent_sources" not in st.session_state:
            st.session_state.agent_sources = []
        if "processed_agent_event_ids" not in st.session_state:
            st.session_state.processed_agent_event_ids = []
        elif isinstance(st.session_state.processed_agent_event_ids, set):
            st.session_state.processed_agent_event_ids = list(
                st.session_state.processed_agent_event_ids
            )

        if react_ui.is_react_available():
            agent_event = react_ui.market_agent(
                messages=st.session_state.chat_messages,
                examples=examples,
                sources=st.session_state.agent_sources,
                evidence=react_ui.articles_from_rows(st.session_state.agent_evidence),
                key="market_agent",
            )
            # Custom components keep returning the last click on every rerun — process once per eventId.
            if agent_event and agent_event.get("action") == "ask":
                event_id = str(agent_event.get("eventId") or "")
                if not event_id:
                    event_id = json.dumps(agent_event, sort_keys=True)
                processed_ids: list = st.session_state.processed_agent_event_ids
                if event_id and event_id not in processed_ids:
                    processed_ids.append(event_id)
                    if len(processed_ids) > 100:
                        st.session_state.processed_agent_event_ids = processed_ids[-50:]

                    question = str(agent_event.get("question", "")).strip()
                    if question:
                        st.session_state.chat_messages.append(
                            {"role": "user", "content": question}
                        )
                        with st.spinner("Retrieving evidence and generating answer…"):
                            result = rag_pipeline.answer_market_question(
                                question, filters=ask_filters, top_k=ask_top_k
                            )
                        if result.get("error"):
                            st.error(result["error"])
                        answer = result.get("answer") or ""
                        if answer:
                            st.session_state.chat_messages.append(
                                {"role": "assistant", "content": answer}
                            )
                        st.session_state.agent_evidence = (
                            result.get("retrieved_articles") or []
                        )
                        st.session_state.agent_sources = result.get("sources_used") or []
                        st.rerun()

            if st.button("Clear chat", key="clear_agent_chat"):
                st.session_state.chat_messages = []
                st.session_state.agent_evidence = []
                st.session_state.agent_sources = []
                st.session_state.processed_agent_event_ids = []
                st.rerun()
        else:
            st.markdown("**Try:** " + " · ".join(examples))
            question = st.text_area("Your question", height=100, key="rag_question")
            if st.button("Ask", type="primary", key="ask_btn"):
                if not question.strip():
                    st.info("Enter a question first.")
                else:
                    with st.spinner("Retrieving evidence and generating answer…"):
                        result = rag_pipeline.answer_market_question(
                            question, filters=ask_filters, top_k=ask_top_k
                        )
                    if result.get("error"):
                        st.error(result["error"])
                    if result.get("answer"):
                        ui_helpers.render_markdown_block("Answer", result["answer"])
                    st.markdown("#### Retrieved evidence")
                    for i, art in enumerate(result.get("retrieved_articles") or [], start=1):
                        ui_helpers.semantic_search_card(art, rank=i)
                    ui_helpers.citations_block(result.get("sources_used") or [], title="Sources used")

    with tab_brief:
        ui_helpers.section_header("Generate Research Brief", "Ticker, sector, or macro topic.")
        brief_topic = st.text_input(
            "Topic",
            placeholder="e.g. NVDA, semiconductors, Federal Reserve…",
            key="brief_topic",
        )
        brief_top_k = st.slider("Articles to include", 4, 15, 8, key="brief_top_k")
        brief_filters = _rag_filter_widgets("brief", df)

        if st.button("Generate Market Brief", type="primary", key="brief_btn"):
            if not brief_topic.strip():
                st.info("Enter a topic or ticker.")
            else:
                with st.spinner("Building cited research brief…"):
                    result = rag_pipeline.generate_market_brief(
                        brief_topic, filters=brief_filters, top_k=brief_top_k
                    )
                if result.get("error"):
                    st.error(result["error"])
                if result.get("brief"):
                    ui_helpers.render_markdown_block("Market Brief", result["brief"])
                ui_helpers.citations_block(result.get("sources_used") or [], title="Sources used")
                ui_helpers.rag_results_panel(
                    result.get("retrieved_articles") or [],
                    title="Evidence used",
                    key=f"brief_evidence_{brief_topic[:30]}",
                )

    with tab_vector:
        ui_helpers.section_header("Vector Database", "Local ChromaDB + Titan embeddings.")
        st.markdown(
            """
            **Workflow:** ingest news → Bedrock summaries → **Sync** below → search / ask / brief.

            Phase 3 will move vectors to **Amazon OpenSearch Serverless**.
            """
        )
        sqlite_n = db.count_articles(conn)
        chroma_n = vector_store.count_embedded_articles()
        ui_helpers.metrics_row(
            [
                ("SQLite articles", sqlite_n),
                ("ChromaDB vectors", chroma_n),
                ("Bedrock ready", "Yes" if aws_configured() else "No"),
            ],
            key="mi_vector_metrics",
        )
        st.caption(f"Vector store: `{config.VECTOR_DB_PATH}`")

        if st.button("Sync Articles to Vector DB", type="primary", key="sync_chroma"):
            if sqlite_n == 0:
                st.error("SQLite is empty — refresh market news in the sidebar first.")
            elif not embeddings.embeddings_configured():
                st.error("Set AWS_REGION and BEDROCK_EMBEDDING_MODEL_ID in `.env`.")
            else:
                with st.spinner("Embedding articles with Titan and upserting to Chroma…"):
                    articles = db.fetch_all_articles(conn)
                    stats = vector_store.sync_sqlite_articles_to_vector_store(articles)
                if stats.get("errors") and stats["embedded"] == 0 and stats["skipped"] == 0:
                    for msg in stats["errors"]:
                        st.error(msg)
                else:
                    st.success(
                        f"Sync complete — embedded: {stats['embedded']}, "
                        f"skipped: {stats['skipped']}, failed: {stats['failed']}."
                    )
                    if stats.get("errors"):
                        with st.expander("Warnings"):
                            for msg in stats["errors"]:
                                st.warning(msg)


def main() -> None:
    conn = _get_db_connection()
    df = db.fetch_articles_df(conn)
    pending_total = db.count_articles_needing_summary(conn)
    chroma_n = vector_store.count_embedded_articles()
    bedrock_ok = aws_configured()

    # --- Sidebar ---
    with st.sidebar:
        ui_helpers.render_quick_start_sidebar()
        st.divider()
        st.markdown("##### Data & AI")
        max_fetch = st.slider("Headlines per refresh", 5, 50, 20)

        if pending_total > 0:
            st.progress(
                1.0 - (pending_total / max(db.count_articles(conn), 1)),
                text=f"{pending_total} article(s) need summaries",
            )
        else:
            st.success("All articles summarized")

        batch_ai = st.slider(
            "AI batch size (per click)",
            1,
            50,
            min(10, max(8, pending_total)) if pending_total else 8,
        )

        if st.button("Refresh market news", type="primary", use_container_width=True):
            with st.spinner("Fetching headlines…"):
                try:
                    new_n, src = _ingest_latest(conn, max_items=max_fetch)
                    st.success(f"Added {new_n} new article(s) · {src}")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Ingestion failed: {exc}")

        if st.button("Run AI on pending (batch)", use_container_width=True):
            if pending_total == 0:
                st.info("Nothing pending.")
            else:
                with st.spinner(f"Summarizing up to {batch_ai} articles…"):
                    try:
                        stats = _summarize_pending(conn, batch_limit=batch_ai)
                        remaining = db.count_articles_needing_summary(conn)
                        st.success(
                            f"Processed {stats['processed']}: "
                            f"{stats['live']} live, {stats['demo']} demo, {stats['failed']} failed. "
                            f"{remaining} still pending."
                        )
                        for msg in stats.get("errors") or []:
                            st.error(msg)
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))

        if st.button("Summarize ALL pending", use_container_width=True):
            pending_all = db.count_articles_needing_summary(conn)
            if pending_all == 0:
                st.info("Nothing left to summarize.")
            else:
                with st.spinner(f"Summarizing {pending_all} articles — may take a few minutes…"):
                    try:
                        stats = _summarize_pending(conn, batch_limit=pending_all)
                        remaining = db.count_articles_needing_summary(conn)
                        st.success(
                            f"Done: {stats['live']} live, {stats['demo']} demo, "
                            f"{stats['failed']} failed. {remaining} still pending."
                        )
                        for msg in stats.get("errors") or []:
                            st.error(msg)
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                st.rerun()

        with st.expander("Advanced"):
            if st.button("Clear summaries & re-run Bedrock", use_container_width=True):
                cleared = db.clear_all_ai_summaries(conn)
                st.success(f"Cleared AI fields on {cleared} article(s). Re-run summarize.")
                st.rerun()

        st.divider()
        st.markdown("##### Filters")
        ticker_options = ["All"]
        if not df.empty and "ticker_category" in df.columns:
            ticker_options += sorted(df["ticker_category"].dropna().astype(str).unique().tolist())
        ticker_filter = st.selectbox("Ticker / category", ticker_options)

        sent_options = ["All"]
        if not df.empty and "sentiment" in df.columns:
            sent_options += sorted(df["sentiment"].dropna().astype(str).unique().tolist())
        sentiment_filter = st.selectbox("Sentiment", sent_options)

        src_options = ["All"]
        if not df.empty and "source" in df.columns:
            src_options += sorted(df["source"].dropna().astype(str).unique().tolist())
        source_filter = st.selectbox("Source", src_options)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            date_from = st.date_input("From", value=None)
        with col_d2:
            date_to = st.date_input("To", value=None)

        st.divider()
        search_q = st.text_input("Keyword search", placeholder="Titles & summaries…")

    ticker_val = None if ticker_filter == "All" else ticker_filter
    sentiment_val = None if sentiment_filter == "All" else sentiment_filter
    source_val = None if source_filter == "All" else source_filter
    d_from = date_from if isinstance(date_from, date) else None
    d_to = date_to if isinstance(date_to, date) else None

    filtered = analytics.filter_dataframe(
        df,
        ticker=ticker_val,
        sentiment=sentiment_val,
        source=source_val,
        date_from=d_from,
        date_to=d_to,
        search=search_q or None,
    )

    # --- Main ---
    ui_helpers.render_hero()
    if is_streamlit_cloud():
        st.caption(
            "Hosted on Streamlit Cloud · Data is ephemeral across redeploys — ideal for demos."
        )
    elif not react_ui.is_react_available() and not _IS_PRODUCTION:
        st.info(
            "Build React components for interactive UI: "
            "`./scripts/build_frontend.sh` then commit `frontend/build/` for Cloud."
        )
    ui_helpers.render_status_pills(
        bedrock=bedrock_ok,
        pending=pending_total,
        vector_count=chroma_n,
        article_count=analytics.article_count(df),
    )

    tab_dash, tab_feed, tab_rag, tab_help = st.tabs(
        ["Dashboard", "Market Feed", "RAG Intelligence", "Help & Demo"]
    )

    with tab_dash:
        ui_helpers.section_header("At a glance")
        total = analytics.article_count(df)
        top_topics_all = analytics.top_topics(df, top_n=10)
        latest_ts = analytics.latest_published_timestamp(df)
        latest_str = (
            latest_ts.strftime("%Y-%m-%d %H:%M UTC")
            if isinstance(latest_ts, datetime)
            else "—"
        )
        ui_helpers.metrics_row(
            [
                ("Articles in database", total),
                ("Matching filters", analytics.article_count(filtered)),
                ("Latest published", latest_str),
            ],
            key="mi_dash_metrics",
        )

        if pending_total > 0:
            ui_helpers.callout(
                f"You have **{pending_total}** article(s) without AI summaries. "
                "Use **Summarize ALL pending** in the sidebar before RAG."
            )

        st.divider()
        ui_helpers.dashboard_panel(
            analytics.sentiment_distribution(df),
            top_topics_all[:8],
            key="main_dashboard",
        )

    with tab_feed:
        ui_helpers.section_header("Latest headlines", "Filtered table of ingested market news.")
        if filtered.empty:
            st.info("No articles match your filters. Refresh news or relax filters in the sidebar.")
        else:
            display_cols = ["published_at", "title", "source", "ticker_category", "url"]
            exist = [c for c in display_cols if c in filtered.columns]
            table_df = filtered[exist].head(50).copy()
            if "published_at" in table_df.columns:
                dt = pd.to_datetime(table_df["published_at"], errors="coerce", utc=True)
                table_df["published_at"] = dt.dt.strftime("%Y-%m-%d %H:%M").fillna("—")
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                column_config={"url": st.column_config.LinkColumn("url")},
            )

        st.divider()
        ui_helpers.section_header("AI summaries", "Bedrock-generated bullets, sentiment, and topics.")
        show_n = st.slider("Cards to show", 3, 30, 10, key="feed_cards_n")
        feed_rows = [row.to_dict() for _, row in filtered.head(show_n).iterrows()]
        ui_helpers.article_feed(feed_rows, key="market_feed_cards")

    with tab_rag:
        _render_rag_tab(df, conn)

    with tab_help:
        ui_helpers.render_help_page()

    st.caption(
        "AWS Bedrock · Titan embeddings · ChromaDB · Optional Finnhub / NewsAPI / Yahoo RSS"
    )


main()
