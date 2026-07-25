import csv
import math
import os
import unicodedata
from collections import defaultdict
from functools import lru_cache

from app.external_data import enrich_indicator_metadata
from app.indicator_notes import build_indicator_explain, display_unit
from app.taxonomy import MACRO_AREA_ORDER, category_metadata


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

# ISTAT's standard geographic partition (ripartizione geografica), Nord
# collapsing Nord-ovest/Nord-est: used only for the region page's eyebrow, not
# for any scoring or filtering.
REGION_GEO_AREA = {
    "piemonte": "Nord",
    "valle-d-aosta": "Nord",
    "lombardia": "Nord",
    "trentino-alto-adige": "Nord",
    "veneto": "Nord",
    "friuli-venezia-giulia": "Nord",
    "liguria": "Nord",
    "emilia-romagna": "Nord",
    "toscana": "Centro",
    "umbria": "Centro",
    "marche": "Centro",
    "lazio": "Centro",
    "abruzzo": "Sud",
    "molise": "Sud",
    "campania": "Sud",
    "puglia": "Sud",
    "basilicata": "Sud",
    "calabria": "Sud",
    "sicilia": "Isole",
    "sardegna": "Isole",
}


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
SOURCE_EUSILC = {
    "label": "Istat, Reddito e condizioni di vita (Eu-Silc)",
    "url": "https://www.istat.it/statistiche-per-temi/reddito-e-condizioni-di-vita/",
}
CONTI_TERRITORIALI_IDS = {"901", "902", "903", "904", "905", "906", "907"}
DEMOGRAFICI_IDS = {"910", "911", "912", "913", "920", "921", "922", "923"}
EUSILC_IDS = {"930"}


def source_for(indicator_id):
    """Authoritative Istat source link for an indicator (label + url)."""
    iid = str(indicator_id)
    if iid in CONTI_TERRITORIALI_IDS:
        return SOURCE_CONTI_TERRITORIALI
    if iid in DEMOGRAFICI_IDS:
        return SOURCE_DEMOGRAFICI
    if iid in EUSILC_IDS:
        return SOURCE_EUSILC
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


class _Row:
    """Riga del dataset regionale (~110k istanze tenute in cache per un'ora).

    __slots__ invece di dict: niente hash table per istanza, solo un blocco
    fisso di puntatori. get_rows()/get_catalog() e affini leggono via
    row["campo"] o row.get("campo"), quindi replichiamo quell'interfaccia
    invece di propagare l'accesso ad attributo in tutto il codebase.
    """

    __slots__ = (
        "id",
        "territory",
        "region_key",
        "theme",
        "indicator",
        "unit",
        "source",
        "archive",
        "year",
        "value",
    )

    def __init__(self, id, territory, region_key, theme, indicator, unit, source, archive, year, value):
        self.id = id
        self.territory = territory
        self.region_key = region_key
        self.theme = theme
        self.indicator = indicator
        self.unit = unit
        self.source = source
        self.archive = archive
        self.year = year
        self.value = value

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


@lru_cache(maxsize=1)
def get_rows():
    # Colonne come territorio/tema/indicatore/fonte/archivio si ripetono su
    # ~110k righe ma hanno poche decine/centinaia di valori distinti: senza
    # dedup, ogni riga porta la sua copia della stringa. Un cache locale di
    # interning le fa condividere lo stesso oggetto tra tutte le righe.
    interned = {}

    def _dedup(value):
        return interned.setdefault(value, value)

    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = []
        for row in reader:
            rows.append(
                _Row(
                    id=_dedup(row["idIndicatore"]),
                    territory=_dedup(row["Territorio"]),
                    region_key=_dedup(_slugify(row["Territorio"])),
                    theme=_dedup(_clean_text(row["Tema"])),
                    indicator=_dedup(_clean_text(row["Indicatore"])),
                    unit=_dedup(display_unit(_clean_text(row["UDM"]))),
                    source=_dedup(_clean_text(row["Fonte"])),
                    archive=_dedup(_clean_text(row["Archivio"])),
                    year=int(row["Anno"]),
                    value=_parse_number(row["Dato"]),
                )
            )
    return rows


