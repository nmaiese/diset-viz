#!/usr/bin/env python3
"""The hunter: watchlist discovery over configured sources.

Runs the curated adapters, classifies each discovered indicator against the
committed regional series, scores it, and upserts it into the discovery queue
(data/discovery/candidates.csv). It never touches live data. A scheduled Claude
Code agent runs this, then reviews the queue and opens a PR (see
docs/DISCOVERY_PIPELINE.md).

    python3 scripts/discover_candidates.py --source eurostat_regional --offline
    python3 scripts/discover_candidates.py --source eurostat_regional        # live, cache-first
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery, eurostat_source, istat_regional_source  # noqa: E402


# Failures collected by the last survey: [(series_id, message)]. Read by the CLI
# and by whoever calls run(), so a series that could not be fetched is reported
# rather than silently missing from the queue.
FAILURES = []


def _survey(series_ids, fetch):
    """Fetch every series, and let one broken series cost only itself.

    This used to be a list comprehension, which meant the first exception ended
    the whole scan. That was survivable while the series lived in a Python module
    that only a human edited. It stopped being survivable when the scout started
    writing rows into `config/istat_series.yaml` on its own: one wrong code, and
    every following run of the hunter died on a traceback, discovering nothing
    from any source, for as long as nobody read the log.

    A failure is not swallowed either. It goes into FAILURES, gets printed, and
    an empty result is an error exit: "found nothing" and "could not look" must
    not look the same from outside.
    """
    rows = []
    for series_id in series_ids:
        try:
            rows.append(fetch(series_id))
        except Exception as error:  # noqa: BLE001 - any source failure, one series
            FAILURES.append((series_id, f"{type(error).__name__}: {error}"))
    return rows


# source id -> callable(offline, refresh) -> list[raw candidate dict]
def _eurostat_watchlist(offline, refresh):
    return _survey(
        eurostat_source.EUROSTAT_SERIES,
        lambda sid: eurostat_source.discover(sid, offline=offline, refresh=refresh),
    )


def _istat_demografia_watchlist(offline, refresh):
    return _survey(
        istat_regional_source.ISTAT_SERIES,
        lambda sid: istat_regional_source.discover(sid, offline=offline, refresh=refresh),
    )


WATCHLIST = {
    "eurostat_regional": _eurostat_watchlist,
    "istat_demografia": _istat_demografia_watchlist,
}


def _enrich(raw, existing_index, mode):
    definition_match, duplicate_of = discovery.classify_definition_match(
        raw["name"], existing_index
    )
    candidate = {
        "candidate_id": discovery.candidate_id(raw["source"], raw["source_indicator_id"]),
        "discovered_at": raw.get("updated", ""),
        "discovery_mode": mode,
        "source": raw["source"],
        "source_dataset": raw["source_dataset"],
        "source_indicator_id": raw["source_indicator_id"],
        "name": raw["name"],
        "territory_level": raw["territory_level"],
        "year_max": raw["year_max"],
        "coverage": raw["coverage"],
        "unit": raw["unit"],
        "proposed_theme": raw["proposed_theme"],
        "proposed_quality_life_category": raw["proposed_quality_life_category"],
        "proposed_direction": raw["proposed_direction"],
        "definition_match": definition_match,
        "duplicate_of": duplicate_of,
        "freshness_status": discovery.freshness_status(raw["year_max"] or None),
        "source_url": raw["source_url"],
        "license": raw["license"],
        "triage_status": "new",
        "triage_notes": "",
    }
    candidate["priority_score"] = discovery.priority_score(candidate)
    return candidate


def run(source, offline=True, refresh=False, mode="watchlist"):
    if source not in WATCHLIST:
        raise SystemExit(
            f"Unknown source '{source}'. Configured: {', '.join(sorted(WATCHLIST))}"
        )
    FAILURES.clear()
    existing_index = discovery.build_existing_index()
    discovered = [_enrich(raw, existing_index, mode) for raw in WATCHLIST[source](offline, refresh)]
    merged = discovery.upsert_candidates(discovery.read_candidates(), discovered)
    discovery.write_candidates(merged)
    return discovered, merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="eurostat_regional")
    parser.add_argument("--offline", action="store_true", help="read committed fixtures, no network")
    parser.add_argument("--refresh", action="store_true", help="ignore cache, refetch live")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        existing_index = discovery.build_existing_index()
        discovered = [
            _enrich(raw, existing_index, "watchlist")
            for raw in WATCHLIST[args.source](args.offline, args.refresh)
        ]
        for cand in sorted(discovered, key=lambda c: -c["priority_score"]):
            print(
                f"{cand['priority_score']:.3f}  {cand['definition_match']:<11} "
                f"{cand['freshness_status']:<8} {cand['year_max']:<6} "
                f"cov={cand['coverage']}  {cand['name']}"
            )
        return

    discovered, merged = run(args.source, offline=args.offline, refresh=args.refresh)
    print(f"Discovered {len(discovered)} candidate(s) from {args.source}.")
    print(f"Queue now holds {len(merged)} candidate(s): {discovery.CANDIDATES_PATH}")
    for series_id, message in FAILURES:
        print(f"  SERIE NON LETTA  {series_id}: {message}", file=sys.stderr)
    if FAILURES and not discovered:
        # Nessuna serie letta. Uscire con zero direbbe all'agente "scansionato,
        # niente di nuovo", che e' la cosa piu' sbagliata da fargli credere.
        raise SystemExit(f"nessuna serie leggibile da {args.source}")


if __name__ == "__main__":
    main()
