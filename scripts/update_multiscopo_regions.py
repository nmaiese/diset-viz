#!/usr/bin/env python3
"""Fetch and normalise the Istat "Indagine Multiscopo" regional dataflows.

Single process, rate-limited SDMX client (5 queries/minute per IP at Istat,
see docs/PROVINCE_PIPELINE.md), cache-first and resumable. Writes the same
12-column dataset contract as the other regional CSVs plus an auditable
manifest, following the pattern of scripts/update_bes_regions.py.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import istat_sdmx, multiscopo_sources  # noqa: E402
from scripts.update_data import OUTPUT_COLUMNS  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"
DATA_DIR = PROJECT_ROOT / "app" / "static" / "data"
OUTPUT = DATA_DIR / "Assoluti_Multiscopo_Regione.csv"
MANIFEST = DATA_DIR / "multiscopo_regione_manifest.csv"
CODELIST_PATH = PROJECT_ROOT / "data" / "provincia" / "codelist_CL_ITTER107.csv"

NUTS2_PATTERN = re.compile(r"^IT[A-Z]\d$")

MANIFEST_COLUMNS = [
    "id", "name", "domain", "domain_name", "proposed_category",
    "proposed_direction", "unit", "year_min", "year_max", "n_region",
    "coverage", "n_region_latest", "coverage_latest", "source_dataflow", "scoreable",
]


def _load_region_names():
    names = {}
    with CODELIST_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            names[row["code"]] = row["name"].split("/", 1)[0].strip()
    return names


def _to_italian_decimal(value):
    return (value or "").strip().replace(".", ",")


def _write_atomic(rows, columns, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name
    os.replace(temp_name, path)
    os.chmod(path, 0o644)


def _matches(row, filters):
    return all(row.get(dim) == code for dim, code in filters.items())


def build(
    min_interval=16.0,
    max_requests=200,
    output=OUTPUT,
    manifest=MANIFEST,
    cache_dir=DEFAULT_CACHE,
    data_max_age=istat_sdmx.DATA_MAX_AGE,
    refresh_data=False,
):
    client = istat_sdmx.SdmxClient(
        cache_dir=cache_dir,
        min_interval=min_interval,
        data_max_age=data_max_age,
        refresh_data=refresh_data,
    )
    region_names = _load_region_names()

    dataset = []
    manifest_rows = []
    by_flow_cache = {}

    for spec in multiscopo_sources.MULTISCOPO_INDICATORS:
        if client.request_count >= max_requests:
            raise RuntimeError(
                f"Raggiunto --max-requests={max_requests} prima di completare il dataset. "
                "Nessun file è stato sovrascritto; rilanciare usando la cache già popolata."
            )
        flow_id = spec["flow_id"]
        if flow_id not in by_flow_cache:
            dsd_dims = _dataflow_dim_count(client, flow_id)
            key = "A" + "." * (dsd_dims - 1)
            rows = client.data(flow_id, key=key, start=2018)
            by_flow_cache[flow_id] = rows
        rows = by_flow_cache[flow_id]

        matching = [r for r in rows if _matches(r, spec["filters"])]
        # per-region, per-year value (averaging Bolzano+Trento into one region)
        by_region_year = defaultdict(dict)
        trentino_parts = defaultdict(dict)
        for row in matching:
            area = row["REF_AREA"]
            year = row["TIME_PERIOD"]
            value = row.get("OBS_VALUE")
            if value in (None, ""):
                continue
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                raise ValueError(f"{spec['id']}: valore non finito per {area}, {year}")
            if spec["unit"] == "%" and not 0 <= numeric_value <= 100:
                raise ValueError(
                    f"{spec['id']}: percentuale fuori intervallo per {area}, {year}: {value}"
                )
            if area in multiscopo_sources.TRENTINO_PARTS:
                if area in trentino_parts[year]:
                    raise ValueError(f"{spec['id']}: serie SDMX duplicata per {area}, {year}")
                trentino_parts[year][area] = numeric_value
                continue
            if not NUTS2_PATTERN.match(area) or area not in region_names:
                continue
            if year in by_region_year[area]:
                raise ValueError(
                    f"{spec['id']}: più osservazioni corrispondono ai filtri per {area}, {year}"
                )
            by_region_year[area][year] = value

        for year, parts in trentino_parts.items():
            if all(code in parts for code in multiscopo_sources.TRENTINO_PARTS):
                # Population-weighted mean of Bolzano and Trento (a plain mean
                # would publish a synthetic value for these rates).
                weights = multiscopo_sources.TRENTINO_WEIGHTS
                total_weight = sum(weights[code] for code in multiscopo_sources.TRENTINO_PARTS)
                weighted = sum(
                    parts[code] * weights[code] for code in multiscopo_sources.TRENTINO_PARTS
                ) / total_weight
                by_region_year[multiscopo_sources.TRENTINO_CODE][year] = repr(round(weighted, 6))

        years_seen = set()
        areas_seen = set()
        areas_by_year = defaultdict(set)
        for area, by_year in by_region_year.items():
            name = (
                "Trentino Alto Adige"
                if area == multiscopo_sources.TRENTINO_CODE
                else region_names.get(area, area)
            )
            for year, value in by_year.items():
                dataset.append({
                    "idIndicatore": spec["id"],
                    "Territorio": name,
                    "Tema": spec["tema"],
                    "Indicatore": spec["name"],
                    "UDM": spec["unit"],
                    "Fonte": "Istat",
                    "Archivio": f"{multiscopo_sources.ARCHIVE_LABEL}, {flow_id}",
                    "Anno": year,
                    "Livello/Variazione": "Livello",
                    "Dato": _to_italian_decimal(value),
                    "Benchmark": "",
                    "Area": "Regione",
                })
                years_seen.add(int(year))
                areas_seen.add(area)
                areas_by_year[int(year)].add(area)

        if not years_seen:
            print(f"  {spec['id']}: NO DATA matched filters {spec['filters']} in {flow_id}")
            continue
        year_max = max(years_seen)
        n_latest = len(areas_by_year[year_max])
        manifest_rows.append({
            "id": spec["id"],
            "name": spec["name"],
            "domain": spec["tema"],
            "domain_name": spec["tema"],
            "proposed_category": "",  # resolved at load time via app.taxonomy
            "proposed_direction": spec["direction"],
            "unit": spec["unit"],
            "year_min": min(years_seen),
            "year_max": year_max,
            "n_region": len(areas_seen),
            "coverage": round(len(areas_seen) / 20, 4),
            "n_region_latest": n_latest,
            "coverage_latest": round(n_latest / 20, 4),
            "source_dataflow": flow_id,
            "scoreable": int(spec["id"] in multiscopo_sources.QUALITY_LIFE_SCORE_IDS),
        })
        print(f"  {spec['id']}: year_max={year_max} coverage_latest={n_latest}/20 "
              f"(queries so far: {client.request_count})")

    dataset.sort(key=lambda r: (r["idIndicatore"], r["Territorio"], int(r["Anno"])))
    manifest_rows.sort(key=lambda r: r["id"])
    expected = {spec["id"] for spec in multiscopo_sources.MULTISCOPO_INDICATORS}
    completed = {row["id"] for row in manifest_rows}
    if completed != expected:
        missing = sorted(expected - completed)
        raise RuntimeError(f"Dataset incompleto, indicatori senza dati: {', '.join(missing)}")

    _write_atomic(dataset, OUTPUT_COLUMNS, output)
    _write_atomic(manifest_rows, MANIFEST_COLUMNS, manifest)
    print(f"\nWrote {output}: {len(dataset)} rows, {len(manifest_rows)} indicators")
    print(f"Wrote {manifest}")
    print(f"Total network queries used: {client.request_count}")


def _dataflow_dim_count(client, flow_id):
    import re
    flows = client.dataflows()
    flow = next(f for f in flows if f["id"] == flow_id)
    m = re.search(r"DataStructure=[^:]+:([^()]+)\(", flow["dsd"])
    dsd = client.datastructure(m.group(1))
    return len(dsd["dimensions"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--min-interval", type=float, default=16.0)
    parser.add_argument("--max-requests", type=int, default=200)
    parser.add_argument(
        "--data-max-age",
        type=float,
        default=istat_sdmx.DATA_MAX_AGE,
        help="Età massima in secondi di una risposta dati in cache (0 = sempre scaduta). "
             "Le strutture (dataflow, DSD, codelist) restano in cache senza scadenza.",
    )
    parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="Riscarica le risposte dati ignorando la cache, strutture escluse.",
    )
    args = parser.parse_args()
    build(
        min_interval=args.min_interval,
        max_requests=args.max_requests,
        output=args.output,
        manifest=args.manifest,
        cache_dir=args.cache_dir,
        data_max_age=args.data_max_age,
        refresh_data=args.refresh_data,
    )
