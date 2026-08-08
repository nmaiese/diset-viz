"""Lo stato della catena come lo vede il cruscotto: run e agenti di un workflow.

Sostituisce `app/pipeline_state.py`, che descriveva la catena editoriale
autonoma (un indicatore che attraversa stadi, battiti che scadono a sei ore, PR
aperte fotografate a ogni tick). Quella catena e' stata ritirata: adesso una run
e' **un workflow** con dentro N agenti, e questo modulo tiene le due tabelle che
lo dicono.

La regola che governa tutto il file, e l'unica da non rompere:

    il **battito** scrive certe colonne, il **consuntivo** ne scrive altre,
    e i due insiemi non si toccano mai.

Il battito arriva mentre la run gira, da chi legge i trascritti
(`lab/cruscotto.py`), e non conosce i token: il workflow non li conosce. Il
consuntivo arriva a run finita, dalla lettura degli stessi trascritti con
`scripts/baseline_tokens.py`, e non conosce lo stato vivo. Se le due sorgenti
scrivessero le stesse colonne, un consuntivo ripetuto o arrivato in ritardo
cancellerebbe quello che il vivo aveva registrato, e il cruscotto direbbe una
bugia proprio sulla run che qualcuno stava guardando.

Una Session per chiamata (vedi `app/db.py`): nessuna connessione condivisa fra
thread, in linea col deploy (gunicorn a piu' thread, un solo worker).

Tollerante di una tabella che non esiste ancora: su una macchina appena avviata
il cruscotto deve restare vuoto, non cadere.
"""

import json

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import session_scope
from app.models import PipelineAgente, PipelineRun

# Il valore di ritorno di un agente puo' essere un articolo intero. In una riga
# di cruscotto non ci sta e non ci serve: si tronca qui, dove il troncamento e'
# visibile, invece che nel browser dove sembrerebbe un dato mancante.
TETTO_RISULTATO = 20000

# Le colonne che ogni sorgente puo' scrivere. Elencate per **inclusione**: una
# colonna nuova resta fuori finche' qualcuno non decide a quale delle due
# sorgenti appartiene. Una lista per esclusione mentirebbe per omissione, ed e'
# lo stesso difetto che `scripts/baseline_tokens.py` ha gia' pagato con i ruoli.
#
# `workflow` e `args` stanno dalla parte del **consuntivo**, e non e' una scelta
# di gusto: dal vivo non esistono. I file che il runtime scrive mentre la run
# gira (`journal.jsonl`, `agent-<id>.meta.json`) portano gli agenti e i loro
# tipi, non il nome del workflow, che compare solo in `<runId>.json` a run
# finita. Metterli fra i campi del battito li faceva scrivere da nessuno, e la
# colonna restava vuota: trovato girando il lettore contro un server vero.
CAMPI_BATTITO_RUN = ("avviata_il", "ultimo_battito", "fase_stimata",
                     "agenti_visti", "sessione", "progetto")
CAMPI_CONSUNTIVO_RUN = ("workflow", "args", "stato", "durata_ms", "fasi", "esito", "logs", "agenti",
                        "turni", "tool", "token_in", "token_cache_w",
                        "token_cache_r", "token_out", "advisor_in", "advisor_out",
                        "advisor_chiamate", "costo", "costo_pavimento",
                        "consuntivo_il")
CAMPI_BATTITO_AGENTE = ("agent_type", "fase_stimata", "indicatore", "avviato_il",
                        "chiuso_il", "stato_vivo", "risultato")
CAMPI_CONSUNTIVO_AGENTE = ("label", "fase", "modello", "stato", "turni", "tool",
                           "strumenti", "token_in", "token_cache_w",
                           "token_cache_r", "token_out", "advisor_in",
                           "advisor_out", "advisor_chiamate", "costo")

_JSON_RUN = ("args", "fasi", "esito", "logs")
_JSON_AGENTE = ("risultato", "strumenti")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _testo(valore, tetto=None):
    """Un campo strutturato diventa JSON in Text; una stringa resta se stessa.

    Chi chiama puo' mandare gia' una stringa JSON (il lettore la costruisce
    cosi') o un oggetto: si accettano entrambi, perche' rifiutarne uno dei due
    farebbe perdere righe per una differenza che non conta."""
    if valore is None:
        return None
    testo = valore if isinstance(valore, str) else json.dumps(valore, ensure_ascii=False)
    return testo[:tetto] if tetto else testo


