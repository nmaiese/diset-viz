# Freschezza dati

Ogni indicatore territoriale esposto dal catalogo riceve metadati di freschezza:

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

Il catalogo pubblico include anche tutti gli indicatori BES regionali con id
`bes:*`, anno massimo, copertura e fonte Istat. Il filtro `Fonte dati` permette di
isolarli nell'Atlante. Questa esposizione descrittiva non cambia la regola più
restrittiva applicata al punteggio della qualità della vita.

La classifica regionale applica una regola più forte del badge: dal 2026 usa
solo indicatori BES con anno di riferimento 2025 o successivo. La classifica
provinciale resta sull'ultima edizione disponibile del BES dei Territori e ne
dichiara l'anno senza fingere un aggiornamento che Istat non ha pubblicato.

## Audit

Rigenera i report con:

```bash
.venv/bin/python scripts/build_external_dataset.py --source all --year 2025
.venv/bin/python scripts/audit_external_indicators.py
.venv/bin/python scripts/refresh_official_data.py --check-only
```

Output:

- `reports/indicator_inventory.csv`: inventario completo richiesto per audit,
  con id, nome, livello territoriale, categoria, direzione, unità, ultimo anno,
  fonte e uso in atlante/profili/scoring.
- `reports/data_freshness_2025.csv`: matrice operativa di aggiornabilità.
- `reports/data_freshness_2025.md`: riepilogo leggibile con decisioni e fonti.
- `app/static/data/external_indicator_manifest.csv`: manifest consumato dal sito.

## Decisioni attuali

- Integrati nel layer esterno: indicatori demografici Istat regionali 2025/2026 e
  indicatori Istat lavoro regionali 2025 già presenti nel dataset locale
  aggiornato.
- Integrato nella qualità della vita regionale: BES nazionale, aggiornamento
  intermedio 2026. Comprende 67 serie regionali al 2025, incluse misure INVALSI,
  sicurezza, salute, povertà, acqua e copertura internet.
- Movimprese, turismo, Terna e Infratel restano candidati o `needs_review` fino a
  verifica di definizione, unità, copertura e licenza.
- Demografia strutturale, fecondità e saldi migratori restano contestuali o
  descrittivi, salvo motivazione metodologica esplicita.
