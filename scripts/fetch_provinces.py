#!/usr/bin/env python3
"""Fetch provincial BES data from Istat SDMX, one query per BES domain.

This only warms the on-disk cache: the build step reads the same cached
responses. Resumable by construction (cached domains are skipped for free) and
rate-limited by the client (>= min_interval between network calls). A
`--max-requests` cap is an extra safety net against the 5/min IP ban.

    python scripts/fetch_provinces.py                  # all 12 BES domains
    python scripts/fetch_provinces.py --domains BES_01 # validate one domain first
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import istat_sdmx, province_sources  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--min-interval", type=float, default=16.0)
    parser.add_argument("--dataflow", default=province_sources.BES_DATAFLOW)
    parser.add_argument("--start", type=int, default=province_sources.BES_START_PERIOD)
    parser.add_argument("--domains", default="", help="Comma-separated BES domains (default: all 12)")
    parser.add_argument("--max-requests", type=int, default=20, help="Safety cap on network queries")
    return parser.parse_args()


def main():
    args = parse_args()
    domains = (
        [d.strip() for d in args.domains.split(",") if d.strip()]
        if args.domains
        else list(province_sources.BES_DOMAINS)
    )
    client = istat_sdmx.SdmxClient(cache_dir=args.cache_dir, min_interval=args.min_interval)

    total = len(domains)
    eta_min = (total * args.min_interval) / 60.0
    print(f"Fetching {total} BES domains from {args.dataflow} (start={args.start}). "
          f"Worst-case ~{eta_min:.1f} min at {args.min_interval:.0f}s/query.")

    for index, domain in enumerate(domains, start=1):
        if client.request_count >= args.max_requests:
            print(f"Reached --max-requests={args.max_requests}; stopping. Re-run to resume.")
            break
        key = province_sources.bes_key(domain)
        try:
            rows = client.data(args.dataflow, key=key, start=args.start)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print(f"  [{index}/{total}] {domain}: no data (HTTP 404), skipped")
                continue
            raise
        print(f"  [{index}/{total}] {domain}: {len(rows)} observations "
              f"(network queries so far: {client.request_count})")

    print(f"Done. Network queries used this run: {client.request_count}. "
          f"Cache: {args.cache_dir}")


if __name__ == "__main__":
    main()
