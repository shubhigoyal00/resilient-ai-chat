# Resilient AI Chat

A production-ready AI chatbot: **React + Vite + TypeScript + Tailwind** frontend,
**FastAPI + LiteLLM + Google Gemini** backend, **SQLite (SQLAlchemy)** persistence,
and LiteLLM's **built-in in-memory cache**. The backend keeps a pool of Gemini API
keys and automatically fails over between them on `429` / quota-exhaustion / `5xx`.

## 1. Live URLs

The frontend and backend are deployed and connected — the Vercel frontend calls
the Render backend over the public API:

- **Frontend (Vercel):** https://resilient-ai-chat-frontend.vercel.app/
- **Backend (Render):** https://resilient-ai-chat-api.onrender.com/
- **Backend health check:** https://resilient-ai-chat-api.onrender.com/health
- **GitHub repository:** https://github.com/shubhigoyal00/resilient-ai-chat

```bash
curl https://resilient-ai-chat-api.onrender.com/health
# -> {"status":"ok","keys_configured":2,"cache_enabled":true}
```

## 2. Run locally: with Docker and without

### With Docker

```bash
cp .env.example .env       # fill in real Gemini keys
make up                    # = docker compose up --build -d
```

- Frontend → http://localhost:3000
- Backend → http://localhost:8000 (`GET /health`)
- SQLite file → named Docker volume `sqlite_data` mounted at `/data`

```bash
make down                  # = docker compose down
```

### Without Docker

Backend:

```bash
cd backend
python -m venv .venv && .\.venv\Scripts\activate   # or source .venv/bin/activate
pip install -r requirements.txt
# env vars (PowerShell):
$env:LLM_API_KEYS="key1,key2"; $env:DATABASE_URL="sqlite:///./app.db"
$env:ALLOWED_ORIGINS="http://localhost:3000"; $env:ENABLE_FAILURE_SIMULATION="true"
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
# .env.local or shell: VITE_API_BASE_URL=http://localhost:8000
npm run dev        # serves on http://localhost:3000
```

## 3. Design decisions: key fallback, caching, SQLite session storage

### Key fallback (`backend/app/services/llm_service.py`)

- `LLM_API_KEYS=k1,k2` is parsed into an ordered pool `key_1`, `key_2`.
- Every request iterates the pool in order, calling `litellm.acompletion(
  model=<GEMINI_MODEL>, messages=..., api_key=<secret>)`.
- Any provider exception — `429` (rate limit / quota) or `5xx` — counts as a
  failed attempt and moves to the next key. `fallback_attempts` = number of keys
  that failed before the successful one. If every key fails → `503
  {"detail": "all providers unavailable"}`.
- Only the key *identifier* (`key_1`, …) is recorded in metadata and logs —
  never the secret. Per-key provider errors are logged as
  `[LiteLLM ERROR] key_N: <ErrorType>: <message>` to aid debugging.
- `X-Simulate-Failure: key_1=429` / `key_1=500,key_2=503` / `*=429` forces
  per-key failures for a single request (requires
  `ENABLE_FAILURE_SIMULATION=true`).

### Caching (`backend/app/services/cache_service.py`)

- LiteLLM's built-in local cache (`litellm.cache = Cache(type="local")`) — no
  Redis, no hand-rolled cache.
- LiteLLM derives the cache key from the **entire completion payload**
  (model + full `messages`), so the system prompt, history and the new message
  all contribute to cache identity. `api_key` is *not* part of the key, and hit
  responses are marked `hidden_params["cache_hit"] = True` (verified against
  the installed version, litellm 1.74.9).
- On a hit the service returns `resolution_source=LLM_CACHE`, `key_id=null`,
  `fallback_attempts=0`, the identical reply text, and the *stored* token usage
  from the original response.

### SQLite session storage (`backend/app/`)

- Tables `sessions` and `messages(id, session_id, role, content, metadata,
  created_at)` are created at startup via SQLAlchemy `create_all`.
- The user + assistant pair is written **only after a successful inference**,
  so failed requests never appear in history. Assistant `metadata` is stored
  as JSON.
- Per-session history is fetched chronologically and prepended (system prompt
  + history + new message) to every LiteLLM call — the frontend only sends the
  latest message.
- `system_prompt` is a per-session override: sent once, it is stored on the
  session row and reused until overridden; it never becomes a visible message.
- `GET /sessions/{id}/messages` → chronological array;
  `404 {"detail": "session not found"}` for unknown sessions.

### Where the SQLite file lives

- **Local / Docker Compose:** `DATABASE_URL=sqlite:////data/app.db` with the
  named volume `sqlite_data` mounted at `/data` — data survives container
  restarts (`make down` / `make up`).
- **Render deployment:** the backend runs on a **free instance whose
  filesystem is ephemeral**. `DATABASE_URL=sqlite:///./app.db` writes into the
  service's working directory, so conversation history **may be lost on
  restart, redeploy, or spin-down**. No persistent disk is provisioned on the
  free plan. (A paid Render disk mounted at `/data` +
  `DATABASE_URL=sqlite:////data/app.db` would make it durable; the app needs
  no code change — only env/disk config.)

