#!/usr/bin/env python3
"""Il lanciatore per-indicatore: che cosa lanciare adesso, e quanto in parallelo.

Sostituisce il dispatcher-scheduler (`pipeline_dispatch.py`). Il dispatcher
serializzava: un tick, uno stadio, e rifiutava di partire finché una pull
request della catena era aperta. Serviva quando l'unità di lavoro era lo
**stadio** e sette stadi separati si scrivevano addosso i registri condivisi.
Adesso l'unità di lavoro è l'**indicatore**, e tre soli ruoli lo lavorano:

    ammissione (scout+hunter+promoter+curator) -> produttore (writer+reviewer)
    -> verificatore

Indicatori diversi toccano file diversi, quindi non c'è contesa da
serializzare: il lanciatore non sceglie uno stadio, **elenca** tutto il lavoro
lanciabile, prioritizzato, e chi lo esegue (l'agente lanciatore, o una persona)
ne mette in volo quanti ne vuole in parallelo senza rischio di collisione.

- **Produttore e verificatore sono per-indicatore.** Ogni indicatore pronto è
  una voce a sé, perché due produttori su due indicatori diversi non si
  toccano. La priorità e il ruolo vengono dal dossier per-indicatore
  (`practice_timeline`), la stessa logica di `stage_priorities()`: una smentita
  su una pagina online (peso 100) precede una candidatura nuova.
- **L'ammissione è batch.** Una sessione triaga l'intera coda di fonti e
  candidati e promuove ciò che approva, quindi è una voce sola. La sua
  esistenza si legge dalle code pre-pratica (`scout`, `hunter`, `promoter`), che
  non sono indicatori nel dossier, più le pratiche in stato `proposta`.

Come il dispatcher, non lancia niente: questo è stdlib puro. Dice **che cosa**
lanciare, con ruolo e indicatore, e per i ruoli che sono una run anche il
`run_id` già coniato (l'officina non lo è, vedi `plan_launches`). La decisione
è deterministica e verificabile da un test, l'esecuzione no.

    python3 scripts/pipeline_launch.py            # il piano, leggibile
    python3 scripts/pipeline_launch.py --json     # per chi lancia
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

from scripts import practice_timeline, verification_queue  # noqa: E402  (path bootstrap above)

# I tre ruoli fusi, e la mappa dal vecchio stadio (che il dossier ancora nomina,
# perché è il vocabolario di `ready_stage`) al ruolo che oggi lo copre. Uno
# solo, non ricopiato: se domani un ruolo assorbe un altro stadio, si cambia qui.
ROLE_OF_STAGE = {
    "scout": "admissions",
    "hunter": "admissions",
    "promoter": "admissions",
    # `curator` va all'ammissione, non al produttore, e la ragione è il
    # perimetro. Curare vuol dire eseguire `scripts/apply_curation.py`, che
    # scrive il layer esterno, il manifest e le descrizioni curate: tutti file
    # dell'ammissione in `pipeline_gate.STAGE_PATHS`. L'officina scrive
    # `content/indicators/` e non sa curare. Mandarla lì significava mandare il
    # lavoro a chi non ha né il gesto né il permesso. Non è mai successo solo
    # perché la coda `curator` è vuota da quando la mappa esiste.
    "curator": "admissions",
    "writer": "producer",
    "reviewer": "producer",
    "verificatore": "verificatore",
}

# **Il produttore non è più un agente.** Scrivere un articolo è passato
# all'officina, cioè a un workflow con quattro tipi stretti, e il file
# `.claude/agents/producer.md` non esiste più. Un piano che continuasse a
# nominarlo sarebbe un puntatore morto che qualcuno lancia una volta sola,
# scoprendo il guasto quando la run muore: quindi il ruolo resta (la coda dice
# ancora "questo indicatore va scritto"), e cambia il bersaglio.
#
# I ruoli che non si lanciano come agente ma come workflow, con l'indicatore
# fra gli argomenti. Chi legge il piano trova il comando già scritto.
WORKFLOW_OF_ROLE = {
    "producer": ".claude/workflows/produci-indicatori.js",
}


def target(role, indicator):
    """Che cosa lanciare per questo ruolo: un agente, oppure un workflow.

    Per i ruoli che sono agenti il nome del ruolo **è** il nome dell'agente, e
    non c'è una mappa. Ce n'era una, e conteneva una sola voce che traducesse
    davvero: il ruolo `verificatore` verso il file `indicator-verifier.md`. Un
    dizionario identità su tre voci non è un'astrazione, è una mappa che
    aspetta di divergere: il file adesso si chiama `verificatore.md` e la
    traduzione non serve più. Un test tiene l'invariante (ogni chiave di
    `pipeline_gate.STAGE_PATHS` ha il suo `.claude/agents/<chiave>.md`).

    **Il comando porta il codice pubblico, non la chiave dello store.** Il piano
    ragiona in chiavi, perché è così che il dossier e le code nominano un
    indicatore (`dem:DEPENDRATE`, `176`); l'officina ragiona in codici URL
    (`dem-DEPENDRATE`, `ter-176`) e gli altri li rifiuta: `officina.pacchetti`
    risponde "nessun indicatore per" al primo passo, `officina.pubblica.chiave`
    solleva all'ultimo. Il piano scriveva perciò comandi che non partivano, e
    non se ne accorgeva nessuno perché il comando lo esegue chi legge il piano,
    non chi lo calcola. La conversione è `verification_queue.code_of`, che già
    esisteva ed è quella che usa `reading_queue`: una regola sola, non due.
    """
    if role in WORKFLOW_OF_ROLE:
        codice = verification_queue.code_of(str(indicator)) if indicator else ""
        return {"agent": None, "workflow": WORKFLOW_OF_ROLE[role],
                "comando": f'Workflow({{scriptPath: "{WORKFLOW_OF_ROLE[role]}", '
                           f'args: ["{codice}"]}})'}
    return {"agent": role}

# L'ordine di precedenza dei ruoli, a monte prima, come la catena: rompe solo i
# pari merito di priorità. Una smentita (priorità 100) scavalca comunque tutto
# perché l'ordinamento è prima sulla priorità. Il reader-editor sta PRIMA del
# verificatore di proposito: se un indicatore è insieme da leggere e da
# verificare, leggerlo prima evita di sprecare una verifica su un testo che una
# bocciatura di leggibilità farà riscrivere (l'hint d'ordine del piano).
ROLE_ORDER = ("admissions", "producer", "reader-editor", "verificatore")

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


def _revise_reason(row):
    """Il motivo di una riscrittura per leggibilità, con dentro l'indirizzo.

    La riga di lancio è l'unica cosa che il produttore riceve, quindi è l'unico
    posto in cui il lavoro del reader-editor può arrivargli: se porta solo
    "bocciato per leggibilità" la riscrittura parte cieca, il produttore rifà
    la metà sbagliata dell'articolo e si fa bocciare di nuovo finché il freno
    non parcheggia il codice. Tre cose, in ordine di durezza: i fallimenti duri
    (che sono classi, non opinioni), i criteri caduti sotto il massimo col loro
    punteggio, e la nota, che è il punto d'inciampo scritto da chi ha letto.
    """
    parts = [f"{row.get('code')} bocciato dal reader-editor per leggibilità"]
    hard = row.get("hard_failures") or []
    if hard:
        parts.append("fallimenti duri: " + ", ".join(hard))
    low = row.get("low_scores") or []
    if low:
        parts.append("criteri sotto il massimo: "
                     + ", ".join(f"{name}={value}" for name, value in low))
    note = (row.get("note") or "").strip()
    if note:
        parts.append(f"dove inciampa: {note}")
    return ". ".join(parts)


def plan_launches(dossier, queues=None, mint=None, readings=None):
    """La lista prioritizzata di lanci, dai soli artefatti già letti.

    `dossier` è l'uscita di `practice_timeline.reconstruct()`/`load_real()`:
    `{indicator_id: dossier}`. `queues` sono le dimensioni delle code
    (`pipeline_status.queue_sizes()`), da cui si legge il lavoro pre-pratica
    dell'ammissione (le proposte di fonti non sono indicatori). `readings` sono le
    righe di `reading_queue.build_queue()`: da qui nascono i lanci del
    reader-editor (i pubblicati non ancora letti) e i lanci di riscrittura per
    leggibilità del produttore (i bocciati), SENZA passare da `ready_stage`, che
    è terminale su `pubblicata`. `mint(role)` conia il `run_id`, iniettato così
    il nucleo resta puro.

    Ritorna una lista di voci di lancio ordinate per priorità decrescente, ogni
    voce con `role`, `agent`, `indicator` (None per l'ammissione batch), `scope`,
    `priority`, `reason`.

    **`run_id` solo per i ruoli che sono una run.** Le voci `producer` non ce
    l'hanno, e non è una dimenticanza: un `run_id` esiste per legare la riga di
    diario dentro la pull request alla riga di esito su master, e l'officina
    (`.claude/workflows/produci-indicatori.js`) non apre una pull request e non
    scrive nel diario. `pipeline_log.build_entry("producer", ...)` alza
    `SystemExit`, perché `producer` non è in `STAGES` (`STAGES` deriva da
    `pipeline_gate.STAGE_PATHS`, dove l'officina non compare per decisione: non
    ha un perimetro nel cancello). Coniarlo lo stesso era promettere un
    identificativo che il diario rifiuta. La chiave è **assente**, non vuota,
    così un consumatore futuro fallisce invece di scrivere `""`.
    """
    mint = mint or (lambda role: "")
    queues = queues or {}
    readings = readings or []
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

    # Una coda a monte accende l'ammissione se ha un conteggio positivo, o se è
    # stata contata e risulta incontabile (`None` esplicito nel dizionario, "vai a
    # vedere"). Una chiave assente è "nessuna informazione", non "forse lavoro":
    # scout/hunter/promoter sono sempre contabili, quindi None qui è raro e vero.
    adm_from_queue = any(
        (queues.get(stage) or 0) > 0 or (stage in queues and queues.get(stage) is None)
        for stage in ADMISSIONS_QUEUES
    )
    if adm_from_queue or adm_priorities:
        launches.append({
            "role": "admissions",
            **target("admissions", None),
            "indicator": None,
            "scope": "batch",
            "priority": max(adm_priorities) if adm_priorities else 0.0,
            "reason": _admissions_reason(adm_batch, len(adm_priorities)),
            "queues": adm_batch,
            "run_id": mint("admissions"),
        })

    # `producer_codes` raccoglie gli indicatori che già hanno un produttore in
    # questo tick, per non lanciarne due sullo stesso (il lanciatore non deduplica
    # le run in volo, quindi il doppione va evitato almeno entro il tick). Serve a
    # due sorgenti di produttore: la coda di `ready_stage` qui sotto e le
    # bocciature di leggibilità subito dopo.
    producer_codes = set()
    for code, stage, priority in producer_items:
        launches.append({
            "role": "producer",
            **target("producer", code),
            "indicator": code,
            "scope": "indicatore",
            "priority": priority,
            "reason": f"{code} pronto per il produttore (stadio d'ingresso {stage})",
        })
        producer_codes.add(code)

    # Le bocciature di leggibilità (`revise`, già senza i parcheggiati per il
    # freno K-round di reading_queue) tornano al produttore come una riscrittura.
    # Dedup per indicatore contro la coda di `ready_stage`: un indicatore già in
    # produzione per un altro motivo (un vintage scaduto) riscriverà comunque, e
    # un secondo lancio sarebbe il doppione che il lanciatore non sa evitare da sé.
    for row in readings:
        if row.get("status") != "revise":
            continue
        key = row.get("key")
        if key in producer_codes:
            continue
        producer_codes.add(key)
        d = (dossier or {}).get(key) or {}
        priority = float(d.get("priority", 0.0) or 0.0)
        launches.append({
            "role": "producer",
            **target("producer", key),
            "indicator": key,
            "scope": "indicatore",
            "priority": priority,
            "reason": _revise_reason(row),
        })

    for code, stage, priority in verifier_items:
        launches.append({
            "role": "verificatore",
            **target("verificatore", code),
            "indicator": code,
            "scope": "indicatore",
            "priority": priority,
            "reason": f"{code} firmato, nessuno ha ancora provato a smentirlo",
            "run_id": mint("verificatore"),
        })

    # I pubblicati che nessun reader-editor ha ancora letto sulla prosa di adesso.
    # Non passano da `ready_stage` (terminale su `pubblicata`): la loro coda è
    # l'assenza di una lettura, letta qui. Salta gli indicatori che in questo tick
    # hanno già un produttore: stanno per essere riscritti, leggerli ora è
    # sprecato (l'impronta cambierà e la lettura scadrebbe subito).
    for row in readings:
        if row.get("status") != "unread":
            continue
        key = row.get("key")
        if key in producer_codes:
            continue
        d = (dossier or {}).get(key) or {}
        priority = float(d.get("priority", 0.0) or 0.0)
        launches.append({
            "role": "reader-editor",
            **target("reader-editor", key),
            "indicator": key,
            "scope": "indicatore",
            "priority": priority,
            "reason": f"{row.get('code')} pubblicato, nessuna lettura di leggibilità",
            "run_id": mint("reader-editor"),
        })

    launches = _one_role_per_indicator(launches)
    launches.sort(key=lambda item: (-item["priority"],
                                    ROLE_ORDER.index(item["role"]),
                                    item["indicator"] or ""))
    return launches


def _one_role_per_indicator(launches):
    """Un indicatore, un ruolo per tick: vince il primo di `ROLE_ORDER`.

    Le liste sono indipendenti e possono nominare lo stesso indicatore. Il caso
    reale è un articolo appena firmato: entra fra i `verifier_items` (nessuno ha
    provato a smentirlo) **e** fra gli `unread` (nessuno l'ha letto), ed erano due
    voci che il lanciatore metteva in volo insieme. `ROLE_ORDER` non bastava a
    evitarlo: è solo il criterio che rompe i pari merito nell'ordinamento, e il
    lanciatore lancia in parallelo le voci in cima. Se poi la lettura boccia, la
    riscrittura cambia l'impronta e la verifica appena fatta scade: una run opus
    buttata, e proprio l'ordine "leggi prima, verifica dopo" che questa PR dice di
    volere. Nel piano vero erano 23 indicatori.

    Scartare qui non è perdere lavoro, è rimandarlo: il piano si ricalcola a
    ogni tick, quindi la verifica ricompare appena la lettura esiste. La voce che
    resta si tiene la priorità più alta fra quelle in collisione, così un
    indicatore non scende nel piano per il fatto di essere stato dedotto.
    """
    winner = {}
    for item in launches:
        code = item["indicator"]
        if code is None:
            continue
        current = winner.get(code)
        if current is None:
            winner[code] = item
            continue
        if ROLE_ORDER.index(item["role"]) < ROLE_ORDER.index(current["role"]):
            item["priority"] = max(item["priority"], current["priority"])
            winner[code] = item
        else:
            current["priority"] = max(current["priority"], item["priority"])
    return [item for item in launches
            if item["indicator"] is None or winner[item["indicator"]] is item]


def load_plan(today=""):
    """Collega i lettori reali (tutti stdlib puri) e ritorna il piano di lancio.

    La metà con l'IO, tenuta fuori da `plan_launches` così il nucleo resta
    provabile senza disco."""
    from scripts import pipeline_log, pipeline_status, reading_queue
    dossier = practice_timeline.load_real(today=today)
    queues = pipeline_status.queue_sizes()
    readings = reading_queue.build_queue()
    return plan_launches(dossier, queues, mint=pipeline_log.new_run_id, readings=readings)


def log_tick(launches, runner=None, do_commit=True, log=print):
    """Il battito del lanciatore: un tick `launch` nel diario, portato su master.

    È l'unico segno che il lanciatore è partito. Senza, una Routine che gira
    con il piano vuoto non lascia niente e ha lo stesso aspetto di una che non è
    mai partita, che è il guasto più pericoloso della catena (il silenzio letto
    come normalità). Il tick rende misurabile quel silenzio: `silence` guarda il
    gruppo `lanciatore`, e la sua unica fonte di dati è questo shard.

    Sta dentro il perimetro `launch` della guardia (solo journal). Il verso di
    prudenza del cancello vale anche qui: un push perso non è un errore del tick,
    si logga e si continua. `runner`/`do_commit` sono iniettabili così il test non
    tocca git.
    """
    from scripts import pipeline_log
    summary = f"tick: {len(launches)} unità pronte"
    entry = pipeline_log.build_entry("launch", "nothing", summary, trigger="routine")
    pipeline_log.append(entry)
    if not do_commit:
        return entry
    rel = f"data/pipeline/runs/{pipeline_log.shard_name(entry)}"
    kwargs = {"log": log, "label": "battito"}
    if runner is not None:
        kwargs["runner"] = runner
    try:
        if not pipeline_log.land_on_master([rel], "Diario: tick del lanciatore", **kwargs):
            log("  battito: non su master (corsa al push persa), il tick resta locale")
    except Exception as exc:  # un battito non deve far cadere il giro
        log(f"  battito: land_on_master fallito ({type(exc).__name__}), il tick resta locale")
    return entry


def cap_for_tick(launches, *, max_parallel=3, top=None, reserve_reader=1):
    """Le voci che il lanciatore lancia in un solo tick.

    Il piano è già ordinato per priorità, quindi prendere le prime
    `max_parallel` tiene il parallelismo basso senza mai tagliare la voce più
    urgente (una smentita pubblica, peso 100, sta in testa e resta). `top` è un
    override esplicito di visualizzazione; un cap di 0 (o None) non taglia.

    Uno slot è però riservato al reader-editor (`reserve_reader`, default 1). Le
    letture ereditano la priorità del dossier, che per un articolo già pubblicato
    è alta: senza riserva monopolizzerebbero il tick e fermerebbero il lavoro
    fattuale (produrre, verificare) per tutto lo smaltimento dell'arretrato. Con la
    riserva l'arretrato di lettura drena di una voce a tick e gli altri due slot
    restano al lavoro fattuale. Un reader-editor è un critico `soft`: cammina
    accanto alla catena, non le passa davanti. Se non c'è lavoro fattuale gli slot
    liberi si riempiono di letture; se non c'è lettura, la riserva non toglie
    niente."""
    cap = top if top is not None else (max_parallel or None)
    if not cap:
        return launches
    if top is not None:
        # Override esplicito di visualizzazione: la testa del piano com'è, senza
        # riserva (chi lo chiede vuole vedere l'ordine vero).
        return launches[:cap]
    readers = [item for item in launches if item.get("role") == "reader-editor"]
    others = [item for item in launches if item.get("role") != "reader-editor"]
    keep_readers = readers[:min(reserve_reader, cap)]
    keep_others = others[:cap - len(keep_readers)]
    chosen = keep_others + keep_readers
    if len(chosen) < cap:
        # Una delle due sponde è finita: riempi con l'altra, in ordine.
        pool = readers[len(keep_readers):] + others[len(keep_others):]
        chosen += pool[:cap - len(chosen)]
    chosen.sort(key=lambda item: (-item["priority"],
                                  ROLE_ORDER.index(item["role"]),
                                  item.get("indicator") or ""))
    return chosen


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Che cosa lanciare adesso nella catena per-indicatore, e in che ordine.",
        epilog="uscita 0 = c'è lavoro da lanciare, 1 = niente da lanciare.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-parallel", type=int, default=3,
                        help="quante voci in cima al piano lanciare per tick "
                             "(default 3, 0 = nessun cap). Il cap tiene basso il "
                             "numero di ruoli che partono insieme a ogni tick "
                             "della Routine: le voci sotto il taglio, già "
                             "ordinate per priorità, aspettano il tick dopo.")
    parser.add_argument("--top", type=int, default=None,
                        help="mostra solo le prime N voci (le più prioritarie)")
    parser.add_argument("--today", default="",
                        help="data di riferimento YYYY-MM-DD per la priorità")
    # `--publish` non fa più la verifica-sito (rimossa: il progetto ha ratificato
    # merge = pubblicazione). Il flag resta accettato, e a ogni tick vero della
    # Routine segna il battito del lanciatore nel diario. `--publish-base` resta
    # accettato e ignorato, così la Routine viva non erra su un argomento ignoto.
    parser.add_argument("--publish", action="store_true",
                        help="tick vero della Routine: segna il battito del lanciatore "
                             "nel diario, su master. Default spento (sola lettura).")
    parser.add_argument("--publish-base", default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    launches = load_plan(today=args.today)
    shown = cap_for_tick(launches, max_parallel=args.max_parallel, top=args.top)

    # Il battito, solo a un tick vero della Routine (`--publish`): una riga `launch`
    # che rende il suo silenzio misurabile. In sola lettura (`--json` senza
    # `--publish`, come nei test e nelle ispezioni a mano) non si scrive niente.
    if args.publish:
        log_tick(launches, log=(lambda *_: None) if args.json else print)

    if args.json:
        # A un tick vero (`--publish`) la forma resta un oggetto con `launches`:
        # è ciò che legge chi lancia. L'agente `launcher.md` non esiste più
        # (era un workflow scritto in prosa), quindi oggi lo legge un umano o un
        # workflow. In sola lettura resta l'array nudo, comodo per ispezioni.
        payload = {"launches": shown} if args.publish else shown
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if launches else 1

    if not launches:
        print("niente da lanciare: nessun indicatore ha lavoro pronto e le code a monte sono vuote.")
        return 1

    print(f"Catena Divario Italia, {len(launches)} unità di lavoro pronte "
          f"(indicatori diversi, lanciabili in parallelo):\n")
    for item in shown:
        target = item["indicator"] or "(coda intera)"
        print(f"  {item['priority']:6.1f}  {item['role']:12s} {target:24.24s} {item['reason']}")
        # Un ruolo che non è un agente stampa il comando, non "agente None":
        # il piano si legge per lanciare, quindi deve dire che cosa lanciare.
        if item.get("agent"):
            print(f"          agente {item['agent']}, run_id {item['run_id']}")
        else:
            print(f"          {item.get('comando', item.get('workflow', ''))}")
    if len(launches) > len(shown):
        print(f"\n  ... e altre {len(launches) - len(shown)} voci sotto il cap "
              f"di parallelismo ({len(shown)} per tick), al prossimo tick.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
