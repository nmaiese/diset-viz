"""Harmonised regional profiles and SEO landing-page data.

Raw indicator values use mixed units (percentages, euros, indices, counts), so
they are never compared across indicators. Instead each indicator is normalised
*within itself* (same latest year, all regions) into a percentile, which makes
regions comparable on a single 0..1 axis per indicator.

- Similarity between regions uses the neutral value-percentile vector over the
  "complete" indicator subset (20 regions, >=98% filled). Direction is irrelevant
  for distance, so the neutral percentile is used directly.
- "Excels / lags" uses only directional indicators (lower_better / higher_worse /
  higher_better) from the complete subset, oriented so that 1.0 = best. Indicators
  flagged "contextual" by indicator_notes are excluded from scoring (no clear
  good/bad direction) but still surface on the page descriptively.
- Theme strength is the mean oriented percentile of a theme's directional
  indicators, computed only for themes with at least MIN_THEME_INDICATORS of them.
"""

import math
import re
import unicodedata
from collections import defaultdict

from app.cache import cache
from app.data import REGION_ORDER, get_catalog, get_rows

# Directions that carry a clear better/worse meaning (everything else is contextual).
SCOREABLE_DIRECTIONS = ("lower_better", "higher_worse", "higher_better")
HIGHER_IS_BETTER = "higher_better"
# A theme needs at least this many directional indicators before we rank a region
# as strong or weak in it; below this the average is too noisy to be honest.
MIN_THEME_INDICATORS = 3
SIMILAR_COUNT = 4
# Region views only use indicators that are both complete (all 20 regions) and
# reasonably current. Istat publishes most series with a lag, so 2025 data barely
# exists; 2023 is the most recent year with broad complete coverage.
CORE_MIN_YEAR = 2023


def is_core(item):
    """An indicator usable in region profiles: complete and reasonably current."""
    return item["complete"] and item["year_max"] >= CORE_MIN_YEAR


def slugify(value):
    """Accent-stripped, hyphen-collapsed slug for indicator and theme names."""
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", " ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def region_key_for(region):
    """Slug used in /regione/<key>, matching data.py's region_key field."""
    value = unicodedata.normalize("NFKD", region).encode("ascii", "ignore").decode("ascii")
    return value.lower().replace("'", " ").replace(" ", "-")


@cache.memoize(timeout=3600)
def _region_key_map():
    return {region_key_for(region): region for region in REGION_ORDER}


def region_name(region_key):
    return _region_key_map().get(region_key)


def indicator_slug(name):
    slug = slugify(name)
    # Keep URLs readable; the numeric id in front is what actually resolves.
    return slug[:80].rstrip("-")


def indicator_path(indicator_id, name):
    slug = indicator_slug(name)
    return f"/indicatore/{indicator_id}-{slug}" if slug else f"/indicatore/{indicator_id}"


@cache.memoize(timeout=3600)
def _theme_slug_map():
    """slug -> exact theme name, built from the catalog so it always matches data."""
    return {slugify(theme["name"]): theme["name"] for theme in get_catalog()["themes"]}


def theme_name(theme_slug):
    return _theme_slug_map().get(theme_slug)


def theme_path(name):
    return f"/tema/{slugify(name)}"


@cache.memoize(timeout=3600)
def _percentile_matrix():
    """Per complete indicator, the neutral value-percentile of each region.

    Returns dict: indicator_id -> {region_key: percentile in [0, 1]} where higher
    percentile means a higher raw value (direction not yet applied). Only "complete"
    indicators are included, so every region is present on every axis.
    """
    catalog = get_catalog()
    complete = {
        item["id"]: item["year_max"]
        for item in catalog["indicators"]
        if is_core(item)
    }

    latest_by_id = defaultdict(dict)  # id -> {region_key: value}
    for row in get_rows():
        ind_id = row["id"]
        year = complete.get(ind_id)
        if year is None or row["year"] != year or row["value"] is None:
            continue
        latest_by_id[ind_id][row["region_key"]] = row["value"]

    matrix = {}
    for ind_id, by_region in latest_by_id.items():
        ranked = sorted(by_region.items(), key=lambda kv: (kv[1], kv[0]))
        n = len(ranked)
        if n < 2:
            continue
        matrix[ind_id] = {region: idx / (n - 1) for idx, (region, _) in enumerate(ranked)}
    return matrix


@cache.memoize(timeout=3600)
def _indicator_meta():
    """id -> light metadata needed for scoring and links."""
    return {
        item["id"]: {
            "id": item["id"],
            "name": item["name"],
            "theme": item["theme"],
            "unit": item["unit"],
            "direction": (item.get("explain") or {}).get("direction"),
            "year_max": item["year_max"],
            "path": indicator_path(item["id"], item["name"]),
        }
        for item in get_catalog()["indicators"]
    }


def _oriented(percentile, direction):
    """Re-orient a neutral percentile so 1.0 = best for this indicator."""
    if direction == HIGHER_IS_BETTER:
        return percentile
    return 1.0 - percentile  # lower_better and higher_worse: lower value is better


