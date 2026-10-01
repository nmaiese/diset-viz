# RICERCA INDICATORI NUOVI (Divario Italia) - SOLO RICERCA
Report redatto in conformità a SPEC-ORCA-opencode-232740.md
Data verifica: 2026-10-01

Principio: nessuna modifica al codice del repo. Solo ricerca verificata aprendo davvero le fonti (non dalla memoria).


## FONTI ESAMINATE (Eurostat - regionale NUTS2)

Le serie Eurostat testate per copertura Italia (NUTS2) e ultimo anno di riferimento >= 2025, in coerenza con vincolo committente:

## CANDIDATI SELEZIONATI (max 12, ordinati per valore di arricchimento)

### 1. CANDIDATO: Accesso a Internet nelle famiglie (Eurostat, NUTS2)
- Nome pubblico italiano breve: Accesso a Internet nelle famiglie
- Istituzione che pubblica: Commissione Europea – Eurostat (istituzione pubblica dell'UE)
- URL esatto del dato scaricabile (CSV/XLSX/SDMX/API): https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_r_iacc_h?format=JSON&lang=EN&geoLevel=nuts2
- URL della pagina di metodo: https://ec.europa.eu/eurostat/web/digital-economy-and-society/methodology
- Ok-licenza: CC BY 4.0 (Eurostat). Si cita la frase letta: "Eurostat has an open data policy and the data are made available under the CC BY 4.0 licence" (https://ec.europa.eu/eurostat/web/products-datasets/-/isoc_r_iacc_h)
- Livello territoriale: Regionale NUTS2 – copertura completa IT (21 unità NUTS2). Province (107): no. Comuni: no. NUTS3/province non presenti.
- Anni disponibili: 2023–2025 (primo 2023, ultimo 2025). Frequenza di aggiornamento: annuale.
- Ultimo anno di riferimento >= 2025: Sì, 2025 (ultimo anno disponibile = 2025). Verificato direttamente via API Eurostat con sinceTimePeriod=2025.
- Unità di misura: % delle famiglie (PC_HH). Relativo: Sì.
- Verso onesto: higher_better (maggior accesso a internet nelle famiglie = migliore)
- Doppione: verificato nei manifest esistenti (bes_regione_manifest, multiscopo_regione_manifest, province_manifest, external_indicator_manifest, Assoluti_Regione/Province). Termini chiave cercati: "internet", "famiglie", "accesso internet". Dichiarato: NUOVO. Dimensione digitale non coperta da indicatori già presenti.
- Esempio reale (3 valori letti dal file API, anno 2025, NUTS2 IT): ITC1 Piemonte = 93,94%; ITC2 Valle d'Aosta = 96,22%; ITF1 Abruzzo = 93,86%. (verificato via chiamata API in tempo reale)
- Difficoltà di integrazione: formato JSON-Stat (facile da estrarre), join territori: mappatura NUTS2→20 regioni esistente in pipeline Eurostat (scripts/eurostat_source.py). Anni mancanti: 2025 completo per tutte 21 unità NUTS2 (copertura 100%). Attenzione: Trentino-Alto Adige = ITH1+ITH2 → combinazione ponderata per popolazione (regola pipeline già applicata).
