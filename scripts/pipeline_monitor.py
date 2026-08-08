#!/usr/bin/env python3
"""Il monitoraggio della catena, una vista di lettura sul dossier per-indicatore.

Non è un sottosistema a parte con un secondo modello di stato: è una vista
sullo **stesso** dossier che `practice_timeline` ricostruisce dagli artefatti
committati, promosso qui a sorgente unica del monitoraggio. La domanda che
risponde è quella che prima costava sette comandi e una testa che li teneva
insieme: **dov'è fermo, e perché**.

Tre cose, tutte derivate dal dossier (più il diario per la storia recente e i
battiti di sessione per il vivo):

- **la frase in testa**: "2 indicatori bloccati: ter-X smentita aperta da 2
  giorni, dem-Y aspetta il produttore da 5". Non una tabella da interpretare.
- **una riga per indicatore**: stato, da quando, prossimo ruolo, priorità.
- **le sessioni in volo adesso**, dai battiti che ogni ruolo lascia all'avvio
  (best effort: se un ruolo non ha battuto, il vivo tace, il committato no).

Il nucleo (`board`, `headline`) è puro: prende i dati già letti e non tocca il
disco, così un test lo prova con un dossier sintetico. La CLI e la rotta Flask
`/_pipeline` collegano i lettori reali. Stdlib puro come il resto della catena.

    python3 scripts/pipeline_monitor.py            # dov'è fermo, in una schermata
    python3 scripts/pipeline_monitor.py --json      # per la rotta o un altro programma
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pipeline_launch, practice_model, practice_timeline  # noqa: E402

# Il registro dei battiti: un file per run in volo, ignorato da git (è vivo, non
# storia). Ogni ruolo lo scrive all'avvio e lo cancella alla chiusura; un battito
# più vecchio della soglia si considera morto (una sessione caduta senza pulire).
HEARTBEATS_DIR = PROJECT_ROOT / "data" / "pipeline" / "heartbeats"
HEARTBEAT_STALE_HOURS = 6

# Stati che sono un "fermo" da mettere in testa, con la ragione leggibile.
# `in-attesa` non è qui perché non è sempre un blocco: quando aspetta il passo
# a monte (`motivo=monte-mancante`) è contropressione normale, non urgenza. Solo
# gli altri motivi contano come fermo: lo decide `is_stuck`, non l'appartenenza.
STUCK_STATES = {
    "invalidata": "un input è cambiato, i passaggi a valle non valgono più",
    "in-quarantena": "in-attesa terminale, tolta dalla coda",
}


def is_stuck(row: dict) -> bool:
    """Vero se la riga è un fermo da segnalare in testa (§3, §9).

    `invalidata` e `in-quarantena` lo sono sempre. `in-attesa` lo è solo quando
    il motivo è un cambio esterno o una correzione tecnica: l'attesa del passo a
    monte è normale e non va contata fra i bloccati."""
    st = row.get("state")
    if st in STUCK_STATES:
        return True
    if st == "in-attesa":
        return row.get("motivo") not in (None, "", "monte-mancante")
    return False

# Che cosa fa uno stadio, non chi lo fa. Sono descrizioni per chi guarda uno
# schermo, e restano anche per gli stadi storici, perché il dossier li nomina
# ancora e una riga senza etichetta si legge peggio di una con l'etichetta
# vecchia.
STAGE_LABELS = {
    "scout": "Scoperta fonte",
    "hunter": "Valutazione candidatura",
    "promoter": "Ammissione nel catalogo",
    "curator": "Curatela",
    "writer": "Scrittura",
    "reviewer": "Rilettura e firma",
    "producer": "Officina",
    "verificatore": "Verifica indipendente",
    "reader-editor": "Lettura di leggibilità",
    "launch": "Lancio",
}

# Una sola voce, e non è una traduzione: il ruolo si chiama ancora `producer`
# perché la coda dice ancora "questo indicatore va scritto", ma ciò che parte
# è l'officina, un workflow. Le altre tre voci erano personaggi italiani
# (`ammissione`, `produttore`) sovrapposti a nomi che già esistevano: un
# lettore che vede `ammissione` sul cruscotto e `admissions` nel diario deve
# tenere a mente una mappa per capire che sono la stessa cosa. Il chiamante
# (`:260`) fa `.get(owner, owner)`, quindi un ruolo assente stampa il proprio
# nome, che è esattamente ciò che si vuole.
ROLE_LABELS = {
    "producer": "officina",
}

# La lavorazione come la intende chi guarda il cruscotto, non lo stato grezzo
# del modello. `state` marca "in-lavorazione" ogni indicatore non ancora
# pubblicato, comprese le centinaia mai toccate (prosa legacy, zero run): qui
# si separa ciò che la pipeline lavora davvero (una run o un ruolo in volo)
# da ciò che è solo in coda. Unica fonte: prima viveva duplicata anche in
# `frontend/src/monitor/main.js`.
STATUS_ORDER = [
    "da correggere",
    "in quarantena",
    "in attesa",
    "in lavorazione",
    "in coda",
    "proposta",
    "pubblicata",
    "chiusa",
]

STATUS_HELP = {
    "in lavorazione": "La pipeline ci sta lavorando: una run in corso o già fatta.",
    "in coda": "Nel catalogo ma mai lavorato dalla pipeline (nessuna run).",
    "in attesa": "Ferma in attesa di una condizione. Il motivo la qualifica: manca il passo a monte (l'artefatto dello stadio precedente non esiste), oppure aspetta un cambio esterno alla fonte, oppure una correzione tecnica.",
    "pubblicata": "Fusa su master: il progetto ha ratificato merge = pubblicazione.",
    "da correggere": "Un input è cambiato (dati aggiornati, definizione, o una smentita aperta): il lavoro a valle non vale più e va rifatto.",
    "in quarantena": "Fermo in modo terminale, tolto dalla coda per non fermare le altre.",
    "proposta": "Candidato approvato, in attesa di essere promosso nel catalogo dal prossimo giro di ammissione (manca ancora curatela e articolo).",
    "chiusa": "Candidatura chiusa, nessuna azione.",
}

_STATE_TO_WORK_STATUS = {
    "pubblicata": "pubblicata",
    "invalidata": "da correggere",
    "in-attesa": "in attesa",
    "in-quarantena": "in quarantena",
    "chiusa": "chiusa",
    "proposta": "proposta",
}


def work_status(row: dict) -> str:
    """La lavorazione leggibile di una riga (vedi commento sopra `STATUS_ORDER`).

    Va chiamata dopo che `row["in_flight"]` è stato attaccato in `board()`:
    prima di quel punto ogni riga sarebbe letta come "in coda"."""
    mapped = _STATE_TO_WORK_STATUS.get(row.get("state"))
    if mapped:
        return mapped
    return "in lavorazione" if (row.get("in_flight") or row.get("runs")) else "in coda"


def _csv_rows(path: Path) -> list:
    """Legge i manifest del catalogo senza dipendenze dall'app Flask."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream, delimiter=";"))
    except OSError:
        return []


