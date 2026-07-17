"""Selection rules for the regional quality-of-life score.

The public indicator universe is federated.  This module identifies the subset
that can contribute to the regional score, regardless of whether its source is
the national BES workbook or the territorial-development dataset.
"""

import re
import unicodedata
from functools import lru_cache

from app.bes_data import MIN_PUBLIC_COVERAGE, get_bes_manifest
from app.profiles import SCOREABLE_DIRECTIONS
from app.quality_life import quality_life_indicator_set


BES_PREFIX = "bes:"
REGIONAL_BES_MIN_YEAR = 2025


def _normalise_name(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@lru_cache(maxsize=1)
def regional_quality_life_selection():
    """Public indicator id -> quality-of-life category for regional scoring.

    BES indicators must be current, sufficiently covered and explicitly
    directional. Territorial indicators reuse the already curated DISET core
    selection. Exact name duplicates are counted once, preferring BES.
    """
    manifest = get_bes_manifest("regione")
    selected = {}
    bes_names = set()
    for raw_id, info in manifest.items():
        if info["year_max"] < REGIONAL_BES_MIN_YEAR:
            continue
        if info["coverage_latest"] < MIN_PUBLIC_COVERAGE:
            continue
        if info["direction"] not in SCOREABLE_DIRECTIONS or not info["category"]:
            continue
        selected[f"{BES_PREFIX}{raw_id}"] = info["category"]
        bes_names.add(_normalise_name(info["name"]))

    from app.data import get_catalog

    catalog = {item["id"]: item for item in get_catalog()["indicators"]}
    for category, indicator_ids in quality_life_indicator_set().items():
        for indicator_id in indicator_ids:
            item = catalog[indicator_id]
            if _normalise_name(item["name"]) in bes_names:
                continue
            selected[indicator_id] = category
    return selected


def quality_life_category(indicator_id):
    return regional_quality_life_selection().get(str(indicator_id))