## 4. Verification: how to see failover, cache hits and per-message token usage

All commands work against the deployed backend
(`https://resilient-ai-chat-api.onrender.com`) or `http://localhost:8000`.

### Failover (simulated)

```bash
# key_1 fails -> key_2 answers; metadata.fallback_attempts=1, key_id="key_2"
curl -X POST https://resilient-ai-chat-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"demo","message":"Hello"}'

# all keys fail -> 503
curl -X POST https://resilient-ai-chat-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"demo","message":"Hello"}'
# -> {"detail":"all providers unavailable"}
```

### Cache hit

```bash
# Send the SAME first message from two different sessions.
curl -X POST https://resilient-ai-chat-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"a","message":"What is caching?"}'   # LIVE_INFERENCE
curl -X POST https://resilient-ai-chat-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"b","message":"What is caching?"}'   # LLM_CACHE, key_id=null
```

The second response reports `resolution_source: "LLM_CACHE"`, identical
`reply`, the original token counts, `key_id: null`, `fallback_attempts: 0`,
and dramatically lower `latency_ms` (single-digit ms vs ~1 s live).

### Per-message token usage

Every `POST /chat` response contains `metadata.input_tokens` (the complete
prompt for *that* request — system + history + new message) and
`metadata.output_tokens` (this answer only). The frontend shows them, plus
`key_id` and `fallback_attempts`, in the metadata panel under each assistant
message. `GET /sessions/{id}/messages` returns stored per-message metadata.

### Validation / errors

```bash
curl -X POST https://resilient-ai-chat-api.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s","message":""}'                        # 422
curl https://resilient-ai-chat-api.onrender.com/sessions/unknown/messages
# -> 404 {"detail":"session not found"}
```

## 5. Setup Used

- **Editor:** Windsurf
- **AI tooling:** Devin (SWE-2) — implementation, tests, and verification.

## 6. Bonus features

- Per-session `system_prompt` override persisted server-side.
- Premium dark SaaS-style UI: sidebar with per-page-load conversation history,
  markdown-rendered replies, suggested prompts, error retry, mobile overlay
  sidebar.
- `render.yaml` blueprint matching the deployed Python web service;
  `vercel.json` for the Vite frontend.
- `Makefile` (`make up` / `make down` / `make test` / `make build`).
- `GET /health` performs a real SQLite probe and reports the key-pool size.

---

## Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `LLM_API_KEYS` | Comma-separated Gemini keys → `key_1`, `key_2` | `k1,k2` |
| `GEMINI_MODEL` | LiteLLM model string | `gemini/gemini-3.5-flash-lite` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:////data/app.db` (volume) / `sqlite:///./app.db` (ephemeral) |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `https://resilient-ai-chat-frontend.vercel.app` |
| `ENABLE_FAILURE_SIMULATION` | Enable `X-Simulate-Failure` header | `true` |
| `VITE_API_BASE_URL` | Backend URL baked into the frontend bundle | `https://resilient-ai-chat-api.onrender.com` |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | `{"status":"ok","keys_configured":2,"cache_enabled":true}` |
| `POST` | `/chat` | `{session_id, message, system_prompt?}` → `{session_id, reply, metadata}` |
| `GET` | `/sessions/{id}/messages` | Chronological message array; `404` if unknown |

API docs routes (`/docs`, `/openapi.json`) are intentionally disabled to keep
the public surface to exactly these endpoints.

## Tests

```bash
cd backend
pytest -q        # 32 tests: validation, fallback, simulation, real LiteLLM cache
```

Cache tests patch only the provider dispatch *inside* LiteLLM
(`litellm.main.vertex_chat_completion.completion`), so the real
`LLMCachingHandler` marks `hidden_params["cache_hit"]` for genuine cache
hits — no timing guesses, no mocked cache flag.

## Deployment

### Backend → Render (deployed)

Deployed as a **Python 3 Web Service** on the free plan:

| Setting | Value |
|---|---|
| Service name | `resilient-ai-chat-api` |
| Repository / branch | `shubhigoyal00/resilient-ai-chat` · `main` |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Instance | Free (ephemeral filesystem) |

Environment variables set on Render: `LLM_API_KEYS`, `GEMINI_MODEL`,
`DATABASE_URL=sqlite:///./app.db`, `ALLOWED_ORIGINS` (the Vercel URL),
`ENABLE_FAILURE_SIMULATION`. `render.yaml` encodes the same configuration
for Blueprint deploys.

### Frontend → Vercel (deployed)

- Project root: `frontend` (framework preset: Vite).
- Env var: `VITE_API_BASE_URL=https://resilient-ai-chat-api.onrender.com`.
- `ALLOWED_ORIGINS` on the backend is set to
  `https://resilient-ai-chat-frontend.vercel.app`.
