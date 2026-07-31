"""Classifica globale del quiz, sul backend mutabile condiviso (Postgres in
produzione, SQLite in test).

Una Session per chiamata (vedi app/db.py): nessuna connessione condivisa tra
thread, in linea col deploy (gunicorn a piu' thread, un solo worker). Il
punteggio salvato e' sempre la miglior streak verificata di una sessione firmata
(app/quiz_tokens.py): il client non manda mai un punteggio arbitrario, vedi
app/views.py. `user_id` (opzionale) lega la riga a un account Supabase quando c'e'
un JWT valido: il gioco resta anonimo per chi non si registra.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.db import session_scope
from app.models import Score

MODES = ("compare", "order")
PERIODS = ("week", "all")
MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def _now_iso():
    # ISO UTC con la Z finale: il confronto lessicografico e' cronologico, cosi'
    # ordinamento e finestra settimanale non usano funzioni-tempo SQL.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _week_cutoff():
    return (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upsert_if_higher(session, row):
    """INSERT con ON CONFLICT(mode, session_id): un punteggio piu' alto sostituisce
    il precedente, uno piu' basso non fa nulla (niente regressioni in classifica).
    Atomico, un solo punto che distingue il dialetto."""
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as _insert
    else:
        from sqlalchemy.dialects.sqlite import insert as _insert
    stmt = _insert(Score).values(**row)
    stmt = stmt.on_conflict_do_update(
        index_elements=["mode", "session_id"],
        set_={
            "score": stmt.excluded.score,
            "nickname": stmt.excluded.nickname,
            "detail": stmt.excluded.detail,
            "user_id": stmt.excluded.user_id,
            "created_at": stmt.excluded.created_at,
        },
        where=(stmt.excluded.score > Score.score),
    )
    session.execute(stmt)


def submit(mode, session_id, nickname, score, detail=None, user_id=None):
    """Upsert per (mode, session_id): sostituisce solo se il punteggio migliora."""
    if mode not in MODES:
        raise ValueError("bad_mode")
    with session_scope() as s:
        _upsert_if_higher(s, {
            "mode": mode, "session_id": session_id, "nickname": nickname,
            "score": int(score), "detail": json.dumps(detail or {}),
            "user_id": user_id, "created_at": _now_iso(),
        })


def delete_entry(mode, nickname):
    """Rimuove una riga per moderazione (nickname sfuggito al filtro, voce di
    test, ecc). Usata dall'endpoint admin in app/views.py."""
    if mode not in MODES:
        raise ValueError("bad_mode")
    with session_scope() as s:
        result = s.execute(
            delete(Score).where(Score.mode == mode, Score.nickname == nickname))
        return result.rowcount


def _rank(session, mode, score, created_at, week_cutoff=None):
    q = select(func.count()).select_from(Score).where(Score.mode == mode)
    if week_cutoff is not None:
        q = q.where(Score.created_at >= week_cutoff)
    q = q.where(
        (Score.score > score)
        | ((Score.score == score) & (Score.created_at < created_at)))
    return session.execute(q).scalar_one() + 1


def ranks_for_session(mode, session_id):
    """(rank_all, rank_week) per la riga appena inviata, o (None, None) se
    non e' stata salvata (punteggio peggiore di uno gia' registrato)."""
    with session_scope() as s:
        row = s.execute(
            select(Score.score, Score.created_at)
            .where(Score.mode == mode, Score.session_id == session_id)).first()
        if row is None:
            return None, None
        score, created_at = row
        rank_all = _rank(s, mode, score, created_at)
        rank_week = _rank(s, mode, score, created_at, week_cutoff=_week_cutoff())
        return rank_all, rank_week


def top(mode, period="all", limit=DEFAULT_LIMIT):
    if mode not in MODES:
        raise ValueError("bad_mode")
    if period not in PERIODS:
        raise ValueError("bad_period")
    limit = max(1, min(limit, MAX_LIMIT))
    with session_scope() as s:
        q = select(Score.nickname, Score.score, Score.detail, Score.created_at) \
            .where(Score.mode == mode)
        if period == "week":
            q = q.where(Score.created_at >= _week_cutoff())
        # id ASC come ultimo criterio: due invii nello stesso secondo hanno lo
        # stesso created_at (risoluzione al secondo, come il vecchio strftime),
        # quindi l'ordine di inserimento fa da spareggio deterministico sui due
        # dialetti (prima lo faceva implicitamente il rowid di SQLite).
        q = q.order_by(Score.score.desc(), Score.created_at.asc(), Score.id.asc()).limit(limit)
        rows = s.execute(q).all()
    return [
        {
            "rank": idx + 1,
            "nickname": nickname,
            "score": score,
            "detail": json.loads(detail),
            "when": created_at,
        }
        for idx, (nickname, score, detail, created_at) in enumerate(rows)
    ]
