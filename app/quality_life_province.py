"""Provincial quality-of-life ranking, built on the BES dei Territori dataset.

A parallel of `app/quality_life.py` for the 107 province. It reuses the same
profiles, categories and scoring helpers, but reads the provincial dataset and
its manifest (`app/province_data.py`) instead of the regional percentile matrix.
The math is identical: oriented percentile per indicator (0..100), mean per
category, profile-weighted final score with weights renormalised over the
available categories.

Directions and category assignments come from `province_manifest.csv`, where
they are still PROPOSED (heuristic). Only indicators that have a category and a
clear direction feed the score; everything else is ignored, exactly like the
contextual indicators in the regional engine.
"""

from collections import defaultdict

from app.cache import cache
from app.profiles import SCOREABLE_DIRECTIONS
from app.province_data import get_province_codes, get_province_manifest, get_province_rows, has_province_data
from app.quality_life import (
    _build_category_scores,
    _category_entry,
    _coverage_for_region,
    _profile_payload,
    _top_indicators_for_region,
    get_quality_life_categories,
    normalize_weights,
)
from app.quality_life_config import DEFAULT_PROFILE, QUALITY_LIFE_CATEGORIES

_TOP_CATEGORIES = 3


@cache.memoize(timeout=3600)
def _province_matrix_and_meta():
    """(matrix, meta): per indicator, latest-year percentile per province + meta."""
    manifest = get_province_manifest()
    by_id = defaultdict(list)
    for row in get_province_rows():
        if row["province_key"]:
            by_id[row["id"]].append(row)

    matrix, meta = {}, {}
    for ind_id, items in by_id.items():
        info = manifest.get(ind_id)
        if not info:
            continue
        year_max = info["year_max"]
        latest = {
            row["province_key"]: row["value"]
            for row in items
            if row["year"] == year_max and row["value"] is not None
        }
        if len(latest) < 2:
            continue
        ranked = sorted(latest.items(), key=lambda kv: (kv[1], kv[0]))
        n = len(ranked)
        matrix[ind_id] = {key: idx / (n - 1) for idx, (key, _) in enumerate(ranked)}
        meta[ind_id] = {
            "id": ind_id,
            "name": info["name"],
            "theme": info["domain_name"],
            "direction": info["direction"],
            "year_max": year_max,
            "unit": info["unit"],
            "path": "",  # no per-indicator page for provincial data yet
        }
    return matrix, meta


@cache.memoize(timeout=3600)
def province_indicator_set():
    """category slug -> [indicator_id] for scoreable, categorised provincial indicators."""
    manifest = get_province_manifest()
    matrix, _ = _province_matrix_and_meta()
    by_category = {slug: [] for slug in QUALITY_LIFE_CATEGORIES}
    for ind_id, info in manifest.items():
        category = info["category"]
        if category not in QUALITY_LIFE_CATEGORIES:
            continue
        if info["direction"] not in SCOREABLE_DIRECTIONS:
            continue
        if ind_id not in matrix:
            continue
        by_category[category].append(ind_id)
    return by_category


@cache.memoize(timeout=3600)
def build_province_ranking(profile_slug=DEFAULT_PROFILE):
    """Full provincial ranking payload, or None if the profile/data is missing."""
    if not has_province_data():
        return None
    profile = _profile_payload(profile_slug)
    if profile is None:
        return None

    indicators_by_category = province_indicator_set()
    expected_categories = [c for c in QUALITY_LIFE_CATEGORIES if indicators_by_category.get(c)]
    empty_categories = [c for c in QUALITY_LIFE_CATEGORIES if not indicators_by_category.get(c)]
    all_ids = [ind_id for ids in indicators_by_category.values() for ind_id in ids]

    matrix, meta = _province_matrix_and_meta()
    codes = get_province_codes()["by_key"]
    weights = profile["weights"]

    rows = []
    unrated = []
    for province_key, info in codes.items():
        category_scores = _build_category_scores(province_key, indicators_by_category, matrix, meta)
        if not category_scores:
            # Provinces with no recent BES data (e.g. the abolished pre-2016
            # Sardinian provinces) are not scored, not ranked 0.
            unrated.append({"province": info["name"], "province_key": province_key,
                            "region": info["region"]})
            continue
        available_weights = {c: weights[c] for c in category_scores if c in weights}
        normalised = normalize_weights(available_weights)
        final = sum(category_scores[c] * w for c, w in normalised.items()) if normalised else 0.0

        ordered = sorted(category_scores.items(), key=lambda kv: kv[1], reverse=True)
        strongest = [_category_entry(c, s) for c, s in ordered[:_TOP_CATEGORIES]]
        weakest = [_category_entry(c, s) for c, s in ordered[::-1][:_TOP_CATEGORIES]]
        top_positive, top_negative = _top_indicators_for_region(province_key, all_ids, matrix, meta)

        rows.append({
            "province": info["name"],
            "province_key": province_key,
            "region": info["region"],
            "metro_city": info["metro_city"],
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

    # Category champions: the province that leads each category. Surfaces the
    # territorial variety that a single averaged index hides.
    champions = []
    for category in expected_categories:
        best = max(
            (r for r in rows if category in r["category_scores"]),
            key=lambda r: r["category_scores"][category],
            default=None,
        )
        if best is not None:
            champions.append({
                "slug": category,
                "name": QUALITY_LIFE_CATEGORIES[category]["name"],
                "province": best["province"],
                "province_key": best["province_key"],
                "region": best["region"],
                "score": best["category_scores"][category],
            })

    methodology = {
        "source": "Istat, BES dei Territori (Bes at local level)",
        "territorial_level": "province e città metropolitane",
        "normalization": (
            "Percentile orientato per indicatore tra le province: 0 = peggiore, "
            "1 = migliore. Scala UI 0-100."
        ),
        "indicator_counts": {c: len(ids) for c, ids in indicators_by_category.items()},
        "total_indicators": len(all_ids),
        "expected_categories": expected_categories,
        "quality_checks": {
            "empty_categories": empty_categories,
            "unrated_provinces": [p["province"] for p in unrated],
            "note": (
                "Direzioni curate a mano sulle polarità BES. I pesi sono per "
                "categoria: una categoria con pochi indicatori (es. Cultura e "
                "digitale) pesa quanto una ricca, quindi va letta con cautela."
            ),
        },
    }

    return {
        "profile": profile,
        "categories": get_quality_life_categories(),
        "ranking": rows,
        "unrated": unrated,
        "champions": champions,
        "methodology": methodology,
        "level": "provincia",
    }


def build_province_profile(province_key, profile_slug=DEFAULT_PROFILE):
    """One province's row within a profile's ranking, or None if unknown."""
    if province_key not in get_province_codes()["by_key"]:
        return None
    ranking = build_province_ranking(profile_slug)
    if ranking is None:
        return None
    row = next((r for r in ranking["ranking"] if r["province_key"] == province_key), None)
    if row is None:
        return None
    return {
        "profile": ranking["profile"],
        "categories": ranking["categories"],
        "province": row,
        "total": len(ranking["ranking"]),
        "methodology": ranking["methodology"],
    }
