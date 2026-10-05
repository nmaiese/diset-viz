#!/usr/bin/env python3
"""Create article CSV for indicator 104 from the repository's regional source."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "app/static/data/Assoluti_Regione.csv"
OUTPUT = ROOT / "app/static/data/articles/livello-istruzione-regioni.csv"
GROUPS = {
    "Piemonte": "Nord", "Valle d'Aosta": "Nord", "Liguria": "Nord", "Lombardia": "Nord",
    "Trentino Alto Adige": "Nord", "Veneto": "Nord", "Friuli-Venezia Giulia": "Nord", "Emilia-Romagna": "Nord",
    "Toscana": "Centro", "Umbria": "Centro", "Marche": "Centro", "Lazio": "Centro",
    "Abruzzo": "Mezzogiorno", "Molise": "Mezzogiorno", "Campania": "Mezzogiorno", "Puglia": "Mezzogiorno",
    "Basilicata": "Mezzogiorno", "Calabria": "Mezzogiorno", "Sicilia": "Mezzogiorno", "Sardegna": "Mezzogiorno",
}

def main():
    values = {}
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter=";"):
            if row["idIndicatore"] == "104" and row["Area"] == "Regione" and row["Anno"] in {"2018", "2024"}:
                values.setdefault(row["Territorio"], {})[row["Anno"]] = float(row["Dato"].replace(",", "."))
    if set(values) != set(GROUPS) or any(set(years) != {"2018", "2024"} for years in values.values()):
        raise ValueError("Expected exactly 20 regions with 2018 and 2024 values for indicator 104")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["regione", "ripartizione", "2018", "2024", "variazione_punti"])
        for region, area in GROUPS.items():
            old, new = values[region]["2018"], values[region]["2024"]
            writer.writerow([region, area, f"{old:.1f}", f"{new:.1f}", f"{new-old:.1f}"])
    print(OUTPUT)

if __name__ == "__main__":
    main()
