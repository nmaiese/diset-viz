# Fonti esterne aperte e verificate (08/10/2026), `bes:10AMB016`

Aperte con `curl` (User-Agent `DivarioCheck/1.0`, HTTP 200) e lette in locale l'8/10/2026. Le citazioni sono copiate dal testo estratto (xlsx con openpyxl, PDF con pypdf).

## 1. Istat, Bes dei territori: appendice statistica (zip) con file `Metadati.xlsx` e `indicatori_regione_sesso.xlsx`
- Istituzione: Istat. Data: `last-modified` 25/05/2026 (file interni datati 8-25 maggio 2026). Aggiornamento intermedio Bes 2026.
- URL: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip (HTTP 200, 1.789.151 byte, application/zip)
- Anno del dato: serie 2004-2024, ultimo anno 2024.
- Citazione, `Metadati.xlsx`, riga 10AMB016: «Percentuale di consumi di energia elettrica coperti da fonti rinnovabili sul totale dei consumi interni lordi. L'indicatore è ottenuto come rapporto tra la produzione lorda elettrica da FER effettiva (non normalizzata) e il Consumo Interno Lordo di energia elettrica (pari alla produzione lorda di energia elettrica al lordo della produzione da apporti di pompaggio più il saldo scambi con l'estero o tra le regioni).» Fonte indicata: «Terna S.p.A. - Statistica annuale della produzione e del consumo di energia elettrica in Italia».
- Citazione, nota in ogni riga di `indicatori_regione_sesso.xlsx`: «L'indicatore è stato calcolato considerando il consumo interno lordo comprensivo dei pompaggi. Valori superiori a 100 sono dovuti alla produzione di energia superiore alla richiesta interna.»
- Dati ripartizioni e Italia (stesso file), 2024: Italia 41,7, Nord 40,7, Centro 30,8, Mezzogiorno 51,3. 2004: Italia 15,5, Nord 18,8, Centro 16,9, Mezzogiorno 8,2. Province autonome 2024: Bolzano 234,3, Trento 143,4.
- Ruolo: fonte primaria del dato (definizione, unità, valori e valore nazionale). Limite d'uso: la formula è riportata in una frase sola, e dal testo non si riesce a ricostruire come il saldo con l'estero o fra regioni entri nel denominatore. Non riscrivere la formula con parole nostre.

## 2. Terna, comunicato stampa del 16 gennaio 2025 sul consuntivo 2024
- Istituzione: Terna S.p.A. (gestore della rete di trasmissione nazionale). Data: 16/01/2025 (`last-modified` della copia 17/01/2025).
- URL aperto: https://italia-informa.com/public/italiainforma/ComunicatiStampa/Terna/TERNA_16_GENNAIO.pdf (HTTP 200, 230.662 byte, 3 pagine). È una copia del comunicato su un distributore di comunicati, non il sito Terna: l'originale su terna.it non l'ho aperto.
- Anno del dato: 2024 (dati provvisori nazionali).
- Citazione: «Lo scorso anno le fonti rinnovabili hanno registrato il dato più alto di sempre di copertura della domanda, pari al 41,2% (rispetto al 37,1% del 2023).» E: «crescita a due cifre della produzione idroelettrica (+30,4%) e fotovoltaica (+19,3%)».
- Ruolo: contesto nazionale 2024 e definizione di «copertura della domanda» di Terna. Limite d'uso: il 41,2% (domanda, dati provvisori) NON è il 41,7% dell'Istat (consumo interno lordo con pompaggi): denominatori diversi. Se si citano entrambi, si dice quale è quale. Dato nazionale: non spiega le differenze fra regioni e non va usato come causa del salto 2023-2024 di Valle d'Aosta e Trentino-Alto Adige.

