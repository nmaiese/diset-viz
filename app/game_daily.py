"""Sfida del giorno: il giorno del gioco e' quello di Roma.

Un'unica funzione, `oggi_roma()`, dice che giorno e' per il gioco. Il server
gira in UTC (Cloud Run): senza questa funzione la sfida nuova uscirebbe all'una
o alle due di notte in Italia, e un punto che usa `date.today()` darebbe un
giorno diverso da quello che il giocatore vede. I timestamp restano in UTC.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")


def oggi_roma(now=None):
    """Il giorno corrente a Roma. `now` (datetime con fuso) serve ai test."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ROMA).date()


def prossima_sfida_roma(oggi=None):
    """ISO 8601 UTC della mezzanotte di Roma che apre il giorno dopo `oggi`."""
    oggi = oggi or oggi_roma()
    mezzanotte = datetime.combine(oggi + timedelta(days=1), datetime.min.time(), tzinfo=ROMA)
    return mezzanotte.astimezone(timezone.utc).isoformat()