def indicator_labels(root=None) -> dict:
    """Nome e famiglia leggibili per ogni id noto al catalogo.

    Il dossier resta la fonte dello stato. Questi manifest aggiungono soltanto
    il lessico umano che serve alla vista: cercare 379 codici nudi non è
    monitoraggio. Tutti i file sono CSV committati e si leggono con la stdlib.
    """
    base = Path(root or PROJECT_ROOT)
    out = {}

    def add(indicator_id, name, family):
        if indicator_id and name:
            out[str(indicator_id)] = {"name": str(name), "family": family}

    for row in _csv_rows(base / "app/static/data/external_indicator_manifest.csv"):
        add(row.get("target_indicator_id"), row.get("target_indicator_name"), "Territoriale")
    for row in _csv_rows(base / "app/static/data/bes_regione_manifest.csv"):
        add(f"bes:{row.get('id')}", row.get("name"), "BES")
    for row in _csv_rows(base / "app/static/data/Assoluti_Provincia.csv"):
        add(f"bes:{row.get('idIndicatore')}", row.get("Indicatore"), "BES")
    for row in _csv_rows(base / "app/static/data/multiscopo_regione_manifest.csv"):
        add(f"multiscopo:{row.get('id')}", row.get("name"), "Multiscopo")
    for row in _csv_rows(base / "data/discovery/curation.csv"):
        target = row.get("target_indicator_id")
        family = "Eurostat" if str(target).startswith("eur:") else "Istat"
        add(target, row.get("name"), family)
    return out


def _reason(d: dict) -> str:
    """Perché un indicatore è dov'è, in una riga leggibile, dalle bandiere."""
    f = d.get("flags") or {}
    if f.get("open_smentita"):
        return "smentita aperta, una frase falsa in pagina"
    if f.get("needs_info"):
        return "rimandata: aspetta un chiarimento o un cambio alla fonte"
    if f.get("stale_vintage"):
        return "le cifre dell'articolo sono cambiate dopo la firma"
    if f.get("stale_curation"):
        return "la fonte ha pubblicato un anno nuovo, la curatela è scaduta"
    if d.get("state") == "in-attesa":
        # needs_info (dipendenza-esterna) è già uscito sopra: qui resta monte-mancante.
        return "manca il passo a monte: l'artefatto dello stadio precedente non esiste ancora"
    return STUCK_STATES.get(d.get("state"), d.get("state") or "")


def _days(start: str, today: str) -> int:
    return practice_model._days_between(start, today) if start and today else 0


def _run_history(run_ids, runs_by_id) -> list:
    """Le run che hanno toccato l'indicatore, dalla più recente, già collassate.

    Riusa `d["runs"]` (i run_id che `practice_timeline` ha già associato
    all'indicatore) e li unisce alle run collassate indicizzate per run_id, così
    il dettaglio per-indicatore non fa un secondo giro sul diario."""
    out = []
    for rid in run_ids or []:
        run = (runs_by_id or {}).get(rid)
        if not run:
            continue
        out.append({
            "run_id": rid,
            "stage": run.get("stage", ""),
            "outcome": run.get("outcome", ""),
            "summary": run.get("summary", ""),
            "at": run.get("at", ""),
            "model": run.get("model", ""),
            "duration_seconds": run.get("duration_seconds"),
            "detail": list(run.get("detail") or []),
            "pr": run.get("pr", ""),
            "trigger": run.get("trigger", ""),
            "gate": run.get("gate", ""),
            "queue_before": run.get("queue_before"),
            "queue_after": run.get("queue_after"),
            "claude_code_version": run.get("claude_code_version", ""),
        })
    out.sort(key=lambda r: r.get("at", ""), reverse=True)
    return out


