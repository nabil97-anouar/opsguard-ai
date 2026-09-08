from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from app.db import session as db_session


def get_registered_table_names() -> list[str]:
    import app.models  # noqa: F401

    return sorted(SQLModel.metadata.tables.keys())


def create_db_and_tables(active_engine: Engine | None = None) -> list[str]:
    import app.models  # noqa: F401

    target_engine = active_engine or db_session.engine
    SQLModel.metadata.create_all(target_engine)
    from app.db.compatibility import upgrade_evaluation_integrity

    upgrade_evaluation_integrity(target_engine)
    return get_registered_table_names()


if __name__ == "__main__":
    print(create_db_and_tables())
