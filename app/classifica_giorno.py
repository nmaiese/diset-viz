"""La classifica del giorno di Indovina la Regione.

Legge solo `daily_results` (il risultato giornaliero, scritto dalla guess) e
`profiles` (il nickname). Ordina per tentativi, poi per ora di arrivo: l'ora sta
in `daily_scores` (gioco `indovina`), scritta dalla stessa guess. Chi ha un
risultato senza quella riga (registrato prima che la guess la scrivesse) viene
dopo a parità di tentativi.

Compare solo chi ha un account, un nickname non vuoto e che supera ancora
`moderation.validate_nickname`. Nessun dato personale esce: né id né email.
"""

from sqlalchemy import select

from app import game_daily, moderation
from app.db import session_scope
from app.models import DailyResult, DailyScore, Profile

DEFAULT_LIMIT = 20
MAX_LIMIT = 20


def classifica_oggi(limit=DEFAULT_LIMIT, giorno=None):
    """[{rank, nickname, attempts, when}] di chi ha risolto la sfida di oggi."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    giorno = (giorno or game_daily.oggi_roma()).isoformat()
    with session_scope() as s:
        righe = s.execute(
            select(Profile.nickname, DailyResult.attempts, DailyScore.created_at)
            .join(Profile, Profile.auth_id == DailyResult.auth_id)
            .outerjoin(DailyScore, (DailyScore.auth_id == DailyResult.auth_id)
                       & (DailyScore.gioco == "indovina") & (DailyScore.data == giorno))
            .where(DailyResult.puzzle_date == giorno, DailyResult.solved == 1)
            .order_by(DailyResult.attempts.asc(),
                      DailyScore.created_at.is_(None), DailyScore.created_at.asc(),
                      DailyResult.auth_id.asc())
        ).all()
    voci = []
    for nickname, attempts, arrivo in righe:
        pulito, errore = moderation.validate_nickname(nickname)
        if errore:
            continue
        voci.append({"rank": len(voci) + 1, "nickname": pulito, "attempts": attempts, "when": arrivo})
        if len(voci) >= limit:
            break
    return voci
