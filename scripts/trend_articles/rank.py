"""Fase 3: dal tema all'indicatore, e la classifica di che cosa scrivere.

Ogni coppia tema-indicatore prende tre punteggi fra 0 e 1, e ognuno si
legge da solo nel file di uscita, con la sua motivazione:

**interesse** (`interest`), quanto il tema e' cercato e discusso adesso:
  - `news`: quanti titoli degli ultimi sette giorni confermano il tema
    (ricerca Google News, tenuti solo quelli dove una parola del tema compare
    davvero), in scala logaritmica sul tema piu' coperto.
  - `topical`: 1 se il tema e' fra le ricerche di tendenza di Google o fra
    le notizie principali di oggi, 0,5 se tocca una pubblicazione Istat
    recente, 0 altrimenti.
  - `growth` e `level` da Google Trends (`interest.json`), se ci sono.
    Se mancano, il peso si ridistribuisce sugli altri: un dato mancante non e'
    uno zero.

**dato** (`data`), quanto e' solido l'indicatore che da' il contesto:
  - recenza dell'ultimo anno (2025 = 1, poi scende),
  - copertura (103 province = 1, 20 regioni = 0,8),
  - profondita' della serie (otto anni o piu' = 1).

**storia** (`story`), se nei dati c'e' qualcosa da raccontare, calcolata dai
valori: un territorio a oltre 2,5 deviazioni dagli altri nell'ultimo anno,
un'inversione della media dei territori, un divario Mezzogiorno/Centro-Nord
che si allarga o si stringe di oltre un quarto, un record della serie. Il
punteggio e' il piu' forte dei quattro: una storia basta.

Il **totale** e' interesse x (dato + storia) / 2, e una coppia si scarta se
l'interesse e' sotto 0,25 o il dato sotto 0,5.

    bin/py -m scripts.trend_articles.rank --day 2026-09-23
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import statistics
import sys
from zoneinfo import ZoneInfo

from scripts.trend_articles import common

MIN_INTEREST = 0.25
MIN_DATA = 0.5


def _yearly_means(values: dict) -> dict[int, float]:
    years: dict[int, list[float]] = {}
    for per in values.values():
        for year, v in per.items():
            years.setdefault(year, []).append(v)
    return {y: statistics.fmean(v) for y, v in sorted(years.items()) if len(v) >= 3}


def data_score(meta: dict, values: dict) -> dict:
    last = meta["years"][1]
    recency = {2026: 1, 2025: 1, 2024: 0.9, 2023: 0.75, 2022: 0.55}.get(last, 0.3)
    coverage = 1.0 if meta["territories"] >= 100 else 0.8 if meta["territories"] >= 19 else 0.4
    n_years = len({y for per in values.values() for y in per})
    depth = min(1.0, n_years / 8)
    return {
        "score": round(0.5 * recency + 0.25 * coverage + 0.25 * depth, 2),
        "last_year": last, "years": n_years, "territories": meta["territories"],
    }


def story_score(meta: dict, values: dict) -> dict:
    level = meta["level"]
    last = meta["years"][1]
    now = {t: per[last] for t, per in values.items() if last in per}
    found: list[tuple[float, str]] = []

    if len(now) >= 5:
        mean = statistics.fmean(now.values())
        spread = statistics.pstdev(now.values())
        if spread:
            t, v = max(now.items(), key=lambda kv: abs(kv[1] - mean))
            z = abs(v - mean) / spread
            found.append((min(1.0, z / 2.5) if z >= 1.8 else 0.0,
                          f"outlier: {t} {common.fmt(v, 2)} contro una media dei territori di {common.fmt(mean, 2)} (z={z:.1f}, {last})"))

    means = _yearly_means(values)
    years = list(means)
    if len(years) >= 6:
        recent = means[years[-1]] - means[years[-3]]
        before = means[years[-4]] - means[years[-6]]
        if recent * before < 0 and abs(recent) > 0.02 * abs(means[years[-1]] or 1):
            found.append((0.9, f"inversione: la media dei territori {'sale' if recent > 0 else 'scende'} dal {years[-3]} al {years[-1]} dopo essere {'scesa' if before < 0 else 'salita'} dal {years[-6]} al {years[-4]}"))
    if years:
        all_means = list(means.values())
        if means[years[-1]] in (max(all_means), min(all_means)) and len(years) >= 5:
            which = "massimo" if means[years[-1]] == max(all_means) else "minimo"
            found.append((0.7, f"record: nel {years[-1]} la media dei territori tocca il {which} della serie ({years[0]}-{years[-1]})"))

    def gap(year):
        groups: dict[str, list[float]] = {}
        for t, per in values.items():
            if year in per:
                groups.setdefault(common.macro_area(t, level), []).append(per[year])
        if len(groups) < 2 or min(len(g) for g in groups.values()) < 3:
            return None
        return statistics.fmean(groups["Mezzogiorno"]) - statistics.fmean(groups["Centro-Nord"])

    if years:
        first, end = gap(years[0]), gap(years[-1])
        if first and end is not None:
            change = (abs(end) - abs(first)) / abs(first)
            if abs(change) >= 0.25:
                found.append((min(1.0, abs(change)),
                              f"divario Mezzogiorno/Centro-Nord {'allargato' if change > 0 else 'ristretto'} del {abs(change) * 100:.0f}% dal {years[0]} al {years[-1]}"))

    found.sort(reverse=True)
    return {"score": round(found[0][0], 2) if found else 0.0, "stories": [d for s, d in found if s > 0]}


def interest_score(topic: dict, signals: list[dict], interest: dict, most_news: int) -> dict:
    tid = topic["id"]
    news = [s for s in signals if s["type"] == "google_news_tema" and s.get("topic") == tid and tid in s["topics"]]
    trending = [s for s in signals if s["type"] == "google_trends_tendenza" and tid in s["topics"]]
    top = [s for s in signals if s["type"] == "google_news_principali" and tid in s["topics"]]
    istat = [s for s in signals if s["type"] == "istat_comunicato" and tid in s["topics"]]

    parts = {"news": math.log1p(len(news)) / math.log1p(max(most_news, 1))}
    parts["topical"] = 1.0 if (trending or top) else 0.5 if istat else 0.0
    weights = {"news": 0.35, "topical": 0.25}

    measured = interest.get(tid, [])
    growths = [m["growth"] for m in measured if m.get("growth") is not None]
    if growths:
        parts["growth"] = max(0.0, min(1.0, (max(growths) - 0.8) / 1.2))
        weights["growth"] = 0.2
    levels = [m["level_vs_anchor"] for m in measured if m.get("level_vs_anchor")]
    if levels:
        parts["level"] = max(0.0, min(1.0, 1 + math.log10(max(levels)) / 2))
        weights["level"] = 0.2

    total = sum(parts[k] * weights[k] for k in weights) / sum(weights.values())
    top_regions = {m["query"]: sorted(m["regions_7d"].items(), key=lambda kv: -kv[1])[:5]
                   for m in measured if m.get("regions_7d")}
    return {
        "score": round(total, 2),
        "parts": {k: round(v, 2) for k, v in parts.items()},
        "news_7d": len(news),
        "google_trending": [s["term"] for s in trending],
        "top_news": [s["title"] for s in top],
        "istat": [s["title"] for s in istat],
        "trends": [{k: m.get(k) for k in ("query", "growth", "level_vs_anchor", "mean_7d")} for m in measured],
        "top_regions": top_regions,
        "news_examples": [{"title": s["title"], "url": s["url"], "published": s["published"]} for s in news[:5]],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--day", help="cartella di lavoro AAAA-MM-GG (default: oggi, ora italiana)")
    args = parser.parse_args(argv)

    day = args.day or dt.datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    folder = common.day_dir(day)
    signals = common.read_json(folder / "signals.json")["signals"]
    interest = common.read_json(folder / "interest.json")["topics"] if (folder / "interest.json").exists() else {}
    topics = common.read_json(common.TOPICS_CONFIG)["topics"]

    counts = [sum(1 for s in signals if s["type"] == "google_news_tema" and s.get("topic") == t["id"] and t["id"] in s["topics"])
              for t in topics]
    pairs = []
    for topic in topics:
        inter = interest_score(topic, signals, interest, max(counts))
        for key in topic["indicators"]:
            s = common.series(key)
            data = data_score(s["meta"], s["values"])
            story = story_score(s["meta"], s["values"])
            total = inter["score"] * (data["score"] + story["score"]) / 2
            discarded = []
            if inter["score"] < MIN_INTEREST:
                discarded.append("interesse sotto soglia")
            if data["score"] < MIN_DATA:
                discarded.append("dato debole")
            if story["score"] == 0:
                discarded.append("nessuna storia nei dati")
            pairs.append({
                "topic": topic["id"], "topic_name": topic["name"], "indicator": key,
                "indicator_name": s["meta"]["name"], "level": s["meta"]["level"],
                "total": round(total, 3), "interest": inter, "data": data, "story": story,
                "discarded": discarded,
            })

    pairs.sort(key=lambda r: (bool(r["discarded"]), -r["total"]))
    common.write_json(folder / "ranking.json", {"day": day, "pairs": pairs})

    lines = [f"# Classifica tema-indicatore, {day}", "",
             "| # | tema | indicatore | liv. | interesse | dato | storia | totale | note |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(pairs, 1):
        note = "; ".join(r["discarded"]) or (r["story"]["stories"][0] if r["story"]["stories"] else "")
        lines.append(f"| {i} | {r['topic']} | {r['indicator']} {r['indicator_name'][:50]} | {r['level'][:4]} | "
                     f"{r['interest']['score']} | {r['data']['score']} | {r['story']['score']} | {r['total']} | {note} |")
    (folder / "ranking.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:30]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
