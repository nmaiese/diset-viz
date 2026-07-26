#!/usr/bin/env python3
"""Il diario della catena: che cosa ha fatto ogni agente, quando, e come e' finita.

Il problema che risolve. Gli agenti girano in cloud, a freddo, e per tutta la
durata della run non lasciano nessuna traccia: l'unico segno che qualcosa e'
successo arriva alla fine, sotto forma di commit o di pull request. Se una run
non produce niente (coda vuota, cancello che blocca, agente che si ferma a
meta') non resta assolutamente nulla da leggere, e la domanda "che cosa ha fatto
stanotte il revisore" non ha risposta. Peggio: una Routine che gira e non
produce ha lo stesso aspetto di una Routine che non e' mai partita, ed e'
esattamente cosi' che lo scrittore ha lavorato per settimane su un file morto
senza che nessuno se ne accorgesse.

Il diario e' la risposta. Ogni agente, alla fine della run, scrive una riga qui
dentro, **anche quando non ha prodotto niente**, che e' il caso in cui serve di
piu'. Il file e' committato, quindi la storia sopravvive alla sessione che l'ha
creata, ed e' JSON per riga, quindi due run concorrenti non si corrompono a
vicenda come farebbero dentro un JSON unico.

    python3 scripts/pipeline_log.py                    # la timeline
    python3 scripts/pipeline_log.py --stage writer     # un agente solo
    python3 scripts/pipeline_log.py --json

    # quello che scrive un agente alla fine della sua run
    python3 scripts/pipeline_log.py --write \\
        --stage reviewer --outcome merged \\
        --summary "5 articoli riletti, 2 correzioni causali" \\
        --detail "eur-rd_e_gerdreg: tolta la domanda retorica" \\
        --gate auto --pr 42

Stdlib puro come il resto della catena.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

JOURNAL = PROJECT_ROOT / "data" / "pipeline" / "runs.jsonl"

STAGES = ("scout", "hunter", "promoter", "curator", "writer", "reviewer")

# Come e' finita una run. Il vocabolario e' corto di proposito: un campo libero
# si riempirebbe di sinonimi e diventerebbe illeggibile in aggregato.
OUTCOMES = {
    "merged": "fatto e pubblicato",
    "pr-open": "PR aperta, aspetta",
    "blocked": "cancello bloccato",
    "nothing": "niente da fare",
    "stopped": "fermato a meta'",
    "error": "errore",
}

# Quali esiti meritano di essere notati leggendo in fretta. `nothing` non e' un
# problema, e' la risposta giusta quando la coda e' vuota.
ATTENTION = {"blocked", "stopped", "error"}


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args):
    result = subprocess.run(
        ("git",) + args, cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def read_journal(path=None):
    path = Path(path) if path else JOURNAL
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            # Una riga rotta non deve rendere illeggibile tutto il diario: e' un
            # registro, non uno schema, e la riga dopo vale ancora.
            entries.append({"stage": "?", "outcome": "error", "summary": f"riga illeggibile: {line[:80]}"})
    return entries


def append(entry, path=None):
    path = Path(path) if path else JOURNAL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def build_entry(stage, outcome, summary, detail=None, gate=None, pr=None,
                commit=None, branch=None, queue_before=None, queue_after=None):
    if stage not in STAGES:
        raise SystemExit(f"stadio sconosciuto '{stage}'. Noti: {', '.join(STAGES)}")
    if outcome not in OUTCOMES:
        raise SystemExit(f"esito sconosciuto '{outcome}'. Noti: {', '.join(OUTCOMES)}")
    if not branch:
        code, out, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
        branch = out.strip() if code == 0 else ""
    if not commit:
        code, out, _ = _git("rev-parse", "--short", "HEAD")
        commit = out.strip() if code == 0 else ""
    entry = {
        "at": _now(),
        "stage": stage,
        "outcome": outcome,
        "summary": summary,
        "detail": detail or [],
        "gate": gate or "",
        "pr": pr or "",
        "commit": commit,
        "branch": branch,
    }
    if queue_before is not None:
        entry["queue_before"] = queue_before
    if queue_after is not None:
        entry["queue_after"] = queue_after
    return entry


def summarize(entries):
    """Aggregato per stadio: l'ultima run e quante ne meritano attenzione."""
    by_stage = {}
    for entry in entries:
        by_stage.setdefault(entry.get("stage", "?"), []).append(entry)
    out = {}
    for stage, runs in by_stage.items():
        ordered = sorted(runs, key=lambda r: r.get("at", ""))
        out[stage] = {
            "runs": len(ordered),
            "last": ordered[-1],
            "attention": sum(1 for r in ordered if r.get("outcome") in ATTENTION),
        }
    return out


