"""
Local RAG Engine — offline retrieval-augmented generation for child agents.

Loads encrypted knowledge packs, decrypts to local vector index,
and runs retrieval queries without network dependency.
"""

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_INDEX_DIR = Path.home() / ".matrix" / "rag_index"


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_id: str = ""
    retrieval_keywords: list[str] = field(default_factory=list)
    canonical_question: str = ""
    role_tags: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_id": self.source_id,
            "retrieval_keywords": self.retrieval_keywords,
            "canonical_question": self.canonical_question,
            "role_tags": self.role_tags,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        return cls(**data)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float


class LocalRAGEngine:
    def __init__(self, index_dir: Path = DEFAULT_INDEX_DIR):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: list[Chunk] = []

    def load_knowledge_pack(self, pack_data: list[dict], roles: list[str]):
        self.chunks = []
        for item in pack_data:
            chunk = Chunk.from_dict(item)
            chunk_tags = set(chunk.role_tags)
            if not chunk_tags or any(r in chunk_tags for r in roles):
                self.chunks.append(chunk)

    def search(self, query: str, top_k: int = 5, roles: list[str] | None = None) -> list[SearchResult]:
        query_lower = query.lower()
        results: list[SearchResult] = []

        for chunk in self.chunks:
            score = 0.0

            if chunk.canonical_question and query_lower in chunk.canonical_question.lower():
                score += 2.0

            for kw in chunk.retrieval_keywords:
                if kw.lower() in query_lower:
                    score += 1.5

            if query_lower in chunk.text.lower():
                score += 1.0

            if score > 0:
                results.append(SearchResult(chunk=chunk, score=score))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        for c in self.chunks:
            if c.chunk_id == chunk_id:
                return c
        return None

    def save_index(self, version: str):
        index_file = self.index_dir / f"index_{version}.json"
        index_file.write_text(json.dumps([c.to_dict() for c in self.chunks], ensure_ascii=False))

    def load_index(self, version: str) -> bool:
        index_file = self.index_dir / f"index_{version}.json"
        if not index_file.exists():
            return False
        data = json.loads(index_file.read_text())
        self.chunks = [Chunk.from_dict(d) for d in data]
        return True

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
