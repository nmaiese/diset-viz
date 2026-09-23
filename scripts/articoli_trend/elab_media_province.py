"""Elaborazione: un indicatore provinciale portato a livello di regione.

Serve quando l'Istat pubblica un indicatore solo per provincia (per esempio
la mortalita' stradale extraurbana, 07SIC008P) e lo si vuole confrontare con
un dato regionale. Metodo: media semplice delle province della regione, anno
per anno, eventualmente mediata su piu' anni per smorzare i numeri piccoli.
Non e' il valore regionale ufficiale (che pesa gli incidenti): e' dichiarato
come elaborazione, e un articolo lo scrive cosi'.

    bin/py -m scripts.articoli_trend.elab_media_province prov:07SIC008P 2021 2022 2023 --nome letalita_extraurbana_regioni
"""

from __future__ import annotations

import argparse
import statistics
import sys

from scripts.articoli_trend import comuni

NOMI = {"Provincia Autonoma Bolzano": "Trentino Alto Adige", "Provincia Autonoma Trento": "Trentino Alto Adige"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("indicatore")
    parser.add_argument("anni", nargs="+", type=int)
    parser.add_argument("--nome", required=True)
    args = parser.parse_args(argv)

    s = comuni.serie(args.indicatore)
    regione = comuni.regione_di_provincia()
    gruppi: dict[str, list[float]] = {}
    for prov, per in s["valori"].items():
        if all(a in per for a in args.anni):
            r = NOMI.get(regione.get(prov, ""), regione.get(prov, ""))
            gruppi.setdefault(r, []).append(statistics.fmean(per[a] for a in args.anni))
    anno = args.anni[-1]
    base = comuni.ELABORAZIONI / args.nome
    comuni.ELABORAZIONI.mkdir(parents=True, exist_ok=True)
    with base.with_suffix(".csv").open("w", encoding="utf-8") as f:
        f.write("territorio,anno,valore\n")
        for r, v in sorted(gruppi.items()):
            f.write(f"{r},{anno},{statistics.fmean(v):.2f}\n")
    periodo = f"{args.anni[0]}-{args.anni[-1]}" if len(args.anni) > 1 else str(anno)
    comuni.scrivi_json(base.with_suffix(".json"), {
        "nome": f"{s['meta']['nome']}, media delle province della regione, {periodo}",
        "unita": s["meta"]["unita"],
        "fonte": s["meta"]["fonte"],
        "archivio": s["meta"]["archivio"],
        "source_url": comuni.definizione(args.indicatore)["source_url"],
        "method": (f"Media semplice dei valori provinciali di {args.indicatore} per regione"
                   + (f", mediati sugli anni {periodo}" if len(args.anni) > 1 else "")
                   + ". Non e' il valore regionale ufficiale."),
        "script": "scripts/articoli_trend/elab_media_province.py",
    })
    for r, v in sorted(gruppi.items(), key=lambda kv: -statistics.fmean(kv[1])):
        print(f"{r:25s} {statistics.fmean(v):5.2f} ({len(v)} province)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
