#!/usr/bin/env bash
#
# Refresh locale dei dati ufficiali, da eseguire a mano come gli altri passi
# della pipeline (promote, curate, apply). Sostituisce il workflow GitHub
# rimosso: stessi passi, ma il diff resta da revisionare a mano, senza commit
# ne' PR automatici.
#
# Uso, dalla radice del repo:
#     scripts/refresh_official_local.sh            # controlla e integra
#     scripts/refresh_official_local.sh --check    # solo controllo, non scrive
#
# ATTENZIONE — limite Istat SDMX. update_multiscopo_regions interroga Istat dal
# vivo. Istat impone 5 richieste al minuto per IP: oltre, blocca l'IP per 1-2
# giorni. Il client spazia le chiamate di 16s e i flussi distinti sono 14,
# quindi una singola esecuzione sta dentro il limite. Non lanciare due refresh
# in parallelo e non forzare --refresh se non serve.
#
# Le strutture SDMX (dataflow, DSD, codelist) restano in cache senza scadenza;
# le risposte dati scadono da sole dopo sei giorni (DATA_MAX_AGE). In locale le
# mtime dei file di cache sono reali, quindi la scadenza funziona senza
# --refresh-data: passa REFRESH_DATA=1 solo se vuoi forzare comunque il
# riscaricamento dei dati.
set -euo pipefail

cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

if [ "${1:-}" = "--check" ]; then
  echo ">> Controllo hash delle fonti ufficiali (nessuna scrittura)"
  "$PY" scripts/refresh_official_data.py --check-only
  exit 0
fi

MULTI_FLAGS=()
[ "${REFRESH_DATA:-0}" = "1" ] && MULTI_FLAGS+=(--refresh-data)

echo ">> Backbone territoriale e BES"
"$PY" scripts/refresh_official_data.py

echo ">> Multiscopo regionale (Istat SDMX, cache-first)"
"$PY" scripts/update_multiscopo_regions.py "${MULTI_FLAGS[@]}"

if git diff --quiet; then
  echo ">> Nessun cambiamento nei dati ufficiali: niente da rigenerare."
else
  echo ">> Dati cambiati: rigenero il layer esterno e l'audit"
  "$PY" scripts/build_external_dataset.py --source all --year 2025
  "$PY" scripts/audit_external_indicators.py
fi

echo ">> Verifica: test backend e build frontend"
"$PY" -m unittest discover -s tests
npm --prefix frontend run build

echo
echo ">> Fatto. Rivedi il diff prima di committare:"
echo "     git diff --stat"
echo "   Controlla cambi di definizione, copertura o direzione, poi committa a mano."
