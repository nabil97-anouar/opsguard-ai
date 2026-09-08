from __future__ import annotations

from collections.abc import Generator
from time import perf_counter

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.core.config import get_settings


def build_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    resolved_url = database_url or settings.database_url
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}

    if resolved_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if resolved_url in {"sqlite://", "sqlite:///:memory:"} or ":memory:" in resolved_url:
            engine_kwargs["poolclass"] = StaticPool
    elif resolved_url.startswith("postgresql"):
        engine_kwargs["connect_args"] = {"connect_timeout": 3}

    result = create_engine(resolved_url, **engine_kwargs)
    if resolved_url.startswith("sqlite"):
        @event.listens_for(result, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return result


engine = build_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def check_database_connection(active_engine: Engine | None = None) -> float:
    target_engine = active_engine or engine
    started_at = perf_counter()

    with target_engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return round((perf_counter() - started_at) * 1000, 2)