def _owner_of(stage: str) -> str:
    """Il proprietario da mostrare per un vecchio stadio: dalla mappa, e con la
    sua etichetta.

    Le due metà vanno insieme. Erano separate, e si vedeva: i rami speciali
    scrivevano il ruolo a mano e il ramo generico applicava `ROLE_LABELS`,
    quindi la stessa riga del cruscotto diceva `produttore` o `officina` a
    seconda di quale ramo l'aveva prodotta. I template rendono questo campo
    alla lettera, e i filtri per proprietario ci si appoggiano.
    """
    ruolo = pipeline_launch.ROLE_OF_STAGE.get(stage) or stage
    return ROLE_LABELS.get(ruolo, ruolo)


def _next_step(d: dict, ready_stage: str | None) -> dict:
    """La prossima azione, detta come gesto e proprietario, non come stato."""
    flags = d.get("flags") or {}
    state = d.get("state", "")
    if flags.get("needs_info"):
        return {"owner": "fonte esterna", "stage": "", "kind": "blocked",
                "label": "Attendere il chiarimento richiesto alla fonte"}
    if state == "chiusa" or flags.get("rejected"):
        return {"owner": "nessuno", "stage": "", "kind": "closed",
                "label": "Nessuna azione, candidatura chiusa"}
    # Il proprietario si **legge** dalla mappa, non si scrive qui. Era scritto
    # (`produttore` per tutti e tre), e alla prima occasione ha mentito: quando
    # `curator` è passato all'ammissione, il cruscotto ha continuato a mandare
    # chi lo legge a un workflow che non sa curare e non ha nel perimetro i file
    # della curatela. Sotto, il ramo generico già passava da `ROLE_OF_STAGE`:
    # erano questi tre casi speciali a scavalcarla.
    if flags.get("open_smentita"):
        return {"owner": _owner_of("reviewer"), "stage": "reviewer", "kind": "attention",
                "label": "Correggere le affermazioni smentite e firmare di nuovo"}
    if flags.get("stale_curation"):
        return {"owner": _owner_of("curator"), "stage": "curator", "kind": "attention",
                "label": "Rivedere la curatela sui dati aggiornati"}
    if flags.get("stale_vintage"):
        return {"owner": _owner_of("reviewer"), "stage": "reviewer", "kind": "attention",
                "label": "Rileggere e firmare la nuova versione dei dati"}
    if state == "pubblicata":
        return {"owner": "monitoraggio", "stage": "", "kind": "done",
                "label": "Sorvegliare la fonte per nuovi dati o cambi di definizione"}
    if ready_stage:
        owner = _owner_of(ready_stage)
        labels = {
            "promoter": "Ammettere la candidatura nel catalogo",
            "curator": "Definire verso, categoria e ammissibilità al punteggio",
            "writer": "Scrivere l'articolo dell'indicatore",
            "reviewer": "Rileggere, correggere e firmare l'articolo",
            "verificatore": "Controllare in modo indipendente tutte le affermazioni",
        }
        return {"owner": owner, "stage": ready_stage,
                "kind": "ready", "label": labels.get(ready_stage, f"Eseguire {ready_stage}")}
    return {"owner": "monitoraggio", "stage": "", "kind": "waiting",
            "label": "Controllare gli artefatti: nessun passo lanciabile ricostruito"}


def _lifecycle(d: dict, next_step: dict) -> tuple[list, int, str]:
    """Quattro fasi stabili, dall'ingresso al merge su master (= pubblicazione)."""
    completed = set(d.get("completed_stages") or [])
    required = list(d.get("required_stages") or [])
    # **Le fasi si ricavano dal ruolo, non da un elenco di stadi scritto qui.**
    # Erano scritte: `promoter` era l'ammissione e tutto il resto la produzione,
    # quindi quando `curator` è passato all'ammissione la stessa riga del
    # cruscotto diceva proprietario `admissions` e fase `produzione`, e i filtri
    # per fase classificavano male ogni curatela, iniziale o scaduta.
    di_ruolo = lambda ruolo: [s for s in required
                              if pipeline_launch.ROLE_OF_STAGE.get(s) == ruolo]
    admission_required = di_ruolo("admissions")
    production_required = di_ruolo("producer")
    has_downstream = bool(completed or d.get("timeline"))
    admission_done = (has_downstream and d.get("state") != "proposta"
                      and set(admission_required).issubset(completed))
    production_done = bool(production_required) and set(production_required).issubset(completed)
    verification_done = "verificatore" in completed and d.get("verification_valid") is True
    # Pubblicazione = fuso su master (il progetto ha ratificato merge = pubblicazione).
    publication_done = d.get("state") == "pubblicata"
    current_stage = next_step.get("stage")
    current_phase = (
        "pubblicazione" if publication_done else
        "verifica" if current_stage == "verificatore" or (production_done and not verification_done) else
        "ammissione" if pipeline_launch.ROLE_OF_STAGE.get(current_stage) == "admissions"
        or not admission_done else
        "produzione"
    )
    if d.get("state") == "chiusa":
        current_phase = "chiusa"

    def status(key, done):
        if key == current_phase and next_step.get("kind") in ("attention", "blocked"):
            return "issue"
        if done:
            return "done"
        if d.get("state") == "chiusa":
            return "off"
        if key == current_phase:
            return "current"
        return "pending"

    phases = [
        {"key": "ammissione", "label": "Ammissione", "status": status("ammissione", admission_done)},
        {"key": "produzione", "label": "Produzione", "status": status("produzione", production_done)},
        {"key": "verifica", "label": "Verifica", "status": status("verifica", verification_done)},
        {"key": "pubblicazione", "label": "Pubblicazione", "status": status("pubblicazione", publication_done)},
    ]
    done_count = sum(p["status"] == "done" for p in phases)
    return phases, done_count * 25, current_phase


