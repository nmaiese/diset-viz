#!/usr/bin/env python3
"""Build the normalized external-source dataset.

Currently promoted parser:
- istat_demografia: normalizes existing official Istat demographic 2025+ rows
  already present in the regional atlas, without mutating the legacy CSV.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.external_data import EXTERNAL_COLUMNS  # noqa: E402
from app.indicator_notes import direction_for  # noqa: E402
from app.profiles import region_key_for  # noqa: E402
from scripts.external_sources import source_by_id  # noqa: E402


LEGACY_REGION = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
OUTPUT = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"

DEMOGRAPHY_IDS = {"910", "911", "912", "913", "920", "921", "922", "923"}
CONTEXTUAL_DEMOGRAPHY = {"920", "921", "922", "923"}


def _bool(value):
    return "true" if value else "false"


def _write_atomic(rows, columns, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=output_path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name
    os.replace(temp_name, output_path)
    os.chmod(output_path, 0o644)


def _coverage(rows):
    areas = defaultdict(set)
    for row in rows:
        areas[(row["target_indicator_id"], row["year"])].add(row["territory_code"])
    return {key: round(len(value) / 20, 4) for key, value in areas.items()}


def build_istat_demografia(year, level):
    source = source_by_id("istat_demografia")
    if source is None:
        raise RuntimeError("Missing istat_demografia in external source registry")
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = []
    with LEGACY_REGION.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            indicator_id = row["idIndicatore"]
            if indicator_id not in DEMOGRAPHY_IDS:
                continue
            if level and level != "regione":
                continue
            try:
                row_year = int(row["Anno"])
            except ValueError:
                continue
            if row_year < year:
                continue
            direction = "contextual" if indicator_id in CONTEXTUAL_DEMOGRAPHY else direction_for(indicator_id, row["Indicatore"])
            definition_match = "exact" if indicator_id in {"910", "911", "912", "913"} else "compatible"
            rows.append({
                "source": "istat_demografia",
                "source_dataset": source["dataset"],
                "source_indicator_id": indicator_id,
                "target_indicator_id": indicator_id,
                "name": row["Indicatore"],
                "territory_level": "regione",
                "territory_code": region_key_for(row["Territorio"]),
                "territory_name": row["Territorio"],
                "year": row["Anno"],
                "value": row["Dato"],
                "unit": row["UDM"],
                "theme": row["Tema"],
                "quality_life_category": "salute_cura" if indicator_id in {"910", "911", "912", "913"} else "salute_cura",
                "direction": direction,
                "definition_match": definition_match,
                "atlas_eligible": _bool(True),
                "profile_eligible": _bool(True),
                "score_eligible": _bool(False),
                "coverage": "",
                "retrieved_at": retrieved_at,
                "source_url": source["landing_page"],
                "license": source["license"],
                "notes": "Normalized from existing Istat regional demographic atlas rows. No BES replacement is applied here.",
            })

    cov = _coverage(rows)
    for row in rows:
        row["coverage"] = cov[(row["target_indicator_id"], row["year"])]
    rows.sort(key=lambda r: (r["target_indicator_id"], int(r["year"]), r["territory_name"]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="istat_demografia")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--level", default="regione")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.source != "istat_demografia":
        raise SystemExit(f"No promoted parser for {args.source}. Add a fixture/parser before building.")

    rows = build_istat_demografia(args.year, args.level)
    if not rows:
        raise SystemExit("No external rows built")
    if args.dry_run:
        print(f"Would write {len(rows)} rows to {OUTPUT}")
        return
    _write_atomic(rows, EXTERNAL_COLUMNS, OUTPUT)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
