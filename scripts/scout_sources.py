#!/usr/bin/env python3
"""The scout: propose NEW institutional sources, not just new indicators.

The hunter (scripts/discover_candidates.py) discovers indicators inside sources
that are already on the allowlist (config/external_sources.yaml). The scout sits
one level up: it reads the Istat SDMX dataflow catalogue and proposes regional
dataflows that are **not yet covered** by any allowlisted source or curated
adapter, so a human can decide whether to admit a genuinely new domain (health,
justice, environment, culture, transport, ...) to the allowlist.

Gate, deliberately: the scout writes ONLY to data/discovery/source_candidates.csv
(a reviewable queue). It never edits config/external_sources.yaml. Admitting a
domain to the allowlist is a human merge; wiring its hunter adapter is a later
step. This is the same PR-gated discipline as the indicator hunter, one rung up.

Catalogue-level by design: the proposal uses only the dataflow list (one cached
query, shared with scripts/discover_provinces.py) plus name signals. It does not
spend a data query per dataflow to measure freshness or coverage, so it stays
cheap against the Istat 5-queries/minute limit; the human confirms a proposal
before any adapter fetches its data. Pure stdlib.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discover_provinces, istat_regional_source, istat_sdmx, multiscopo_sources
from scripts.external_sources import load_registry

SOURCE_CANDIDATES_PATH = PROJECT_ROOT / "data" / "discovery" / "source_candidates.csv"
CACHE_DIR = PROJECT_ROOT / "data" / "istat_cache"

COLUMNS = [
    "candidate_id",      # istat_sdmx:<dataflow_id>, stable
    "discovered_at",
    "source_kind",       # istat_sdmx (the catalogue this came from)
    "dataflow_id",
    "name",
    "territory_hint",    # regione | territoriale (name-level guess only)
    "priority_score",    # 0..1, catalogue-level name signal
    "reason",
    "triage_status",     # new -> approved / rejected / needs-info (human, in PR)
    "triage_notes",
]

# A dataflow name that names the regional/territorial breakdown. Regional is the
# priority; broader territorial names still qualify (a human sets the level).
REGIONAL_HINT = re.compile(r"\b(region|ripartiz|nuts2)", re.IGNORECASE)
# Provincial/municipal-only breakdowns are allowed but ranked lower (the project
# prioritises regional, then provincial).
SUBREGIONAL_HINT = re.compile(r"\b(provinc|comun|nuts3)", re.IGNORECASE)
# Generic words that carry no domain signal, so they never count as "already
# covered" when matched against the allowlist.
STOPWORDS = {
    "indicatori", "indicatore", "dati", "dato", "per", "del", "della", "delle",
    "dei", "degli", "regione", "regioni", "regionale", "regionali", "provincia",
    "province", "provinciale", "provinciali", "nazionale", "italia", "istat",
    "rilevazione", "rilevazioni", "statistiche", "statistica", "sistema",
    "annuale", "annuali", "trimestrale", "trimestrali", "mensile", "mensili",
    "sesso", "eta", "totale", "and", "the", "regional", "statistics", "nuts",
    "sostenibile", "equo", "ripartizione", "ripartizioni", "ripartizionale",
    "livello", "dalla", "grezzi", "grezze", "destagionalizzati", "base", "valori",
    "valore", "classi", "classe", "tipo", "comune", "comuni", "numero",
    "standardizzati", "approfondimenti", "condizione", "professionale", "durata",
    "frequenze", "saldi", "clima", "climi",
}

# Dataflows that are metadata/lookup tables, not indicators. Never proposed.
METADATA_NAME = re.compile(
    r"corrispondenz|codice e|nome della|classificazion|metadat|bulk", re.IGNORECASE
)
# SDMX family codes of allowlisted domains whose terse dataflow names ("Dati
# regionali - durata della disoccupazione") do not reveal the domain to the
# name-token dedup. Forze di Lavoro (istat_lavoro) is the notable case.
ALLOWLIST_FAMILY_HINT = re.compile(r"TAXOCCU|TAXDISOCCU|DISOCCUP|FORZLV|NEET", re.IGNORECASE)


def _norm(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _tokens(text):
    return {t for t in re.split(r"[^a-z0-9]+", _norm(text)) if len(t) > 3 and t not in STOPWORDS}


def covered_flow_ids():
    """Dataflow ids already consumed by a curated adapter, so never re-proposed."""
    ids = {spec["flow_id"] for spec in multiscopo_sources.MULTISCOPO_INDICATORS}
    ids.add(istat_regional_source.DATAFLOW)
    return ids


def _family(flow_id):
    """Istat survey family of a dataflow id: the first two tokens after 'DF_'
    (e.g. '83_63_DF_DCCV_AVQ_PERSONE_141' -> 'DCCV_AVQ'). Used to exclude a whole
    already-integrated survey (Multiscopo AVQ) instead of only its exact flows,
    so the scout does not re-propose new *indicators* of a known source as if
    they were a new *source*."""
    match = re.search(r"DF_([A-Z0-9]+(?:_[A-Z0-9]+)?)", flow_id or "")
    return match.group(1) if match else ""


def covered_families(covered=None):
    covered = covered if covered is not None else covered_flow_ids()
    return {_family(flow_id) for flow_id in covered if _family(flow_id)}


def allowlist_terms(registry=None):
    """Distinctive domain tokens already represented on the allowlist, from each
    source's dataset name and id (generic words stripped)."""
    registry = registry if registry is not None else load_registry()
    terms = set()
    for source in registry:
        terms |= _tokens(source.get("dataset", ""))
        terms |= _tokens((source.get("source", "") or "").replace("_", " "))
    return terms


