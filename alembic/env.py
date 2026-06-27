"""Alembic environment configuration.

Reads ACCOUNT_MANAGER_DATABASE_URL from the environment (matching the convention
in core/db/engine.py).  Falls back to a local SQLite database when the variable
is not set.

Alembic needs a *synchronous* engine, so PostgreSQL URLs that use the ``asyncpg``
dialect are transparently rewritten to ``psycopg2``.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Project root on sys.path so ``core.db`` is importable ──────────────
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

# ── Alembic Config object ─────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import target metadata from SQLModel definitions ──────────────────
from sqlmodel import SQLModel  # noqa: E402

# This triggers model registration so that SQLModel.metadata is populated.
from core.db import models  # noqa: E402, F401

target_metadata = SQLModel.metadata


# ── Helpers ───────────────────────────────────────────────────────────

def _resolve_database_url() -> str:
    """Return the synchronous database URL derived from the environment."""
    url = os.getenv(
        "ACCOUNT_MANAGER_DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'account_manager.db')}",
    )
    # Alembic always needs a sync driver; normalise asyncpg → psycopg2.
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return url


# ── Offline migrations (generates SQL without a live connection) ───────

def run_migrations_offline() -> None:
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations (uses a live DB connection) ─────────────────────

def run_migrations_online() -> None:
    url = _resolve_database_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