## 3. Regione autonoma Valle d'Aosta, Annuario statistico 2025, tavola 12.13 (dati Terna, anno 2023)
- Istituzione: Regione autonoma Valle d'Aosta, Struttura statistica, che riproduce dati «Terna SpA - Rete elettrica nazionale». Data: `last-modified` 06/08/2025.
- URL: https://www.regione.vda.it/statistica/pubblicazioni/annuari/annuario2025/SITE/12/13.PDF (HTTP 200, 431.222 byte, 1 pagina)
- Anno del dato: 2023.
- Titolo: «Tavola 12.13 - Produzione lorda di energia elettrica per fonte energetica rinnovabile utilizzata, regione e aree geografiche (in milioni di kWh) - Anno 2023».
- Valori letti (milioni di kWh, 2023): Valle d'Aosta idrica 3.124,5 su totale 3.170,2. Trentino-Alto Adige idrica 9.438,0 su 10.359,0. Basilicata eolica 3.239,1 su 4.338,5. Puglia eolica 6.463,7, fotovoltaica 4.193,3, totale 12.279,1. Liguria totale 617,8. Italia 116.578,6 (idrica 40.517,3, eolica 23.640,5, fotovoltaica 30.711,1). Nord 57.007,5, Centro 16.489,3, Mezzogiorno 43.081,9.
- Ruolo: mostra di che cosa sono fatti i numeri alti (idroelettrico alpino, eolico lucano) e controlla che il Nord produce in assoluto più rinnovabile del Mezzogiorno. Limite d'uso: è una ripubblicazione di dati Terna, non il file Terna. Riferito al 2023, non al 2024: non confonderlo con l'ultimo anno dell'indicatore.

## 4. Stessa fonte, tavola 12.14 (consumi, anni 2022-2023)
- URL: https://www.regione.vda.it/statistica/pubblicazioni/annuari/annuario2025/SITE/12/14.PDF (HTTP 200, 431.865 byte). Titolo: «Tavola 12.14 - Consumo di energia elettrica per categoria di utilizzazioni, regione e aree geografiche (in milioni di kWh) - Anni 2022-2023». Totale 2023: Italia 287.372,0, Valle d'Aosta 907,3, Basilicata 2.600,1.
- Ruolo e limite: sconsigliata nel pezzo. Il rapporto fra tavola 12.13 e tavola 12.14 NON riproduce l'indicatore (Valle d'Aosta: 3.170,2/907,3 = 349% contro 293,3 dell'indicatore 2023, Basilicata 167% contro 136,6) perché il denominatore Istat è il consumo interno lordo, un'altra grandezza. Non fare questa divisione nella scheda.

## Non trovato / non aperto
- Il file statistico Terna originale per regione (`terna.it`, «Dati statistici sull'energia elettrica in Italia» 2024): le pagine terna.it/it/sistema-elettrico/statistiche si aprono (HTTP 200) ma la lista dei documenti è caricata via script e non ho ottenuto un PDF regionale 2024. Non elencato come fonte.
- Un report Istat «Bes dei territori 2025» per regione che citi questo indicatore: i PDF `BesT2025_Basilicata.pdf` e `BesT2025_Valle-d-Aosta.pdf` dati per probabili sono 404. Non li ho cercati oltre.
- GSE, Rapporto statistico sulle fonti rinnovabili (quota FER sui consumi finali di energia): la ricerca web non ha dato l'edizione recente, non aperto. Quindi nessuna cifra sulla quota di energia rinnovabile sul totale dell'energia (non solo elettrica) può entrare nella scheda.
- Una fonte aperta che spieghi perché la serie scende nel 2022 (Italia 30,7 contro 35,1 del 2021) o perché Valle d'Aosta e Trentino-Alto Adige salgono tanto nel 2024: non trovata. Il comunicato Terna dice +30,4% dell'idroelettrico nazionale nel 2024, non lo collega alle regioni.
- Le note del worker precedente («confermato da dati Terna-BES») non hanno una fonte aperta: il file Terna non è stato letto da nessuno.
