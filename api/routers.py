"""HTTP routes: chat (LangGraph + streaming), knowledge base upload/list/delete."""

from __future__ import annotations

import json
import urllib.parse
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi_clerk_auth import HTTPAuthorizationCredentials
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, field_validator

from .clerk_auth import clerk_guard
from .knowledge_store import get_knowledge_store
from .workflow_graph import CHAT_MODEL, run_orchestration

api_router = APIRouter()

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".txt", ".md", ".pdf"})


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


def _user_id(creds: HTTPAuthorizationCredentials) -> str:
    return str(creds.decoded["sub"])


@api_router.post("/api/chat")
def chat_stream(
    request: ChatRequest,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    uid = _user_id(creds)
    payload = [m.model_dump() for m in request.messages]

    def event_stream():
        try:
            lc_messages = run_orchestration(uid, payload)
        except Exception as exc:
            yield f"data: {json.dumps({'delta': '', 'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"
            return
        llm = ChatOpenAI(model=CHAT_MODEL, streaming=True)
        for chunk in llm.stream(lc_messages):
            piece = chunk.content
            if piece:
                yield f"data: {json.dumps({'delta': piece})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@api_router.get("/api/knowledge/sources")
def knowledge_sources(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)):
    uid = _user_id(creds)
    return {"sources": get_knowledge_store().list_sources(uid)}


@api_router.post("/api/knowledge/upload")
async def knowledge_upload(
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    file: UploadFile = File(...),
):
    uid = _user_id(creds)
    name = file.filename or "upload"
    suffix = ""
    if "." in name:
        suffix = "." + name.rsplit(".", 1)[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"Unsupported file type {suffix or '(none)'}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    if not data.strip():
        raise HTTPException(400, detail="Empty file")
    safe_name = name.replace("\\", "/").split("/")[-1][:240]
    n = get_knowledge_store().ingest_bytes(uid, data, safe_name)
    if n == 0:
        raise HTTPException(400, detail="No text could be indexed from this file")
    return {"ok": True, "source": safe_name, "chunks_ingested": n}


@api_router.delete("/api/knowledge/source")
def knowledge_delete_source(
    source: str,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    if not source.strip():
        raise HTTPException(400, detail="Missing source")
    uid = _user_id(creds)
    decoded = urllib.parse.unquote(source)
    get_knowledge_store().delete_source(uid, decoded)
    return {"ok": True, "source": decoded}


@api_router.post("/api")
def chat_stream_alias(
    request: ChatRequest,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    return chat_stream(request, creds)
