"""Loader for the provincial BES dataset and its manifest.

Kept deliberately separate from `app/data.py` so the regional catalog (which
hard-codes "complete = 20 regions") is never touched by provincial rows. This
module just reads the three artifacts produced by the acquisition pipeline
(see docs/PROVINCE_PIPELINE.md) and shapes them for the provincial quality-of-life
engine. Cached 1h like the rest of the data layer.
"""

import csv
from pathlib import Path

from app.cache import cache
from app.data import _parse_number

DATA_DIR = Path(__file__).resolve().parent / "static" / "data"
PROVINCE_DATASET = DATA_DIR / "Assoluti_Provincia.csv"
PROVINCE_MANIFEST = DATA_DIR / "province_manifest.csv"
PROVINCE_CODES = DATA_DIR / "province_codes.csv"


def has_province_data():
    return PROVINCE_DATASET.exists() and PROVINCE_MANIFEST.exists() and PROVINCE_CODES.exists()


@cache.memoize(timeout=3600)
def get_province_codes():
    """{'by_key': {key: {...}}, 'by_name': {name: key}} for the 107 province."""
    by_key, by_name = {}, {}
    with PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            key = row["province_key"]
            by_key[key] = {
                "name": row["name"],
                "region": row.get("region", ""),
                "metro_city": row.get("metro_city") == "1",
                "code": row.get("code", ""),
            }
            by_name[row["name"]] = key
    return {"by_key": by_key, "by_name": by_name}


@cache.memoize(timeout=3600)
def get_province_manifest():
    """id -> indicator metadata (proposed category and direction, years, coverage)."""
    manifest = {}
    with PROVINCE_MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            manifest[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "domain": row["domain"],
                "domain_name": row["domain_name"],
                "category": row["proposed_category"] or None,
                "direction": row["proposed_direction"],
                "unit": row["unit"],
                "year_max": int(row["year_max"]),
                "coverage_latest": float(row.get("coverage_latest", 0) or 0),
            }
    return manifest


@cache.memoize(timeout=3600)
def get_province_rows():
    """Parsed observations: id, territory, province_key, theme, name, year, value."""
    by_name = get_province_codes()["by_name"]
    rows = []
    with PROVINCE_DATASET.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            territory = row["Territorio"]
            rows.append({
                "id": row["idIndicatore"],
                "territory": territory,
                "province_key": by_name.get(territory),
                "theme": row["Tema"],
                "name": row["Indicatore"],
                "unit": row["UDM"],
                "year": int(row["Anno"]),
                "value": _parse_number(row["Dato"]),
            })
    return rows
