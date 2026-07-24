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
import csv
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery, eurostat_source  # noqa: E402

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
# genuinely new series becomes a standalone atlas entry under the "eur:" public
# id namespace, wired into the federated catalog by app/eurostat_atlas.py.
ENRICHING_MATCHES = {"exact", "compatible", "proxy"}


def _target_id(candidate):
    """The catalog id the promoted rows attach to.

    `duplicate_of` comes from discovery.build_existing_index and is already
    family-qualified ("bes:10AMB014", "multiscopo:...", or a bare numeric id for
    the territorial family, which owns the unprefixed namespace). Anything else
    would name an indicator that does not exist, so it is refused here rather
    than written into the external layer."""
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
    return f"eur:{candidate['source_indicator_id']}"


def _is_known_target(target):
    prefixes = tuple(p for p in discovery.FAMILY_PREFIX.values() if p)
    return target.startswith(prefixes) or target.isdigit()


def _bool(value):
    return "true" if value else "false"


def _external_rows_for(candidate, offline, refresh):
    if candidate["source"] != "eurostat_regional":
        raise SystemExit(f"No promotion parser for source '{candidate['source']}'")
    series_id = candidate["source_indicator_id"]
    rows = eurostat_source.normalized_rows(series_id, offline=offline, refresh=refresh)
    target = _target_id(candidate)
    enriches = candidate["definition_match"] in ENRICHING_MATCHES and bool(candidate.get("duplicate_of"))
    note = (
        "Eurostat NUTS2 arricchisce un indicatore esistente. Nessuna sostituzione BES/atlas."
        if enriches
        else "Voce d'atlante Eurostat autonoma (namespace eur:). Fuori dallo scoring finche la direzione non e revisionata a mano."
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


def _read_semicolon(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _write_semicolon(rows, columns, path):
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


def _merge_dataset(existing, new_rows):
    def key(row):
        return (row["source"], row["source_indicator_id"], row["territory_code"], row["year"])
    merged = {key(row): row for row in existing}
    for row in new_rows:
        merged[key(row)] = row
    return sorted(
        merged.values(),
        key=lambda r: (r["target_indicator_id"], r.get("source_indicator_id", ""), r.get("territory_name", "")),
    )


def _merge_manifest(existing, new_entries):
    def key(row):
        return (row["target_indicator_id"], row.get("source", ""), row.get("source_indicator_id", ""))
    merged = {key(row): row for row in existing}
    for row in new_entries:
        merged[key(row)] = row
    return sorted(merged.values(), key=lambda r: r["target_indicator_id"])


def run(offline=True, refresh=False, candidate_id=None,
        out_dataset=EXTERNAL_DATASET, out_manifest=EXTERNAL_MANIFEST, dry_run=False):
    candidates = discovery.read_candidates()
    approved = [
        c for c in candidates
        if c.get("triage_status") == "approved"
        and (candidate_id is None or c.get("candidate_id") == candidate_id)
    ]
    dataset_rows, manifest_entries, summary = [], [], []
    for candidate in approved:
        rows, target, enriches, note = _external_rows_for(candidate, offline, refresh)
        dataset_rows.extend(rows)
        manifest_entries.append(_manifest_entry(candidate, target, enriches, note, rows))
        summary.append((candidate["candidate_id"], target, candidate["definition_match"], len(rows)))

    if not approved:
        return {"approved": 0, "dataset_rows": 0, "manifest_entries": 0, "summary": []}

    if not dry_run:
        merged_dataset = _merge_dataset(_read_semicolon(out_dataset), dataset_rows)
        _write_semicolon(merged_dataset, EXTERNAL_COLUMNS, out_dataset)
        merged_manifest = _merge_manifest(_read_semicolon(out_manifest), manifest_entries)
        _write_semicolon(merged_manifest, MANIFEST_COLUMNS, out_manifest)

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
