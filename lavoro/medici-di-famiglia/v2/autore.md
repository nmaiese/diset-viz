# Autore (cronista): medici di famiglia v2, il racconto

File: `content/posts/2026-10-07-medici-di-famiglia-regioni.md` (767 parole per `guardia_articolo`, tetto 1100). Dataset: `app/static/data/articles/medici-di-famiglia-regioni.csv`. Esito guardia: un solo errore, atteso, la figura `dispersione-dimissioni` non ha ancora l'SVG (lo fa un altro ruolo). Grep `[—–;…]` vuoto su articolo e CSV. Link interni tutti 200 su divarioitalia.it.

## Cifre usate e dove le ho prese
- Lombardia MMG oltre soglia 74,0, Molise 21,6, Sardegna 60,6 (2023): `numeri.md`, CSV `Assoluti_BES_Regione.csv` (12SER027).
- Dimissioni fuori regione Molise 32,6, Lombardia 5,1, Sardegna 7,1 (2023): `numeri.md` (le prime due), CSV BES 12SER025 (Sardegna).
- Rinuncia Sardegna 13,7 (2023, circa una su sette): `numeri.md`, CSV BES 12SER026. «Più alta fra le venti regioni»: controllato sul CSV (secondo Lazio 10,5).
- Fila ASL oltre 20 minuti Lombardia 47,1, Molise 67,6 (2023): CSV `Assoluti_Multiscopo_Regione.csv`, righe 1475 e 1491. Non sono in `numeri.md`: le ho prese dal CSV.
- Pronto soccorso Lombardia 64,8, Molise 39,8 per 1000 (2023): `numeri.md` e CSV Multiscopo.
- Rho -0,50 (-0,503), -0,32 (-0,318), fila -0,55 (-0,547) e -0,51 (-0,515), PS +0,42 e +0,36: tabella «Incroci» di `numeri.md` e ricalcolo del gate A ter. Non li ho ricalcolati io.
- Italia 15,8 (2004) e 51,7 (2023): CSV v1 e `data/derived/bes_areas_12SER027.csv` (gate A ter).
- 78 coppie: `numeri.md`.
- «Più di ogni altra regione del Mezzogiorno» (Sardegna 60,6, Campania 58,8): dal CSV del v1.

## Dove ho dovuto scegliere fra racconto e cautela
- Apertura «La Lombardia starebbe peggio, il Molise meglio»: è la lettura comune del numero, scritta al condizionale e subito rovesciata. Rischio: il lettore la prende per tesi nostra.
- «Anche la fila allo sportello va nello stesso senso» (Lombardia 47,1, Molise 67,6): vale per i due estremi, non per ogni regione (Sicilia 68,4 è sopra il Molise). Il testo non dice «più alta d'Italia» per la fila.
- «Dove più medici superano i 1500 assistiti, la quota di dimissioni è più bassa»: è l'indice a dirlo, formulato come associazione, mai come causa.
- Sardegna «sta con la Lombardia» sulle dimissioni (7,1 contro 5,1): approssimazione di racconto, entrambe nella parte bassa. Lo scrivo senza dire «uguale».
- Il motivo della rinuncia (economico, scomodità, lista d'attesa) viene dalla definizione di 12SER026, non da una causa regionale.
- Non ho usato: multicronicità 75+ (-0,52), difficoltà ai servizi 12SER004 (contesto triennale), gli esiti deboli salvo «nessun ordinamento comune evidente» per le rinunce. Per spazio e per tenere il filo.

## Limiti del gate A ter, dove stanno
1 quote e non conteggi: ovunque («quota di dimissioni», «quota di utenti»). Nel pronto soccorso «una quota più alta di persone». 2 il 32,6% è una quota di dimissioni ordinarie per acuti, la fila è quota di utenti oltre 20 minuti, 13,7% «circa una su sette». 3 una frase di esplorazione (sezione «Una coppia scelta tra tante»). 4 PS +0,42 e dimissioni -0,32 nel testo. 5 «da solo non basta», nessuna freccia.

## Non verificato
- Rho ricalcolati da me: nessuno, mi fido di `numeri.md` e gate A ter.
- Il grafico (non esiste ancora l'SVG; il titolo del grafico deve rispettare il limite 1).
- Pagina del sito col dato in produzione: solo 200 sui link, non il contenuto.
- La lettura a 375 px, il rendering della bozza HTML.
- La copertina e la licenza restano quelle del v1, non riverificate.
