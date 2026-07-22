"""Federated regional atlas over the territorial and national BES datasets.

The legacy territorial CSV remains the source of truth for ``app.data`` and for
regional profiles.  This module only adapts national BES regional observations
to the public atlas API contract, using namespaced ids so the two source
families can coexist without collisions or accidental double counting.
"""

from collections import defaultdict
from functools import lru_cache
import unicodedata

from app.bes_data import BES_SOURCE_URLS, bes_indicator_path, get_bes_manifest, get_bes_rows
from app.data import REGION_ORDER, get_catalog, get_indicator
from app.indicator_notes import build_bes_indicator_explain
from app.multiscopo_data import (
    SOURCE_URL as MULTISCOPO_SOURCE_URL,
    get_multiscopo_manifest,
    get_multiscopo_rows,
    has_multiscopo_data,
    multiscopo_indicator_path,
)
from app.profiles import indicator_path, slugify
from app.quality_life_config import QUALITY_LIFE_CATEGORIES
from app.quality_life_selection import regional_quality_life_selection
from app.taxonomy import (
    CANONICAL_CATEGORIES,
    DUPLICATE_BES_IDS,
    MACRO_AREA_ORDER,
    canonical_category_slug,
    category_metadata,
    category_path,
)


BES_ID_PREFIX = "bes:"
BES_SOURCE_LABEL = "Istat, BES nazionale, aggiornamento intermedio 2026"
MULTI_ID_PREFIX = "multiscopo:"
MULTI_SOURCE_LABEL = "Istat, Indagine Multiscopo sulle famiglie"

def _region_sort_key(name):
    try:
        return REGION_ORDER.index(name)
    except ValueError:
        return len(REGION_ORDER)


def _bes_public_id(indicator_id):
    return f"{BES_ID_PREFIX}{indicator_id}"


def _bes_raw_id(indicator_id):
    value = str(indicator_id)
    return value[len(BES_ID_PREFIX):] if value.startswith(BES_ID_PREFIX) else None


def _bes_explain(info):
    return info.get("explain") or build_bes_indicator_explain(info, "territori regionali")


def _national_average(rows, years):
    points = []
    for year in years:
        values = [row["value"] for row in rows if row["year"] == year and row["value"] is not None]
        if values:
            points.append({"year": year, "value": sum(values) / len(values)})
    return points


def _downsample(points, limit=24):
    if len(points) <= limit:
        return points
    positions = {round(index * (len(points) - 1) / (limit - 1)) for index in range(limit)}
    return [point for index, point in enumerate(points) if index in positions]


@lru_cache(maxsize=1)
def _bes_rows_by_indicator():
    index = defaultdict(list)
    for row in get_bes_rows("regione"):
        index[row["id"]].append(row)
    return dict(index)


@lru_cache(maxsize=None)
def get_bes_atlas_indicator(indicator_id):
    """Return one national BES regional indicator in the atlas API shape."""
    raw_id = _bes_raw_id(indicator_id)
    if raw_id is None:
        return None
    info = get_bes_manifest("regione").get(raw_id)
    rows = _bes_rows_by_indicator().get(raw_id, [])
    if info is None or not rows:
        return None

    years = sorted({row["year"] for row in rows})
    regions = sorted({row["territory"] for row in rows}, key=_region_sort_key)
    non_null = sum(row["value"] is not None for row in rows)
    grid = len(years) * len(regions)
    historical_completeness = round(non_null / grid, 4) if grid else 0.0
    latest_year = years[-1]
    latest_region_count = sum(
        row["year"] == latest_year and row["value"] is not None for row in rows
    )
    completeness = info["coverage_latest"]
    public_id = _bes_public_id(raw_id)
    averages = _national_average(rows, years)
    spark = [
        {"year": point["year"], "value": round(point["value"], 3)}
        for point in _downsample(averages)
    ]
    first = rows[0]
    source_theme = info["domain_name"]
    metadata = {
        "id": public_id,
        "raw_id": raw_id,
        **category_metadata(source_theme),
        "name": info["name"],
        "unit": info["unit"],
        "source": first.get("source") or BES_SOURCE_LABEL,
        "source_label": BES_SOURCE_LABEL,
        "source_url": BES_SOURCE_URLS["regione"],
        "archive": first.get("archive") or "Benessere equo e sostenibile, appendice regionale",
        "explain": _bes_explain(info),
        "years": years,
        "year_min": years[0],
        "year_max": years[-1],
        "regions": regions,
        "region_count": latest_region_count,
        "row_count": len(rows),
        "completeness": completeness,
        "historical_completeness": historical_completeness,
        "complete": latest_region_count == 20 and completeness >= 0.98,
        "spark": spark,
        "catalog_family": "bes",
        "catalog_family_label": "Qualità della vita, BES",
        "path": bes_indicator_path(raw_id, info["name"]),
    }
    series = [
        {
            "year": row["year"],
            "region": row["territory"],
            "region_key": row["territory_key"],
            "value": row["value"],
        }
        for row in sorted(rows, key=lambda item: (item["year"], _region_sort_key(item["territory"])))
    ]
    return {"metadata": metadata, "series": series}


