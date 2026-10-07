# Gate A ter: medici di famiglia v2 (verifica mirata, ultimo controllo)

Esito: PASSA, con i limiti obbligatori elencati sotto. Data: 7 ottobre 2026. Terzo e ultimo controllo, un solo giro, contesto pulito.
Brief esaminato: `lavoro/medici-di-famiglia/v2/brief.md`, versione 3, commit `efec4f33152e7add36a1f61a97ef06c9c4aed1c7`.
Hash SHA-256 del brief: `b00a48fcdbf67c5b84f977c3b12572773157969527c5ea0abeb2ebe834ae731a`.
Autore del brief: leader Claude Sonnet 5.5, famiglia Anthropic. Primi giudici: Codex GPT-6 Astra (gate A), Codex GPT-6 Sol (gate A bis), famiglia OpenAI.
Giudice di questo gate: Claude Fable 5.1 (`claude-fable-5-1`), famiglia Anthropic, lanciato da Orca. Stessa famiglia del leader, ma modello diverso e contesto nuovo: lo dichiaro perché la spec chiedeva una terza famiglia e il lanciatore ha scelto Claude.
Domanda: il numero di assistiti del mio medico dice quanto è difficile curarsi nella mia regione?
Tesi giudicata (riga 9): nel 2023, nelle 20 regioni, una quota maggiore di MMG oltre soglia si associa a una minore quota di dimissioni fuori regione e di utenti con lunghe file ASL: il confronto non stabilisce quanto sia facile curarsi né perché le mappe differiscano.
Codici e confronto: `bes:12SER027` con `bes:12SER025`, `ims:MULTI_ASL_FILA_OLTRE_20_MIN`, `bes:01SAL021`, `ims:MULTI_PRONTO_SOCCORSO`, contesto `bes:12SER004`. Regioni, N=20, 2023, controlli 2019-2023 e N=18.

## Le quattro verifiche chieste dalla direzione, riga per riga

