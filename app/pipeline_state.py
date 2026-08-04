"""Lo stato **vivo** della catena, su cui il cruscotto /_pipeline si aggiorna.

Il cruscotto sembrava morto per una ragione strutturale. I battiti che ogni
ruolo lasciava erano file locali, ignorati da git, scritti sul disco effimero
dell'agente cloud: il server che serve divarioitalia.it e' un'altra macchina, e
quei file non la raggiungevano mai. L'unico canale condiviso era il commit su
master, che pero' compare solo a merge avvenuto (e su Cloud Run solo dopo un
rebuild dell'immagine), quindi il lavoro in volo restava invisibile.

Questo modulo chiude il buco riusando il backend mutabile condiviso: le stesse
tabelle stanno su Postgres (Supabase) in produzione e su SQLite in test. Gli
agenti non scrivono qui direttamente (non hanno credenziali): fanno un POST
all'endpoint del sito, che scrive queste tabelle. Cosi' il battito e' vivo,
condiviso fra le macchine, e non sporca master di un commit per battito.

Una riga e' `beat` (un ruolo che lavora, prima ancora che ci sia una PR) o `pr`
(una PR aperta su `automation/*`, con stato CI e mergeabilita', che il lanciatore
fotografa a ogni tick). Le righe piu' vecchie della soglia si considerano morte,
come i vecchi battiti su file: una sessione caduta senza chiudere non resta in
pagina per sempre.

Una Session per chiamata (vedi app/db.py), come prima: nessuna connessione
condivisa fra thread, in linea col deploy (gunicorn a piu' thread, un solo
worker).
"""

import json

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.db import session_scope
from app.models import PipelineActivity, PipelineOutcome, PipelineToken

STALE_HOURS = 6


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


def record_beat(run_id, role="", indicator="", stage="", now=None):
    """Un ruolo che parte (o continua) lascia il proprio battito. Idempotente sul
    `run_id`, cosi' un aggiornamento sostituisce il precedente."""
    if not run_id:
        raise ValueError("run_id mancante")
    stamp = now or _now()
    key = f"beat:{run_id}"
    with session_scope() as s:
        row = s.get(PipelineActivity, key)
        if row is None:
            s.add(PipelineActivity(
                key=key, kind="beat", role=role, indicator=indicator,
                stage=stage, run_id=run_id, updated_at=stamp))
        else:
            row.role, row.indicator, row.stage, row.updated_at = role, indicator, stage, stamp


def close_beat(run_id):
    """Un ruolo che chiude cancella il proprio battito."""
    if not run_id:
        return
    with session_scope() as s:
        s.execute(delete(PipelineActivity).where(PipelineActivity.key == f"beat:{run_id}"))


def replace_prs(prs, now=None):
    """Sostituisce in blocco la fotografia delle PR aperte (il lanciatore la
    riscrive a ogni tick). Atomico: o c'e' la nuova, o resta la vecchia."""
    stamp = now or _now()
    with session_scope() as s:
        s.execute(delete(PipelineActivity).where(PipelineActivity.kind == "pr"))
        for pr in prs or []:
            number = pr.get("pr")
            s.add(PipelineActivity(
                key=f"pr:{number}", kind="pr", role=pr.get("role", ""),
                indicator=pr.get("indicator", ""), run_id=pr.get("run_id", ""),
                pr=number, branch=pr.get("branch", ""), ci=pr.get("ci", ""),
                mergeable=pr.get("mergeable", ""), title=pr.get("title", ""),
                updated_at=stamp))


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
    with session_scope() as s:
        row = s.get(PipelineToken, run_id)
        if row is None:
            s.add(PipelineToken(run_id=run_id, indicator=indicator, stage=stage,
                                role=role, tokens=n, updated_at=stamp))
        else:
            row.tokens, row.indicator, row.stage, row.role, row.updated_at = \
                n, indicator, stage, role, stamp


def tokens_by_run():
    """Il consumo token per run_id, `{run_id: {tokens, indicator, stage, role, since}}`.

    Durevole: **non** filtrato dalla finestra di freschezza, a differenza di
    `live()`. Tollerante di una tabella non ancora creata (niente token = mappa
    vuota, il cruscotto non deve cadere per la telemetria)."""
    try:
        with session_scope() as s:
            rows = s.execute(select(
                PipelineToken.run_id, PipelineToken.tokens, PipelineToken.indicator,
                PipelineToken.stage, PipelineToken.role, PipelineToken.updated_at)).all()
    except SQLAlchemyError:
        return {}
    return {run_id: {"tokens": tokens, "indicator": indicator, "stage": stage,
                     "role": role, "since": updated_at}
            for run_id, tokens, indicator, stage, role, updated_at in rows}


