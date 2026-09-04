#!/usr/bin/env python3
"""Read-only audit: do the already-downloaded Istat sources hold more
dimension data (sex, secondary theme) than the converters currently read?

Downloads the same two archives scripts/update_data.py and
scripts/update_bes_regions.py already fetch, and reports what their
converters leave on the floor: unread columns, rows dropped by the
territory filter, and (for the historical catalogue) a cross-check of the
title-suffix heuristic against Istat's own gender-breakdown tag.

Written for docs/FAMIGLIE_INDICATORI.md (Settimana 3-4, passo a), after
Nello asked whether the sources already acquired had more of this than we
were using. Does not touch any file under app/static/data: report only.
"""

from __future__ import annotations

import csv
import io
import re
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.update_data import REGION_NAME_MAP, SOURCE_URL, SUPPORTED_REGIONS  # noqa: E402
from scripts.update_bes_regions import FALLBACK_ARTIFACT as BES_URL  # noqa: E402

# Columns scripts/update_data.py:convert_row actually reads.
CATALOGO_COLONNE_USATE = {
    "COD_INDICATORE", "TITOLO", "SOTTOTITOLO", "ANNO_RIFERIMENTO",
    "UNITA_MISURA", "VALORE", "DESCRIZIONE_RIPARTIZIONE",
    "DESCRIZIONE_TEMA1", "OC_TEMA_SINTETICO", " 1° OBIETTIVO",
}

TAG_GENERE = "Asse VII - Articolazione di genere."

GENERE_SUFFIX_RE = re.compile(
    r"""(?:\s*\(\s*(?P<g1>maschi|femmine|totale)\s*\)\s*$
          |\s*[-,]\s*(?P<g2>maschi|femmine|totale)\s*$
          |\s+(?P<g3>maschi|femmine|totale)\s*$)""",
    re.IGNORECASE | re.VERBOSE,
)


def _scarica(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "diset-viz-audit/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def audit_catalogo_storico() -> None:
    print("=" * 70)
    print("CATALOGO STORICO (Assoluti_Regione.csv, fonte BDTPS)")
    print("=" * 70)
    archive = zipfile.ZipFile(io.BytesIO(_scarica(SOURCE_URL)))
    csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
    with archive.open(csv_names[0]) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text, delimiter=";")
        header = reader.fieldnames or []
        non_usate = [c for c in header if c not in CATALOGO_COLONNE_USATE]
        print(f"\nColonne nel CSV Istat: {len(header)}, lette da convert_row: "
              f"{len(CATALOGO_COLONNE_USATE)}, mai lette: {len(non_usate)}")
        print(f"  {non_usate}")

        ripartizioni = Counter()
        tema2 = set()
        genere_ids = set()
        titolo_per_id = {}
        n_righe = 0
        for row in reader:
            n_righe += 1
            ripartizioni[row["DESCRIZIONE_RIPARTIZIONE"]] += 1
            if row["DESCRIZIONE_TEMA2"].strip():
                tema2.add(row["DESCRIZIONE_TEMA2"].strip())
            territorio = REGION_NAME_MAP.get(
                row["DESCRIZIONE_RIPARTIZIONE"], row["DESCRIZIONE_RIPARTIZIONE"]
            )
            if territorio in SUPPORTED_REGIONS:
                iid = row["COD_INDICATORE"].lstrip("0") or "0"
                titolo_per_id[iid] = row["TITOLO"].strip()
                if row["DESCRIZIONE_ASSE_QCS"].strip() == TAG_GENERE:
                    genere_ids.add(iid)

    tenute = sum(v for k, v in ripartizioni.items()
                 if REGION_NAME_MAP.get(k, k) in SUPPORTED_REGIONS)
    print(f"\nRighe totali: {n_righe}, tenute (20 regioni): {tenute}, "
          f"scartate per territorio: {n_righe - tenute}")
    for k, v in sorted(ripartizioni.items(), key=lambda x: -x[1]):
        if REGION_NAME_MAP.get(k, k) not in SUPPORTED_REGIONS:
            print(f"  scartato: {k!r}: {v} righe")

    print(f"\nDESCRIZIONE_TEMA2 (seconda classificazione, mai letta): "
          f"{len(tema2)} valori -> {sorted(tema2)}")
    print(f"\nIndicatori taggati {TAG_GENERE!r} (ufficiale Istat, mai letto): "
          f"{len(genere_ids)} su {len(titolo_per_id)}")

    regex_mf = set()
    for iid, titolo in titolo_per_id.items():
        m = GENERE_SUFFIX_RE.search(titolo)
        if m:
            g = (m.group("g1") or m.group("g2") or m.group("g3")).lower()
            if g in ("maschi", "femmine"):
                regex_mf.add(iid)
    solo_regex = regex_mf - genere_ids
    solo_tag = genere_ids - regex_mf
    esito = "combaciano" if not solo_regex and not solo_tag else "DISCREPANZE"
    print(f"Regex sui titoli vs tag ufficiale: {len(solo_regex)} solo regex, "
          f"{len(solo_tag)} solo tag -> {esito}")


def audit_bes() -> None:
    print()
    print("=" * 70)
    print("BES (Assoluti_BES_Regione.csv, fonte Appendice Statistica)")
    print("=" * 70)
    with zipfile.ZipFile(io.BytesIO(_scarica(BES_URL))) as archive:
        xlsx_names = [n for n in archive.namelist() if n.lower().endswith(".xlsx")]
        print(f"\nFile Excel nello ZIP: {len(xlsx_names)}")
        for n in xlsx_names:
            usato = "usato" if Path(n).name.lower() == "indicatori_regione_sesso.xlsx" else "mai aperto"
            print(f"  {n} [{usato}]")

        target = next(n for n in xlsx_names if Path(n).name.lower() == "indicatori_regione_sesso.xlsx")
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            tmp.write(archive.read(target))
            tmp.flush()
            wb = load_workbook(tmp.name, read_only=True, data_only=True)
            sheet = wb.active
            rows = sheet.iter_rows(values_only=True)
            header = next(rows)
            pos = {v: i for i, v in enumerate(header)}

            sesso_counter = Counter()
            ids_per_sesso = defaultdict(set)
            territori = set()
            for values in rows:
                sesso = str(values[pos["SESSO"]] or "").strip()
                sesso_counter[sesso] += 1
                ids_per_sesso[sesso].add(str(values[pos["CODICE"]] or "").strip())
                territori.add(str(values[pos["TERRITORIO"]] or "").strip())
            wb.close()

    print(f"\nRighe per SESSO: {dict(sesso_counter)}")
    tot = ids_per_sesso.get("Totale", set())
    masch = ids_per_sesso.get("Maschi", set())
    femm = ids_per_sesso.get("Femmine", set())
    print(f"Indicatori con tripletta Totale+Maschi+Femmine: {len(tot & masch & femm)}")
    print(f"Indicatori Totale-only nella fonte: {len(tot - masch - femm)}")
    print(f"Righe scartate dal filtro 'solo Totale': "
          f"{sesso_counter.get('Maschi', 0) + sesso_counter.get('Femmine', 0)}")
    print(f"Territori oltre le 20 regioni (scartati): "
          f"{sorted(territori - SUPPORTED_REGIONS)}")


if __name__ == "__main__":
    audit_catalogo_storico()
    audit_bes()
