# Desk — Enterprise customer support MVP

Next.js UI + FastAPI backend. Signed-in users chat with an OpenAI assistant for **B2B-style enterprise support** (billing, access, escalations). AI output is **not** a contract, SLA, or legal commitment—use your official vendor channels when it matters.

**Stack:** Next.js · FastAPI · Clerk · OpenAI

## Setup

```bash
npm install && pip install -r requirements.txt
```

**`.env.local`** (Next): `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`

**`api/.env`** (or same keys in `.env.local`): `OPENAI_API_KEY`, `CLERK_JWKS_URL`

Optional: `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`). For local dev without billing: `NEXT_PUBLIC_CLERK_PLAN_REQUIRED=false` in `.env.local`.

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
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=... -e CLERK_JWKS_URL=... -e CLERK_SECRET_KEY=... enterprise-support-mvp
```

App + API on port **8000**.

## API

`POST /api/chat` — header `Authorization: Bearer <Clerk JWT>`, body `{ "messages": [{ "role": "user"|"assistant", "content": "..." }] }`. Response: SSE with `data: {"delta":"..."}` and `data: [DONE]`.

`GET /health` — health check.

`api/index.py` also maps `POST /api` to the same chat handler for some serverless routes.

## Disclaimer

AI-assisted guidance only. Not legal, financial, or contractual advice. For security incidents, billing disputes, and binding terms, use your official support and account channels.