def _multi_public_id(indicator_id):
    return f"{MULTI_ID_PREFIX}{indicator_id}"


def _multi_raw_id(indicator_id):
    value = str(indicator_id)
    return value[len(MULTI_ID_PREFIX):] if value.startswith(MULTI_ID_PREFIX) else None


@lru_cache(maxsize=1)
def _multiscopo_rows_by_indicator():
    index = defaultdict(list)
    for row in get_multiscopo_rows():
        index[row["id"]].append(row)
    return dict(index)


@lru_cache(maxsize=None)
def get_multiscopo_atlas_indicator(indicator_id):
    """Return one Multiscopo regional indicator in the atlas API shape."""
    raw_id = _multi_raw_id(indicator_id)
    if raw_id is None:
        return None
    info = get_multiscopo_manifest().get(raw_id)
    rows = _multiscopo_rows_by_indicator().get(raw_id, [])
    if info is None or not rows:
        return None

    years = sorted({row["year"] for row in rows})
    regions = sorted({row["territory"] for row in rows}, key=_region_sort_key)
    non_null = sum(row["value"] is not None for row in rows)
    grid = len(years) * len(regions)
    historical_completeness = round(non_null / grid, 4) if grid else 0.0
    latest_year = years[-1]
    latest_region_count = sum(
        row["year"] == latest_year and row["value"] is not None for row in rows
    )
    completeness = info["coverage_latest"]
    public_id = _multi_public_id(raw_id)
    averages = _national_average(rows, years)
    spark = [
        {"year": point["year"], "value": round(point["value"], 3)}
        for point in _downsample(averages)
    ]
    first = rows[0]
    source_theme = info["domain_name"]
    metadata = {
        "id": public_id,
        "raw_id": raw_id,
        **category_metadata(source_theme),
        "name": info["name"],
        "unit": info["unit"],
        "source": first.get("source") or MULTI_SOURCE_LABEL,
        "source_label": MULTI_SOURCE_LABEL,
        "source_url": MULTISCOPO_SOURCE_URL,
        "archive": first.get("archive") or "Indagine Multiscopo sulle famiglie",
        "explain": info.get("explain") or build_bes_indicator_explain(info, "regioni"),
        "years": years,
        "year_min": years[0],
        "year_max": years[-1],
        "regions": regions,
        "region_count": latest_region_count,
        "row_count": len(rows),
        "completeness": completeness,
        "historical_completeness": historical_completeness,
        "complete": latest_region_count == 20 and completeness >= 0.98,
        "spark": spark,
        "catalog_family": "multiscopo",
        "catalog_family_label": "Indagine Multiscopo",
        "path": multiscopo_indicator_path(raw_id, info["name"]),
    }
    series = [
        {
            "year": row["year"],
            "region": row["territory"],
            "region_key": row["territory_key"],
            "value": row["value"],
        }
        for row in sorted(rows, key=lambda item: (item["year"], _region_sort_key(item["territory"])))
    ]
    return {"metadata": metadata, "series": series}


def _catalog_entry(payload):
    return dict(payload["metadata"])


def _canonicalize_item(item):
    """Add the public category while retaining the exact Istat source label."""
    source_theme = item.get("source_theme") or item.get("theme") or ""
    return {**item, **category_metadata(source_theme)}


