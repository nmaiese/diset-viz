#!/usr/bin/env python3
"""Estrazione dati AGCOM Broadband Map (FTTH 4T 2025).

Estrae l'indicatore AGCOM_FTTH per regioni (20) e province (105):
- AGCOM_FTTH: Famiglie raggiunte dalla rete in fibra FTTH (%)
Nota: Le province autonome di Bolzano e Trento sono escluse per lacuna di rilevazione dichiarata.
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
import urllib.request
from collections import defaultdict
import openpyxl

URL_DESI_2025 = "https://geo.agcom.it/reportistica/desi/Survey_Italy_IT_DESI_2026_Data_2025_v2_pub.xlsx"
CACHE_DIR = "lavoro/cache"
XLSX_CACHE_PATH = os.path.join(CACHE_DIR, "Survey_Italy_IT_DESI_2026_Data_2025_v2_pub.xlsx")

OUT_DATA_PATH = "app/static/data/nuovi/agcom.csv"
OUT_MANIFEST_PATH = "app/static/data/nuovi/agcom_manifest.csv"
PROVINCE_CODES_PATH = "app/static/data/province_codes.csv"

NUTS2_REGION_MAP = {
    "ITC1": "piemonte",
    "ITC2": "valle-d-aosta",
    "ITC3": "liguria",
    "ITC4": "lombardia",
    "ITH1": "trentino-alto-adige",
    "ITH2": "trentino-alto-adige",
    "ITH3": "veneto",
    "ITH4": "friuli-venezia-giulia",
    "ITH5": "emilia-romagna",
    "ITI1": "toscana",
    "ITI2": "umbria",
    "ITI3": "marche",
    "ITI4": "lazio",
    "ITF1": "abruzzo",
    "ITF2": "molise",
    "ITF3": "campania",
    "ITF4": "puglia",
    "ITF5": "basilicata",
    "ITF6": "calabria",
    "ITG1": "sicilia",
    "ITG2": "sardegna",
}

PROVINCE_ALIASES = {
    "valle d’aosta/vallée d’aoste": "aosta",
    "valle d'aosta/vallée d'aoste": "aosta",
    "valle d'aosta": "aosta",
    "bolzano-bozen": "bolzano",
    "bolzano": "bolzano",
    "l’aquila": "l-aquila",
    "l'aquila": "l-aquila",
    "reggio nell’emilia": "reggio-emilia",
    "reggio nell'emilia": "reggio-emilia",
    "reggio emilia": "reggio-emilia",
    "reggio di calabria": "reggio-calabria",
    "reggio calabria": "reggio-calabria",
    "forli-cesena": "forli-cesena",
    "forlì-cesena": "forli-cesena",
    "massa-carrara": "massa-carrara",
    "pesaro e urbino": "pesaro-e-urbino",
    "monza e della brianza": "monza-e-della-brianza",
    "barletta-andria-trani": "barletta-andria-trani",
}


def slugify(val):
    val = unicodedata.normalize("NFKD", val or "").encode("ascii", "ignore").decode("ascii")
    val = val.lower().replace("'", " ").replace("’", " ")
    return re.sub(r"[^a-z0-9]+", "-", val).strip("-")


def load_province_keys(path):
    prov_keys = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            prov_keys[slugify(row["name"])] = row["province_key"]
    return prov_keys


def ensure_file(offline=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    if os.path.exists(XLSX_CACHE_PATH):
        return
    if offline:
        raise FileNotFoundError(f"File non presente in cache: {XLSX_CACHE_PATH}")
    print(f"Scaricamento file AGCOM DESI da {URL_DESI_2025}...")
    req = urllib.request.Request(URL_DESI_2025, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        with open(XLSX_CACHE_PATH, "wb") as f:
            f.write(data)


def extract_agcom_data(xlsx_path, prov_map):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["DESI 2026 KPI NUTS3 DATA 4Q25"]
    
    prov_rows = {}
    reg_households = defaultdict(float)
    reg_fttp_households = defaultdict(float)
    
    for r in range(2, ws.max_row + 1):
        nuts3 = str(ws.cell(r, 1).value or "").strip()
        desc = str(ws.cell(r, 2).value or "").strip()
        hh = float(ws.cell(r, 3).value or 0)
        fttp_frac = float(ws.cell(r, 11).value or 0)
        
        if not desc or hh == 0:
            continue
            
        nuts2 = nuts3[:4]
        rkey = NUTS2_REGION_MAP.get(nuts2)
        if rkey:
            reg_households[rkey] += hh
            reg_fttp_households[rkey] += hh * fttp_frac
            
        clean_desc = desc.split("/")[0].strip().lower()
        pkey = PROVINCE_ALIASES.get(clean_desc) or PROVINCE_ALIASES.get(desc.lower()) or prov_map.get(slugify(clean_desc))
        
        # Bolzano e Trento escluse per lacuna di rilevazione dichiarata
        if pkey and pkey not in ["bolzano", "trento"]:
            pct = round(fttp_frac * 100, 2)
            prov_rows[pkey] = pct

    rows = []
    # Province (105)
    for pkey, pct in sorted(prov_rows.items()):
        rows.append({
            "indicator_id": "AGCOM_FTTH",
            "level": "provincia",
            "territory_key": pkey,
            "year": 2025,
            "value": f"{pct:.2f}"
        })
        
    # Regioni (20)
    for rkey, tot_hh in sorted(reg_households.items()):
        if tot_hh > 0:
            pct = round((reg_fttp_households[rkey] / tot_hh) * 100, 2)
            rows.append({
                "indicator_id": "AGCOM_FTTH",
                "level": "regione",
                "territory_key": rkey,
                "year": 2025,
                "value": f"{pct:.2f}"
            })
            
    return rows


def write_outputs(rows):
    os.makedirs(os.path.dirname(OUT_DATA_PATH), exist_ok=True)
    with open(OUT_DATA_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["indicator_id", "level", "territory_key", "year", "value"], delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        
    manifest_rows = [
        {
            "indicator_id": "AGCOM_FTTH",
            "name": "Famiglie raggiunte dalla rete in fibra FTTH",
            "institution": "Autorità per le garanzie nelle comunicazioni",
            "unit": "%",
            "decimals": 2,
            "direction": "higher_better",
            "theme": "Società dell'informazione",
            "source_url": "https://geo.agcom.it/",
            "method_url": "https://geo.agcom.it/reportistica/",
            "license": "CC BY 4.0",
            "license_quote": "Tutti i dati del Portale BBMap sono rilasciati sotto licenza Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)",
            "year_min": 2025,
            "year_max": 2025,
            "n_provincia": 105,
            "n_regione": 20,
            "note": "Percentuale di famiglie raggiunte da connettivita in fibra FTTH (4T 2025). Indicatore distinto dalla copertura ultrabroadband Istat/BES perche limitato alla sola tecnologia FTTH. Le province autonome di Bolzano e Trento presentano una lacuna di rilevazione nei dati provinciali e sono escluse dalle province."
        }
    ]
    
    with open(OUT_MANIFEST_PATH, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["indicator_id", "name", "institution", "unit", "decimals", "direction", "theme",
                      "source_url", "method_url", "license", "license_quote", "year_min", "year_max",
                      "n_provincia", "n_regione", "note"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(manifest_rows)


def main():
    parser = argparse.ArgumentParser(description="Estrattore dati AGCOM FTTH")
    parser.add_argument("--offline", action="store_true", help="Usa solo i file in cache locale")
    args = parser.parse_args()

    ensure_file(offline=args.offline)
    prov_map = load_province_keys(PROVINCE_CODES_PATH)
    rows = extract_agcom_data(XLSX_CACHE_PATH, prov_map)
    write_outputs(rows)
    print(f"Estratte {len(rows)} righe per AGCOM. Salvare in {OUT_DATA_PATH} e {OUT_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
