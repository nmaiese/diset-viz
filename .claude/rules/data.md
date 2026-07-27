---
paths:
  - "app/static/data/**"
  - "config/**"
  - "data/**"
---

# Dati: indicatori, temi, province

Il documento che possiede la materia e'
[`docs/DATA_PIPELINE.md`](../../docs/DATA_PIPELINE.md); per le province,
[`docs/PROVINCE_PIPELINE.md`](../../docs/PROVINCE_PIPELINE.md); per freschezza
e monitoraggio delle fonti, [`docs/DATA_FRESHNESS.md`](../../docs/DATA_FRESHNESS.md)
e [`docs/SOURCE_MONITORING.md`](../../docs/SOURCE_MONITORING.md).

- Temi, punteggi, profili regionali e macro-aree sono **derivati** e ricalcolati
  a runtime. Per ogni indicatore nuovo: il verso in `CURATED_DIRECTION`
  (`app/indicator_notes.py`). Per ogni tema nuovo: una riga in
  `config/theme_categories.csv` verso una delle 12 categorie canoniche. Le
  categorie e le quattro macro-aree vivono in `app/taxonomy.py` e inventarne
  una e' codice, non dati.
- **Un tema non mappato e' il guasto silenzioso da conoscere**: l'indicatore
  resta nel catalogo e sparisce da ogni totale di macro-area, senza che niente
  fallisca.
- Dopo un cambio dati: **riavvia gunicorn** (i loader usano `lru_cache`, non un
  TTL), ricompila il frontend se serve, rilancia la suite, ricontrolla quali
  temi sono "valutabili".
- Province separate dalle regioni: la cache SDMX resta fuori da git, si
  committano solo i CSV normalizzati, e mai righe provinciali dentro il CSV
  regionale o `app/data.py`.
