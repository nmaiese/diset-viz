"""Migrazione una-tantum: lo stato mutabile da SQLite a Postgres (Supabase).

Si lancia UNA volta, quando si accende Supabase, PRIMA di rimuovere Litestream:
finche' il bucket GCS c'e', le righe sono recuperabili; una volta tolto
Litestream, il prossimo deploy le renderebbe irraggiungibili.

Sequenza:
  1. scarica lo SQLite corrente da GCS (fuori da qui, con gsutil):
       gsutil cp gs://nil-automata-diset-viz-leaderboard/leaderboard <file>.sqlite3
  2. DATABASE_URL=<pooler Supabase>  .venv/bin/python \
       scripts/migrate_leaderboard_to_postgres.py --source <file>.sqlite3
  3. confronta i conteggi riga stampati.

Legge la sorgente con sqlite3 grezzo (nessuna assunzione sullo schema vecchio,
che non ha `user_id`), scrive la destinazione con l'ORM (lo stesso di app/). Si
rifiuta se la destinazione ha gia' righe in `scores`, salvo `--force`.
"""

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import session_scope
from app.models import PipelineActivity, PipelineToken, Score


def _rows(conn, table, columns):
    try:
        cur = conn.execute(f"SELECT {', '.join(columns)} FROM {table}")
    except sqlite3.OperationalError:
        return []  # tabella assente nella sorgente: niente da migrare
    return [dict(zip(columns, r)) for r in cur.fetchall()]


def migrate(source_path, force=False):
    src = sqlite3.connect(source_path)
    try:
        scores = _rows(src, "scores", ["mode", "session_id", "nickname", "score", "detail", "created_at"])
        activity = _rows(src, "pipeline_activity",
                         ["key", "kind", "role", "indicator", "stage", "run_id", "pr",
                          "branch", "ci", "mergeable", "title", "updated_at"])
        tokens = _rows(src, "pipeline_tokens",
                       ["run_id", "indicator", "stage", "role", "tokens", "updated_at"])
    finally:
        src.close()

    with session_scope() as s:
        existing = s.query(Score).count()
        if existing and not force:
            print(f"RIFIUTO: la destinazione ha gia' {existing} righe in scores. "
                  f"Usa --force per procedere comunque.", file=sys.stderr)
            return 1
        for r in scores:
            r.setdefault("user_id", None)  # lo schema vecchio non ha user_id
            s.add(Score(**r))
        for r in activity:
            s.add(PipelineActivity(**r))
        for r in tokens:
            s.merge(PipelineToken(**r))

    with session_scope() as s:
        print(f"scores:            sorgente {len(scores):>5}  ->  destinazione {s.query(Score).count():>5}")
        print(f"pipeline_activity: sorgente {len(activity):>5}  ->  destinazione {s.query(PipelineActivity).count():>5}")
        print(f"pipeline_tokens:   sorgente {len(tokens):>5}  ->  destinazione {s.query(PipelineToken).count():>5}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="path allo SQLite scaricato da GCS")
    ap.add_argument("--force", action="store_true", help="scrivi anche se scores non e' vuota")
    args = ap.parse_args()
    return migrate(args.source, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
