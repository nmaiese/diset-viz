#!/usr/bin/env python3
"""List configured official external sources."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.external_sources import load_registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "csv"), default="text")
    args = parser.parse_args()
    rows = load_registry()

    if args.format == "csv":
        fieldnames = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        return

    for row in rows:
        enabled = "enabled" if row.get("enabled") else "disabled"
        print(f"{row['source']}: {row['dataset']} ({enabled})")
        print(f"  levels: {', '.join(row.get('territory_levels', []))}")
        print(f"  parser: {row.get('parser')} | landing: {row.get('landing_page')}")


if __name__ == "__main__":
    main()
