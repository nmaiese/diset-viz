"""Loader for the BES datasets at both territorial levels (region and province).

One framework, two resolutions: the quality-of-life section reads the BES dei
Territori for regions (NUTS2, 20 with Trentino reconstructed) and provinces
(NUTS3, 103). Kept separate from `app/data.py` so the Istat-territorial catalog
and its 20-region completeness rule are untouched. Cached 1h.
"""

import csv
from pathlib import Path

from app.cache import cache
from app.data import _parse_number
from app.profiles import region_key_for

DATA_DIR = Path(__file__).resolve().parent / "static" / "data"

LEVELS = {
    "regione": {
        "dataset": "Assoluti_BES_Regione.csv",
        "manifest": "bes_regione_manifest.csv",
    },
    "provincia": {
        "dataset": "Assoluti_Provincia.csv",
        "manifest": "province_manifest.csv",
    },
}
PROVINCE_CODES = DATA_DIR / "province_codes.csv"


def _paths(level):
    cfg = LEVELS[level]
    return DATA_DIR / cfg["dataset"], DATA_DIR / cfg["manifest"]


def has_bes_data(level):
    dataset, manifest = _paths(level)
    if not (dataset.exists() and manifest.exists()):
        return False
    return level == "regione" or PROVINCE_CODES.exists()


@cache.memoize(timeout=3600)
def get_bes_territories(level):
    """{key: {name, region, metro_city}} for the level's territories."""
    if level == "provincia":
        territories = {}
        with PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                territories[row["province_key"]] = {
                    "name": row["name"],
                    "region": row.get("region", ""),
                    "metro_city": row.get("metro_city") == "1",
                }
        return territories
    # regione: derive keys from the dataset's distinct territories
    dataset, _ = _paths(level)
    names = set()
    with dataset.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            names.add(row["Territorio"])
    return {
        region_key_for(name): {"name": name, "region": "", "metro_city": False}
        for name in names
    }


@cache.memoize(timeout=3600)
def _name_to_key(level):
    return {info["name"]: key for key, info in get_bes_territories(level).items()}


@cache.memoize(timeout=3600)
def get_bes_manifest(level):
    """id -> {name, domain_name, category, direction, year_max, unit, coverage_latest}."""
    _, manifest_path = _paths(level)
    manifest = {}
    with manifest_path.open(encoding="utf-8", newline="") as handle:
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
def get_bes_rows(level):
    """Parsed observations with a territory_key for the level."""
    dataset, _ = _paths(level)
    name_to_key = _name_to_key(level)
    rows = []
    with dataset.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            territory = row["Territorio"]
            rows.append({
                "id": row["idIndicatore"],
                "territory": territory,
                "territory_key": name_to_key.get(territory),
                "theme": row["Tema"],
                "name": row["Indicatore"],
                "unit": row["UDM"],
                "year": int(row["Anno"]),
                "value": _parse_number(row["Dato"]),
            })
    return rows
