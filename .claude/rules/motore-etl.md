---
paths:
  - "**/scripts/update_*.py"
  - "**/scripts/refresh_*.py"
  - "**/ingest/**"
  - "**/facts/**"
---

# Ingest e fatti

- Gli snapshot non si sovrascrivono: ogni fetch aggiunge una riga con `fetched_at` e `source_hash` (sha256 del payload). La riga più recente è quella corrente, le precedenti restano.
- Quando `source_hash` cambia, i contenuti che dipendono da quei `fact_id` entrano nella coda di refresh: l'ingest scrive la coda, non tocca i contenuti.
- Ogni fatto ha `fact_id, value, unit, period, territory, source_url, source_hash, fetched_at`. Un fatto senza `source_url` non si registra.
- I parser sono deterministici e testati su un campione salvato in `tests/fixtures/`; un cambio di formato della fonte deve far fallire un test, non passare in silenzio.
- Le fonti hanno limiti di rate: si rispettano con attesa esplicita e cache su disco (vedi `scripts/istat_sdmx.py` in diset-viz), non con retry aggressivi.
