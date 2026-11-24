"""LiteLLM in-memory cache configuration.

We use LiteLLM's built-in local (in-memory) cache. The cache key is derived
by LiteLLM from the full completion-call payload — model + messages — so the
system prompt, conversation history, and the new user message all contribute
to cache identity. No Redis or external cache is used.
"""

import litellm
from litellm.caching import Cache


def configure_cache() -> None:
    """Enable LiteLLM's in-memory cache for all completion calls."""
    litellm.cache = Cache(type="local")


def cache_enabled() -> bool:
    return litellm.cache is not None