def _print_timeline(entries, limit):
    if not entries:
        print("Il diario e vuoto: nessun agente ha ancora registrato una run.")
        print("Le run precedenti al diario si leggono in git (`git log --oneline`) e nelle PR.")
        return
    shown = sorted(entries, key=lambda r: r.get("at", ""), reverse=True)[:limit]
    print(f"Diario della catena, ultime {len(shown)} run su {len(entries)}\n")
    for entry in shown:
        mark = "!" if entry.get("outcome") in ATTENTION else " "
        when = (entry.get("at") or "")[:16].replace("T", " ")
        outcome = OUTCOMES.get(entry.get("outcome"), entry.get("outcome", "?"))
        print(f"{mark} {when}  {entry.get('stage', '?'):9s} {outcome:22s} {entry.get('summary', '')}")
        for line in entry.get("detail") or []:
            print(f"      - {line}")
        refs = []
        if entry.get("pr"):
            refs.append(f"PR #{entry['pr']}")
        if entry.get("gate"):
            refs.append(f"cancello: {entry['gate']}")
        if entry.get("commit"):
            refs.append(entry["commit"])
        if refs:
            print(f"      {' | '.join(refs)}")
    print()
    for stage in STAGES:
        state = summarize(entries).get(stage)
        if not state:
            print(f"  {stage:9s} mai registrata una run")
            continue
        last = state["last"]
        warn = f"  ({state['attention']} da guardare)" if state["attention"] else ""
        print(f"  {stage:9s} {state['runs']:3d} run, ultima {(last.get('at') or '')[:10]}"
              f" -> {OUTCOMES.get(last.get('outcome'), '?')}{warn}")


def main():
    parser = argparse.ArgumentParser(description="Il diario della catena: chi ha girato, quando, con che esito.")
    parser.add_argument("--stage", choices=STAGES, help="un solo stadio")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    write = parser.add_argument_group("scrittura (la usa l'agente a fine run)")
    write.add_argument("--write", action="store_true", help="aggiunge una riga al diario")
    write.add_argument("--outcome", choices=sorted(OUTCOMES))
    write.add_argument("--summary", help="una riga: che cosa hai fatto")
    write.add_argument("--detail", action="append", default=[], help="ripetibile: una riga per decisione")
    write.add_argument("--gate", help="il campo merge del verdetto del cancello")
    write.add_argument("--pr", help="numero della pull request, se l'hai aperta")
    args = parser.parse_args()

    if args.write:
        if not (args.stage and args.outcome and args.summary):
            raise SystemExit("per scrivere servono --stage, --outcome e --summary")
        entry = append(build_entry(
            args.stage, args.outcome, args.summary,
            detail=args.detail, gate=args.gate, pr=args.pr,
        ))
        print(f"registrato: {entry['stage']} -> {entry['outcome']}")
        return 0

    entries = read_journal()
    if args.stage:
        entries = [e for e in entries if e.get("stage") == args.stage]
    if args.json:
        print(json.dumps({"entries": entries, "by_stage": summarize(entries)},
                         ensure_ascii=False, indent=2))
        return 0
    _print_timeline(entries, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
