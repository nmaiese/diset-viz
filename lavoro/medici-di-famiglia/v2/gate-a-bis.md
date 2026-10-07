# Gate A bis: medici di famiglia v2

Esito: FERMO. Data: 7 ottobre 2026. Secondo e ultimo controllo del brief rivisto.
Brief esaminato: `lavoro/medici-di-famiglia/v2/brief.md`, commit `849310eefb26c78a0d17c7dd1962c9c3679f857d`.
Hash SHA-256 del brief: `6a15c86ec89ef84e0333bf6317fd1bb74ecff3d22c06d7fd85d92a88e2012f1b`.
Autore: leader Claude Sonnet 5.5, famiglia Anthropic. Giudice: Codex GPT-6 Sol, famiglia OpenAI, `AGENT_ID=codex-gpt-6-sol`.
Domanda: il numero di assistiti del mio medico dice quanto è difficile curarsi nella mia regione?
Tesi giudicata: nel 2023 più MMG sopra soglia si associano a meno dimissioni fuori regione e a meno persone in fila ASL, senza stabilire facilità di cura o causa.
Codici e confronto: `bes:12SER027` con `bes:12SER025`, `ims:MULTI_ASL_FILA_OLTRE_20_MIN`, `bes:01SAL021`, `ims:MULTI_PRONTO_SOCCORSO` e, come contesto, `bes:12SER004`. Regioni, N=20, 2023 e controlli 2019-2023.

## Tre correzioni del primo gate

| Correzione | Stato | Citazione del brief e giudizio |
|---|---|---|
| 1. Tesi prudente, senza esclusioni causali né confusione fra persone e dimissioni | Parzialmente | Riga 9: "non stabilisce quanto sia facile curarsi né perché le mappe differiscano". Riga 15: "il 32,6% del Molise riguarda le dimissioni". Però riga 18 prescrive "non è la dotazione di medici né l'età", proprio l'esclusione vietata alle righe 14 e 27. La tesi dice "meno dimissioni" e "meno persone" dove i dati sono quote di dimissioni e di utenti ASL. Supera così, nelle unità, la formulazione massima del primo gate. |
| 2. Accesso triennale come contesto, controlli e unità in `numeri.md` | Applicata | Riga 12: accesso "solo come CONTESTO", cella 2023 pari alla media 2022-2024. Riga 15 distingue popolazioni e denominatori. La sezione finale di `numeri.md` riporta codici, finestre, N=20/18, esclusioni, negativi, controlli e PS per 1.000. Limite: compatibilità territoriale, non individuale. |
| 3. Esplorazione di 78 coppie dichiarata | Applicata | Riga 13: "ricerca ESPLORATIVA", "78 coppie", scelte dopo la matrice e controlli non provati cronologicamente. Limite: nessuna replica indipendente o correzione per selezione. |

## Cinque criteri della sezione A

| Criterio | Sì/no | Prova | Limite |
|---|---|---|---|
| 1. Corregge la sola classifica e risponde al lettore | sì | Righe 5-12 pongono la domanda e mostrano una discordanza regionale reale. | "Non regge come termometro" (riga 12) va inteso solo per le misure osservate, non come verdetto generale sull'accesso alle cure. |
| 2. Tre misure pertinenti, anno, livello e popolazioni compatibili | sì | MMG, dimissioni e fila ASL sono incrociati sulle stesse 20 regioni nel 2023. | Denominatori diversi: medici, dimissioni, utenti ASL. Solo ordinamenti ecologici. L'accesso ai servizi è triennale e resta contesto. |
| 3. Formula, chiavi, N ed esclusioni in `numeri.md` | sì | Il file nomina Spearman con ranghi medi, elenca le 20 chiavi, N, codici, finestre, N=18 senza Lombardia/Molise, esiti e script riproducibile. | Nessuna formula algebrica esplicita nel testo; metodo e implementazione sono verificabili. |
| 4. Risultato distinto dalla causa | no | Righe 14-15 dichiarano meccanismo ignoto e vietano cause. | Riga 18 ordina di citare i rho deboli come "non è la dotazione di medici né l'età": un rho debole non esclude questi fattori. Riga 23 trasforma la soglia ASL oltre 20 minuti in "quanto si aspetta", che non è misurato. |
| 5. Controllo contrario scelto prima del calcolo | sì | `numeri.md` conserva 2019-2023, N=18, PS di segno opposto e rho dimissioni ridotto da -0,503 a -0,318. | Scelta dopo la matrice, cronologia non provata, anni non indipendenti: controllo descrittivo, non conferma. |

