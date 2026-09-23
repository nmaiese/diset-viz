"""Elaborazione: un indicatore provinciale portato a livello di regione.

Serve quando l'Istat pubblica un indicatore solo per provincia (per esempio
la mortalita' stradale extraurbana, 07SIC008P) e lo si vuole confrontare con
un dato regionale. Metodo: media semplice delle province della regione, anno
per anno, eventualmente mediata su piu' anni per smorzare i numeri piccoli.
Non e' il valore regionale ufficiale (che pesa gli incidenti): e' dichiarato
come elaborazione, e un articolo lo scrive cosi'.

    bin/py -m scripts.trend_articles.derive_province_mean prov:07SIC008P 2021 2022 2023 --name extraurban_lethality_regions
"""

from __future__ import annotations

import argparse
import statistics
import sys

from scripts.trend_articles import common

REGION_ALIASES = {"Provincia Autonoma Bolzano": "Trentino Alto Adige", "Provincia Autonoma Trento": "Trentino Alto Adige"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("indicator")
    parser.add_argument("years", nargs="+", type=int)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)

    s = common.series(args.indicator)
    regions = common.province_regions()
    groups: dict[str, list[float]] = {}
    for province, per in s["values"].items():
        if all(y in per for y in args.years):
            region = REGION_ALIASES.get(regions.get(province, ""), regions.get(province, ""))
            groups.setdefault(region, []).append(statistics.fmean(per[y] for y in args.years))
    year = args.years[-1]
    base = common.DERIVED_DIR / args.name
    common.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    with base.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write("territory,year,value\n")
        for region, v in sorted(groups.items()):
            f.write(f"{region},{year},{statistics.fmean(v):.2f}\n")
    period = f"{args.years[0]}-{args.years[-1]}" if len(args.years) > 1 else str(year)
    common.write_json(base.with_suffix(".json"), {
        "name": f"{s['meta']['name']}, media delle province della regione, {period}",
        "unit": s["meta"]["unit"],
        "source": s["meta"]["source"],
        "archive": s["meta"]["archive"],
        "source_url": common.definition(args.indicator)["source_url"],
        "method": (f"Media semplice dei valori provinciali di {args.indicator} per regione"
                   + (f", mediati sugli anni {period}" if len(args.years) > 1 else "")
                   + f". Non e' il valore regionale ufficiale. Nel CSV l'anno indicato e' l'ultimo del periodo ({year})."),
        "script": "scripts/trend_articles/derive_province_mean.py",
        "period": period,
    })
    for region, v in sorted(groups.items(), key=lambda kv: -statistics.fmean(kv[1])):
        print(f"{region:25s} {statistics.fmean(v):5.2f} ({len(v)} province)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
