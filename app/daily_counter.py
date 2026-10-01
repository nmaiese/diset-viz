"""Il contatore delle sfide del giorno finite: una misura lato server, senza consenso.

L'analitica del sito dipende dal consenso, e in 90 giorni ha visto circa sei partite
finite. Questo contatore non passa dal browser: la rotta che riceve l'ultima risposta di
una sfida legata a un token lo incrementa, e basta. Una riga per `(gioco, data,
punteggio)` con quante sfide sono finite cosi'.

Niente account, niente sessione, niente IP, niente identificativo di alcun tipo: solo
numeri aggregati. Per questo non serve chiedere niente a nessuno, e per lo stesso motivo
non si puo' sapere quante di quelle partite siano della stessa persona.

`record` non solleva mai: una misura che rompe la risposta al giocatore costa piu' di
quanto vale. Un errore finisce nel log e la partita prosegue.
"""

import logging
import re
from datetime import date

from sqlalchemy import select

from app.db import session_scope
from app.models import DailyCounter

log = logging.getLogger(__name__)

_GAME_NAME = re.compile(r"^[a-z][a-z_]{0,31}$")
# Un tetto di buon senso: la sfida piu' lunga ha dieci round, oltre mille e' un errore.
MAX_SCORE = 1000


def _is_valid(game, day, score):
    if not isinstance(game, str) or not _GAME_NAME.match(game):
        return False
    if not isinstance(day, str):
        return False
    try:
        date.fromisoformat(day)
    except ValueError:
        return False
    if isinstance(score, bool) or not isinstance(score, int):
        return False
    return 0 <= score <= MAX_SCORE


def _upsert(session, game, day, score):
    """`INSERT ... ON CONFLICT DO UPDATE conteggio + 1`: atomico, due richieste insieme
    non si perdono un incremento. Un solo punto distingue il dialetto."""
    if session.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as _insert
    else:
        from sqlalchemy.dialects.sqlite import insert as _insert
    stmt = _insert(DailyCounter).values(gioco=game, data=day, punteggio=score, conteggio=1)
    session.execute(stmt.on_conflict_do_update(
        index_elements=["gioco", "data", "punteggio"],
        set_={"conteggio": DailyCounter.conteggio + 1},
    ))


def record(game, day, score):
    """Conta una sfida finita. `data` e' il giorno della sfida (ISO), `punteggio` un
    intero. Ritorna True se ha scritto, False se l'input non era valido o il DB ha
    fallito (e in quel caso lo dice nel log). Non solleva mai."""
    try:
        if not _is_valid(game, day, score):
            log.warning("daily_counter: input non valido, niente da contare (%r, %r, %r)", game, day, score)
            return False
        with session_scope() as s:
            _upsert(s, game, day, score)
        return True
    except Exception:  # noqa: BLE001 - una misura non rompe mai la partita
        log.exception("daily_counter: conteggio non scritto")
        return False


def totals(game=None, since=None, until=None):
    """Le partite finite, una voce per `(data, gioco)`: `{"gioco", "data", "partite",
    "punteggi": {punteggio: conteggio}}`, in ordine di data e poi di gioco. `gioco`
    filtra un solo gioco; `da` e `a` sono date ISO incluse (o None per nessun limite)."""
    stmt = select(DailyCounter)
    if game:
        stmt = stmt.where(DailyCounter.gioco == game)
    if since:
        stmt = stmt.where(DailyCounter.data >= since)
    if until:
        stmt = stmt.where(DailyCounter.data <= until)
    with session_scope() as s:
        rows = s.execute(stmt).scalars().all()
    entries = {}
    for row in rows:
        entry = entries.setdefault((row.data, row.gioco), {
            "gioco": row.gioco, "data": row.data, "partite": 0, "punteggi": {}})
        entry["partite"] += row.conteggio
        entry["punteggi"][row.punteggio] = row.conteggio
    return [entries[k] for k in sorted(entries)]
