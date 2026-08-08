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
- The pilot dataflow has exactly three SDMX dimensions (FREQ, REF_AREA,
  DATA_TYPE), which is not the common case: most Istat dataflows also break
  down by sex, age band, household type, and so on. `_build_key` reads a
  series' `dimension_order` and `dimension_values` (see `load_series`) to
  build a key of any length instead of the pilot's fixed three slots, and
  refuses to build one for a dimension with no known value rather than
  wildcarding it, since an unfiltered SDMX dimension returns every code for
  it, not a total.
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

from scripts import discovery, external_sources, istat_sdmx, multiscopo_sources

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "data" / "discovery" / "fixtures" / "istat"
CACHE_DIR = PROJECT_ROOT / "data" / "istat_cache"
CODELIST_PATH = PROJECT_ROOT / "data" / "provincia" / "codelist_CL_ITTER107.csv"

DATAFLOW = "22_293_DF_DCIS_INDDEMOG1_1"
DSD_LABEL = "DCIS_INDDEMOG1"
SOURCE = "istat_demografia"
SOURCE_URL = "https://esploradati.istat.it/databrowser/#/it"
LICENSE = "CC BY 4.0 (Istat)"
START_YEAR = 2015

# Region-level REF_AREA codes look like ITC1, ITD1, ITF3 (two letters + digit).
# Macro-areas (ITC, ITD, ...) and the national code (IT) do not match, so they
# are dropped from the regional view.
REGION_CODE_RE = re.compile(r"^IT[A-Z]\d$")
REGION_COUNT = 20
MIN_COVERAGE = 0.8

# SDMX observation statuses that mean "not final yet". Istat flags the current
# year 'e' on the demographic indicators, because the 1 January population it is
# computed on is itself an estimate that will be revised.
#
# Nothing in the app read this field, so the 2026 estimates presented themselves
# as observations: they set year_max, won `freshness_status=current` and put the
# candidate at the top of the queue with priority_score 1.0, ahead of series with
# real published years. Worse downstream, the writer would have pinned a
# `vintage` to numbers Istat will change, and the drift guard only notices a NEW
# year, never a REVISED value, so the prose would have gone quietly wrong.
#
# Deliberately narrow. 'b' (break in series), 'd' (definition differs) and 'u'
# (low reliability) are final values with a caveat, and dropping them would
# throw away good observations.
NON_FINAL_STATUSES = frozenset({"e", "p", "f"})

# Bolzano (ITD1) + Trento (ITD2) -> Trentino Alto Adige. Reuse the Multiscopo
# population weights so the split is combined identically across Istat families.
TRENTINO_PARTS = multiscopo_sources.TRENTINO_PARTS
TRENTINO_WEIGHTS = multiscopo_sources.TRENTINO_WEIGHTS
TRENTINO_NAME = "Trentino Alto Adige"

SERIES_CONFIG = PROJECT_ROOT / "config" / "istat_series.yaml"


def _parse_dimension_values(raw):
    """'SESSO=9;ETA1=99' -> {'SESSO': '9', 'ETA1': '99'}.

    A flat scalar, not a nested mapping: `external_sources.load_flat_list`
    reads only one level of scalars under a list on purpose (the discovery
    chain is stdlib-pure, no PyYAML), so a dataflow with several extra
    dimensions still fits in one YAML row as a single string.

    A pair without '=' is dropped rather than raised here. Raising here would
    fail every series in the file at once, since this runs at import time
    through `ISTAT_SERIES = load_series()`; dropping it just leaves that
    dimension unresolved, so `_build_key` refuses *that one series* later,
    where `scripts/discover_candidates.py`'s per-series try/except isolates
    the failure the way a wrong `dataflow` or `dsd_label` already does.
    """
    values = {}
    if not raw:
        return values
    for pair in str(raw).split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        dim, code = pair.split("=", 1)
        dim = dim.strip()
        if dim:
            values[dim] = code.strip()
    return values


