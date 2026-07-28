#!/usr/bin/env python3
"""Il lanciatore per-indicatore: che cosa lanciare adesso, e quanto in parallelo.

Sostituisce il dispatcher-scheduler (`pipeline_dispatch.py`). Il dispatcher
serializzava: un tick, uno stadio, e rifiutava di partire finche' una pull
request della catena era aperta. Serviva quando l'unita' di lavoro era lo
**stadio** e sette stadi separati si scrivevano addosso i registri condivisi.
Adesso l'unita' di lavoro e' l'**indicatore**, e tre soli ruoli lo lavorano:

    ammissione (scout+hunter+promoter) -> produttore (curator+writer+reviewer)
    -> verificatore

Indicatori diversi toccano file diversi, quindi non c'e' contesa da
serializzare: il lanciatore non sceglie uno stadio, **elenca** tutto il lavoro
lanciabile, prioritizzato, e chi lo esegue (l'agente lanciatore, o una persona)
ne mette in volo quanti ne vuole in parallelo senza rischio di collisione.

- **Produttore e verificatore sono per-indicatore.** Ogni indicatore pronto e'
  una voce a se', perche' due produttori su due indicatori diversi non si
  toccano. La priorita' e il ruolo vengono dal dossier per-indicatore
  (`practice_timeline`), la stessa logica di `stage_priorities()`: una smentita
  su una pagina online (peso 100) precede una candidatura nuova.
- **L'ammissione e' batch.** Una sessione triaga l'intera coda di fonti e
  candidati e promuove cio' che approva, quindi e' una voce sola. La sua
  esistenza si legge dalle code pre-pratica (`scout`, `hunter`, `promoter`), che
  non sono indicatori nel dossier, piu' le pratiche in stato `proposta`.

Come il dispatcher, non lancia l'agente: un agente e' una sessione Claude Code,
questo e' stdlib puro. Dice **che cosa** lanciare, con ruolo, indicatore e
`run_id` gia' coniato, e l'agente lanciatore fa il resto. La decisione e'
deterministica e verificabile da un test, l'esecuzione no.

    python3 scripts/pipeline_launch.py            # il piano, leggibile
    python3 scripts/pipeline_launch.py --json     # per l'agente lanciatore
    python3 scripts/pipeline_launch.py --top 3    # solo le prime tre voci

Stdlib puro come il resto della catena.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import practice_timeline  # noqa: E402  (path bootstrap above)

# I tre ruoli fusi, e la mappa dal vecchio stadio (che il dossier ancora nomina,
# perche' e' il vocabolario di `ready_stage`) al ruolo che oggi lo copre. Uno
# solo, non ricopiato: se domani un ruolo assorbe un altro stadio, si cambia qui.
ROLE_OF_STAGE = {
    "scout": "admissions",
    "hunter": "admissions",
    "promoter": "admissions",
    "curator": "producer",
    "writer": "producer",
    "reviewer": "producer",
    "verificatore": "verificatore",
}

# L'agente che esegue ogni ruolo. Il verificatore e' rimasto invariato nella
# ri-architettura, quindi conserva il suo file storico.
AGENT_OF_ROLE = {
    "admissions": "admissions",
    "producer": "producer",
    "verificatore": "indicator-verifier",
}

# L'ordine di precedenza dei ruoli, a monte prima, come la catena: rompe solo i
# pari merito di priorita'. Una smentita (priorita' 100) scavalca comunque tutto
# perche' l'ordinamento e' prima sulla priorita'.
ROLE_ORDER = ("admissions", "producer", "verificatore")

# Le code pre-pratica che accendono l'ammissione ma non sono indicatori nel
# dossier: proposte di fonti (scout), candidati da triare (hunter), approvati da
# promuovere (promoter).
ADMISSIONS_QUEUES = ("scout", "hunter", "promoter")


def _admissions_reason(batch, proposte=0):
    labels = {
        "scout": "fonti da valutare",
        "hunter": "candidati da triare",
        "promoter": "approvati da promuovere",
    }
    parts = []
    for stage in ADMISSIONS_QUEUES:
        n = (batch or {}).get(stage)
        if n is None:
            parts.append(f"{labels[stage]}: ?")
        elif n:
            parts.append(f"{labels[stage]}: {n}")
    if proposte:
        parts.append(f"proposte in attesa di promozione: {proposte}")
    return "coda ammissione, " + ", ".join(parts) if parts else "coda ammissione"


def plan_launches(dossier, queues=None, mint=None):
    """La lista prioritizzata di lanci, dai soli artefatti gia' letti.

    `dossier` e' l'uscita di `practice_timeline.reconstruct()`/`load_real()`:
    `{indicator_id: dossier}`. `queues` sono le dimensioni delle code
    (`pipeline_status.queue_sizes()`), da cui si legge il lavoro pre-pratica
    dell'ammissione (le proposte di fonti non sono indicatori). `mint(role)` conia
    il `run_id`, iniettato cosi' il nucleo resta puro e un test lo prova con un
    dossier sintetico e un contatore finto.

    Ritorna una lista di voci di lancio ordinate per priorita' decrescente, ogni
    voce con `role`, `agent`, `indicator` (None per l'ammissione batch), `scope`,
    `priority`, `reason`, `run_id`.
    """
    mint = mint or (lambda role: "")
    queues = queues or {}
    adm_batch = {stage: queues.get(stage) for stage in ADMISSIONS_QUEUES}

    adm_priorities = []
    producer_items, verifier_items = [], []
    for code, d in (dossier or {}).items():
        stage = practice_timeline.ready_stage(d)
        if not stage:
            continue
        role = ROLE_OF_STAGE.get(stage)
        priority = float(d.get("priority", 0.0) or 0.0)
        if role == "admissions":
            adm_priorities.append(priority)          # proposta in attesa del promoter
        elif role == "producer":
            producer_items.append((code, stage, priority))
        elif role == "verificatore":
            verifier_items.append((code, stage, priority))

    launches = []

    # Una coda a monte accende l'ammissione se ha un conteggio positivo, o se e'
    # stata contata e risulta incontabile (`None` esplicito nel dizionario, "vai a
    # vedere"). Una chiave assente e' "nessuna informazione", non "forse lavoro":
    # scout/hunter/promoter sono sempre contabili, quindi None qui e' raro e vero.
    adm_from_queue = any(
        (queues.get(stage) or 0) > 0 or (stage in queues and queues.get(stage) is None)
        for stage in ADMISSIONS_QUEUES
    )
    if adm_from_queue or adm_priorities:
        launches.append({
            "role": "admissions",
            "agent": AGENT_OF_ROLE["admissions"],
            "indicator": None,
            "scope": "batch",
            "priority": max(adm_priorities) if adm_priorities else 0.0,
            "reason": _admissions_reason(adm_batch, len(adm_priorities)),
            "queues": adm_batch,
            "run_id": mint("admissions"),
        })

    for code, stage, priority in producer_items:
        launches.append({
            "role": "producer",
            "agent": AGENT_OF_ROLE["producer"],
            "indicator": code,
            "scope": "indicatore",
            "priority": priority,
            "reason": f"{code} pronto per il produttore (stadio d'ingresso {stage})",
            "run_id": mint("producer"),
        })

    for code, stage, priority in verifier_items:
        launches.append({
            "role": "verificatore",
            "agent": AGENT_OF_ROLE["verificatore"],
            "indicator": code,
            "scope": "indicatore",
            "priority": priority,
            "reason": f"{code} firmato, nessuno ha ancora provato a smentirlo",
            "run_id": mint("verificatore"),
        })

    launches.sort(key=lambda item: (-item["priority"],
                                    ROLE_ORDER.index(item["role"]),
                                    item["indicator"] or ""))
    return launches


def load_plan(today="", proofs_root=None):
    """Collega i lettori reali (tutti stdlib puri) e ritorna il piano di lancio.

    La meta' con l'IO, tenuta fuori da `plan_launches` cosi' il nucleo resta
    provabile senza disco."""
    from scripts import pipeline_log, pipeline_status
    dossier = practice_timeline.load_real(today=today, proofs_root=proofs_root)
    queues = pipeline_status.queue_sizes()
    return plan_launches(dossier, queues, mint=pipeline_log.new_run_id)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Che cosa lanciare adesso nella catena per-indicatore, e in che ordine.",
        epilog="uscita 0 = c'e' lavoro da lanciare, 1 = niente da lanciare.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--top", type=int, default=None,
                        help="mostra solo le prime N voci (le piu' prioritarie)")
    parser.add_argument("--today", default="",
                        help="data di riferimento YYYY-MM-DD per la priorita'")
    parser.add_argument("--publish", action="store_true",
                        help="passo del sito, meccanico e post-deploy: verifica gli "
                             "indicatori 'fusa' contro il sito e committa le prove su "
                             "master. Non e' un ruolo, non lancia un agente, non apre "
                             "PR. Default spento.")
    parser.add_argument("--publish-base", default=None,
                        help="il sito da verificare col passo del sito (default: il sito pubblico)")
    args = parser.parse_args(argv)

    publish = None
    if args.publish:
        from scripts import verify_publication
        base = args.publish_base or verify_publication.DEFAULT_BASE
        publish = verify_publication.publish_step(
            base=base, log=(lambda *_: None) if args.json else print)

    launches = load_plan(today=args.today)
    shown = launches[:args.top] if args.top else launches

    if args.json:
        payload = {"launches": shown, "publish": publish} if publish is not None else shown
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if launches else 1

    if not launches:
        print("niente da lanciare: nessun indicatore ha lavoro pronto e le code a monte sono vuote.")
        return 1

    print(f"Catena Divario Italia, {len(launches)} unita' di lavoro pronte "
          f"(indicatori diversi, lanciabili in parallelo):\n")
    for item in shown:
        target = item["indicator"] or "(coda intera)"
        print(f"  {item['priority']:6.1f}  {item['role']:12s} {target:24.24s} {item['reason']}")
        print(f"          agente {item['agent']}, run_id {item['run_id']}")
    if args.top and len(launches) > args.top:
        print(f"\n  ... e altre {len(launches) - args.top} voci sotto soglia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
