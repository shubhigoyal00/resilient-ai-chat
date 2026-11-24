# Resilient AI Chat

A production-ready AI chatbot: **React + Vite + TypeScript + Tailwind** frontend,
**FastAPI + LiteLLM + Google Gemini** backend, **SQLite (SQLAlchemy)** persistence,
and LiteLLM's **built-in in-memory cache**. The backend keeps a pool of Gemini API
keys and automatically fails over between them on `429` / quota-exhaustion / `5xx`.

## 1. Live URLs

- Frontend (Vercel): _pending deployment — see section 16 instructions below_
- Backend (Render): _pending deployment — see section 16 instructions below_

(The application is deploy-ready: `render.yaml` + persistent `/data` disk for the
backend, Vite build + `vercel.json` for the frontend.)

## 2. Run locally: with Docker and without

### With Docker (recommended)

```bash
cp .env.example .env       # fill in real Gemini keys
make up                    # = docker compose up --build -d
```

- Frontend → http://localhost:3000
- Backend → http://localhost:8000 (`GET /health`)
- SQLite file → named volume `sqlite_data` mounted at `/data`

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
$env:LLM_API_KEYS="key1,key2"; $env:DATABASE_URL="sqlite:///./app.db"; $env:ALLOWED_ORIGINS="http://localhost:3000"; $env:ENABLE_FAILURE_SIMULATION="true"
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
# .env or shell: VITE_API_BASE_URL=http://localhost:8000
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
- Only the key *identifier* (`key_1`, …) is recorded in metadata — never the
  secret. Errors are never fabricated into fake answers.
- `X-Simulate-Failure: key_1=429` / `key_1=500,key_2=503` / `*=429` lets you
  force failures per key for a single request (requires
  `ENABLE_FAILURE_SIMULATION=true`).

### Caching (`backend/app/services/cache_service.py`)

- Uses LiteLLM's built-in local cache (`litellm.cache = Cache(type="local")`) —
  no Redis, no hand-rolled cache.
- LiteLLM derives the cache key from the **entire completion payload**
  (model + full `messages`), so system prompt, history and the new message all
  contribute to cache identity. Verified against the installed version
  (litellm 1.74.9): `api_key` is *not* part of the key, and hit responses are
  marked `hidden_params["cache_hit"] = True`.
- On a hit the service returns `resolution_source=LLM_CACHE`,
  `key_id=null`, `fallback_attempts=0`, the identical reply text, and the
  *stored* token usage from the original response.

### SQLite session storage (`backend/app/`)

- Tables `sessions` and `messages(id, session_id, role, content, metadata,
  created_at)` are created at startup via SQLAlchemy `create_all`.
- The user + assistant pair is written **only after a successful inference**,
  so failed requests never appear in history. Assistant `metadata` is stored as
  JSON.
- Per-session history is fetched chronologically and prepended (system prompt +
  history + new message) to every LiteLLM call — the frontend only sends the
  latest message.
- `system_prompt` behaves as a per-session override: sent once, it's stored on
  the session row and reused until overridden again; it is never stored as a
  visible message.
- `GET /sessions/{id}/messages` → chronological array, `404 {"detail":
  "session not found"}` for unknown sessions.

## 4. Verification: how to see failover, cache hits and per-message token usage

### Failover (simulated)

```bash
# key_1 fails -> key_2 answers; metadata.fallback_attempts = 1, key_id = key_2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"demo","message":"Hello"}'

# all keys fail -> 503
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"demo","message":"Hello"}'
# -> {"detail":"all providers unavailable"}
```

### Cache hit

```bash
# Send the SAME first message from two different sessions.
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"session_id":"a","message":"What is caching?"}'   # LIVE_INFERENCE
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"session_id":"b","message":"What is caching?"}'   # LLM_CACHE, key_id=null
```

The second response reports `resolution_source: "LLM_CACHE"`, identical
`reply`, the original token counts, `key_id: null`, `fallback_attempts: 0`,
and lower `latency_ms`.

### Per-message token usage

Every `POST /chat` response contains `metadata.input_tokens` (the complete
prompt for *that* request — system + history + new message) and
`metadata.output_tokens` (this answer only). The frontend shows them in the
metadata panel under each assistant message. `GET
/sessions/{id}/messages` returns the stored per-message metadata too.

### Validation / errors

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"session_id":"s","message":""}'            # 422
curl http://localhost:8000/sessions/unknown/messages   # 404 {"detail":"session not found"}
```

## 5. Setup Used

- **Editor**: Windsurf
- **AI tooling**: Devin (SWE-2) — implementation, tests, and verification.

## 6. Bonus features

- Per-session `system_prompt` override persisted server-side (stored
  `sessions` table) — send it once, reuse it for the session.
- `render.yaml` blueprint + `vercel.json` for one-click-ish deploys.
- `Makefile` (`make up` / `make down` / `make test`).
- `GET /health` performs a real SQLite probe and reports the key-pool size.

---

## Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `LLM_API_KEYS` | Comma-separated Gemini keys → `key_1`, `key_2` | `k1,k2` |
| `GEMINI_MODEL` | LiteLLM model string | `gemini/gemini-2.5-flash` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:////data/app.db` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000` |
| `ENABLE_FAILURE_SIMULATION` | Enable `X-Simulate-Failure` header | `true` |
| `VITE_API_BASE_URL` | Backend URL baked into the frontend bundle | `http://localhost:8000` |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | `{"status":"ok","keys_configured":2,"cache_enabled":true}` |
| `POST` | `/chat` | `{session_id, message, system_prompt?}` → `{session_id, reply, metadata}` |
| `GET` | `/sessions/{id}/messages` | Chronological message array; `404` if unknown |

## Tests

```bash
cd backend
pytest -q        # 32 tests: validation, fallback, simulation, real LiteLLM cache
```

Cache tests patch only the provider dispatch *inside* LiteLLM
(`litellm.main.vertex_chat_completion.completion`), so the real
`LLMCachingHandler` marks `hidden_params["cache_hit"]` for genuine cache hits —
no timing guesses, no mocked cache flag.

## Deployment

### Backend → Render

1. New → Blueprint, point at this repo (or: New → Web Service → Docker,
   root dir `backend`).
2. `render.yaml` provisions a 1 GB persistent disk mounted at `/data` —
   `DATABASE_URL=sqlite:////data/app.db` survives restarts.
3. Set env vars: `LLM_API_KEYS`, `ALLOWED_ORIGINS=https://<your-vercel-app>`,
   `ENABLE_FAILURE_SIMULATION`, `GEMINI_MODEL`, `DATABASE_URL`.
4. Health check path `/health` is already configured.

### Frontend → Vercel

1. Import the repo, set **root directory** to `frontend` (framework: Vite).
2. Env var `VITE_API_BASE_URL=https://<your-render-backend>.onrender.com`.
3. Deploy; then update `ALLOWED_ORIGINS` on the backend to the Vercel URL.
