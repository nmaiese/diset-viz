# Gate A: mortalita-stradale
Contratto: v3
Tipo pezzo: scheda indicatore
Esito: PASSA
SHA brief: 3870f2e781a478cf0540ef8d6d22a22194e449b3
Hash brief: c6b2803420046228483391067549d7447aa017c0d43234696ec3d1030d1190f2
Autore/modello: Claude Sonnet (leader del brief)
Giudice/modello: Codex GPT-6
Domanda: Dove il tasso di mortalità stradale tra i 15 e i 34 anni è più alto, e come è cambiato dal 2004?
Angoli verificati: tassi regionali 2024, Sardegna 1,3 e quattro regioni a 0,4; dinamica 2004-2024, calo in 20 regioni su 20 e inversione contenuta delle medie di ripartizione
Tesi: Nel 2024 il tasso standardizzato va da 1,3 in Sardegna a 0,4 in Liguria, Marche, Molise e Piemonte. Dal 2004 è sceso in tutte le regioni. Il brief riconosce la variabilità dei tassi su pochi decessi e non attribuisce cause.
Codici e confronto: `bes:01SAL005`, livello regione, 2004-2024. Indicatore spiegato. I dati nazionali e gli altri conteggi sono solo contesto.
Ultimo dato: 2024
Data fonte del dato: 2026-05-25
URL fonte del dato: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip
Ruolo indicatori interni: indicatore spiegato e contesto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2026-05-25 | https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip | Metadati.xlsx, codice 01SAL005: “Tassi di mortalità per incidenti stradali standardizzati con la popolazione europea al 2013 all'interno della classe di età 15-34 anni, per 10.000 residenti.” Serie indicata nel brief fino al 2024. | sì |
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Sardegna.pdf | BesT 2025, dato 2023: Sardegna 0,8 e Italia 0,6. Il testo afferma che gli indicatori sono “molto variabili a livello territoriale e temporale” per l'esiguità dei fenomeni. | sì |
| Istat | 2025-07-24 | https://www.istat.it/wp-content/uploads/2025/07/REPORT_INCIDENTI_STRADALI_2024.pdf | Report anno 2024: 3.030 morti. Prospetto 3 riporta i conteggi per età e identifica i morti entro 30 giorni. | sì |
Grafico con dati esterni: non richiesto per scheda indicatore
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Indicatore, domanda e tesi sono coerenti con una scheda | sì | Brief identifica `bes:01SAL005` e confronta i tassi regionali 15-34 anni nel 2024 e nel tempo. La query “incidenti stradali” è dichiarata parziale e debole. Il lead proposto chiarisce entro due frasi che non si tratta di cronaca, totale delle vittime o feriti. | La scheda non risponde alla domanda sul totale nazionale o sugli incidenti del giorno, limite già esplicito. |
| Fonti esterne datate e dati centrali verificati | sì | Ho aperto i metadati Istat e verificato la definizione letterale. Il report BesT Sardegna conferma 2023 e la cautela sulla variabilità. Ricalcolo indipendente dal CSV `Assoluti_BES_Regione.csv` con `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py`: 20 regioni nel 2024, Sardegna 1,3, Calabria e Puglia 0,9, Liguria, Marche, Molise e Piemonte 0,4. Tutte le 20 regioni calano tra 2004 e 2024. | Il CSV verifica i valori regionali, non fornisce il valore Italia 2024. La media semplice dei territori non è un tasso nazionale. |
| Limiti, definizioni e cause sono gestiti | sì | Brief indica classe 15-34, tasso standardizzato per 10.000 residenti, pochi decessi e oscillazioni annuali. Proibisce cause non documentate e dichiara non trovato il criterio territoriale di attribuzione dei decessi. Istat BesT conferma che l'indicatore è molto variabile per l'esiguità dei fenomeni. | La definizione non specifica se la regione sia quella dell'incidente o della residenza. Il numero assoluto regionale sottostante non è disponibile nelle fonti aperte. |
| Livello e requisiti di struttura/metadati sono adeguati | sì | Il brief indica `level: regione`, chiave `bes:01SAL005`, vintage 2024, H1, `seo_title` entro 60 caratteri e fonti 1, 2 e 3. Prevede anche la fonte 5 se resta il dato sardo 113, che la struttura proposta include. | Sono istruzioni per la scheda futura. Il Gate A non verifica il front matter di una scheda ancora da scrivere. |
| Brief scrivibile senza affermazioni non sostenute | sì | La sezione 7 ora dice: “Nel 2024 la media semplice dei 20 tassi regionali sale e 9 regioni su 20 aumentano”. La frase identifica l'unità territoriale della media e non la presenta come valore o andamento nazionale. La ricerca di “nazional”, “Italia” e “media” nel brief conferma che il divieto è esplicito: il valore Istat Italia è ammesso solo per il 2023, mentre il 2024 nazionale non è disponibile. Ricalcolo dal CSV: media semplice regionale 0,590 nel 2023 e 0,685 nel 2024; 9 regioni aumentano, 4 calano e 7 restano invariate. | La media è descrittiva dei 20 tassi regionali, non sostituisce il valore Italia. Il brief mantiene questo limite. |
Motivo: Il brief aggiornato soddisfa la correzione richiesta. La frase separa la media semplice regionale dal dato nazionale, e nessun altro passaggio attribuisce alla media semplice delle regioni valore, quadro o andamento nazionale. Definizione, ultimo dato, confronti e cautele restano coerenti con le prove già raccolte.
Destinatario: leader
Data: 2026-10-08
