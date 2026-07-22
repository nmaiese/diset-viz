"""Loader for the regional "Indagine Multiscopo" dataset.

Same shape as `app/bes_data.py` (own CSV + manifest, own cache), kept
separate so the Istat-territorial catalog (`app/data.py`) and the BES
regional dataset are both left untouched. Cached 1h.
"""

import csv
import statistics
from pathlib import Path

from app.cache import cache
from app.data import _parse_number, indicator_year_over_year_stats
from app.indicator_notes import (
    annual_change_framing,
    build_bes_indicator_explain,
    change_unit_label,
    display_unit,
    value_unit_label,
)
from app.profiles import region_key_for, slugify
from app.taxonomy import CANONICAL_CATEGORIES, category_for_indicator, category_path

DATA_DIR = Path(__file__).resolve().parent / "static" / "data"
DATASET_PATH = DATA_DIR / "Assoluti_Multiscopo_Regione.csv"
MANIFEST_PATH = DATA_DIR / "multiscopo_regione_manifest.csv"
MIN_PUBLIC_COVERAGE = 0.8
SOURCE_URL = "https://esploradati.istat.it/databrowser/#/it"


def has_multiscopo_data():
    return DATASET_PATH.exists() and MANIFEST_PATH.exists()


@cache.memoize(timeout=3600)
def get_multiscopo_territories():
    """{key: {name}} for every region present in the dataset."""
    names = set()
    with DATASET_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            names.add(row["Territorio"])
    return {region_key_for(name): {"name": name} for name in names}


@cache.memoize(timeout=3600)
def _name_to_key():
    return {info["name"]: key for key, info in get_multiscopo_territories().items()}


@cache.memoize(timeout=3600)
def get_multiscopo_manifest():
    """id -> {name, domain_name, category, direction, year_max, unit, coverage_latest}."""
    manifest = {}
    with MANIFEST_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            proposed = row["proposed_category"] or None
            category = proposed if proposed in CANONICAL_CATEGORIES else category_for_indicator(
                row["id"], row["domain_name"]
            )
            item = {
                "id": row["id"],
                "name": row["name"],
                "domain": row["domain"],
                "domain_name": row["domain_name"],
                "category": category,
                "category_name": CANONICAL_CATEGORIES[category]["name"] if category else None,
                "category_path": category_path(category) if category else None,
                "direction": row["proposed_direction"],
                "unit": display_unit(row["unit"]),
                "year_min": int(row["year_min"]),
                "year_max": int(row["year_max"]),
                "coverage_latest": float(row.get("coverage_latest", 0) or 0),
            }
            item["explain"] = build_bes_indicator_explain(item, "regioni")
            manifest[row["id"]] = item
    return manifest


@cache.memoize(timeout=3600)
def get_multiscopo_rows():
    """Parsed observations with a territory_key."""
    name_to_key = _name_to_key()
    rows = []
    with DATASET_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            territory = row["Territorio"]
            rows.append({
                "id": row["idIndicatore"],
                "territory": territory,
                "territory_key": name_to_key.get(territory),
                "theme": row["Tema"],
                "name": row["Indicatore"],
                "unit": display_unit(row["UDM"]),
                "source": row.get("Fonte", ""),
                "archive": row.get("Archivio", ""),
                "year": int(row["Anno"]),
                "value": _parse_number(row["Dato"]),
            })
    return rows


def multiscopo_indicator_path(indicator_id, name):
    return f"/qualita-della-vita/indicatore/multiscopo-{indicator_id}/{slugify(name)}"


@cache.memoize(timeout=3600)
def all_multiscopo_indicators():
    """One public catalog entry per Multiscopo indicator."""
    manifest = get_multiscopo_manifest()
    indicators = []
    for indicator_id, info in sorted(manifest.items()):
        indexable = info["coverage_latest"] >= MIN_PUBLIC_COVERAGE and info["year_max"] >= 2023
        indicators.append({
            **info,
            "path": multiscopo_indicator_path(indicator_id, info["name"]),
            "indexable": indexable,
            "territory_total": len(get_multiscopo_territories()),
        })
    return indicators


@cache.memoize(timeout=3600)
def get_multiscopo_indicator_page(indicator_id):
    """Metadata and observations for one Multiscopo indicator.

    Shaped like `app.bes_data.get_bes_indicator_page` (a single "regione"
    entry in `level_payloads`) so the same quality-of-life indicator template
    can render both sources.
    """
    entry = next((item for item in all_multiscopo_indicators() if item["id"] == indicator_id), None)
    if entry is None:
        return None

    rows = [
        row for row in get_multiscopo_rows()
        if row["id"] == indicator_id and row["value"] is not None and row["territory_key"]
    ]
    observations = [row for row in rows if row["year"] == entry["year_max"]]
    reverse = entry["direction"] == "higher_better"
    observations.sort(key=lambda row: row["value"], reverse=reverse)
    values = [row["value"] for row in observations]
    annual_change = indicator_year_over_year_stats(
        {"metadata": {"year_max": entry["year_max"]}, "series": rows}
    )
    level_payload = {
        "level": "regione",
        "label": "Regioni",
        "year_min": entry["year_min"],
        "year_max": entry["year_max"],
        "coverage_latest": entry["coverage_latest"],
        "count_latest": len(observations),
        "territory_total": len(get_multiscopo_territories()),
        "observations": observations,
        "mean": sum(values) / len(values) if values else None,
        "median": statistics.median(values) if values else None,
        "annual_change": annual_change,
        "annual_note": annual_change_framing(
            entry["name"],
            entry["direction"],
            annual_change["average_delta"] if annual_change else None,
        ),
    }
    return {
        **entry,
        "levels": {"regione": entry},
        "level_payloads": [level_payload],
        "year_min": entry["year_min"],
        "year_max": entry["year_max"],
        "value_unit": value_unit_label(entry["name"], entry["unit"]),
        "change_unit": change_unit_label(entry["name"], entry["unit"]),
        "source_url": SOURCE_URL,
    }
