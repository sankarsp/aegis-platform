import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
engine = create_engine(_settings.database_url, connect_args=_connect_args, pool_pre_ping=True, pool_recycle=900)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class _RdsSecret:
    """Reads the RDS-managed secret, cached for five minutes, so rotated passwords are picked up without a restart."""

    def __init__(self, arn: str, region: str):
        self._arn, self._region = arn, region
        self._value: dict | None = None
        self._at = 0.0
        self._lock = threading.Lock()

    def get(self) -> dict:
        with self._lock:
            if self._value is None or time.monotonic() - self._at > 300:
                import boto3

                raw = boto3.client("secretsmanager", region_name=self._region).get_secret_value(SecretId=self._arn)
                self._value, self._at = json.loads(raw["SecretString"]), time.monotonic()
            return self._value

    def expire(self) -> None:
        with self._lock:
            self._value = None


if _settings.db_secret_arn:
    _secret = _RdsSecret(_settings.db_secret_arn, _settings.aws_region)

    @event.listens_for(engine, "do_connect")
    def _inject_credentials(dialect, conn_rec, cargs, cparams):
        creds = _secret.get()
        cparams["user"], cparams["password"] = creds["username"], creds["password"]
        try:
            return dialect.connect(*cargs, **cparams)
        except Exception:
            _secret.expire()  # the password may have just rotated; the next attempt re-reads it
            raise


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


@contextmanager
def advisory_lock(db: Session, key: int):
    """Serialises work across API tasks and workers on PostgreSQL (released at commit). No-op on SQLite."""
    if is_postgres():
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
    yield


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
