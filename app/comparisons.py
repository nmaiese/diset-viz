"""Confronti salvati per-account (Fase 5.3).

Invariante: `auth_id` sempre dal JWT verificato, mai dal body. Il backend gira
BYPASSRLS: il confine per-utente è il `WHERE auth_id = ?` qui. Serviti solo dal
backend (niente accesso browser diretto, niente condivisione pubblica).
"""

import json
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db import session_scope
from app.models import SavedComparison

MAX_PER_USER = 100
MAX_TITLE = 120


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public(row):
    try:
        config = json.loads(row.config)
    except (TypeError, ValueError):
        config = {}
    return {"id": row.id, "title": row.title, "config": config,
            "created_at": row.created_at, "updated_at": row.updated_at}


def list_for(auth_id):
    if not auth_id:
        return []
    with session_scope() as s:
        rows = s.execute(
            select(SavedComparison)
            .where(SavedComparison.auth_id == auth_id)
            .order_by(SavedComparison.updated_at.desc())).scalars().all()
        return [_public(r) for r in rows]


def save(auth_id, title, config):
    """Crea un confronto salvato. Ritorna la voce pubblica, o None se invalido /
    oltre il tetto per utente."""
    if not auth_id:
        return None
    title = (title or "").strip()[:MAX_TITLE] or "Confronto senza titolo"
    now = _now_iso()
    with session_scope() as s:
        count = s.query(SavedComparison).filter(SavedComparison.auth_id == auth_id).count()
        if count >= MAX_PER_USER:
            return None
        row = SavedComparison(auth_id=auth_id, title=title,
                              config=json.dumps(config or {}), created_at=now, updated_at=now)
        s.add(row)
        s.flush()
        return _public(row)


def remove(auth_id, comparison_id):
    """Toglie un confronto, solo se dell'utente (il WHERE su auth_id impedisce di
    cancellare quelli altrui)."""
    if not auth_id:
        return
    with session_scope() as s:
        s.execute(delete(SavedComparison).where(
            SavedComparison.id == comparison_id, SavedComparison.auth_id == auth_id))
