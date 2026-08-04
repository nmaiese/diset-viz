"""Shared quality-of-life categories, weights and territorial selection.

The public regional and provincial rankings are built by
``app.quality_life_bes``. This module retains the small shared layer that engine
and the federated source selection use: weight normalisation, serialisable
category metadata, and the curated territorial-indicator subset.
"""

from app.cache import cache
from app.data import get_catalog
from app.profiles import (
    SCOREABLE_DIRECTIONS,
    _indicator_meta,
    _percentile_matrix,
    is_core,
)
from app.quality_life_config import QUALITY_LIFE_CATEGORIES


def normalize_weights(weights):
    """Scale a dict of weights so the values sum to 1.0 (empty if all <= 0)."""
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in weights.items()}


@cache.memoize(timeout=3600)
def _theme_category_map():
    """Source-theme and canonical category name -> category slug."""
    mapping = {}
    for slug, category in QUALITY_LIFE_CATEGORIES.items():
        mapping[category["name"]] = slug
        for theme in category["themes"]:
            mapping[theme] = slug
    return mapping


def get_quality_life_categories():
    """Categories as a serialisable list, in declaration order."""
    return [
        {
            "slug": slug,
            "name": category["name"],
            "description": category["description"],
            "themes": list(category["themes"]),
        }
        for slug, category in QUALITY_LIFE_CATEGORIES.items()
    ]


@cache.memoize(timeout=3600)
def quality_life_indicator_set():
    """category slug -> [indicator_id], using only scoreable core indicators.

    An indicator qualifies when it is complete and recent (``is_core``), present
    in the percentile matrix, has a clear direction, and its Istat theme maps to
    a quality-of-life category. Contextual indicators are excluded by design.
    """
    matrix = _percentile_matrix()
    meta = _indicator_meta()
    theme_category = _theme_category_map()
    by_category = {slug: [] for slug in QUALITY_LIFE_CATEGORIES}
    for item in get_catalog()["indicators"]:
        ind_id = item["id"]
        if not is_core(item) or ind_id not in matrix:
            continue
        info = meta.get(ind_id)
        if not info or info["direction"] not in SCOREABLE_DIRECTIONS:
            continue
        category = info.get("category_slug") or theme_category.get(info["theme"])
        if category is None:
            continue
        by_category[category].append(ind_id)
    return by_category
