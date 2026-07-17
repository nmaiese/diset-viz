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
from app.indicator_notes import MACRO_AREA_ORDER, THEME_CAVEATS, THEME_EXAMPLES
from app.profiles import indicator_path, slugify
from app.quality_life_config import QUALITY_LIFE_CATEGORIES
from app.quality_life_selection import regional_quality_life_selection


BES_ID_PREFIX = "bes:"
BES_SOURCE_LABEL = "Istat, BES nazionale, aggiornamento intermedio 2026"

_BES_MACRO_AREAS = {
    "Salute": "Demografia e salute",
    "Istruzione e formazione": "Lavoro e istruzione",
    "Lavoro e conciliazione dei tempi di vita": "Lavoro e istruzione",
    "Benessere economico": "Economia e produzione",
    "Relazioni sociali": "Società e inclusione",
    "Politica e istituzioni": "Istituzioni e infrastrutture",
    "Sicurezza": "Società e inclusione",
    "Benessere soggettivo": "Società e inclusione",
    "Paesaggio e patrimonio culturale": "Ambiente, energia e territorio",
    "Ambiente": "Ambiente, energia e territorio",
    "Innovazione, ricerca e creatività": "Economia e produzione",
    "Qualità dei servizi": "Istituzioni e infrastrutture",
}


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
    direction = info["direction"]
    if direction == "higher_better":
        reading = "A parità di condizioni, un valore più alto descrive un esito più favorevole."
    elif direction in {"lower_better", "higher_worse"}:
        reading = "A parità di condizioni, un valore più basso descrive un esito più favorevole."
    else:
        reading = "Il dato descrive il territorio, ma non stabilisce da solo quale regione stia meglio."
    return {
        "plain": f"È un indicatore del dominio BES «{info['domain_name']}» pubblicato da Istat.",
        "example": "Esempio: confronta il valore regionale con le altre regioni e con la serie storica.",
        "reading": reading,
        "caveat": (
            "Il confronto va letto insieme a unità di misura, anno e copertura. "
            "Una media regionale può nascondere differenze interne al territorio."
        ),
        "direction": direction,
    }


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
    metadata = {
        "id": public_id,
        "raw_id": raw_id,
        "theme": info["domain_name"],
        "macro_area": _BES_MACRO_AREAS.get(info["domain_name"], "Altro"),
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


def _catalog_entry(payload):
    return dict(payload["metadata"])


@lru_cache(maxsize=1)
def get_atlas_catalog():
    """Merge legacy territorial metadata and BES metadata for atlas browsing."""
    legacy = get_catalog()
    score_selection = regional_quality_life_selection()
    legacy_indicators = [
        {
            **item,
            "catalog_family": "territorial",
            "catalog_family_label": "Indicatori territoriali",
            "path": indicator_path(item["id"], item["name"]),
            "quality_life_scored": item["id"] in score_selection,
            "quality_life_category": score_selection.get(item["id"]),
        }
        for item in legacy["indicators"]
    ]
    bes_indicators = [
        {
            **_catalog_entry(get_bes_atlas_indicator(_bes_public_id(raw_id))),
            "quality_life_scored": _bes_public_id(raw_id) in score_selection,
            "quality_life_category": score_selection.get(_bes_public_id(raw_id)),
        }
        for raw_id in get_bes_manifest("regione")
    ]
    for item in legacy_indicators + bes_indicators:
        category = item.get("quality_life_category")
        item["quality_life_category_label"] = (
            QUALITY_LIFE_CATEGORIES[category]["name"] if category else None
        )
    indicators = sorted(
        legacy_indicators + bes_indicators,
        key=lambda item: (item["theme"].lower(), item["name"].lower(), item["catalog_family"]),
    )

    themes = defaultdict(lambda: {"indicator_count": 0, "row_count": 0, "macro_area": "Altro"})
    for item in indicators:
        theme = themes[item["theme"]]
        theme["indicator_count"] += 1
        theme["row_count"] += item["row_count"]
        if theme["macro_area"] == "Altro" or item["macro_area"] != "Altro":
            theme["macro_area"] = item["macro_area"]
    theme_items = [
        {"name": name, **payload}
        for name, payload in sorted(themes.items(), key=lambda pair: pair[0].lower())
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
                **payload["metadata"],
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
            **payload["metadata"],
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


@lru_cache(maxsize=1)
def _theme_slug_map():
    return {slugify(theme["name"]): theme["name"] for theme in get_atlas_catalog()["themes"]}


def get_atlas_theme_profile(theme_slug):
    name = _theme_slug_map().get(theme_slug)
    if name is None:
        return None
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
        }
        for item in get_atlas_catalog()["indicators"]
        if item["theme"] == name
    ]
    indicators.sort(key=lambda item: (not item["complete"], item["name"].lower()))
    theme = next(item for item in get_atlas_catalog()["themes"] if item["name"] == name)
    return {
        "theme": name,
        "theme_slug": theme_slug,
        "theme_path": f"/tema/{theme_slug}",
        "macro_area": theme["macro_area"],
        "example": THEME_EXAMPLES.get(name),
        "caveat": THEME_CAVEATS.get(name),
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
            "path": f"/tema/{slugify(theme['name'])}",
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
            "path": f"/tema/{slugify(theme['name'])}",
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
        haystack = " ".join(
            unicodedata.normalize(
                "NFKD",
                f"{item['name']} {item['theme']} {item.get('archive', '')} {item['catalog_family_label']}",
            ).encode("ascii", "ignore").decode("ascii").lower().split()
        )
        if query and query not in haystack:
            continue
        results.append(item)
        if len(results) >= limit:
            break
    return results
