"""Download the official definition of every Istat territorial indicator.

The chain has always compared the *figures* in an article against the series.
Nothing compared the *definition*, and that is the hole the second batch of
rewrites walked into: `ter-402` called "imprese a guida femminile" what Istat
defines as women holding sole proprietorships, and repeated it in the `limiti`
section, which is the one place meant to say what the indicator does not
measure. A wrong figure dies at the first reader who opens the brief. A wrong
definition survives every reading that looks at numbers, because the numbers
are right.

Istat publishes those definitions in the `Metadati` sheet of
`Metainformazione.xls`, next to the archive that `scripts/update_data.py`
already downloads. This normalizes that sheet into a CSV under version control,
so `scripts/definition_check.py` and every agent that writes or reads an article
can be held to the source without a network call.

    python3 scripts/fetch_definitions.py                 # scarica e riscrive il CSV
    python3 scripts/fetch_definitions.py --dry-run       # dice solo che cosa cambierebbe
    python3 scripts/fetch_definitions.py --from-file Metainformazione.xls

This fetcher owns only the native territorial sheet. BES, Multiscopo, Eurostat,
demographic indicators and the local territorial additions publish their
definitions elsewhere and in other shapes; the companion
`scripts/fetch_federated_definitions.py` normalizes those into the second CSV
that `load_definitions()` merges automatically.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.xls_reader import XlsError, read_sheets, sheet_rows  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.istat.it/storage/politiche-sviluppo/Metainformazione.xls"
SHEET = "Metadati"
OUTPUT_PATH = PROJECT_ROOT / "data" / "definitions" / "istat_territoriali.csv"
FEDERATED_OUTPUT_PATH = PROJECT_ROOT / "data" / "definitions" / "federated.csv"

COLUMNS = [
    "id",
    "indicatore",
    "definizione",
    "dati_di_base",
    "unita_territoriale",
    "anno_iniziale",
    "anno_finale",
    "periodicita",
    "fonti",
    "note",
]

# The header row of the sheet, mapped to our column names. Matched on the exact
# label rather than on a position: Istat has moved these columns before, and a
# silent off-by-one would publish the wrong definition under the right code,
# which is worse than no definition at all.
HEADER_MAP = {
    "CODICE": "id",
    "INDICATORE": "indicatore",
    "DEFINIZIONE TECNICA INDICATORE": "definizione",
    "DATI DI BASE ASSOCIATI": "dati_di_base",
    "AMBITO TERRITORIALE": "unita_territoriale",
    "ANNO INIZIALE": "anno_iniziale",
    "ANNO FINALE": "anno_finale",
    "PERIODICITA'": "periodicita",
    "FONTI": "fonti",
    "NOTE": "note",
}

# The upstream file has been through a Latin-1 round trip and lost every curly
# apostrophe and quotation mark to U+00BF, 102 times. `¿` never occurs in
# Italian, so restoring it is unambiguous: between two letters it was an
# apostrophe ("sull¿acqua"), anywhere else it opened or closed a quotation
# ("el commercio¿ è divenuto").
MOJIBAKE_APOSTROPHE = re.compile(r"(?<=\w)¿(?=\w)")


def _clean(value: object) -> str:
    text = "" if value is None else str(value)
    text = MOJIBAKE_APOSTROPHE.sub("'", text).replace("¿", '"')
    return re.sub(r"\s+", " ", text).strip()


def _code(value: object) -> str:
    """The indicator id as the rest of the project writes it.

    The sheet zero-pads to three digits (`060`) and the archive CSV strips the
    padding (`60`), so a join on the raw cell matches nothing at all. Numeric
    cells arrive as floats through the reader, hence the `.0` too.
    """
    text = _clean(value)
    if text.endswith(".0"):
        text = text[:-2]
    text = text.lstrip("0")
    return text if text.isdigit() else ""


def _year(value: object) -> str:
    text = _clean(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text if re.fullmatch(r"\d{4}", text) else ""


def parse_sheet(rows: list[list[object]]) -> list[dict[str, str]]:
    """The `Metadati` grid as one row per indicator, keyed by our column names."""
    header_index = None
    for index, row in enumerate(rows[:20]):
        labels = {_clean(cell).upper() for cell in row}
        if "CODICE" in labels and "DEFINIZIONE TECNICA INDICATORE" in labels:
            header_index = index
            break
    if header_index is None:
        raise XlsError(
            "no header row in the %r sheet: Istat changed the layout, "
            "check HEADER_MAP before trusting anything downstream" % SHEET
        )

    header = [_clean(cell).upper() for cell in rows[header_index]]
    positions: dict[str, int] = {}
    for position, label in enumerate(header):
        name = HEADER_MAP.get(label)
        if name and name not in positions:
            positions[name] = position

    missing = [name for name in ("id", "indicatore", "definizione") if name not in positions]
    if missing:
        raise XlsError(f"the {SHEET!r} sheet has no column for {', '.join(missing)}")

    out: dict[str, dict[str, str]] = {}
    for row in rows[header_index + 1:]:
        code = _code(row[positions["id"]]) if positions["id"] < len(row) else ""
        if not code:
            # `060_P` and `472_C` are the provincial and municipal cuts of an
            # indicator whose regional cut is `060`. This project's provincial
            # pages come from Istat BES dei Territori and are keyed differently
            # (`docs/PROVINCE_PIPELINE.md`), so those rows have no page to check
            # and are ignored rather than kept.
            continue
        record = {"id": code}
        for name, position in positions.items():
            if name == "id":
                continue
            value = row[position] if position < len(row) else ""
            record[name] = _year(value) if name.startswith("anno_") else _clean(value)
        for name in COLUMNS:
            record.setdefault(name, "")
        # Last row wins, and the sheet has no duplicates today. Keeping the last
        # rather than the first means a hypothetical corrected re-entry beats the
        # stale one, which is the direction an errata would go.
        out[code] = record
    return [out[code] for code in sorted(out, key=int)]


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "diset-viz-definitions/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def write_atomic(
    records: list[dict[str, str]], path: Path, columns: list[str] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", delete=False, dir=path.parent
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns or COLUMNS, delimiter=";", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(records)
        temporary = handle.name
    os.replace(temporary, path)
    os.chmod(path, 0o644)


def _load_csv(target: Path) -> dict[str, dict[str, str]]:
    if not target.exists():
        return {}
    with target.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle, delimiter=";")}


def load_definitions(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Committed source definitions, keyed by the editorial store id.

    An explicit path remains a single-file test/CLI seam.  The normal loader
    merges the historical territorial sheet with the federated archive.  The
    latter uses namespaced ids (``bes:*``, ``multiscopo:*``, ``dem:*``,
    ``eur:*``), plus the few local territorial ids absent upstream, so the two
    files cannot silently overwrite the same definition.
    """
    if path is not None:
        return _load_csv(Path(path))
    definitions = _load_csv(OUTPUT_PATH)
    federated = _load_csv(FEDERATED_OUTPUT_PATH)
    overlap = sorted(set(definitions) & set(federated))
    if overlap:
        raise ValueError(
            "Definition ids occur in both committed archives: " + ", ".join(overlap)
        )
    definitions.update(federated)
    return definitions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", default=SOURCE_URL)
    parser.add_argument("--from-file", type=Path, help="un .xls gia' scaricato")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--dry-run", action="store_true",
                        help="non scrive, dice solo quante righe cambierebbero")
    args = parser.parse_args(argv)

    try:
        raw = args.from_file.read_bytes() if args.from_file else download(args.url)
        sheets = read_sheets(raw)
        if SHEET not in sheets:
            raise XlsError(
                f"no {SHEET!r} sheet (found {', '.join(sheets) or 'nothing'})"
            )
        records = parse_sheet(sheet_rows(sheets[SHEET]))
    except XlsError as error:
        print(f"errore: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"errore di rete: {error}", file=sys.stderr)
        return 1

    if not records:
        print("errore: il foglio non ha prodotto nessuna definizione", file=sys.stderr)
        return 1

    previous = load_definitions(args.output)
    added = [r["id"] for r in records if r["id"] not in previous]
    changed = [
        r["id"] for r in records
        if r["id"] in previous and previous[r["id"]]["definizione"] != r["definizione"]
    ]
    gone = sorted(set(previous) - {r["id"] for r in records}, key=int)

    print(f"{len(records)} definizioni dal foglio {SHEET}")
    print(f"  nuove          {len(added)}  {', '.join(added[:12])}")
    print(f"  ridefinite     {len(changed)}  {', '.join(changed[:12])}")
    print(f"  sparite        {len(gone)}  {', '.join(gone[:12])}")

    if args.dry_run:
        return 0

    write_atomic(records, args.output)
    print(f"scritto {args.output.relative_to(PROJECT_ROOT)}")
    if changed:
        print("una definizione riscritta invalida gli articoli che la descrivono: "
              "python3 scripts/definition_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
