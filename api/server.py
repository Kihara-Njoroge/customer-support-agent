import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parent
load_dotenv(_API_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / ".env.local", override=True)

from fastapi import Depends, FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_clerk_auth import (  # type: ignore
    ClerkConfig,
    ClerkHTTPBearer,
    HTTPAuthorizationCredentials,
)
from openai import OpenAI  # type: ignore
from pydantic import BaseModel, field_validator  # type: ignore

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_clerk_jwks = (os.getenv("CLERK_JWKS_URL") or "").strip()
if not _clerk_jwks:
    raise RuntimeError(
        "CLERK_JWKS_URL is not set. Add it to api/.env or the project root .env.local "
        "(e.g. https://YOUR_INSTANCE.clerk.accounts.dev/.well-known/jwks.json), then restart the server."
    )
clerk_config = ClerkConfig(jwks_url=_clerk_jwks)
clerk_guard = ClerkHTTPBearer(clerk_config)

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

CHAT_SYSTEM_PROMPT = """
You are an enterprise customer support AI assistant for a B2B software or services vendor. You help
customers—often IT, security, finance, procurement, and operations—with account questions such as
billing and invoices, plans and usage limits, SSO/SCIM and access, API keys and rate limits,
onboarding, feature availability, documentation pointers, and how to escalate to support or a
customer success manager.

Tone: professional, concise, calm, and respectful of urgency (renewals, outages, compliance
deadlines). Use clear language. You do not have access to private contracts, ticket queues, or
internal systems: never invent specific SLA percentages, pricing, legal terms, case numbers, or
commitments. When an answer depends on account data or a signed agreement, say what is typically
needed and direct them to their account team, official support portal, or legal/finance contacts.

If the user describes an active security incident, suspected breach, or data exposure, advise them
to use the vendor's security or abuse channel and their own incident response process immediately;
keep guidance high-level and brief.

If a question is outside B2B customer support (e.g. personal medical or unrelated consumer topics),
politely note your scope and suggest appropriate resources.

Remind users occasionally (not every message) that replies are AI-assisted and may not reflect the
latest policy; authoritative answers come from their contract and vendor communications.

Keep replies concise unless the user asks for detail. Short Markdown (lists, **bold**) is fine when
it helps readability.
""".strip()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("message content cannot be empty")
        if len(text) > 12000:
            raise ValueError("message too long")
        return text


class ChatRequest(BaseModel):
    messages: list[ChatMessage]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if not value:
            raise ValueError("messages cannot be empty")
        if len(value) > 40:
            raise ValueError("too many messages in one request")
        return value


@app.post("/api/chat")
def chat_stream(
    request: ChatRequest,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    _uid = creds.decoded["sub"]

    client = OpenAI()
    openai_messages: list[dict] = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for m in request.messages:
        openai_messages.append({"role": m.role, "content": m.content})

    def event_stream():
        stream = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=openai_messages,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield f"data: {json.dumps({'delta': delta.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


static_path = Path("static")
if static_path.exists():

    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")

    app.mount("/", StaticFiles(directory="static", html=True), name="static")
