"""Le partite finite delle sfide del giorno, per gioco e per giorno.

Legge `daily_counter` (vedi `app/daily_counter.py`): la misura lato server, che conta
anche chi ha rifiutato il consenso alle analitiche. Niente account ne' identificativi,
solo aggregati.

    bin/py scripts/partite_giocate.py                    # ultimi 14 giorni
    bin/py scripts/partite_giocate.py --giorni 30
    bin/py scripts/partite_giocate.py --da 2026-10-01 --a 2026-10-07
    bin/py scripts/partite_giocate.py --gioco compare --punteggi

Con `DATABASE_URL` in ambiente legge il Postgres di Supabase, senza il file SQLite
locale. `--punteggi` aggiunge la distribuzione: "8:3" vuol dire tre partite finite con 8.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import daily_counter, game_daily  # noqa: E402


def righe(voci, con_punteggi=False):
    """Le righe di testo, una per `(data, gioco)`, e in coda il totale per gioco."""
    if not voci:
        return ["Nessuna partita finita nel periodo."]
    out = [f"{'data':<12}{'gioco':<20}{'partite':>8}" + ("  punteggi" if con_punteggi else "")]
    totale = {}
    for v in voci:
        riga = f"{v['data']:<12}{v['gioco']:<20}{v['partite']:>8}"
        if con_punteggi:
            riga += "  " + " ".join(f"{p}:{c}" for p, c in sorted(v["punteggi"].items()))
        out.append(riga)
        totale[v["gioco"]] = totale.get(v["gioco"], 0) + v["partite"]
    out.append("")
    out.append("Totale per gioco")
    for gioco in sorted(totale):
        out.append(f"{gioco:<32}{totale[gioco]:>8}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gioco", help="un solo gioco (compare, order, provincia, provincia_regione)")
    ap.add_argument("--da", help="prima data, ISO (default: --giorni fa)")
    ap.add_argument("--a", help="ultima data, ISO (default: oggi)")
    ap.add_argument("--giorni", type=int, default=14, help="finestra di default, in giorni (14)")
    ap.add_argument("--punteggi", action="store_true", help="mostra anche la distribuzione dei punteggi")
    args = ap.parse_args(argv)

    a = args.a or game_daily.oggi_roma().isoformat()
    da = args.da or (date.fromisoformat(a) - timedelta(days=args.giorni - 1)).isoformat()
    for riga in righe(daily_counter.totals(args.gioco, da, a), args.punteggi):
        print(riga)
    return 0


if __name__ == "__main__":
    sys.exit(main())
