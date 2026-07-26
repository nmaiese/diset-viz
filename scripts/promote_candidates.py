#!/usr/bin/env python3
"""The integrator: promote approved candidates into the normalized external layer.

Reads the discovery queue and acts ONLY on candidates a human has marked
``triage_status=approved``. For each, it writes normalized regional rows into the
external dataset and a manifest entry with ``status=proposed`` (never
``integrated``: the merge of the resulting PR is what actually publishes it).

This closes the loop hunter -> queue -> (human approves in queue) -> external
layer diff, all under the PR gate. Pure stdlib; the external/manifest column
lists mirror app.external_data so the app is not imported here.

    python3 scripts/promote_candidates.py --offline --dry-run
    python3 scripts/promote_candidates.py --offline            # writes the diff
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery, eurostat_source, istat_regional_source  # noqa: E402

# One promotion parser per hunter adapter. This registry is the fix for a real
# hole: the hunter grew a second adapter (istat_demografia) while promotion
# still tested `source != "eurostat_regional"` and refused everything else, so
# two candidates sat at the top of the queue with no path out of it. Adding an
# adapter now means adding its `normalized_rows` here and its family in
# discovery.FEED_FAMILY, nothing more.
PROMOTION_PARSERS = {
    "eurostat_regional": eurostat_source.normalized_rows,
    "istat_demografia": istat_regional_source.normalized_rows,
}

EXTERNAL_DATASET = PROJECT_ROOT / "app" / "static" / "data" / "external" / "normalized_external_indicators.csv"
EXTERNAL_MANIFEST = PROJECT_ROOT / "app" / "static" / "data" / "external_indicator_manifest.csv"

# Mirror of app.external_data.EXTERNAL_COLUMNS / MANIFEST_COLUMNS (kept in sync).
EXTERNAL_COLUMNS = [
    "source", "source_dataset", "source_indicator_id", "target_indicator_id", "name",
    "territory_level", "territory_code", "territory_name", "year", "value", "unit",
    "theme", "quality_life_category", "direction", "definition_match", "atlas_eligible",
    "profile_eligible", "score_eligible", "coverage", "retrieved_at", "source_url",
    "license", "notes",
]
MANIFEST_COLUMNS = [
    "target_indicator_id", "target_indicator_name", "source", "source_indicator_id",
    "definition_match", "current_year", "new_year", "territory_level", "unit_match",
    "coverage", "direction", "score_eligible", "status", "review_notes",
]

# A real overlap enriches an existing indicator (target = the existing id); a
# genuinely new series becomes a standalone atlas entry under its own family's public
# id namespace, wired into the federated catalog by app/external_atlas.py.
ENRICHING_MATCHES = {"exact", "compatible", "proxy"}


def _target_id(candidate):
    """The catalog id the promoted rows attach to.

    `duplicate_of` comes from discovery.build_existing_index and is already
    family-qualified ("bes:10AMB014", "multiscopo:...", or a bare numeric id for
    the territorial family, which owns the unprefixed namespace). Anything else
    would name an indicator that does not exist, so it is refused here rather
    than written into the external layer.

    A genuinely new series gets the namespace of the family its *own* adapter
    feeds. This used to be a hardcoded "eur:", which was harmless while Eurostat
    was the only adapter and a lie the moment a second one landed: an Istat
    demographic series would have been published at /indicatore/<slug>/eur-...,
    labelled "Eurostat, statistiche regionali" and carrying Eurostat's licence.
    """
    if candidate["definition_match"] in ENRICHING_MATCHES and candidate.get("duplicate_of"):
        target = candidate["duplicate_of"]
        if not _is_known_target(target):
            raise SystemExit(
                f"{candidate['candidate_id']}: duplicate_of='{target}' is not a "
                "family-qualified catalog id (expected 'bes:<id>', "
                "'multiscopo:<id>' or a numeric territorial id). Re-run the "
                "hunter so the match carries its family."
            )
        return target
    family = discovery.FEED_FAMILY.get(candidate["source"])
    if family is None:
        raise SystemExit(
            f"{candidate['candidate_id']}: source '{candidate['source']}' has no "
            "catalog family. Add it to discovery.FEED_FAMILY and to the `feeds` "
            "of a family in app/sources.py before promoting it."
        )
    return discovery.public_id(family, candidate["source_indicator_id"])


def _is_known_target(target):
    prefixes = tuple(p for p in discovery.FAMILY_PREFIX.values() if p)
    return target.startswith(prefixes) or target.isdigit()


def _bool(value):
    return "true" if value else "false"


def _external_rows_for(candidate, offline, refresh):
    parser = PROMOTION_PARSERS.get(candidate["source"])
    if parser is None:
        raise SystemExit(
            f"No promotion parser for source '{candidate['source']}'. "
            f"Known: {', '.join(sorted(PROMOTION_PARSERS))}."
        )
    series_id = candidate["source_indicator_id"]
    rows = parser(series_id, offline=offline, refresh=refresh)
    target = _target_id(candidate)
    enriches = candidate["definition_match"] in ENRICHING_MATCHES and bool(candidate.get("duplicate_of"))
    prefix = discovery.FAMILY_PREFIX.get(discovery.FEED_FAMILY.get(candidate["source"], ""), "")
    note = (
        f"{candidate['source']} arricchisce un indicatore esistente. Nessuna sostituzione BES/atlas."
        if enriches
        else f"Voce d'atlante autonoma (namespace {prefix}). Fuori dallo scoring finche la direzione non e revisionata a mano."
    )
    out = []
    for row in rows:
        out.append({
            "source": candidate["source"],
            "source_dataset": candidate["source_dataset"],
            "source_indicator_id": candidate["source_indicator_id"],
            "target_indicator_id": target,
            "name": candidate["name"],
            "territory_level": "regione",
            "territory_code": row["region_key"],
            "territory_name": row["region_name"],
            "year": str(row["year"]),
            "value": row["value"],
            "unit": candidate["unit"],
            "theme": candidate["proposed_theme"],
            "quality_life_category": candidate["proposed_quality_life_category"],
            "direction": candidate["proposed_direction"],
            "definition_match": candidate["definition_match"],
            # Both paths are browsable in the atlas; only a reviewed overlap feeds
            # regional profiles, and nothing feeds the score without manual review.
            "atlas_eligible": _bool(True),
            "profile_eligible": _bool(enriches),
            "score_eligible": _bool(False),
            "coverage": row["coverage"],
            "retrieved_at": candidate.get("discovered_at", ""),
            "source_url": candidate["source_url"],
            "license": candidate["license"],
            "notes": note,
        })
    return out, target, enriches, note


def _manifest_entry(candidate, target, enriches, note, rows):
    # rows span the full historical series; the manifest headline is the latest year.
    year = max((r["year"] for r in rows), default=candidate.get("year_max", ""))
    return {
        "target_indicator_id": target,
        "target_indicator_name": candidate["name"],
        "source": candidate["source"],
        "source_indicator_id": candidate["source_indicator_id"],
        "definition_match": candidate["definition_match"],
        "current_year": "",
        "new_year": year,
        "territory_level": "regione",
        "unit_match": "",
        "coverage": candidate.get("coverage", ""),
        "direction": candidate["proposed_direction"],
        "score_eligible": _bool(False),
        "status": "proposed",
        "review_notes": note,
    }


def _merge_dataset(existing, new_rows, curated_series=()):
    """Merge promoted rows into the external dataset, per region-year.

    `curated_series` is the set of (source, source_indicator_id) the curator has
    already signed off. Their reviewed fields survive the refresh: the dataset
    rows carry `direction`, `score_eligible` and `quality_life_category` too, and
    those are what app.external_atlas actually reads to decide whether an
    indicator is in the quality-of-life score. Protecting only the manifest was
    not enough, and a re-promotion silently dropped a live indicator out of the
    ranking while the manifest still said `integrated`.
    """
    def key(row):
        return (row["source"], row["source_indicator_id"], row["territory_code"], row["year"])

    def series(row):
        return (row.get("source", ""), row.get("source_indicator_id", ""))

    curated = set(curated_series)
    previous_by_series = {}
    merged = {}
    for row in existing:
        merged[key(row)] = row
        previous_by_series.setdefault(series(row), row)
    for row in new_rows:
        if series(row) in curated:
            reference = previous_by_series.get(series(row))
            if reference:
                row = {**row, **{
                    field: reference.get(field, "")
                    for field in CURATED_DATASET_FIELDS
                }}
        merged[key(row)] = row
    return sorted(
        merged.values(),
        key=lambda r: (r["target_indicator_id"], r.get("source_indicator_id", ""), r.get("territory_name", "")),
    )


def _curated_series(manifest_rows):
    """(source, source_indicator_id) for every series the curator has integrated."""
    return {
        (row.get("source", ""), row.get("source_indicator_id", ""))
        for row in manifest_rows
        if row.get("status") == "integrated" and row.get("source")
    }


def _merge_manifest(existing, new_entries):
    """Merge on the source series, exactly like the dataset.

    A source series has one current target: candidate_id is
    `<source>:<source_indicator_id>` and each candidate promotes to a single
    target. Including the target in the key meant a re-promotion after a human
    corrected `duplicate_of` in the review PR (the documented way a match is
    confirmed) moved the data rows to the new target but left the old entry
    behind, still claiming status=integrated for an indicator with no data."""
    def key(row):
        source, series = row.get("source", ""), row.get("source_indicator_id", "")
        if source or series:
            return ("series", source, series)
        # Placeholder entries carry no source (status=unavailable: no external
        # series exists for that indicator yet). They are one per target, so the
        # target is what identifies them.
        return ("target", row.get("target_indicator_id", ""))

    merged = {key(row): row for row in existing}
    for row in new_entries:
        merged[key(row)] = _keep_curation(merged.get(key(row)), row)
    return sorted(merged.values(), key=lambda r: r["target_indicator_id"])


# What the curator owns once an indicator is integrated. A re-promotion refreshes
# the data and the headline year; it must not undo the review. The two lists
# differ because the manifest and the dataset carry different reviewed fields,
# and app.external_atlas reads the *dataset* ones to build the score.
CURATED_FIELDS = ("direction", "score_eligible", "status", "review_notes")
CURATED_DATASET_FIELDS = ("direction", "score_eligible", "quality_life_category")


def _keep_curation(previous, entry):
    """Carry a completed curation across a re-promotion of the same series.

    Re-promoting is a normal operation: a data refresh adds a year, and a human
    correcting `duplicate_of` in the review PR retargets the rows. But the
    promoter fills the manifest from the *candidate*, so it wrote back the
    proposed direction, `score_eligible=false` and `status=proposed` over an
    entry the curator had already signed off. On `eur:rd_p_persreg`, which is
    integrated and score-eligible, one unscoped run would have dropped it out of
    the quality-of-life score with no error anywhere.

    So: refresh the data fields, keep the reviewed ones.
    """
    if not previous or previous.get("status") != "integrated":
        return entry
    return {**entry, **{field: previous.get(field, "") for field in CURATED_FIELDS}}


def _check_candidate_id(candidate):
    """The queue's stable key must stay `<source>:<source_indicator_id>`.

    The dataset merge is keyed on the source series, not on candidate_id, so a
    row whose id no longer matches its own source fields silently overwrites
    *another* candidate's series and retargets it: a live atlas entry can
    disappear from the catalog with no error. The queue is hand-edited in the
    review PR (that is where triage_status is set), so this is a plausible typo,
    and it must fail before anything is written."""
    expected = f"{candidate.get('source', '')}:{candidate.get('source_indicator_id', '')}"
    if candidate.get("candidate_id") != expected:
        raise SystemExit(
            f"{candidate.get('candidate_id')}: candidate_id does not match its own "
            f"source fields (expected '{expected}'). Promoting it would overwrite "
            "the series that owns that key. Fix the queue row."
        )


def _mark_promoted(candidates, promoted_ids):
    """Close the loop on the queue: approved -> promoted, written by the script.

    This used to be a manual edit in the review PR, and it was missed once:
    `eurostat_regional:rd_p_persreg` stayed `approved` while its manifest entry
    said `integrated`, so the queue and the manifest disagreed about what had
    already shipped and the next unscoped run re-promoted a live indicator.
    A step that has actually run should record that itself.
    """
    changed = False
    for candidate in candidates:
        if candidate.get("candidate_id") in promoted_ids and candidate.get("triage_status") != "promoted":
            candidate["triage_status"] = "promoted"
            changed = True
    if changed:
        discovery.write_candidates(candidates)


def run(offline=True, refresh=False, candidate_id=None,
        out_dataset=EXTERNAL_DATASET, out_manifest=EXTERNAL_MANIFEST, dry_run=False):
    candidates = discovery.read_candidates()
    approved = [
        c for c in candidates
        if c.get("triage_status") == "approved"
        and (candidate_id is None or c.get("candidate_id") == candidate_id)
    ]
    for candidate in approved:
        _check_candidate_id(candidate)
    dataset_rows, manifest_entries, summary = [], [], []
    for candidate in approved:
        rows, target, enriches, note = _external_rows_for(candidate, offline, refresh)
        dataset_rows.extend(rows)
        manifest_entries.append(_manifest_entry(candidate, target, enriches, note, rows))
        summary.append((candidate["candidate_id"], target, candidate["definition_match"], len(rows)))

    if not approved:
        return {"approved": 0, "dataset_rows": 0, "manifest_entries": 0, "summary": []}

    if not dry_run:
        existing_manifest = discovery.read_semicolon(out_manifest)
        merged_dataset = _merge_dataset(
            discovery.read_semicolon(out_dataset), dataset_rows,
            _curated_series(existing_manifest),
        )
        discovery.write_semicolon(merged_dataset, EXTERNAL_COLUMNS, out_dataset)
        merged_manifest = _merge_manifest(existing_manifest, manifest_entries)
        discovery.write_semicolon(merged_manifest, MANIFEST_COLUMNS, out_manifest)
        _mark_promoted(candidates, {c["candidate_id"] for c in approved})

    return {
        "approved": len(approved),
        "dataset_rows": len(dataset_rows),
        "manifest_entries": len(manifest_entries),
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--candidate-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(offline=args.offline, refresh=args.refresh,
                 candidate_id=args.candidate_id, dry_run=args.dry_run)
    if result["approved"] == 0:
        print("No approved candidates in the queue (set triage_status=approved to promote).")
        return
    verb = "Would promote" if args.dry_run else "Promoted"
    print(f"{verb} {result['approved']} candidate(s): "
          f"{result['dataset_rows']} dataset rows, {result['manifest_entries']} manifest entries.")
    for cid, target, match, count in result["summary"]:
        print(f"  {cid} -> target={target} ({match}, {count} rows)")


if __name__ == "__main__":
    main()
