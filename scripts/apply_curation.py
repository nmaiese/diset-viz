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
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import curate, discovery  # noqa: E402
from scripts.promote_candidates import EXTERNAL_COLUMNS, MANIFEST_COLUMNS  # noqa: E402

EXTERNAL_DATASET = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"
EXTERNAL_MANIFEST = PROJECT_ROOT / "app" / "static" / "data" / "external_indicator_manifest.csv"
CURATED_DESCRIPTIONS = PROJECT_ROOT / "app" / "static" / "data" / "external" / "curated_descriptions.csv"
DESCRIPTION_COLUMNS = ["target_indicator_id", "plain", "value_explanation"]

VALID_DIRECTIONS = {"higher_better", "lower_better", "higher_worse", "contextual"}


def _validate(decision):
    direction = decision.get("reviewed_direction", "")
    if direction not in VALID_DIRECTIONS:
        raise SystemExit(f"{decision['target_indicator_id']}: invalid reviewed_direction '{direction}'")
    if decision.get("score_eligible") == "true" and direction not in curate.SCOREABLE_DIRECTIONS:
        raise SystemExit(
            f"{decision['target_indicator_id']}: score_eligible=true but direction '{direction}' is not scoreable"
        )


def _row_key(row):
    """What a decision is about: a target, reached from one source series.

    Keying on the target alone was enough while one external series existed per
    target. It stops being enough as soon as two sources enrich the same
    indicator: reviewing one of them would silently rewrite the direction and
    the score flag of the other, which nobody has looked at."""
    return (
        row.get("target_indicator_id", ""),
        row.get("source", ""),
        row.get("source_indicator_id", ""),
    )


def _decision_lookup(decisions):
    """(exact-key map, target-only fallback).

    The fallback covers curation rows that name no source at all, written before
    the source columns were part of the key: those still apply to every row of
    their target. A decision that *does* name its source only ever touches that
    source, which is the whole point."""
    by_key = {_row_key(d): d for d in decisions}
    by_target = {
        d["target_indicator_id"]: d
        for d in decisions
        if not d.get("source") and not d.get("source_indicator_id")
    }
    return by_key, by_target


def _decision_for(row, by_key, by_target):
    decision = by_key.get(_row_key(row))
    if decision is not None:
        return decision
    return by_target.get(row.get("target_indicator_id"))


def apply(decisions, dataset_rows, manifest_rows, descriptions):
    for decision in decisions:
        _validate(decision)
    by_key, by_target = _decision_lookup(decisions)

    for row in dataset_rows:
        decision = _decision_for(row, by_key, by_target)
        if decision is None:
            continue
        row["direction"] = decision["reviewed_direction"]
        if decision.get("reviewed_category"):
            row["quality_life_category"] = decision["reviewed_category"]
        row["score_eligible"] = decision.get("score_eligible", "false")

    for row in manifest_rows:
        decision = _decision_for(row, by_key, by_target)
        if decision is None:
            continue
        row["direction"] = decision["reviewed_direction"]
        row["score_eligible"] = decision.get("score_eligible", "false")
        row["status"] = "integrated"
        if decision.get("reviewer_notes"):
            row["review_notes"] = decision["reviewer_notes"]

    # The description belongs to the atlas entry, so it stays keyed by target.
    # Two sources describing the same target differently is a review conflict,
    # not something to resolve by whichever row happens to come last.
    desc_by_target = {d["target_indicator_id"]: d for d in descriptions}
    written = {}
    for decision in decisions:
        if not (decision.get("description") or decision.get("value_explanation")):
            continue
        target = decision["target_indicator_id"]
        entry = {
            "target_indicator_id": target,
            "plain": decision.get("description", ""),
            "value_explanation": decision.get("value_explanation", ""),
        }
        if written.get(target, entry) != entry:
            raise SystemExit(
                f"{target}: two curation rows describe the same indicator "
                "differently. Keep one description per target."
            )
        written[target] = entry
        desc_by_target[target] = entry
    return dataset_rows, manifest_rows, sorted(desc_by_target.values(), key=lambda r: r["target_indicator_id"])


def run(dry_run=False, dataset=EXTERNAL_DATASET, manifest=EXTERNAL_MANIFEST,
        descriptions=CURATED_DESCRIPTIONS, curation_path=None):
    decisions = curate.read_curation(curation_path)
    if not decisions:
        return {"applied": 0, "score_eligible": 0}
    dataset_rows = discovery.read_semicolon(dataset)
    manifest_rows = discovery.read_semicolon(manifest)
    desc_rows = discovery.read_semicolon(descriptions)
    dataset_rows, manifest_rows, desc_rows = apply(decisions, dataset_rows, manifest_rows, desc_rows)
    if not dry_run:
        discovery.write_semicolon(dataset_rows, EXTERNAL_COLUMNS, dataset)
        discovery.write_semicolon(manifest_rows, MANIFEST_COLUMNS, manifest)
        if desc_rows:
            discovery.write_semicolon(desc_rows, DESCRIPTION_COLUMNS, descriptions)
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
