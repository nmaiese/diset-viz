"""Gestione account: nickname, export e cancellazione (GDPR, Fase 5.3).

Invariante: `auth_id` sempre dal JWT verificato. La cancellazione elimina tutte
le righe dell'utente su Postgres e l'utente su Supabase Auth (admin API con la
secret key). Best-effort sull'admin API: se non risponde, le righe sono comunque
cancellate e lo si segnala.
"""

import urllib.error
import urllib.request

from sqlalchemy import delete, select

from app import config
from app.db import session_scope
from app.models import (Achievement, DailyResult, Favorite, PlayerStat, Profile,
                        SavedComparison, Score)


def set_nickname(auth_id, nickname):
    """Aggiorna il nickname del profilo (gia' validato dal chiamante). Ritorna
    True se il profilo esiste."""
    if not auth_id:
        return False
    with session_scope() as s:
        row = s.get(Profile, auth_id)
        if row is None:
            return False
        row.nickname = nickname
        return True


def export_data(auth_id):
    """Tutti i dati dell'utente, per il diritto di portabilita'."""
    if not auth_id:
        return {}
    with session_scope() as s:
        profile = s.get(Profile, auth_id)
        favs = s.execute(select(Favorite.indicator_id, Favorite.created_at)
                         .where(Favorite.auth_id == auth_id)).all()
        stats = s.execute(select(PlayerStat).where(PlayerStat.auth_id == auth_id)).scalars().all()
        daily = s.execute(select(DailyResult).where(DailyResult.auth_id == auth_id)).scalars().all()
        achs = s.execute(select(Achievement.achievement_id, Achievement.unlocked_at)
                         .where(Achievement.auth_id == auth_id)).all()
        scores = s.execute(select(Score.mode, Score.score, Score.created_at)
                           .where(Score.user_id == auth_id)).all()
        comps = s.execute(select(SavedComparison).where(SavedComparison.auth_id == auth_id)).scalars().all()
        return {
            "profile": ({"auth_id": profile.auth_id, "email": profile.email,
                         "nickname": profile.nickname, "created_at": profile.created_at}
                        if profile else None),
            "favorites": [{"indicator_id": i, "created_at": c} for i, c in favs],
            "player_stats": [{"mode": r.mode, "best_streak": r.best_streak,
                              "rounds_played": r.rounds_played, "correct": r.correct,
                              "games_played": r.games_played, "wins": r.wins,
                              "current_daily_streak": r.current_daily_streak,
                              "max_daily_streak": r.max_daily_streak} for r in stats],
            "daily_results": [{"puzzle_date": r.puzzle_date, "attempts": r.attempts,
                               "solved": bool(r.solved)} for r in daily],
            "achievements": [{"achievement_id": a, "unlocked_at": u} for a, u in achs],
            "scores": [{"mode": m, "score": sc, "when": w} for m, sc, w in scores],
            "saved_comparisons": [{"title": r.title, "config": r.config,
                                   "created_at": r.created_at} for r in comps],
        }


def _delete_supabase_user(auth_id):
    """Cancella l'utente su Supabase Auth via admin API. Ritorna True/False."""
    url = (config.SUPABASE_URL or "").rstrip("/")
    secret = config.SUPABASE_SECRET_KEY
    if not url or not secret:
        return False
    req = urllib.request.Request(
        f"{url}/auth/v1/admin/users/{auth_id}",
        headers={"apikey": secret, "Authorization": f"Bearer {secret}"},
        method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        return e.code == 404  # gia' assente = ok
    except Exception:  # noqa: BLE001
        return False


def delete_account(auth_id):
    """Diritto all'oblio: elimina tutte le righe dell'utente e l'utente Supabase.
    Ritorna `{rows_deleted, supabase_deleted}`."""
    if not auth_id:
        return {"rows_deleted": False, "supabase_deleted": False}
    with session_scope() as s:
        for model in (Favorite, PlayerStat, DailyResult, Achievement, SavedComparison):
            s.execute(delete(model).where(model.auth_id == auth_id))
        s.execute(delete(Score).where(Score.user_id == auth_id))
        s.execute(delete(Profile).where(Profile.auth_id == auth_id))
    supa = _delete_supabase_user(auth_id)
    return {"rows_deleted": True, "supabase_deleted": supa}
