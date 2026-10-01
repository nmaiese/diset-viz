"""Selection rules for the regional quality-of-life score.

The public indicator universe is federated.  This module identifies the subset
that can contribute to the regional score, regardless of whether its source is
the national BES workbook or the territorial-development dataset.
"""

import re
import unicodedata
from functools import lru_cache

from app import external_data, provincial_families, sources
from app.bes_data import MIN_PUBLIC_COVERAGE, get_bes_manifest
from app.external_atlas import external_regional_scoreables, has_external_data
from app.multiscopo_data import get_multiscopo_manifest, has_multiscopo_data
from app.profiles import SCOREABLE_DIRECTIONS
from app.quality_life import quality_life_indicator_set
from app.quality_life_config import QUALITY_LIFE_CATEGORIES


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
PROVINCIAL_EXTERNAL_MIN_YEAR = 2023


def external_regional_score_gate():
    """public_id -> scoring info for the regional external series in the score.

    Two places hold a curator's verdict: `score_eligible` on the normalized
    rows (the older admission flow) and `scoreable` in the per-level
    publication manifest (`external_indicator_levels.csv`). Where the manifest
    has a regional row it decides, in both directions, so a single CSV cell
    turns a series on or off. Without one the normalized flag still applies.
    Selection and engine read this same gate: reading two different ones let a
    series be selected and then silently dropped for lack of info.
    """
    gate = dict(external_regional_scoreables())
    for row in external_data.get_external_levels():
        if row.get("territory_level") != "regione":
            continue
        public_id = row.get("target_indicator_id", "")
        if sources.split_internal_id(public_id)[0] not in sources.EXTERNAL_FAMILIES:
            continue
        direction = row.get("direction")
        category = row.get("quality_life_category")
        if (row.get("scoreable") != "true" or direction not in SCOREABLE_DIRECTIONS
                or not category):
            gate.pop(public_id, None)
            continue
        try:
            coverage = float(row.get("coverage_latest") or 0.0)
        except (TypeError, ValueError):
            coverage = 0.0
        try:
            year_max = int(row.get("year_max"))
        except (TypeError, ValueError):
            year_max = None
        gate[public_id] = {
            "name": row.get("name", ""),
            "category": category,
            "direction": direction,
            "coverage": coverage,
            "year_max": year_max,
        }
    return gate


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
        for public_id, info in external_regional_score_gate().items():
            # Direction and score-eligibility are the curator's reviewed verdict
            # (external_regional_score_gate already enforces both); here we only
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


def provincial_external_selection(bes_names):
    """External provincial series admitted to the provincial score, in order.

    The provincial score is BES dei Territori first. An external series joins
    only if the curator marked it `scoreable` in the levels manifest
    (`provincial_families.scoreables()` already demands that, a scoreable
    direction and an indexable provincial level) and it passes the gates
    restated here, so the score never depends on a loader default: scoreable
    direction, latest year >= 2023, coverage >= 0.80, a canonical category.
    `bes_names` are the normalised names of the BES series already scored:
    an identical phenomenon stays BES. Names accumulate, so two external
    families cannot add the same phenomenon twice either. No fuzzy matching:
    similar names with different definitions are a curator's call.
    """
    used_names = set(bes_names)
    selected = []
    for item in provincial_families.scoreables():
        meta = item["metadata"]
        level = item["levels"][provincial_families.PROVINCE_LEVEL]
        if meta["direction"] not in SCOREABLE_DIRECTIONS:
            continue
        if level["year_max"] < PROVINCIAL_EXTERNAL_MIN_YEAR:
            continue
        if level["coverage_latest"] < MIN_PUBLIC_COVERAGE:
            continue
        if meta["quality_life_category"] not in QUALITY_LIFE_CATEGORIES:
            continue
        name = _normalise_name(meta["name"])
        if name in used_names:
            continue
        used_names.add(name)
        selected.append(item)
    return selected
