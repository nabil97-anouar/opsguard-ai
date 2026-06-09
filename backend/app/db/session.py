from __future__ import annotations

from collections.abc import Generator
from time import perf_counter

from sqlalchemy import text
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

    return create_engine(resolved_url, **engine_kwargs)


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