@cache.memoize(timeout=3600)
def _similarity_matrix():
    """region_key -> list of (other_key, distance) sorted nearest first."""
    matrix = _percentile_matrix()
    keys = list(_region_key_map().keys())
    vectors = {key: [] for key in keys}
    for by_region in matrix.values():
        if not all(key in by_region for key in keys):
            continue
        for key in keys:
            vectors[key].append(by_region[key])

    result = {}
    for a in keys:
        dists = []
        for b in keys:
            if a == b:
                continue
            dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(vectors[a], vectors[b])))
            dists.append((b, dist))
        dists.sort(key=lambda kv: kv[1])
        result[a] = dists
    return result


def similar_regions(region_key, k=SIMILAR_COUNT):
    neighbours = _similarity_matrix().get(region_key, [])[:k]
    return [
        {"region": region_name(other), "region_key": other, "distance": round(dist, 4)}
        for other, dist in neighbours
    ]


@cache.memoize(timeout=3600)
def region_profile(region_key):
    """Harmonised profile for one region, or None if the key is unknown."""
    region = region_name(region_key)
    if region is None:
        return None

    matrix = _percentile_matrix()
    meta = _indicator_meta()

    scored = []          # directional indicators with this region's oriented score
    by_theme = defaultdict(list)
    for ind_id, by_region in matrix.items():
        if region_key not in by_region:
            continue
        info = meta.get(ind_id)
        if not info:
            continue
        direction = info["direction"]
        if direction not in SCOREABLE_DIRECTIONS:
            continue
        oriented = _oriented(by_region[region_key], direction)
        entry = {
            "id": ind_id,
            "name": info["name"],
            "theme": info["theme"],
            "path": info["path"],
            "score": round(oriented, 4),
        }
        scored.append(entry)
        by_theme[info["theme"]].append(entry)

    theme_table = []
    for theme, entries in by_theme.items():
        avg = sum(e["score"] for e in entries) / len(entries)
        theme_table.append({
            "theme": theme,
            "theme_path": theme_path(theme),
            "count": len(entries),
            "score": round(avg, 4),
            "rated": len(entries) >= MIN_THEME_INDICATORS,
        })
    theme_table.sort(key=lambda t: t["score"], reverse=True)

    rated = [t for t in theme_table if t["rated"]]
    themes_strong = [t for t in rated if t["score"] >= 0.6][:4]
    themes_weak = [t for t in reversed(rated) if t["score"] <= 0.4][:4]

    top_excels = sorted(scored, key=lambda e: e["score"], reverse=True)
    top_excels = [e for e in top_excels if e["score"] >= 0.7][:6]
    top_lags = sorted(scored, key=lambda e: e["score"])
    top_lags = [e for e in top_lags if e["score"] <= 0.3][:6]

    return {
        "region": region,
        "region_key": region_key,
        "scored_count": len(scored),
        "theme_table": theme_table,
        "themes_strong": themes_strong,
        "themes_weak": themes_weak,
        "top_excels": top_excels,
        "top_lags": top_lags,
        "similar_regions": similar_regions(region_key),
    }


@cache.memoize(timeout=3600)
def theme_profile(theme_slug):
    """Indicator hub for one theme, or None if the slug is unknown."""
    name = theme_name(theme_slug)
    if name is None:
        return None

    indicators = [
        {
            "id": item["id"],
            "name": item["name"],
            "unit": item["unit"],
            "path": indicator_path(item["id"], item["name"]),
            "year_min": item["year_min"],
            "year_max": item["year_max"],
            "region_count": item["region_count"],
            "completeness": item["completeness"],
            "complete": item["complete"],
            "spark": item["spark"],
            "plain": (item.get("explain") or {}).get("plain"),
        }
        for item in get_catalog()["indicators"]
        if item["theme"] == name
    ]
    indicators.sort(key=lambda i: (not i["complete"], i["name"]))

    return {
        "theme": name,
        "theme_slug": theme_slug,
        "theme_path": theme_path(name),
        "indicator_count": len(indicators),
        "indicators": indicators,
    }


@cache.memoize(timeout=3600)
def all_regions_index():
    return [
        {"region": region, "region_key": region_key_for(region), "path": f"/regione/{region_key_for(region)}"}
        for region in REGION_ORDER
    ]


@cache.memoize(timeout=3600)
def regions_overview():
    """Compact per-region data for the clickable map tooltips."""
    overview = {}
    for region in REGION_ORDER:
        key = region_key_for(region)
        profile = region_profile(key)
        overview[key] = {
            "region": region,
            "path": f"/regione/{key}",
            "strong": [t["theme"] for t in profile["themes_strong"][:2]],
            "weak": [t["theme"] for t in profile["themes_weak"][:2]],
        }
    return overview


@cache.memoize(timeout=3600)
def all_themes_index():
    return [
        {
            "theme": theme["name"],
            "path": theme_path(theme["name"]),
            "indicator_count": theme["indicator_count"],
        }
        for theme in get_catalog()["themes"]
    ]
