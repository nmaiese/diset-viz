"""Fase 4: i numeri di un pezzo, tutti, con la loro provenienza.

Il dossier e' l'unico posto da cui chi scrive prende una cifra. Contiene:

- per ogni indicatore del pezzo: fonte, archivio, unita', anni, la pagina
  canonica sul sito (risolta dall'app, non indovinata);
- l'ultimo anno per tutti i territori, in ordine;
- la **media semplice dei territori** (non e' la media nazionale e non va mai
  chiamata cosi': per Italia e ripartizioni si usano i valori ufficiali Istat,
  con `ext:bes_areas_<codice>`), e le medie semplici di Centro-Nord e
  Mezzogiorno;
- la serie completa per territorio e le variazioni fra primo e ultimo anno;
- `figures`: l'elenco delle cifre ammesse nel testo, ognuna gia' scritta come
  comparira' (virgola decimale, precisione della fonte) e con da dove viene.
  `verify.py` rifiuta un numero del pezzo che non stia qui o fra le
  `external_figures` del frontmatter.

Scrive anche il CSV scaricabile del pezzo in `app/static/data/articles/`,
quello che lo schema `Dataset` dell'articolo dichiara come `distribution`.

    bin/py -m scripts.trend_articles.dossier <slug> bes:03LAV007 prov:03LAV007 --date 2026-09-23
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys

from scripts.trend_articles import common


def indicator_page(meta: dict) -> str | None:
    """Il percorso canonico della scheda, chiesto all'app: segue il 301.

    None solo per le elaborazioni (`ext:`), che una scheda non ce l'hanno.
    """
    if meta["family"] == "ext":
        return None
    from app import app  # l'app si carica solo qui: le altre fasi non la usano

    acronym = {"ter": "ter", "bes": "bes", "ims": "ims", "prov": "bes"}[meta["family"]]
    client = app.test_client()
    path = f"/indicatore/{acronym}-{meta['code']}"
    for _ in range(3):
        response = client.get(path)
        if response.status_code in (301, 302, 308):
            path = response.headers["Location"].replace("http://localhost", "")
            continue
        if response.status_code == 200:
            return path
        raise LookupError(f"scheda di {meta['key']} non trovata: {path} risponde {response.status_code}")
    raise LookupError(f"scheda di {meta['key']}: troppi redirect a partire da /indicatore/{acronym}-{meta['code']}")


def analyze(key: str) -> dict:
    s = common.series(key)
    meta, values = s["meta"], s["values"]
    level = meta["level"]
    decimals = common.source_decimals([v for per in values.values() for v in per.values()])
    first, last = meta["years"]

    ordered = sorted(((t, per[last]) for t, per in values.items() if last in per), key=lambda kv: -kv[1])
    figures: list[dict] = []

    def figure(value: float, what: str, digits: int = decimals) -> str:
        text = common.fmt(value, digits)
        figures.append({"figure": text, "what": what, "indicator": key})
        # Sopra 100 i decimali non dicono niente al lettore: e' ammesso anche l'intero.
        if abs(value) >= 100 and digits:
            text = common.fmt(value, 0)
            figures.append({"figure": text, "what": what + " (arrotondato)", "indicator": key})
        return text

    ranking = [
        {"rank": i, "territory": t, "value": v, "text": figure(v, f"{t}, {last}"), "area": common.macro_area(t, level)}
        for i, (t, v) in enumerate(ordered, 1)
    ]

    means = {}
    # Le ripartizioni ufficiali sono gia' medie pesate: non si fa la media delle medie.
    mean_years = [] if level == "ripartizione" else sorted({y for per in values.values() for y in per})
    for year in mean_years:
        row = [per[year] for per in values.values() if year in per]
        if len(row) < 3:
            continue
        groups: dict[str, list[float]] = {}
        for t, per in values.items():
            if year in per:
                groups.setdefault(common.macro_area(t, level), []).append(per[year])
        means[year] = {
            "territories": len(row),
            "simple_mean": round(statistics.fmean(row), 4),
            **{f"mean_{k.lower().replace('-', '_')}": round(statistics.fmean(g), 4) for k, g in groups.items()},
        }
    # Una media di valori a un decimale si puo' scrivere con un decimale in piu':
    # 0,825 e 0,592 dicono una distanza che 0,8 e 0,6 appiattiscono. Sono
    # ammesse tutte e due le scritture, e il testo sceglie.
    for year, m in means.items():
        for k, v in m.items():
            if k.startswith(("simple_mean", "mean_")):
                what = f"{k.replace('_', ' ')} dei territori, {year} (media semplice, non pesata)"
                figure(v, what)
                figure(v, what, decimals + 1)

    changes = []
    for t, per in values.items():
        years = sorted(per)
        if len(years) >= 2:
            delta = per[years[-1]] - per[years[0]]
            changes.append({"territory": t, "from": years[0], "to": years[-1], "delta": round(delta, 4),
                            "text": figure(abs(delta), f"variazione {t} {years[0]}-{years[-1]} (in valore assoluto)")})
    changes.sort(key=lambda r: r["delta"])

    if ordered and ordered[-1][1]:
        figure(ordered[0][1] / ordered[-1][1], f"rapporto fra primo ({ordered[0][0]}) e ultimo ({ordered[-1][0]}) nel {last}")

    for t, per in values.items():
        for year, v in per.items():
            if year != last:
                figure(v, f"{t}, {year}")

    return {
        "meta": {**meta, **common.definition(key), "page": indicator_page(meta), "decimals": decimals},
        "last_year": last, "first_year": first,
        "ranking": ranking, "means": means, "changes": changes,
        "series": {t: {str(y): v for y, v in sorted(per.items())} for t, per in values.items()},
        "figures": figures,
    }


def write_csv(slug: str, analyses: list[dict]) -> str:
    common.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = common.DOWNLOAD_DIR / f"{slug}.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        w = csv.writer(file, lineterminator="\n")
        w.writerow(["indicatore", "codice", "livello", "territorio", "anno", "valore", "unita", "fonte", "archivio"])
        for a in analyses:
            m = a["meta"]
            for t, per in sorted(a["series"].items()):
                for year, v in per.items():
                    w.writerow([m["name"], m["code"], m["level"], t, year, v, m["unit"], m["source"], m["archive"]])
    return "/" + str(path.relative_to(common.ROOT / "app")).replace("\\", "/")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("slug")
    parser.add_argument("indicators", nargs="+", help="famiglia:codice, il primo e' il principale")
    parser.add_argument("--date", required=True, help="data del pezzo AAAA-MM-GG, scritta nel dossier")
    args = parser.parse_args(argv)

    analyses = [analyze(k) for k in args.indicators]
    download = write_csv(args.slug, analyses)
    out = common.ARTICLES_DIR / args.slug / "dossier.json"
    common.write_json(out, {
        "slug": args.slug, "created": args.date, "download": download,
        "note": "Le medie dei territori sono medie semplici, non pesate: per Italia e ripartizioni si usano i valori ufficiali Istat.",
        "indicators": analyses,
    })
    for a in analyses:
        m = a["meta"]
        print(f"{m['key']}: {m['name']} [{m['unit']}] {m['years'][0]}-{m['years'][1]}, {m['territories']} territori, pagina {m['page']}")
        head = ", ".join(f"{r['territory']} {r['text']}" for r in a["ranking"][:3])
        tail = ", ".join(f"{r['territory']} {r['text']}" for r in a["ranking"][-3:])
        print(f"   {a['last_year']} in testa: {head} | in fondo: {tail}")
    print(f"-> {out.relative_to(common.ROOT)}  csv {download}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
