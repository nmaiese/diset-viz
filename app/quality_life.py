"""Composition engine for the "Qualità della vita" regional ranking.

This is a thin, auditable layer on top of the existing scoring machinery in
``app/profiles.py``. It does NOT recompute percentiles or invent data: it reads
the neutral percentile matrix (``_percentile_matrix``), applies each indicator's
curated direction (``_oriented``), groups indicators into quality-of-life
categories (``app/quality_life_config.py``), averages them, and combines the
category scores with a profile's weights into a final 0-100 score per region.

Every number is traceable:
- indicator_score = oriented_percentile * 100  (0 = worst region, 100 = best)
- category_score  = average(indicator_scores in that category)
- final_score     = weighted_average(category_scores, profile weights)
Weights are normalised to sum to 1.0 and renormalised over the categories that
are actually available for a region, so a missing category never blocks the
ranking; coverage is reported instead.

Only directional, complete and recent indicators feed the score (see
``is_core`` and ``SCOREABLE_DIRECTIONS`` in ``app/profiles.py``). Contextual
indicators are excluded. The whole thing is cached for 1h like the rest of the
profiles layer; restart gunicorn to refresh after a data change.
"""

from app.cache import cache
from app.data import get_catalog
from app.profiles import (
    CORE_MIN_YEAR,
    SCOREABLE_DIRECTIONS,
    _indicator_meta,
    _oriented,
    _percentile_matrix,
    _region_key_map,
    is_core,
    region_name,
)
from app.quality_life_config import (
    DEFAULT_PROFILE,
    QUALITY_LIFE_CATEGORIES,
    QUALITY_LIFE_PROFILES,
)

# How many strongest/weakest categories and top/bottom indicators to surface.
_TOP_CATEGORIES = 3
_TOP_INDICATORS = 5


def normalize_weights(weights):
    """Scale a dict of weights so the values sum to 1.0 (empty if all <= 0)."""
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in weights.items()}


def _score_to_ui(value):
    """Internal 0..1 score to the 0..100 UI scale, rounded to one decimal."""
    return round(value * 100, 1)


@cache.memoize(timeout=3600)
def _theme_category_map():
    """Exact Istat theme name -> category slug (inverts the config table)."""
    mapping = {}
    for slug, category in QUALITY_LIFE_CATEGORIES.items():
        for theme in category["themes"]:
            mapping[theme] = slug
    return mapping


def category_for_indicator(item):
    """Category slug for an indicator meta dict (or a bare theme name), or None."""
    theme = item["theme"] if isinstance(item, dict) else item
    return _theme_category_map().get(theme)


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


def _profile_payload(profile_slug):
    """A profile with normalised weights, or None if the slug is unknown."""
    config = QUALITY_LIFE_PROFILES.get(profile_slug)
    if config is None:
        return None
    return {
        "slug": profile_slug,
        "name": config["name"],
        "description": config["description"],
        "weights": normalize_weights(config["weights"]),
    }


def get_quality_life_profiles():
    """All profiles with normalised weights, in declaration order."""
    return [_profile_payload(slug) for slug in QUALITY_LIFE_PROFILES]


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
        category = theme_category.get(info["theme"])
        if category is None:
            continue
        by_category[category].append(ind_id)
    return by_category


def _oriented_score(ind_id, region_key, matrix, meta):
    """Oriented 0..1 score (1 = best) for one indicator/region, or None."""
    by_region = matrix.get(ind_id, {})
    if region_key not in by_region:
        return None
    return _oriented(by_region[region_key], meta[ind_id]["direction"])


def _build_category_scores(region_key, indicators_by_category, matrix, meta):
    """category slug -> UI score (0..100), only for categories with data here."""
    scores = {}
    for category, ids in indicators_by_category.items():
        values = [
            score
            for ind_id in ids
            if (score := _oriented_score(ind_id, region_key, matrix, meta)) is not None
        ]
        if values:
            scores[category] = _score_to_ui(sum(values) / len(values))
    return scores


def _coverage_for_region(category_scores, expected_categories):
    """Share (0..1) of expected categories that have a score for this region."""
    if not expected_categories:
        return 0.0
    return round(len(category_scores) / len(expected_categories), 4)


def _category_entry(slug, score):
    return {"slug": slug, "name": QUALITY_LIFE_CATEGORIES[slug]["name"], "score": score}


