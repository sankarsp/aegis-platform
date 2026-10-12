"""Semantic search over governance knowledge, backed by the vector store, and an optional drafted answer."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import User, require
from ..config import get_settings
from ..db import get_db
from ..governance import reindex
from ..vectorstore import get_store

router = APIRouter(prefix="/api", tags=["search"])

KINDS = ["dataset", "cde", "term", "policy", "model", "report", "rail"]


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


def _hits(db: Session, q: str, k: int, kinds: list[str] | None):
    return [
        {"kind": h.kind, "refId": h.ref_id, "title": h.title, "body": h.body, "score": round(h.score, 3)}
        for h in get_store().search(db, q, k=k, kinds=kinds or KINDS)
    ]


@router.get("/search")
def search(
    q: str = Query(min_length=2),
    k: int = Query(8, ge=1, le=25),
    kind: list[str] | None = Query(None),
    db: Session = Depends(get_db),
):
    return {"query": q, "results": _hits(db, q, k, kind)}


@router.post("/ask")
def ask(body: AskIn, db: Session = Depends(get_db)):
    """Retrieves the most relevant governance records. If a Bedrock chat model is configured,
    it also drafts a short answer that cites only those records."""
    hits = _hits(db, body.question, 6, None)
    s = get_settings()
    answer = None
    if s.bedrock_chat_model_id and hits:
        import boto3

        context = "\n".join(f"[{i + 1}] {h['kind']} {h['title']}: {h['body']}" for i, h in enumerate(hits))
        client = boto3.client("bedrock-runtime", region_name=s.aws_region)
        resp = client.converse(
            modelId=s.bedrock_chat_model_id,
            system=[
                {
                    "text": "You answer questions about a fintech's data and AI governance records. Use only the "
                    "numbered records provided, cite them like [2], and say so if they do not answer the question."
                }
            ],
            messages=[{"role": "user", "content": [{"text": f"Records:\n{context}\n\nQuestion: {body.question}"}]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0},
        )
        answer = resp["output"]["message"]["content"][0]["text"]
    return {"question": body.question, "answer": answer, "sources": hits}


@router.post("/admin/reindex")
def admin_reindex(db: Session = Depends(get_db), _: User = Depends(require("admin"))):
    return {"indexed": reindex(db)}


@router.get("/admin/vector-config")
def vector_config():
    s = get_settings()
    return {"provider": s.embedding_provider, "dimensions": s.embedding_dim, "store": type(get_store()).__name__}
