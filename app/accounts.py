"""L'account utente su Postgres (Fase 5): upsert del profilo al login.

Invariante di tutte le tabelle account: `auth_id` viene SEMPRE dal JWT verificato
(app/auth.py), mai dal body della richiesta. Il backend gira come `postgres`
(BYPASSRLS), quindi la RLS non è il confine: il confine è il `WHERE auth_id = ?`
qui e in ogni modulo dati account. La RLS in scripts/supabase_setup.sql resta come
difesa in profondità.
"""

from datetime import datetime, timezone

from app.db import session_scope
from app.models import Profile


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert_profile(auth_id, email="", nickname_seed=""):
    """Crea il profilo al primo accesso, o aggiorna last_seen_at (ed email se
    cambiata). Ritorna il profilo come dict. `nickname_seed` popola il nickname
    solo alla creazione e solo se non vuoto (di norma il nickname locale del
    gioco), mai sovrascrive uno già scelto."""
    if not auth_id:
        return None
    now = _now_iso()
    email = (email or "").lower()
    with session_scope() as s:
        row = s.get(Profile, auth_id)
        if row is None:
            row = Profile(auth_id=auth_id, email=email,
                          nickname=(nickname_seed or "").strip()[:32],
                          created_at=now, last_seen_at=now)
            s.add(row)
        else:
            row.last_seen_at = now
            if email:
                row.email = email
        return {"auth_id": row.auth_id, "email": row.email,
                "nickname": row.nickname, "created_at": row.created_at}
