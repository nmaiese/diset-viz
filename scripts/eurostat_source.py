#!/usr/bin/env python3
"""Eurostat regional (NUTS2) source adapter: the pilot second institution.

Pure stdlib. Cache-first with an offline fixture path so the discovery step is
repeatable and testable without network. The adapter only *reads* Eurostat and
maps NUTS2 series onto the 20 Italian regions; it never writes live data.

Design choices that mirror the rest of the pipeline:
- One Eurostat dataset = one curated series (no code heuristics), exactly like
  scripts/multiscopo_sources.py.
- Bolzano and Trento (ITH1, ITH2) are combined into a single Trentino Alto Adige
  region by a population-weighted mean (for ratios like per-capita GDP a plain
  mean would be a synthetic value), keeping the 20-region standard.
- "Freshest honest year": we pick the most recent year that clears a coverage
  threshold, not the absolute latest (Eurostat's newest year is often sparse).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "data" / "discovery" / "fixtures" / "eurostat"
CACHE_DIR = PROJECT_ROOT / "data" / "eurostat_cache"

API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
LANDING = "https://ec.europa.eu/eurostat/web/regions/data/database"
LICENSE = "CC BY 4.0 (Eurostat)"

# NUTS2 -> region_key (matching app.data / app.profiles.region_key_for slugs).
# Bolzano (ITH1) and Trento (ITH2) both map to Trentino Alto Adige and are
# combined by a population-weighted mean (see parse_regional / SPLIT_NUTS).
NUTS2_TO_REGION = {
    "ITC1": "piemonte", "ITC2": "valle-d-aosta", "ITC3": "liguria", "ITC4": "lombardia",
    "ITH1": "trentino-alto-adige", "ITH2": "trentino-alto-adige", "ITH3": "veneto",
    "ITH4": "friuli-venezia-giulia", "ITH5": "emilia-romagna",
    "ITI1": "toscana", "ITI2": "umbria", "ITI3": "marche", "ITI4": "lazio",
    "ITF1": "abruzzo", "ITF2": "molise", "ITF3": "campania", "ITF4": "puglia",
    "ITF5": "basilicata", "ITF6": "calabria", "ITG1": "sicilia", "ITG2": "sardegna",
}

REGION_NAMES = {
    "piemonte": "Piemonte", "valle-d-aosta": "Valle d'Aosta", "liguria": "Liguria",
    "lombardia": "Lombardia", "trentino-alto-adige": "Trentino Alto Adige",
    "veneto": "Veneto", "friuli-venezia-giulia": "Friuli-Venezia Giulia",
    "emilia-romagna": "Emilia-Romagna", "toscana": "Toscana", "umbria": "Umbria",
    "marche": "Marche", "lazio": "Lazio", "abruzzo": "Abruzzo", "molise": "Molise",
    "campania": "Campania", "puglia": "Puglia", "basilicata": "Basilicata",
    "calabria": "Calabria", "sicilia": "Sicilia", "sardegna": "Sardegna",
}
REGION_COUNT = 20
MIN_COVERAGE = 0.8

# NUTS2 codes that share a single region (Bolzano + Trento -> Trentino Alto
# Adige). Combining them for a ratio (per-capita, share of GDP) needs weights,
# not an unweighted mean; we weight by average annual population (the same
# denominator Eurostat uses for regional GDP).
SPLIT_NUTS = tuple(
    nuts for nuts in NUTS2_TO_REGION
    if sum(1 for other in NUTS2_TO_REGION.values() if other == NUTS2_TO_REGION[nuts]) > 1
)
WEIGHT_DATASET = "nama_10r_3popgdp"
WEIGHT_PARAMS = {"unit": "THS"}

# Curated pilot series, keyed by Eurostat dataset id. Each is a single,
# well-defined NUTS2 series (no code heuristics).
EUROSTAT_SERIES = {
    "nama_10r_2gdp": {
        "dataset": "nama_10r_2gdp",
        "params": {"unit": "EUR_HAB"},
        "name": "PIL pro capite ai prezzi di mercato (Eurostat, NUTS2)",
        "unit": "euro per abitante",
        "decimals": 0,
        "proposed_theme": "Conti economici regionali (Eurostat)",
        "proposed_quality_life_category": "reddito_accessibilita",
        "proposed_direction": "higher_better",
        # Per-capita ratio: Bolzano+Trento combined by population weight, not a
        # plain mean (which would be synthetic).
        "combine_split": "weighted",
    },
    "rd_e_gerdreg": {
        "dataset": "rd_e_gerdreg",
        "params": {"unit": "PC_GDP", "sectperf": "TOTAL"},
        "name": "Spesa in ricerca e sviluppo sul PIL (Eurostat, NUTS2)",
        "unit": "% del PIL",
        "decimals": 2,
        "proposed_theme": "Ricerca e sviluppo (Eurostat)",
        "proposed_quality_life_category": "ricerca_innovazione_digitale",
        "proposed_direction": "higher_better",
        # Intensity ratio (share of GDP): population-weighted combination of the
        # two provinces (a close, defensible proxy for GDP weighting given their
        # near-equal size), not a plain mean.
        "combine_split": "weighted",
    },
}


def _build_url(dataset, params):
    query = ["format=JSON", "lang=EN", "geoLevel=nuts2", "sinceTimePeriod=2019"]
    for key in sorted(params):
        query.append(f"{key}={params[key]}")
    return f"{API_BASE}/{dataset}?" + "&".join(query)


def fetch_dataset(series_id, offline=True, refresh=False):
    """Return the raw JSON-stat document for a curated series.

    offline: read the committed fixture (default, used by tests and repeatable
    runs). Live mode is cache-first: a cached response is reused, otherwise the
    Eurostat API is queried once and the response is cached under
    data/eurostat_cache/ (gitignored)."""
    series = EUROSTAT_SERIES[series_id]
    dataset = series["dataset"]
    if offline:
        return json.loads((FIXTURE_DIR / f"{dataset}.json").read_text(encoding="utf-8"))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{dataset}.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    url = _build_url(dataset, series["params"])
    request = urllib.request.Request(url, headers={"User-Agent": "divarioitalia-discovery/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (institutional host)
        payload = response.read().decode("utf-8")
    cache_path.write_text(payload, encoding="utf-8")
    return json.loads(payload)


def _nuts_year_values(doc):
    """{nuts: {year: value}} straight from a JSON-stat doc, general over the
    number of pinned (size-1) dimensions (only geo and time vary here)."""
    dims = doc["id"]
    sizes = doc["size"]
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    geo_index = doc["dimension"]["geo"]["category"]["index"]
    time_index = doc["dimension"]["time"]["category"]["index"]
    values = doc["value"]

    def flat(geo_idx, time_idx):
        pos = 0
        for i, dim in enumerate(dims):
            idx = geo_idx if dim == "geo" else (time_idx if dim == "time" else 0)
            pos += idx * strides[i]
        return pos

    out = {}
    for nuts, geo_idx in geo_index.items():
        for year, time_idx in time_index.items():
            value = values.get(str(flat(geo_idx, time_idx)))
            if value is not None:
                out.setdefault(nuts, {})[year] = float(value)
    return out


def parse_regional(doc, combine_split="weighted", weights=None):
    """JSON-stat -> {region_key: {year: value}} over the 20 Italian regions.

    When more than one NUTS2 maps to the same region (Bolzano + Trento ->
    Trentino Alto Adige), `combine_split` decides how to combine them:
    - ``weighted``: population-weighted mean (correct for per-capita and share
      ratios; keeps the region at its true value). Needs `weights`
      ({nuts: {year: pop}}); if a weight is missing the region-year is dropped
      rather than silently averaged.
    - ``mean`` / ``sum``: unweighted mean or sum, for genuinely averageable or
      additive metrics.
    - ``drop``: leave the split region-year missing.
    A region with a single NUTS2 is always taken as-is."""
    by_nuts = _nuts_year_values(doc)
    raw = {}  # region_key -> year -> [(nuts, value)]
    for nuts, region_key in NUTS2_TO_REGION.items():
        for year, value in by_nuts.get(nuts, {}).items():
            raw.setdefault(region_key, {}).setdefault(year, []).append((nuts, value))

    def _combine(pairs, year):
        if len(pairs) == 1:
            return pairs[0][1]
        if combine_split == "mean":
            return sum(v for _, v in pairs) / len(pairs)
        if combine_split == "sum":
            return sum(v for _, v in pairs)
        if combine_split == "weighted" and weights:
            wv = [(v, (weights.get(n) or {}).get(year)) for n, v in pairs]
            total = sum(w for _, w in wv if w is not None)
            if all(w is not None for _, w in wv) and total > 0:
                return sum(v * w for v, w in wv) / total
        return None  # cannot combine honestly -> leave missing

    result = {}
    for region_key, years in raw.items():
        combined = {
            year: value
            for year, pairs in years.items()
            if (value := _combine(pairs, year)) is not None
        }
        if combined:
            result[region_key] = combined
    return result


def fetch_weights(offline=True, refresh=False):
    """Population weights ({nuts: {year: pop}}) for the split NUTS2 regions,
    from Eurostat's average-annual-population series. Cache-first with a
    committed fixture, like the data series."""
    if offline:
        doc = json.loads((FIXTURE_DIR / f"{WEIGHT_DATASET}.json").read_text(encoding="utf-8"))
    else:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = CACHE_DIR / f"{WEIGHT_DATASET}.json"
        if cache_path.exists() and not refresh:
            doc = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            url = _build_url(WEIGHT_DATASET, WEIGHT_PARAMS)
            request = urllib.request.Request(url, headers={"User-Agent": "divarioitalia-discovery/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                payload = response.read().decode("utf-8")
            cache_path.write_text(payload, encoding="utf-8")
            doc = json.loads(payload)
    by_nuts = _nuts_year_values(doc)
    return {nuts: by_nuts.get(nuts, {}) for nuts in SPLIT_NUTS}


def best_recent_year(regional, min_coverage=MIN_COVERAGE):
    """(year, coverage, {region_key: value}) for the most recent year that clears
    the coverage threshold; falls back to the best-covered year otherwise."""
    years = sorted({year for values in regional.values() for year in values}, reverse=True)
    fallback = None
    for year in years:
        present = {rk: vals[year] for rk, vals in regional.items() if year in vals}
        coverage = round(len(present) / REGION_COUNT, 4)
        if fallback is None or coverage > fallback[1]:
            fallback = (year, coverage, present)
        if coverage >= min_coverage:
            return year, coverage, present
    return fallback if fallback else (None, 0.0, {})


def discover(series_id, offline=True, refresh=False):
    """Raw candidate for one curated series: data fields only. definition_match,
    duplicate_of and priority_score are added by discover_candidates.py, which
    holds the existing-indicator index and the scoring policy."""
    series = EUROSTAT_SERIES[series_id]
    doc = fetch_dataset(series_id, offline=offline, refresh=refresh)
    combine = series.get("combine_split", "weighted")
    weights = fetch_weights(offline=offline, refresh=refresh) if combine == "weighted" else None
    regional = parse_regional(doc, combine, weights)
    year, coverage, _ = best_recent_year(regional)
    return {
        "source": "eurostat_regional",
        "source_dataset": series["dataset"],
        "source_indicator_id": series_id,
        "name": series["name"],
        "territory_level": "regione",
        "year_max": str(year) if year is not None else "",
        "coverage": coverage,
        "unit": series["unit"],
        "proposed_theme": series["proposed_theme"],
        "proposed_quality_life_category": series["proposed_quality_life_category"],
        "proposed_direction": series["proposed_direction"],
        "source_url": _dataset_url(series["dataset"]),
        "license": LICENSE,
        "updated": doc.get("updated", ""),
    }


def normalized_rows(series_id, offline=True, refresh=False):
    """External-layer rows (regione level) for the promotion step, for the single
    best-recent year. Values use the Italian decimal comma, like the other CSVs."""
    series = EUROSTAT_SERIES[series_id]
    doc = fetch_dataset(series_id, offline=offline, refresh=refresh)
    combine = series.get("combine_split", "weighted")
    weights = fetch_weights(offline=offline, refresh=refresh) if combine == "weighted" else None
    regional = parse_regional(doc, combine, weights)
    year, coverage, present = best_recent_year(regional)
    rows = []
    for region_key in sorted(present):
        rows.append({
            "region_key": region_key,
            "region_name": REGION_NAMES.get(region_key, region_key),
            "year": year,
            "value": _format_value(present[region_key], series["decimals"]),
            "coverage": coverage,
        })
    return rows


def _format_value(value, decimals):
    text = f"{value:.{decimals}f}" if decimals else f"{round(value)}"
    return text.replace(".", ",")


def _dataset_url(dataset):
    return f"https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table?lang=en"
