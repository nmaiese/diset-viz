#!/usr/bin/env python3
"""Refresh the two official regional backbones and record source fingerprints.

The command is idempotent: when the remote artifact hashes have not changed it
does not touch committed files.  When they do change, both datasets are rebuilt
atomically and a compact, reviewable source-state/report pair is updated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import update_bes_regions, update_data  # noqa: E402


STATE_PATH = PROJECT_ROOT / "data" / "source_state.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "official_data_refresh.md"
ATLAS_OUTPUT = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
BES_OUTPUT = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_BES_Regione.csv"
BES_MANIFEST = PROJECT_ROOT / "app" / "static" / "data" / "bes_regione_manifest.csv"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _load_state(path=STATE_PATH):
    if not Path(path).exists():
        return {"version": 1, "sources": {}}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _atlas_rows(archive_bytes):
    rows = [
        converted
        for raw in update_data.read_zip_csv(archive_bytes)
        if (converted := update_data.convert_row(raw))
    ]
    if not rows:
        raise RuntimeError("No regional atlas rows converted")
    refreshed_ids = {row["idIndicatore"] for row in rows}
    preserved = update_data.read_preserved_rows(ATLAS_OUTPUT, refreshed_ids)
    rows.extend(preserved)
    rows.sort(key=lambda row: (int(row["idIndicatore"]), row["Territorio"], int(row["Anno"])))
    return rows, len(preserved)


def _manifest_summary(rows):
    years = Counter(int(row["year_max"]) for row in rows)
    return {
        "indicator_count": len(rows),
        "current_indicator_count": sum(year >= 2025 for year in years.elements()),
        "latest_year": max(years) if years else None,
        "year_distribution": {str(year): count for year, count in sorted(years.items())},
    }


def _atlas_summary(rows, preserved_count):
    latest = {}
    for row in rows:
        indicator_id = row["idIndicatore"]
        latest[indicator_id] = max(latest.get(indicator_id, 0), int(row["Anno"]))
    years = Counter(latest.values())
    return {
        "row_count": len(rows),
        "indicator_count": len(latest),
        "preserved_row_count": preserved_count,
        "current_indicator_count": sum(year >= 2025 for year in latest.values()),
        "latest_year": max(latest.values()),
        "year_distribution": {str(year): count for year, count in sorted(years.items())},
    }


def _write_report(state, atlas_summary, bes_summary):
    atlas = state["sources"]["istat_indicatori_territoriali"]
    bes = state["sources"]["istat_bes_regioni"]
    lines = [
        "# Monitoraggio fonti dati ufficiali",
        "",
        "Questo file viene aggiornato solo quando cambia almeno un artefatto ufficiale.",
        "",
        "## Stato integrato",
        "",
        f"- Atlante regionale: {atlas_summary['indicator_count']} indicatori, "
        f"{atlas_summary['current_indicator_count']} con ultimo anno 2025 o 2026, "
        f"massimo {atlas_summary['latest_year']}.",
        f"- Qualità della vita regionale: {bes_summary['indicator_count']} indicatori BES "
        f"con dati regionali, {bes_summary['current_indicator_count']} al 2025, "
        f"massimo {bes_summary['latest_year']}.",
        "- Province: restano sul BES dei Territori 2025 finché Istat non pubblica la nuova edizione.",
        "",
        "## Artefatti monitorati",
        "",
        "| fonte | URL | ultima modifica HTTP | sha256 |",
        "|---|---|---|---|",
        f"| Indicatori territoriali Istat | {atlas['url']} | {atlas.get('last_modified') or '-'} | `{atlas['sha256']}` |",
        f"| BES nazionale, regioni | {bes['url']} | {bes.get('last_modified') or '-'} | `{bes['sha256']}` |",
        "",
        "## Regole automatiche",
        "",
        "- Un hash diverso avvia la rigenerazione dei dataset e dei manifest.",
        "- I test bloccano schema, copertura, direzioni e regressioni del punteggio.",
        "- Il workflow apre una pull request: i cambi di definizione o copertura non entrano in produzione senza una revisione leggibile.",
        "- Le serie non confrontabili restano contestuali e non entrano nello scoring.",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--atlas-input", type=Path)
    parser.add_argument("--bes-input", type=Path)
    parser.add_argument("--atlas-url", default=update_data.SOURCE_URL)
    parser.add_argument("--bes-artifact-url", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.atlas_input:
        atlas_bytes = args.atlas_input.read_bytes()
        atlas_meta = {"url": str(args.atlas_input), "etag": "", "last_modified": ""}
    else:
        atlas_bytes, atlas_meta = update_bes_regions.download_artifact(args.atlas_url)

    if args.bes_input:
        bes_bytes = args.bes_input.read_bytes()
        bes_meta = {"url": str(args.bes_input), "etag": "", "last_modified": ""}
    else:
        bes_url = args.bes_artifact_url or update_bes_regions.discover_artifact_url()
        bes_bytes, bes_meta = update_bes_regions.download_artifact(bes_url)

    state = _load_state()
    new_sources = {
        "istat_indicatori_territoriali": {
            **atlas_meta,
            "bytes": len(atlas_bytes),
            "sha256": _sha256(atlas_bytes),
        },
        "istat_bes_regioni": {
            **bes_meta,
            "bytes": len(bes_bytes),
            "sha256": _sha256(bes_bytes),
        },
    }
    old_sources = state.get("sources", {})
    changed = [
        source_id for source_id, info in new_sources.items()
        if old_sources.get(source_id, {}).get("sha256") != info["sha256"]
    ]
    print(json.dumps({"changed": changed, "sources": new_sources}, ensure_ascii=False))
    if args.check_only or not changed:
        return

    atlas_rows, preserved_count = _atlas_rows(atlas_bytes)
    bes_rows, bes_manifest = update_bes_regions.parse_archive(bes_bytes)
    update_data.write_atomic(atlas_rows, ATLAS_OUTPUT)
    update_bes_regions._write_atomic(bes_rows, update_data.OUTPUT_COLUMNS, BES_OUTPUT)
    update_bes_regions._write_atomic(
        bes_manifest, update_bes_regions.MANIFEST_COLUMNS, BES_MANIFEST
    )

    state = {"version": 1, "sources": new_sources}
    atlas_summary = _atlas_summary(atlas_rows, preserved_count)
    bes_summary = _manifest_summary(bes_manifest)
    state["sources"]["istat_indicatori_territoriali"]["dataset"] = atlas_summary
    state["sources"]["istat_bes_regioni"]["dataset"] = bes_summary
    _write_json(STATE_PATH, state)
    _write_report(state, atlas_summary, bes_summary)


if __name__ == "__main__":
    main()
