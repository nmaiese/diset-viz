"""Unified quality-of-life engine on the BES framework (regions and provinces).

Replaces the percentile-of-rank averaging with **oriented z-scores**, which keep
the magnitude of gaps instead of flattening everyone toward the middle, and makes
a category's contribution independent of how many indicators it happens to hold
(a category score is the *mean* of its z-scores).

Two ideas address the "the profiles do nothing / results feel obvious" problem:
- **delta-rank**: how many positions a territory gains or loses under the chosen
  profile versus the balanced one. The territorial divide dominates the absolute
  ranking, so the movement is where the lens visibly bites.
- **specializations**: per-category rankings and champions, so "where does each
  territory excel or lag" is foreground, not buried under one averaged number.

Same categories and profiles as `app/quality_life_config.py`; same source (BES dei
Territori) at both levels, so regions and provinces are finally comparable.
"""

import statistics
from collections import defaultdict

from app.cache import cache
from app.profiles import SCOREABLE_DIRECTIONS
from app.bes_data import get_bes_manifest, get_bes_rows, get_bes_territories, has_bes_data
from app.quality_life import get_quality_life_categories, normalize_weights
from app.quality_life_config import DEFAULT_PROFILE, QUALITY_LIFE_CATEGORIES, QUALITY_LIFE_PROFILES

LEVELS = ("regione", "provincia")
_DISPLAY_SPREAD = 12.0   # display = 50 + 12 * (standardised score), clipped to 0..100
_TOP_CATEGORIES = 3
_TOP_INDICATORS = 5
_TOP_PER_CATEGORY = 5


def _display(z):
    return round(max(0.0, min(100.0, 50.0 + _DISPLAY_SPREAD * z)), 1)


def _standardise(values):
    """Map a dict key->raw to key->z (population z-score); zeros if no spread."""
    nums = list(values.values())
    if len(nums) < 2:
        return {k: 0.0 for k in values}
    mean = statistics.fmean(nums)
    sd = statistics.pstdev(nums)
    if sd == 0:
        return {k: 0.0 for k in values}
    return {k: (v - mean) / sd for k, v in values.items()}


def _profile_payload(profile_slug):
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
    return [_profile_payload(slug) for slug in QUALITY_LIFE_PROFILES]


@cache.memoize(timeout=3600)
def _matrix_and_meta(level):
    """(matrix, meta): per indicator, oriented z-score per territory (latest year)."""
    manifest = get_bes_manifest(level)
    by_id = defaultdict(list)
    for row in get_bes_rows(level):
        if row["territory_key"]:
            by_id[row["id"]].append(row)

    matrix, meta = {}, {}
    for ind_id, items in by_id.items():
        info = manifest.get(ind_id)
        if not info:
            continue
        year_max = info["year_max"]
        latest = {
            row["territory_key"]: row["value"]
            for row in items
            if row["year"] == year_max and row["value"] is not None
        }
        if len(latest) < 3:
            continue
        z = _standardise(latest)
        if not any(z.values()):
            continue
        sign = 1.0 if info["direction"] == "higher_better" else -1.0  # orient
        matrix[ind_id] = {k: sign * v for k, v in z.items()}
        meta[ind_id] = {
            "id": ind_id,
            "name": info["name"],
            "theme": info["domain_name"],
            "direction": info["direction"],
            "year_max": year_max,
            "unit": info["unit"],
            "path": "",
        }
    return matrix, meta


@cache.memoize(timeout=3600)
def _indicators_by_category(level):
    manifest = get_bes_manifest(level)
    matrix, _ = _matrix_and_meta(level)
    by_category = {slug: [] for slug in QUALITY_LIFE_CATEGORIES}
    for ind_id, info in manifest.items():
        category = info["category"]
        if category not in QUALITY_LIFE_CATEGORIES:
            continue
        if info["direction"] not in SCOREABLE_DIRECTIONS or ind_id not in matrix:
            continue
        by_category[category].append(ind_id)
    return by_category


def _category_raw_scores(level):
    """territory_key -> {category: mean oriented z} (only categories with data)."""
    matrix, _ = _matrix_and_meta(level)
    by_category = _indicators_by_category(level)
    territories = get_bes_territories(level)
    scores = defaultdict(dict)
    for category, ids in by_category.items():
        for key in territories:
            zs = [matrix[i][key] for i in ids if key in matrix.get(i, {})]
            if zs:
                scores[key][category] = sum(zs) / len(zs)
    return dict(scores)


def _final_raw(category_raw, weights):
    """Weighted mean of a territory's category z-scores (weights renormalised)."""
    available = {c: weights[c] for c in category_raw if c in weights}
    norm = normalize_weights(available)
    return sum(category_raw[c] * w for c, w in norm.items()) if norm else None


@cache.memoize(timeout=3600)
def _ranking_keys(level, profile_slug):
    """Ordered list of territory keys for a profile (for delta-rank), best first."""
    weights = _profile_payload(profile_slug)["weights"]
    category_raw = _category_raw_scores(level)
    finals = {}
    for key, cats in category_raw.items():
        value = _final_raw(cats, weights)
        if value is not None:
            finals[key] = value
    return [k for k, _ in sorted(finals.items(), key=lambda kv: kv[1], reverse=True)]


