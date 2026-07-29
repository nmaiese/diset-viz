"""Externally sourced indicators as first-class atlas entries.

Phase 2 of the multi-source aggregator: a genuinely new external indicator (one
with no counterpart in the committed backbone) becomes a standalone atlas
indicator, not just a freshness badge on an existing one. It reads the committed
normalized external layer (rows whose ``target_indicator_id`` sits in one of the
external families' namespaces and are ``atlas_eligible``) and adapts them to the
exact atlas API contract used by the territorial and BES families, so the same
catalog, page, map, search and sitemap work with no special cases downstream.

One module serves every external family, not just Eurostat. The prefix on the
public id selects the family (``app.sources.EXTERNAL_FAMILIES``) and the family
supplies the user-facing institution, label and licence, so an Istat series can
never be published under Eurostat's name.

Enriching rows (a Eurostat series that overlaps an existing Istat indicator,
targeted at that indicator's id) are deliberately NOT surfaced here: those add
provenance/freshness to the indicator they point at, via app.external_data.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from app import sources
from app.data import _parse_number, REGION_ORDER
from app.external_data import freshness_label, freshness_status, get_external_rows
from app.indicator_notes import build_bes_indicator_explain, display_unit
from app.profiles import SCOREABLE_DIRECTIONS, slugify
from app.taxonomy import category_metadata


MIN_INDEXABLE_YEAR = 2020
# Reviewed plain-language descriptions written by the curator (apply_curation.py).
CURATED_DESC_PATH = Path(__file__).resolve().parent / "static" / "data" / "external" / "curated_descriptions.csv"

# Every family published through the external layer, by public-id prefix. This
# used to be the single constant "eur:", which meant the second hunter adapter
# (istat_demografia) could discover a series that no atlas could then show, and
# promoting it under "eur:" would have put an Istat indicator on the page under
# Eurostat's name and licence. The prefix decides the family, and the family
# decides institution, label and licence.
_PREFIX_TO_FAMILY = {
    sources.SOURCES[family]["internal_prefix"]: family
    for family in sources.EXTERNAL_FAMILIES
}


def _family_of(public_id):
    """The external family a public id belongs to, or None if it is not one.

    Enriching rows target an existing indicator (a bare numeric id, or bes:/
    multiscopo:), and those are not standalone atlas entries.
    """
    value = str(public_id)
    for prefix, family in _PREFIX_TO_FAMILY.items():
        if prefix and value.startswith(prefix):
            return family
    return None


def _raw_id(public_id):
    family = _family_of(public_id)
    if family is None:
        return None
    prefix = sources.SOURCES[family]["internal_prefix"]
    return str(public_id)[len(prefix):]


def external_indicator_path(raw_id, name, family):
    return sources.indicator_url(family, raw_id, slugify(name))


def _region_sort_key(name):
    try:
        return REGION_ORDER.index(name)
    except ValueError:
        return len(REGION_ORDER)


@lru_cache(maxsize=1)
def _rows_by_target():
    """Standalone Eurostat atlas rows grouped by public id (eur:*)."""
    grouped = defaultdict(list)
    for row in get_external_rows():
        target = row.get("target_indicator_id", "")
        if _family_of(target) is None:
            continue
        if row.get("atlas_eligible") != "true" or row.get("territory_level") != "regione":
            continue
        grouped[target].append(row)
    return dict(grouped)


def has_external_data():
    return bool(_rows_by_target())


@lru_cache(maxsize=1)
def _curated_descriptions():
    """id -> {'plain', 'example'} reviewed by the curator, if present."""
    if not CURATED_DESC_PATH.exists():
        return {}
    with CURATED_DESC_PATH.open(encoding="utf-8", newline="") as handle:
        return {
            row["target_indicator_id"]: {
                "plain": (row.get("plain") or "").strip(),
                "example": (row.get("value_explanation") or "").strip(),
            }
            for row in csv.DictReader(handle, delimiter=";")
            if row.get("target_indicator_id")
        }


def external_regional_scoreables():
    """public_id -> scoring metadata for Eurostat indicators the curator has
    marked score-eligible with a scoreable direction. This is the gate the
    quality-of-life selection reads: nothing here until a human confirms the
    verso (direction) and flips score_eligible."""
    result = {}
    for public_id, rows in _rows_by_target().items():
        first = rows[0]
        if first.get("score_eligible") != "true":
            continue
        direction = first.get("direction")
        category = first.get("quality_life_category")
        if direction not in SCOREABLE_DIRECTIONS or not category:
            continue
        try:
            coverage = float(first.get("coverage") or 0.0)
        except (TypeError, ValueError):
            coverage = 0.0
        years = [int(r["year"]) for r in rows if r.get("year")]
        result[public_id] = {
            # The name travels with the entry so the selection can deduplicate
            # against the other families without reopening the external rows.
            "name": first.get("name", ""),
            "category": category,
            "direction": direction,
            "coverage": coverage,
            "year_max": max(years) if years else None,
        }
    return result


def _national_average(series):
    by_year = defaultdict(list)
    for point in series:
        if point["value"] is not None:
            by_year[point["year"]].append(point["value"])
    return [
        {"year": year, "value": sum(values) / len(values)}
        for year, values in sorted(by_year.items())
    ]


def _downsample(points, limit=24):
    if len(points) <= limit:
        return points
    step = (len(points) - 1) / (limit - 1)
    keep = sorted({round(i * step) for i in range(limit)})
    return [points[i] for i in keep]


def _explain_with_curation(public_id, explain):
    """Let a curator-reviewed description override the auto-generated one."""
    curated = _curated_descriptions().get(public_id)
    if not curated:
        return explain
    result = dict(explain)
    if curated.get("plain"):
        result["plain"] = curated["plain"]
    if curated.get("example"):
        result["example"] = curated["example"]
    return result


def get_external_atlas_indicator(public_id):
    """One Eurostat regional indicator in the atlas API shape, or None."""
    family = _family_of(public_id)
    if family is None:
        return None
    raw_id = _raw_id(public_id)
    rows = _rows_by_target().get(str(public_id))
    if not rows:
        return None

    source_label = sources.family_label(family)
    institution = sources.family_institution(family)
    default_license, license_url = sources.family_license(family)
    first = rows[0]
    source_theme = first["theme"]
    direction = first.get("direction") or "contextual"
    unit = display_unit(first["unit"])

    series = sorted(
        (
            {
                "year": int(row["year"]),
                "region": row["territory_name"],
                "region_key": row["territory_code"],
                "value": _parse_number(row["value"]),
            }
            for row in rows
        ),
        key=lambda point: (point["year"], _region_sort_key(point["region"])),
    )
    years = sorted({point["year"] for point in series})
    regions = sorted({point["region"] for point in series}, key=_region_sort_key)
    latest_year = years[-1]
    latest_region_count = sum(
        point["year"] == latest_year and point["value"] is not None for point in series
    )
    completeness = round(latest_region_count / 20, 4)
    spark = [
        {"year": point["year"], "value": round(point["value"], 3)}
        for point in _downsample(_national_average(series))
    ]

    metadata = {
        "id": str(public_id),
        "raw_id": raw_id,
        **category_metadata(source_theme),
        "name": first["name"],
        "unit": unit,
        "source": source_label,
        "source_label": source_label,
        "source_url": first.get("source_url") or "",
        "institution": institution,
        "license": first.get("license") or default_license,
        "license_url": license_url,
        "date_modified": max((row.get("retrieved_at") or "")[:10] for row in rows) or None,
        "archive": first.get("source_dataset") or source_label,
        "explain": _explain_with_curation(
            str(public_id),
            build_bes_indicator_explain(
                {"name": first["name"], "unit": unit, "theme": source_theme,
                 "id": str(public_id), "direction": direction},
                level="territori regionali",
            ),
        ),
        "years": years,
        "year_min": years[0],
        "year_max": latest_year,
        "regions": regions,
        "region_count": latest_region_count,
        "row_count": len(series),
        "completeness": completeness,
        "complete": latest_region_count == 20 and completeness >= 0.98,
        "spark": spark,
        # Freshness badge (same contract as territorial metadata) driven by the
        # latest published year, so indicator_page.html doesn't render an empty badge.
        "freshness_status": freshness_status(latest_year),
        "freshness_label": freshness_label(freshness_status(latest_year)),
        "freshness_year_max": latest_year,
        "catalog_family": family,
        "catalog_family_label": source_label,
        "path": external_indicator_path(raw_id, first["name"], family),
    }
    return {"metadata": metadata, "series": series}


@lru_cache(maxsize=1)
def all_external_indicators():
    """Catalog entries for every standalone Eurostat indicator, with an
    `indexable` flag for the sitemap."""
    indicators = []
    for public_id in sorted(_rows_by_target()):
        payload = get_external_atlas_indicator(public_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        indicators.append({
            **meta,
            "indexable": meta["region_count"] == 20 and meta["year_max"] >= MIN_INDEXABLE_YEAR,
        })
    return indicators
