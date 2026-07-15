# Freschezza dati

Ogni indicatore esposto dal catalogo riceve metadati di freschezza:

- `year_max`
- `source`
- `retrieved_at`, quando disponibile dal layer esterno
- `freshness_status`

Classificazione:

- `current`: anno massimo dal 2025 in poi
- `recent`: anno massimo dal 2023
- `dated`: anno massimo dal 2020
- `stale`: anno massimo prima del 2020

I badge sono visibili nelle pagine indicatore, nei profili regionali e nella
qualità della vita. Sono segnali informativi, non modificano ordinamenti,
normalizzazioni o score.

## Audit

Rigenera i report con:

```bash
.venv/bin/python scripts/build_external_dataset.py --source istat_demografia --year 2025
.venv/bin/python scripts/audit_external_indicators.py
```

Output:

- `reports/indicator_inventory.csv`: inventario completo richiesto per audit,
  con id, nome, livello territoriale, categoria, direzione, unità, ultimo anno,
  fonte e uso in atlante/profili/scoring.
- `reports/data_freshness_2025.csv`: matrice operativa di aggiornabilità.
- `reports/data_freshness_2025.md`: riepilogo leggibile con decisioni e fonti.
- `app/static/data/external_indicator_manifest.csv`: manifest consumato dal sito.

## Decisioni attuali

- Integrati nel layer esterno: indicatori demografici Istat regionali 2025/2026
  già presenti nel dataset locale.
- Non integrati automaticamente: lavoro, INVALSI, Movimprese, turismo, Terna e
  Infratel. Sono fonti candidate o `needs_review` fino a verifica di definizione,
  unità, copertura e licenza.
- Demografia strutturale, fecondità e saldi migratori restano contestuali o
  descrittivi, salvo motivazione metodologica esplicita.
