#!/usr/bin/env python3
"""Cache metadata for one configured external source.

Network downloads are intentionally source-specific. Until a parser is promoted
from fixture mode, this command writes a reproducible fetch marker and refuses to
pretend that data was downloaded.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.external_sources import PROJECT_ROOT, source_by_id


RAW_DIR = PROJECT_ROOT / "data" / "external" / "raw"
CACHE_DIR = PROJECT_ROOT / "data" / "external" / "cache"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--level", default="")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = source_by_id(args.source)
    if source is None:
        raise SystemExit(f"Unknown source: {args.source}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    marker = CACHE_DIR / f"{args.source}_{args.year}_fetch.json"
    payload = {
        "source": args.source,
        "year": args.year,
        "level": args.level,
        "offline": args.offline,
        "refresh": args.refresh,
        "max_requests": args.max_requests,
        "dry_run": args.dry_run,
        "parser": source.get("parser"),
        "landing_page": source.get("landing_page"),
        "download_url": source.get("download_url"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "status": "metadata_only",
        "notes": "No network data fetched unless a promoted parser exists for this source.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    marker.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {marker}")


if __name__ == "__main__":
    main()
