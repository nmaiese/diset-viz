"""Statistiche di gioco per-account (Fase 5.2), server-authoritative.

Raccolte dal profilo leggero pre-Supabase (branch game-user-db-achievements) e
ri-chiavate da player_id ad auth_id, sopra l'ORM. Gli aggregati per modalità
('compare', 'order', 'daily') si aggiornano dagli endpoint di gioco dove il
risultato è già verificato dal server. Lo storico giornaliero
(`daily_results`) alimenta la streak ed evita che rigiocare lo stesso giorno
gonfi i numeri.

Invariante: `auth_id` viene sempre dal JWT verificato, mai dal body. Read-modify-
write in una Session per chiamata (un utente per volta, traffico basso): niente
ON CONFLICT con espressioni SQL, così la semantica è identica sui due dialetti.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import game_daily
from app.db import session_scope
from app.models import DailyResult, DailyScore, PlayerStat

QUIZ_MODES = ("compare", "order")
_ALL_MODES = (*QUIZ_MODES, "daily")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_mode_stats():
    return {
        "best_streak": 0, "rounds_played": 0, "correct": 0,
        "games_played": 0, "wins": 0,
        "current_daily_streak": 0, "max_daily_streak": 0,
        "historic_best_streak": 0,
        "last_played_at": None,
    }


def _get_or_new(session, auth_id, mode):
    row = session.get(PlayerStat, {"auth_id": auth_id, "mode": mode})
    if row is None:
        row = PlayerStat(auth_id=auth_id, mode=mode)
        session.add(row)
    return row


def record_quiz_answer(auth_id, mode, correct, best_streak):
    """Aggiorna gli aggregati di una modalità quiz dopo una risposta verificata:
    un round in più, un colpito in più se corretto, record di streak se
    migliorato. Da chiamare una volta per risposta (il chiamante lo garantisce)."""
    if not auth_id or mode not in QUIZ_MODES:
        return
    with session_scope() as s:
        row = _get_or_new(s, auth_id, mode)
        row.best_streak = max(row.best_streak or 0, int(best_streak or 0))
        row.rounds_played = (row.rounds_played or 0) + 1
        row.correct = (row.correct or 0) + (1 if correct else 0)
        row.last_played_at = _now_iso()


def _daily_streaks(solved_dates, today=None):
    """(current, max) run di giorni consecutivi risolti. `current` risale dalla
    data risolta piu' recente, cosi' l'ordine di arrivo non falsa il conteggio, e
    vale solo se quella data e' oggi o ieri (giorno di Roma): una serie ferma da due
    giorni e' spezzata."""
    if not solved_dates:
        return 0, 0
    today = today or game_daily.oggi_roma()
    days = sorted({date.fromisoformat(d) for d in solved_dates})
    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        longest = max(longest, run)
    if today - days[-1] > timedelta(days=1):
        return 0, longest
    current = 1
    for prev, cur in zip(reversed(days[:-1]), reversed(days[1:])):
        if cur - prev == timedelta(days=1):
            current += 1
        else:
            break
    return current, longest


def record_daily(auth_id, puzzle_date, attempts, solved):
    """Registra il risultato di una giornaliera. `puzzle_date` e' una data ISO
    (YYYY-MM-DD), il resto si rifiuta. Non sovrascrive un risultato gia' presente
    per quella data (niente replay che gonfia i numeri). La serie a giorni non si
    salva: si ricalcola da `daily_results` a ogni lettura (`stats_map`). Ritorna
    True se il risultato era nuovo."""
    if not auth_id or not isinstance(puzzle_date, str):
        return False
    try:
        date.fromisoformat(puzzle_date)
    except ValueError:
        return False
    with session_scope() as s:
        exists = s.get(DailyResult, {"auth_id": auth_id, "puzzle_date": puzzle_date})
        if exists is not None:
            return False
        s.add(DailyResult(auth_id=auth_id, puzzle_date=puzzle_date,
                          attempts=int(attempts or 0), solved=1 if solved else 0))
        row = _get_or_new(s, auth_id, "daily")
        row.games_played = (row.games_played or 0) + 1
        row.wins = (row.wins or 0) + (1 if solved else 0)
        row.last_played_at = _now_iso()
        return True


def record_daily_score(auth_id, gioco, data, punteggio):
    """Registra il punteggio di una sfida del giorno. Un solo tentativo per
    (account, gioco, data): il secondo si rifiuta (False) e non sovrascrive."""
    if not auth_id or not gioco or not isinstance(data, str):
        return False
    try:
        date.fromisoformat(data)
    except ValueError:
        return False
    try:
        with session_scope() as s:
            s.add(DailyScore(auth_id=auth_id, gioco=gioco, data=data,
                             punteggio=int(punteggio), created_at=_now_iso()))
        return True
    except IntegrityError:
        return False


def stats_map(auth_id):
    """{mode: stats} per tutte le modalità, con default a zero. Usato dagli
    achievement e dall'endpoint profilo."""
    result = {mode: _empty_mode_stats() for mode in _ALL_MODES}
    if not auth_id:
        return result
    with session_scope() as s:
        rows = s.execute(
            select(PlayerStat).where(PlayerStat.auth_id == auth_id)).scalars().all()
        solved_dates = s.execute(
            select(DailyResult.puzzle_date)
            .where(DailyResult.auth_id == auth_id, DailyResult.solved == 1)).scalars().all()
    for r in rows:
        result[r.mode] = {
            "best_streak": r.best_streak, "rounds_played": r.rounds_played,
            "correct": r.correct, "games_played": r.games_played, "wins": r.wins,
            "current_daily_streak": r.current_daily_streak,
            "max_daily_streak": 0, "historic_best_streak": 0,
            "last_played_at": r.last_played_at,
        }
    # La serie a giorni viene sempre da `daily_results`. Il `max_daily_streak`
    # salvato e' il dato storico del merge locale (vittorie di fila, non giorni)
    # e si espone a parte, senza toccarlo e senza mescolarlo.
    daily = result["daily"]
    daily["historic_best_streak"] = max((r.max_daily_streak or 0 for r in rows if r.mode == "daily"), default=0)
    daily["current_daily_streak"], daily["max_daily_streak"] = _daily_streaks(list(solved_dates))
    return result


def merge_local(auth_id, local):
    """Fonde le statistiche locali (localStorage del gioco) nell'account, UNA
    volta. I campi 'best' si fondono con max, i contatori con somma. Idempotenza
    la garantisce il chiamante (flag one-time lato client); qui si applica e basta.

    `local` è `{mode: {best_streak, rounds_played, correct, games_played, wins,
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
