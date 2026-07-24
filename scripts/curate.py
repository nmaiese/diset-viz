#!/usr/bin/env python3
"""Curation layer: the qualitative pass the scouting hunter does not do.

The hunter proposes a direction and a category from names alone. The curator
(a scheduled agent, or a human) verifies the *verso* against the actual data,
reviews the description, and records a decision in data/discovery/curation.csv.
apply_curation.py then publishes that decision into the external layer so the
indicator enters scoring, quiz and quality of life.

This module is pure stdlib: it reads the committed normalized external dataset
to build direction evidence, and it defines the curation record schema.
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURATION_PATH = PROJECT_ROOT / "data" / "discovery" / "curation.csv"
EXTERNAL_DATASET = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"

CURATION_COLUMNS = [
    "target_indicator_id",     # eur:rd_e_gerdreg (the public atlas id)
    "source",
    "source_indicator_id",
    "name",
    "reviewed_direction",      # higher_better | lower_better | higher_worse | contextual
    "direction_verdict",       # confermato | corretto  (was the hunter's guess right?)
    "reviewed_category",       # canonical category slug
    "score_eligible",          # true only after the verso is verified as scoreable
    "description",             # reviewed plain-language definition (optional override)
    "value_explanation",       # reviewed unit reading (optional override)
    "reviewer_notes",
    "reviewed_at",
]

SCOREABLE_DIRECTIONS = {"higher_better", "lower_better", "higher_worse"}


def _parse_number(value):
    if value is None or not value.strip():
        return None
    normalized = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def read_external(path=EXTERNAL_DATASET):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def direction_evidence(target_indicator_id, rows=None):
    """Rank the regions on the latest year so the curator can judge the verso.

    Returns the top and bottom regions with values, the proposed direction, and
    a plain reading: if the proposed direction is higher_better, the top regions
    should be the ones we would call 'better'. If they are not, the verso is
    probably wrong and must be corrected."""
    rows = rows if rows is not None else read_external()
    series = [r for r in rows if r.get("target_indicator_id") == target_indicator_id]
    if not series:
        return None
    years = [int(r["year"]) for r in series if r.get("year")]
    latest = max(years)
    points = [
        (r["territory_name"], _parse_number(r["value"]))
        for r in series
        if int(r["year"]) == latest and _parse_number(r["value"]) is not None
    ]
    points.sort(key=lambda item: item[1], reverse=True)
    if not points:
        return None
    proposed = series[0].get("direction", "")
    return {
        "target_indicator_id": target_indicator_id,
        "name": series[0].get("name", ""),
        "unit": series[0].get("unit", ""),
        "year": latest,
        "coverage": series[0].get("coverage", ""),
        "proposed_direction": proposed,
        "quality_life_category": series[0].get("quality_life_category", ""),
        "definition_match": series[0].get("definition_match", ""),
        "highest": points[:3],
        "lowest": points[-3:],
    }


def uncurated_targets(rows=None):
    """Standalone external atlas indicators (eur:*) not yet score-eligible: the
    curator's worklist."""
    rows = rows if rows is not None else read_external()
    seen = {}
    for row in rows:
        target = row.get("target_indicator_id", "")
        if target.startswith("eur:") and row.get("atlas_eligible") == "true":
            seen.setdefault(target, row.get("score_eligible") == "true")
    return [target for target, scoreable in seen.items() if not scoreable]


def read_curation(path=CURATION_PATH):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_curation(rows, path=CURATION_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=CURATION_COLUMNS, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CURATION_COLUMNS})
        temp_name = tmp.name
    os.replace(temp_name, path)
    os.chmod(path, 0o644)


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="Print direction evidence for the curator.")
    parser.add_argument("--target", help="a specific eur: id; default: all uncurated")
    args = parser.parse_args()

    rows = read_external()
    targets = [args.target] if args.target else uncurated_targets(rows)
    if not targets:
        print("No uncurated Eurostat atlas indicators.")
        return
    for target in targets:
        ev = direction_evidence(target, rows)
        if ev is None:
            print(f"{target}: no data")
            continue
        print(f"\n{target}  {ev['name']}  ({ev['unit']}, {ev['year']}, cov={ev['coverage']})")
        print(f"  verso proposto: {ev['proposed_direction']}  categoria: {ev['quality_life_category']}")
        print("  piu alti:  " + ", ".join(f"{n} {v:g}" for n, v in ev["highest"]))
        print("  piu bassi: " + ", ".join(f"{n} {v:g}" for n, v in ev["lowest"]))
        print("  -> se il verso e higher_better, in cima devono esserci le regioni 'migliori'.")


if __name__ == "__main__":
    _cli()
