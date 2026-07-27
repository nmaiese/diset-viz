#!/usr/bin/env python3
"""Il dispatcher: quale stadio tocca adesso, e uno solo.

Sostituisce sei cron con un battito. Prima ogni stadio aveva la sua Routine e il
suo giorno, e la catena aveva un problema che nessun singolo stadio poteva
vedere: **le dipendenze sono di dato e la schedulazione era di calendario**. Il
curatore girava il giovedi'. Se il promotore aveva prodotto il venerdi' prima,
il curatore aspettava sei giorni; se non aveva prodotto niente, il curatore
girava a vuoto e apriva una pull request che diceva "niente da fare". Dalla
fonte alla pagina passavano fino a tre settimane, e ogni passaggio era un tiro
di dado sul fatto che a monte ci fosse qualcosa.

L'altro guasto era peggiore: **due stadi potevano girare insieme**. Nessuno
aspettava nessuno, tutti partivano da master, e tutti scrivevano nei registri
condivisi. Il conflitto era la norma, non l'eccezione, al punto che il contratto
degli agenti conteneva una sezione dedicata a come risolverlo a mano.

Quel secondo guasto adesso e' chiuso da due parti. Gli store a un file per
record (`content/indicators/`, `data/pipeline/runs/`,
`data/pipeline/verifiche/`) tolgono il conflitto di contenuto, e questo file
toglie la concorrenza: **un tick, uno stadio**. Non serve un lock e non serve
un lease, perche' non c'e' mai un secondo scrittore.

## Come lo decide

Legge le code con `pipeline_status.queue_sizes()` e prende il primo stadio con
lavoro **in ordine di catena**, che e' anche l'ordine in cui il lavoro si
propaga: uno stadio a monte che ha qualcosa da fare vale piu' di uno a valle,
perche' quello che produce diventa la coda del prossimo.

Uno stadio con la coda non calcolabile (`None`) conta come stadio con lavoro,
per la stessa ragione per cui lo fa `pipeline_status`: chi chiama non sa
distinguere "niente da fare" da "nessuno ha contato", e mandarcelo costa una run
mentre saltarlo costa un buco silenzioso.

## Perche' rifiuta anche quando ci sarebbe lavoro

Perche' una pull request aperta e' una run ancora in corso. Se lo scrittore ha
una pull request in attesa dei check e il dispatcher lancia il revisore, i due
lavorano sullo stesso store degli articoli partendo da due basi diverse, e la
seconda a fondersi trova un master che non aveva davanti. Con
`--check-open-prs` il dispatcher lo verifica su GitHub e, se trova una pull
request della catena ancora aperta, non lancia niente e lo scrive.

Senza `gh`, o senza rete, il controllo non e' possibile: lo dice e lascia
decidere, invece di fingere che non ci sia nessuna pull request aperta. Un
controllo che passa perche' non ha potuto girare e' il difetto che il cancello
di questa catena esiste per non avere.

## Che cosa fa, e che cosa non fa

Non lancia l'agente. Non puo': un agente e' una sessione Claude Code, e questo
e' uno script Python di stdlib. Dice **quale** lanciare, con il suo file di
definizione e il suo `run_id` gia' coniato, e il prompt della Routine fa il
resto. La divisione e' voluta e vale la pena scriverla: la decisione e'
deterministica e verificabile da un test, l'esecuzione no.

    python3 scripts/pipeline_dispatch.py               # chi tocca, leggibile
    python3 scripts/pipeline_dispatch.py --json        # per il prompt della Routine
    python3 scripts/pipeline_dispatch.py --check-open-prs
    python3 scripts/pipeline_dispatch.py --json --record   # e registra il tick

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

from scripts import pipeline_log, pipeline_status  # noqa: E402  (path bootstrap above)

# L'ordine della catena, che e' anche l'ordine di precedenza. Preso da
# `pipeline_status` invece che ricopiato: due elenchi di stadi in due file sono
# due elenchi che divergono, e questo repo ha gia' pagato una volta per una
# regola ricopiata invece che indicata.
STAGE_ORDER = pipeline_status.STAGE_ORDER
AGENT_OF = pipeline_status.AGENT_OF


def _run(argv, cwd=None):
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def open_chain_prs(runner=_run, cwd=None):
    """Le pull request della catena ancora aperte. Ritorna (stato, elenco).

    Lo stato e' `"letto"` quando la risposta e' vera, `"ignoto"` quando non si
    e' potuto chiedere. Tenerli distinti e' tutto il punto: un elenco vuoto
    perche' non ci sono pull request aperte e un elenco vuoto perche' `gh` non
    esiste portano a decisioni opposte.
    """
    try:
        from scripts import pipeline_merge

        slug = pipeline_merge.repo_slug(runner=runner, cwd=cwd)
        ok, data = pipeline_merge.api(
            f"repos/{slug}/pulls?state=open&per_page=100", runner=runner, cwd=cwd
        )
    except (OSError, RuntimeError):
        return "ignoto", []
    if not ok or not isinstance(data, list):
        return "ignoto", []
    prs = []
    for row in data:
        branch = ((row.get("head") or {}).get("ref") or "")
        if branch.startswith("automation/"):
            prs.append({"number": row.get("number"), "branch": branch,
                        "title": row.get("title") or ""})
    return "letto", prs


def decide(queues=None, open_prs=None, pr_state="non-controllato"):
    """Quale stadio lanciare. Sempre un dizionario, mai un'eccezione.

    Separata dall'IO perche' e' la parte che va provata: le code e le pull
    request arrivano da fuori, cosi' un test costruisce lo stato che gli serve
    senza toccare git, GitHub o il catalogo.
    """
    queues = pipeline_status.queue_sizes() if queues is None else queues

    if pr_state == "letto" and open_prs:
        first = open_prs[0]
        return {
            "stage": None,
            "agent": None,
            "reason": (
                f"una run della catena e' ancora in corso: PR #{first['number']} "
                f"su {first['branch']}. Un secondo stadio partirebbe da una base che la "
                f"prima non ha ancora fuso."
            ),
            "waiting": None,
            "queues": queues,
            "open_prs": open_prs,
            "pr_state": pr_state,
        }

    for stage in STAGE_ORDER:
        waiting = queues.get(stage)
        if waiting is None or waiting:
            counted = "coda non calcolabile, ci si va a vedere" if waiting is None \
                else f"{waiting} in coda"
            return {
                "stage": stage,
                "agent": AGENT_OF[stage],
                "reason": f"primo stadio con lavoro in ordine di catena, {counted}",
                "waiting": waiting,
                "queues": queues,
                "open_prs": open_prs or [],
                "pr_state": pr_state,
                "run_id": pipeline_log.new_run_id(stage),
            }

    return {
        "stage": None,
        "agent": None,
        "reason": "tutte le code sono vuote: non c'e' niente da lanciare",
        "waiting": 0,
        "queues": queues,
        "open_prs": open_prs or [],
        "pr_state": pr_state,
    }


def record_tick(plan):
    """Registra il tick nel diario, anche quando non lancia niente.

    E' la riga che rende misurabile il silenzio della catena. Prima l'attesa
    era scritta in `pipeline_log.WATCH_GROUPS`, che ricopiava il cron delle
    Routine cloud, cioe' una promessa che nessuno poteva verificare e che
    sarebbe andata fuori sincrono alla prima modifica della schedulazione. Il
    battito del dispatcher e' la stessa informazione, ma misurata invece che
    dichiarata.
    """
    stage = plan.get("stage")
    summary = (f"lanciato {stage} ({plan['agent']})" if stage
               else f"nessun lancio: {plan['reason']}")
    return pipeline_log.append(pipeline_log.build_entry(
        "dispatch",
        "pr-open" if stage else "nothing",
        summary,
        detail=[plan["reason"]],
        trigger="dispatch",
        queue_before=plan.get("waiting"),
    ))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Quale stadio della catena tocca adesso, e uno solo.",
        epilog="uscita 0 = c'e' uno stadio da lanciare, 1 = non c'e' niente da fare.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-open-prs", action="store_true",
                        help="non lanciare niente se una run della catena e' ancora aperta")
    parser.add_argument("--record", action="store_true",
                        help="scrivi il tick nel diario (lo fa la Routine, non una prova a mano)")
    args = parser.parse_args(argv)

    pr_state, open_prs = "non-controllato", []
    if args.check_open_prs:
        pr_state, open_prs = open_chain_prs()

    plan = decide(open_prs=open_prs, pr_state=pr_state)
    if args.record:
        # Il tick ha un `run_id` suo, che descrive la decisione. Quello dentro
        # `plan` descrive la run che lo stadio dovra' registrare, ed e' un'altra
        # cosa: confonderli farebbe apparire il lancio e il lanciato come una
        # run sola.
        record_tick(plan)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["stage"] else 1

    if plan["stage"]:
        print(f"tocca a: {plan['stage']}  (agente {plan['agent']})")
        print(f"  perche': {plan['reason']}")
        print(f"  run_id:  {plan['run_id']}")
    else:
        print(f"niente da lanciare: {plan['reason']}")
    if pr_state == "ignoto":
        print("  ATTENZIONE: non ho potuto chiedere a GitHub quali PR sono aperte. "
              "La decisione qui sopra non tiene conto delle run in corso.")
    print()
    for stage in STAGE_ORDER:
        waiting = plan["queues"].get(stage)
        shown = "?" if waiting is None else str(waiting)
        mark = ">" if stage == plan["stage"] else " "
        print(f"  {mark} {stage:13s} {shown:>4s} in coda")
    return 0 if plan["stage"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
