"""Per-user Chroma vector stores for uploaded knowledge bases."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def _user_collection_slug(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:40]
    return f"desk_kb_{digest}"


def chroma_persist_dir() -> Path:
    raw = (os.getenv("CHROMA_PERSIST_DIR") or "").strip()
    base = Path(raw) if raw else Path(__file__).resolve().parent.parent / "data" / "chroma"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _read_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def _read_textual(data: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _read_pdf(data)
    return data.decode("utf-8", errors="replace")


class KnowledgeStore:
    def __init__(self) -> None:
        self._persist = chroma_persist_dir()
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self._embeddings = OpenAIEmbeddings(model=model)
        self._splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def _vectorstore(self, user_id: str) -> Chroma:
        return Chroma(
            collection_name=_user_collection_slug(user_id),
            persist_directory=str(self._persist),
            embedding_function=self._embeddings,
        )

    def chunk_count(self, user_id: str) -> int:
        vs = self._vectorstore(user_id)
        return int(vs._collection.count())

    def ingest_bytes(self, user_id: str, data: bytes, source_name: str) -> int:
        text = _read_textual(data, source_name).strip()
        if not text:
            return 0
        chunks = self._splitter.split_text(text)
        if not chunks:
            return 0
        docs = [Document(page_content=c, metadata={"source": source_name}) for c in chunks]
        vs = self._vectorstore(user_id)
        vs.add_documents(docs)
        return len(docs)

    def similarity_search(self, user_id: str, query: str, k: int = 6) -> list[Document]:
        if self.chunk_count(user_id) == 0:
            return []
        vs = self._vectorstore(user_id)
        return vs.similarity_search(query, k=k)

    def list_sources(self, user_id: str) -> list[dict]:
        vs = self._vectorstore(user_id)
        if self.chunk_count(user_id) == 0:
            return []
        raw = vs._collection.get(include=["metadatas"])
        metas = raw.get("metadatas") or []
        counts: dict[str, int] = {}
        for m in metas:
            if not m:
                continue
            src = m.get("source") or "unknown"
            counts[src] = counts.get(src, 0) + 1
        return [{"source": k, "chunks": v} for k, v in sorted(counts.items())]

    def delete_source(self, user_id: str, source_name: str) -> None:
        vs = self._vectorstore(user_id)
        vs._collection.delete(where={"source": source_name})


_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store