def live(now=None, stale_hours=STALE_HOURS):
    """Le righe vive: battiti e PR piu' recenti della soglia. `{beats, prs}`.

    Tollerante di una tabella che non esiste ancora (il DB puo' non essere mai
    stato scritto su una macchina appena avviata): in quel caso, niente vivo."""
    ref = now or _now()
    cutoff = _cutoff(ref, stale_hours)
    try:
        with session_scope() as s:
            rows = s.execute(
                select(PipelineActivity)
                .where(PipelineActivity.updated_at >= cutoff)
                .order_by(PipelineActivity.updated_at.desc())).scalars().all()
    except SQLAlchemyError:
        return {"beats": [], "prs": []}
    beats, prs = [], []
    for r in rows:
        item = {"role": r.role, "indicator": r.indicator, "stage": r.stage,
                "run_id": r.run_id, "pr": r.pr, "branch": r.branch, "ci": r.ci,
                "mergeable": r.mergeable, "title": r.title, "since": r.updated_at}
        (prs if r.kind == "pr" else beats).append(item)
    return {"beats": beats, "prs": prs}


# I campi dello snapshot che la board legge dal dossier ricostruito. Le prime tre
# strutture viaggiano come JSON in Text; `published`/`verification_valid` come
# interi nullable (tri-stato); il resto come stringa.
_OUTCOME_JSON = ("completed_stages", "required_stages", "flags")
_OUTCOME_TRISTATE = ("published", "verification_valid")


def _tri_to_int(value):
    """`True`/`False`/`None` -> `1`/`0`/`None`. Tiene il tri-stato in una colonna
    intera nullable, senza inventare un terzo valore."""
    if value is None:
        return None
    return 1 if value else 0


def record_outcome(indicator, run_id, snapshot, at="", base_commit="", now=None):
    """Lo snapshot di stato di un indicatore, chiavato su `indicator`. Idempotente,
    l'ultimo vince, MA con una guardia su `at`: uno snapshot piu' vecchio non
    sovrascrive uno piu' recente gia' registrato (due run sullo stesso indicatore
    che fondono quasi insieme, o un POST che arriva fuori ordine). Durevole: non
    scade, a differenza dei battiti.

    `snapshot` e' il payload dell'agente, da cui si leggono i campi del dossier
    (`state`, `completed_stages`, `flags`, `published`, ...). I campi non presenti
    prendono un default neutro."""
    if not indicator:
        raise ValueError("indicator mancante")
    stamp = now or _now()
    at = at or stamp
    snap = snapshot or {}
    values = {
        "run_id": run_id or "",
        "at": at,
        "base_commit": base_commit or "",
        "state": str(snap.get("state", "")),
        "type": str(snap.get("type", "")),
        "entered_at": str(snap.get("entered_at", "")),
        "completed_stages": json.dumps(snap.get("completed_stages") or []),
        "required_stages": json.dumps(snap.get("required_stages") or []),
        "flags": json.dumps(snap.get("flags") or {}),
        "published": _tri_to_int(snap.get("published")),
        "verification_valid": _tri_to_int(snap.get("verification_valid")),
        "score_eligible": 1 if snap.get("score_eligible") else 0,
        "error_class": snap.get("error_class"),
        "motivo": str(snap.get("motivo", "")),
        "priority": "" if snap.get("priority") is None else str(snap.get("priority")),
        "updated_at": stamp,
    }
    with session_scope() as s:
        row = s.get(PipelineOutcome, indicator)
        if row is not None and row.at and row.at > at:
            # Arrivato dopo, ma piu' vecchio: non e' l'ultimo stato, lo ignoro.
            return
        if row is None:
            s.add(PipelineOutcome(indicator=indicator, **values))
        else:
            for field, value in values.items():
                setattr(row, field, value)


def outcomes_by_indicator():
    """Gli snapshot vivi per indicatore, `{indicator: {...}}`, gia' deserializzati.

    Durevole: **non** filtrato dalla finestra di freschezza (come `tokens_by_run`,
    non come `live`). Tollerante di una tabella non ancora creata (niente overlay
    = mappa vuota, la board non deve cadere per questo) e di una riga con JSON
    corrotto (che degrada ai default, non fa cadere il resto)."""
    try:
        with session_scope() as s:
            rows = s.execute(select(PipelineOutcome)).scalars().all()
    except SQLAlchemyError:
        return {}
    out = {}
    for r in rows:
        out[r.indicator] = {
            "run_id": r.run_id,
            "at": r.at,
            "base_commit": r.base_commit,
            "state": r.state,
            "type": r.type,
            "entered_at": r.entered_at,
            "completed_stages": _load_json(r.completed_stages, []),
            "required_stages": _load_json(r.required_stages, []),
            "flags": _load_json(r.flags, {}),
            "published": None if r.published is None else bool(r.published),
            "verification_valid": (None if r.verification_valid is None
                                   else bool(r.verification_valid)),
            "score_eligible": bool(r.score_eligible),
            "error_class": r.error_class,
            "motivo": r.motivo,
            "priority": _to_float(r.priority, 0.0),
        }
    return out


def _load_json(text, default):
    """Deserializza un campo JSON-in-Text, degradando al default se e' vuoto o
    corrotto: una riga difettosa non deve far sparire tutte le altre."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


def _to_float(text, default):
    """Come `_load_json`, ma per `priority`: un valore non numerico degrada al
    default invece di far cadere l'intera mappa (una riga sola non deve zittire
    l'overlay di tutte le altre)."""
    if not text:
        return default
    try:
        return float(text)
    except (ValueError, TypeError):
        return default
