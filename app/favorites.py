"""Gli indicatori preferiti di un utente (Fase 5.1).

Invariante di sicurezza: `auth_id` arriva SEMPRE dal JWT verificato
(app/auth.current_user), mai dal body. Il backend gira BYPASSRLS, quindi la RLS
non e' il confine: e' il `WHERE auth_id = ?` qui sotto. Un endpoint che accettasse
`auth_id` dal client sarebbe una fuga completa dei dati account.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db import session_scope
from app.models import Favorite


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_ids(auth_id):
    """Gli id indicatore preferiti dell'utente, piu' recenti prima."""
    if not auth_id:
        return []
    with session_scope() as s:
        rows = s.execute(
            select(Favorite.indicator_id)
            .where(Favorite.auth_id == auth_id)
            .order_by(Favorite.created_at.desc())).scalars().all()
    return list(rows)


def add(auth_id, indicator_id):
    """Aggiunge un preferito. Idempotente (se c'e' gia', non fa nulla)."""
    if not auth_id or not indicator_id:
        return
    with session_scope() as s:
        exists = s.get(Favorite, {"auth_id": auth_id, "indicator_id": indicator_id})
        if exists is None:
            s.add(Favorite(auth_id=auth_id, indicator_id=indicator_id, created_at=_now_iso()))


def remove(auth_id, indicator_id):
    """Toglie un preferito."""
    if not auth_id or not indicator_id:
        return
    with session_scope() as s:
        s.execute(delete(Favorite).where(
            Favorite.auth_id == auth_id, Favorite.indicator_id == indicator_id))