@lru_cache(maxsize=1)
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
            enrich_indicator_metadata({
                "id": indicator_id,
                # Populate the canonical public category (theme/macro_area) right at
                # the source, keeping the verbatim Istat sub-theme as source_theme.
                # Every consumer of get_catalog() then sees the same taxonomy without
                # having to remember to call category_metadata() itself (a couple of
                # call sites used to skip it and leak the raw sub-theme to users).
                **category_metadata(first["theme"]),
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
            })
        )

    indicators.sort(key=lambda item: (item["theme"], item["name"]))
    theme_items = [
        {"name": name, "macro_area": category_metadata(name)["macro_area"], **payload}
        for name, payload in sorted(themes.items(), key=lambda item: item[0].lower())
    ]

    # Macro-area rollup: a coarse, non-destructive grouping over the Istat themes,
    # following MACRO_AREA_ORDER and keeping any unmapped theme under "Altro".
    macro = defaultdict(lambda: {"themes": [], "indicator_count": 0})
    for theme in theme_items:
        bucket = macro[theme["macro_area"]]
        bucket["themes"].append(theme["name"])
        bucket["indicator_count"] += theme["indicator_count"]
    ordered_areas = [a for a in MACRO_AREA_ORDER if a in macro] + [
        a for a in macro if a not in MACRO_AREA_ORDER
    ]
    macro_areas = [
        {
            "name": name,
            "themes": macro[name]["themes"],
            "indicator_count": macro[name]["indicator_count"],
        }
        for name in ordered_areas
    ]

    return {
        "featured_indicator_id": featured_id,
        "regions": REGION_ORDER,
        "themes": theme_items,
        "macro_areas": macro_areas,
        "indicators": indicators,
    }


@lru_cache(maxsize=1)
def _rows_by_indicator():
    """Indice righe-per-indicatore costruito UNA volta (memoizzato) invece di
    filtrare tutte le ~110k righe a ogni chiamata di get_indicator(). lru_cache
    invece di cache.memoize: quest'ultimo passa da Flask-Caching, che ripickla
    l'intero indice a ogni lettura anche in-process (SimpleCache serializza
    sempre) — con ~120 indicatori letti in sequenza (es. pool del quiz) il
    solo unpickling costava diversi secondi. lru_cache tiene l'oggetto vero in
    memoria per la vita del processo, che qui coincide con un container: i
    dati sono statici per deploy, quindi non serve un timeout."""
    index = defaultdict(list)
    for row in get_rows():
        index[row["id"]].append(row)
    return dict(index)