@lru_cache(maxsize=1)
def get_atlas_catalog():
    """Merge legacy territorial metadata and BES metadata for atlas browsing."""
    legacy = get_catalog()
    score_selection = regional_quality_life_selection()
    legacy_indicators = [
        _canonicalize_item({
            **item,
            "catalog_family": "territorial",
            "catalog_family_label": "Indicatori territoriali",
            "path": indicator_path(item["id"], item["name"]),
            "quality_life_scored": item["id"] in score_selection,
            "quality_life_category": score_selection.get(item["id"]),
        })
        for item in legacy["indicators"]
    ]
    bes_indicators = [
        {
            **_catalog_entry(get_bes_atlas_indicator(_bes_public_id(raw_id))),
            "quality_life_scored": _bes_public_id(raw_id) in score_selection,
            "quality_life_category": score_selection.get(_bes_public_id(raw_id)),
        }
        for raw_id in get_bes_manifest("regione")
        if raw_id not in DUPLICATE_BES_IDS
    ]
    multiscopo_indicators = [
        {
            **_catalog_entry(get_multiscopo_atlas_indicator(_multi_public_id(raw_id))),
            "quality_life_scored": _multi_public_id(raw_id) in score_selection,
            "quality_life_category": score_selection.get(_multi_public_id(raw_id)),
        }
        for raw_id in get_multiscopo_manifest()
    ] if has_multiscopo_data() else []
    for item in legacy_indicators + bes_indicators + multiscopo_indicators:
        category = item.get("quality_life_category")
        item["quality_life_category_label"] = (
            QUALITY_LIFE_CATEGORIES[category]["name"] if category else None
        )
    indicators = sorted(
        legacy_indicators + bes_indicators + multiscopo_indicators,
        key=lambda item: (item["theme"].lower(), item["name"].lower(), item["catalog_family"]),
    )

    themes = defaultdict(
        lambda: {"indicator_count": 0, "row_count": 0, "source_themes": set()}
    )
    for item in indicators:
        theme = themes[item["theme"]]
        theme["indicator_count"] += 1
        theme["row_count"] += item["row_count"]
        theme["source_themes"].add(item["source_theme"])
    theme_items = [
        {
            "name": category["name"],
            "slug": slug,
            "path": category_path(slug),
            "description": category["description"],
            "macro_area": category["macro_area"],
            "indicator_count": themes[category["name"]]["indicator_count"],
            "row_count": themes[category["name"]]["row_count"],
            "source_themes": sorted(themes[category["name"]]["source_themes"]),
        }
        for slug, category in CANONICAL_CATEGORIES.items()
        if category["name"] in themes
    ]

    macro = defaultdict(lambda: {"themes": [], "indicator_count": 0})
    for theme in theme_items:
        bucket = macro[theme["macro_area"]]
        bucket["themes"].append(theme["name"])
        bucket["indicator_count"] += theme["indicator_count"]
    ordered_areas = [area for area in MACRO_AREA_ORDER if area in macro]
    ordered_areas += [area for area in macro if area not in MACRO_AREA_ORDER]

    return {
        "featured_indicator_id": legacy["featured_indicator_id"],
        "regions": legacy["regions"],
        "themes": theme_items,
        "macro_areas": [
            {
                "name": area,
                "themes": macro[area]["themes"],
                "indicator_count": macro[area]["indicator_count"],
            }
            for area in ordered_areas
        ],
        "source_families": [
            {
                "id": "territorial",
                "label": "Indicatori territoriali",
                "indicator_count": len(legacy_indicators),
            },
            {
                "id": "bes",
                "label": "Qualità della vita, BES",
                "indicator_count": len(bes_indicators),
            },
            {
                "id": "multiscopo",
                "label": "Indagine Multiscopo",
                "indicator_count": len(multiscopo_indicators),
            },
        ],
        "indicators": indicators,
    }


