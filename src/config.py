"""
Application configuration loaded from environment variables.

Beginners: `python-dotenv` loads a local `.env` file so you do not
hard-code secrets in source code.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = parent of `src/`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "market_news.db"

# Load .env from project root (safe if file is missing)
load_dotenv(PROJECT_ROOT / ".env")


def _coerce_secret_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        # Common paste mistakes in Streamlit Secrets UI
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            text = text[1:-1].strip()
        return text or None
    return None


_FORCE_ENV_KEYS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_PROFILE",
        "BEDROCK_CHAT_MODEL_ID",
        "BEDROCK_MODEL_ID",
        "BEDROCK_EMBEDDING_MODEL_ID",
        "BEDROCK_MAX_TOKENS",
        "TITAN_EMBED_DIMENSIONS",
        "DEPLOY_ENV",
        "DEPLOY_TARGET",
        "FINNHUB_API_KEY",
        "NEWSAPI_KEY",
    }
)


def _collect_streamlit_secrets(node: object, out: dict[str, str]) -> None:
    """Flatten Streamlit secrets (top-level and [sections]) into a dict."""
    if node is None:
        return
    keys_fn = getattr(node, "keys", None)
    if not callable(keys_fn):
        return
    for key in keys_fn():
        try:
            value = node[key]
        except Exception:
            continue
        text = _coerce_secret_value(value)
        if text is not None:
            out[str(key)] = text
        else:
            _collect_streamlit_secrets(value, out)


def _apply_streamlit_secrets() -> None:
    """Map Streamlit Community Cloud secrets into os.environ."""
    try:
        import streamlit as st

        collected: dict[str, str] = {}
        _collect_streamlit_secrets(st.secrets, collected)
        for key, text in collected.items():
            # Overwrite empty .env placeholders so Cloud secrets always win
            if key in _FORCE_ENV_KEYS:
                os.environ[key] = text
            else:
                os.environ.setdefault(key, text)
    except Exception:
        return


def reload_from_env() -> None:
    """Refresh module-level settings after Streamlit secrets are applied."""
    global AWS_REGION, AWS_PROFILE, BEDROCK_CHAT_MODEL_ID, BEDROCK_MODEL_ID
    global BEDROCK_EMBEDDING_MODEL_ID, BEDROCK_MAX_TOKENS, TITAN_EMBED_DIMENSIONS
    global VECTOR_DB_PATH, CHROMA_COLLECTION_NAME, CHROMA_DB_PATH
    global FINNHUB_API_KEY, NEWSAPI_KEY

    AWS_REGION = _get_env("AWS_REGION", "us-east-1") or "us-east-1"
    AWS_PROFILE = _get_env("AWS_PROFILE")
    BEDROCK_CHAT_MODEL_ID = (
        _get_env("BEDROCK_CHAT_MODEL_ID")
        or _get_env("BEDROCK_MODEL_ID")
        or "anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    BEDROCK_MODEL_ID = BEDROCK_CHAT_MODEL_ID
    BEDROCK_EMBEDDING_MODEL_ID = (
        _get_env("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
        or "amazon.titan-embed-text-v2:0"
    )
    _max_tok = _get_env("BEDROCK_MAX_TOKENS", "1024") or "1024"
    try:
        BEDROCK_MAX_TOKENS = max(256, min(4096, int(_max_tok)))
    except ValueError:
        BEDROCK_MAX_TOKENS = 1024
    _dim = _get_env("TITAN_EMBED_DIMENSIONS", "1024") or "1024"
    try:
        TITAN_EMBED_DIMENSIONS = int(_dim)
        if TITAN_EMBED_DIMENSIONS not in (256, 512, 1024):
            TITAN_EMBED_DIMENSIONS = 1024
    except ValueError:
        TITAN_EMBED_DIMENSIONS = 1024
    _vector_path = _get_env("VECTOR_DB_PATH", "data/vector_db") or "data/vector_db"
    VECTOR_DB_PATH = (
        (PROJECT_ROOT / _vector_path).resolve()
        if not Path(_vector_path).is_absolute()
        else Path(_vector_path)
    )
    CHROMA_COLLECTION_NAME = _get_env("CHROMA_COLLECTION_NAME", "market_articles") or "market_articles"
    CHROMA_DB_PATH = VECTOR_DB_PATH
    FINNHUB_API_KEY = _get_env("FINNHUB_API_KEY")
    NEWSAPI_KEY = _get_env("NEWSAPI_KEY")


def refresh_streamlit_secrets() -> None:
    """Call after `st.set_page_config` so Cloud secrets are loaded before AWS clients."""
    _apply_streamlit_secrets()
    if os.getenv("AWS_PROFILE", "").strip() == "":
        os.environ.pop("AWS_PROFILE", None)
    reload_from_env()


def is_streamlit_cloud() -> bool:
    return os.getenv("DEPLOY_TARGET", "").strip().lower() == "streamlit-cloud"


# Local .env only (Cloud uses Secrets UI)
_apply_streamlit_secrets()

# Empty AWS_PROFILE breaks boto3 ("config profile () could not be found")
if os.getenv("AWS_PROFILE", "").strip() == "":
    os.environ.pop("AWS_PROFILE", None)


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return value.strip()


# --- AWS / Amazon Bedrock (initialized; call reload_from_env() after Streamlit secrets) ---
AWS_REGION: str = "us-east-1"
AWS_PROFILE: str | None = None
BEDROCK_CHAT_MODEL_ID: str | None = None
BEDROCK_MODEL_ID: str | None = None
BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
BEDROCK_MAX_TOKENS: int = 1024
TITAN_EMBED_DIMENSIONS: int = 1024
VECTOR_DB_PATH: Path = DATA_DIR / "vector_db"
CHROMA_COLLECTION_NAME: str = "market_articles"
CHROMA_DB_PATH: Path = VECTOR_DB_PATH
FINNHUB_API_KEY: str | None = None
NEWSAPI_KEY: str | None = None

reload_from_env()

# Ensure data directories exist when other modules import config
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
