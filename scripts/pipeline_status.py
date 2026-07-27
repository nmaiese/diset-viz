#!/usr/bin/env python3
"""One question, one answer: what does the chain have to do next?

Every stage of the pipeline already owns a deterministic queue computed from
committed files, which is what lets a scheduled agent start cold and still know
its work. What was missing is the view *across* those queues. Without it each
agent can see its own inbox and nothing else, so nobody can tell whether the
chain is idle because it is finished or idle because it is stuck two stages
upstream, and a human asking "how is it going" has to run six commands and hold
the answer in their head.

This is that view. It reads the same files the agents read, adds no state of its
own, and answers for every stage: how much is waiting, and what the next action
is.

    python3 scripts/pipeline_status.py              # la catena, stadio per stadio
    python3 scripts/pipeline_status.py --json       # per un agente
    python3 scripts/pipeline_status.py --stage writer

Two halves, on purpose. The queues that read CSVs are **pure stdlib**, so a
cloud agent can run this as its first command, before it has a venv. The two
that need the app view model (the whole-catalogue editorial state, and the
reading order) degrade to a stated "non calcolabile senza il venv" rather than
crashing: a status command that fails on a fresh checkout would be useless
exactly when it is needed most.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import curate, discovery, pending_notes  # noqa: E402

CANDIDATES = PROJECT_ROOT / "data" / "discovery" / "candidates.csv"
SOURCE_CANDIDATES = PROJECT_ROOT / "data" / "discovery" / "source_candidates.csv"

# The order is the chain. Printing them in any other order would invite reading
# a downstream idle queue as "nothing to do" when the reason is upstream.
STAGE_ORDER = ["scout", "hunter", "promoter", "curator", "writer", "reviewer",
               "verificatore"]

AGENT_OF = {
    "scout": "source-scout",
    "hunter": "indicator-hunter",
    "promoter": "indicator-hunter",
    "curator": "indicator-curator",
    "writer": "indicator-writer",
    "reviewer": "indicator-reviewer",
    "verificatore": "indicator-verifier",
}


def _rows(path):
    return discovery.read_semicolon(path) if path.exists() else []


def scout_stage():
    rows = _rows(SOURCE_CANDIDATES)
    waiting = [r for r in rows if (r.get("triage_status") or "new") == "new"]
    approved = [r for r in rows if r.get("triage_status") == "approved"]
    return {
        "stage": "scout",
        "waiting": len(waiting),
        "detail": {"da_valutare": len(waiting), "approvate_da_cablare": len(approved)},
        "next": (
            f"valutare {len(waiting)} dataflow proposti per l'allowlist"
            if waiting else "nessuna proposta di fonte da valutare"
        ),
        "command": "python3 scripts/scout_sources.py",
    }


def hunter_stage():
    rows = _rows(CANDIDATES)
    fresh = [r for r in rows if (r.get("triage_status") or "new") == "new"]
    return {
        "stage": "hunter",
        "waiting": len(fresh),
        "detail": {
            "in_coda": len(rows),
            "da_decidere": len(fresh),
            "rimandati": sum(1 for r in rows if r.get("triage_status") == "needs-info"),
        },
        "next": (
            f"decidere il triage di {len(fresh)} candidati"
            if fresh else "watchlist esaurita, nessun candidato da decidere"
        ),
        "command": "python3 scripts/discover_candidates.py --source <fonte>",
    }


def promoter_stage():
    rows = _rows(CANDIDATES)
    approved = [r for r in rows if r.get("triage_status") == "approved"]
    return {
        "stage": "promoter",
        "waiting": len(approved),
        "detail": {"approvati": len(approved)},
        "next": (
            f"promuovere {len(approved)} candidati nel layer esterno"
            if approved else "nessun candidato approvato in attesa"
        ),
        "command": "python3 scripts/promote_candidates.py",
    }


def curator_stage():
    try:
        queue = curate.worklist()
    except FileNotFoundError:
        queue = {"new": [], "recheck": []}
    waiting = len(queue["new"]) + len(queue["recheck"])
    if queue["new"]:
        nxt = f"curare {len(queue['new'])} indicatori mai visti"
        if queue["recheck"]:
            nxt += f", e riconfermarne {len(queue['recheck'])}"
    elif queue["recheck"]:
        nxt = f"riconfermare {len(queue['recheck'])} versi giudicati su dati piu vecchi"
    else:
        nxt = "ogni indicatore esterno e curato sull'anno corrente"
    return {
        "stage": "curator",
        "waiting": waiting,
        "detail": {
            "mai_curati": len(queue["new"]),
            "da_riconfermare": len(queue["recheck"]),
            "riconferme": [item["target"] for item in queue["recheck"]][:10],
        },
        "next": nxt,
        "command": "python3 scripts/curate.py --include-recheck",
    }


def writer_stage():
    missing, stale = pending_notes.build_worklist()
    backlog = _catalogue_editorial_state()
    waiting = len(missing) + len(stale)
    if missing or stale:
        nxt = f"scrivere {len(missing)} articoli e aggiornarne {len(stale)}"
    elif backlog.get("incomplete"):
        nxt = f"lavorare l'arretrato: {backlog['incomplete']} pagine ancora composte dal template"
    else:
        nxt = "nessun articolo da scrivere"
    return {
        "stage": "writer",
        "waiting": waiting,
        "detail": {
            "da_scrivere": len(missing),
            "da_aggiornare": len(stale),
            "arretrato_catalogo": backlog,
        },
        "next": nxt,
        "command": "python3 scripts/pending_notes.py",
    }


def reviewer_stage():
    state = _reading_order()
    waiting = state.get("da_leggere")
    if waiting is None:
        nxt = "non calcolabile senza il venv dell'app"
    elif state.get("riletture"):
        nxt = (
            f"rileggere {state['riletture']} articoli le cui cifre sono cambiate dopo la firma, "
            f"poi {waiting - state['riletture']} mai letti"
        )
    elif waiting:
        nxt = f"leggere {waiting} articoli, in ordine di rischio"
    else:
        nxt = "ogni articolo e stato letto contro i dati correnti"
    return {
        # `None`, mai `0`. La coda del revisore e' l'unica che serve il venv
        # dell'app per essere contata, e riportare zero quando la risposta e'
        # "non lo so" rende le due indistinguibili: un orchestratore che legge
        # `next_stage` salterebbe il revisore per sempre su un checkout senza
        # venv, in silenzio. E' lo stesso difetto del diario che non vedeva la
        # differenza fra una Routine a vuoto e una mai partita.
        "stage": "reviewer",
        "waiting": waiting,
        "detail": state,
        "next": nxt,
        "command": ".venv/bin/python -m scripts.review_queue",
    }


def _catalogue_editorial_state():
    """The whole-catalogue editorial backlog, when the app is importable.

    `pending_notes` only sees indicators the external manifest tracks, which is
    the discovery chain's hand-off and nothing else. The writer also owns 600+
    pages whose sections the template is still composing, and that number is the
    difference between "the chain is idle" and "the chain is idle and there are
    650 pages waiting".
    """
    try:
        from scripts import text_queue
    except Exception:
        return {"disponibile": False, "motivo": "serve il venv dell'app"}
    try:
        rows = text_queue.build_queue()
    except Exception as exc:
        return {"disponibile": False, "motivo": f"{type(exc).__name__}"}
    complete = sum(1 for row in rows if row.get("written") == 4)
    return {
        "disponibile": True,
        "pagine": len(rows),
        "complete": complete,
        "incomplete": len(rows) - complete,
        "vintage_arretrato": sum(1 for row in rows if row.get("stale")),
    }


def _reading_order():
    try:
        from scripts import review_queue
    except Exception:
        return {"disponibile": False, "da_leggere": None, "motivo": "serve il venv dell'app"}
    try:
        rows = review_queue.build_queue()
    except Exception as exc:
        return {"disponibile": False, "da_leggere": None, "motivo": f"{type(exc).__name__}"}
    pending = [row for row in rows if not row["reviewed_at"]]
    return {
        "disponibile": True,
        "scritti": len(rows),
        "firmati": len(rows) - len(pending),
        "da_leggere": len(pending),
        "riletture": sum(1 for row in pending if "rilettura" in row["flags"]),
    }


def verificatore_stage():
    """Di quello che il revisore ha firmato, cosa nessuno ha provato a smentire.

    Ultimo della catena e non per modo di dire: e' lo stadio che misura lo stadio
    prima. Una firma e' la parola del revisore sul lavoro del revisore, e finche'
    nessuno provava a farla cadere il numero che diceva quanto valesse non
    esisteva. Adesso esiste, ed e' 7 smentite su 529 affermazioni.
    """
    try:
        from scripts import verification_queue
    except Exception as exc:  # pragma: no cover - solo senza il repo completo
        return {
            "stage": "verificatore",
            "waiting": 0,
            "detail": {"disponibile": False, "motivo": f"{type(exc).__name__}"},
            "next": "coda non calcolabile",
            "command": "python3 scripts/verification_queue.py",
        }
    rows = verification_queue.build_queue()
    summary = verification_queue.summarize(rows)
    waiting = summary["da_verificare"]
    aperte = summary["smentite_aperte"]
    if aperte:
        # Prima di verificarne altri: una smentita aperta e' una frase falsa in
        # pagina, e l'unico stadio che puo' chiuderla e' il revisore.
        nxt = (f"{aperte} smentite aperte da chiudere, tocca al revisore, "
               f"poi {waiting} articoli da verificare")
    elif summary["riverificare"]:
        nxt = (f"riverificare {summary['riverificare']} articoli riscritti dopo la verifica, "
               f"poi {waiting - summary['riverificare']} mai verificati")
    elif waiting:
        nxt = f"provare a smentire {waiting} articoli firmati e mai verificati"
    else:
        nxt = "ogni articolo firmato e' stato verificato sul testo di adesso"
    return {
        "stage": "verificatore",
        "waiting": waiting,
        "detail": summary,
        "next": nxt,
        "command": "python3 scripts/verification_queue.py",
    }


BUILDERS = {
    "scout": scout_stage,
    "hunter": hunter_stage,
    "promoter": promoter_stage,
    "curator": curator_stage,
    "writer": writer_stage,
    "reviewer": reviewer_stage,
    "verificatore": verificatore_stage,
}


def queue_sizes(stages=None):
    """`{stadio: quanti in attesa}`, con None dove la coda non si e' contata.

    La forma piu' piccola dello stato, per chi deve solo decidere. La usano il
    dispatcher, per scegliere lo stadio da lanciare, e `pipeline_log.silence`,
    per non segnalare fermo uno stadio che tace perche' non ha niente da fare.
    """
    return {entry["stage"]: entry["waiting"] for entry in build_status(stages)["stages"]}


def build_status(stages=None):
    wanted = stages or STAGE_ORDER
    report = [BUILDERS[name]() for name in wanted]
    for entry in report:
        entry["agent"] = AGENT_OF[entry["stage"]]
    unknown = [e["stage"] for e in report if e["waiting"] is None]
    return {
        "stages": report,
        # The first stage with work is where a human should look, and where an
        # orchestrator should start. An empty chain says so explicitly rather
        # than leaving the reader to scan six zeroes.
        #
        # A stage whose queue could not be counted (`waiting: None`) counts as
        # work, not as done. Skipping it would be the quiet failure this whole
        # file exists to prevent: the caller cannot tell "nothing to do" from
        # "nobody counted", so the answer that costs least is to send it there
        # and let it find out.
        "next_stage": next(
            (e["stage"] for e in report if e["waiting"] is None or e["waiting"]), None
        ),
        "total_waiting": sum(e["waiting"] or 0 for e in report),
        # Reported, not folded into the total: a sum that silently omits a term
        # is a wrong number, a sum that names what it left out is a partial one.
        "unknown_stages": unknown,
    }


def main():
    parser = argparse.ArgumentParser(description="Lo stato della catena, stadio per stadio.")
    parser.add_argument("--stage", choices=STAGE_ORDER, help="un solo stadio")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    status = build_status([args.stage] if args.stage else None)
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0

    print("Catena Divario Italia, stato per stadio\n")
    for entry in status["stages"]:
        waiting = entry["waiting"]
        mark = "?" if waiting is None else ("." if not waiting else "*")
        shown = "?" if waiting is None else str(waiting)
        print(f" {mark} {entry['stage']:9s} {entry['agent']:19s} in attesa: {shown:<5s} {entry['next']}")
    print()
    if status["unknown_stages"]:
        print("Code non contate (il totale le esclude): "
              + ", ".join(status["unknown_stages"]))
    if status["next_stage"]:
        first = next(e for e in status["stages"] if e["stage"] == status["next_stage"])
        print(f"Prossimo passo: {first['agent']} -> {first['command']}")
    else:
        print("Niente in coda: la catena e ferma perche ha finito, non perche e bloccata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
