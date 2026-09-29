# La issue di un pezzo del blog

Il formato del corpo della issue con cui parte un articolo del blog. Lo
prescrive `PIANO.md` in questa cartella ("Il flusso di un pezzo", passi 1 e 2,
e "Il team" per la regola di rotazione).

## Come si usa

Il giorno dei trend, dopo `collect` e `rank`, il leader copia il modello qui
sotto in un file fuori dal worktree, lo compila e apre la issue:

```bash
gh issue create --label run:blog --title "Blog, trend del <AAAA-MM-GG>" --body-file <file>
```

Nessuna domanda a Nello e nessun worker aspetta una sua risposta: il leader
sceglie tema e angolo, scrive il motivo, e Nello rivede alla fine nella PR.

1. **Il tema.** Il leader scrive una rosa di tre-cinque temi presi dalla
   classifica, ne sceglie uno e scrive perché nello spazio "Tema scelto".
2. **L'angolo.** Sul tema scelto il leader scrive due angoli candidati, diversi
   fra loro nella tesi e non solo nelle parole, sceglie uno e scrive perché
   nello spazio "Angolo scelto". Un worker di famiglia diversa, in sola lettura,
   dà un secondo sguardo (il bersaglio esiste alla lettera, la tesi si può
   contestare, la prova contraria è la più forte) e può mettere il veto solo su
   un bersaglio inventato o su un uomo di paglia. L'esito va sotto "Secondo
   sguardo".

Il corpo della issue passa, tale e quale, nella sezione "Come è stato scelto"
del corpo della PR, perché Nello veda da dove viene il pezzo.

Il bersaglio di un angolo è un'affermazione che esiste davvero, copiata alla
lettera con URL e data: un titolo, la frase di chi fa la politica, il
presupposto di un piano. Se è un titolo dai segnali di Google News, l'URL è
quello del segnale finché lo scout non lo sostituisce con l'URL aperto della
testata e la citazione verificata.

La sezione `## Stato` sta in fondo al corpo e si **riscrive sul posto** a ogni
passo (`gh issue edit <n> --body-file <file>`), mai in un commento: tutti gli
agenti scrivono con l'identità di Nello, e `--edit-last` toccherebbe l'ultimo
commento di chiunque. Per ogni ruolo lanciato si scrive l'agente, il motivo
della scelta secondo la regola del piano (vincoli duri, il meno usato negli
ultimi pezzi, il ruolo più difficile prende il migliore) e la quota letta con
`orca-stato.sh` o `agent-probe.sh` prima del lancio, con l'ora.

La rosa segue l'ordine della classifica e mostra anche i temi che una regola
tiene fuori, con il motivo scritto nel rischio, perché la scelta si rilegge alla fine.
Le regole legano la scelta: un tema non torna prima di 30 giorni dall'ultimo
pezzo sullo stesso tema, e il tetto è di 8 pagine nuove a settimana, blog e
schede insieme.

Ogni titolo citato, nell'aggancio o nel bersaglio, porta subito dopo il suo URL.
Quello che il leader ne ricava si scrive a parte, come sua lettura, non dentro
la citazione.

## Il modello

```markdown
### La rosa dei temi, trend del <AAAA-MM-GG>

Classifica: `data/trend/<AAAA-MM-GG>/ranking.md`. Segnali: `data/trend/<AAAA-MM-GG>/signals.json`.

**1. <tema>** (punteggio <totale>, posto <n> in classifica, indicatore `<id>`)
- Aggancio: "<titolo vero>", <testata>, <data>. <URL>
- Punteggio: interesse <x>, dato <y>, storia <z>. <nota della classifica, in parole>
- Rischio: <aggancio debole, dato che non tiene una storia, tema già scritto>
- Già nel mese: <nessun pezzo | `content/posts/<file>.md`, <data>>

**2. ...**

### Tema scelto

<!-- il numero o il nome del tema, e perché in tre righe -->

### I due angoli candidati

Tema: <tema>. Coppia tema-indicatore: `<id>`, con `<id>` di contorno.

**Angolo A. <la tesi, in una frase con cui si può non essere d'accordo>**
- Bersaglio: "<affermazione alla lettera>", <chi>, <dove>, <data>. <URL>
- Lettura del leader: <che cosa del bersaglio il pezzo contesta, in una riga>
- Prova contraria: <la più forte, e come il pezzo la tratta>
- Che cosa cambia per chi legge: <in parole semplici, è la chiusa del pezzo>

**Angolo B. <...>**
- Bersaglio:
- Lettura del leader:
- Prova contraria:
- Che cosa cambia per chi legge:

### Angolo scelto

<!-- A o B, o la correzione in una riga -->

## Stato
Fase: <rosa proposta | angoli proposti | scout | brief | scrittore | grafico e foto | PR draft | revisore giro <n> | riparazione <n> | PRONTA PER NELLO | unita>
SHA: <ultimo commit del ramo nmaiese/blog-<slug>, o nessuno>
Prossimo passo: <una riga>
Chi lo fa: <leader | Nello | ruolo e agente>
Agenti:
- scout: <agente e modello>, perché <motivo>, quota <valore letto> alle <ora>
- scrittore: ...
- grafico e foto: ... (deve vedere le immagini)
- revisore: ... (famiglia diversa dallo scrittore)
- secondo parere: ...
```