def _carica(testo, default):
    if not testo:
        return default
    try:
        return json.loads(testo)
    except (ValueError, TypeError):
        return default


def _applica(riga, payload, campi, json_campi=(), tetto=None, salta_nulli=False):
    """Scrive su `riga` **solo** i campi dell'insieme dichiarato che il payload
    porta davvero. Un campo assente non azzera quello che c'e': un battito
    parziale non deve cancellare un battito piu' completo.

    `salta_nulli` serve al battito, dove `None` vuol dire "non lo so ancora" e
    non "vuoto": un agente aperto non ha ancora restituito niente, e il lettore
    manda `risultato: null`. Scriverlo farebbe fallire la colonna, che non e'
    nullable, e con lei l'intero POST (visto girando il lettore contro un server
    vero: 500 su ogni agente aperto). Le colonne di consuntivo invece sono
    nullable e un `None` la' dentro e' un'informazione, quindi passa."""
    scritti = 0
    for campo in campi:
        if campo not in payload:
            continue
        valore = payload[campo]
        if salta_nulli and valore is None:
            continue
        if campo in json_campi:
            valore = _testo(valore, tetto if campo == "risultato" else None)
        setattr(riga, campo, valore)
        scritti += 1
    return scritti


# ------------------------------------------------------------------ scrittura

def registra_run(run_id, payload, now=None):
    """Il battito di una run: la prima riga la crea, le successive la aggiornano.

    Scrive solo `CAMPI_BATTITO_RUN`. `ultimo_battito` lo mette il server e non
    chi chiama, cosi' la freschezza si legge sull'orologio di una macchina sola.
    """
    if not run_id:
        raise ValueError("run_id mancante")
    dati = dict(payload or {})
    dati["ultimo_battito"] = now or _now()
    dati.setdefault("avviata_il", dati["ultimo_battito"])
    with session_scope() as s:
        riga = s.get(PipelineRun, run_id)
        if riga is None:
            riga = PipelineRun(run_id=run_id)
            s.add(riga)
        elif riga.avviata_il:
            # `avviata_il` la fissa il primo battito: un battito successivo che
            # la riportasse sposterebbe indietro l'inizio e falserebbe la durata.
            #
            # La guardia e' sul **valore**, non sull'esistenza della riga: la
            # riga puo' esistere perche' l'ha creata il consuntivo (che arriva
            # per primo quando il lettore parte a run gia' finita), e in quel
            # caso `avviata_il` e' ancora vuota e il primo battito deve poterla
            # scrivere. Con la guardia sull'esistenza, quella run restava senza
            # inizio e finiva in fondo a un elenco ordinato per tempo.
            dati.pop("avviata_il", None)
        _applica(riga, dati, CAMPI_BATTITO_RUN, _JSON_RUN, salta_nulli=True)


def registra_agente(run_id, agent_id, payload):
    """Il battito di un agente: aperto quando compare, chiuso col suo valore di
    ritorno quando il journal lo registra. Scrive solo `CAMPI_BATTITO_AGENTE`."""
    if not run_id or not agent_id:
        raise ValueError("run_id o agent_id mancante")
    with session_scope() as s:
        # La run si legge partendo da `pipeline_run`: un agente la cui run non
        # esiste sparirebbe dal cruscotto senza che niente lo dica. Succede se
        # il POST della run si perde e quello dell'agente passa, ed e' proprio
        # nell'orizzonte in tempo reale che la perdita si noterebbe di meno.
        if s.get(PipelineRun, run_id) is None:
            s.add(PipelineRun(run_id=run_id))
        riga = s.get(PipelineAgente, (run_id, agent_id))
        if riga is None:
            riga = PipelineAgente(run_id=run_id, agent_id=agent_id)
            s.add(riga)
        _applica(riga, dict(payload or {}), CAMPI_BATTITO_AGENTE, _JSON_AGENTE,
                 tetto=TETTO_RISULTATO, salta_nulli=True)


