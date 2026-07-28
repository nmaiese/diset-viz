#!/usr/bin/env python3
"""Il monitoraggio della catena, una vista di lettura sul dossier per-indicatore.

Non e' un sottosistema a parte con un secondo modello di stato: e' una vista
sullo **stesso** dossier che `practice_timeline` ricostruisce dagli artefatti
committati, promosso qui a sorgente unica del monitoraggio. La domanda che
risponde e' quella che prima costava sette comandi e una testa che li teneva
insieme: **dov'e' fermo, e perche'**.

Tre cose, tutte derivate dal dossier (piu' il diario per la storia recente e i
battiti di sessione per il vivo):

- **la frase in testa**: "2 indicatori bloccati: ter-X smentita aperta da 2
  giorni, dem-Y aspetta il produttore da 5". Non una tabella da interpretare.
- **una riga per indicatore**: stato, da quando, prossimo ruolo, priorita'.
- **le sessioni in volo adesso**, dai battiti che ogni ruolo lascia all'avvio
  (best effort: se un ruolo non ha battuto, il vivo tace, il committato no).

Il nucleo (`board`, `headline`) e' puro: prende i dati gia' letti e non tocca il
disco, cosi' un test lo prova con un dossier sintetico. La CLI e la rotta Flask
`/_pipeline` collegano i lettori reali. Stdlib puro come il resto della catena.

    python3 scripts/pipeline_monitor.py            # dov'e' fermo, in una schermata
    python3 scripts/pipeline_monitor.py --json      # per la rotta o un altro programma
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_launch, practice_model, practice_timeline  # noqa: E402

# Il registro dei battiti: un file per run in volo, ignorato da git (e' vivo, non
# storia). Ogni ruolo lo scrive all'avvio e lo cancella alla chiusura; un battito
# piu' vecchio della soglia si considera morto (una sessione caduta senza pulire).
HEARTBEATS_DIR = PROJECT_ROOT / "data" / "pipeline" / "heartbeats"
HEARTBEAT_STALE_HOURS = 6

# Stati che sono un "fermo" da mettere in testa, con la ragione leggibile.
STUCK_STATES = {
    "bloccata": "ferma, aspetta un cambio esterno",
    "invalidata": "un input e' cambiato, i passaggi a valle non valgono piu'",
    "in-quarantena": "bloccata terminale, tolta dalla coda",
}


def _reason(d: dict) -> str:
    """Perche' un indicatore e' dov'e', in una riga leggibile, dalle bandiere."""
    f = d.get("flags") or {}
    if f.get("open_smentita"):
        return "smentita aperta, una frase falsa in pagina"
    if f.get("needs_info"):
        return "rimandata: aspetta un chiarimento o un cambio alla fonte"
    if f.get("stale_vintage"):
        return "le cifre dell'articolo sono cambiate dopo la firma"
    if f.get("stale_curation"):
        return "la fonte ha pubblicato un anno nuovo, la curatela e' scaduta"
    return STUCK_STATES.get(d.get("state"), d.get("state") or "")


def _days(start: str, today: str) -> int:
    return practice_model._days_between(start, today) if start and today else 0


def row_of(d: dict, today: str = "") -> dict:
    """La riga di monitoraggio di un indicatore, dal suo dossier."""
    stage = practice_timeline.ready_stage(d)
    return {
        "id": d["id"],
        "state": d.get("state", ""),
        "entered_at": d.get("entered_at", ""),
        "days": _days(d.get("entered_at", ""), today),
        "next_role": pipeline_launch.ROLE_OF_STAGE.get(stage) if stage else None,
        "priority": round(float(d.get("priority", 0.0) or 0.0), 1),
        "error_class": d.get("error_class"),
        "flags": sorted(k for k, v in (d.get("flags") or {}).items() if v is True),
        "reason": _reason(d),
    }


def headline(rows: list, today: str = "") -> str:
    """La frase in testa: dov'e' fermo, e perche'. Dai soli `rows` gia' calcolati."""
    stuck = [r for r in rows if r["state"] in STUCK_STATES]
    if stuck:
        stuck.sort(key=lambda r: (-r["days"], r["id"]))
        parts = []
        for r in stuck[:3]:
            when = f" da {r['days']} giorni" if r["days"] else ""
            parts.append(f"{r['id']} {r['reason']}{when}")
        more = f", e altri {len(stuck) - 3}" if len(stuck) > 3 else ""
        n = len(stuck)
        return (f"{n} indicatore bloccato: " if n == 1 else f"{n} indicatori bloccati: ") \
            + "; ".join(parts) + more
    ready = [r for r in rows if r["next_role"]]
    if ready:
        top = ready[0]
        return (f"{len(ready)} indicatori pronti al lavoro, niente e' bloccato. "
                f"Il piu' urgente: {top['id']} -> {top['next_role']}.")
    return "catena in pari: nessun indicatore bloccato, niente in coda."


def board(dossier: dict, runs=None, heartbeats=None, today: str = "",
          recent: int = 12) -> dict:
    """Il cruscotto intero, dai soli artefatti gia' letti. Puro.

    `dossier` e' l'uscita di `practice_timeline`. `runs` sono le run gia'
    collassate (`pipeline_log.collapse_runs`), per la storia recente.
    `heartbeats` sono i battiti vivi. Ritorna la frase in testa, le righe per
    indicatore, i fermi, il vivo, la storia recente e i totali per stato.
    """
    rows = [row_of(d, today) for d in dossier.values()]
    rows.sort(key=lambda r: (-r["priority"], -r["days"], r["id"]))

    totals: dict = {}
    for r in rows:
        totals[r["state"]] = totals.get(r["state"], 0) + 1

    recent_runs = sorted((runs or []), key=lambda run: run.get("at", ""), reverse=True)[:recent]

    return {
        "headline": headline(rows, today),
        "totals": totals,
        "stuck": [r for r in rows if r["state"] in STUCK_STATES],
        "ready": [r for r in rows if r["next_role"]],
        "rows": rows,
        "in_flight": sorted(heartbeats or [], key=lambda h: h.get("since", "")),
        "recent": [{"at": run.get("at", ""), "stage": run.get("stage", ""),
                    "outcome": run.get("outcome", ""), "summary": run.get("summary", ""),
                    "run_id": run.get("run_id", "")} for run in recent_runs],
        "generated_for": today,
    }


# --- i battiti: il vivo, best effort ----------------------------------------

def write_heartbeat(role: str, run_id: str, indicator: str = "", root=None,
                    now: str = "") -> Path:
    """Un ruolo che parte lascia un battito: chi lavora su cosa, da quando.

    File per run (il `run_id` e' unico), cosi' due ruoli in volo insieme non si
    sovrascrivono. Ignorato da git: e' vivo, non storia. `now` iniettabile per i
    test (niente `datetime.now` nel nucleo)."""
    from datetime import datetime, timezone
    base = Path(root or HEARTBEATS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    beat = {"role": role, "run_id": run_id, "indicator": indicator,
            "since": now or datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path = base / f"{run_id}.json"
    path.write_text(json.dumps(beat, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def clear_heartbeat(run_id: str, root=None) -> None:
    """Un ruolo che chiude cancella il proprio battito."""
    path = Path(root or HEARTBEATS_DIR) / f"{run_id}.json"
    try:
        path.unlink()
    except OSError:
        pass


def read_heartbeats(root=None, now: str = "", stale_hours: int = HEARTBEAT_STALE_HOURS) -> list:
    """I battiti vivi: quelli piu' vecchi della soglia si scartano (sessione
    caduta senza pulire). `now` iniettabile per i test."""
    from datetime import datetime, timezone
    base = Path(root or HEARTBEATS_DIR)
    if not base.is_dir():
        return []
    ref = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for path in sorted(base.glob("*.json")):
        try:
            beat = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if practice_model._days_between(beat.get("since", "")[:10], ref[:10]) * 24 > stale_hours \
                and beat.get("since", "")[:10] != ref[:10]:
            continue
        out.append(beat)
    return out


def load_board(today: str = "", proofs_root=None, recent: int = 12) -> dict:
    """Collega i lettori reali (tutti stdlib puri) e ritorna il cruscotto."""
    from datetime import datetime, timezone
    from scripts import pipeline_log
    ref = today or datetime.now(timezone.utc).date().isoformat()
    dossier = practice_timeline.load_real(today=ref, proofs_root=proofs_root)
    runs = pipeline_log.collapse_runs(pipeline_log.read_journal())
    heartbeats = read_heartbeats(now=ref)
    return board(dossier, runs=runs, heartbeats=heartbeats, today=ref, recent=recent)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dov'e' fermo la catena, e perche'.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--today", default="", help="data di riferimento YYYY-MM-DD")
    parser.add_argument("--beat-open", nargs=2, metavar=("RUOLO", "RUN_ID"),
                        help="un ruolo che parte lascia il proprio battito (il vivo del cruscotto)")
    parser.add_argument("--beat-close", metavar="RUN_ID",
                        help="un ruolo che chiude cancella il proprio battito")
    parser.add_argument("--indicator", default="",
                        help="l'indicatore su cui batte il ruolo (con --beat-open)")
    args = parser.parse_args(argv)

    # I battiti: due gesti che un agente fa in apertura e chiusura della sua run.
    # Non stampano il cruscotto, aprono/chiudono il vivo e basta.
    if args.beat_open:
        role, run_id = args.beat_open
        path = write_heartbeat(role, run_id, indicator=args.indicator)
        if not args.json:
            print(f"battito aperto: {role} su {args.indicator or '(coda)'} -> {path}")
        return 0
    if args.beat_close:
        clear_heartbeat(args.beat_close)
        if not args.json:
            print(f"battito chiuso: {args.beat_close}")
        return 0

    b = load_board(today=args.today)
    if args.json:
        print(json.dumps(b, ensure_ascii=False, indent=2))
        return 0

    print(b["headline"])
    print()
    print("stato della catena:  " + "  ".join(f"{k}={v}" for k, v in sorted(b["totals"].items())))
    if b["in_flight"]:
        print("\nin volo adesso:")
        for h in b["in_flight"]:
            target = h.get("indicator") or "(coda)"
            print(f"  {h.get('role', ''):12} {target:24.24} da {h.get('since', '')}")
    if b["stuck"]:
        print("\nfermi:")
        for r in b["stuck"]:
            print(f"  {r['id']:28.28} {r['state']:14} {r['reason']}")
    print(f"\n{len(b['rows'])} indicatori. Storia recente: {len(b['recent'])} run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
