"""Tests run on SQLite by default. Set AEGIS_TEST_DATABASE_URL to a PostgreSQL URL with pgvector
(for example postgresql+psycopg://postgres@localhost:5433/aegis_test) to exercise the real vector store."""

import os

PG_URL = os.environ.get("AEGIS_TEST_DATABASE_URL")
os.environ["AEGIS_DATABASE_URL"] = PG_URL or "sqlite:///./test_aegis.db"
os.environ["AEGIS_EMBEDDING_PROVIDER"] = "hash"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _reset() -> None:
    if PG_URL:
        from sqlalchemy import create_engine, text

        with create_engine(PG_URL).begin() as c:
            c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    elif os.path.exists("test_aegis.db"):
        os.remove("test_aegis.db")


@pytest.fixture(scope="session")
def client():
    _reset()
    from app.main import app

    with TestClient(app) as c:
        yield c
    _reset()
