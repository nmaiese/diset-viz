# Estrazione Istat AVQ regionale 2025

Fatto: `scripts/nuovi_dati/istat_avq.py` legge solo la cache `data/istat_cache` (symlink, non committato), mai la rete. Tutte le 13 chiavi di flusso sono in cache. 23 indicatori su 23 estratti, 10960 righe, `level=regione`, 20 regioni, ultimo anno 2025 con 20/20 regioni per ogni serie.
Anni: 2001-2025 (AVQ_CINQUE_PORZIONI 2005-2025). Nessun anno con meno di 20 regioni.
Filtri verificati sul file: DATA_TYPE/MEASURE del rapporto coincidono, SEX=9 (famiglie: NUMBER_HOUSEHOLD_COMP=TOT), nessun duplicato. THV scartato.
Trentino Alto Adige: media ponderata TRENTINO_WEIGHTS (535.8, 544.1) di ITD1 e ITD2, per ogni anno in cui ci sono entrambe.
Province: 0 (solo regionale), tutte le 107 mancano per scelta.
Temi proposti dai domini del manifest Multiscopo: Salute, Benessere economico, Benessere soggettivo, Ambiente, Abitazione, Energia. Per bus, cultura, amici non c'e un dominio adatto: scelta discutibile (Benessere soggettivo).
Licenza: CC BY 4.0, frase letta con WebFetch su istat.it/note-legali (riassunto del modello, quindi la citazione va riverificata a mano).
Non verificato: pagina di metodo (URL dedotto dal rapporto, non aperto); intervalli di confidenza non letti; i valori note del rapporto sono stati ritrovati nei dati (Campania 42.5, Toscana 71.5, ER 100.5 ecc.).
Rumorosi: RICOVERO_ASSISTENZA_MEDICA (max 100), INCIDENTI_DOMESTICI, PRONTO_SOCCORSO, GUARDIA_MEDICA, CINQUE_PORZIONI, LAVORO_BICICLETTA.
`--offline` e' il default; senza `--rete` non si apre mai il client di rete.
