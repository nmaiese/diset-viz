"""Fase 2: quanto si cerca ogni tema, se sta crescendo, e dove.

Usa Google Trends attraverso `pytrends`, che non e' una dipendenza del sito e
non ci deve diventare: si lancia in un ambiente usa-e-getta con uv.

    ~/.local/bin/uv run --no-project --with pytrends --with "urllib3<2" \\
        --with pandas python -m scripts.trend_articles.interest --day 2026-09-23

Per ogni tema di `config/trend_topics.json`, per ogni query in `trends`:

- **crescita** (`growth`): media dell'interesse negli ultimi 7 giorni diviso la
  media degli 83 giorni prima (finestra `today 3-m`). Sopra 1 il tema sale.
- **livello** (`level_vs_anchor`): interesse medio degli ultimi 7 giorni
  **rispetto a una query di riferimento fissa** ("pensioni"), nella stessa
  richiesta. Google Trends normalizza ogni richiesta a 100 sul suo massimo,
  quindi due temi si confrontano solo se passano per la stessa ancora.
- **regioni** (`regions_7d`): interesse per regione negli ultimi 7 giorni
  (0-100, relativo alla regione dove la quota di ricerche e' piu' alta).

Sono **indici relativi, non volumi di ricerca**. Nel testo di un articolo non
si scrivono mai come "N ricerche": si puo' dire che un tema e' cresciuto, e in
quali regioni e' piu' cercato, citando Google Trends e la finestra.

Se Google risponde 429 (troppe richieste) lo script aspetta e riprova. Se
fallisce comunque, il tema resta senza misura, l'errore finisce nel file e la
classifica lo tratta come dato mancante, non come zero.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from zoneinfo import ZoneInfo

from scripts.trend_articles import common

# "meteo" era troppo forte: al primo giro (23 settembre 2026) schiacciava
# a zero il livello di tutti i temi. Un'ancora deve stare nello stesso ordine
# di grandezza dei temi che misura.
ANCHOR = "pensioni"
PAUSE = 6


def _retry(call, label: str, errors: list, attempts: int = 3):
    for attempt in range(attempts):
        try:
            return call()
        except Exception as error:  # noqa: BLE001 - pytrends solleva eccezioni generiche anche per i 429
            wait = PAUSE * (attempt + 2) * 2
            print(f"    {label}: {error!r}, riprovo tra {wait}s", file=sys.stderr)
            if attempt == attempts - 1:
                errors.append({"request": label, "error": repr(error)})
            time.sleep(wait)
    return None


def measure(trend, query: str, errors: list) -> dict:
    result: dict = {"query": query}

    def over_time(words, window):
        trend.build_payload(words, geo="IT", timeframe=window)
        return trend.interest_over_time()

    def by_region():
        trend.build_payload([query], geo="IT", timeframe="now 7-d")
        table = trend.interest_by_region(resolution="REGION", inc_low_vol=True)
        return {str(k): int(v) for k, v in table[query].items()}

    history = _retry(lambda: over_time([query], "today 3-m"), f"{query} today 3-m", errors)
    time.sleep(PAUSE)
    if history is not None and not history.empty:
        values = history[query].tolist()
        recent, before = values[-7:], values[:-7]
        mean_before = sum(before) / len(before) if before else 0
        mean_recent = sum(recent) / len(recent)
        result["mean_7d"] = round(mean_recent, 1)
        result["mean_83d_before"] = round(mean_before, 1)
        result["growth"] = round(mean_recent / mean_before, 2) if mean_before else None
        result["series_90d"] = {str(i.date()): int(v) for i, v in history[query].items()}
    compared = _retry(lambda: over_time([query, ANCHOR], "now 7-d"), f"{query} vs {ANCHOR}", errors)
    time.sleep(PAUSE)
    if compared is not None and not compared.empty:
        anchor = compared[ANCHOR].mean()
        result["level_vs_anchor"] = round(compared[query].mean() / anchor, 3) if anchor else None
    result["regions_7d"] = _retry(by_region, f"regioni {query}", errors)
    time.sleep(PAUSE)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--day", help="cartella di lavoro AAAA-MM-GG (default: oggi, ora italiana)")
    parser.add_argument("--topics", nargs="*", help="solo questi id di tema")
    args = parser.parse_args(argv)

    from pytrends.request import TrendReq

    day = args.day or dt.datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    trend = TrendReq(hl="it-IT", tz=-120, timeout=(10, 30))
    topics = common.read_json(common.TOPICS_CONFIG)["topics"]
    if args.topics:
        topics = [t for t in topics if t["id"] in args.topics]

    results, errors = {}, []
    for topic in topics:
        print(f"  {topic['id']}", flush=True)
        results[topic["id"]] = [measure(trend, q, errors) for q in topic["trends"]]

    out = common.day_dir(day) / "interest.json"
    previous = common.read_json(out)["topics"] if out.exists() else {}
    previous.update(results)
    common.write_json(out, {
        "source": "Google Trends (pytrends), geo=IT",
        "anchor": ANCHOR,
        "detected": day,
        "note": "Indici relativi 0-100, non volumi di ricerca.",
        "topics": previous,
        "errors": errors,
    })
    print(f"-> {out.relative_to(common.ROOT)} ({len(errors)} richieste fallite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