def _last_activity(timeline: list, runs: list) -> dict:
    candidates = [
        {"at": event.get("at", ""), "label": event.get("detail", ""),
         "stage": event.get("stage", "")}
        for event in timeline if event.get("at")
    ]
    candidates.extend({"at": run.get("at", ""), "label": run.get("summary", ""),
                       "stage": run.get("stage", "")} for run in runs if run.get("at"))
    return max(candidates, key=lambda item: item["at"]) if candidates else {}


def row_of(d: dict, today: str = "", runs_by_id: dict = None, labels: dict = None) -> dict:
    """La riga di monitoraggio di un indicatore, dal suo dossier.

    Con `runs_by_id` (le run collassate indicizzate per run_id) la riga porta
    anche stadi fatti, stato di pubblicazione e verifica, e la storia delle run
    che hanno toccato l'indicatore: così il cruscotto può aprire un dettaglio
    per-indicatore senza un secondo giro sul diario."""
    stage = practice_timeline.ready_stage(d)
    next_step = _next_step(d, stage)
    lifecycle, progress, phase = _lifecycle(d, next_step)
    runs = _run_history(d.get("runs"), runs_by_id)
    timeline = [dict(event, stage_label=STAGE_LABELS.get(event.get("stage"), event.get("stage", "")))
                for event in (d.get("timeline") or [])]
    label = (labels or {}).get(d["id"], {})
    return {
        "id": d["id"],
        "name": label.get("name") or d["id"],
        "family": label.get("family") or (str(d["id"]).split(":", 1)[0].upper()
                                             if ":" in str(d["id"]) else "Territoriale"),
        "type": d.get("type", ""),
        "state": d.get("state", ""),
        "entered_at": d.get("entered_at", ""),
        "days": _days(d.get("entered_at", ""), today),
        "next_role": pipeline_launch.ROLE_OF_STAGE.get(stage) if stage else None,
        "next_stage": stage,
        "next_step": next_step,
        "phase": phase,
        "progress": progress,
        "lifecycle": lifecycle,
        "priority": round(float(d.get("priority", 0.0) or 0.0), 1),
        "error_class": d.get("error_class"),
        "motivo": d.get("motivo", ""),
        "flags": sorted(k for k, v in (d.get("flags") or {}).items() if v is True),
        "reason": _reason(d),
        "completed_stages": list(d.get("completed_stages") or []),
        "published": d.get("published"),
        "verification_valid": d.get("verification_valid"),
        "runs": runs,
        "timeline": timeline,
        "last_activity": _last_activity(timeline, runs),
        "required_stages": list(d.get("required_stages") or []),
        "score_eligible": bool(d.get("score_eligible")),
    }


def headline(rows: list, today: str = "", admissions=None) -> str:
    """La frase in testa: dov'è fermo, e perché. Dai soli `rows` già calcolati."""
    stuck = [r for r in rows if is_stuck(r)]
    if stuck:
        stuck.sort(key=lambda r: (-r["days"], r["id"]))
        top = stuck[0]
        when = f" da {top['days']} giorni" if top["days"] else ""
        n = len(stuck)
        prefix = f"{n} indicatore bloccato." if n == 1 else f"{n} indicatori bloccati."
        more = f" Altri {n - 1} sono elencati nelle priorità." if n > 1 else ""
        return f"{prefix} Prima priorità: {top['id']}, {top['reason']}{when}.{more}"
    ready = [r for r in rows if r["next_role"] and r["next_role"] != "admissions"]
    if ready:
        top = ready[0]
        return (f"{len(ready)} indicatori pronti al lavoro, niente è bloccato. "
                f"Il più urgente: {top['id']} -> {top['next_role']}.")
    if admissions:
        return "ammissione pronta al lavoro, niente è bloccato. La coda a monte richiede un batch."
    return "catena in pari: nessun indicatore bloccato, niente in coda."


