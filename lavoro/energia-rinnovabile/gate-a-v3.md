# Gate A: energia-rinnovabile
Contratto: v3
Tipo pezzo: scheda indicatore
Esito: PASSA
SHA brief: b756bd9f441ce07015afb1aa81f565cbdb005e1f
Hash brief: e1f44d7e41b3e51f600d18cfd576789c1545ed573e77d245748403086eab9f4a
Autore/modello: Claude Sonnet (leader del brief)
Giudice/modello: Codex GPT-6
Domanda: Quanta energia rinnovabile c'è, e dove? La corrispondenza con «energia rinnovabile» è parziale: la scheda misura soltanto il rapporto fra produzione elettrica rinnovabile e consumi elettrici interni lordi regionali, non la quota rinnovabile dell'energia complessivamente usata.
Angoli verificati: non richiesto per scheda indicatore
Tesi: Nel 2024 il rapporto fra produzione elettrica da fonti rinnovabili e consumi elettrici interni lordi varia dal 12,4% della Liguria al 327,8% della Valle d'Aosta. È un confronto descrittivo fra produzione e consumi regionali, non una misura di virtù o di produzione assoluta.
Codici e confronto: `bes:10AMB016`, livello regione, serie 2004-2024. Indicatore oggetto; altri indicatori non necessari.
Ultimo dato: 2024
Data fonte del dato: 2026-05-25
URL fonte del dato: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip
Ruolo indicatori interni: indicatore spiegato e contesto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2026-05-25 | https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip | Metadati.xlsx, codice 10AMB016: «Percentuale di consumi di energia elettrica coperti da fonti rinnovabili sul totale dei consumi interni lordi». Il file indicatori_regione_sesso.xlsx riporta: «Valori superiori a 100 sono dovuti alla produzione di energia superiore alla richiesta interna.» Serie fino al 2024. | sì |
| Regione autonoma Valle d'Aosta, Struttura statistica | 2025-08-06 | https://www.regione.vda.it/statistica/pubblicazioni/annuari/annuario2025/SITE/12/13.PDF | Tavola 12.13, anno 2023, produzione lorda elettrica rinnovabile in milioni di kWh: Valle d'Aosta 3.170,2, di cui 3.124,5 idrica; Basilicata 4.338,5, di cui 3.239,1 eolica; Nord 57.007,5 e Mezzogiorno 43.081,9. La tavola dichiara fonte Terna SpA. | sì |
Grafico con dati esterni: non richiesto per scheda indicatore
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Tesi = fatto sul mondo descrittivo | sì | Brief confronta quote territoriali dello stesso indicatore e precisa che non sono graduatoria di impegno o virtù. Il confronto assoluto del 2023 da tavola 12.13 mostra Nord 57.007,5 e Mezzogiorno 43.081,9 milioni di kWh, quindi il brief vieta correttamente di dire che il Sud produce più del Nord. | Istat misura un rapporto, non attribuisce le differenze territoriali a politiche, clima, orografia o esportazioni. |
| Limiti e definizione gestiti | sì | Istat definisce il rapporto fra produzione lorda elettrica da FER effettiva e consumo interno lordo elettrico. Il brief chiarisce unità percentuale, perimetro solo elettrico e frase ufficiale sui valori oltre 100. La serie CSV conferma 327,8% Valle d'Aosta e 12,4% Liguria nel 2024. | La citazione Istat menziona il saldo degli scambi nella formula senza spiegarne in dettaglio il calcolo. Non si può dedurre dove vada la produzione eccedente. |
| Corrispondenza con la domanda di ricerca dichiarata con onestà | sì | Il brief dichiara copertura parziale della query «energia rinnovabile» e richiede che entro le prime due frasi il lead specifichi che la misura riguarda elettricità e rapporto con i consumi regionali. Distingue inoltre le ricerche sulla quota dell'energia totale e sulla produzione assoluta, a cui la scheda non risponde. | La domanda generica può far attendere fonti rinnovabili per riscaldamento e trasporti, escluse dall'indicatore. |
| `level` e front matter richiesti | sì | Il brief specifica `level: regione`, `key: "bes:10AMB016"`, `vintage: 2024`, fonti 1, 2 e 3, H1 e `seo_title` entro 60 caratteri. Dati ammessi e struttura proposta restano sul livello regionale e sull'indicatore oggetto. | Requisiti da conservare nella scheda finale; questo gate valuta il brief, non una scheda già scritta. |
| Il brief non obbliga a scrivere ciò che le fonti non reggono | sì | Brief vieta cause non documentate, l'equivalenza fra quota e produzione, l'uso della media semplice 66,63 come nazionale e l'inferenza che oltre 100 significhi esportazione. Istat attesta il 41,7% nazionale 2024; fonte regionale ripubblica dati di produzione 2023 e il brief li mantiene distinti per anno e unità. | Il comunicato Terna citato come fonte 2 è una copia su un distributore e l'originale Terna non è stato aperto; non serve a sostenere la tesi, che resta basata su Istat e sulla tavola regionale verificata. |
Motivo: Il brief supera il Gate A v3. Ho ricalcolato dal CSV del sito 20 regioni nel 2024, estremi 12,4% e 327,8%, media semplice 66,63 e 15 regioni in diminuzione nel 2022 rispetto al 2021. Ho aperto l'appendice Istat e verificato definizione e citazione testuale, anno 2024 e nota sui valori oltre 100; la tavola regionale 12.13 conferma citazione Terna, anno 2023, unità e valori usati per composizione e confronto assoluto. Il brief distingue produzione da consumi e descrive correttamente la copertura parziale della domanda di ricerca.
Correzione: Nessuna bloccante per il Gate A. Nella scheda mantenere il chiarimento entro le prime due frasi, spiegare i valori oltre 100 con la formulazione Istat, non chiamare la media regionale media nazionale e non attribuire cause o esportazioni.
Destinatario: archivio
Data: 2026-10-08
