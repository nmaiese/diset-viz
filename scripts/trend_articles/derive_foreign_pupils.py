"""Elaborazione: quota di alunni con cittadinanza non italiana in terza media, per regione.

Fonte: open data del Ministero dell'Istruzione e del Merito, "Alunni per
cittadinanza, scuola e anno di corso", scuole statali e paritarie
(`ALUITASTRACITSTA<anni>0831.csv` e `ALUITASTRACITPAR<anni>0831.csv` su
dati.istruzione.it). Licenza IODL 2.0.

Metodo: si tengono le righe con ORDINESCUOLA = "SCUOLA SECONDARIA I GRADO" e
ANNOCORSO = 3, si attribuisce ogni scuola alla regione dalla sigla di
provincia nelle prime due lettere del CODICESCUOLA, si sommano alunni totali e
alunni con cittadinanza non italiana. La quota e' il rapporto, per cento.

Serve a mettere alla prova un'ipotesi (piu' alunni stranieri = piu' studenti
sotto la soglia Invalsi), non a spiegare da sola un fenomeno: la cittadinanza
non e' l'origine (un ragazzo nato in Italia da genitori stranieri che ha preso
la cittadinanza conta come italiano), e un confronto fra regioni non dice
niente sui singoli studenti. Valle d'Aosta e Trentino-Alto Adige non sono
negli open data del Ministero (scuole a ordinamento autonomo).

    bin/py -m scripts.trend_articles.derive_foreign_pupils 201718 202425

Scrive `data/derived/foreign_pupils_grade8.csv` e il `.json` con il metodo.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys

import requests

from scripts.trend_articles import common

URL = "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/ALUITASTRACIT{kind}{years}{end}0831.csv"
OUTPUT = common.DERIVED_DIR / "foreign_pupils_grade8"

PROVINCE_CODES = {
    "Piemonte": "TO VC NO CN AT AL BI VB",
    "Lombardia": "VA CO SO MI BG BS PV CR MN LC LO MB",
    "Veneto": "VR VI BL TV VE PD RO",
    "Friuli-Venezia Giulia": "UD GO TS PN",
    "Liguria": "IM SV GE SP",
    "Emilia-Romagna": "PC PR RE MO BO FE RA FC RN FO",
    "Toscana": "MS LU PT FI LI PI AR SI GR PO",
    "Umbria": "PG TR",
    "Marche": "PU AN MC AP FM PS",
    "Lazio": "VT RI RM LT FR",
    "Abruzzo": "AQ TE PE CH",
    "Molise": "CB IS",
    "Campania": "CE BN NA AV SA",
    "Puglia": "FG BA TA BR LE BT",
    "Basilicata": "PZ MT",
    "Calabria": "CS CZ RC KR VV",
    "Sicilia": "TP PA ME AG CL EN CT RG SR",
    "Sardegna": "SS NU CA OR SU CI VS OT OG",
}
REGION_BY_CODE = {code: region for region, codes in PROVINCE_CODES.items() for code in codes.split()}


def shares(school_year: str) -> dict[str, tuple[int, int]]:
    """'201718' -> {regione: (alunni di terza media, di cui stranieri)}."""
    totals: dict[str, list[int]] = {}
    for kind in ("STA", "PAR"):
        url = URL.format(kind=kind, years=school_year, end="20" + school_year[4:6])
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        for r in csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))):
            if r["ORDINESCUOLA"] != "SCUOLA SECONDARIA I GRADO" or r["ANNOCORSO"] != "3":
                continue
            region = REGION_BY_CODE.get(r["CODICESCUOLA"][:2])
            if region is None:
                continue
            t = totals.setdefault(region, [0, 0])
            t[0] += int(r["ALUNNI"] or 0)
            t[1] += int(r["ALUNNICITTADINANZANONITALIANA"] or 0)
    return {k: (v[0], v[1]) for k, v in totals.items()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("school_years", nargs="+", help="anni scolastici, es. 201718 202425")
    args = parser.parse_args(argv)

    common.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out_rows = []
    for school_year in args.school_years:
        # L'anno scolastico 2017/18 finisce con la prova di maggio 2018:
        # nella serie si usa l'anno della prova, come fa l'Istat per Invalsi.
        test_year = int("20" + school_year[4:6])
        for region, (total, foreign) in sorted(shares(school_year).items()):
            out_rows.append({"territory": region, "year": test_year, "value": round(100 * foreign / total, 2),
                             "pupils": total, "foreign": foreign})
            print(test_year, region, total, foreign, round(100 * foreign / total, 2))
    with OUTPUT.with_suffix(".csv").open("w", encoding="utf-8", newline="") as file:
        w = csv.DictWriter(file, fieldnames=["territory", "year", "value", "pupils", "foreign"], lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    common.write_json(OUTPUT.with_suffix(".json"), {
        "name": "Alunni con cittadinanza non italiana in terza media",
        "unit": "percentuale sugli alunni della terza classe della secondaria di primo grado",
        "source": "Ministero dell'Istruzione e del Merito",
        "archive": "Open data, alunni per cittadinanza, scuola e anno di corso (statali e paritarie)",
        "source_url": "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/?area=Studenti",
        "license": "IODL 2.0",
        "method": __doc__.split("Metodo:")[1].split("Serve a")[0].strip().replace("\n", " "),
        "script": "scripts/trend_articles/derive_foreign_pupils.py",
        "school_years": args.school_years,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
