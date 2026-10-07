# Gate A: medici di famiglia v2

Esito: FERMO
Data: 7 ottobre 2026. Unico giro del caporedattore.
Brief esaminato: `lavoro/medici-di-famiglia/v2/brief.md`.
SHA del brief e base della verifica: `a00c0943d79085ee5a60ba3ac8861282b3b08f01`.
Hash SHA-256 del brief: `47fad491c32062da8c08451d63a5eecbb5f5e682ef6f229353932a5ba5e12eba`.
Autore del brief: leader coordinatore, famiglia Anthropic Claude, modello Sonnet 5.5, come dichiarato nel brief.
Giudice: Codex, famiglia OpenAI GPT, modello GPT-6 Astra, `AGENT_ID=codex-gpt-6-astra`.
Domanda: avere un medico con troppi pazienti significa che nella propria regione è più difficile curarsi?
Tesi giudicata: più medici oltre soglia accompagnano servizi più raggiungibili e meno ricoveri fuori regione, dunque la quota misurerebbe l'organizzazione e non la carenza di medicina di base.
Codici e confronto: `bes:12SER027` contro `bes:12SER004`, `bes:12SER025`, `bes:01SAL021`, `ims:MULTI_ASL_FILA_OLTRE_20_MIN`, `ims:MULTI_PRONTO_SOCCORSO`, sulle stesse 20 regioni, etichetta 2023 e controlli 2019-2023.

| criterio | sì/no | prova | limite |
|---|---|---|---|
| 1. Corregge la classifica e risponde al lettore | no | Esiste una discordanza territoriale verificata, utile a contestare la sufficienza della sola quota MMG. | Il brief la trasforma in "non sono quelle dove è più difficile curarsi". Servizi essenziali, fila amministrativa e dimissioni non dimostrano questa conclusione sull'accesso alle cure. |
| 2. Tre misure pertinenti, anni e popolazioni compatibili | no | Gli incroci sono reali, regionali e con N=20, non tre classifiche affiancate. | L'accesso etichettato 2023 è una media 2022-2024. MMG, famiglie, utenti ASL, over 75 e dimissioni hanno denominatori diversi, impropriamente assimilati al disagio sanitario individuale. |
| 3. Formula, chiavi, N ed esclusioni in numeri.md | no | Matrice 2023 e chiavi delle 20 regioni sono presenti. Il calcolo è riproducibile con ranghi medi. | Mancano in numeri.md gli esiti dei nuovi controlli 2019-2023 e senza estremi, riferiti solo nel brief/script. La tabella attribuisce erroneamente percentuali a PS e guardia medica. |
| 4. Risultato distinto dalla causa | sì | Il meccanismo è dichiarato ignoto, opzione espressamente ammessa dalla sezione A. | Ciò non autorizza "misura come è organizzata" né "non è l'età, non è la dotazione". Queste frasi restano da eliminare, inclusa l'ipotesi degli studi associati senza fonte. |
| 5. Controllo contrario scelto prima del calcolo | sì | Secondo la dichiarazione nel brief/script, anni alternativi ed esclusione di Lombardia/Molise precedono il loro calcolo. Ricalcolo conferma segni e conserva l'indebolimento della mobilità. | È un controllo descrittivo dopo la selezione nella matrice, non una conferma indipendente o una preregistrazione. La cronologia dichiarata non è provata separatamente. |

## Verifica indipendente
Eseguito `bin/py lavoro/medici-di-famiglia/v2/calcola_incroci.py`, exit 0. Secondo calcolo autonomo in memoria dai CSV, senza importare script o viste del sito.
Input: `app/static/data/Assoluti_BES_Regione.csv` e `app/static/data/Assoluti_Multiscopo_Regione.csv`. Filtri: Area=Regione, Livello/Variazione=Livello, codice e anno. Chiave univoca codice/anno/Territorio, nessun mancante nelle coppie verificate.
Formula indipendente: rango = 1 + valori inferiori + (numero di pari - 1)/2. Rho = Sxy / sqrt(Sxx × Syy), somme dei prodotti e quadrati dei ranghi centrati. Nel 2023 rango medio=10,5 e Sxx MMG=665.
Le 20 regioni sono quelle elencate in numeri.md, con Trentino Alto Adige aggregato, senza Bolzano/Trento aggiuntivi. Esclusione congiunta di Lombardia e Molise: N=18.

