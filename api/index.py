"""Slim FastAPI entry (e.g. serverless) with the same API routes as api.server minus static hosting."""

from pathlib import Path

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parent
load_dotenv(_API_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / ".env.local", override=True)

from fastapi import FastAPI  # noqa: E402

from .routers import api_router  # noqa: E402

app = FastAPI()
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
