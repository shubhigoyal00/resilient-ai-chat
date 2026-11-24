"""LiteLLM + Gemini inference with multi-key fallback and failure simulation.

Every real LLM call goes through ``litellm.acompletion``. Caching is handled
by LiteLLM's built-in in-memory cache (configured in cache_service).
"""

import logging
import time

import litellm

from app.config import get_settings

logger = logging.getLogger(__name__)

# Statuses supported by the X-Simulate-Failure header.
SIMULATED_STATUSES = {429, 500, 502, 503}
# HTTP statuses that trigger a fallback to the next key.
FALLBACK_STATUSES = {429, 500, 502, 503, 504}


class AllProvidersUnavailable(Exception):
    """Raised when every configured key failed for a request."""


def parse_simulation_header(raw: str | None) -> dict[str, int]:
    """Parse 'key_1=429,key_2=503' or '*=429' into {name: status}."""
    sim: dict[str, int] = {}
    if not raw:
        return sim
    for part in raw.split(","):
        name, sep, status = part.partition("=")
        name = name.strip()
        if not sep or not name:
            continue
        try:
            code = int(status.strip())
        except ValueError:
            continue
        if code in SIMULATED_STATUSES:
            sim[name] = code
    return sim


def _field(obj, name: str, default=None):
    """Read an attribute or dict key, whichever the object supports."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_reply(response) -> str:
    choices = _field(response, "choices", []) or []
    message = _field(choices[0], "message", {}) if choices else {}
    return _field(message, "content", "") or ""


def _extract_usage(response) -> tuple[int, int]:
    usage = _field(response, "usage")
    prompt = _field(usage, "prompt_tokens", 0) or 0
    completion = _field(usage, "completion_tokens", 0) or 0
    return int(prompt), int(completion)


def _is_cache_hit(response) -> bool:
    """Detect a LiteLLM cache hit. LiteLLM marks cached responses via
    ``cache_hit`` inside ``_hidden_params`` (exposed as ``hidden_params``
    on some versions) and/or as a top-level attribute."""
    if _field(response, "cache_hit", False):
        return True
    for attr in ("_hidden_params", "hidden_params"):
        hidden = _field(response, attr) or {}
        if _field(hidden, "cache_hit", False):
            return True
    return False


async def generate_reply(
    messages: list[dict],
    simulate: dict[str, int] | None = None,
) -> tuple[str, dict]:
    """Try each configured key in order; return (reply, metadata).

    On a LiteLLM cache hit, no provider key is consumed and the stored
    response/usage is returned verbatim.
    """
    settings = get_settings()
    simulate = simulate or {}
    start = time.perf_counter()
    fallback_attempts = 0
    last_error: Exception | None = None

    for key_id, secret in settings.key_pool:
        simulated = simulate.get(key_id, simulate.get("*"))
        if simulated is not None:
            # The selected key fails for this request only.
            fallback_attempts += 1
            continue
        try:
            response = await litellm.acompletion(
                model=settings.gemini_model,
                messages=messages,
                api_key=secret,
            )
        except Exception as exc:  # 429 / quota / 5xx / network -> next key
            last_error = exc
            # Never log the secret itself — only the key identifier and error.
            logger.warning(
                "[LiteLLM ERROR] %s: %s: %s", key_id, type(exc).__name__, exc
            )
            fallback_attempts += 1
            continue

        reply = _extract_reply(response)
        input_tokens, output_tokens = _extract_usage(response)
        latency_ms = int((time.perf_counter() - start) * 1000)

        if _is_cache_hit(response):
            return reply, {
                "resolution_source": "LLM_CACHE",
                "model": settings.gemini_model,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": None,
                "fallback_attempts": 0,
            }
        return reply, {
            "resolution_source": "LIVE_INFERENCE",
            "model": settings.gemini_model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "key_id": key_id,
            "fallback_attempts": fallback_attempts,
        }

    raise AllProvidersUnavailable("all providers unavailable") from last_error
