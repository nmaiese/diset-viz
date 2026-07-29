"""Lo stato **vivo** della catena, su cui il cruscotto /_pipeline si aggiorna.

Il cruscotto sembrava morto per una ragione strutturale. I battiti che ogni
ruolo lasciava erano file locali, ignorati da git, scritti sul disco effimero
dell'agente cloud: il server che serve divarioitalia.it e' un'altra macchina, e
quei file non la raggiungevano mai. L'unico canale condiviso era il commit su
master, che pero' compare solo a merge avvenuto (e su Cloud Run solo dopo un
rebuild dell'immagine), quindi il lavoro in volo restava invisibile.

Questo modulo chiude il buco riusando l'infrastruttura gia' in produzione: lo
**stesso** SQLite della leaderboard (`config.LEADERBOARD_DB`), che Litestream
replica di continuo su GCS. Gli agenti non scrivono qui direttamente (non hanno
credenziali GCP, e non devono averne): fanno un POST all'endpoint del sito, che
scrive questa tabella. Cosi' il battito e' vivo, condiviso fra le macchine, e non
sporca master di un commit per battito.

Una riga e' `beat` (un ruolo che lavora, prima ancora che ci sia una PR) o `pr`
(una PR aperta su `automation/*`, con stato CI e mergeabilita', che il lanciatore
fotografa a ogni tick). Le righe piu' vecchie della soglia si considerano morte,
come i vecchi battiti su file: una sessione caduta senza chiudere non resta in
pagina per sempre.

Una connessione per chiamata, come la leaderboard: nessuna connessione condivisa
fra thread, in linea col deploy (gunicorn a piu' thread, un solo worker).
"""

import os
import sqlite3

from app import config

STALE_HOURS = 6

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_activity (
  key TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('beat','pr')),
  role TEXT NOT NULL DEFAULT '',
  indicator TEXT NOT NULL DEFAULT '',
  stage TEXT NOT NULL DEFAULT '',
  run_id TEXT NOT NULL DEFAULT '',
  pr INTEGER,
  branch TEXT NOT NULL DEFAULT '',
  ci TEXT NOT NULL DEFAULT '',
  mergeable TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_kind ON pipeline_activity (kind, updated_at DESC);

