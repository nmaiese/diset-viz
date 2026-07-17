"""Classifica globale del quiz, su un file SQLite (nessun server DB).

Una connessione per chiamata: nessuna connessione condivisa tra thread, in
linea con il modello di deploy attuale (gunicorn a più thread, un solo
worker). Il punteggio salvato è sempre la miglior streak verificata di una
sessione firmata (app.quiz_tokens): il client non manda mai un punteggio
arbitrario, vedi app/views.py.
"""

import json
import os
import sqlite3

from app import config

MODES = ("compare", "order")
PERIODS = ("week", "all")
MAX_LIMIT = 50
DEFAULT_LIMIT = 20

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mode TEXT NOT NULL CHECK (mode IN ('compare','order')),
  session_id TEXT NOT NULL,
  nickname TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score >= 1 AND score <= 10000),
  detail TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  UNIQUE (mode, session_id)
);
CREATE INDEX IF NOT EXISTS idx_scores_rank ON scores (mode, score DESC, created_at ASC);
"""


def _connect():
    db_path = config.LEADERBOARD_DB
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(_SCHEMA)
    return conn


def submit(mode, session_id, nickname, score, detail=None):
    """Upsert per (mode, session_id): un punteggio più alto sostituisce il
    precedente, uno più basso non fa nulla (niente regressioni in classifica)."""
    if mode not in MODES:
        raise ValueError("bad_mode")
    detail_json = json.dumps(detail or {})
    conn = _connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO scores (mode, session_id, nickname, score, detail)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mode, session_id) DO UPDATE SET
                  score = excluded.score,
                  nickname = excluded.nickname,
                  detail = excluded.detail,
                  created_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')
                WHERE excluded.score > scores.score
                """,
                (mode, session_id, nickname, score, detail_json),
            )
    finally:
        conn.close()


def _rank(conn, mode, score, created_at, period_sql):
    row = conn.execute(
        f"SELECT COUNT(*) FROM scores WHERE mode = ? AND {period_sql} "
        "AND (score > ? OR (score = ? AND created_at < ?))",
        (mode, score, score, created_at),
    ).fetchone()
    return row[0] + 1


def ranks_for_session(mode, session_id):
    """(rank_all, rank_week) per la riga appena inviata, o (None, None) se
    non è stata salvata (punteggio peggiore di uno già registrato)."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT score, created_at FROM scores WHERE mode = ? AND session_id = ?",
            (mode, session_id),
        ).fetchone()
        if row is None:
            return None, None
        score, created_at = row
        rank_all = _rank(conn, mode, score, created_at, "1=1")
        rank_week = _rank(conn, mode, score, created_at, "created_at >= datetime('now','-7 days')")
        return rank_all, rank_week
    finally:
        conn.close()


def top(mode, period="all", limit=DEFAULT_LIMIT):
    if mode not in MODES:
        raise ValueError("bad_mode")
    if period not in PERIODS:
        raise ValueError("bad_period")
    limit = max(1, min(limit, MAX_LIMIT))
    where = "mode = ?"
    if period == "week":
        where += " AND created_at >= datetime('now','-7 days')"
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT nickname, score, detail, created_at FROM scores WHERE {where} "
            "ORDER BY score DESC, created_at ASC LIMIT ?",
            (mode, limit),
        ).fetchall()
    finally:
        conn.close()
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
