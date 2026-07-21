"""Loader for the BES datasets at both territorial levels (region and province).

One framework, two resolutions: the quality-of-life section reads the BES dei
Territori for regions (NUTS2, 20 with Trentino reconstructed) and provinces
(NUTS3, 103). Kept separate from `app/data.py` so the Istat-territorial catalog
and its 20-region completeness rule are untouched. Cached 1h.
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
MIN_PUBLIC_COVERAGE = 0.8
BES_SOURCE_URLS = {
    "regione": (
        "https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/"
        "la-misurazione-del-benessere-bes/gli-indicatori-del-bes/"
    ),
    "provincia": "https://www.istat.it/notizia/bes-dei-territori-edizione-2025/",
}


def _trim_words(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:-")
    return cut or text[:limit].rstrip(" ,.;:-")


def _trim_name_preserving_tail(text, limit):
    if len(text) <= limit:
        return text
    words = text.split()
    tail = " ".join(words[-2:]).rstrip(" ,.;:-")
    separator = ": "
    head = _trim_words(text, limit - len(separator) - len(tail))
    if head and tail.lower() not in head.lower():
        return f"{head}{separator}{tail}"
    return _trim_words(text, limit)


def bes_territory_label(indicator):
    levels = set(indicator.get("levels") or {})
    if levels == {"regione", "provincia"}:
        return "regioni e province"
    if levels == {"provincia"}:
        return "province"
    return "regioni"


def bes_seo_title(name, site_name, territory_label="territori"):
    topic_suffix = f": BES {territory_label}"
    brand_suffix = f" | {site_name}"
    candidate = f"{name}{topic_suffix}"
    if len(candidate) + len(brand_suffix) <= 60:
        return candidate + brand_suffix
    if len(candidate) <= 60:
        return candidate
    return f"{_trim_name_preserving_tail(name, 60 - len(topic_suffix))}{topic_suffix}"


def bes_seo_description(name, plain="", territory_label="regioni e province"):
    body = (plain or "Consulta valori e significato dell'indicatore").strip()
    body = body if body.endswith(".") else f"{body}."
    suffix = f" Dati BES Istat per {territory_label}."
    if len(body) + len(suffix) <= 155:
        return body + suffix

    fixed = f": cosa misura, unità e confronto tra {territory_label}. Dati BES Istat."
    concise_name = {
        "Rapporto tra i tassi di occupazione (25-49 anni) delle donne con figli in età prescolare e delle donne senza figli": (
            "Occupazione delle donne con figli piccoli e senza figli"
        ),
    }.get(name, name)
    label = _trim_name_preserving_tail(concise_name, 155 - len(fixed))
    return f"{label}{fixed}"


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
            item["explain"] = build_bes_indicator_explain(
                item,
                "regioni" if level == "regione" else "province",
            )
            manifest[row["id"]] = item
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
                "unit": display_unit(row["UDM"]),
                "source": row.get("Fonte", ""),
                "archive": row.get("Archivio", ""),
                "year": int(row["Anno"]),
                "value": _parse_number(row["Dato"]),
            })
    return rows


def bes_indicator_path(indicator_id, name):
    return f"/qualita-della-vita/indicatore/{indicator_id}/{slugify(name)}"


@cache.memoize(timeout=3600)
def all_bes_indicators():
    """One public catalog entry for every BES indicator used by the rankings."""
    regioni = get_bes_manifest("regione")
    province = get_bes_manifest("provincia")
    indicators = []
    for indicator_id in sorted(set(regioni) | set(province)):
        levels = {
            level: manifest[indicator_id]
            for level, manifest in (("regione", regioni), ("provincia", province))
            if indicator_id in manifest
        }
        info = levels.get("regione") or levels["provincia"]
        indexable = any(
            level_info["coverage_latest"] >= MIN_PUBLIC_COVERAGE
            and level_info["year_max"] >= 2023
            for level_info in levels.values()
        )
        public_scope = (
            "regioni e province"
            if set(levels) == {"regione", "provincia"}
            else "province" if "provincia" in levels else "regioni"
        )
        indicators.append({
            **info,
            "explain": build_bes_indicator_explain(info, public_scope),
            "path": bes_indicator_path(indicator_id, info["name"]),
            "indexable": indexable,
            "levels": levels,
        })
    return indicators


@cache.memoize(timeout=3600)
def get_bes_indicator_page(indicator_id):
    """Metadata and observations for one BES indicator at both public levels."""
    entry = next((item for item in all_bes_indicators() if item["id"] == indicator_id), None)
    if entry is None:
        return None

    level_payloads = []
    for level, label in (("regione", "Regioni"), ("provincia", "Province")):
        info = entry["levels"].get(level)
        if info is None:
            continue
        level_rows = [
            row for row in get_bes_rows(level)
            if row["id"] == indicator_id and row["value"] is not None and row["territory_key"]
        ]
        observations = [
            row for row in level_rows if row["year"] == info["year_max"]
        ]
        reverse = info["direction"] == "higher_better"
        observations.sort(key=lambda row: row["value"], reverse=reverse)
        values = [row["value"] for row in observations]
        annual_change = indicator_year_over_year_stats(
            {"metadata": {"year_max": info["year_max"]}, "series": level_rows}
        )
        level_payloads.append({
            "level": level,
            "label": label,
            "year_min": info["year_min"],
            "year_max": info["year_max"],
            "coverage_latest": info["coverage_latest"],
            "count_latest": len(observations),
            "territory_total": len(get_bes_territories(level)),
            "observations": observations,
            "mean": sum(values) / len(values) if values else None,
            "median": statistics.median(values) if values else None,
            "annual_change": annual_change,
            "annual_note": annual_change_framing(
                entry["name"],
                info["direction"],
                annual_change["average_delta"] if annual_change else None,
            ),
        })
    return {
        **entry,
        "level_payloads": level_payloads,
        "year_min": min(level["year_min"] for level in level_payloads),
        "year_max": max(level["year_max"] for level in level_payloads),
        "value_unit": value_unit_label(entry["name"], entry["unit"]),
        "change_unit": change_unit_label(entry["name"], entry["unit"]),
        "source_url": BES_SOURCE_URLS["regione" if "regione" in entry["levels"] else "provincia"],
    }