@lru_cache(maxsize=None)
def get_indicator(indicator_id):
    rows = _rows_by_indicator().get(indicator_id, [])
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

    national_avg = _national_average(rows, years)
    spark = [
        {"year": point["year"], "value": round(point["value"], 3)}
        for point in _downsample(national_avg, 24)
    ]

    metadata = enrich_indicator_metadata({
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
        "spark": spark,
    })

    return {
        "metadata": metadata,
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


def indicator_year_average(series, year):
    """Mean value across regions for one year of an indicator's full series, or
    None if there is no non-null value for that year."""
    values = [row["value"] for row in series if row["year"] == year and row["value"] is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _gap_abs_for_year(series, year):
    """Magnitude of the spread (max - min) across regions for one year, or None
    if fewer than two regions have a value that year."""
    year_values = [row["value"] for row in series if row["year"] == year and row["value"] is not None]
    if len(year_values) < 2:
        return None
    return max(year_values) - min(year_values)


def _biggest_movers(series, year_min, year_max):
    """The region with the highest signed delta and the one with the lowest signed
    delta in raw value between year_min and year_max, among regions with a value in
    both years. Each result carries its own "kind" (aumento/calo/stabile) derived
    from the actual sign of its delta - the two extremes are not guaranteed to be
    an increase and a decrease (e.g. an indicator rising everywhere has two
    increases, just of different sizes), so callers must render the label from
    "kind", never assume highest=increase/lowest=decrease.

    Purely descriptive (no judgement on whether the movement is favorable - the
    page already carries that framing elsewhere via the indicator's direction).
    Returns (highest_delta, lowest_delta), each a {"region", "region_key", "delta",
    "kind"} dict, or (None, None) if there is no region present in both years."""
    by_region_min = {row["region"]: row for row in series if row["year"] == year_min and row["value"] is not None}
    by_region_max = {row["region"]: row for row in series if row["year"] == year_max and row["value"] is not None}
    common = sorted(set(by_region_min) & set(by_region_max))
    # With a single common region the two extremes would both resolve to the same
    # region, which reads as a contradiction on the page.
    if len(common) < 2:
        return None, None

    def _kind(delta):
        if delta > 0:
            return "aumento"
        if delta < 0:
            return "calo"
        return "stabile"

    deltas = [
        {
            "region": region,
            "region_key": by_region_max[region]["region_key"],
            "delta": by_region_max[region]["value"] - by_region_min[region]["value"],
        }
        for region in common
    ]
    deltas.sort(key=lambda item: item["delta"])
    highest, lowest = deltas[-1], deltas[0]
    highest["kind"] = _kind(highest["delta"])
    lowest["kind"] = _kind(lowest["delta"])
    return highest, lowest


def indicator_year_over_year_stats(payload, year=None):
    """Compare the latest selected year with the previous available year.

    The comparison uses only territories that have a value in both years. This
    keeps the two simple territorial averages on the same base when coverage
    changes between releases. The result is descriptive and never assigns a
    positive or negative meaning to the movement. That interpretation belongs
    to the indicator direction handled by ``indicator_notes``.
    """
    meta = payload["metadata"]
    current_year = year if year is not None else meta["year_max"]
    available_years = sorted({
        row["year"]
        for row in payload["series"]
        if row["value"] is not None and row["year"] <= current_year
    })
    previous_years = [candidate for candidate in available_years if candidate < current_year]
    if not previous_years:
        return None

    previous_year = previous_years[-1]
    def territory_name(row):
        return row.get("region") or row.get("territory")

    def territory_key(row):
        return row.get("region_key") or row.get("territory_key")

    current = {
        territory_name(row): row
        for row in payload["series"]
        if row["year"] == current_year and row["value"] is not None and territory_name(row)
    }
    previous = {
        territory_name(row): row
        for row in payload["series"]
        if row["year"] == previous_year and row["value"] is not None and territory_name(row)
    }
    common = sorted(set(current) & set(previous))
    if not common:
        return None

    changes = []
    for region in common:
        delta = current[region]["value"] - previous[region]["value"]
        if math.isclose(delta, 0.0, abs_tol=1e-12):
            delta = 0.0
            kind = "stabile"
        else:
            kind = "aumento" if delta > 0 else "calo"
        changes.append({
            "region": region,
            "region_key": territory_key(current[region]),
            "previous_value": previous[region]["value"],
            "current_value": current[region]["value"],
            "delta": delta,
            "kind": kind,
        })

    previous_avg = sum(previous[region]["value"] for region in common) / len(common)
    current_avg = sum(current[region]["value"] for region in common) / len(common)
    average_delta = current_avg - previous_avg
    average_delta_pct = (
        average_delta / abs(previous_avg) * 100
        if previous_avg and not math.isclose(previous_avg, 0.0, abs_tol=1e-12)
        else None
    )
    increases = sorted(
        (change for change in changes if change["delta"] > 0),
        key=lambda change: change["delta"],
        reverse=True,
    )
    decreases = sorted(
        (change for change in changes if change["delta"] < 0),
        key=lambda change: change["delta"],
    )

    return {
        "year": current_year,
        "previous_year": previous_year,
        "year_gap": current_year - previous_year,
        "common_count": len(common),
        "current_count": len(current),
        "previous_count": len(previous),
        "same_coverage": len(common) == len(current) == len(previous),
        "previous_avg": previous_avg,
        "current_avg": current_avg,
        "average_delta": average_delta,
        "average_delta_pct": average_delta_pct,
        "increase_count": len(increases),
        "decrease_count": len(decreases),
        "stable_count": sum(change["delta"] == 0 for change in changes),
        "largest_increases": increases[:3],
        "largest_decreases": decreases[:3],
    }


def indicator_trend_stats(payload, year, values, best=None, worst=None):
    """Pure numeric aggregates for the indicator page: regional mean and median
    for the current year, regional mean for year_min (for the long-term trend),
    the best/worst gap, the regions that moved the most, and whether the
    regional gap widened or narrowed over time. `values` is the year-filtered rows
    already in scope in the view (get_indicator_year()["values"]). `best`/`worst`
    are the same two rows the view already picked, or None for contextual
    (non-scoreable) indicators.

    Every derived field is None when it cannot be computed honestly from the data -
    callers must treat None as "omit this claim", never substitute or approximate.
    """
    meta = payload["metadata"]
    year_min, year_max = meta["year_min"], meta["year_max"]
    has_multi_year = year_min != year_max

    year_values = [v["value"] for v in values]
    year_avg = (sum(year_values) / len(year_values)) if year_values else None
    year_count = len(year_values)

    # With only a handful of regions reporting, a median, an "above/below the
    # mean" split or a mean-vs-median spread are statistical theatre: they read as
    # precise but describe two or three numbers. Below the threshold we keep the
    # mean and the min-max gap (honest even at N=2) and drop the rest - the "None
    # means omit" contract then suppresses those claims in both templates.
    SMALL_N = 5
    median = None
    above_avg_count = below_avg_count = None
    if year_values and year_count >= SMALL_N:
        sorted_values = sorted(year_values)
        mid = len(sorted_values) // 2
        median = sorted_values[mid] if len(sorted_values) % 2 else (sorted_values[mid - 1] + sorted_values[mid]) / 2
        if year_avg is not None:
            above_avg_count = sum(1 for v in year_values if v > year_avg)
            below_avg_count = sum(1 for v in year_values if v < year_avg)

    year_min_avg = year_avg if not has_multi_year else indicator_year_average(payload["series"], year_min)

    avg_change_abs = avg_change_pct = None
    if has_multi_year and year_avg is not None and year_min_avg is not None:
        avg_change_abs = year_avg - year_min_avg
        if year_min_avg:
            avg_change_pct = avg_change_abs / year_min_avg * 100

    gap_abs = gap_ratio = None
    if best is not None and worst is not None and best["value"] is not None and worst["value"] is not None:
        # best/worst are picked by direction upstream (views.py), so best can hold
        # either the higher or the lower value depending on the indicator's
        # direction - always report the magnitude of the gap, never a signed diff.
        high_value = max(best["value"], worst["value"])
        low_value = min(best["value"], worst["value"])
        gap_abs = high_value - low_value
        name_lower = meta["name"].lower()
        unit_lower = (meta.get("unit") or "").lower()
        ratio_meaningless = "differenza" in name_lower or "punti percentuali" in unit_lower
        if not ratio_meaningless and low_value > 0:
            ratio = high_value / low_value
            # A "X volte" ratio only reads as informative when the two values are
            # genuinely far apart. When they are close (e.g. life expectancy, 84 vs
            # 81) the ratio rounds to "1,0 volte", which contradicts a non-zero gap
            # and reads as broken; below the threshold the absolute gap says it all.
            if ratio >= 1.2:
                gap_ratio = ratio

    region_highest_delta = region_lowest_delta = None
    year_min_gap_abs = gap_trend = None
    if has_multi_year:
        region_highest_delta, region_lowest_delta = _biggest_movers(payload["series"], year_min, year_max)
        year_min_gap_abs = _gap_abs_for_year(payload["series"], year_min)
        if year_min_gap_abs is not None and gap_abs is not None:
            gap_trend = gap_abs - year_min_gap_abs

    return {
        "year": year,
        "year_avg": year_avg,
        "year_count": year_count,
        "median": median,
        "above_avg_count": above_avg_count,
        "below_avg_count": below_avg_count,
        "year_min": year_min,
        "year_min_avg": year_min_avg,
        "year_max": year_max,
        "has_multi_year": has_multi_year,
        "avg_change_abs": avg_change_abs,
        "avg_change_pct": avg_change_pct,
        "gap_abs": gap_abs,
        "gap_ratio": gap_ratio,
        "region_highest_delta": region_highest_delta,
        "region_lowest_delta": region_lowest_delta,
        "year_min_gap_abs": year_min_gap_abs,
        "gap_trend": gap_trend,
    }


def search_indicators(query="", theme=None, limit=50):
    query = _normalize_search(query)
    theme = _clean_text(theme)
    results = []

    for item in get_catalog()["indicators"]:
        if theme and item["theme"] != theme:
            continue
        explain = item.get("explain") or {}
        haystack = _normalize_search(
            f"{item['name']} {item['theme']} {item['archive']} "
            f"{explain.get('plain', '')} {explain.get('example', '')}"
        )
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