def registra_consuntivo(run_id, run, agenti, now=None):
    """Il consuntivo di una run finita: la run e i suoi agenti in un colpo solo.

    Scrive solo le colonne di consuntivo, quindi puo' arrivare in qualsiasi
    ordine rispetto ai battiti, anche prima (una run gia' finita quando il
    lettore parte) e anche due volte, senza cancellare niente."""
    if not run_id:
        raise ValueError("run_id mancante")
    dati = dict(run or {})
    dati["consuntivo_il"] = now or _now()
    with session_scope() as s:
        riga = s.get(PipelineRun, run_id)
        if riga is None:
            riga = PipelineRun(run_id=run_id)
            s.add(riga)
        _applica(riga, dati, CAMPI_CONSUNTIVO_RUN, _JSON_RUN)
        for agente in agenti or []:
            agent_id = agente.get("agent_id")
            if not agent_id:
                continue
            sotto = s.get(PipelineAgente, (run_id, agent_id))
            if sotto is None:
                sotto = PipelineAgente(run_id=run_id, agent_id=agent_id)
                s.add(sotto)
            _applica(sotto, agente, CAMPI_CONSUNTIVO_AGENTE, _JSON_AGENTE)


# ------------------------------------------------------------------- lettura

def _riga_run(r, agenti):
    return {
        "run_id": r.run_id,
        "workflow": r.workflow,
        "args": _carica(r.args, []),
        "avviata_il": r.avviata_il,
        "ultimo_battito": r.ultimo_battito,
        "fase_stimata": r.fase_stimata,
        "agenti_visti": r.agenti_visti,
        "sessione": r.sessione,
        "progetto": r.progetto,
        "stato": r.stato,
        "in_volo": r.stato is None,
        "durata_ms": r.durata_ms,
        "fasi": _carica(r.fasi, []),
        "esito": _carica(r.esito, None),
        "logs": _carica(r.logs, []),
        "agenti": agenti,
        "turni": r.turni,
        "tool": r.tool,
        "token": {"in": r.token_in, "cache_w": r.token_cache_w,
                  "cache_r": r.token_cache_r, "out": r.token_out},
        "advisor": {"in": r.advisor_in, "out": r.advisor_out,
                    "chiamate": r.advisor_chiamate},
        "costo": r.costo,
        "costo_pavimento": bool(r.costo_pavimento) if r.costo_pavimento is not None else None,
        "consuntivo_il": r.consuntivo_il,
    }


def _riga_agente(a):
    return {
        "agent_id": a.agent_id,
        "agent_type": a.agent_type,
        "fase": a.fase or a.fase_stimata,
        # Il cruscotto deve poter dire "questa fase e' una stima del vivo, non
        # la verita' del consuntivo": senza questo flag mostrerebbe le due cose
        # con la stessa faccia.
        "fase_stimata": a.fase is None,
        "label": a.label,
        "indicatore": a.indicatore,
        "modello": a.modello,
        "stato": a.stato,
        "stato_vivo": a.stato_vivo,
        "avviato_il": a.avviato_il,
        "chiuso_il": a.chiuso_il,
        "risultato": _carica(a.risultato, None),
        "turni": a.turni,
        "tool": a.tool,
        "strumenti": _carica(a.strumenti, {}),
        "token": {"in": a.token_in, "cache_w": a.token_cache_w,
                  "cache_r": a.token_cache_r, "out": a.token_out},
        "advisor": {"in": a.advisor_in, "out": a.advisor_out,
                    "chiamate": a.advisor_chiamate},
        "costo": a.costo,
    }


def run(limite=100):
    """Le run piu' recenti, ognuna con i suoi agenti in ordine di avvio.

    Ordinate per `avviata_il` decrescente: una run in volo sta in cima perche'
    e' la piu' recente, non perche' qualcuno la promuova."""
    try:
        with session_scope() as s:
            righe = s.execute(
                select(PipelineRun).order_by(PipelineRun.avviata_il.desc()).limit(limite)
            ).scalars().all()
            ids = [r.run_id for r in righe]
            agenti = s.execute(
                select(PipelineAgente).where(PipelineAgente.run_id.in_(ids))
                .order_by(PipelineAgente.avviato_il)
            ).scalars().all() if ids else []
            per_run = {}
            for a in agenti:
                per_run.setdefault(a.run_id, []).append(_riga_agente(a))
            return [_riga_run(r, per_run.get(r.run_id, [])) for r in righe]
    except SQLAlchemyError:
        return []
