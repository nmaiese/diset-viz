# Reddito netto medio annuale delle famiglie (ims-MULTI_REDD_MEDIO) — numeri.md

## Definizione (fonte Istat, Indagine Multiscopo sulle famiglie)
- Codice: ims-MULTI_REDD_MEDIO — "Reddito netto medio annuale delle famiglie"
- Definizione esatta della fonte: "Indagine Multiscopo sulle famiglie, Istat SDMX, 32_292_DF_DCCV_REDNETFAMFONTERED_9"
- Fonte: Istat, Indagine Multiscopo sulle famiglie (famiglia "Istat, vita quotidiana delle famiglie"); scheda `content/indicators/multiscopo__MULTI_REDD_MEDIO.md`, vintage 2024
- Unità: importo in euro (reddito netto annuale delle famiglie), valori nominali; non un tasso né un indice
- Livello: regione (20 regioni), anni 2018–2024

## Ultimo anno: 2024, anni 7 (2018–2024), 20 regioni su 20 in ogni anno
- Max: Trentino Alto Adige 55.295 euro
- Min: Calabria 34.741 euro
- Media semplice delle 20 regioni (ricalcolata): 44.462,96 euro (44.463 arrotondato) — NON è un valore nazionale: nel file non c'è riga Italia

## Top 5 (2024)
- Trentino Alto Adige: 55.295 euro
- Lombardia: 52.559 euro
- Emilia-Romagna: 51.994 euro
- Valle d'Aosta: 51.354 euro
- Umbria: 49.570 euro

## Bottom 5 (2024)
- Molise: 39.172 euro
- Basilicata: 37.778 euro
- Campania: 37.596 euro
- Sicilia: 34.754 euro
- Calabria: 34.741 euro

## Serie storica completa (media semplice ricalcolata, max, min per anno)
- 2018: media 35.330 euro — max Trentino Alto Adige 43.560 — min Molise 27.676
- 2019: media 37.063 euro — max Emilia-Romagna 44.435 — min Basilicata 28.735
- 2020: media 36.593 euro — max Trentino Alto Adige 43.721 — min Abruzzo 29.052
- 2021: media 37.886 euro — max Trentino Alto Adige 46.617 — min Campania 30.427
- 2022: media 40.201 euro — max Trentino Alto Adige 49.764 — min Calabria 29.807
- 2023: media 41.876 euro — max Lombardia 49.814 — min Calabria 32.091
- 2024: media 44.463 euro — max Trentino Alto Adige 55.295 — min Calabria 34.741
- Forma media: unico calo 2020 (−470 euro vs 2019); poi crescita ininterrotta; copertura piena (20/20) in tutti gli anni

## Estremi primo–ultimo anno (2018 → 2024)
- Max 2018: Trentino Alto Adige 43.560 → 2024: 55.295
- Min 2018: Molise 27.676 → 2024: Calabria 34.741
- Max 2024: Trentino Alto Adige 55.295 (era 43.560 nel 2018)
- Min 2024: Calabria 34.741 (era 29.307 nel 2018)
- Distanza fra estremi: 15.884 euro nel 2018 → 20.554 nel 2024
- Media semplice: 35.330,44 euro (2018) → 44.462,96 euro (2024), +9.132,52 euro (+25,8% nominale)

## Salgono/scendono
- 2018→2024 (20 comuni): salgono 20, scendono 0, invariati 0
- 2023→2024 (20 comuni): salgono 20, scendono 0, invariati 0
- Aumenti maggiori 2018→2024: Valle d'Aosta +15.546, Emilia-Romagna +12.458, Trentino Alto Adige +11.735
- Aumenti minori: Calabria +5.434, Abruzzo +5.665, Sicilia +6.472

## Regioni, 2018 → 2024 (tutte e 20)
- Valle d'Aosta 35.808 → 51.354 (+15.546)
- Emilia-Romagna 39.536 → 51.994 (+12.458)
- Trentino Alto Adige 43.560 → 55.295 (+11.735)
- Umbria 37.977 → 49.570 (+11.593)
- Molise 27.676 → 39.172 (+11.496)
- Lombardia 41.231 → 52.559 (+11.328)
- Marche 37.794 → 47.146 (+9.352)
- Friuli-Venezia Giulia 38.128 → 47.408 (+9.280)
- Puglia 30.537 → 39.380 (+8.843)
- Liguria 36.116 → 44.570 (+8.454)
- Basilicata 29.638 → 37.778 (+8.140)
- Toscana 39.133 → 47.201 (+8.068)
- Campania 29.535 → 37.596 (+8.061)
- Piemonte 37.745 → 45.685 (+7.940)
- Lazio 37.803 → 45.576 (+7.773)
- Veneto 41.048 → 48.590 (+7.542)
- Sardegna 31.789 → 39.259 (+7.470)
- Sicilia 28.282 → 34.754 (+6.472)
- Abruzzo 33.966 → 39.631 (+5.665)
- Calabria 29.307 → 34.741 (+5.434)

## Outlier/dati anomali
- Trentino Alto Adige è l'unica regione con valori a 6 decimali in tutti e 7 gli anni (es. 55.295,113251): sembra aggregato (province) e non rilevato; usare l'intero
- Valori nominali non deflati: il +25,8% del periodo non è crescita reale di potere d'acquisto
- 2020 unico anno in calo (−470 euro di media): anno pandemico, non spezzare la serie senza nota
- Nessun valore mancante: 20 regioni × 7 anni = 140 righe tutte presenti
- Nessun valore nazionale nel file: la media delle regioni non va scritta come "Italia"

## Confronto utile fra due regioni
- Trentino Alto Adige 55.295 vs Calabria 34.741 (2024): gap 20.554 euro (1,59×), più ampio dei 15.884 del 2018: tutte salgono, ma il divario in euro si allarga

## File e comando
- Dato grezzo: `app/static/data/Assoluti_Multiscopo_Regione.csv`, righe `idIndicatore=MULTI_REDD_MEDIO` (140 righe)
- Dossier: `bin/py -m scripts.editoriale.brief multiscopo:MULTI_REDD_MEDIO --out lavoro/reddito-netto-famiglie/dossier.json`
- Medie/conteggi ricalcolati con script su CSV (`statistics.fmean` per anno): 2024 = 44.462,955663 euro, 2018 = 35.330,4373 — coincidono con `serie.media_semplice_per_anno` del dossier