def board(dossier: dict, runs=None, heartbeats=None, today: str = "",
          recent: int = 12, open_runs=None, labels=None, queues=None) -> dict:
    """Il cruscotto intero, dai soli artefatti già letti. Puro.

    `dossier` è l'uscita di `practice_timeline`. `runs` sono le run già
    collassate (`pipeline_log.collapse_runs`), per la storia recente.
    `heartbeats` sono i battiti vivi (un ruolo che lavora, prima ancora che ci
    sia una PR); `open_runs` sono le PR aperte su `automation/*` con stato CI e
    mergeabilità, fotografate dal lanciatore. Ritorna la frase in testa, le
    righe per indicatore, i fermi, il vivo, le PR aperte, la storia recente e i
    totali per stato.
    """
    runs_by_id = {r.get("run_id"): r for r in (runs or []) if r.get("run_id")}
    rows = [row_of(d, today, runs_by_id, labels=labels) for d in dossier.values()]
    rows.sort(key=lambda r: (-r["priority"], -r["days"], r["id"]))

    totals: dict = {}
    for r in rows:
        totals[r["state"]] = totals.get(r["state"], 0) + 1

    recent_runs = sorted((runs or []), key=lambda run: run.get("at", ""), reverse=True)[:recent]

    in_flight = sorted(heartbeats or [], key=lambda h: h.get("since", ""))
    open_items = sorted(open_runs or [], key=lambda p: (p.get("pr") or 0))
    beats_by_indicator = {}
    for beat in in_flight:
        if beat.get("indicator"):
            beats_by_indicator.setdefault(beat["indicator"], []).append(beat)
    prs_by_run = {item.get("run_id"): item for item in open_items if item.get("run_id")}
    for row in rows:
        row["in_flight"] = beats_by_indicator.get(row["id"], [])
        run_ids = {run.get("run_id") for run in row.get("runs", [])}
        run_ids.update(beat.get("run_id") for beat in row["in_flight"])
        row["open_prs"] = [prs_by_run[rid] for rid in run_ids if rid in prs_by_run]
        row["work_status"] = work_status(row)
        # Lo stato di sosta è uno solo ("in attesa"), ma il tooltip del badge porta
        # il motivo specifico (monte-mancante vs blocco esterno/tecnico), così
        # l'operatore vede la differenza pur con un solo stato armonizzato.
        if row.get("state") == "in-attesa" and row.get("reason"):
            row["work_status_help"] = row["reason"]
        else:
            row["work_status_help"] = STATUS_HELP.get(row["work_status"], "")

    phase_totals = {}
    for row in rows:
        phase_totals[row["phase"]] = phase_totals.get(row["phase"], 0) + 1
    attention = [r for r in rows if r["next_step"]["kind"] in ("attention", "blocked")]
    actionable = [
        r for r in rows
        if r["next_step"]["kind"] in ("attention", "ready")
        and r["next_role"] != "admissions"
    ]
    admission_launch = next(
        (item for item in pipeline_launch.plan_launches(dossier, queues=queues)
         if item["role"] == "admissions"),
        None,
    )
    if admission_launch:
        actionable.append({
            "id": "admissions",
            "name": "Coda di ammissione",
            "priority": admission_launch["priority"],
            "next_step": {
                "owner": "ammissione",
                "stage": "promoter",
                "kind": "ready",
                "label": admission_launch["reason"],
            },
        })
    actionable.sort(key=lambda row: (-row["priority"], row["id"]))

    return {
        "headline": headline(rows, today, admissions=admission_launch),
        "totals": totals,
        "stuck": [r for r in rows if is_stuck(r)],
        "ready": [r for r in rows if r["next_role"]],
        "actionable": actionable,
        "attention": attention,
        "rows": rows,
        "in_flight": in_flight,
        "open_runs": open_items,
        "phase_totals": phase_totals,
        "status_order": STATUS_ORDER,
        "status_help": STATUS_HELP,
        "metrics": {
            "indicators": len(rows),
            "attention": len(attention),
            "actionable": len(actionable),
            "in_flight": len(in_flight),
            "published": sum(r["published"] is True for r in rows),
        },
        "recent": [{"at": run.get("at", ""), "stage": run.get("stage", ""),
                    "outcome": run.get("outcome", ""), "summary": run.get("summary", ""),
                    "run_id": run.get("run_id", "")} for run in recent_runs],
        "generated_for": today,
    }


def summarize_catalog(rows: list, universe: dict) -> dict:
    """Il conto che deve tornare: quanti indicatori esistono nei cataloghi di
    famiglia in tutto (`universe`, già calcolato da `app.views._pipeline_universe`
    perché legge `app.data`/`app.bes_data`/`app.multiscopo_data`/
    `app.external_atlas`: questo modulo resta stdlib-puro), quanti sono
    indicizzabili (non vecchi, non duplicati, non a copertura incompleta), e
    quanti di questi la pipeline ha già scritto, verificato, pubblicato.

    `not_yet_admitted` è la risposta a "se manca qualcosa inseriamo": indicatori
    nel catalogo di una famiglia che non hanno ancora nessuna traccia in una
    pratica di ammissione (`rows`, dal dossier di `practice_timeline`)."""
    total_universe = len(universe)
    indexable = sum(1 for v in universe.values() if v["indexable"])
    non_indexable_by_reason: dict = {}
    for v in universe.values():
        if not v["indexable"]:
            reason = v.get("reason") or "altro"
            non_indexable_by_reason[reason] = non_indexable_by_reason.get(reason, 0) + 1

    by_id = {r["id"]: r for r in rows}
    admitted_ids = set(by_id) & set(universe)
    indexable_admitted = [by_id[i] for i in admitted_ids if universe[i]["indexable"]]

    return {
        "total_universe": total_universe,
        "indexable": indexable,
        "non_indexable": total_universe - indexable,
        "non_indexable_by_reason": non_indexable_by_reason,
        "not_yet_admitted": total_universe - len(admitted_ids),
        "indexable_admitted": len(indexable_admitted),
        "written": sum(1 for r in indexable_admitted if "writer" in (r.get("completed_stages") or [])),
        "verified": sum(1 for r in indexable_admitted if "verificatore" in (r.get("completed_stages") or [])),
        "published": sum(1 for r in indexable_admitted if r.get("published") is True),
    }


