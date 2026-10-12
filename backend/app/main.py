"""Aegis API: data and AI governance for fintechs."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import current_user
from .config import get_settings
from .db import Base, SessionLocal, advisory_lock, engine
from .governance import reindex
from .payments import seed_payments
from .routers import access, ai, catalog, lineage, overview, payments, quality, recert, search
from .seed import seed
from .vectorstore import get_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Alembic migrations own the schema in AWS; create_all keeps local and test runs zero-setup.
    Base.metadata.create_all(engine)
    get_store().init()
    s = get_settings()
    with SessionLocal() as db, advisory_lock(db, STARTUP_LOCK):
        # Several tasks and workers start together; the lock lets exactly one seed and index.
        seeded = s.seed_demo_data and seed(db, s.demo_reviewer_email)
        rails_added = s.seed_demo_data and seed_payments(db)
        if seeded or rails_added or get_store().count(db) == 0:
            reindex(db)
        db.commit()
    yield


STARTUP_LOCK = 7300
settings = get_settings()
app = FastAPI(title="Aegis Governance API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

for r in (overview, lineage, quality, catalog, access, recert, ai, payments, search):
    # Every /api route requires a signed-in user; only /health is open (for the load balancer).
    app.include_router(r.router, dependencies=[Depends(current_user)])


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}
