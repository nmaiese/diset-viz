#!/usr/bin/env python3
"""The writer's worklist: integrated indicators that still need an article.

Fase 4 (lo scrittore) was the only stage of the discovery chain with no automated
trigger. The hunter and the curator run as scheduled Routines, but nothing told
the writer which indicators the curator had just integrated and left without a
note, so `eur:rd_e_gerdreg` sat integrated and score-eligible with no prose. This
closes that gap deterministically, the way `curate.uncurated_targets` feeds the
curator. It reports two worklists:

  - **missing**: an indicator integrated in the manifest (status=integrated) with
    no article yet. This is the curator -> writer hand-off.
  - **stale**:   an article whose vintage is behind the indicator's current
    year_max, the refresh case the writer agent also handles (drift guard in
    tests/integration/test_indicator_texts.py).

This is the *discovery pipeline* trigger and stays scoped to the externally
sourced indicators the manifest tracks. For the editorial state of the whole
catalogue, including which of the four sections are still composed by the
template rather than written, use ``scripts/text_queue.py`` instead.

Stdlib pure, like its sibling discovery scripts: both the queue read and the
current year_max come from committed files (the manifest's ``new_year``), so the
scheduled writer needs no Flask app to know its worklist. This scopes stale
detection to the external/integrated indicators the manifest tracks, which is
exactly pending_notes' role as the discovery-pipeline trigger. year_max stays an
injected callable so the logic is unit-testable without any file at all.

    python3 scripts/pending_notes.py            # human + machine readable worklist
    python3 scripts/pending_notes.py --json      # JSON for an agent to consume
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Same pattern as promote_candidates/apply_curation/curate, so the CLI can import
# the shared discovery helpers when run as `python3 scripts/pending_notes.py`.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery, indicator_store  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "app" / "static" / "data" / "external_indicator_manifest.csv"


def read_manifest(path=None):
    return discovery.read_semicolon(path if path else MANIFEST_PATH)


def read_notes(root=None):
    """Gli articoli scritti. `root` e' una directory di store, non un file."""
    try:
        return indicator_store.load_all(root)
    except indicator_store.StoreError:
        return {}


def integrated_targets(manifest_rows):
    """Target ids the curator has integrated (status=integrated), de-duplicated,
    order preserved. A source series can appear more than once in the manifest;
    the writer works per atlas indicator, so we collapse to the target."""
    seen = []
    for row in manifest_rows:
        if row.get("status") == "integrated":
            target = row.get("target_indicator_id", "")
            if target and target not in seen:
                seen.append(target)
    return seen


# The four roles an article is made of, mirroring app/indicator_texts.ROLES.
# Stdlib-only module, so the list is copied rather than imported; the mirror is
# pinned by tests/unit/test_pending_notes.py.
ARTICLE_ROLES = ("definizione", "quadro", "dinamica", "limiti")


def unwritten_roles(entry):
    """The roles of an article that nobody has written yet.

    An entry can exist and still be half a page. The four-role rewrite made
    "has an entry" and "is written" two different things, and this script only
    knew the first: with both external indicators sitting at two sections out of
    four, it printed "la catena e completa" and the writer stage never fired.
    """
    if not isinstance(entry, dict):
        return list(ARTICLE_ROLES)
    written = {
        section.get("role")
        for section in entry.get("sections") or []
        if isinstance(section, dict) and (section.get("body") or "").strip()
    }
    return [role for role in ARTICLE_ROLES if role not in written]


def pending(manifest_rows, notes, year_max_of):
    """Return ``(missing, stale)`` worklists.

    ``year_max_of(key) -> int | None`` yields the indicator's current latest data
    year. ``missing`` is an integrated indicator whose article is absent or
    incomplete; ``stale`` is any existing note whose vintage has fallen behind
    that year (checked across all notes, not only integrated ones, because a note
    can drift for any family)."""
    missing = []
    for target in integrated_targets(manifest_rows):
        entry = notes.get(target)
        unwritten = unwritten_roles(entry)
        has_lead = bool((entry or {}).get("lead") if isinstance(entry, dict) else None)
        if not unwritten and has_lead:
            continue
        if entry is None:
            reason = "integrated senza articolo"
        else:
            gaps = ", ".join(unwritten) or "nessuna sezione"
            reason = f"articolo incompleto (mancano: {gaps}{'' if has_lead else ', +lead'})"
        missing.append({
            "id": target,
            "reason": reason,
            "year_max": year_max_of(target),
            "unwritten": unwritten,
            "lead": has_lead,
        })
    stale = []
    for key, note in notes.items():
        year_max = year_max_of(key)
        vintage = note.get("vintage")
        if isinstance(year_max, int) and isinstance(vintage, int) and year_max > vintage:
            stale.append({
                "id": key,
                "reason": "vintage della nota indietro rispetto ai dati",
                "vintage": vintage,
                "year_max": year_max,
            })
    return missing, stale


def manifest_year_max(manifest_rows):
    """``{target_indicator_id: latest year}`` from the manifest.

    Stdlib pure: the discovery pipeline records the series' latest year here, so
    the writer's trigger reads it straight from the committed manifest instead of
    importing the app. The year can live in ``new_year`` (a promotion) or only in
    ``current_year`` (an integrated indicator without a fresh promotion year, e.g.
    617/618/623/624), so we take the max of whichever columns are present.
    Reading only ``new_year`` would drop those targets and their notes could never
    enter the ``stale`` worklist. A row with neither contributes no year."""
    out = {}
    for row in manifest_rows:
        target = row.get("target_indicator_id", "")
        if not target:
            continue
        years = [
            int(value)
            for column in ("new_year", "current_year")
            if (value := (row.get(column) or "").strip()).isdigit()
        ]
        if years:
            out[target] = max(years)
    return out


def build_worklist(manifest_path=None, notes_root=None):
    manifest_rows = read_manifest(manifest_path)
    year_of = manifest_year_max(manifest_rows)
    return pending(manifest_rows, read_notes(notes_root), year_of.get)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the worklist as JSON")
    args = parser.parse_args()

    missing, stale = build_worklist()

    if args.json:
        print(json.dumps({"missing": missing, "stale": stale}, ensure_ascii=False, indent=2))
        return

    if not missing and not stale:
        print("Nessun indicatore in attesa di nota: la catena e completa.")
        return
    if missing:
        print(f"Da scrivere ({len(missing)}): indicatori integrati con l'articolo incompleto")
        for item in missing:
            print(f"  {item['id']:24s} year_max={item['year_max']}  ({item['reason']})")
    if stale:
        print(f"\nDa aggiornare ({len(stale)}): note col vintage indietro")
        for item in stale:
            print(f"  {item['id']:24s} vintage={item['vintage']} < year_max={item['year_max']}")


if __name__ == "__main__":
    main()
