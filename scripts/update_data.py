#!/usr/bin/env python3
"""Download and convert the current Istat territorial indicators dataset."""

from __future__ import annotations

import argparse
import csv
import io
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path


SOURCE_URL = (
    "https://www.istat.it/storage/politiche-sviluppo/"
    "Archivio_unico_indicatori_regionali.zip"
)

OUTPUT_COLUMNS = [
    "idIndicatore",
    "Territorio",
    "Tema",
    "Indicatore",
    "UDM",
    "Fonte",
    "Archivio",
    "Anno",
    "Livello/Variazione",
    "Dato",
    "Benchmark",
    "Area",
]

REGION_NAME_MAP = {
    "Valle d'Aosta/Vallée d'Aoste": "Valle d'Aosta",
    "Trentino-Alto Adige/Südtirol": "Trentino Alto Adige",
}

SUPPORTED_REGIONS = {
    "Abruzzo",
    "Basilicata",
    "Calabria",
    "Campania",
    "Emilia-Romagna",
    "Friuli-Venezia Giulia",
    "Lazio",
    "Liguria",
    "Lombardia",
    "Marche",
    "Molise",
    "Piemonte",
    "Puglia",
    "Sardegna",
    "Sicilia",
    "Toscana",
    "Trentino Alto Adige",
    "Umbria",
    "Valle d'Aosta",
    "Veneto",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_output_path() -> Path:
    return project_root() / "app" / "static" / "data" / "Assoluti_Regione.csv"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "diset-viz-data-updater/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def read_zip_csv(archive_bytes: bytes) -> csv.DictReader:
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    if len(csv_names) != 1:
        raise RuntimeError(f"Expected one CSV file in archive, found {len(csv_names)}")

    raw_file = archive.open(csv_names[0])
    text_file = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
    return csv.DictReader(text_file, delimiter=";")


def convert_row(row: dict[str, str]) -> dict[str, str] | None:
    territory = REGION_NAME_MAP.get(
        row["DESCRIZIONE_RIPARTIZIONE"],
        row["DESCRIZIONE_RIPARTIZIONE"],
    )
    if territory not in SUPPORTED_REGIONS:
        return None

    theme = row["DESCRIZIONE_TEMA1"] or row["OC_TEMA_SINTETICO"] or "Indicatori territoriali"
    archive = row["SOTTOTITOLO"] or row[" 1° OBIETTIVO"] or row["OC_TEMA_SINTETICO"]

    return {
        "idIndicatore": row["COD_INDICATORE"].lstrip("0") or "0",
        "Territorio": territory,
        "Tema": theme.strip(),
        "Indicatore": row["TITOLO"].strip(),
        "UDM": row["UNITA_MISURA"].strip(),
        "Fonte": "Istat",
        "Archivio": archive.strip(),
        "Anno": row["ANNO_RIFERIMENTO"].strip(),
        "Livello/Variazione": "Livello",
        "Dato": row["VALORE"].strip(),
        "Benchmark": "",
        "Area": "Regione",
    }


def write_atomic(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=output_path.parent,
    ) as tmp:
        writer = csv.DictWriter(
            tmp,
            fieldnames=OUTPUT_COLUMNS,
            delimiter=";",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        temp_name = tmp.name

    os.replace(temp_name, output_path)
    os.chmod(output_path, 0o644)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=SOURCE_URL, help="Source ZIP URL")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_path(),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archive_bytes = download(args.url)
    rows = [converted for row in read_zip_csv(archive_bytes) if (converted := convert_row(row))]

    if not rows:
        raise RuntimeError("No regional rows were converted")

    rows.sort(key=lambda row: (int(row["idIndicatore"]), row["Territorio"], int(row["Anno"])))
    write_atomic(rows, args.output)

    years = sorted({int(row["Anno"]) for row in rows})
    indicators = {row["idIndicatore"] for row in rows}
    regions = {row["Territorio"] for row in rows}
    print(
        f"Wrote {len(rows)} rows, {len(indicators)} indicators, "
        f"{len(regions)} regions, years {years[0]}-{years[-1]} to {args.output}"
    )


if __name__ == "__main__":
    main()
