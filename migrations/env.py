"""Ambiente Alembic per il backend mutabile.

L'URL viene da `app.config.DIRECT_URL` (connessione diretta Supabase 5432, non il
pooler in transaction mode, che non regge le migrazioni). In assenza di Postgres
si ricade sullo stesso SQLite di app/db.py, cosi' `alembic upgrade head` gira
anche in locale senza un server. `target_metadata` e' il Base ORM: da qui
`--autogenerate` vede le tabelle.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import config as app_config
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url():
    url = (app_config.DIRECT_URL or app_config.DATABASE_URL or "").strip()
    if not url:
        return "sqlite:///" + app_config.LEADERBOARD_DB
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def run_migrations_offline():
    context.configure(
        url=_resolve_url(), target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
