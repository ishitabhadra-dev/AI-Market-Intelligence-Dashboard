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


def _apply_streamlit_secrets() -> None:
    """Map Streamlit Community Cloud secrets.toml into os.environ (setdefault only)."""
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:
        return
    try:
        for key, value in secrets.items():
            if isinstance(value, str) and value.strip():
                os.environ.setdefault(str(key), value.strip())
    except Exception:
        return


def refresh_streamlit_secrets() -> None:
    """Call after `st.set_page_config` so Cloud secrets are loaded before AWS clients."""
    _apply_streamlit_secrets()
    if os.getenv("AWS_PROFILE", "").strip() == "":
        os.environ.pop("AWS_PROFILE", None)


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


# --- AWS / Amazon Bedrock ---
AWS_REGION: str = _get_env("AWS_REGION", "us-east-1") or "us-east-1"
AWS_PROFILE: str | None = _get_env("AWS_PROFILE")

# Chat model (Phase 1 summaries + Phase 2 RAG)
# Examples: anthropic.claude-3-5-haiku-20241022-v1:0 | amazon.nova-lite-v1:0
# Inference profile id (required for Claude 3.5 Haiku on-demand in many regions)
BEDROCK_CHAT_MODEL_ID: str | None = (
    _get_env("BEDROCK_CHAT_MODEL_ID")
    or _get_env("BEDROCK_MODEL_ID")
    or "us.anthropic.claude-sonnet-4-6"
)
# Back-compat alias used in older docs
BEDROCK_MODEL_ID: str | None = BEDROCK_CHAT_MODEL_ID

# Titan embeddings (Phase 2 semantic search)
BEDROCK_EMBEDDING_MODEL_ID: str = (
    _get_env("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    or "amazon.titan-embed-text-v2:0"
)

_max_tok = _get_env("BEDROCK_MAX_TOKENS", "1024") or "1024"
try:
    BEDROCK_MAX_TOKENS: int = max(256, min(4096, int(_max_tok)))
except ValueError:
    BEDROCK_MAX_TOKENS = 1024

_dim = _get_env("TITAN_EMBED_DIMENSIONS", "1024") or "1024"
try:
    TITAN_EMBED_DIMENSIONS: int = int(_dim)
    if TITAN_EMBED_DIMENSIONS not in (256, 512, 1024):
        TITAN_EMBED_DIMENSIONS = 1024
except ValueError:
    TITAN_EMBED_DIMENSIONS = 1024

# --- Local vector store (ChromaDB for Phase 2; OpenSearch Serverless in Phase 3) ---
_vector_path = _get_env("VECTOR_DB_PATH", "data/vector_db") or "data/vector_db"
VECTOR_DB_PATH: Path = (
    (PROJECT_ROOT / _vector_path).resolve()
    if not Path(_vector_path).is_absolute()
    else Path(_vector_path)
)
CHROMA_COLLECTION_NAME: str = _get_env("CHROMA_COLLECTION_NAME", "market_articles") or "market_articles"
# Alias for older references
CHROMA_DB_PATH: Path = VECTOR_DB_PATH

# --- News APIs ---
FINNHUB_API_KEY: str | None = _get_env("FINNHUB_API_KEY")
NEWSAPI_KEY: str | None = _get_env("NEWSAPI_KEY")

# Ensure data directories exist when other modules import config
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
