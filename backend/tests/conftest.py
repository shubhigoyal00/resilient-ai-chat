"""Test fixtures.

Environment variables are set BEFORE importing the application so the
Settings/engine bind to the test configuration.
"""

import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "resilient_chat_test.db")

os.environ.setdefault("LLM_API_KEYS", "test-secret-1,test-secret-2")
os.environ.setdefault("GEMINI_MODEL", "gemini/gemini-3.5-flash-lite")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB}")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("ENABLE_FAILURE_SIMULATION", "true")

import litellm  # noqa: E402
import litellm.main  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from litellm.caching import Cache  # noqa: E402
from litellm.types.utils import Choices, Message, ModelResponse, Usage  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import engine, init_db  # noqa: E402
from app.models import Attachment as AttachmentRow  # noqa: E402
from app.models import Message as MessageRow  # noqa: E402
from app.models import Session as SessionRow  # noqa: E402


def make_model_response(text: str, prompt_tokens: int = 10, output_tokens: int = 5) -> ModelResponse:
    r = ModelResponse(model="gemini/gemini-3.5-flash-lite")
    r.choices = [Choices(index=0, message=Message(role="assistant", content=text))]
    r.usage = Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
    )
    return r


@pytest.fixture(scope="session")
def client() -> TestClient:
    init_db()
    litellm.cache = Cache(type="local")
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state():
    """Isolate tests: wipe tables, reset the LiteLLM in-memory cache,
    and restore default settings."""
    settings = get_settings()
    settings.enable_failure_simulation = True
    settings.llm_api_keys = "test-secret-1,test-secret-2"
    with engine.begin() as conn:
        conn.execute(MessageRow.__table__.delete())
        conn.execute(AttachmentRow.__table__.delete())
        conn.execute(SessionRow.__table__.delete())
    litellm.cache = Cache(type="local")
    yield
    with engine.begin() as conn:
        conn.execute(MessageRow.__table__.delete())
        conn.execute(AttachmentRow.__table__.delete())
        conn.execute(SessionRow.__table__.delete())


def post_chat(client: TestClient, session_id: str = "s-1", message: str = "Hello",
              system_prompt: str | None = None, headers: dict | None = None,
              attachment_ids: list | None = None):
    body = {"session_id": session_id, "message": message}
    if system_prompt is not None:
        body["system_prompt"] = system_prompt
    if attachment_ids is not None:
        body["attachment_ids"] = attachment_ids
    return client.post("/chat", json=body, headers=headers or {})


def upload(client: TestClient, session_id: str, filename: str, data: bytes,
           content_type: str = "application/octet-stream"):
    return client.post(
        "/attachments",
        files={"file": (filename, data, content_type)},
        data={"session_id": session_id},
    )


@pytest.fixture
def provider_spy(monkeypatch):
    """Patch the Gemini provider dispatch inside LiteLLM; count real calls."""
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)

        async def _coro():
            return make_model_response("CACHED REPLY", prompt_tokens=42, output_tokens=9)

        return _coro() if kwargs.get("acompletion") else _sync()

    def _sync():
        return make_model_response("CACHED REPLY", prompt_tokens=42, output_tokens=9)

    monkeypatch.setattr(
        litellm.main.vertex_chat_completion, "completion", fake_completion
    )
    return calls
