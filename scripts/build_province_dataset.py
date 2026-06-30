#!/usr/bin/env python3
"""Normalise cached BES provincial data into the Divario Italia schema.

Offline only: reads the SDMX-CSV responses already in data/istat_cache (via the
same client, cache-only) plus the codelists dumped under data/provincia, and
writes three auditable artifacts under app/static/data:

- Assoluti_Provincia.csv   same 12 columns as the regional dataset, Area="Provincia",
                           one row per (indicator, province, year), total sex only.
- province_manifest.csv    one row per indicator: source dataflow, BES domain,
                           proposed quality-of-life category, proposed direction,
                           unit, years, province coverage. The auditable mapping
                           the integration phase will consume.
- province_codes.csv       the NUTS3 provinces: code, name, key, region.

Nothing here invents data: every value is a real Istat observation, every label
comes from an Istat codelist. Run after scripts/fetch_provinces.py.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import istat_sdmx, province_sources  # noqa: E402
from scripts.province_names import normalize_province_name, province_key  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"
PROVINCIA_DIR = PROJECT_ROOT / "data" / "provincia"
DATA_DIR = PROJECT_ROOT / "app" / "static" / "data"

OUTPUT_COLUMNS = [
    "idIndicatore", "Territorio", "Tema", "Indicatore", "UDM", "Fonte",
    "Archivio", "Anno", "Livello/Variazione", "Dato", "Benchmark", "Area",
]

# UNIT_MEAS code -> readable Italian label (fallback: the raw code).
UNIT_LABELS = {
    "VAL_PERC": "%",
    "EURO": "euro",
    "AVG_NY": "anni (media)",
    "PER_100THOU_INHA": "per 100.000 abitanti",
    "PER_10THOU_INHA": "per 10.000 abitanti",
    "PER_MILLION_INHA": "per milione di abitanti",
    "PER_1THOU_LBIRTHS": "per 1.000 nati vivi",
    "PER_10THOU_EMPL": "per 10.000 occupati",
    "PER_1THOU_RESGRAD": "per 1.000 laureati residenti",
    "STA_RA_PER_10THOU": "tasso standardizzato per 10.000",
    "SPEC_COHORT_RATE": "tasso specifico per coorte",
    "MICROGRAMS_PER_M3": "microgrammi per m3",
    "PER_100_KM2": "per 100 km2",
    "PER_100_M2": "per 100 m2",
    "M2_PER_INHA": "m2 per abitante",
    "KG_PER_INHA": "kg per abitante",
    "VAL_PER_INHA": "valore per abitante",
    "AVG_NUMB_USER": "numero medio di utenti",
    "": "numero",
}

# The 14 metropolitan cities (città metropolitane), for a context flag.
METRO_CITIES = {
    "Torino", "Genova", "Milano", "Venezia", "Bologna", "Firenze", "Roma",
    "Napoli", "Bari", "Reggio Calabria", "Palermo", "Messina", "Catania", "Cagliari",
}


def load_codelist_csv(path):
    """code -> {name, parent} from a dumped codelist CSV (code;name;parent)."""
    mapping = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            mapping[row["code"]] = {"name": row["name"], "parent": row.get("parent") or ""}
    return mapping


def to_italian_decimal(value):
    """SDMX dot-decimal -> Italian comma-decimal, matching the regional CSV."""
    return (value or "").strip().replace(".", ",")


def write_atomic_rows(rows, columns, output_path, delimiter=";"):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=output_path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, delimiter=delimiter, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name
    os.replace(temp_name, output_path)
    os.chmod(output_path, 0o644)


def _clean_region_name(raw):
    """Italian side of a bilingual NUTS2 label, whitespace collapsed."""
    return " ".join((raw or "").split()).split("/", 1)[0].strip()


# level -> how to slice the same BES cache for a different territorial layer.
LEVELS = {
    "province": {
        "pattern": province_sources.NUTS3_PATTERN,
        "area": "Provincia",
        # 107 NUTS3 codes minus the 4 defunct pre-2016 Sardinian provinces we
        # drop; Sud Sardegna is not in this BES vintage, so we rank 103.
        "denom": 103,
        "name_fn": normalize_province_name,
        "dataset": "Assoluti_Provincia.csv",
        "manifest": "province_manifest.csv",
        "unit_col": "n_province",
    },
    "region": {
        "pattern": province_sources.NUTS2_PATTERN,
        "area": "Regione",
        "denom": 20,
        "name_fn": _clean_region_name,
        "dataset": "Assoluti_BES_Regione.csv",
        "manifest": "bes_regione_manifest.csv",
        "unit_col": "n_region",
    },
}


def build(level="province"):
    config = LEVELS[level]
    pattern = config["pattern"]
    name_fn = config["name_fn"]
    denom = config["denom"]
    territory = load_codelist_csv(PROVINCIA_DIR / "codelist_CL_ITTER107.csv")
    indicators = load_codelist_csv(PROVINCIA_DIR / "codelist_CL_BES_INDICATOR.csv")
    domains = load_codelist_csv(PROVINCIA_DIR / "codelist_CL_SUS_DOMAIN.csv")
    client = istat_sdmx.SdmxClient(cache_dir=DEFAULT_CACHE, cache_only=True)

    # latest[(data_type, ref_area, year)] = (edition, row) keeps the newest edition.
    latest = {}
    domain_of = {}
    unit_of = {}
    for domain in province_sources.BES_DOMAINS:
        try:
            rows = client.data(province_sources.BES_DATAFLOW,
                               key=province_sources.bes_key(domain),
                               start=province_sources.BES_START_PERIOD)
        except istat_sdmx.CacheMissError:
            print(f"  {domain}: not in cache; skipped (run fetch_provinces.py first)")
            continue
        for row in rows:
            if row["SEX"] not in province_sources.SEX_TOTAL_CODES:
                continue
            area = row["REF_AREA"]
            if not pattern.match(area):
                continue
            data_type = row["DATA_TYPE"]
            year = row["TIME_PERIOD"]
            value = row["OBS_VALUE"]
            if value in (None, ""):
                continue
            key = (data_type, area, year)
            edition = row.get("EDITION", "")
            if key not in latest or edition > latest[key][0]:
                latest[key] = (edition, row)
            domain_of[data_type] = domain
            unit_of[data_type] = row.get("UNIT_MEAS", "")

    # -- dataset rows --------------------------------------------------------
    defunct = province_sources.DEFUNCT_PROVINCES if level == "province" else set()
    dataset = []
    for (data_type, area, year), (_edition, row) in latest.items():
        name = name_fn(territory.get(area, {}).get("name", area))
        if name in defunct:
            continue
        domain = domain_of[data_type]
        dataset.append({
            "idIndicatore": data_type,
            "Territorio": name,
            "Tema": domains.get(domain, {}).get("name", domain),
            "Indicatore": indicators.get(data_type, {}).get("name", data_type),
            "UDM": UNIT_LABELS.get(unit_of.get(data_type, ""), unit_of.get(data_type, "")),
            "Fonte": "Istat",
            "Archivio": f"BES dei Territori (Bes at local level), {province_sources.BES_DATAFLOW}, dominio {domain}",
            "Anno": year,
            "Livello/Variazione": "Livello",
            "Dato": to_italian_decimal(row["OBS_VALUE"]),
            "Benchmark": "",
            "Area": config["area"],
        })
    dataset.sort(key=lambda r: (r["idIndicatore"], r["Territorio"], int(r["Anno"])))
    write_atomic_rows(dataset, OUTPUT_COLUMNS, DATA_DIR / config["dataset"])

    # -- manifest ------------------------------------------------------------
    by_indicator = defaultdict(lambda: {"years": set(), "areas": set(),
                                         "areas_by_year": defaultdict(set)})
    for (data_type, area, year), _ in latest.items():
        if name_fn(territory.get(area, {}).get("name", area)) in defunct:
            continue
        agg = by_indicator[data_type]
        agg["years"].add(int(year))
        agg["areas"].add(area)
        agg["areas_by_year"][int(year)].add(area)
    count_col = config["unit_col"]
    manifest_rows = []
    for data_type, agg in by_indicator.items():
        domain = domain_of[data_type]
        name = indicators.get(data_type, {}).get("name", data_type)
        year_max = max(agg["years"])
        n_latest = len(agg["areas_by_year"][year_max])
        manifest_rows.append({
            "id": data_type,
            "name": name,
            "domain": domain,
            "domain_name": domains.get(domain, {}).get("name", domain),
            "proposed_category": province_sources.category_for(data_type, domain) or "",
            "proposed_direction": province_sources.direction_for(data_type, name),
            "unit": UNIT_LABELS.get(unit_of.get(data_type, ""), unit_of.get(data_type, "")),
            "year_min": min(agg["years"]),
            "year_max": year_max,
            # ever = areas seen across all years; *_latest = areas present in year_max.
            count_col: len(agg["areas"]),
            "coverage": round(len(agg["areas"]) / denom, 4),
            f"{count_col}_latest": n_latest,
            "coverage_latest": round(n_latest / denom, 4),
            "source_dataflow": province_sources.BES_DATAFLOW,
        })
    manifest_rows.sort(key=lambda r: (r["domain"], r["id"]))
    manifest_columns = ["id", "name", "domain", "domain_name", "proposed_category",
                        "proposed_direction", "unit", "year_min", "year_max",
                        count_col, "coverage", f"{count_col}_latest",
                        "coverage_latest", "source_dataflow"]
    write_atomic_rows(manifest_rows, manifest_columns, DATA_DIR / config["manifest"])

    # -- province codes (province level only) --------------------------------
    n_codes = 0
    if level == "province":
        province_rows = []
        seen = set()
        for code, info in territory.items():
            if not pattern.match(code):
                continue
            pname = name_fn(info["name"])
            if pname in seen or pname in province_sources.DEFUNCT_PROVINCES:
                continue
            seen.add(pname)
            parent = info.get("parent", "")
            region = _clean_region_name(territory.get(parent, {}).get("name", "")) if parent else ""
            province_rows.append({
                "code": code,
                "name": pname,
                "province_key": province_key(pname),
                "region": region,
                "metro_city": "1" if pname in METRO_CITIES else "",
            })
        province_rows.sort(key=lambda r: r["name"])
        write_atomic_rows(province_rows,
                          ["code", "name", "province_key", "region", "metro_city"],
                          DATA_DIR / "province_codes.csv")
        n_codes = len(province_rows)

    # -- summary -------------------------------------------------------------
    n_areas = len({r["Territorio"] for r in dataset})
    years = sorted({int(r["Anno"]) for r in dataset})
    print(f"{config['dataset']}: {len(dataset)} rows, {len(by_indicator)} indicators, "
          f"{n_areas} {level}, years {years[0]}-{years[-1]}")
    print(f"{config['manifest']}: {len(manifest_rows)} indicators")
    if n_codes:
        print(f"province_codes.csv: {n_codes} province")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", choices=sorted(LEVELS), default="province")
    return parser.parse_args()


def main():
    args = parse_args()
    build(args.level)


if __name__ == "__main__":
    main()
