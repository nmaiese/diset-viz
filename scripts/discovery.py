#!/usr/bin/env python3
"""Discovery queue: the staging layer in front of the external data pipeline.

This module is the "discarica revisionabile" the hunter agent writes to. It is
pure stdlib on purpose (like scripts/istat_sdmx.py): the discovery step must run
in a lightweight scheduled agent session without the Flask app or its
dependencies.

Flow (see docs/DISCOVERY_PIPELINE.md):

    hunter (watchlist) --> data/discovery/candidates.csv --> human review (PR)
                                                          --> promote_candidates.py

Nothing here touches live data. The queue is committed to git so every proposal
is auditable in a pull request before it can reach the normalized external layer.
"""

from __future__ import annotations

import csv
import os
import re
import tempfile
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = PROJECT_ROOT / "data" / "discovery"
CANDIDATES_PATH = DISCOVERY_DIR / "candidates.csv"

# Public id namespace per family. A mirror of app/sources.py `internal_prefix`,
# copied rather than imported because this module is stdlib-only (same reason
# promote_candidates.py duplicates the external-layer columns): keep in sync.
FAMILY_PREFIX = {
    "territorial": "",
    "bes": "bes:",
    "multiscopo": "multiscopo:",
}

# Committed regional backbones used to detect whether a discovered indicator is
# genuinely new or overlaps an existing series. Read as raw CSV (no app import).
# Each carries its family: raw ids are only unique *inside* a family, so an id
# without one ("104") does not say which indicator it means.
EXISTING_NAME_SOURCES = [
    ("territorial", PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"),
    ("bes", PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_BES_Regione.csv"),
    ("multiscopo", PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Multiscopo_Regione.csv"),
]


def public_id(family, raw_id):
    """Family-qualified catalog id, the same one app/sources.py builds."""
    return f"{FAMILY_PREFIX[family]}{raw_id}"

CANDIDATE_COLUMNS = [
    "candidate_id",            # stable key: "<source>:<source_indicator_id>"
    "discovered_at",           # provenance timestamp (source 'updated' when known)
    "discovery_mode",          # watchlist | scouting
    "source",                  # registry id, or "proposed:<domain>" in scouting
    "source_dataset",
    "source_indicator_id",
    "name",
    "territory_level",         # regione (priority) | provincia
    "year_max",                # most recent year with sufficient coverage
    "coverage",                # share of the 20 regions (or 107 province) covered
    "unit",
    "proposed_theme",
    "proposed_quality_life_category",
    "proposed_direction",      # higher_better | lower_better | higher_worse | contextual
    "definition_match",        # new | compatible | proxy | different  (never "exact": humans confirm)
    "duplicate_of",            # best-matching existing indicator id, if any
    "freshness_status",        # current | recent | dated | stale | unknown
    "priority_score",          # 0..1, fresh + regional + coverage + novelty
    "source_url",
    "license",
    "triage_status",           # new | approved | rejected | needs-info | promoted
    "triage_notes",
]

# triage_status values the hunter must never overwrite: they carry human review.
HUMAN_TRIAGE = {"approved", "rejected", "needs-info", "promoted"}

# Data fields the hunter refreshes even on an already-reviewed candidate (the
# world moves: a newer year or better coverage should still show up), while the
# triage decision itself is preserved.
REFRESHABLE_FIELDS = [
    "discovered_at", "source_dataset", "name", "territory_level", "year_max",
    "coverage", "unit", "proposed_theme", "proposed_quality_life_category",
    "proposed_direction", "definition_match", "duplicate_of", "freshness_status",
    "priority_score", "source_url", "license",
]


def freshness_status(year):
    """Kept in sync with app.external_data.freshness_status (stdlib copy)."""
    if year is None:
        return "unknown"
    try:
        year = int(year)
    except (TypeError, ValueError):
        return "unknown"
    if year >= 2025:
        return "current"
    if year >= 2023:
        return "recent"
    if year >= 2020:
        return "dated"
    return "stale"


def candidate_id(source, source_indicator_id):
    return f"{source}:{source_indicator_id}"


_FRESHNESS_WEIGHT = {"current": 1.0, "recent": 0.7, "dated": 0.4, "stale": 0.1, "unknown": 0.0}
_LEVEL_WEIGHT = {"regione": 1.0, "provincia": 0.6}
# Novelty: a genuinely new dimension adds most; an overlap still adds freshness.
_NOVELTY_WEIGHT = {"new": 1.0, "compatible": 0.8, "different": 0.6, "proxy": 0.5, "exact": 0.4}


def priority_score(candidate):
    """0..1 ranking that encodes the product rule: prefer fresh, regional,
    well-covered and genuinely additive indicators. Provincial and stale series
    still surface, just lower in the queue."""
    fresh = _FRESHNESS_WEIGHT.get(candidate.get("freshness_status", "unknown"), 0.0)
    level = _LEVEL_WEIGHT.get(candidate.get("territory_level", ""), 0.3)
    try:
        cov = float(candidate.get("coverage") or 0.0)
    except (TypeError, ValueError):
        cov = 0.0
    cov = max(0.0, min(1.0, cov))
    novelty = _NOVELTY_WEIGHT.get(candidate.get("definition_match", "new"), 0.6)
    score = 0.40 * fresh + 0.20 * level + 0.20 * cov + 0.20 * novelty
    return round(score, 4)


def normalize_name(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    return set(token for token in re.split(r"[^a-z0-9]+", value) if len(token) > 2)


def build_existing_index(sources=EXISTING_NAME_SOURCES):
    """[(public_id, name, token_set)] for every committed regional series.

    The id is family-qualified ("bes:10AMB014", "multiscopo:...", or the bare
    numeric id for the territorial family, which owns the unprefixed namespace).
    A duplicate match has to name one indicator unambiguously: downstream,
    promote_candidates.py uses it as the target the candidate enriches."""
    seen = set()
    index = []
    for family, path in sources:
        if not Path(path).exists():
            continue
        with Path(path).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                key = (row.get("idIndicatore"), row.get("Indicatore"))
                if key in seen or not key[1]:
                    continue
                seen.add(key)
                index.append((public_id(family, key[0]), key[1], normalize_name(key[1])))
    return index


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def classify_definition_match(name, existing_index):
    """Heuristic overlap check against existing series. Deliberately conservative:
    the hunter never claims "exact" (that is the only auto-substitute case in
    DATA_PIPELINE.md and must be confirmed by a human in the PR). Returns
    (definition_match, duplicate_of)."""
    tokens = normalize_name(name)
    best_id, best = "", 0.0
    for indicator_id, _, existing_tokens in existing_index:
        score = _jaccard(tokens, existing_tokens)
        if score > best:
            best, best_id = score, indicator_id
    if best >= 0.55:
        return "compatible", best_id
    if best >= 0.35:
        return "proxy", best_id
    return "new", ""


def read_candidates(path=None):
    # Resolve CANDIDATES_PATH at call time (not as a default) so tests can
    # redirect the queue by reassigning the module attribute.
    path = Path(path) if path else CANDIDATES_PATH
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_candidates(rows, path=None):
    path = Path(path) if path else CANDIDATES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda r: (-_as_float(r.get("priority_score")), r.get("candidate_id", "")),
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=path.parent
    ) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=CANDIDATE_COLUMNS, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for row in ordered:
            writer.writerow({col: row.get(col, "") for col in CANDIDATE_COLUMNS})
        temp_name = tmp.name
    os.replace(temp_name, path)
    os.chmod(path, 0o644)


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def upsert_candidates(existing, discovered):
    """Merge freshly discovered candidates into the existing queue by
    candidate_id. A candidate a human already triaged keeps its decision and
    notes; only its data fields are refreshed. New candidates default to
    triage_status='new'."""
    by_id = {row.get("candidate_id"): dict(row) for row in existing}
    for cand in discovered:
        cid = cand["candidate_id"]
        cand.setdefault("triage_status", "new")
        cand.setdefault("triage_notes", "")
        current = by_id.get(cid)
        if current is None:
            by_id[cid] = cand
            continue
        if current.get("triage_status") in HUMAN_TRIAGE:
            for field in REFRESHABLE_FIELDS:
                current[field] = cand.get(field, current.get(field, ""))
        else:
            merged = dict(cand)
            merged["triage_status"] = current.get("triage_status", "new")
            merged["triage_notes"] = current.get("triage_notes", "")
            by_id[cid] = merged
    return list(by_id.values())
