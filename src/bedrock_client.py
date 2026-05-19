"""
Amazon Bedrock client — text generation and Titan embeddings (Phase 1 + 2).

**How Bedrock works (beginners):**
- Your app calls `bedrock-runtime` in AWS with `invoke_model`.
- AWS runs the model (Claude, Nova, Titan, etc.) and returns JSON.
- You authenticate with the normal AWS chain: `aws configure`, env vars, or IAM role.
- Your IAM user needs `bedrock:InvokeModel` and model access enabled in the console.

This module replaces OpenAI for summaries, RAG chat, and embeddings.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
)

from src import config

logger = logging.getLogger(__name__)


class BedrockError(Exception):
    """Clear error when Bedrock cannot be called."""


def get_bedrock_runtime_client():
    """
    Create a Bedrock Runtime client for the configured region.

    Uses optional AWS_PROFILE from `.env` when set.
    """
    if not config.AWS_REGION:
        raise BedrockError("AWS_REGION is not set. Add AWS_REGION=us-east-1 to your `.env` file.")

    profile = (config.AWS_PROFILE or "").strip()
    session_kwargs: dict[str, Any] = {}
    if profile:
        session_kwargs["profile_name"] = profile

    try:
        session = boto3.Session(**session_kwargs)
        creds = session.get_credentials()
        if creds is None:
            raise BedrockError(
                "AWS credentials not found. Run `aws configure` or set AWS_ACCESS_KEY_ID / "
                "AWS_SECRET_ACCESS_KEY."
            )
        return session.client("bedrock-runtime", region_name=config.AWS_REGION)
    except (NoCredentialsError, PartialCredentialsError) as exc:
        raise BedrockError(f"AWS credentials error: {exc}") from exc
    except ProfileNotFound as exc:
        raise BedrockError(
            f"AWS profile '{profile}' not found. Remove AWS_PROFILE from `.env` or run `aws configure`."
        ) from exc


def bedrock_chat_configured() -> bool:
    """True when region + chat model id are set (credentials checked at call time)."""
    return bool(config.AWS_REGION and config.BEDROCK_CHAT_MODEL_ID)


def bedrock_embeddings_configured() -> bool:
    """True when region + Titan embedding model id are set."""
    return bool(config.AWS_REGION and config.BEDROCK_EMBEDDING_MODEL_ID)


def aws_configured() -> bool:
    """Phase 2 UI helper — chat + embeddings model ids and region present."""
    return bedrock_chat_configured() and bedrock_embeddings_configured()


def _geo_prefix_for_region(region: str) -> str:
    """Map AWS region to Bedrock inference-profile geography prefix."""
    r = (region or "us-east-1").lower()
    if r.startswith("us-"):
        return "us"
    if r.startswith("eu-"):
        return "eu"
    if r.startswith("ap-"):
        return "apac"
    return "us"


def resolve_chat_model_id(model_id: str | None = None) -> str:
    """
    Resolve the id passed to `invoke_model`.

    Newer Anthropic models (e.g. Claude 3.5 Haiku) require an **inference profile**
    id such as `us.anthropic.claude-3-5-haiku-20241022-v1:0`, not the bare
    foundation-model id `anthropic.claude-3-5-haiku-20241022-v1:0`.

    See: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-use.html
    """
    mid = (model_id or config.BEDROCK_CHAT_MODEL_ID or "").strip()
    if not mid:
        raise BedrockError("BEDROCK_CHAT_MODEL_ID is not set in `.env`.")

    first = mid.split(".", 1)[0]
    if first in ("us", "eu", "apac"):
        return mid

    # All current Claude models on Bedrock use inference profile ids (us./eu./apac. prefix)
    if mid.startswith("anthropic."):
        prefix = _geo_prefix_for_region(config.AWS_REGION)
        return f"{prefix}.{mid}"

    return mid


def _uses_anthropic_message_format(model_id: str) -> bool:
    return "anthropic" in model_id.lower()


def _read_invoke_body(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    if body is None:
        return {}
    raw = body.read() if hasattr(body, "read") else body
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _invoke(model_id: str, body: dict[str, Any]) -> dict[str, Any]:
    client = get_bedrock_runtime_client()
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        return _read_invoke_body(response)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        hint = ""
        if code == "ResourceNotFoundException" and "Legacy" in msg:
            hint = (
                " Update BEDROCK_CHAT_MODEL_ID to an active model, e.g. "
                "us.anthropic.claude-3-5-haiku-20241022-v1:0 or amazon.nova-lite-v1:0"
            )
        elif code == "ValidationException" and "inference profile" in msg.lower():
            hint = (
                " Set BEDROCK_CHAT_MODEL_ID to an inference profile id, e.g. "
                "us.anthropic.claude-3-5-haiku-20241022-v1:0 (copy from Bedrock → Model catalog)."
            )
        raise BedrockError(f"Bedrock [{code}]: {msg}{hint}") from exc
    except BotoCoreError as exc:
        raise BedrockError(f"AWS SDK error: {exc}") from exc


def invoke_titan_embedding_model(text: str) -> list[float]:
    """
    Amazon Titan Text Embeddings via `invoke_model`.

    Model example: amazon.titan-embed-text-v2:0
    """
    cleaned = (text or "").strip()
    if not cleaned:
        raise BedrockError("Cannot embed empty text.")

    if not config.BEDROCK_EMBEDDING_MODEL_ID:
        raise BedrockError("BEDROCK_EMBEDDING_MODEL_ID is not set in `.env`.")

    # Titan v2 accepts inputText; dimensions optional (256/512/1024).
    body: dict[str, Any] = {
        "inputText": cleaned,
        "dimensions": config.TITAN_EMBED_DIMENSIONS,
        "normalize": True,
    }
    payload = _invoke(config.BEDROCK_EMBEDDING_MODEL_ID, body)
    embedding = payload.get("embedding")
    if not isinstance(embedding, list):
        raise BedrockError("Unexpected Titan embedding response shape.")
    return [float(x) for x in embedding]


def _parse_anthropic_text(payload: dict[str, Any]) -> str:
    for block in payload.get("content") or []:
        if isinstance(block, dict) and block.get("text"):
            return str(block["text"]).strip()
    return ""


def _parse_nova_text(payload: dict[str, Any]) -> str:
    output = payload.get("output") or {}
    message = output.get("message") or {}
    for block in message.get("content") or []:
        if isinstance(block, dict) and block.get("text"):
            return str(block["text"]).strip()
    return ""


def invoke_bedrock_text_model(
    prompt: str,
    *,
    system_prompt: str | None = None,
    model_id: str | None = None,
) -> str:
    """
    Invoke a Bedrock chat model with `invoke_model`.

    Routes by model id prefix:
    - anthropic.* → Claude Messages API body
    - amazon.nova* → Amazon Nova messages body
    """
    user_text = (prompt or "").strip()
    if not user_text:
        raise BedrockError("Prompt is empty.")

    mid = resolve_chat_model_id(model_id)

    system_text = (system_prompt or "").strip()
    temperature = 0.2
    max_tokens = config.BEDROCK_MAX_TOKENS

    if _uses_anthropic_message_format(mid):
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_text}],
        }
        if system_text:
            body["system"] = system_text
        payload = _invoke(mid, body)
        text = _parse_anthropic_text(payload)
    elif "nova" in mid.lower():
        body = {
            "schemaVersion": "messages-v1",
            "messages": [{"role": "user", "content": [{"text": user_text}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system_text:
            body["system"] = [{"text": system_text}]
        payload = _invoke(mid, body)
        text = _parse_nova_text(payload)
    else:
        # Generic: single user message for other text models
        body = {
            "messages": [{"role": "user", "content": [{"text": user_text}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system_text:
            body["system"] = [{"text": system_text}]
        payload = _invoke(mid, body)
        text = _parse_nova_text(payload) or _parse_anthropic_text(payload)
        if not text and "generation" in payload:
            text = str(payload.get("generation", "")).strip()

    if not text:
        raise BedrockError("Bedrock returned an empty text response.")
    return text
