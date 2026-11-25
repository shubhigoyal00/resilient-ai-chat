"""Integration tests exercising the REAL LiteLLM in-memory cache.

Only the network dispatch layer (VertexLLM.completion inside litellm.main)
is patched — LiteLLM's caching handler runs for real, so cache-hit
detection reflects actual library behavior on the installed version.
"""

import pytest

from tests.conftest import post_chat


class TestLiteLLMCache:
    def test_second_identical_request_hits_cache(self, client, provider_spy):
        r1 = post_chat(client, session_id="s-cache-1", message="Hello")
        assert r1.status_code == 200
        assert r1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert r1.json()["metadata"]["key_id"] == "key_1"

        # Same first message in a NEW session -> same full payload -> cache hit.
        r2 = post_chat(client, session_id="s-cache-2", message="Hello")
        assert r2.status_code == 200
        meta = r2.json()["metadata"]
        assert meta["resolution_source"] == "LLM_CACHE"
        assert meta["key_id"] is None
        assert meta["fallback_attempts"] == 0
        # Identical reply and stored token usage preserved.
        assert r2.json()["reply"] == r1.json()["reply"]
        assert meta["input_tokens"] == r1.json()["metadata"]["input_tokens"]
        assert meta["output_tokens"] == r1.json()["metadata"]["output_tokens"]
        # The provider was invoked exactly once.
        assert len(provider_spy) == 1

    def test_different_message_misses_cache(self, client, provider_spy):
        post_chat(client, session_id="s-iso-1", message="Hello")
        r = post_chat(client, session_id="s-iso-2", message="Goodbye")
        assert r.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert len(provider_spy) == 2

    def test_history_changes_cache_key(self, client, provider_spy):
        post_chat(client, session_id="s-hist", message="Hello")
        # Same session now has history -> different full payload -> miss.
        r = post_chat(client, session_id="s-hist", message="Hello again")
        assert r.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert len(provider_spy) == 2

    def test_different_system_prompt_misses_cache(self, client, provider_spy):
        post_chat(client, session_id="s-sp-1", message="Hello")
        r = post_chat(client, session_id="s-sp-2", message="Hello",
                      system_prompt="Answer like a pirate.")
        assert r.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert len(provider_spy) == 2

    def test_cache_hit_skips_provider(self, client, provider_spy):
        # The real speed win is that no provider call happens on a hit;
        # asserting on wall-time would be flaky for in-process calls.
        r1 = post_chat(client, session_id="s-fast-1", message="Hello")
        r2 = post_chat(client, session_id="s-fast-2", message="Hello")
        assert r1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert r2.json()["metadata"]["resolution_source"] == "LLM_CACHE"
        assert len(provider_spy) == 1