| Misura contro MMG | Rho 2023, N=20 | Sxy / Syy | Rho 2023, N=18 | Min/max rho 2019-2023, N=20 ogni anno |
|---|---:|---|---:|---|
| Difficoltà servizi, 12SER004 | -0,551958457 | -366,5 / 663 | -0,522998045 | -0,644846 / -0,425452 |
| Fila ASL, MULTI_ASL_FILA_OLTRE_20_MIN | -0,547368421 | -364 / 665 | -0,514963880 | -0,655639 / -0,509974 |
| Multicronicità, 01SAL021 | -0,523505114 | -348 / 664,5 | -0,525283798 | -0,813088 / -0,455639 |
| Emigrazione, 12SER025 | -0,503196726 | -334,5 / 664,5 | -0,318017595 | -0,597065 / -0,467845 |
| Pronto soccorso, MULTI_PRONTO_SOCCORSO | +0,422556391 | 281 / 665 | +0,360165119 | +0,422556 / +0,713802 |

Celle BES confermate, etichetta 2023: Lombardia MMG 74,0% (riga CSV 36150), Molise MMG 21,6% (36190), Molise emigrazione 32,6% (35620), Lombardia difficoltà 3,2% (32315). Il 32,6% riguarda dimissioni ordinarie per acuti dei residenti fuori regione, non il 32,6% delle persone molisane.
Il CSV multiscopo dà PS Lombardia 64,8 per 1.000 persone e guardia 20,2 per 1.000, non 64,8% e 20,2%. Correggere entrambe le intestazioni in numeri.md. La conversione uniforme non cambia i rho.
Il range PS del brief +0,54/+0,71 omette il 2023: per 2019-2023 è +0,42/+0,71. Tutti i cinque rho puntuali 2023 sono invece confermati.

## Motivo e limiti obbligatori
Insight sì come associazione esplorativa circoscritta, no come tesi attuale sull'accesso alle cure e sull'organizzazione. Il brief non è pronto per lo scrittore.
La matrice contiene 13 × 12 / 2 = 78 coppie distinte, di cui 12 con MMG. Lo script stampa 169 celle, contando diagonale e simmetrie. Questo è il perimetro documentato, non la prova che non siano state esplorate altre combinazioni.
La selezione delle relazioni dopo la matrice aumenta il rischio di risultati casuali selezionati. Anni sugli stessi territori non sono repliche indipendenti, e le medie mobili di accesso si sovrappongono. Non dichiarare significatività, robustezza confermativa o causalità: nessuna correzione per selezione, incertezza campionaria o dipendenza territoriale è stata stimata.
Unità diverse non vietano Spearman. Permettono però solo un confronto ecologico di ordinamenti, senza un punteggio unico di disagio né conclusioni sul paziente. Almeno accesso, fila ASL, multicronicità e uso PS sono misure autodichiarate della stessa indagine AVQ, non due sole misure o conferme indipendenti.
Accesso significa molta difficoltà a raggiungere almeno tre servizi essenziali, anche non sanitari. La fila ASL non misura liste cliniche. La mobilità non misura il motivo del ricovero fuori regione. Una debole correlazione con medici totali non esclude carenza di MMG.
Fonte ufficiale aperta oggi: [Istat, Bes 2024, Qualità dei servizi](https://www.istat.it/wp-content/uploads/2025/11/12-Qualita-dei-servizi.pdf), p. 212 nota d: anno centrale della media mobile. Dunque la cella accesso 2023 riguarda il triennio 2022-2024. Lo stesso capitolo, p. 219, distingue dotazione MMG da medici totali e descrive maggiore carico nelle regioni con meno MMG, senza spiegare le correlazioni qui analizzate.

## Correzione richiesta e destinatario
Destinatario: leader Claude Sonnet 5.5. Un solo ritorno mirato al leader, nessun passaggio allo scrittore ora. Se resta insufficiente dopo il ritorno, archivio secondo la sezione A.
1. Ridimensionare la tesi, eliminare le esclusioni causali e correggere persone/dimissioni. Formulazione massima: "Nelle 20 regioni, nel 2023 una quota maggiore di medici di famiglia oltre soglia si associa a una minore quota di dimissioni fuori regione e di utenti con lunghe file ASL. Questo confronto non stabilisce quanto sia facile curarsi né perché le mappe differiscano".
2. Tenere l'accesso ai servizi come contesto triennale esplicito, oppure riallineare la finestra delle misure prima di farne l'incrocio centrale. Motivare la compatibilità solo territoriale dei denominatori. Trasferire in numeri.md codici, finestre, N, esclusioni, risultati negativi e controlli, correggendo unità PS/guardia e range PS.
3. Dichiarare la ricerca esplorativa su 78 coppie e la scelta successiva dei controlli. Conservare la fragilità dell'emigrazione senza estremi e il segno opposto del PS. Non chiedere nuove correlazioni selezionate per salvare la tesi.

Non verificato: cronologia indipendente della scelta dei controlli, microdati e pesi AVQ, incertezza delle stime, validazione su dati indipendenti, causa delle associazioni e riconciliazione integrale dei CSV con le tavole originali. Verifica numerica limitata ai cinque incroci e alle celle indicate, non all'intero dossier.