def attribute_tokens(rows, tokens_by_run):
    """Attacca il consumo token a ogni run e somma il totale per indicatore.

    Un `run_id` può comparire nella storia di più indicatori: `practice_timeline`
    associa una run a ogni indicatore che il suo testo cita, compresi quelli di
    confronto. Ma il costo è di UNO solo, il bersaglio, che il record di
    telemetria porta in `indicator`. Quindi si attribuisce solo dove combacia,
    mai a un indicatore citato per confronto (né a un batch senza bersaglio, che
    ha `indicator` vuoto e non combacia con nessuna riga). Puro: muta e ritorna
    `rows`."""
    tokens_by_run = tokens_by_run or {}
    for row in rows:
        total = 0
        for run in row.get("runs", []):
            entry = tokens_by_run.get(run.get("run_id"))
            if entry and entry.get("indicator") == row.get("id"):
                run["tokens"] = entry.get("tokens")
                total += entry.get("tokens") or 0
            else:
                run["tokens"] = None
        row["tokens_total"] = total or None
    return rows


def _run_indicators(run: dict, token_entry: dict) -> list:
    """Gli indicatori a cui una run appartiene, dal più affidabile al meno.

    Il record di telemetria porta l'unico bersaglio vero (`indicator`), quando
    c'è: una lista di uno. Senza telemetria si ripiega sugli id citati nel testo
    della run, che sono un insieme (un articolo cita gli indicatori di confronto),
    quindi si torna una lista, mai una scelta. Attribuire i token a un indicatore
    solo quando la lista ha un elemento solo (bersaglio non ambiguo) è compito di
    chi somma, non di qui: qui non si inventa mai un'associazione dove il dato ne
    porta due o zero, la stessa cautela di `_ids_in_text`."""
    target = (token_entry or {}).get("indicator")
    if target:
        return [target]
    text = (run.get("summary") or "") + "\n" + "\n".join(run.get("detail") or [])
    return sorted(practice_timeline._ids_in_text(text))


def runs_timeline(tokens_by_run=None) -> dict:
    """La cronologia di ogni azione della catena, una riga per run, con i token.

    Joina le run collassate dal diario (`pipeline_log`) con la telemetria token
    (`tokens_by_run`, iniettata dal chiamante perché viene da Supabase e questo
    modulo resta stdlib puro) **sul solo `run_id`**: diverso da `attribute_tokens`,
    che scarta i token il cui indicatore non combacia con una riga di board. Qui
    la chiave è la run, e ogni run si conserva, anche senza token (`null`) e anche
    senza un indicatore riconoscibile (lista vuota). Ordinata per `at` decrescente.

    I totali aggregano ciò che si può sommare senza inventare: token per stadio,
    per giorno ed esito per conteggio sono sempre certi; i token per indicatore si
    sommano solo dove la telemetria porta un bersaglio esplicito (`token_entry`),
    mai da un id pescato nella prosa, nemmeno quando ne compare uno solo: un batch
    di ammissione posta il costo senza indicatore, e appenderlo all'unico id che il
    diario cita darebbe a quell'indicatore il conto dell'intera coda. La prosa dice
    quali id una run ha toccato, non di chi è il costo."""
    from scripts import pipeline_log
    tokens_by_run = tokens_by_run or {}
    runs = pipeline_log.collapse_runs(pipeline_log.read_journal())
    out = []
    tokens_by_stage: dict = {}
    tokens_by_indicator: dict = {}
    tokens_by_day: dict = {}
    runs_by_outcome: dict = {}
    for run in runs:
        run_id = run.get("run_id") or ""
        token_entry = tokens_by_run.get(run_id) or {}
        indicators = _run_indicators(run, token_entry)
        tok = token_entry.get("tokens")
        stage = run.get("stage", "")
        day = (run.get("at", ""))[:10]
        outcome = run.get("outcome", "")
        tokens_by_stage[stage] = tokens_by_stage.get(stage, 0) + (tok or 0)
        tokens_by_day[day] = tokens_by_day.get(day, 0) + (tok or 0)
        runs_by_outcome[outcome] = runs_by_outcome.get(outcome, 0) + 1
        # La proprietà del costo la stabilisce SOLO il bersaglio esplicito della
        # telemetria, mai un id pescato nella prosa: un batch di ammissione posta
        # i token senza indicatore, e se il suo diario cita per caso un solo id il
        # costo dell'intera coda finirebbe su quell'indicatore. La prosa va bene
        # per dire "questa run ha toccato questi id", non per dire "il conto è suo".
        target = token_entry.get("indicator")
        if tok and target:
            tokens_by_indicator[target] = tokens_by_indicator.get(target, 0) + tok
        out.append({
            "at": run.get("at", ""),
            "run_id": run_id,
            "stage": stage,
            "indicators": indicators,
            "outcome": outcome,
            "summary": run.get("summary", ""),
            "duration_seconds": run.get("duration_seconds"),
            "pr": run.get("pr", ""),
            "commit": run.get("commit", ""),
            "tokens": tok,
        })
    out.sort(key=lambda r: r["at"], reverse=True)
    return {
        "runs": out,
        "totals": {
            "tokens_by_stage": tokens_by_stage,
            "tokens_by_indicator": tokens_by_indicator,
            "tokens_by_day": tokens_by_day,
            "runs_by_outcome": runs_by_outcome,
            "runs": len(out),
            "tokens": sum(r["tokens"] or 0 for r in out),
        },
    }


