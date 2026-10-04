"""Vector store for governance knowledge: datasets, CDEs, glossary terms, policies, model cards and labelled columns.

On PostgreSQL (Aurora in AWS) vectors live in a pgvector table with an HNSW index.
On SQLite (tests, quick local runs) an in-memory store with the same interface is used.
"""

import json
import math
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import engine, is_postgres
from .embeddings import get_embedder


@dataclass
class Hit:
    kind: str
    ref_id: str
    title: str
    body: str
    score: float
    meta: dict


class PgVectorStore:
    def __init__(self, dim: int):
        self.dim = dim

    def init(self) -> None:
        with engine.begin() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            c.execute(
                text(f"""
                CREATE TABLE IF NOT EXISTS knowledge_vectors (
                    kind TEXT NOT NULL, ref_id TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
                    meta JSONB NOT NULL DEFAULT '{{}}', embedding vector({self.dim}) NOT NULL,
                    PRIMARY KEY (kind, ref_id))""")
            )
            c.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS knowledge_vectors_hnsw ON knowledge_vectors "
                    "USING hnsw (embedding vector_cosine_ops)"
                )
            )

    def upsert(self, db: Session, kind: str, ref_id: str, title: str, body: str, meta: dict | None = None) -> None:
        vec = get_embedder().embed(f"{title}\n{body}")
        db.execute(
            text("""
            INSERT INTO knowledge_vectors (kind, ref_id, title, body, meta, embedding)
            VALUES (:kind, :ref_id, :title, :body, CAST(:meta AS JSONB), CAST(:emb AS vector))
            ON CONFLICT (kind, ref_id) DO UPDATE
              SET title = EXCLUDED.title, body = EXCLUDED.body, meta = EXCLUDED.meta, embedding = EXCLUDED.embedding"""),
            {
                "kind": kind,
                "ref_id": ref_id,
                "title": title,
                "body": body,
                "meta": json.dumps(meta or {}),
                "emb": "[" + ",".join(f"{x:.6f}" for x in vec) + "]",
            },
        )

    def search(self, db: Session, query: str, k: int = 8, kinds: list[str] | None = None) -> list[Hit]:
        vec = "[" + ",".join(f"{x:.6f}" for x in get_embedder().embed(query)) + "]"
        where = "WHERE kind = ANY(:kinds)" if kinds else ""
        rows = db.execute(
            text(f"""
            SELECT kind, ref_id, title, body, meta, 1 - (embedding <=> CAST(:q AS vector)) AS score
            FROM knowledge_vectors {where} ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"""),
            {"q": vec, "k": k, "kinds": kinds},
        ).all()
        return [Hit(r.kind, r.ref_id, r.title, r.body, float(r.score), r.meta or {}) for r in rows]

    def count(self, db: Session) -> int:
        return db.execute(text("SELECT count(*) FROM knowledge_vectors")).scalar_one()


class MemoryVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self._rows: dict[tuple[str, str], tuple[str, str, dict, list[float]]] = {}

    def init(self) -> None:
        pass

    def upsert(self, db: Session, kind: str, ref_id: str, title: str, body: str, meta: dict | None = None) -> None:
        self._rows[(kind, ref_id)] = (title, body, meta or {}, get_embedder().embed(f"{title}\n{body}"))

    def search(self, db: Session, query: str, k: int = 8, kinds: list[str] | None = None) -> list[Hit]:
        q = get_embedder().embed(query)
        scored = []
        for (kind, ref_id), (title, body, meta, v) in self._rows.items():
            if kinds and kind not in kinds:
                continue
            dot = sum(a * b for a, b in zip(q, v, strict=True))
            norm = math.sqrt(sum(a * a for a in q)) * math.sqrt(sum(b * b for b in v)) or 1.0
            scored.append(Hit(kind, ref_id, title, body, dot / norm, meta))
        return sorted(scored, key=lambda h: h.score, reverse=True)[:k]

    def count(self, db: Session) -> int:
        return len(self._rows)


_store = None


def get_store():
    global _store
    if _store is None:
        dim = get_embedder().dim
        _store = PgVectorStore(dim) if is_postgres() else MemoryVectorStore(dim)
    return _store
