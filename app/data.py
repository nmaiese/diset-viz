import csv
import math
import os
import unicodedata
from collections import defaultdict

from app.cache import cache
from app.indicator_notes import build_indicator_explain


DATASET_PATH = os.path.join(os.path.dirname(__file__), "static/data/Assoluti_Regione.csv")
REGION_ORDER = [
    "Piemonte",
    "Valle d'Aosta",
    "Lombardia",
    "Trentino Alto Adige",
    "Veneto",
    "Friuli-Venezia Giulia",
    "Liguria",
    "Emilia-Romagna",
    "Toscana",
    "Umbria",
    "Marche",
    "Lazio",
    "Abruzzo",
    "Molise",
    "Campania",
    "Puglia",
    "Basilicata",
    "Calabria",
    "Sicilia",
    "Sardegna",
]


# Verifiable source links per indicator. Most series come from the Banca dati
# territoriale per le politiche di sviluppo (BDTPS); the "Reddito e ricchezza"
# series are the Conti economici territoriali published on IstatData, so they
# point to the Istat archive page for that release instead.
SOURCE_BDTPS = {
    "label": "Istat, Banca dati territoriale per le politiche di sviluppo",
    "url": "https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/",
}
SOURCE_CONTI_TERRITORIALI = {
    "label": "Istat, Conti economici territoriali",
    "url": "https://www.istat.it/it/archivio/conti+territoriali",
}
SOURCE_DEMOGRAFICI = {
    "label": "Istat, Indicatori demografici",
    "url": "https://www.istat.it/statistiche-per-temi/popolazione-e-famiglie/",
}
CONTI_TERRITORIALI_IDS = {"901", "902", "903", "904", "905"}
DEMOGRAFICI_IDS = {"910", "911", "912", "913", "920", "921", "922", "923"}


def source_for(indicator_id):
    """Authoritative Istat source link for an indicator (label + url)."""
    iid = str(indicator_id)
    if iid in CONTI_TERRITORIALI_IDS:
        return SOURCE_CONTI_TERRITORIALI
    if iid in DEMOGRAFICI_IDS:
        return SOURCE_DEMOGRAFICI
    return SOURCE_BDTPS


def _parse_number(value):
    if value is None or not value.strip():
        return None
    normalized = value.strip().replace(".", "").replace(",", ".")
    if not normalized or normalized == "-":
        return None
    try:
        number = float(normalized)
    except ValueError:
        return None
    # Istat uses "INF" placeholders for undefined ratios; treat non-finite as missing.
    return number if math.isfinite(number) else None


def _slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return value.lower().replace("'", " ").replace(" ", "-")


def _clean_text(value):
    return " ".join((value or "").split())


@cache.memoize(timeout=3600)
def get_rows():
    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = []
        for row in reader:
            rows.append(
                {
                    "id": row["idIndicatore"],
                    "territory": row["Territorio"],
                    "region_key": _slugify(row["Territorio"]),
                    "theme": _clean_text(row["Tema"]),
                    "indicator": _clean_text(row["Indicatore"]),
                    "unit": _clean_text(row["UDM"]),
                    "source": _clean_text(row["Fonte"]),
                    "archive": _clean_text(row["Archivio"]),
                    "year": int(row["Anno"]),
                    "value": _parse_number(row["Dato"]),
                }
            )
    return rows


