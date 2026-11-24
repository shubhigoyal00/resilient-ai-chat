"""API tests: health, validation, chat, history, isolation, failover."""

import litellm
import pytest

from app.config import get_settings
from tests.conftest import make_model_response, post_chat


def make_acompletion_fake(recorded, text="Hi there!", prompt_tokens=42, output_tokens=9,
                          failing_keys=None, error=None):
    """Replace litellm.acompletion. Records every call's model/messages/api_key."""
    async def fake(*, model=None, messages=None, api_key=None, **kwargs):
        recorded.append({"model": model, "messages": messages, "api_key": api_key})
        if failing_keys and api_key in failing_keys:
            raise error or provider_error(429)
        return make_model_response(text, prompt_tokens, output_tokens)
    return fake


def provider_error(status: int):
    try:
        return litellm.APIError(
            status_code=status, message="provider error",
            llm_provider="gemini", model="gemini/gemini-3.5-flash-lite",
        )
    except TypeError:
        exc = Exception("provider error")
        exc.status_code = status
        return exc


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "keys_configured": 2, "cache_enabled": True}

    def test_health_degraded_with_one_key(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "llm_api_keys", "only-one")
        r = client.get("/health")
        assert r.status_code == 503
        assert r.json()["status"] == "unhealthy"
        assert r.json()["keys_configured"] == 1


