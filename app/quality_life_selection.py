"""Selection rules for the regional quality-of-life score.

The public indicator universe is federated.  This module identifies the subset
that can contribute to the regional score, regardless of whether its source is
the national BES workbook or the territorial-development dataset.
"""

import re
import unicodedata
from functools import lru_cache

from app import sources
from app.bes_data import MIN_PUBLIC_COVERAGE, get_bes_manifest
from app.external_atlas import external_regional_scoreables, has_external_data
from app.multiscopo_data import get_multiscopo_manifest, has_multiscopo_data
from app.profiles import SCOREABLE_DIRECTIONS
from app.quality_life import quality_life_indicator_set


BES_PREFIX = "bes:"
REGIONAL_BES_MIN_YEAR = 2025
MULTI_PREFIX = "multiscopo:"
REGIONAL_MULTI_MIN_YEAR = 2023
# Public-id prefixes of every externally sourced family. Named EUR_PREFIX while
# Eurostat was the only one; it is a tuple now so `startswith` covers all of
# them, and a promoted Istat series can reach the score the same way.
EUR_PREFIX = tuple(
    sources.SOURCES[family]["internal_prefix"] for family in sources.EXTERNAL_FAMILIES
)
REGIONAL_EUR_MIN_YEAR = 2021


def _normalise_name(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@lru_cache(maxsize=1)
def regional_quality_life_selection():
    """Public indicator id -> quality-of-life category for regional scoring.

    BES indicators must be current, sufficiently covered and explicitly
    directional. Territorial indicators reuse the already curated DISET core
    selection. Exact name duplicates are counted once, in family order: BES
    first, then territorial, Multiscopo and Eurostat. `used_names` accumulates
    across every family, so a later source cannot re-add a phenomenon already
    in the score under a different id and weigh it twice.
    """
    manifest = get_bes_manifest("regione")
    selected = {}
    used_names = set()
    for raw_id, info in manifest.items():
        if info["year_max"] < REGIONAL_BES_MIN_YEAR:
            continue
        if info["coverage_latest"] < MIN_PUBLIC_COVERAGE:
            continue
        if info["direction"] not in SCOREABLE_DIRECTIONS or not info["category"]:
            continue
        selected[f"{BES_PREFIX}{raw_id}"] = info["category"]
        used_names.add(_normalise_name(info["name"]))

    from app.data import get_catalog

    catalog = {item["id"]: item for item in get_catalog()["indicators"]}
    for category, indicator_ids in quality_life_indicator_set().items():
        for indicator_id in indicator_ids:
            item = catalog[indicator_id]
            name = _normalise_name(item["name"])
            if name in used_names:
                continue
            selected[indicator_id] = category
            used_names.add(name)

    if has_multiscopo_data():
        for raw_id, info in get_multiscopo_manifest().items():
            if info["year_max"] < REGIONAL_MULTI_MIN_YEAR:
                continue
            if info["coverage_latest"] < MIN_PUBLIC_COVERAGE:
                continue
            if not info["scoreable"]:
                continue
            if info["direction"] not in SCOREABLE_DIRECTIONS or not info["category"]:
                continue
            name = _normalise_name(info["name"])
            if name in used_names:
                continue
            selected[f"{MULTI_PREFIX}{raw_id}"] = info["category"]
            used_names.add(name)

    if has_external_data():
        for public_id, info in external_regional_scoreables().items():
            # Direction and score-eligibility are the curator's reviewed verdict
            # (external_regional_scoreables already enforces both); here we only
            # add coverage and freshness gates, consistent with the other families.
            if info["year_max"] is None or info["year_max"] < REGIONAL_EUR_MIN_YEAR:
                continue
            if info["coverage"] < MIN_PUBLIC_COVERAGE:
                continue
            name = _normalise_name(info.get("name", ""))
            if name and name in used_names:
                continue
            selected[public_id] = info["category"]
            used_names.add(name)
    return selected


def quality_life_category(indicator_id):
    return regional_quality_life_selection().get(str(indicator_id))
