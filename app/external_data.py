"""External-source metadata and freshness helpers.

The legacy atlas and BES CSV schemas stay unchanged. This module reads the
separate normalized external layer, when present, and exposes conservative
freshness metadata for APIs and templates.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from app.cache import cache


DATA_DIR = Path(__file__).resolve().parent / "static" / "data"
EXTERNAL_DIR = DATA_DIR / "external"
EXTERNAL_DATASET = EXTERNAL_DIR / "normalized_external_indicators.csv"
EXTERNAL_MANIFEST = DATA_DIR / "external_indicator_manifest.csv"

EXTERNAL_COLUMNS = [
    "source",
    "source_dataset",
    "source_indicator_id",
    "target_indicator_id",
    "name",
    "territory_level",
    "territory_code",
    "territory_name",
    "year",
    "value",
    "unit",
    "theme",
    "quality_life_category",
    "direction",
    "definition_match",
    "atlas_eligible",
    "profile_eligible",
    "score_eligible",
    "coverage",
    "retrieved_at",
    "source_url",
    "license",
    "notes",
]

MANIFEST_COLUMNS = [
    "target_indicator_id",
    "target_indicator_name",
    "source",
    "source_indicator_id",
    "definition_match",
    "current_year",
    "new_year",
    "territory_level",
    "unit_match",
    "coverage",
    "direction",
    "score_eligible",
    "status",
    "review_notes",
]


def freshness_status(year):
    if year is None:
        return "unknown"
    year = int(year)
    if year >= 2025:
        return "current"
    if year >= 2023:
        return "recent"
    if year >= 2020:
        return "dated"
    return "stale"


def freshness_label(status):
    return {
        "current": "Aggiornato",
        "recent": "Recente",
        "dated": "Da aggiornare",
        "stale": "Datato",
        "unknown": "Non noto",
    }.get(status, status)


def _read_semicolon_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


@cache.memoize(timeout=3600)
def get_external_rows():
    return _read_semicolon_csv(EXTERNAL_DATASET)


@cache.memoize(timeout=3600)
def get_external_manifest():
    return _read_semicolon_csv(EXTERNAL_MANIFEST)


@cache.memoize(timeout=3600)
def _external_summary_by_target():
    rows = get_external_rows()
    manifest = get_external_manifest()
    latest_by_target = {}
    sources = defaultdict(set)
    statuses = defaultdict(set)

    for row in rows:
        target = row.get("target_indicator_id", "")
        if not target:
            continue
        sources[target].add(row.get("source", ""))
        try:
            year = int(row.get("year") or 0)
        except ValueError:
            year = 0
        current = latest_by_target.get(target)
        if current is None or year > current["year"]:
            latest_by_target[target] = {
                "year": year,
                "source": row.get("source", ""),
                "retrieved_at": row.get("retrieved_at", ""),
                "definition_match": row.get("definition_match", ""),
            }

    for row in manifest:
        target = row.get("target_indicator_id", "")
        if target:
            statuses[target].add(row.get("status", ""))
            if row.get("source"):
                sources[target].add(row["source"])

    summary = {}
    for target in set(latest_by_target) | set(sources) | set(statuses):
        latest = latest_by_target.get(target)
        summary[target] = {
            "external_year_max": latest["year"] if latest else None,
            "external_source": latest["source"] if latest else "",
            "external_retrieved_at": latest["retrieved_at"] if latest else "",
            "definition_match": latest["definition_match"] if latest else "",
            "sources": sorted(s for s in sources.get(target, set()) if s),
            "manifest_statuses": sorted(s for s in statuses.get(target, set()) if s),
        }
    return summary


def external_summary_for_indicator(indicator_id):
    return _external_summary_by_target().get(str(indicator_id), {})


def freshness_payload(year, source="", retrieved_at=""):
    status = freshness_status(year)
    return {
        "year_max": int(year) if year is not None else None,
        "source": source or "",
        "retrieved_at": retrieved_at or "",
        "freshness_status": status,
        "freshness_label": freshness_label(status),
    }


def enrich_indicator_metadata(item):
    """Return a shallow copy with freshness and external-source metadata."""
    result = dict(item)
    year = result.get("year_max")
    external = external_summary_for_indicator(result.get("id"))
    freshness_year = int(year or 0)
    if external.get("external_year_max") and external["external_year_max"] > int(year or 0):
        freshness_year = external["external_year_max"]
    payload = freshness_payload(freshness_year, result.get("source"), external.get("external_retrieved_at", ""))
    payload.pop("year_max", None)
    result.update(payload)
    result["freshness_year_max"] = freshness_year or None
    result["external_sources"] = external.get("sources", [])
    result["external_statuses"] = external.get("manifest_statuses", [])
    result["external_year_max"] = external.get("external_year_max")
    return result


def count_freshness(items):
    counts = Counter()
    for item in items:
        counts[freshness_status(item.get("year_max") or item.get("year"))] += 1
    return {key: counts.get(key, 0) for key in ("current", "recent", "dated", "stale", "unknown")}
