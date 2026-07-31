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

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.db import session_scope
from app.models import PipelineActivity, PipelineToken

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