-- Il consumo token per run: telemetria durevole, NON un battito. Sta in una
-- tabella a parte perche' i battiti scadono (finestra STALE_HOURS) e si
-- cancellano alla chiusura, mentre il costo di una run e' storia da tenere. La
-- chiave e' il run_id del RUOLO (produttore/verificatore/ammissione), non del
-- lanciatore che lo POSTa, cosi' il totale si attacca all'indicatore giusto.
CREATE TABLE IF NOT EXISTS pipeline_tokens (
  run_id TEXT PRIMARY KEY,
  indicator TEXT NOT NULL DEFAULT '',
  stage TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL DEFAULT '',
  tokens INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
"""


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cutoff(now, stale_hours):
    from datetime import datetime, timedelta
    # now e' ISO UTC; il confronto lessicografico su ISO e' cronologico.
    try:
        ref = datetime.fromisoformat(now)
    except ValueError:
        ref = datetime.fromisoformat(_now())
    return (ref - timedelta(hours=stale_hours)).isoformat(timespec="seconds")


def _connect():
    db_path = config.LEADERBOARD_DB
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(_SCHEMA)
    return conn


def record_beat(run_id, role="", indicator="", stage="", now=None):
    """Un ruolo che parte (o continua) lascia il proprio battito. Idempotente sul
    `run_id`, cosi' un aggiornamento sostituisce il precedente."""
    if not run_id:
        raise ValueError("run_id mancante")
    stamp = now or _now()
    conn = _connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO pipeline_activity (key, kind, role, indicator, stage, run_id, updated_at)
                VALUES (?, 'beat', ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  role=excluded.role, indicator=excluded.indicator,
                  stage=excluded.stage, updated_at=excluded.updated_at
                """,
                (f"beat:{run_id}", role, indicator, stage, run_id, stamp),
            )
    finally:
        conn.close()


def close_beat(run_id):
    """Un ruolo che chiude cancella il proprio battito."""
    if not run_id:
        return
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM pipeline_activity WHERE key = ?", (f"beat:{run_id}",))
    finally:
        conn.close()


def replace_prs(prs, now=None):
    """Sostituisce in blocco la fotografia delle PR aperte (il lanciatore la
    riscrive a ogni tick). Atomico: o c'e' la nuova, o resta la vecchia."""
    stamp = now or _now()
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM pipeline_activity WHERE kind = 'pr'")
            for pr in prs or []:
                number = pr.get("pr")
                conn.execute(
                    """
                    INSERT INTO pipeline_activity
                      (key, kind, role, indicator, stage, run_id, pr, branch, ci, mergeable, title, updated_at)
                    VALUES (?, 'pr', ?, ?, '', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"pr:{number}", pr.get("role", ""), pr.get("indicator", ""),
                     pr.get("run_id", ""), number, pr.get("branch", ""),
                     pr.get("ci", ""), pr.get("mergeable", ""), pr.get("title", ""), stamp),
                )
    finally:
        conn.close()


def record_tokens(run_id, tokens, indicator="", stage="", role="", now=None):
    """Il consumo token di una run, chiavato sul suo `run_id`. Idempotente:
    l'ultimo POST vince (il lanciatore riporta il totale una volta a chiusura,
    ma se ripete non si somma due volte)."""
    if not run_id:
        raise ValueError("run_id mancante")
    try:
        n = int(tokens)
    except (TypeError, ValueError):
        raise ValueError("tokens non numerico")
    stamp = now or _now()
    conn = _connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO pipeline_tokens (run_id, indicator, stage, role, tokens, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                  tokens=excluded.tokens, indicator=excluded.indicator,
                  stage=excluded.stage, role=excluded.role, updated_at=excluded.updated_at
                """,
                (run_id, indicator, stage, role, n, stamp),
            )
    finally:
        conn.close()


def tokens_by_run():
    """Il consumo token per run_id, `{run_id: {tokens, indicator, stage, role, since}}`.

    Durevole: **non** filtrato dalla finestra di freschezza, a differenza di
    `live()`. Tollerante di una tabella non ancora creata (niente token = mappa
    vuota, il cruscotto non deve cadere per la telemetria)."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT run_id, tokens, indicator, stage, role, updated_at FROM pipeline_tokens"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    return {run_id: {"tokens": tokens, "indicator": indicator, "stage": stage,
                     "role": role, "since": updated_at}
            for run_id, tokens, indicator, stage, role, updated_at in rows}


def live(now=None, stale_hours=STALE_HOURS):
    """Le righe vive: battiti e PR piu' recenti della soglia. `{beats, prs}`.

    Tollerante di una tabella che non esiste ancora (il DB puo' non essere mai
    stato scritto su una macchina appena avviata): in quel caso, niente vivo."""
    ref = now or _now()
    cutoff = _cutoff(ref, stale_hours)
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT kind, role, indicator, stage, run_id, pr, branch, ci, mergeable, title, updated_at "
            "FROM pipeline_activity WHERE updated_at >= ? ORDER BY updated_at DESC",
            (cutoff,),
        ).fetchall()
    except sqlite3.OperationalError:
        return {"beats": [], "prs": []}
    finally:
        conn.close()
    beats, prs = [], []
    for kind, role, indicator, stage, run_id, pr, branch, ci, mergeable, title, updated_at in rows:
        item = {"role": role, "indicator": indicator, "stage": stage, "run_id": run_id,
                "pr": pr, "branch": branch, "ci": ci, "mergeable": mergeable,
                "title": title, "since": updated_at}
        (prs if kind == "pr" else beats).append(item)
    return {"beats": beats, "prs": prs}
