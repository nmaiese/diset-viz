#!/usr/bin/env python3
"""Publish curator decisions into the external layer.

Reads data/discovery/curation.csv and applies each reviewed decision to the
normalized external dataset and manifest: the verified direction and category,
the score-eligibility flag (only set once the verso is confirmed scoreable), and
status=integrated. Reviewed descriptions are written to a small committed store
the atlas reads (app/static/data/external/curated_descriptions.csv).

After this runs, quality_life_selection / quality_life_bes pick up the newly
score-eligible indicator and it enters the regional quality-of-life score, while
the atlas page and quiz already show it. All under the PR gate: nothing is live
until the resulting diff is merged. Pure stdlib.

    python3 scripts/apply_curation.py --dry-run
    python3 scripts/apply_curation.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import curate  # noqa: E402
from scripts.promote_candidates import EXTERNAL_COLUMNS, MANIFEST_COLUMNS  # noqa: E402

EXTERNAL_DATASET = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"
EXTERNAL_MANIFEST = PROJECT_ROOT / "app" / "static" / "data" / "external_indicator_manifest.csv"
CURATED_DESCRIPTIONS = PROJECT_ROOT / "app" / "static" / "data" / "external" / "curated_descriptions.csv"
DESCRIPTION_COLUMNS = ["target_indicator_id", "plain", "value_explanation"]

VALID_DIRECTIONS = {"higher_better", "lower_better", "higher_worse", "contextual"}


def _read(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _write(rows, columns, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
        temp_name = tmp.name
    os.replace(temp_name, path)
    os.chmod(path, 0o644)


def _validate(decision):
    direction = decision.get("reviewed_direction", "")
    if direction not in VALID_DIRECTIONS:
        raise SystemExit(f"{decision['target_indicator_id']}: invalid reviewed_direction '{direction}'")
    if decision.get("score_eligible") == "true" and direction not in curate.SCOREABLE_DIRECTIONS:
        raise SystemExit(
            f"{decision['target_indicator_id']}: score_eligible=true but direction '{direction}' is not scoreable"
        )


def apply(decisions, dataset_rows, manifest_rows, descriptions):
    by_target = {d["target_indicator_id"]: d for d in decisions}
    for decision in decisions:
        _validate(decision)

    for row in dataset_rows:
        decision = by_target.get(row.get("target_indicator_id"))
        if decision is None:
            continue
        row["direction"] = decision["reviewed_direction"]
        if decision.get("reviewed_category"):
            row["quality_life_category"] = decision["reviewed_category"]
        row["score_eligible"] = decision.get("score_eligible", "false")

    for row in manifest_rows:
        decision = by_target.get(row.get("target_indicator_id"))
        if decision is None:
            continue
        row["direction"] = decision["reviewed_direction"]
        row["score_eligible"] = decision.get("score_eligible", "false")
        row["status"] = "integrated"
        if decision.get("reviewer_notes"):
            row["review_notes"] = decision["reviewer_notes"]

    desc_by_target = {d["target_indicator_id"]: d for d in descriptions}
    for decision in decisions:
        if decision.get("description") or decision.get("value_explanation"):
            desc_by_target[decision["target_indicator_id"]] = {
                "target_indicator_id": decision["target_indicator_id"],
                "plain": decision.get("description", ""),
                "value_explanation": decision.get("value_explanation", ""),
            }
    return dataset_rows, manifest_rows, sorted(desc_by_target.values(), key=lambda r: r["target_indicator_id"])


def run(dry_run=False, dataset=EXTERNAL_DATASET, manifest=EXTERNAL_MANIFEST, descriptions=CURATED_DESCRIPTIONS):
    decisions = curate.read_curation()
    if not decisions:
        return {"applied": 0, "score_eligible": 0}
    dataset_rows = _read(dataset)
    manifest_rows = _read(manifest)
    desc_rows = _read(descriptions)
    dataset_rows, manifest_rows, desc_rows = apply(decisions, dataset_rows, manifest_rows, desc_rows)
    if not dry_run:
        _write(dataset_rows, EXTERNAL_COLUMNS, dataset)
        _write(manifest_rows, MANIFEST_COLUMNS, manifest)
        if desc_rows:
            _write(desc_rows, DESCRIPTION_COLUMNS, descriptions)
    return {
        "applied": len(decisions),
        "score_eligible": sum(1 for d in decisions if d.get("score_eligible") == "true"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    if result["applied"] == 0:
        print("No curation decisions in data/discovery/curation.csv.")
        return
    verb = "Would apply" if args.dry_run else "Applied"
    print(f"{verb} {result['applied']} curation decision(s); "
          f"{result['score_eligible']} marked score-eligible.")


if __name__ == "__main__":
    main()
