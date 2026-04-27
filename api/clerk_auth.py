"""Clerk JWT verification for protected API routes."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parent
load_dotenv(_API_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / ".env.local", override=True)

_clerk_jwks = (os.getenv("CLERK_JWKS_URL") or "").strip()
if not _clerk_jwks:
    raise RuntimeError(
        "CLERK_JWKS_URL is not set. Add it to api/.env or the project root .env.local "
        "(e.g. https://YOUR_INSTANCE.clerk.accounts.dev/.well-known/jwks.json), then restart the server."
    )

clerk_config = ClerkConfig(jwks_url=_clerk_jwks)
clerk_guard = ClerkHTTPBearer(clerk_config)