def propose_sources(flows, covered=None, terms=None, limit=40):
    """Pure ranking: which catalogue dataflows to propose as new sources.

    A dataflow is proposed when its name names a regional/territorial breakdown,
    its id is not already covered by a curated adapter, and its domain tokens do
    not overlap an allowlisted source (so already-admitted domains, like labour
    or demography, are not re-proposed). One proposal per distinct name."""
    covered = covered if covered is not None else covered_flow_ids()
    families = covered_families(covered)
    terms = terms if terms is not None else allowlist_terms()
    seen_names = set()
    proposals = []
    for flow in flows:
        name = flow.get("name") or ""
        blob = f"{flow.get('id', '')} {name}"
        if not REGIONAL_HINT.search(blob):
            continue
        if METADATA_NAME.search(name):
            continue
        if ALLOWLIST_FAMILY_HINT.search(flow.get("id", "")):
            continue
        if flow.get("id") in covered or _family(flow.get("id", "")) in families:
            continue
        domain = _tokens(name)
        if not domain or domain & terms:
            continue  # domain already represented on the allowlist
        key = _norm(name)
        if key in seen_names:
            continue
        seen_names.add(key)
        regional = bool(REGIONAL_HINT.search(name))
        subregional = bool(SUBREGIONAL_HINT.search(blob))
        score = 0.6 + (0.3 if regional else 0.0) - (0.2 if subregional and not regional else 0.0)
        proposals.append({
            "dataflow_id": flow.get("id", ""),
            "name": name,
            "territory_hint": "regione" if regional else "territoriale",
            "priority_score": round(min(max(score, 0.0), 1.0), 2),
            "reason": (
                "Dataflow territoriale non coperto da fonti in allowlist ne da adapter "
                "curati; dominio nuovo per il catalogo. Da verificare a mano: livello "
                "regionale, freschezza, copertura e licenza prima di ammetterlo."
            ),
        })
    proposals.sort(key=lambda p: (-p["priority_score"], p["name"]))
    return proposals[:limit]


def to_rows(proposals, now=None):
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    rows = []
    for p in proposals:
        rows.append({
            "candidate_id": f"istat_sdmx:{p['dataflow_id']}",
            "discovered_at": stamp,
            "source_kind": "istat_sdmx",
            "dataflow_id": p["dataflow_id"],
            "name": p["name"],
            "territory_hint": p["territory_hint"],
            "priority_score": p["priority_score"],
            "reason": p["reason"],
            "triage_status": "new",
            "triage_notes": "",
        })
    return rows


def read_source_candidates(path=SOURCE_CANDIDATES_PATH):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def upsert(existing, fresh):
    """Merge fresh proposals over the queue, preserving any human triage already
    recorded for a candidate (status and notes are never overwritten)."""
    by_id = {row["candidate_id"]: dict(row) for row in existing}
    for row in fresh:
        prior = by_id.get(row["candidate_id"])
        if prior and prior.get("triage_status") not in ("", "new", None):
            merged = dict(row)
            merged["triage_status"] = prior["triage_status"]
            merged["triage_notes"] = prior.get("triage_notes", "")
            by_id[row["candidate_id"]] = merged
        else:
            by_id[row["candidate_id"]] = row
    return sorted(by_id.values(), key=lambda r: (-float(r["priority_score"]), r["name"]))


def write_source_candidates(rows, path=SOURCE_CANDIDATES_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _load_flows(offline, cache_dir):
    client = istat_sdmx.SdmxClient(cache_dir=str(cache_dir), cache_only=offline)
    return client.dataflows()


def run(offline=True, cache_dir=CACHE_DIR, limit=40, path=SOURCE_CANDIDATES_PATH):
    flows = _load_flows(offline, cache_dir)
    proposals = propose_sources(flows, limit=limit)
    merged = upsert(read_source_candidates(path), to_rows(proposals))
    write_source_candidates(merged, path)
    return proposals, merged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="use only the cached dataflow catalogue")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true", help="print proposals, do not write the queue")
    args = parser.parse_args()

    flows = _load_flows(args.offline, CACHE_DIR)
    proposals = propose_sources(flows, limit=args.limit)
    if args.dry_run:
        for p in proposals:
            print(f"{p['priority_score']:.2f}  {p['territory_hint']:<12} {p['dataflow_id']:<28} {p['name']}")
        print(f"\n{len(proposals)} proposte (dry-run, nulla scritto).")
        return
    merged = upsert(read_source_candidates(), to_rows(proposals))
    write_source_candidates(merged)
    print(f"Scritte {len(proposals)} proposte in {SOURCE_CANDIDATES_PATH} (coda ora: {len(merged)}).")


if __name__ == "__main__":
    main()
