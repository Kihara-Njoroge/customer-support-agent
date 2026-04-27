import os
from pathlib import Path

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _API_DIR.parent
load_dotenv(_API_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / ".env.local", override=True)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from .routers import api_router  # noqa: E402

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


static_path = Path("static")
if static_path.exists():

    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")

    app.mount("/", StaticFiles(directory="static", html=True), name="static")
