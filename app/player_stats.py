"""Statistiche di gioco per-account (Fase 5.2), server-authoritative.

Raccolte dal profilo leggero pre-Supabase (branch game-user-db-achievements) e
ri-chiavate da player_id ad auth_id, sopra l'ORM. Gli aggregati per modalita'
('compare', 'order', 'daily') si aggiornano dagli endpoint di gioco dove il
risultato e' gia' verificato dal server. Lo storico giornaliero
(`daily_results`) alimenta la streak ed evita che rigiocare lo stesso giorno
gonfi i numeri.

Invariante: `auth_id` viene sempre dal JWT verificato, mai dal body. Read-modify-
write in una Session per chiamata (un utente per volta, traffico basso): niente
ON CONFLICT con espressioni SQL, cosi' la semantica e' identica sui due dialetti.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.db import session_scope
from app.models import DailyResult, PlayerStat

QUIZ_MODES = ("compare", "order")
_ALL_MODES = (*QUIZ_MODES, "daily")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_mode_stats():
    return {
        "best_streak": 0, "rounds_played": 0, "correct": 0,
        "games_played": 0, "wins": 0,
        "current_daily_streak": 0, "max_daily_streak": 0,
        "last_played_at": None,
    }


def _get_or_new(session, auth_id, mode):
    row = session.get(PlayerStat, {"auth_id": auth_id, "mode": mode})
    if row is None:
        row = PlayerStat(auth_id=auth_id, mode=mode)
        session.add(row)
    return row


def record_quiz_answer(auth_id, mode, correct, best_streak):
    """Aggiorna gli aggregati di una modalita' quiz dopo una risposta verificata:
    un round in piu', un colpito in piu' se corretto, record di streak se
    migliorato. Da chiamare una volta per risposta (il chiamante lo garantisce)."""
    if not auth_id or mode not in QUIZ_MODES:
        return
    with session_scope() as s:
        row = _get_or_new(s, auth_id, mode)
        row.best_streak = max(row.best_streak or 0, int(best_streak or 0))
        row.rounds_played = (row.rounds_played or 0) + 1
        row.correct = (row.correct or 0) + (1 if correct else 0)
        row.last_played_at = _now_iso()


def _daily_streaks(solved_dates):
    """(current, max) run di giorni consecutivi risolti. `current` risale dalla
    data risolta piu' recente, cosi' l'ordine di arrivo non falsa il conteggio."""
    if not solved_dates:
        return 0, 0
    days = sorted({date.fromisoformat(d) for d in solved_dates})
    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        longest = max(longest, run)
    current = 1
    for prev, cur in zip(reversed(days[:-1]), reversed(days[1:])):
        if cur - prev == timedelta(days=1):
            current += 1
        else:
            break
    return current, longest


def record_daily(auth_id, puzzle_date, attempts, solved):
    """Registra il risultato di una giornaliera. Non sovrascrive un risultato
    gia' presente per quella data (niente replay che gonfia i numeri). Ricalcola
    le streak dallo storico. Ritorna True se il risultato era nuovo."""
    if not auth_id or not puzzle_date:
        return False
    with session_scope() as s:
        exists = s.get(DailyResult, {"auth_id": auth_id, "puzzle_date": puzzle_date})
        if exists is not None:
            return False
        s.add(DailyResult(auth_id=auth_id, puzzle_date=puzzle_date,
                          attempts=int(attempts or 0), solved=1 if solved else 0))
        s.flush()
        solved_dates = s.execute(
            select(DailyResult.puzzle_date)
            .where(DailyResult.auth_id == auth_id, DailyResult.solved == 1)).scalars().all()
        current, longest = _daily_streaks(list(solved_dates))
        row = _get_or_new(s, auth_id, "daily")
        row.games_played = (row.games_played or 0) + 1
        row.wins = (row.wins or 0) + (1 if solved else 0)
        row.current_daily_streak = current
        row.max_daily_streak = max(row.max_daily_streak or 0, longest)
        row.last_played_at = _now_iso()
        return True


def stats_map(auth_id):
    """{mode: stats} per tutte le modalita', con default a zero. Usato dagli
    achievement e dall'endpoint profilo."""
    result = {mode: _empty_mode_stats() for mode in _ALL_MODES}
    if not auth_id:
        return result
    with session_scope() as s:
        rows = s.execute(
            select(PlayerStat).where(PlayerStat.auth_id == auth_id)).scalars().all()
    for r in rows:
        result[r.mode] = {
            "best_streak": r.best_streak, "rounds_played": r.rounds_played,
            "correct": r.correct, "games_played": r.games_played, "wins": r.wins,
            "current_daily_streak": r.current_daily_streak,
            "max_daily_streak": r.max_daily_streak, "last_played_at": r.last_played_at,
        }
    return result


def merge_local(auth_id, local):
    """Fonde le statistiche locali (localStorage del gioco) nell'account, UNA
    volta. I campi 'best' si fondono con max, i contatori con somma. Idempotenza
    la garantisce il chiamante (flag one-time lato client); qui si applica e basta.

    `local` e' `{mode: {best_streak, rounds_played, correct, games_played, wins,
    max_daily_streak}}` con le chiavi che il client sa produrre; le mancanti = 0."""
    if not auth_id or not isinstance(local, dict):
        return
    with session_scope() as s:
        for mode in _ALL_MODES:
            src = local.get(mode) or {}
            if not any(src.get(k) for k in ("best_streak", "rounds_played", "correct",
                                            "games_played", "wins", "max_daily_streak")):
                continue
            row = _get_or_new(s, auth_id, mode)
            row.best_streak = max(row.best_streak or 0, int(src.get("best_streak", 0) or 0))
            row.rounds_played = (row.rounds_played or 0) + int(src.get("rounds_played", 0) or 0)
            row.correct = (row.correct or 0) + int(src.get("correct", 0) or 0)
            row.games_played = (row.games_played or 0) + int(src.get("games_played", 0) or 0)
            row.wins = (row.wins or 0) + int(src.get("wins", 0) or 0)
            row.max_daily_streak = max(row.max_daily_streak or 0, int(src.get("max_daily_streak", 0) or 0))