## Verifica indipendente

Ho letto direttamente i due CSV regionali BES e Multiscopo, filtrato `Area=Regione`, `Livello/Variazione=Livello`, codice e anno, poi calcolato ranghi medi e correlazione di Pearson sui ranghi in memoria, senza importare `calcola_incroci.py` o viste del sito. N=20 per ogni coppia e anno verificato, N=18 senza Lombardia e Molise.

| Coppia con `12SER027` | Rho 2023, N=20 | Rho senza estremi, N=18 | Intervallo 2019-2023, N=20 |
|---|---:|---:|---:|
| `12SER025`, dimissioni fuori regione | -0,503197 | -0,318018 | da -0,597065 a -0,467845 |
| `MULTI_ASL_FILA_OLTRE_20_MIN`, fila ASL | -0,547368 | -0,514964 | da -0,655639 a -0,509974 |
| `01SAL021`, multicronicità 75+ | -0,523505 | -0,525284 | da -0,813088 a -0,455639 |
| `MULTI_PRONTO_SOCCORSO`, uso PS | +0,422556 | +0,360165 | da +0,422556 a +0,713802 |
| `12SER004`, difficoltà servizi | -0,551958 | -0,522998 | da -0,644846 a -0,425452 |

Celle 2023 confermate nel CSV BES: Molise `12SER025` 32,6% delle dimissioni, Lombardia `12SER025` 5,1% delle dimissioni, Sardegna `12SER026` 13,7% di rinunce. Fra le 20 regioni, Molise e Lombardia sono rispettivamente massimo e minimo per la quota di dimissioni fuori regione. Il CSV Multiscopo definisce la fila ASL come quota di utenti con attesa oltre 20 minuti, non numero assoluto di persone né durata dell'attesa.

## Forza narrativa, motivo ed esito

Il racconto può reggere circa 700-900 parole: Lombardia e Molise mostrano che due classifiche non vanno lette come la stessa cosa; la Sardegna impedisce una regola semplice; PS e controllo senza estremi impediscono una conclusione comoda. Millecento parole rischiano di diventare un elenco di coefficienti. Angolo più forte: "una lista lunga non basta a dire come si cura una regione". Aprire sul contrasto territoriale e chiudere su ciò che il dato non permette di sapere per il singolo lettore, lasciando i rho al grafico e a poche frasi di metodo.

FERMO: un "no" al criterio 4 ferma lo scrittore. La correzione del primo gate è incompleta anche nella tesi: servono "quota di dimissioni" e "quota di utenti ASL", non conteggi. Formulazione massima consentita: "Nelle 20 regioni, nel 2023 una quota maggiore di medici di famiglia oltre soglia si associa a una minore quota di dimissioni fuori regione e di utenti con lunghe file ASL. Questo confronto non stabilisce quanto sia facile curarsi né perché le mappe differiscano". Eliminare l'esclusione su dotazione ed età e la promessa sulla durata della fila. Destinatario: leader Claude Sonnet 5.5; dopo questo secondo controllo, archiviare il brief secondo la sezione A, senza passaggio allo scrittore e senza nuove correlazioni selezionate.

Non verificato: cronologia indipendente dei controlli, microdati e pesi dell'indagine, incertezza delle stime, validazione indipendente, cause delle associazioni e riconciliazione integrale dei CSV con le tavole originali. Il ricalcolo ha riguardato cinque coppie e tre celle richieste, non l'intero dossier.
