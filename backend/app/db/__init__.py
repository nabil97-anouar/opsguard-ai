"""Database utilities for SQLModel sessions and initialization."""

from app.db.session import build_engine, check_database_connection, engine, get_session


def create_db_and_tables():
    from app.db.init_db import create_db_and_tables as _create_db_and_tables

    return _create_db_and_tables()


def get_registered_table_names():
    from app.db.init_db import get_registered_table_names as _get_registered_table_names

    return _get_registered_table_names()


__all__ = [
    "build_engine",
    "check_database_connection",
    "create_db_and_tables",
    "engine",
    "get_registered_table_names",
    "get_session",
]