def load_series(path=None):
    """Curated series read from config, not from this file.

    One `dataflow` plus one `DATA_TYPE` code selects exactly one indicator, so a
    series is fully described by a row of scalars. That is the whole reason this
    moved out of Python: admitting an Istat series used to mean editing a module,
    which no agent is allowed to do, so the chain stalled the moment its wired
    sources ran out. Now the scout writes a row and the hunter picks it up.

    `direction` stays a *proposal* read from the name. It is the curator that
    checks it against the real ranking, and a dependency ratio has no better end
    at all, which is why both seeded series say `contextual`.

    Two more fields describe a dataflow with more than the pilot's three
    dimensions, and both are optional: a row that omits them gets the pilot's
    plain `FREQ.REF_AREA.DATA_TYPE` shape, so the seed series need neither.
    `indicator_dimension` names the dimension that carries this series' own
    code (`DATA_TYPE` unless the dataflow calls it something else).
    `dimension_order` is the dataflow's dimensions in their real SDMX position
    order, e.g. `[FREQ, REF_AREA, SESSO, ETA1, DATA_TYPE]`: a key is read
    positionally, so the order has to match the dataflow's own `datastructure`
    response, not just list the dimensions. `dimension_values` gives the code
    for every dimension besides `REF_AREA` and the indicator one, normally the
    dataflow's own 'total' code for that breakdown (`SESSO=9;ETA1=99`).
    """
    path = Path(path) if path else SERIES_CONFIG
    if not path.exists():
        return {}
    series = {}
    for entry in external_sources.load_flat_list(path, "series"):
        series_id = (entry.get("id") or "").strip()
        if not series_id:
            continue
        indicator_dimension = entry.get("indicator_dimension") or "DATA_TYPE"
        dimension_order = entry.get("dimension_order") or ["FREQ", "REF_AREA", indicator_dimension]
        series[series_id] = {
            "data_type": series_id,
            "dataflow": entry.get("dataflow", DATAFLOW),
            "dsd_label": entry.get("dsd_label", DSD_LABEL),
            "name": entry.get("name", series_id),
            "unit": entry.get("unit", ""),
            "decimals": entry.get("decimals", 1),
            "proposed_theme": entry.get("theme", ""),
            "proposed_quality_life_category": entry.get("quality_life_category", ""),
            "proposed_direction": entry.get("direction", "contextual"),
            "indicator_dimension": indicator_dimension,
            "dimension_order": list(dimension_order),
            "dimension_values": _parse_dimension_values(entry.get("dimension_values")),
        }
    return series


ISTAT_SERIES = load_series()


def _load_region_names():
    """{REF_AREA code: region name} from the committed ITTER107 codelist."""
    names = {}
    with CODELIST_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            names[row["code"]] = row["name"].split("/", 1)[0].strip()
    return names


def _fixture_path(series_id):
    spec = ISTAT_SERIES[series_id]
    return FIXTURE_DIR / f"{spec['dsd_label']}__{series_id}.csv"


def _build_key(spec):
    """Dot-separated SDMX key for `spec`, for any number of dimensions.

    SDMX reads a key positionally: segment N is dimension N of the DSD, so a
    key with the wrong shape either errors or is silently padded with
    wildcards. `REF_AREA` is always wildcarded (every region in one call);
    the indicator dimension takes this series' own code; every other
    dimension must resolve through `dimension_values` (`FREQ` alone falls
    back to `A`, annual, since every series here is annual and it would
    otherwise have to be repeated in every row). A dimension that resolves to
    nothing is refused here, not wildcarded: an unfiltered SDMX dimension
    does not average away into a total, it returns every code for that
    dimension (every sex, every age band, ...) mixed into rows that would
    otherwise look like one clean number per region.
    """
    parts = []
    for dim in spec["dimension_order"]:
        if dim == "REF_AREA":
            parts.append("")
        elif dim == spec["indicator_dimension"]:
            parts.append(spec["data_type"])
        elif dim in spec["dimension_values"]:
            parts.append(spec["dimension_values"][dim])
        elif dim == "FREQ":
            parts.append("A")
        else:
            raise ValueError(
                f"{spec['dsd_label']}/{spec['data_type']}: la dimensione '{dim}' "
                f"non ha un valore noto (non è REF_AREA, non è la dimensione "
                f"indicatore '{spec['indicator_dimension']}', non compare in "
                "dimension_values). Serve il codice 'totale' di questa "
                "dimensione prima di poter interrogare il dataflow."
            )
    return ".".join(parts)


def _data_path(series_id):
    spec = ISTAT_SERIES[series_id]
    key = _build_key(spec)
    return f"data/{spec['dataflow']}/{key}?startPeriod={START_YEAR}"


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