@cache.memoize(timeout=3600)
def build_bes_ranking(level, profile_slug=DEFAULT_PROFILE):
    """Full ranking payload for a level+profile, or None if missing."""
    if level not in LEVELS or not has_bes_data(level):
        return None
    profile = _profile_payload(profile_slug)
    if profile is None:
        return None

    matrix, meta = _matrix_and_meta(level)
    by_category = _indicators_by_category(level)
    territories = get_bes_territories(level)
    weights = profile["weights"]
    all_ids = [i for ids in by_category.values() for i in ids]
    expected = [c for c in QUALITY_LIFE_CATEGORIES if by_category.get(c)]
    empty = [c for c in QUALITY_LIFE_CATEGORIES if not by_category.get(c)]

    category_raw = _category_raw_scores(level)
    # Standardise category scores across territories for readable 0-100 display.
    category_display = {}
    for category in expected:
        raw = {k: category_raw[k][category] for k in category_raw if category in category_raw[k]}
        zz = _standardise(raw)
        category_display[category] = {k: _display(v) for k, v in zz.items()}

    finals = {k: _final_raw(c, weights) for k, c in category_raw.items()}
    finals = {k: v for k, v in finals.items() if v is not None}
    final_display = {k: _display(v) for k, v in _standardise(finals).items()}

    base_order = _ranking_keys(level, DEFAULT_PROFILE)
    base_rank = {k: i + 1 for i, k in enumerate(base_order)}

    rows = []
    unrated = []
    for key, info in territories.items():
        if key not in finals:
            unrated.append({"name": info["name"], "key": key, "region": info["region"]})
            continue
        cats = {c: category_display[c][key] for c in category_raw[key] if c in category_display}
        ordered = sorted(cats.items(), key=lambda kv: kv[1], reverse=True)
        top_pos, top_neg = _top_indicators(key, all_ids, matrix, meta)
        rows.append({
            "name": info["name"],
            "key": key,
            "region": info["region"],
            "metro_city": info["metro_city"],
            "score": final_display[key],
            "raw": finals[key],
            "coverage": round(len(cats) / len(expected), 4) if expected else 0.0,
            "category_scores": cats,
            "strongest_categories": [_category_entry(c, s) for c, s in ordered[:_TOP_CATEGORIES]],
            "weakest_categories": [_category_entry(c, s) for c, s in ordered[::-1][:_TOP_CATEGORIES]],
            "top_positive_indicators": top_pos,
            "top_negative_indicators": top_neg,
        })

    rows.sort(key=lambda r: r["raw"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["delta_rank"] = base_rank.get(row["key"], rank) - rank  # + = up vs balanced
        del row["raw"]

    return {
        "level": level,
        "profile": profile,
        "categories": get_quality_life_categories(),
        "ranking": rows,
        "unrated": unrated,
        "champions": _champions(level, category_display, territories, expected),
        "category_rankings": _category_rankings(level, category_display, territories, expected),
        "methodology": {
            "source": "Istat, BES dei Territori (Bes at local level)",
            "territorial_level": "regioni" if level == "regione" else "province e città metropolitane",
            "normalization": "z-score orientato per indicatore (distanze conservate), display 0-100 con media 50.",
            "indicator_counts": {c: len(ids) for c, ids in by_category.items()},
            "total_indicators": len(all_ids),
            "quality_checks": {"empty_categories": empty,
                               "unrated": [u["name"] for u in unrated]},
        },
    }


def _category_entry(slug, score):
    return {"slug": slug, "name": QUALITY_LIFE_CATEGORIES[slug]["name"], "score": score}


def _top_indicators(key, indicator_ids, matrix, meta, limit=_TOP_INDICATORS):
    scored = []
    for ind_id in indicator_ids:
        if key not in matrix.get(ind_id, {}):
            continue
        info = meta[ind_id]
        scored.append({
            "id": ind_id, "name": info["name"], "theme": info["theme"],
            "score": _display(matrix[ind_id][key]), "year_max": info["year_max"],
            "direction": info["direction"], "path": info["path"],
        })
    top_positive = sorted(scored, key=lambda e: e["score"], reverse=True)[:limit]
    top_negative = sorted(scored, key=lambda e: e["score"])[:limit]
    return top_positive, top_negative


def _champions(level, category_display, territories, expected):
    champions = []
    for category in expected:
        scores = category_display.get(category, {})
        if not scores:
            continue
        best_key = max(scores, key=scores.get)
        info = territories[best_key]
        champions.append({
            "slug": category, "name": QUALITY_LIFE_CATEGORIES[category]["name"],
            "territory": info["name"], "key": best_key, "region": info["region"],
            "score": scores[best_key],
        })
    return champions


def _category_rankings(level, category_display, territories, expected, top=_TOP_PER_CATEGORY):
    rankings = {}
    for category in expected:
        scores = category_display.get(category, {})
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        rows = [{"territory": territories[k]["name"], "key": k,
                 "region": territories[k]["region"], "score": s} for k, s in ordered]
        rankings[category] = {
            "name": QUALITY_LIFE_CATEGORIES[category]["name"],
            "top": rows[:top],
            "bottom": rows[-top:][::-1],
        }
    return rankings


def build_bes_territory(level, key, profile_slug=DEFAULT_PROFILE):
    """One territory's row within a level+profile ranking, or None if unknown."""
    if level not in LEVELS or key not in get_bes_territories(level):
        return None
    ranking = build_bes_ranking(level, profile_slug)
    if ranking is None:
        return None
    row = next((r for r in ranking["ranking"] if r["key"] == key), None)
    if row is None:
        return None
    return {
        "level": level,
        "profile": ranking["profile"],
        "categories": ranking["categories"],
        "territory": row,
        "total": len(ranking["ranking"]),
        "methodology": ranking["methodology"],
    }
