"""Refresh locale dei dati ufficiali, da eseguire a mano come gli altri passi
della pipeline (promote, curate, apply). Sostituisce il workflow GitHub rimosso:
stessi passi, ma il diff resta da revisionare a mano, senza commit ne' PR
automatici.

Uso, dalla radice del repo:
    bin/py scripts/refresh_official_local.py            # controlla e integra
    bin/py scripts/refresh_official_local.py --check    # solo controllo, non scrive

ATTENZIONE: limite Istat SDMX. update_multiscopo_regions interroga Istat dal
vivo. Istat impone 5 richieste al minuto per IP: oltre, blocca l'IP per 1-2
giorni. Il client spazia le chiamate di 16s e i flussi distinti sono 14, quindi
una singola esecuzione sta dentro il limite. Non lanciare due refresh in
parallelo e non forzare --refresh se non serve.

Le strutture SDMX (dataflow, DSD, codelist) restano in cache senza scadenza; le
risposte dati scadono da sole dopo sei giorni (DATA_MAX_AGE). In locale le mtime
dei file di cache sono reali, quindi la scadenza funziona senza --refresh-data:
passa REFRESH_DATA=1 solo se vuoi forzare comunque il riscaricamento dei dati.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str) -> None:
    """Esegue un passo con lo stesso interprete di questo script; si ferma al primo errore."""
    proc = subprocess.run(list(args), cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main(argv: list[str]) -> int:
    py = sys.executable

    if argv[:1] == ["--check"]:
        print(">> Controllo hash delle fonti ufficiali (nessuna scrittura)")
        run(py, "scripts/refresh_official_data.py", "--check-only")
        return 0

    multi_flags = ["--refresh-data"] if os.environ.get("REFRESH_DATA") == "1" else []

    print(">> Backbone territoriale e BES")
    run(py, "scripts/refresh_official_data.py")

    print(">> Multiscopo regionale (Istat SDMX, cache-first)")
    run(py, "scripts/update_multiscopo_regions.py", *multi_flags)

    unchanged = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0
    if unchanged:
        print(">> Nessun cambiamento nei dati ufficiali: niente da rigenerare.")
    else:
        print(">> Dati cambiati: rigenero il layer esterno e l'audit")
        run(py, "scripts/build_external_dataset.py", "--source", "all", "--year", "2025")
        run(py, "scripts/audit_external_indicators.py")

    print(">> Verifica: test backend e build frontend")
    run(py, "-m", "unittest", "discover", "-s", "tests")
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("refresh: npm non trovato nel PATH")
    run(npm, "--prefix", "frontend", "run", "build")

    print()
    print(">> Fatto. Rivedi il diff prima di committare:")
    print("     git diff --stat")
    print("   Controlla cambi di definizione, copertura o direzione, poi committa a mano.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
