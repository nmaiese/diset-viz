"""Sovraccarico del costo dell'abitazione per titolo di godimento, Italia 2025.

Eurostat `ilc_lvho07c` (EU-SILC): quota di persone che vive in famiglie dove il
costo totale dell'abitazione supera il 40% del reddito disponibile, per titolo
di godimento. Il dato esiste solo per l'Italia intera. Il CSV usa i titoli al
posto dei territori, in modo che `figures bars` li disegni come barre.

    bin/py -m scripts.trend_articles.derive_casa_titolo_godimento

Scrive `data/derived/casa_titolo_godimento.{csv,json}` e, per la linea di riferimento delle
figure, `casa_titolo_godimento_totale.{csv,json}` con il totale Italia di Eurostat.
"""

from __future__ import annotations

import csv
import io
import json

import requests

from scripts.trend_articles import common

URL = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/ilc_lvho07c/A.PC..IT"
       "?format=SDMX-CSV&startPeriod=2025&endPeriod=2025&labels=name")
YEAR = 2025
LABELS = {
    "RENT_MKT": "Affitto di mercato",
    "RENT_FR": "Affitto ridotto/gratis",
    "OWN_NL": "Proprietà senza mutuo",
    "OWN_L": "Proprietà con mutuo",
}


def main() -> None:
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(response.text)))
    code_col = next(c for c in rows[0] if c.startswith("tenure"))
    values = {}
    total = None
    for r in rows:
        code = r[code_col].split(":")[0].strip()
        if r["TIME_PERIOD"] != str(YEAR):
            continue
        if code in LABELS:
            values[LABELS[code]] = float(r["OBS_VALUE"])
        elif code == "TOTAL":
            total = float(r["OBS_VALUE"])
    if total is None:
        raise SystemExit("totale Italia mancante nella risposta Eurostat")
    missing = set(LABELS.values()) - set(values)
    if missing:
        raise SystemExit(f"titoli mancanti nella risposta Eurostat: {sorted(missing)}")
    out_csv = common.DERIVED_DIR / "casa_titolo_godimento.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["territory", "year", "value"])
        for label in LABELS.values():
            writer.writerow([label, YEAR, values[label]])
    meta = {
        "name": "Sovraccarico del costo dell'abitazione per titolo di godimento, Italia",
        "unit": "Valori percentuali",
        "source": "Eurostat, EU-SILC",
        "archive": "ilc_lvho07c, Housing cost overburden rate by tenure status",
        "source_url": URL,
        "method": "Valori Eurostat per l'Italia, 2025, senza rielaborazione: persone in famiglie dove il costo totale dell'abitazione supera il 40% del reddito disponibile. Il dato non esiste per regione. Al posto dei territori ci sono i titoli di godimento.",
        "script": "scripts/trend_articles/derive_casa_titolo_godimento.py",
    }
    (common.DERIVED_DIR / "casa_titolo_godimento.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (common.DERIVED_DIR / "casa_titolo_godimento_totale.csv").write_text(
        f"territory,year,value\nItalia,{YEAR},{total}\n", encoding="utf-8")
    meta_totale = dict(meta, name="Sovraccarico del costo dell'abitazione, totale Italia",
                       method="Totale Italia di Eurostat, tutti i titoli di godimento, 2025, senza rielaborazione.")
    (common.DERIVED_DIR / "casa_titolo_godimento_totale.json").write_text(
        json.dumps(meta_totale, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(values, total)


if __name__ == "__main__":
    main()
