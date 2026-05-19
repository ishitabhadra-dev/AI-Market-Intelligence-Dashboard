"""
Financial news ingestion from free sources.

Priority:
1. Finnhub (if FINNHUB_API_KEY is set) — rich JSON, easy to parse
2. NewsAPI (if NEWSAPI_KEY is set)
3. Yahoo Finance RSS (no key) via `requests`
4. Curated demo articles if every live source fails or returns nothing

Beginners: each `fetch_*` function returns the same list shape so the
rest of the app does not care which provider succeeded.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)

# Yahoo headline feed (broad market); works without an API key
YAHOO_RSS_URL = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline?"
    "s=%5EGSPC,%5EDJI,%5EIXIC&region=US&lang=en-US"
)


def _iso_from_unix(ts: int | float | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def _normalize_item(
    title: str,
    source: str | None,
    url: str,
    published_at: str | None,
    ticker_category: str | None,
) -> dict[str, Any]:
    return {
        "title": title.strip(),
        "source": (source or "Unknown").strip(),
        "url": url.strip(),
        "published_at": published_at,
        "ticker_category": (ticker_category or "General").strip(),
    }


def fetch_finnhub(max_items: int = 30) -> list[dict[str, Any]]:
    """General market news from Finnhub (requires API key)."""
    if not config.FINNHUB_API_KEY:
        return []
    url = "https://finnhub.io/api/v1/news"
    params = {"category": "general", "token": config.FINNHUB_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("Finnhub request failed: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return out
    for row in data[:max_items]:
        if not isinstance(row, dict):
            continue
        title = row.get("headline") or row.get("title") or ""
        link = row.get("url") or ""
        if not title or not link:
            continue
        pub = _iso_from_unix(row.get("datetime"))
        src = row.get("source")
        cat = row.get("category") or "General"
        out.append(_normalize_item(title, src, link, pub, cat))
    return out


def fetch_newsapi(max_items: int = 30) -> list[dict[str, Any]]:
    """Headlines from NewsAPI (requires API key)."""
    if not config.NEWSAPI_KEY:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "stock market OR finance OR economy",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(max_items, 100),
        "apiKey": config.NEWSAPI_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        logger.warning("NewsAPI request failed: %s", exc)
        return []

    articles = payload.get("articles") or []
    out: list[dict[str, Any]] = []
    for row in articles:
        if not isinstance(row, dict):
            continue
        title = row.get("title") or ""
        link = row.get("url") or ""
        if not title or not link:
            continue
        pub_raw = row.get("publishedAt")
        src = (row.get("source") or {}).get("name") if isinstance(row.get("source"), dict) else row.get("source")
        out.append(_normalize_item(title, src, link, pub_raw, "NewsAPI"))
    return out


def _parse_rss_xml(xml_text: str, max_items: int) -> list[dict[str, Any]]:
    """Parse RSS 2.0 items from raw XML (used for Yahoo Finance)."""
    out: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("RSS parse error: %s", exc)
        return out

    # RSS 2.0: channel/item
    channel = root.find("channel")
    if channel is None:
        return out
    for item in channel.findall("item")[:max_items]:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        pub = (pub_el.text or "").strip() if pub_el is not None else None
        if not title or not link:
            continue
        out.append(_normalize_item(title, "Yahoo Finance", link, pub, "Indices"))
    return out


def fetch_yahoo_rss(max_items: int = 30) -> list[dict[str, Any]]:
    """Yahoo Finance RSS — no API key required."""
    try:
        resp = requests.get(YAHOO_RSS_URL, timeout=20, headers={"User-Agent": "AIMarketIntel/1.0"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Yahoo RSS request failed: %s", exc)
        return []
    return _parse_rss_xml(resp.text, max_items)


def demo_articles() -> list[dict[str, Any]]:
    """
    Static sample stories so the dashboard is usable on day one
    without any API keys (great for learning / demos).
    """
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return [
        _normalize_item(
            "Major indices steady as investors weigh inflation data",
            "Demo Feed",
            "https://example.com/demo/inflation-indices",
            now,
            "SPY",
        ),
        _normalize_item(
            "Tech earnings preview: what analysts expect this quarter",
            "Demo Feed",
            "https://example.com/demo/tech-earnings",
            now,
            "QQQ",
        ),
        _normalize_item(
            "Energy sector volatility tied to supply headlines",
            "Demo Feed",
            "https://example.com/demo/energy-supply",
            now,
            "XLE",
        ),
    ]


def fetch_latest_news(max_items: int = 30) -> tuple[list[dict[str, Any]], str]:
    """
    Try providers in order; return (articles, source_label).

    `source_label` tells the UI which backend supplied the batch
    (helpful when debugging keys and quotas).
    """
    for label, fn in (
        ("Finnhub", lambda: fetch_finnhub(max_items)),
        ("NewsAPI", lambda: fetch_newsapi(max_items)),
        ("Yahoo Finance RSS", lambda: fetch_yahoo_rss(max_items)),
    ):
        try:
            items = fn()
        except Exception as exc:  # noqa: BLE001 — defensive for demo app
            logger.exception("Unexpected error in %s: %s", label, exc)
            items = []
        if items:
            return items[:max_items], label

    return demo_articles(), "Demo data (no API keys / all sources failed)"
