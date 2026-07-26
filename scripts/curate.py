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

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Same pattern as promote_candidates/apply_curation, so the CLI can import the
# shared discovery helpers when run as `python3 scripts/curate.py`.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery  # noqa: E402

CURATION_PATH = PROJECT_ROOT / "data" / "discovery" / "curation.csv"
EXTERNAL_DATASET = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"

CURATION_COLUMNS = [
    "target_indicator_id",     # eur:rd_e_gerdreg, dem:OLDAGEDEPR (the public atlas id)
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
    return discovery.read_semicolon(path)


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


# Public-id prefixes of every family published through the external layer, from
# the shared registry rather than the single literal "eur:" this used to test.
# With a second adapter live, that literal meant the curator could not see the
# indicator the hunter had just promoted: dem:OLDAGEDEPR would have sat
# integrated-but-unreviewed with nothing pointing at it.
EXTERNAL_PREFIXES = tuple(
    prefix for family, prefix in discovery.FAMILY_PREFIX.items()
    if prefix and family in discovery.FEED_FAMILY.values()
)


def uncurated_targets(rows=None, decisions=None):
    """Standalone external atlas indicators nobody has reviewed yet.

    "Reviewed" means a row exists in `data/discovery/curation.csv`, not
    `score_eligible=true`. Those are different things, and reading the flag was
    a bug with teeth for a scheduled curator: `contextual` is a legitimate and
    final verdict that leaves `score_eligible` false forever, so a correctly
    curated dependency ratio came back on the worklist every single run and the
    agent would have re-reviewed it, and opened a PR for it, week after week.
    """
    rows = rows if rows is not None else read_external()
    decisions = decisions if decisions is not None else read_curation()
    reviewed = {row.get("target_indicator_id") for row in decisions}
    seen = []
    for row in rows:
        target = row.get("target_indicator_id", "")
        if not target.startswith(EXTERNAL_PREFIXES) or row.get("atlas_eligible") != "true":
            continue
        if target in reviewed or target in seen:
            continue
        seen.append(target)
    return seen


def read_curation(path=None):
    # Resolve CURATION_PATH at call time (not as a default) so tests can point
    # the curation file elsewhere without ever risking the committed one.
    path = Path(path) if path else CURATION_PATH
    return discovery.read_semicolon(path)


def write_curation(rows, path=None):
    path = Path(path) if path else CURATION_PATH
    discovery.write_semicolon(rows, CURATION_COLUMNS, path)


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="Print direction evidence for the curator.")
    parser.add_argument("--target", help="a specific external id (eur:..., dem:...); default: all uncurated")
    args = parser.parse_args()

    rows = read_external()
    targets = [args.target] if args.target else uncurated_targets(rows)
    if not targets:
        print("Nessun indicatore esterno da curare.")
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
