# Energia elettrica da fonti rinnovabili (bes:10AMB016) — numeri.md

## Definizione (fonte Istat BES dei territori, glossario)
- Codice: bes:10AMB016 / bes-10AMB016
- Fonte: Istat, BES nazionale, aggiornamento intermedio 2026 (https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/la-misurazione-del-benessere-bes/gli-indicatori-del-bes/)
- Unità (fonte): Valori percentuali (%) — variazione in punti percentuali
- Livello: regione (2004–2024), provincia (2015–2023)
- Definizione: energia elettrica da fonti rinnovabili (TERNA S.p.A. - Statistica annuale della produzione e del consumo di energia elettrica in Italia).
- Tipo: rapporto (percentuale). Può superare 100% se produzione > consumo.

## Ultimo anno disponibile (livello regionale)
- Ultimo anno: 2024
- Serie completa: 21 anni (2004–2024)

## Estremi territorio — 2024 (regionale)
- Max: Valle d'Aosta 327.8%
- Min: Liguria 12.4%
- Media semplice (NON nazionale): calcolata sui territori regionali presenti.
- Media semplice territori: 66.63%

## Top 5 regioni — 2024
- Valle d'Aosta: 327.8%
- Trentino Alto Adige: 186.3%
- Basilicata: 124.1%
- Calabria: 78.7%
- Molise: 77.1%

## Bottom 5 regioni — 2024
- Lombardia: 31.1%
- Marche: 27.3%
- Emilia-Romagna: 22.6%
- Lazio: 20.3%
- Liguria: 12.4%

## Serie storica completa (regionale, valori per regione in ultimo anno; sintesi)
- 2004: max Valle d'Aosta 242.2%, min Sicilia 1.5%, media semplice 31.25%
- 2005: max Valle d'Aosta 229.2%, min Liguria 2.3%, media semplice 28.52%
- 2010: max Valle d'Aosta 251.4%, min Liguria 5.4%, media semplice 41.49%
- 2015: max Valle d'Aosta 323.1%, min Liguria 8.6%, media semplice 56.66%
- 2020: max Valle d'Aosta 314.5%, min Liguria 8.3%, media semplice 62.27%

## Come cambiano gli estremi (primo–ultimo anno, regionale)
- Max 2004->2024: Valle d'Aosta 242.2% → Valle d'Aosta 327.8% (delta +85.6 pp)
- Min 2004->2024: Sicilia 1.5% → Liguria 12.4% (delta +10.9 pp)

## Territori: salgono/scendono fra primo e ultimo anno (regionale)
- Comuni tra primo e ultimo: 20; salgono: 20; scendono: 0; invariati: 0

## Outlier/anomali
- Valori >100% indicano produzione > consumo (es. Valle d'Aosta). Coerenti con indicatore percentuale.
- Estremi provinciali (es. Sondrio 449,6% nel 2023) confermano logica % sui consumi.

## Confronto utile
- Valle d'Aosta vs Liguria (2024): 327,8% vs 12,4% — forte divario tra territori montani/alpini vs altri.

## Dati anomali da verificare
- Nessun dato palesemente errato rilevato; unità coerente con definizione (%).

## File e comando di provenienza
- File CSV: app/static/data/Assoluti_BES_Regione.csv, app/static/data/Assoluti_Provincia.csv
- Comando: DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.brief bes:10AMB016 --out lavoro/energia-rinnovabile/dossier.json