def parse_regional(rows, data_type, include_non_final=False, indicator_dimension="DATA_TYPE",
                    dimension_filters=None):
    """{region_name: {year: value}} for the 20 regions, Bolzano+Trento combined
    by population weight. Keeps only rows matching `data_type` on
    `indicator_dimension`, and region-level REF_AREA codes.

    `dimension_filters` (a {dimension: code} mapping, empty by default) guards
    a dataflow with more than the pilot's three dimensions: a row is kept only
    if every dimension it names in `filters` matches the code we asked for. It
    is a second check on top of the query key `_build_key` already sent,
    because a wrong server response should not be trusted just because the
    request looked right: if Istat silently ignored one of our filter codes,
    this is what stops an unrelated breakdown (a different age band, say) from
    being counted into what would look like a clean regional total.

    Two rows surviving those filters for the same region and year with
    different values are not averaged or silently overwritten. That shape only
    happens when the key did not actually isolate one series, almost always a
    missing or wrong 'total' code for some dimension, and publishing either
    number would be a guess dressed up as data, so this raises instead of
    picking one.

    Observations flagged not final (see NON_FINAL_STATUSES) are dropped unless
    `include_non_final`, so an estimated year cannot pass for a published one.
    """
    names = _load_region_names()
    filters = dimension_filters or {}
    by_region = {}
    trentino = {}  # year -> {part_code: value}
    for row in rows:
        if row.get(indicator_dimension) != data_type:
            continue
        if any(row.get(dim) != code for dim, code in filters.items()):
            # Fail closed, not open: a dimension missing from the row (a
            # truncated response, a typo in dimension_values that names a
            # column the dataflow doesn't have) must not be treated as a
            # match just because there was nothing to compare against.
            # row.get(dim) is None for a missing column, and None never
            # equals a real code, so this already excludes it.
            continue
        area = row.get("REF_AREA")
        year = row.get("TIME_PERIOD")
        raw = row.get("OBS_VALUE")
        if not area or not year or raw in (None, ""):
            continue
        if not include_non_final and (row.get("OBS_STATUS") or "").strip().lower() in NON_FINAL_STATUSES:
            continue
        value = float(raw)
        if area in TRENTINO_PARTS:
            part_values = trentino.setdefault(year, {})
            if area in part_values and part_values[area] != value:
                raise ValueError(
                    f"{indicator_dimension}={data_type}: {area} {year} ha due valori "
                    f"diversi ({part_values[area]!r} e {value!r}) dopo i filtri, prima "
                    "ancora di combinare Bolzano e Trento."
                )
            part_values[area] = value
            continue
        if not REGION_CODE_RE.match(area):
            continue
        region = names.get(area, area)
        existing = by_region.setdefault(region, {})
        if year in existing and existing[year] != value:
            raise ValueError(
                f"{indicator_dimension}={data_type}: {region} {year} ha due valori "
                f"diversi ({existing[year]!r} e {value!r}) dopo i filtri. La chiave non "
                "isola una riga sola: probabile codice 'totale' sbagliato o mancante "
                "per una dimensione del dataflow."
            )
        existing[year] = value
    for year, parts in trentino.items():
        # Both provinces must be present to combine honestly: a lone Bolzano or
        # Trento is not Trentino Alto Adige, so a partial year is left missing
        # (and does not count toward regional coverage) rather than published as
        # one province's value.
        if all(part in parts for part in TRENTINO_PARTS):
            total = sum(TRENTINO_WEIGHTS[p] for p in TRENTINO_PARTS)
            weighted = sum(parts[p] * TRENTINO_WEIGHTS[p] for p in TRENTINO_PARTS) / total
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
    regional = parse_regional(
        rows, spec["data_type"],
        indicator_dimension=spec["indicator_dimension"],
        dimension_filters=spec["dimension_values"],
    )
    year, coverage, _ = best_recent_year(regional)
    return {
        "source": SOURCE,
        "source_dataset": spec["dataflow"],
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
        # Provenance for the queue's `discovered_at`. Istat SDMX gives no
        # per-dataflow publication timestamp on the data query, so the honest
        # stand-in is the last final year: it says which vintage the candidate
        # was read at, which is what a reviewer comparing two runs needs. Left
        # blank before, so the two Istat rows were the only ones in the queue
        # with no provenance at all.
        "updated": f"{year}-12-31" if year is not None else "",
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
    regional = parse_regional(
        rows, spec["data_type"],
        indicator_dimension=spec["indicator_dimension"],
        dimension_filters=spec["dimension_values"],
    )
    years = sorted({int(y) for v in regional.values() for y in v})
    out = []
    for year in years:
        key = str(year)
        present = {r: v[key] for r, v in regional.items() if key in v}
        coverage = round(len(present) / REGION_COUNT, 4)
        if coverage < MIN_COVERAGE:
            continue
        for region_name in sorted(present):
            region_key = discovery.region_key(region_name)
            if region_key is None:
                # A name outside the 20 regions would be written with no key the
                # atlas can join on, so it would vanish from the map without an
                # error. Fail here instead.
                raise SystemExit(
                    f"{series_id}: '{region_name}' is not one of the 20 regional "
                    "names. Check the ITTER107 codelist mapping."
                )
            out.append({
                "region_key": region_key,
                "region_name": region_name,
                "year": key,
                "value": _format_value(present[region_name], spec["decimals"]),
                "coverage": coverage,
            })
    return out
