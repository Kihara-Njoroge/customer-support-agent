# Desk — Enterprise customer support MVP

Next.js UI + FastAPI backend. Signed-in users chat with an OpenAI assistant for **B2B-style enterprise support** (billing, access, escalations). AI output is **not** a contract, SLA, or legal commitment—use your official vendor channels when it matters.

**Stack:** Next.js · FastAPI · Clerk · OpenAI · LangGraph · LangChain · Chroma (per-user vector KB)

## Setup

```bash
npm install && pip install -r requirements.txt
```

If you use a virtualenv, install Python deps **into that same env** (the one you use to run `uvicorn`), e.g. `./venv/bin/pip install -r requirements.txt`. Otherwise you may see `ModuleNotFoundError: No module named 'langchain_openai'`.

**`.env.local`** (Next): `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`

**`api/.env`** (or same keys in `.env.local`): `OPENAI_API_KEY`, `CLERK_JWKS_URL`

Optional: `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`), `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`), `CHROMA_PERSIST_DIR` (default `./data/chroma` under the repo). For local dev without billing: `NEXT_PUBLIC_CLERK_PLAN_REQUIRED=false` in `.env.local`.

## Run locally

Terminal 1 — API:

```bash
uvicorn api.server:app --reload --port 8000
```

Terminal 2 — UI (`next.config` proxies `/api` to `:8000`):

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Chat is at `/product`.

## Docker

```bash
docker build --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<pk> -t enterprise-support-mvp .
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=... -e CLERK_JWKS_URL=... -e CLERK_SECRET_KEY=... -v desk-chroma:/app/data/chroma enterprise-support-mvp
```

App + API on port **8000**.

## API

`POST /api/chat` — header `Authorization: Bearer <Clerk JWT>`, body `{ "messages": [{ "role": "user"|"assistant", "content": "..." }] }`. Response: SSE with `data: {"delta":"..."}` and `data: [DONE]`. Each turn runs a **LangGraph** pipeline: **supervisor** (route: general / kb / hybrid) → **retrieve** (Chroma similarity on the signed-in user’s uploads) → **KB analyst** (condenses excerpts) → **prepare** (system prompt + notes), then the final reply is **streamed** from the support model.

**Knowledge base (same auth):**

- `GET /api/knowledge/sources` — `{ "sources": [{ "source": "filename", "chunks": N }] }`
- `POST /api/knowledge/upload` — `multipart/form-data` field `file` (`.txt`, `.md`, `.pdf`, max ~12 MB)
- `DELETE /api/knowledge/source?source=<url-encoded filename>` — remove one uploaded document’s chunks

`GET /health` — health check.

`api/index.py` also exposes `POST /api` as an alias for the chat stream.

## Disclaimer

AI-assisted guidance only. Not legal, financial, or contractual advice. For security incidents, billing disputes, and binding terms, use your official support and account channels.