@cache.memoize(timeout=3600)
def get_catalog():
    rows = get_rows()
    by_id = defaultdict(list)
    for row in rows:
        by_id[row["id"]].append(row)

    themes = defaultdict(lambda: {"indicator_count": 0, "row_count": 0})
    indicators = []
    featured_id = None
    featured_score = -1

    for indicator_id, indicator_rows in by_id.items():
        first = indicator_rows[0]
        years = sorted({row["year"] for row in indicator_rows})
        regions = sorted({row["territory"] for row in indicator_rows}, key=_region_sort_key)
        latest_year = years[-1]
        latest_values = [row for row in indicator_rows if row["year"] == latest_year and row["value"] is not None]
        score = (len(years) * 1000) + (latest_year * 10) + len(latest_values)

        non_null = sum(1 for row in indicator_rows if row["value"] is not None)
        grid = len(regions) * len(years)
        completeness = round(non_null / grid, 4) if grid else 0.0
        complete = len(regions) == 20 and completeness >= 0.98

        national_avg = _national_average(indicator_rows, years)
        spark = [
            {"year": point["year"], "value": round(point["value"], 3)}
            for point in _downsample(national_avg, 24)
        ]

        if score > featured_score:
            featured_score = score
            featured_id = indicator_id

        themes[first["theme"]]["indicator_count"] += 1
        themes[first["theme"]]["row_count"] += len(indicator_rows)
        indicators.append(
            {
                "id": indicator_id,
                "theme": first["theme"],
                "name": first["indicator"],
                "unit": first["unit"],
                "source": first["source"],
                "source_label": source_for(indicator_id)["label"],
                "source_url": source_for(indicator_id)["url"],
                "archive": first["archive"],
                "explain": build_indicator_explain(first),
                "years": years,
                "year_min": years[0],
                "year_max": latest_year,
                "regions": regions,
                "region_count": len(regions),
                "row_count": len(indicator_rows),
                "completeness": completeness,
                "complete": complete,
                "spark": spark,
            }
        )

    indicators.sort(key=lambda item: (item["theme"], item["name"]))
    theme_items = [
        {"name": name, **payload}
        for name, payload in sorted(themes.items(), key=lambda item: item[0].lower())
    ]

    return {
        "featured_indicator_id": featured_id,
        "regions": REGION_ORDER,
        "themes": theme_items,
        "indicators": indicators,
    }


def get_indicator(indicator_id):
    rows = [row for row in get_rows() if row["id"] == indicator_id]
    if not rows:
        return None

    first = rows[0]
    years = sorted({row["year"] for row in rows})
    regions = sorted({row["territory"] for row in rows}, key=_region_sort_key)
    series = [
        {
            "year": row["year"],
            "region": row["territory"],
            "region_key": row["region_key"],
            "value": row["value"],
        }
        for row in sorted(rows, key=lambda item: (item["year"], _region_sort_key(item["territory"])))
    ]

    return {
        "metadata": {
            "id": indicator_id,
            "theme": first["theme"],
            "name": first["indicator"],
            "unit": first["unit"],
            "source": first["source"],
            "source_label": source_for(indicator_id)["label"],
            "source_url": source_for(indicator_id)["url"],
            "archive": first["archive"],
            "explain": build_indicator_explain(first),
            "years": years,
            "year_min": years[0],
            "year_max": years[-1],
            "regions": regions,
        },
        "series": series,
    }


def get_indicator_year(indicator_id, year):
    indicator = get_indicator(indicator_id)
    if indicator is None:
        return None

    values = [
        row for row in indicator["series"]
        if row["year"] == year and row["value"] is not None
    ]
    values.sort(key=lambda row: row["value"], reverse=True)

    return {
        "metadata": indicator["metadata"],
        "year": year,
        "values": values,
    }


def search_indicators(query="", theme=None, limit=50):
    query = _normalize_search(query)
    theme = _clean_text(theme)
    results = []

    for item in get_catalog()["indicators"]:
        if theme and item["theme"] != theme:
            continue
        haystack = _normalize_search(f"{item['name']} {item['theme']} {item['archive']}")
        if query and query not in haystack:
            continue
        results.append(item)
        if len(results) >= limit:
            break

    return results


def _normalize_search(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(value.lower().split())


def _region_sort_key(region):
    try:
        return REGION_ORDER.index(region)
    except ValueError:
        return len(REGION_ORDER)


def _national_average(rows, years):
    by_year = defaultdict(list)
    for row in rows:
        if row["value"] is not None:
            by_year[row["year"]].append(row["value"])
    series = []
    for year in years:
        values = by_year.get(year)
        if values:
            series.append({"year": year, "value": sum(values) / len(values)})
    return series


def _downsample(points, max_points):
    count = len(points)
    if count <= max_points:
        return points
    step = (count - 1) / (max_points - 1)
    indices = sorted({round(i * step) for i in range(max_points)})
    return [points[i] for i in indices]