| Verifica | Sì/no | Prova (riga del brief v3) | Limite |
|---|---|---|---|
| (a) Nessuna esclusione causale («non è la dotazione né l'età» o simili) | sì | Riga 18 ora dice: esiti deboli «da citare solo come "nessun ordinamento comune evidente nelle regioni" e mai come esclusione di un fattore». Righe 14 e 27 nominano la frase solo per vietarla. Grep su «dotazione», «età», «esclud», «non è l'»: nessun'altra occorrenza. | Riga 12 «non regge come termometro» e riga 23 «descrive quante liste sono lunghe, non quanto è facile o difficile curarsi» restano affermazioni su ciò che il dato non dice, non esclusioni di un fattore: vanno scritte come «da solo non basta», non come verdetto. |
| (b) Nessuna promessa sulla durata della fila ASL | sì | Riga 23: «quante persone dichiarano una fila oltre 20 minuti allo sportello ASL (una quota di utenti, non la durata dell'attesa)». «Quanto si aspetta» non c'è più in nessuna riga. | «Quante persone dichiarano» è ancora un conteggio: lo scrittore scriva «quale quota di utenti dichiara». La parentesi corregge, il verbo no. |
| (c) Tesi entro la formulazione massima del gate bis | sì | Riga 9 riprende parola per parola «quota maggiore di medici di famiglia oltre soglia», «minore quota di dimissioni fuori regione e di utenti con lunghe file ASL», «non stabilisce quanto sia facile curarsi né perché le mappe differiscano». Solo i due punti al posto del punto. | Nessuna. Riga 12 allinea anche l'insight («è minore la quota di dimissioni», «la quota di utenti»). |
| (d) Nessuna frase nuova contro le tre correzioni o i cinque criteri | sì | `git diff 849310ee efec4f33` sul brief tocca solo le righe 9, 12, 18 e 23, tutte in senso restrittivo. Nessuna aggiunta altrove. | Rientrano dal v2, non nuove: riga 12 «meno anziani di 75 anni o più» (01SAL021 è una quota) e riga 29 titolo d'esempio «meno dimissioni avvengono fuori regione» (12SER025 è una quota di dimissioni). Vedi limiti obbligatori. |

## Verifica indipendente dei numeri

Script mio, in memoria, dai soli CSV `Assoluti_BES_Regione.csv` e `Assoluti_Multiscopo_Regione.csv` (separatore `;`, `Area=Regione`, `Livello/Variazione=Livello`), senza importare `calcola.py` né `calcola_incroci.py`. Ranghi medi sui pari, rho = Sxy / sqrt(Sxx · Syy) sui ranghi centrati. Le 20 regioni sono quelle di `numeri.md`, Trentino Alto Adige aggregato, nessun mancante.

| Coppia con `12SER027` | Rho 2023, N=20 | Rho 2023, N=18 senza Lombardia e Molise | Min / max 2019-2023, N=20 |
|---|---:|---:|---|
| `12SER025` dimissioni fuori regione | -0,503197 | -0,318018 | -0,597065 (2019) / -0,467845 (2021) |
| `MULTI_ASL_FILA_OLTRE_20_MIN` fila ASL | -0,547368 | -0,514964 | -0,655639 (2021) / -0,509974 (2019) |
| `01SAL021` multicronicità 75+ | -0,523505 | -0,525284 | -0,813088 (2019) / -0,455639 (2020) |
| `MULTI_PRONTO_SOCCORSO` uso PS | +0,422556 | +0,360165 | +0,422556 (2023) / +0,713802 (2019) |
| `12SER004` difficoltà servizi | -0,551958 | -0,522998 | -0,644846 (2022) / -0,425452 (2021) |

Tutti identici a `numeri.md`, `gate-a.md` e `gate-a-bis.md` al sesto decimale; il segno non cambia in nessun anno 2019-2023, come dice la riga 12. Celle 2023 confermate: Lombardia MMG 74,0 e dimissioni 5,1 (minimo delle 20), Molise MMG 21,6 e dimissioni 32,6 (massimo), Sardegna MMG 60,6 e rinunce 13,7. Italia 15,8 (2004) e 51,7 (2023) confermati solo da `data/derived/bes_areas_12SER027.csv`, non dalla tavola Istat.

## Limiti obbligatori da scrivere nel pezzo (per scrittore e gate B)
1. Ogni misura è una quota, mai un conteggio: «quota di dimissioni», «quota di utenti ASL», «quota di anziani 75+». Vale anche per il titolo del grafico (riga 29): non «meno dimissioni avvengono fuori regione» ma «la quota di dimissioni fuori regione è più bassa».
2. Il 32,6% del Molise è una quota di dimissioni ordinarie per acuti, non di persone; la fila ASL è la quota di utenti oltre 20 minuti, non una durata né le liste d'attesa cliniche; il 13,7% della Sardegna va scritto «circa una su sette» o con la cifra, non «una su sette» secco.
3. Dichiarare in una frase l'esplorazione (78 coppie, relazioni scelte dopo la matrice, controlli non provati cronologicamente, anni non indipendenti). Niente significatività, niente causa, nessuna esclusione di fattori: gli esiti deboli si citano solo come «nessun ordinamento comune evidente».
4. Il risultato contrario resta nel testo: pronto soccorso di segno opposto (+0,42) e dimissioni che scendono a -0,32 senza i due estremi. L'accesso ai servizi (12SER004) solo come contesto triennale 2022-2024, non come incrocio centrale.
5. «Non regge come termometro» e «non quanto è facile curarsi» si scrivono come limite del singolo dato («da solo non basta a dire»), mai come verdetto sull'accesso alle cure di una regione. La freccia «→» della riga 24 non va nel pezzo (STYLE.md).

Motivo: i due «no» del gate bis sono rimossi, la tesi è nella formulazione massima, i numeri reggono a un terzo ricalcolo. Destinatario: coordinatore, per il passaggio allo scrittore; la label gate-a vale per il commit `efec4f33` e decade se la tesi cambia.
Non verificato: cronologia dei controlli, microdati e pesi AVQ, incertezza delle stime, cause, riconciliazione dei CSV con le tavole Istat, il valore Italia 2004-2023 sulla fonte primaria, l'intero dossier oltre le cinque coppie e le sette celle citate.
