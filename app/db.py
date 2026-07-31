"""L'accesso al backend mutabile: un Engine SQLAlchemy, una Session per chiamata.

Uno store, due dialetti. In produzione `config.DATABASE_URL` punta al Postgres di
Supabase (pooler Supavisor in transaction mode); in test e in CI, dove nessun
server Postgres esiste, `DATABASE_URL` e' vuoto e si ricade su un file SQLite,
ricavato da `config.LEADERBOARD_DB` esattamente come prima della migrazione. Lo
stesso codice ORM gira su entrambi: il gate della catena e i deploy, che girano
la suite intera su checkout senza database, restano leggeri.

L'Engine e' in cache **per URL risolta**, non globale: i test riassegnano
`config.LEADERBOARD_DB` a un file temporaneo per classe, quindi l'URL cambia e un
nuovo Engine nasce da solo, con le tabelle create al volo (su SQLite lo schema lo
possiede questo modulo, su Postgres lo possiede Alembic).
"""

import threading
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.models import Base

_engines = {}
_sessionmakers = {}
_lock = threading.Lock()


def _resolve_url():
    """L'URL del backend: Postgres se configurato, altrimenti un file SQLite."""
    url = (config.DATABASE_URL or "").strip()
    if url:
        # Forza il driver psycopg v3 e non v2 (default storico dello schema
        # `postgresql://`): e' quello nei requirements.
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        elif url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        return url
    return "sqlite:///" + config.LEADERBOARD_DB


def _make_engine(url):
    if url.startswith("sqlite"):
        engine = create_engine(
            url, future=True,
            # una connessione per thread condivisa dai molti thread di gunicorn
            connect_args={"check_same_thread": False},
        )
        # Su SQLite non c'e' Alembic: lo schema lo crea qui, idempotente.
        Base.metadata.create_all(engine)
        return engine
    # Postgres via pooler Supavisor (6543, transaction mode): niente prepared
    # statement (il transaction pooler non li supporta), pool piccolo per
    # istanza (1 worker x 8 thread), pre-ping contro le connessioni morte.
    return create_engine(
        url, future=True,
        pool_size=3, max_overflow=2, pool_pre_ping=True,
        connect_args={"prepare_threshold": None, "sslmode": "require"},
    )


def _sessionmaker_for(url):
    sm = _sessionmakers.get(url)
    if sm is None:
        with _lock:
            sm = _sessionmakers.get(url)
            if sm is None:
                engine = _make_engine(url)
                _engines[url] = engine
                sm = sessionmaker(bind=engine, future=True, expire_on_commit=False)
                _sessionmakers[url] = sm
    return sm


def get_engine():
    url = _resolve_url()
    _sessionmaker_for(url)
    return _engines[url]


@contextmanager
def session_scope():
    """Una Session per chiamata, con commit/rollback/close automatici: lo stesso
    modello 'una connessione per chiamata' del vecchio sqlite3 grezzo, cosi' non
    serve un contesto di richiesta Flask (i test chiamano gli store diretti)."""
    session = _sessionmaker_for(_resolve_url())()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