def get_atlas_indicator(indicator_id):
    if _bes_raw_id(indicator_id) is not None:
        payload = get_bes_atlas_indicator(str(indicator_id))
        if payload is None:
            return None
        category = regional_quality_life_selection().get(str(indicator_id))
        return {
            **payload,
            "metadata": {
                **_canonicalize_item(payload["metadata"]),
                "quality_life_scored": category is not None,
                "quality_life_category": category,
                "quality_life_category_label": (
                    QUALITY_LIFE_CATEGORIES[category]["name"] if category else None
                ),
            },
        }
    if _multi_raw_id(indicator_id) is not None:
        payload = get_multiscopo_atlas_indicator(str(indicator_id))
        if payload is None:
            return None
        category = regional_quality_life_selection().get(str(indicator_id))
        return {
            **payload,
            "metadata": {
                **_canonicalize_item(payload["metadata"]),
                "quality_life_scored": category is not None,
                "quality_life_category": category,
                "quality_life_category_label": (
                    QUALITY_LIFE_CATEGORIES[category]["name"] if category else None
                ),
            },
        }
    payload = get_indicator(str(indicator_id))
    if payload is None:
        return None
    category = regional_quality_life_selection().get(str(indicator_id))
    return {
        **payload,
        "metadata": {
            **_canonicalize_item(payload["metadata"]),
            "catalog_family": "territorial",
            "catalog_family_label": "Indicatori territoriali",
            "path": indicator_path(payload["metadata"]["id"], payload["metadata"]["name"]),
            "quality_life_scored": category is not None,
            "quality_life_category": category,
            "quality_life_category_label": (
                QUALITY_LIFE_CATEGORIES[category]["name"] if category else None
            ),
        },
    }


def get_atlas_indicator_year(indicator_id, year):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        return None
    values = [
        row for row in payload["series"]
        if row["year"] == year and row["value"] is not None
    ]
    values.sort(key=lambda row: row["value"], reverse=True)
    return {"metadata": payload["metadata"], "year": year, "values": values}


def get_atlas_theme_profile(theme_slug):
    category_slug = canonical_category_slug(theme_slug)
    if category_slug is None:
        return None
    category = CANONICAL_CATEGORIES[category_slug]
    name = category["name"]
    indicators = [
        {
            "id": item["id"],
            "name": item["name"],
            "path": item["path"],
            "year_min": item["year_min"],
            "year_max": item["year_max"],
            "region_count": item["region_count"],
            "complete": item["complete"],
            "plain": (item.get("explain") or {}).get("plain"),
            "catalog_family_label": item["catalog_family_label"],
            "quality_life_scored": item["quality_life_scored"],
            "quality_life_category_label": item["quality_life_category_label"],
            "source_theme": item["source_theme"],
        }
        for item in get_atlas_catalog()["indicators"]
        if item["theme"] == name
    ]
    indicators.sort(key=lambda item: (not item["complete"], item["name"].lower()))
    theme = next(item for item in get_atlas_catalog()["themes"] if item["name"] == name)
    return {
        "theme": name,
        "theme_slug": slugify(name),
        "theme_path": category_path(category_slug),
        "macro_area": theme["macro_area"],
        "description": category["description"],
        "source_themes": theme["source_themes"],
        "indicator_count": len(indicators),
        "complete_count": sum(item["complete"] for item in indicators),
        "quality_life_count": sum(item["quality_life_scored"] for item in indicators),
        "indicators": indicators,
    }


@lru_cache(maxsize=1)
def atlas_themes_by_macro_area():
    catalog = get_atlas_catalog()
    by_macro = defaultdict(list)
    for theme in catalog["themes"]:
        by_macro[theme["macro_area"]].append({
            "theme": theme["name"],
            "path": theme["path"],
            "indicator_count": theme["indicator_count"],
        })
    return [
        {
            "macro_area": area["name"],
            "indicator_count": area["indicator_count"],
            "themes": sorted(by_macro[area["name"]], key=lambda item: item["theme"]),
        }
        for area in catalog["macro_areas"]
    ]


def all_atlas_themes_index():
    return [
        {
            "theme": theme["name"],
            "path": theme["path"],
            "indicator_count": theme["indicator_count"],
        }
        for theme in get_atlas_catalog()["themes"]
    ]


def search_atlas_indicators(query="", theme=None, limit=50):
    query = " ".join(
        unicodedata.normalize("NFKD", query or "").encode("ascii", "ignore").decode("ascii").lower().split()
    )
    results = []
    for item in get_atlas_catalog()["indicators"]:
        if theme and item["theme"] != theme:
            continue
        explain = item.get("explain") or {}
        haystack = " ".join(
            unicodedata.normalize(
                "NFKD",
                f"{item['name']} {item['theme']} {item.get('source_theme', '')} "
                f"{item.get('archive', '')} {item['catalog_family_label']} "
                f"{explain.get('plain', '')} {explain.get('example', '')}",
            ).encode("ascii", "ignore").decode("ascii").lower().split()
        )
        if query and query not in haystack:
            continue
        results.append(item)
        if len(results) >= limit:
            break
    return results