# --- i battiti: il vivo, best effort ----------------------------------------

def write_heartbeat(role: str, run_id: str, indicator: str = "", root=None,
                    now: str = "") -> Path:
    """Un ruolo che parte lascia un battito: chi lavora su cosa, da quando.

    File per run (il `run_id` è unico), così due ruoli in volo insieme non si
    sovrascrivono. Ignorato da git: è vivo, non storia. `now` iniettabile per i
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


def post_beat(payload: dict, url: str = "", token: str = "", timeout: int = 5,
              opener=None) -> bool:
    """Manda un battito all'endpoint del sito, best effort. Ritorna se è andata.

    È ciò che fa comparire il vivo su /_pipeline mentre un agente lavora, anche
    prima che ci sia una commit: gli agenti girano su macchine effimere separate
    dal server, e l'unico modo perché il server veda il vivo senza dare a ognuno
    una credenziale GCS è che lo scriva il server, su richiesta. Puro urllib,
    stdlib. `url`/`token` di default dall'ambiente; se mancano, non fa niente e lo
    dice, così in locale (o senza segreto) non è un errore, è silenzio."""
    import json as _json
    import os
    import urllib.request

    url = url or os.environ.get("PIPELINE_INGEST_URL", "")
    token = token or os.environ.get("PIPELINE_INGEST_TOKEN", "")
    if not url or not token:
        return False
    endpoint = url.rstrip("/") + "/_pipeline/beat"
    data = _json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST", headers={
        "Content-Type": "application/json", "X-Pipeline-Key": token})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:  # noqa: BLE001  (best effort: un battito perso non ferma la run)
        return False


def post_tokens(run_id: str, tokens, indicator: str = "", stage: str = "",
                role: str = "", **kw) -> bool:
    """Il consumo token di una run all'endpoint del sito, best effort.

    Chiavato sul `run_id` del RUOLO (non del lanciatore che lo POSTa), così il
    totale si attacca all'indicatore giusto. È telemetria durevole: a differenza
    di un battito non scade. Riusa `post_beat` (stesso endpoint, stesso segreto)."""
    return post_beat({"action": "tokens", "run_id": run_id, "tokens": tokens,
                      "indicator": indicator, "stage": stage, "role": role}, **kw)


def post_outcome(run_id: str, indicator: str, snapshot: dict,
                 base_commit: str = "", at: str = "", **kw) -> bool:
    """Lo snapshot di stato di un indicatore all'endpoint del sito, best effort.

    Lo POSTa il passo di merge dopo aver fuso, perché il cruscotto rifletta
    l'esito senza aspettare il redeploy dell'immagine. Riusa `post_beat` (stesso
    endpoint, stesso segreto): `snapshot` è il dossier del solo indicatore, le sue
    liste/dict annidati viaggiano nativi nel JSON del POST."""
    payload = {"action": "outcome", "run_id": run_id, "indicator": indicator,
               "base_commit": base_commit, "at": at}
    payload.update(snapshot or {})
    return post_beat(payload, **kw)


def read_heartbeats(root=None, now: str = "", stale_hours: int = HEARTBEAT_STALE_HOURS) -> list:
    """I battiti vivi: quelli più vecchi della soglia si scartano (sessione
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


# I campi del dossier che uno snapshot sovrappone. `id`, `runs` e `timeline` non
# ci sono: la chiave e i due registri li tiene la board, non l'overlay.
_OVERLAY_FIELDS = ("state", "type", "entered_at", "completed_stages",
                   "required_stages", "flags", "published", "verification_valid",
                   "score_eligible", "error_class", "motivo", "priority")


def _dossier_from_outcome(indicator: str, snap: dict) -> dict:
    """Un dossier minimo per un indicatore che l'immagine deployata non conosce
    ancora (interamente lavorato dopo la build). `runs`/`timeline` vuoti: `row_of`
    li tollera (`_run_history` e `_last_activity` reggono le liste vuote)."""
    run_id = snap.get("run_id") or ""
    return {
        "id": indicator,
        "type": snap.get("type") or "nuovo",
        "state": snap.get("state") or "in-lavorazione",
        "entered_at": snap.get("entered_at") or "",
        "completed_stages": list(snap.get("completed_stages") or []),
        "flags": dict(snap.get("flags") or {}),
        "error_class": snap.get("error_class"),
        "score_eligible": bool(snap.get("score_eligible")),
        "published": snap.get("published"),
        "verification_valid": snap.get("verification_valid"),
        "runs": [run_id] if run_id else [],
        "timeline": [],
        "required_stages": list(snap.get("required_stages") or []),
        "motivo": snap.get("motivo") or "",
        "priority": snap.get("priority") or 0.0,
    }


def _apply_outcomes(dossier: dict, outcomes: dict) -> None:
    """Sovrappone gli snapshot vivi al dossier committato, in loco.

    Riconciliazione, unica regola: uno snapshot si applica **solo se** il suo
    `run_id` non è già nei `runs` del dossier committato. Dopo il deploy che porta
    quella run su master, `reconstruct` aggiunge quel `run_id` ai `runs` e l'overlay
    si spegne da solo, senza uno stato da azzerare a mano né da confrontare campo a
    campo: è l'unico ritiro sicuro. Confrontare invece lo stato (es. 'stessi stadi
    e stesso published') ritirava a torto proprio il caso che conta, una smentita su
    un indicatore già pubblicato, dove cambiano solo `state`/`flags`, e lasciava il
    cruscotto su `pubblicata` invece dell'invalidazione."""
    for indicator, snap in outcomes.items():
        d = dossier.get(indicator)
        if d is None:
            dossier[indicator] = _dossier_from_outcome(indicator, snap)
            continue
        run_id = snap.get("run_id")
        if run_id and run_id in (d.get("runs") or []):
            continue
        for field in _OVERLAY_FIELDS:
            if field in snap:
                d[field] = snap[field]
        if run_id and run_id not in (d.get("runs") or []):
            d.setdefault("runs", []).append(run_id)


def load_board(today: str = "", recent: int = 12,
               heartbeats=None, open_runs=None, outcomes=None) -> dict:
    """Collega i lettori reali (tutti stdlib puri) e ritorna il cruscotto.

    `heartbeats`/`open_runs` iniettabili: la rotta Flask li passa dal SQLite
    vivo (scritto dai POST degli agenti, replicato su GCS). Quando `heartbeats`
    è None si torna ai battiti su file, che è ciò che vuole la CLI in locale
    (agente e file sulla stessa macchina); sul server quei file sono sempre vuoti,
    ed è esattamente il motivo per cui il cruscotto sembrava morto.

    `outcomes` iniettabile allo stesso modo: gli snapshot di stato che gli agenti
    POSTano al merge, per indicatore. Si applicano al dossier **prima** di
    costruire le righe, così stato/lifecycle/prossimo passo e i contatori si
    ricalcolano coerenti. Servono a chiudere la finestra fra 'fuso su master' e
    'immagine deployatà: la CLI in locale lascia `None` (legge i file freschi)."""
    from datetime import datetime, timezone
    from scripts import pipeline_log, pipeline_status
    ref = today or datetime.now(timezone.utc).date().isoformat()
    dossier = practice_timeline.load_real(today=ref)
    if outcomes:
        _apply_outcomes(dossier, outcomes)
    runs = pipeline_log.collapse_runs(pipeline_log.read_journal())
    beats = read_heartbeats(now=ref) if heartbeats is None else heartbeats
    return board(dossier, runs=runs, heartbeats=beats, today=ref, recent=recent,
                 open_runs=open_runs, labels=indicator_labels(),
                 queues=pipeline_status.queue_sizes(pipeline_launch.ADMISSIONS_QUEUES))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dov'è fermo la catena, e perché.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--today", default="", help="data di riferimento YYYY-MM-DD")
    parser.add_argument("--beat-open", nargs=2, metavar=("RUOLO", "RUN_ID"),
                        help="un ruolo che parte lascia il proprio battito (il vivo del cruscotto)")
    parser.add_argument("--beat-close", metavar="RUN_ID",
                        help="un ruolo che chiude cancella il proprio battito")
    parser.add_argument("--indicator", default="",
                        help="l'indicatore su cui batte il ruolo (con --beat-open/--post-tokens)")
    parser.add_argument("--post-tokens", nargs=2, metavar=("RUN_ID", "N"),
                        help="POSTa il consumo token di una run (il lanciatore, a chiusura di un ruolo)")
    parser.add_argument("--role", default="", help="ruolo, per --post-tokens")
    parser.add_argument("--stage", default="", help="stadio, per --post-tokens")
    args = parser.parse_args(argv)

    if args.post_tokens:
        run_id, n = args.post_tokens
        sent = post_tokens(run_id, n, indicator=args.indicator,
                           stage=args.stage, role=args.role)
        if not args.json:
            print(f"token {n} per {run_id}: "
                  + ("inviati al sito" if sent else "ingest spento o non raggiungibile"))
        return 0

    # I battiti: due gesti che un agente fa in apertura e chiusura della sua run.
    # Non stampano il cruscotto, aprono/chiudono il vivo e basta.
    if args.beat_open:
        role, run_id = args.beat_open
        path = write_heartbeat(role, run_id, indicator=args.indicator)
        # Il file locale resta per la CLI in locale; il POST fa comparire il vivo
        # sul sito servito (best effort: se l'ambiente non ha URL/segreto, tace).
        sent = post_beat({"action": "beat", "run_id": run_id, "role": role,
                          "indicator": args.indicator, "stage": role})
        if not args.json:
            print(f"battito aperto: {role} su {args.indicator or '(coda)'} -> {path}"
                  + ("  (inviato al sito)" if sent else ""))
        return 0
    if args.beat_close:
        clear_heartbeat(args.beat_close)
        post_beat({"action": "close", "run_id": args.beat_close})
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