def _top_indicators_for_region(region_key, indicator_ids, matrix, meta, limit=_TOP_INDICATORS):
    """Best and worst indicators for a region, each fully traceable."""
    scored = []
    for ind_id in indicator_ids:
        score = _oriented_score(ind_id, region_key, matrix, meta)
        if score is None:
            continue
        info = meta[ind_id]
        scored.append({
            "id": ind_id,
            "name": info["name"],
            "theme": info["theme"],
            "score": _score_to_ui(score),
            "path": info["path"],
            "year_max": info["year_max"],
            "direction": info["direction"],
        })
    top_positive = sorted(scored, key=lambda e: e["score"], reverse=True)[:limit]
    top_negative = sorted(scored, key=lambda e: e["score"])[:limit]
    return top_positive, top_negative


@cache.memoize(timeout=3600)
def _unmapped_themes():
    """Catalog themes not assigned to any category (diagnostics only)."""
    mapped = set(_theme_category_map())
    return sorted(theme["name"] for theme in get_catalog()["themes"] if theme["name"] not in mapped)


@cache.memoize(timeout=3600)
def build_quality_life_ranking(profile_slug=DEFAULT_PROFILE):
    """Full ranking payload for a profile, or None if the profile is unknown."""
    profile = _profile_payload(profile_slug)
    if profile is None:
        return None

    indicators_by_category = quality_life_indicator_set()
    expected_categories = [c for c in QUALITY_LIFE_CATEGORIES if indicators_by_category.get(c)]
    empty_categories = [c for c in QUALITY_LIFE_CATEGORIES if not indicators_by_category.get(c)]
    all_ids = [ind_id for ids in indicators_by_category.values() for ind_id in ids]

    matrix = _percentile_matrix()
    meta = _indicator_meta()
    weights = profile["weights"]

    rows = []
    for region_key, region in _region_key_map().items():
        category_scores = _build_category_scores(region_key, indicators_by_category, matrix, meta)
        available_weights = {c: weights[c] for c in category_scores if c in weights}
        normalised = normalize_weights(available_weights)
        final = sum(category_scores[c] * w for c, w in normalised.items()) if normalised else 0.0

        ordered = sorted(category_scores.items(), key=lambda kv: kv[1], reverse=True)
        strongest = [_category_entry(c, s) for c, s in ordered[:_TOP_CATEGORIES]]
        weakest = [_category_entry(c, s) for c, s in ordered[::-1][:_TOP_CATEGORIES]]
        top_positive, top_negative = _top_indicators_for_region(region_key, all_ids, matrix, meta)

        rows.append({
            "region": region,
            "region_key": region_key,
            "score": round(final, 1),
            "coverage": _coverage_for_region(category_scores, expected_categories),
            "category_scores": category_scores,
            "strongest_categories": strongest,
            "weakest_categories": weakest,
            "top_positive_indicators": top_positive,
            "top_negative_indicators": top_negative,
        })

    rows.sort(key=lambda r: r["score"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    methodology = {
        "source": "Istat, Indicatori territoriali per le politiche di sviluppo",
        "territorial_level": "regioni",
        "core_criteria": {"complete": True, "min_year": CORE_MIN_YEAR, "regions": 20},
        "normalization": (
            "Percentile orientato per indicatore: 0 = regione peggiore, 1 = migliore. "
            "Scala UI 0-100."
        ),
        "indicator_counts": {c: len(ids) for c, ids in indicators_by_category.items()},
        "total_indicators": len(all_ids),
        "expected_categories": expected_categories,
        "quality_checks": {
            "empty_categories": empty_categories,
            "unmapped_themes": _unmapped_themes(),
        },
    }

    return {
        "profile": profile,
        "categories": get_quality_life_categories(),
        "ranking": rows,
        "methodology": methodology,
    }


def build_quality_life_region_profile(region_key, profile_slug=DEFAULT_PROFILE):
    """One region's row within a profile's ranking, or None if unknown."""
    if region_name(region_key) is None:
        return None
    ranking = build_quality_life_ranking(profile_slug)
    if ranking is None:
        return None
    row = next((r for r in ranking["ranking"] if r["region_key"] == region_key), None)
    if row is None:
        return None
    return {
        "profile": ranking["profile"],
        "categories": ranking["categories"],
        "region": row,
        "total": len(ranking["ranking"]),
        "methodology": ranking["methodology"],
    }
