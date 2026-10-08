# Gate A: pilota-pensioni
Contratto: v3
Tipo pezzo: scheda indicatore
Esito: PASSA
SHA brief: e37d275e98d7a9762457564d4f81e4052035c9a7
Hash brief: 62a0e8286f06a62b9437ed9946fe78b1efecf921301631200eceee2f72ac3c3d
Autore/modello: Claude Sonnet (leader del brief)
Giudice/modello: Codex GPT-6
Domanda: Quanti pensionati hanno un reddito pensionistico basso e dove? La corrispondenza con «pensioni minime» è parziale: la scheda misura la quota sotto 500 euro lordi, non il trattamento minimo INPS.
Angoli verificati: distribuzione provinciale 2023, da Crotone 16,9% a Bolzano 4,1%; dinamica 2015-2023, calo in tutte le 106 province comparabili e distanza tra estremi da 13,2 a 12,8 punti.
Tesi: Nel 2023 la quota provinciale di pensionati con reddito pensionistico lordo mensile sotto 500 euro varia da 4,1% a Bolzano a 16,9% a Crotone. Tra 2015 e 2023 scende in tutte le province comparabili, mentre la distanza tra gli estremi resta ampia. È un confronto descrittivo, non un effetto causale del luogo di residenza.
Codici e confronto: `bes:04BEC006P`, provincia, 2015-2023; indicatore oggetto. `bes:04BEC005P` è previsto come un solo numero di contesto per Crotone e Milano, non come tesi né correlazione.
Ultimo dato: 2023
Data fonte del dato: 2025-12-04
URL fonte del dato: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf
Ruolo indicatori interni: indicatore spiegato e contesto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf | BesT 2025, dato 2023: Crotone 16,9%, Italia 8,9%; il report definisce la misura come pensionati con reddito pensionistico sotto 500 euro mensili. | sì |
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Trentino-Alto-Adige.pdf | Tavola 4, Bolzano 4,1% nel 2023; supporta l'estremo provinciale inferiore. | sì |
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/Appendice_Sicilia_2025.xlsx | Glossario: percentuale di pensionati con reddito pensionistico lordo mensile sotto 500 euro sul totale dei pensionati. Tavola Dominio 04: Italia 10,4% nel 2019 e 8,9% nel 2023; Mezzogiorno 14,8% e 12,8%. | sì |
| INPS | 2026-03-23 | https://servizi2.inps.it/servizi/osservatoristatistici/api/getAllegato/?idAllegato=1037 | Osservatorio al 1 gennaio 2026: classi sotto 750 euro contano pensioni, non pensionati; più prestazioni o altri redditi impediscono di leggere la classe come condizione economica individuale. Fonte di limite, non conferma della serie Bes. | sì |
| Istat | 2025-12-17 | https://www.istat.it/storage/ASI/2025/capitoli/C05.pdf | Annuario 2025, dato 2023: circa 22,9 milioni di trattamenti pensionistici; supporto al contesto sulle prestazioni, non al tasso Bes. | sì |
Grafico con dati esterni: non richiesto per scheda indicatore
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Indicatore, domanda e tesi sono coerenti con una scheda | sì | Brief identifica `bes:04BEC006P` come quota provinciale sotto 500 euro lordi mensili. La tesi confronta territori e anni senza trasformare la quota in conteggio di persone. Il lead proposto chiarisce entro due frasi che il dato non è la pensione minima INPS. | La query «pensioni minime» resta solo parzialmente coperta, limite dichiarato nel brief e da mantenere nel lead. |
| Fonti esterne datate e dati centrali verificati | sì | Istat BesT Calabria conferma 2023, Crotone 16,9% e Italia 8,9%; il report del Trentino-Alto Adige conferma Bolzano 4,1%. Glossario e appendice Istat verificano definizione e confronti nazionali. Ho ricalcolato il CSV provinciale del repository: massimo Crotone 16,9%, minimo Bolzano 4,1%, distanza 12,8 punti nel 2023. | Il CSV del sito verifica le serie provinciali, non sostituisce la fonte Istat per il valore nazionale. |
| Limiti, definizioni e cause sono gestiti | sì | Il brief distingue quota da conteggio e reddito pensionistico da reddito individuale o familiare, vieta di equiparare 500 euro al trattamento minimo o alla povertà, non attribuisce cause e prescrive il limite che Istat non chiarisce se la provincia rappresenti residenza o luogo di erogazione. La formulazione aggiornata descrive quote territoriali e nega un effetto causale della residenza. | Il glossario non chiarisce trattamento di integrazione al minimo, prestazioni multiple e reversibilità; la fonte INPS usa unità pensioni e soglia 750 euro nel 2026. |
| Livello e requisiti di struttura/metadati sono adeguati | sì | `brief.md` indica `level: provincia`, chiave `bes:04BEC006P`, vintage 2023, fonti 1, 2 e 4; dato INPS è correttamente condizionato al suo uso nella sezione dei limiti. La struttura include la nota territoriale e i marcatori claims. | Front matter e marcatori sono istruzioni per la futura scheda, non una scheda già scritta. |
| Brief scrivibile senza affermazioni non sostenute | sì | Ricalcolo dal CSV `Assoluti_Provincia.csv`: 106 province con osservazioni sia nel 2015 sia nel 2023, nessun aumento; distanza massima-minima 13,2 punti nel 2015 e 12,8 nel 2023. Ricerca testuale del brief: nessuna tesi residua di probabilità o causalità; tali termini compaiono solo per vietare o descrivere limiti/letture da evitare. | Il salto di Bolzano nel 2023 e gli effetti della soglia nominale restano non spiegati, correttamente esclusi dalle conclusioni. |
Motivo: Il brief aggiornato supera il gate v3. Le correzioni del primo giro sono presenti nel testo proposto: distinzione immediata dal trattamento minimo INPS, tesi descrittiva senza nesso causale e limite sul significato territoriale della provincia. Ricalcolo dei dati e fonti Istat supportano gli estremi e il confronto temporale. Nessuna formulazione causale o probabilistica è rimasta come affermazione del brief.
Correzione: Nessuna per il Gate A. Conservare nella futura scheda i caveat prescritti, i valori nazionali attribuiti a Istat e i limiti dell'osservazione INPS.
Destinatario: archivio
Data: 2026-10-08
