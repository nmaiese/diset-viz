# Gate A: infortuni-lavoro
Contratto: v3
Tipo pezzo: scheda indicatore
Esito: PASSA
SHA brief: b756bd9f441ce07015afb1aa81f565cbdb005e1f
Hash brief: b49fd62144c6b7bd9e3d1d7b8af44f64853184a381b3b76ea88e4ebf0bf9fec3
Autore/modello: Claude Sonnet (leader del brief)
Giudice/modello: Codex GPT-6
Domanda: Quanti sono gli infortuni sul lavoro gravi e come variano tra regioni? La corrispondenza con «morti sul lavoro» è parziale: il tasso unisce gli infortuni mortali e quelli con inabilità permanente, e non fornisce il numero delle morti.
Angoli verificati: non applicabile, scheda indicatore
Tesi: Nel 2022 il tasso va da 8,0 per 10.000 occupati in Piemonte a 17,8 in Umbria. Tra 2018 e 2022 la distanza tra massimo e minimo si riduce, con cali più marcati nella parte alta della serie. Confronto descrittivo, senza spiegazione causale.
Codici e confronto: `bes:03LAV007`, livello regione, 2018-2022; indicatore oggetto. Altri indicatori solo contesto, senza correlazioni come tesi.
Ultimo dato: 2022
Data fonte del dato: 2025-12-04
URL fonte del dato: https://www.istat.it/wp-content/uploads/2025/12/Appendice_Sicilia_2025.xlsx
Ruolo indicatori interni: indicatore spiegato e contesto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/Appendice_Sicilia_2025.xlsx | Glossario 03-03: «Numero di infortuni sul lavoro mortali e con inabilità permanente sul totale degli occupati (al netto delle forze armate) per 10.000». Dominio 03: 11,0 per l'Italia nel 2022, marcato provvisorio. | sì |
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf | BesT Calabria 2025: nel 2022 Calabria 13,5 per 10 mila occupati, Catanzaro 8,0 e Reggio di Calabria 17,3; -3,1 punti dal 2019. Documento aperto e controllato. | sì |
| INAIL | 2025-10-23 | https://www.inail.it/content/dam/inail-hub-site/documenti/rapporti-e-relazioni-inail/2025/10/UMBRIA.pdf | Rapporto regionale 2024: 1.313 infortuni accertati positivi con menomazioni in Umbria nel 2022 e 14 con esito mortale; unità amministrative distinte dal tasso Bes, non confermano né ricostruiscono 17,8. | sì |
Grafico con dati esterni: non richiesto per scheda indicatore
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Indicatore, domanda e tesi sono coerenti con una scheda | sì | Brief identifica `bes:03LAV007` come oggetto e descrive la copertura di «morti sul lavoro» come parziale. Impone che il lead distingua numero delle morti e tasso combinato entro le prime due frasi. | La query di testa non è soddisfatta come conteggio dei decessi. Mantenere esplicita la corrispondenza parziale nel lead. |
| Fonti esterne datate e dati centrali verificati | sì | Ho aperto appendice Istat e report Istat Calabria. La prima dà definizione e valore Italia provvisorio 11,0; il secondo riporta 13,5, Catanzaro 8,0 e Reggio di Calabria 17,3. Ho ricalcolato il CSV: per il 2022 massimo Umbria 17,8, minimo Piemonte 8,0, media semplice 12,42; nel 2018 estremi 24,1 e 7,9. | Il CSV del sito controlla la serie regionale ma non sostituisce la fonte per il dato nazionale. Il glossario non specifica il perimetro operativo completo del numeratore. |
| Limiti, definizioni e cause sono gestiti | sì | Il brief distingue tasso da conteggio, nomina sia esiti mortali sia inabilità permanente, vieta di chiamare i valori morti, vieta cause non documentate e correlazioni interne come tesi. Specifica che i conteggi INAIL non confermano il tasso e vieta di sommarli o dividerli per occupati. Il rapporto INAIL aperto mostra concretamente unità e conteggi distinti. | Non trovato il dettaglio su gestioni, modalità di accadimento, soglia di menomazione e anno di riferimento del numeratore Bes. Il brief prescrive di dichiarare il limite e di non riconciliare i conteggi INAIL. |
| Livello e requisiti di struttura/metadati sono adeguati | sì | Il front matter del brief contiene `level: regione`; le istruzioni per la futura scheda prescrivono `key: "bes:03LAV007"`, `vintage: 2022`, fonti 1-3, `h1`, `seo_title` entro 60 caratteri e il carattere provvisorio del 2022 nei limiti. | Non è ancora una scheda scritta: la presenza e validità dei metadati prescritti andranno controllate sulla bozza. |
| Brief scrivibile senza affermazioni non sostenute | sì | Ricalcolo dal CSV `Assoluti_BES_Regione.csv`: 20 regioni per ciascun anno dal 2018 al 2022; nel 2022 Umbria 17,8 e Piemonte 8,0; dal 2018 al 2022 15 regioni scendono, 3 salgono e 2 restano invariate. Il brief vieta esplicitamente di riprendere dalla scheda attuale cause su struttura del lavoro o sotto-denuncia. | Il 2022 è provvisorio; la serie copre cinque anni e non spiega variazioni o differenze. Mantenere questi limiti senza attribuire meccanismi. |
Motivo: Il brief spiega l'indicatore richiesto e pone limiti coerenti con la definizione Istat. I numeri regionali chiave sono confermati dal ricalcolo e una fonte Istat esterna verifica definizione e ordine di grandezza. Ho controllato anche il report INAIL: i suoi accertamenti e il tasso Bes hanno unità e perimetri diversi, distinzione che il brief prescrive di conservare. La ricerca «morti sul lavoro» è dichiarata parzialmente coperta entro il lead, e la precedente spiegazione causale della scheda è vietata.
Correzione: Nessuna per il Gate A. Nella bozza mantenere la distinzione tra tasso combinato e morti, il 2022 provvisorio, l'assenza di cause dimostrate e l'incomparabilità dei conteggi INAIL.
Destinatario: archivio
Data: 2026-10-08
