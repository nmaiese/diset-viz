#!/usr/bin/env python3
"""Discover candidate Istat SDMX dataflows for provincial (NUTS3) data.

Cheap by design so it respects the 5-query/min Istat limit:

- the dataflow list is ONE query (cached afterwards);
- DSD + territory-codelist inspection is opt-in (`--inspect` / `--inspect-shortlist`),
  one or two queries per dataflow, so you can validate connectivity and parsing on
  a single cheap call before spending budget.

Outputs (under data/provincia/):
- dataflows.csv        all IT1 dataflows (id, version, name)
- shortlist.csv        dataflows whose name hints at provincial/BES/territorial data
- manifest_candidates.json   for inspected dataflows: dimensions, territory
                       dimension, number of NUTS3-looking codes, sample codes

Typical use:
    python scripts/discover_provinces.py                 # 1 query: list + shortlist
    python scripts/discover_provinces.py --inspect-shortlist --max-inspect 8
    python scripts/discover_provinces.py --inspect 92_123,DCIS_POPRES1
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import istat_sdmx  # noqa: E402  (after sys.path bootstrap)

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"
DEFAULT_OUT = PROJECT_ROOT / "data" / "provincia"

# Name/id hints for provincial or BES-territorial dataflows.
SHORTLIST_PATTERNS = re.compile(
    r"\b(bes|benessere|territori|provinc|nuts|ripartiz|comun)", re.IGNORECASE
)
# Codelist ids that carry the Italian territory hierarchy (incl. NUTS3 provinces).
TERRITORY_CODELIST_HINT = re.compile(r"(ITTER|TERRIT|REF_AREA|REGIO|PROV)", re.IGNORECASE)
# NUTS3 province codes look like ITC11, ITF33, ITH10... (IT + letter + 2 digits).
NUTS3_PATTERN = re.compile(r"^IT[A-Z]\d{2}$")


def _codelist_id(urn):
    match = re.search(r"Codelist=[^:]+:([^()]+)\(", urn or "")
    return match.group(1) if match else ""


def write_dataflows_csv(flows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["id", "version", "name"])
        for flow in sorted(flows, key=lambda f: f["id"]):
            writer.writerow([flow["id"], flow["version"], flow["name"]])


def shortlist(flows):
    return [f for f in flows if SHORTLIST_PATTERNS.search(f"{f['id']} {f['name']}")]


def inspect_dataflow(client, flow):
    """Fetch DSD + territory codelist for one dataflow; summarise it."""
    dsd_id = _dsd_id_from_structure(flow["dsd"]) or flow["id"]
    dsd = client.datastructure(dsd_id)
    dimensions = dsd.get("dimensions", [])
    territory_dim = None
    for dim in dimensions:
        if TERRITORY_CODELIST_HINT.search(dim["id"]) or TERRITORY_CODELIST_HINT.search(
            _codelist_id(dim["codelist"])
        ):
            territory_dim = dim
            break

    summary = {
        "dataflow": flow["id"],
        "name": flow["name"],
        "dsd": dsd_id,
        "dimensions": [d["id"] for d in dimensions],
        "territory_dimension": territory_dim["id"] if territory_dim else None,
        "territory_codelist": _codelist_id(territory_dim["codelist"]) if territory_dim else None,
        "nuts3_count": 0,
        "nuts3_sample": [],
    }

    if territory_dim and summary["territory_codelist"]:
        codelist = client.codelist(summary["territory_codelist"])
        nuts3 = [c for c in codelist["codes"] if NUTS3_PATTERN.match(c)]
        summary["nuts3_count"] = len(nuts3)
        summary["nuts3_sample"] = [
            {"code": c, "name": codelist["codes"][c]["name"]} for c in sorted(nuts3)[:5]
        ]
    return summary


def _dsd_id_from_structure(urn):
    match = re.search(r"DataStructure=[^:]+:([^()]+)\(", urn or "")
    return match.group(1) if match else ""


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--min-interval", type=float, default=16.0)
    parser.add_argument("--inspect", default="", help="Comma-separated dataflow ids to inspect")
    parser.add_argument("--inspect-shortlist", action="store_true", help="Inspect the shortlist")
    parser.add_argument("--max-inspect", type=int, default=8, help="Cap on dataflows to inspect")
    parser.add_argument(
        "--dump-codelists",
        default="",
        help="Comma-separated codelist ids to fetch and dump as CSV (code;name)",
    )
    parser.add_argument("--no-dataflows", action="store_true", help="Skip the dataflow list step")
    return parser.parse_args()


def dump_codelist(client, codelist_id, out_dir):
    codelist = client.codelist(codelist_id)
    path = out_dir / f"codelist_{codelist_id}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["code", "name", "parent"])
        for code in codelist["codes"].values():
            writer.writerow([code["id"], code["name"], code.get("parent") or ""])
    print(f"  {codelist_id}: {len(codelist['codes'])} codes -> {path.name}")


def main():
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    client = istat_sdmx.SdmxClient(cache_dir=args.cache_dir, min_interval=args.min_interval)

    flows = []
    if not args.no_dataflows:
        print("Fetching dataflow list (1 query if not cached)...")
        flows = client.dataflows()
        write_dataflows_csv(flows, args.out_dir / "dataflows.csv")
        short = shortlist(flows)
        write_dataflows_csv(short, args.out_dir / "shortlist.csv")
        print(f"{len(flows)} dataflows total, {len(short)} shortlisted -> {args.out_dir}")

    if args.dump_codelists:
        print("Dumping codelists...")
        for codelist_id in (x.strip() for x in args.dump_codelists.split(",") if x.strip()):
            dump_codelist(client, codelist_id, args.out_dir)

    to_inspect = []
    if args.inspect:
        wanted = {x.strip() for x in args.inspect.split(",") if x.strip()}
        to_inspect = [f for f in flows if f["id"] in wanted]
    elif args.inspect_shortlist:
        to_inspect = short[: args.max_inspect]

    if to_inspect:
        print(f"Inspecting {len(to_inspect)} dataflows (DSD + territory codelist each)...")
        summaries = []
        for flow in to_inspect:
            try:
                summary = inspect_dataflow(client, flow)
            except Exception as exc:  # noqa: BLE001 - record and continue
                summary = {"dataflow": flow["id"], "name": flow["name"], "error": str(exc)}
            summaries.append(summary)
            tag = summary.get("nuts3_count", "err")
            print(f"  {flow['id']:24} nuts3={tag}  {flow['name'][:60]}")
        out = args.out_dir / "manifest_candidates.json"
        out.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")

    print(f"Network queries used this run: {client.request_count}")


if __name__ == "__main__":
    main()
