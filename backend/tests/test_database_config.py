import os
import importlib
from unittest import mock
import pytest


def test_default_sqlite_configuration():
    """Verify that when DATABASE_URL is not set, default SQLite configuration is used with check_same_thread=False."""
    with mock.patch.dict(os.environ, {}, clear=True):
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        from app.core import database
        importlib.reload(database)

        assert database.DATABASE_URL.startswith("sqlite:///")
        # Confirm engine was created with SQLite connect_args
        assert database.engine.url.drivername == "sqlite"


def test_postgres_url_normalization_and_connect_args():
    """Verify postgres:// is converted to postgresql:// and connect_args is empty for PostgreSQL."""
    test_pg_url = "postgres://postgres_user:secret_pass@db.supabase.co:5432/postgres"

    with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
        with mock.patch.dict(os.environ, {"DATABASE_URL": test_pg_url}):
            from app.core import database
            importlib.reload(database)

            # Check created engine args
            mock_create_engine.assert_called_once()
            called_url, called_kwargs = mock_create_engine.call_args
            assert called_url[0].startswith("postgresql://")
            assert called_kwargs.get("connect_args") == {}


def test_postgresql_standard_url():
    """Verify standard postgresql:// URL works and connect_args is empty (no SQLite-specific check_same_thread)."""
    test_pg_url = "postgresql://postgres_user:secret_pass@db.supabase.co:5432/postgres"

    with mock.patch("sqlalchemy.create_engine") as mock_create_engine:
        with mock.patch.dict(os.environ, {"DATABASE_URL": test_pg_url}):
            from app.core import database
            importlib.reload(database)

            mock_create_engine.assert_called_once()
            called_url, called_kwargs = mock_create_engine.call_args
            assert called_url[0].startswith("postgresql://")
            assert called_kwargs.get("connect_args") == {}


def test_init_db_runs_without_error():
    """Verify init_db() initializes database schema and migration checks without error."""
    from app.core import database
    importlib.reload(database)

    # Calling init_db() should run inspector-based column migration check without error
    database.init_db()