class TestValidation:
    def test_missing_session_id(self, client):
        assert client.post("/chat", json={"message": "hi"}).status_code == 422

    def test_empty_session_id(self, client):
        r = client.post("/chat", json={"session_id": "", "message": "hi"})
        assert r.status_code == 422

    def test_session_id_too_long(self, client):
        r = client.post("/chat", json={"session_id": "x" * 129, "message": "hi"})
        assert r.status_code == 422

    def test_empty_message(self, client):
        r = post_chat(client, message="")
        assert r.status_code == 422

    def test_whitespace_only_message(self, client):
        r = post_chat(client, message="    ")
        assert r.status_code == 422

    def test_overlength_message(self, client):
        r = post_chat(client, message="a" * 4001)
        assert r.status_code == 422

    def test_max_length_message_accepted(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        r = post_chat(client, session_id="s-max", message="a" * 4000)
        assert r.status_code == 200

    def test_malformed_json(self, client):
        r = client.post("/chat", content="{not json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422
        assert "detail" in r.json()


class TestChat:
    def test_successful_chat(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        r = post_chat(client, session_id="s-7f3a", message="Hello")
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] == "s-7f3a"
        assert body["reply"] == "Hi there!"
        meta = body["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["model"] == "gemini/gemini-3.5-flash-lite"
        assert isinstance(meta["latency_ms"], int)
        assert meta["input_tokens"] == 42
        assert meta["output_tokens"] == 9
        assert meta["key_id"] == "key_1"
        assert meta["fallback_attempts"] == 0
        # Key secret never leaves the backend.
        assert "test-secret-1" not in r.text

    def test_messages_stored_after_success(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        post_chat(client, session_id="s-store", message="Hello")
        r = client.get("/sessions/s-store/messages")
        assert r.status_code == 200
        msgs = r.json()
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["content"] == "Hi there!"
        assert msgs[1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    def test_multi_turn_history_sent_to_llm(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        post_chat(client, session_id="s-multi", message="first")
        post_chat(client, session_id="s-multi", message="second")
        msgs = recorded[-1]["messages"]
        assert msgs[0] == {"role": "system", "content": "You are a helpful assistant."}
        assert msgs[1] == {"role": "user", "content": "first"}
        assert msgs[2] == {"role": "assistant", "content": "Hi there!"}
        assert msgs[3] == {"role": "user", "content": "second"}

    def test_system_prompt_override_persists(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        post_chat(client, session_id="s-sys", message="one", system_prompt="You are terse.")
        assert recorded[-1]["messages"][0] == {"role": "system", "content": "You are terse."}
        # A later request without system_prompt reuses the stored override.
        post_chat(client, session_id="s-sys", message="two")
        assert recorded[-1]["messages"][0] == {"role": "system", "content": "You are terse."}
        # The system prompt is never stored as a visible message.
        roles = [m["role"] for m in client.get("/sessions/s-sys/messages").json()]
        assert "system" not in roles

    def test_session_isolation(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        post_chat(client, session_id="s-a", message="alpha")
        post_chat(client, session_id="s-b", message="beta")
        b_msgs = recorded[-1]["messages"]
        assert [m["content"] for m in b_msgs if m["role"] == "user"] == ["beta"]
        assert client.get("/sessions/s-a/messages").json()[0]["content"] == "alpha"
        assert client.get("/sessions/s-b/messages").json()[0]["content"] == "beta"

    def test_unknown_session_404(self, client):
        r = client.get("/sessions/nope/messages")
        assert r.status_code == 404
        assert r.json() == {"detail": "session not found"}


class TestFallback:
    def test_provider_429_falls_back_to_key_2(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(
            litellm, "acompletion",
            make_acompletion_fake(recorded, failing_keys={"test-secret-1"}),
        )
        r = post_chat(client, session_id="s-fb", message="Hello")
        assert r.status_code == 200
        meta = r.json()["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1
        assert recorded[0]["api_key"] == "test-secret-1"
        assert recorded[1]["api_key"] == "test-secret-2"

    def test_provider_5xx_falls_back(self, client, monkeypatch):
        monkeypatch.setattr(
            litellm, "acompletion",
            make_acompletion_fake([], failing_keys={"test-secret-1"}, error=provider_error(503)),
        )
        r = post_chat(client, session_id="s-fb5", message="Hello")
        assert r.status_code == 200
        assert r.json()["metadata"]["key_id"] == "key_2"

    def test_all_providers_fail_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(
            litellm, "acompletion",
            make_acompletion_fake([], failing_keys={"test-secret-1", "test-secret-2"}),
        )
        r = post_chat(client, session_id="s-dead", message="Hello")
        assert r.status_code == 503
        assert r.json() == {"detail": "all providers unavailable"}

    def test_failed_request_not_stored(self, client, monkeypatch):
        monkeypatch.setattr(
            litellm, "acompletion",
            make_acompletion_fake([], failing_keys={"test-secret-1", "test-secret-2"}),
        )
        post_chat(client, session_id="s-failed", message="Hello")
        assert client.get("/sessions/s-failed/messages").status_code == 404

    def test_history_clean_after_failure(self, client, monkeypatch):
        recorded = []
        fake = make_acompletion_fake(recorded, failing_keys={"test-secret-1", "test-secret-2"})
        monkeypatch.setattr(litellm, "acompletion", fake)
        post_chat(client, session_id="s-recover", message="first")
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        post_chat(client, session_id="s-recover", message="second")
        contents = [m["content"] for m in recorded[-1]["messages"]]
        assert contents == ["You are a helpful assistant.", "second"]


class TestFailureSimulation:
    def test_sim_key1_429_falls_back(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        r = post_chat(client, session_id="s-sim", message="Hello",
                      headers={"X-Simulate-Failure": "key_1=429"})
        assert r.status_code == 200
        meta = r.json()["metadata"]
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1
        # Only key_2 made a real call.
        assert len(recorded) == 1
        assert recorded[0]["api_key"] == "test-secret-2"

    def test_sim_key1_500_falls_back(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        r = post_chat(client, session_id="s-sim5", message="Hello",
                      headers={"X-Simulate-Failure": "key_1=500"})
        assert r.status_code == 200
        assert r.json()["metadata"]["key_id"] == "key_2"

    def test_sim_both_keys_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        r = post_chat(client, session_id="s-simall", message="Hello",
                      headers={"X-Simulate-Failure": "key_1=500,key_2=503"})
        assert r.status_code == 503
        assert r.json() == {"detail": "all providers unavailable"}

    def test_sim_wildcard_returns_503(self, client, monkeypatch):
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        r = post_chat(client, session_id="s-simwild", message="Hello",
                      headers={"X-Simulate-Failure": "*=429"})
        assert r.status_code == 503
        assert r.json() == {"detail": "all providers unavailable"}
        assert recorded == []

    def test_sim_ignored_when_disabled(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "enable_failure_simulation", False)
        recorded = []
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake(recorded))
        r = post_chat(client, session_id="s-nosim", message="Hello",
                      headers={"X-Simulate-Failure": "*=429"})
        assert r.status_code == 200
        assert r.json()["metadata"]["key_id"] == "key_1"

    def test_sim_failed_request_not_stored(self, client, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion", make_acompletion_fake([]))
        post_chat(client, session_id="s-simnostore", message="Hello",
                  headers={"X-Simulate-Failure": "*=503"})
        assert client.get("/sessions/s-simnostore/messages").status_code == 404
