#!/usr/bin/env python3
"""Istat SDMX regional source adapter (demographic indicators, NUTS2).

Second Istat family wired into the hunter, after the Eurostat pilot. Pure stdlib
on top of scripts.istat_sdmx (the rate-limited, cache-first SDMX client), and
shaped exactly like scripts/eurostat_source.py so scripts/discover_candidates.py
can consume it without any special case.

Design choices that mirror the rest of the pipeline:
- One curated dataflow + DATA_TYPE code = one candidate series (no code
  heuristics), like scripts/multiscopo_sources.py. The pilot dataflow is
  DCIS_INDDEMOG1 (Indicatori demografici), whose DATA_TYPE dimension selects the
  single indicator.
- Every series name is confirmed `new` against the existing catalogue (via
  discovery.classify_definition_match) before it is listed here, so the adapter
  proposes genuinely additive indicators, not duplicates of the backbone/BES.
- Bolzano (ITD1) and Trento (ITD2) are combined into one Trentino Alto Adige
  region by a population-weighted mean, reusing the Multiscopo weights so every
  Istat family combines the split the same way (a plain mean of a ratio would be
  a synthetic value), keeping the 20-region standard.
- Offline fixture path (committed SDMX-CSV under data/discovery/fixtures/istat/)
  so discovery is repeatable and testable without touching the network or the
  Istat 5-queries/minute limit. The raw client cache (data/istat_cache) stays
  gitignored.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from scripts import istat_sdmx, multiscopo_sources

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "data" / "discovery" / "fixtures" / "istat"
CACHE_DIR = PROJECT_ROOT / "data" / "istat_cache"
CODELIST_PATH = PROJECT_ROOT / "data" / "provincia" / "codelist_CL_ITTER107.csv"

DATAFLOW = "22_293_DF_DCIS_INDDEMOG1_1"
DSD_LABEL = "DCIS_INDDEMOG1"
SOURCE = "istat_demografia"
SOURCE_URL = "https://esploradati.istat.it/databrowser/#/it"
LICENSE = "CC BY 3.0 IT (Istat)"
START_YEAR = 2015

# Region-level REF_AREA codes look like ITC1, ITD1, ITF3 (two letters + digit).
# Macro-areas (ITC, ITD, ...) and the national code (IT) do not match, so they
# are dropped from the regional view.
REGION_CODE_RE = re.compile(r"^IT[A-Z]\d$")
REGION_COUNT = 20
MIN_COVERAGE = 0.8

# Bolzano (ITD1) + Trento (ITD2) -> Trentino Alto Adige. Reuse the Multiscopo
# population weights so the split is combined identically across Istat families.
TRENTINO_PARTS = multiscopo_sources.TRENTINO_PARTS
TRENTINO_WEIGHTS = multiscopo_sources.TRENTINO_WEIGHTS
TRENTINO_NAME = "Trentino Alto Adige"

# Curated series: one DATA_TYPE code within DCIS_INDDEMOG1 = one candidate.
# `direction` is left `contextual` on purpose: an ageing/dependency ratio is not
# unambiguously good or bad, so the human curator decides the verso and score
# eligibility later. The hunter only records the proposal.
ISTAT_SERIES = {
    "OLDAGEDEPR": {
        "data_type": "OLDAGEDEPR",
        "name": "Indice di dipendenza strutturale degli anziani (Istat, regioni)",
        "unit": "%",
        "decimals": 1,
        "proposed_theme": "Indicatori demografici (Istat)",
        "proposed_quality_life_category": "salute_cura",
        "proposed_direction": "contextual",
    },
    "DEPENDRATE": {
        "data_type": "DEPENDRATE",
        "name": "Indice di dipendenza strutturale (Istat, regioni)",
        "unit": "%",
        "decimals": 1,
        "proposed_theme": "Indicatori demografici (Istat)",
        "proposed_quality_life_category": "salute_cura",
        "proposed_direction": "contextual",
    },
}


def _load_region_names():
    """{REF_AREA code: region name} from the committed ITTER107 codelist."""
    names = {}
    with CODELIST_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            names[row["code"]] = row["name"].split("/", 1)[0].strip()
    return names


def _fixture_path(series_id):
    return FIXTURE_DIR / f"{DSD_LABEL}__{series_id}.csv"


def _data_path(series_id):
    code = ISTAT_SERIES[series_id]["data_type"]
    # FREQ.REF_AREA.DATA_TYPE : annual, all territories, one indicator.
    return f"data/{DATAFLOW}/A..{code}?startPeriod={START_YEAR}"


def fetch_rows(series_id, offline=True, refresh=False, client=None):
    """Raw SDMX-CSV rows (list of dicts) for one series.

    offline reads the committed fixture (default, used by tests and repeatable
    runs). Live mode goes through the rate-limited SDMX client, which caches the
    response under data/istat_cache (gitignored)."""
    if offline:
        text = _fixture_path(series_id).read_text(encoding="utf-8")
        return istat_sdmx.parse_sdmx_csv(text)
    if client is None:
        client = istat_sdmx.SdmxClient(cache_dir=CACHE_DIR, refresh_data=refresh)
    body = client.get(
        _data_path(series_id), istat_sdmx.ACCEPT_CSV,
        max_age=client.data_max_age, force=refresh,
    )
    return istat_sdmx.parse_sdmx_csv(body)


def parse_regional(rows, data_type):
    """{region_name: {year: value}} for the 20 regions, Bolzano+Trento combined
    by population weight. Keeps only the requested DATA_TYPE and region-level
    REF_AREA codes."""
    names = _load_region_names()
    by_region = {}
    trentino = {}  # year -> {part_code: value}
    for row in rows:
        if row.get("DATA_TYPE") != data_type:
            continue
        area = row.get("REF_AREA")
        year = row.get("TIME_PERIOD")
        raw = row.get("OBS_VALUE")
        if not area or not year or raw in (None, ""):
            continue
        value = float(raw)
        if area in TRENTINO_PARTS:
            trentino.setdefault(year, {})[area] = value
            continue
        if not REGION_CODE_RE.match(area):
            continue
        by_region.setdefault(names.get(area, area), {})[year] = value
    for year, parts in trentino.items():
        if all(p in TRENTINO_WEIGHTS for p in parts):
            total = sum(TRENTINO_WEIGHTS[p] for p in parts)
            if total > 0:
                weighted = sum(parts[p] * TRENTINO_WEIGHTS[p] for p in parts) / total
                by_region.setdefault(TRENTINO_NAME, {})[year] = weighted
    return by_region


def best_recent_year(by_region, min_coverage=MIN_COVERAGE):
    """Most recent year clearing the coverage threshold (the absolute latest is
    often sparse). Returns (year:int, coverage:float, present:{region: value})."""
    years = sorted({int(y) for v in by_region.values() for y in v}, reverse=True)
    fallback = None
    for year in years:
        key = str(year)
        present = {r: v[key] for r, v in by_region.items() if key in v}
        coverage = round(len(present) / REGION_COUNT, 4)
        if fallback is None:
            fallback = (year, coverage, present)
        if coverage >= min_coverage:
            return year, coverage, present
    return fallback if fallback else (None, 0.0, {})


def discover(series_id, offline=True, refresh=False, client=None):
    """Raw candidate for one curated series: data fields only. definition_match,
    duplicate_of and priority_score are added by discover_candidates.py."""
    spec = ISTAT_SERIES[series_id]
    rows = fetch_rows(series_id, offline=offline, refresh=refresh, client=client)
    regional = parse_regional(rows, spec["data_type"])
    year, coverage, _ = best_recent_year(regional)
    return {
        "source": SOURCE,
        "source_dataset": DATAFLOW,
        "source_indicator_id": series_id,
        "name": spec["name"],
        "territory_level": "regione",
        "year_max": str(year) if year is not None else "",
        "coverage": coverage,
        "unit": spec["unit"],
        "proposed_theme": spec["proposed_theme"],
        "proposed_quality_life_category": spec["proposed_quality_life_category"],
        "proposed_direction": spec["proposed_direction"],
        "source_url": SOURCE_URL,
        "license": LICENSE,
        "updated": "",
    }


def _format_value(value, decimals):
    text = f"{value:.{decimals}f}" if decimals else f"{round(value)}"
    return text.replace(".", ",")


def normalized_rows(series_id, offline=True, refresh=False, client=None):
    """External-layer rows (regione level) for the promotion step: the full
    historical series, one row per region per year that clears the coverage
    threshold. Values use the Italian decimal comma, like the other CSVs."""
    spec = ISTAT_SERIES[series_id]
    rows = fetch_rows(series_id, offline=offline, refresh=refresh, client=client)
    regional = parse_regional(rows, spec["data_type"])
    years = sorted({int(y) for v in regional.values() for y in v})
    out = []
    for year in years:
        key = str(year)
        present = {r: v[key] for r, v in regional.items() if key in v}
        coverage = round(len(present) / REGION_COUNT, 4)
        if coverage < MIN_COVERAGE:
            continue
        for region_name in sorted(present):
            out.append({
                "region_name": region_name,
                "year": key,
                "value": _format_value(present[region_name], spec["decimals"]),
                "coverage": coverage,
            })
    return out