## Un esempio compilato, trend del 29 settembre 2026

Con i dati veri di quel giorno: la classifica è `data/trend/2026-09-29/ranking.md`,
gli agganci sono titoli di `data/trend/2026-09-29/signals.json`, le cifre degli
angoli vengono dalla bozza sulla casa del 29 settembre (ramo
`nmaiese/art-casa-0929`, dati Istat Bes 2025 ed Eurostat Eu-Silc 2025). Il
pilota del piano è proprio questo tema.

```markdown
### La rosa dei temi, trend del 2026-09-29

Classifica: `data/trend/2026-09-29/ranking.md`. Segnali: `data/trend/2026-09-29/signals.json`.

**1. Energia e bollette** (punteggio 0,95, primo in classifica, indicatore `bes:10AMB016`, energia elettrica da fonti rinnovabili)
- Aggancio: "gasolio" fra le ricerche di tendenza del 29 settembre 2026, con "Price cap ai carburanti anche per Q8. 'Sconto sul gasolio fino al 5 ottobre, poi accise mobili'", ANSA, 29 settembre 2026. https://www.ansa.it/sito/notizie/economia/2026/09/29/price-cap-ai-carburanti-anche-per-q8.-sconto-sul-gasolio-fino_6531a720-8d40-4446-9ea8-50d214ad9a06.html E "Eni: da Plenitude sconto 30% su bollette luce e gas, prezzo bloccato due anni", Sky TG24, 29 settembre 2026. https://news.google.com/rss/articles/CBMid0FVX3lxTE9kclJHaXY3WlV0bDVDQmZMQzBOUTY1dXBKc1JPa3pUTHhOZGZXenY1WEV3dGNvUHhEaWJqUEtzLU9NS0cybDBSSElKTXZQalI2bHNiMU1QUXFkRjh4U1FiaTR0dW9jNDJuUFVSRU1LbDUwRTREamZR?oc=5
- Punteggio: interesse 1,0, dato 0,9, storia 1,0. La Valle d'Aosta produce da rinnovabili 327,8 contro una media dei territori di 66,6 (2024).
- Rischio: l'aggancio parla di prezzi, l'indicatore di produzione. Il legame fra rinnovabili e bolletta di una famiglia non sta nel dato regionale, e la bozza del 29 settembre ha trovato una tesi che cambiava segno cambiando il metodo di calcolo.
- Già nel mese: nessun pezzo pubblicato. C'è la bozza non unita del 29 settembre, ramo `nmaiese/art-energia-0929`.

**2. Scuola e competenze** (punteggio 0,907, quarto in classifica, indicatore `prov:02IST010P`, competenza numerica non adeguata)
- Aggancio: "Gratteri su dispersione scolastica: "Ragazzi non istruiti diventano schiavi della Camorra"", Sky TG24, 29 settembre 2026. https://news.google.com/rss/articles/CBMi1wFBVV95cUxQRlpQdmhHRlplMkRHM2Nld3BIYlUwZkdUdERja3FQRi1QcFFJWGFzaldoRU1ZakpaUVpBOVRYdTI3NURJcWs1ZUJFZzlDd3JReVE1ZjRZR3ZsNjFtaGVVckFGVHNvb3d2aWVZSHl3VTFwb2lVOUZyRUo0MlRBV2hPczFYUnJicEFqNnBidWh4YVVuU2VUZnU3MUMwTERQN25zSU1kQUlCRFN3TTVtRVZMamM4OFpCZURySFNDazJxSXcwczNCcmRMenZNRkszb1ZKdHVpbXF2TQ?oc=5
- Punteggio: interesse 0,96, dato 0,89, storia 1,0. A Crotone il 71,9% degli studenti non raggiunge una competenza numerica adeguata, contro una media dei territori di 44,2 (2024).
- Rischio: il tema è già stato scritto nel mese, e la regola dei 30 giorni lo tiene fuori fino al 23 ottobre. Il segnale più forte della settimana è il decreto sul tetto agli studenti stranieri, che è un altro argomento.
- Già nel mese: `content/posts/2026-09-23-scuola-media-competenze-nord-sud.md`, 23 settembre 2026.

**3. Casa e affitti** (punteggio 0,845, decimo in classifica, indicatore `ims:MULTI_ABIT_SPESA_REDDITO`, con `bes:SDG-222` sovraccarico del costo dell'abitazione, 0,766)
- Aggancio: "Immobili: Foti, su stretta Ue affitti brevi ci sia clausola nazionale", Il Sole 24 ORE, 23 settembre 2026. https://news.google.com/rss/articles/CBMibEFVX3lxTE5iMVMwTlhMSk1hYmNBb2RKSU95NHJwM2lKM1VwTVhJNjQ5cUtWam9qTXl2S1c0ZFJuNmI4VzV6WExzcEtFSkNUU21GUVowNm1xbG9xOUIyWjVSc0dWdVR2RG5SbnVNVjVMWFZnMw?oc=5 E, fra le notizie principali, "In Spagna niente più sfratti fino al 2030: approvato il "decreto Maricarmen" dopo le proteste per la crisi abitativa", Il Fatto Quotidiano, 29 settembre 2026. https://news.google.com/rss/articles/CBMioAFBVV95cUxOSXFFM3pBTHJ3UC1HZUZYSUctRXFUMVZDWW1MbFdDSHhUaS00MWpSYlJWR1pMenB0UlpoSm9FQWJSWEoyWlpWcV9QM3ptd3A5Q1l0Ym5oUWtETXhTQUIyTGhqajFsd1VLaVpEYkZWQVF6R2dZY1FxcTgzZG5GajBsUGJFMlZZRTYxZ01xX3ZpcXpqX25DX3IzSk9DOFRNdzk2?oc=5
- Punteggio: interesse 0,88, dato 0,95, storia 0,97. La nota della classifica ("divario allargato del 97%") è calcolata su medie dei territori: i valori Istat per ripartizione della spesa sul reddito scendono ovunque dal 2018 al 2025, quindi non è una notizia da titolo.
- Rischio: i dati non misurano gli affitti brevi, che sono il centro del dibattito. Il sovraccarico regionale è campionario e nel 2025 manca per sei regioni.
- Già nel mese: nessun pezzo pubblicato. C'è la bozza non unita del 29 settembre, ramo `nmaiese/art-casa-0929`: il pilota la rifà.

### Tema scelto

3, casa e affitti. Perché: l'aggancio è italiano e recente (Foti, 23 settembre), il dato tiene una storia, è il pilota del piano e permette il confronto con la bozza del 29 settembre.

### I due angoli candidati

Tema: casa e affitti. Coppia tema-indicatore: `bes:SDG-222`, con `ims:MULTI_ABIT_AFFITTO` e il sovraccarico per titolo di godimento di Eurostat (`ilc_lvho07c`) di contorno.

**Angolo A. Chi rischia con la casa non è una regione, è chi paga un affitto di mercato.**
- Bersaglio: "A Milano nasce la Società della Casa: un piano pubblico per gli affitti a canone calmierato dedicati al ceto medio", MilanoToday, 28 settembre 2026. https://news.google.com/rss/articles/CBMiigFBVV95cUxOQmM1eWUwTTVCNkRZUnBvV3FYbHlLV0xLWVRXY1NWdXJ6dTVaUW5malZ5WnRYWl9fTGxnZ0hMaXplblFYTUVNZWoyeGFqYW14b3hIOE5mVVdBYTVtbGJIcnlHVFRpY2hjbVNrejduX3A0ZFlVUFJJRmNERlBnN1c2TFJoaTNtS1Bib1E?oc=5
- Lettura del leader: i piani di questi giorni scelgono una città e una fascia di reddito, il ceto medio. Il dato dice che la linea che conta è un'altra, pagare o no un affitto di mercato.
- Prova contraria: il territorio conta ancora. Il sovraccarico è 6,1 nel Mezzogiorno e 4,1 al Nord, e la Campania è prima con 8,4. Il pezzo la tratta dicendo che il divario fra chi affitta e chi possiede (22,3% contro 1,3% e 2,1%) è molto più largo di quello fra regioni, e che l'Istat non pubblica i due tagli insieme.
- Che cosa cambia per chi legge: se paga un affitto a prezzo di mercato, sta in un gruppo dove poco più di una persona su cinque spende oltre il 40% del reddito per la casa, in qualunque regione abiti. Un alloggio calmierato aiuta soprattutto chi sta in quel gruppo.

**Angolo B. L'emergenza casa si racconta dalle città del Centro-Nord, ma le regioni dove più persone sono schiacciate dalla casa sono la Campania e la Liguria.**
- Bersaglio: "L'emergenza abitativa: "Città sotto pressione"", La Nazione, 27 settembre 2026. https://news.google.com/rss/articles/CBMimgFBVV95cUxPMzhhcG0za2h4YUlmNzFsc2lzM2xaNjZZT25jcHVXaWhnVG8wa0dWSklqVmJDNDNoYV9lWHRRVVF1Wjd3RkNpSFRDejhqbXBaZ2UzWkZYdjZKRUo3OEU3WHl4QWdRdnJYUTNid3NpQWNZTGItTnNkbTdYRlAzVDhqZnZ4THpYMUFNVWRSa0tGaU5VNVdNWlVuQmx3?oc=5 E "Casa in Emilia-Romagna, piano da 300 milioni per 3.500 alloggi: affitti medi a 350 euro", BolognaToday, 24 settembre 2026. https://news.google.com/rss/articles/CBMipwFBVV95cUxNVXRSUDlld0FhZ01Vam9EVk15NU5ZdXVfLUtSekpkbUE1TDdVeExuQ1YxLUNSaU0zQjZYSkhVOW1QREVKSDFiWFlSaVpxVk5Ba1pfMTZVdzh3REtVNWpkaUJwZC1pTmREVkNucHhiREE0TG9HWjNBUEc2QVFaMm9hSGsxdjNyVnhwTmZOS3RMc3p6V1UxOHppOENEUTd0azZWbFd3MEVBbw?oc=5
- Lettura del leader: nei titoli di questi giorni l'emergenza ha la geografia delle città del Centro-Nord (Milano, Bologna, Modena, Siena, Udine), e i primi soldi pubblici vanno lì.
- Prova contraria: un valore regionale nasconde la città. "Stangata affitti in provincia: a Modena i canoni liberi crescono del 35% in sette anni", ModenaToday, 24 settembre 2026 (https://news.google.com/rss/articles/CBMitAFBVV95cUxQcXFaQmZxZXNsUEswcUs1TGNTZ1VVOGtKVFFCVFNFdjBnSXMwUkl2WUU3ekJTUm5vVUtfZldZRVV6UWd0bHo1Mjd0dGhZb0M3d3NvSUt4X0Q1LVBfTUJoaHptbU0yQXpuR2F6WEVYM0tNRFJmNE04SnBZTDNUekd3Y0dIQmozNXktNS1laVl4dTNkOWZHd21zak53X3JyNGQ1aExOclZIY2h5N3o4TERQeUFBLU4?oc=5), e l'Emilia-Romagna ha il sovraccarico più basso dopo il Trentino Alto Adige, 3,1. Il pezzo la tratta separando il prezzo dell'affitto dal peso sul reddito: dove i redditi sono più alti, un canone alto pesa meno.
- Che cosa cambia per chi legge: i soldi pubblici per la casa seguono il dibattito. Chi cerca casa in Campania o in Liguria ha più probabilità di spendere oltre il 40% del reddito per la casa che in Emilia-Romagna, e di questo si parla meno.

### Angolo scelto

<!-- A o B, e perché in tre righe -->

### Secondo sguardo

<!-- esito del worker di famiglia diversa: bersaglio, tesi, prova contraria; veto sì o no -->

## Stato
Fase: angoli proposti
SHA: nessuno, il ramo `nmaiese/blog-casa-affitti` non esiste ancora
Prossimo passo: scelta dell'angolo e secondo sguardo, poi worktree senza agente da origin/master e scout
Chi lo fa: leader
Agenti:
- scout: non ancora scelto. Vincoli: web con URL aperti. Quota da leggere prima del lancio.
- scrittore: non ancora scelto. Codex escluso finché la quota non risale (circa 11% fino al 3 ottobre, dato del piano del 29 settembre, da rileggere). OpenCode non primo candidato.
- grafico e foto: non ancora scelto. Deve vedere le immagini: Claude o Antigravity, oppure il leader.
- revisore: non ancora scelto. Famiglia diversa dallo scrittore.
- secondo parere: non ancora scelto.
```

Una volta scelto e lanciato, una riga di agente si legge così: `scrittore:
claude (opus), perché è il ruolo più difficile e Codex è sotto quota, quota
<valore letto> alle <ora> con orca-stato.sh`.
