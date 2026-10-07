# Meno furti in casa, ma sentirsi sicuri è un'altra cosa

Tipo: blog
Issue: #357 · PR draft: #358
Chiave: `furti-sicurezza-percepita`
Stato: brief per Gate A. Non è una bozza e non è un giudizio di Gate A.

Autore: Claude Sonnet 5.5 (leader). Giudice atteso: Astra, contesto nuovo, famiglia diversa.
Numeri, formule e chiavi: `lavoro/furti-sicurezza-percepita/numeri.md`. Fonti: `fonti.md`. Censimento: `copertura.csv`.

## Domanda del lettore

"Se nella mia regione diminuiscono i furti, perché non mi sento più sicuro?"

## Lettura da correggere

La lettura è quella della sola classifica dei furti in abitazione: la regione che sale o scende di posto sui furti dovrebbe salire o scendere anche nel senso di sicurezza. Nei livelli la lettura regge in parte (2025, 20 regioni, Spearman furti/rischio ρ=0,635). Nei cambiamenti no, ed è questo che il pezzo mostra.

## Tesi provvisoria (circoscritta)

Fra le 20 regioni italiane, negli anni 2019-2025, quanto cambiano i furti in abitazione non dice quanto cambia il rischio di criminalità percepito. Il rischio percepito sale mentre i furti scendono sotto il livello del 2019, e fra i reati la rapina è la misura che lo accompagna meglio, ma solo se si guarda la finestra lunga.

Che cosa la tesi NON dice: non dice che i furti non contano per la percezione, non dice che la criminalità cala, non propone una causa, non descrive nessuna persona o famiglia.

### Restringimento rispetto alla tesi scelta da Astra

Astra ha scelto: "il calo dei furti non coincide sempre con una diminuzione del rischio percepito, e gli altri reati impediscono di ridurre la sicurezza a una sola classifica". I numeri la sostengono, ma con tre correzioni che il brief adotta e che lo scrittore non può aggirare:

1. Il conteggio delle regioni divergenti (furti giù e rischio su) da solo NON prova il distacco. Nel 2023-25 sono 8/20, ma furti in calo in 13/20 e rischio in aumento in 15/20: se le due misure fossero indipendenti se ne aspetterebbero circa 9,8 (13×15/20). Nel 2019-25 sono 11/20 contro circa 11,1 attese. Il conteggio quindi si racconta come descrizione dei casi, mai come prova. Questo confronto con l'attesa è stato calcolato dopo la pre-registrazione di Astra: è esplorativo.
2. La prova del distacco è la correlazione fra i cambiamenti, Spearman ρ=-0,014 (2023-25) e ρ=0,100 (2019-25), N=20 in entrambi. Valori vicini a zero, descrittivi, senza p-value.
3. Il 2023 è un minimo del rischio percepito (media semplice 18,83%, contro 22,09% nel 2019). Il rialzo 2023-25 è quindi in buona parte un ritorno verso il livello pre-2020. Il pezzo deve dirlo con la finestra 2019-25 accanto, non usare 2023-25 da solo.

H2 di Astra (borseggi, rapine o degrado diversi dai furti nelle regioni divergenti) non viene confermata come specifica delle divergenti: vedi "Controllo contrario". Si conserva il risultato negativo.

## Le tre misure realmente incrociate

Stesso livello (regione), stessa fonte (Istat, BES, CSV locale `app/static/data/Assoluti_BES_Regione.csv`), anni comuni 2019, 2023, 2025, 20 regioni (Trentino-Alto Adige unità unica).

| Misura | Codice | Unità | Che cosa misura |
| --- | --- | --- | --- |
| Furti in abitazione | bes-07SIC002 | vittime per 1.000 famiglie | stima Istat, corretta per le mancate denunce |
| Rischio di criminalità percepito | bes-07SIC022 | % di famiglie che dichiarano rischio molto o abbastanza elevato nella zona | percezione soggettiva |
| Rapine | bes-07SIC004 | vittime per 1.000 abitanti | stima Istat, corretta per le mancate denunce |

Popolazioni e unità sono diverse (famiglie, famiglie, abitanti). Non si sommano e non si confrontano come livelli fra misure. Si confrontano solo i ranghi delle variazioni regione per regione (Spearman), e il pezzo lo scrive in chiaro.

Misure di contesto, NON del test centrale: degrado (bes-07SIC021) e sicurezza camminando al buio (bes-07SIC020), perché si comportano allo stesso modo nei due gruppi (vedi sotto). Borseggi (bes-07SIC003) solo in nota. `ter-43` (quasi gemello del rischio) e `ims-MULTI_ZONA_CRIMINALITA` non si contano come conferme: censimento in `numeri.md`.

## Insight

Le tre misure dicono tre cose diverse sulle stesse 20 regioni, e la classifica dei soli furti le nasconde:

| Variazione fra regioni | Spearman 2023-25 (N=20) | Spearman 2019-25 (N=20) |
| --- | ---: | ---: |
| furti vs rischio | -0,014 | +0,100 |
| rapine vs rischio | +0,118 | +0,469 |
| furti vs rapine | +0,166 | -0,041 |

Medie semplici delle 20 regioni (non medie nazionali): furti 9,38 → 6,86 per 1.000 famiglie fra 2019 e 2025 (-27%), rischio 22,09% → 22,61%, rapine 0,680 → 0,775 per 1.000 abitanti.

Lettura che il pezzo può fare, e solo questa: i furti calano ovunque in media, il rischio percepito torna al livello del 2019, e fra le regioni il cambiamento dei furti non ordina il cambiamento del rischio. Le rapine, che salgono in 13/20 regioni sul 2019-25, ordinano il rischio meglio (ρ=0,47 contro 0,10), ma la stessa relazione nel 2023-25 è quasi assente (ρ=0,12). La relazione dipende dalla finestra, ed è un risultato da dichiarare, non da nascondere.

### Perché fa avanzare il racconto: il confronto Toscana-Campania

Il confronto esplicito, già fissato da Astra, serve a mostrare due direzioni opposte dello stesso scostamento. Va usato come coppia di casi regionali, non come famiglie o persone (nessuna scena individuale dedotta dalle medie):

- Toscana: furti 14,8 → 12,6 per 1.000 famiglie (2023-25), rischio 20,5% → 27,8%, rapine 1,4 → 1,2 per 1.000 abitanti. Dal 2019: furti 18,1 → 12,6, rischio 25,9% → 27,8%.
- Campania: furti 6,2 → 5,5, rischio 39,0% → 38,0%, rapine 1,5 → 1,1. Dal 2019: furti 7,0 → 5,5, rischio 36,4% → 38,0%.

La Campania ha il rischio più alto del campione in entrambi gli anni con furti sotto la mediana (5,5 contro una mediana regionale di circa 7 nel 2025): il livello del rischio non segue il livello dei furti, e ancora meno la sua variazione. La Toscana ha i furti più alti del campione e un rischio sotto quello campano, che però cresce di 7,3 punti nel 2023-25. Nel 2019-25 anche la Campania entra fra le regioni divergenti, e per questo il contrasto Toscana/Campania vale per 2023-25 e non va esteso alla finestra lunga (lo dice `numeri.md`).

## Controllo contrario (scelto prima del calcolo da Astra) e controllo aggiunto dopo

Pre-registrati: esclusione di Toscana e Campania, finestra 2019-25. Ricalcolo diretto dal CSV locale, indipendente da `numeri.md`:

| Controllo | N | Divergenti | ρ furti/rischio (variazioni) | ρ rapine/rischio (variazioni) |
| --- | ---: | ---: | ---: | ---: |
| 2023-25, tutte | 20 | 8 | -0,014 | +0,118 |
| 2023-25, senza Toscana e Campania | 18 | 7 | +0,100 | +0,104 |
| 2019-25, tutte | 20 | 11 | +0,100 | +0,469 |
| 2019-25, senza Toscana e Campania | 18 | 9 | +0,139 | +0,534 |

Resiste: il segno opposto non dipende dai due casi evidenziati, e ρ resta vicino a zero per i furti in tutte le righe. Il valore di ρ cambia, quindi non si scrive "il risultato regge" come fosse un test di tenuta: si scrive che non dipende dalle due regioni scelte.

Controllo aggiunto dopo (esplorativo, vedi sopra): leave-one-out sulla coppia rapine/rischio, 2019-25. ρ resta fra 0,412 (senza Calabria) e 0,570 (senza Emilia-Romagna). Sul 2023-25 va da -0,002 (senza Campania) a 0,214 (senza Toscana): intervallo largo, quasi zero. La relazione rapine/rischio del 2019-25 non dipende da una regione sola.

Risultati negativi da conservare:
- Degrado e sicurezza al buio non separano le regioni divergenti dalle altre: nel 2023-25 il degrado sale in 8/8 divergenti e già in 10/12 non divergenti, la sicurezza al buio cala in 8/8 e in 11/12. Il segnale percettivo è generale, non specifico delle otto regioni. Non spiega il distacco.
- Le rapine 2023-25 salgono in 4/8 divergenti e in 2/12 non divergenti, ma i valori sono a un decimale e 6 regioni su 20 hanno variazione esattamente 0,0 (molti ex aequo): non basta per un racconto.
- Nel 2019-25 le rapine salgono in 8/11 divergenti e in 5/9 non divergenti: nessuna specificità.
- La media delle rapine sale (0,680 → 0,775 nel 2019-25), perciò non si può scrivere "la criminalità diminuisce".

## Meccanismo

Ignoto, dichiarato. Nessuna fonte aperta dimostra un nesso causale fra reati locali e percezione regionale (`fonti.md`, "Non trovato"). Il pezzo non propone spiegazioni (media, social, età, composizione) come cause. Può elencare ciò che questi dati non misurano.

## Piano per lo scrittore (solo vincoli, niente bozza)

- Apertura: la domanda del lettore, subito il numero che la illumina (furti -27% dal 2019, rischio tornato al livello 2019). Significato concreto nei primi due paragrafi.
- Struttura: livelli (la classifica regge), cambiamenti (non regge), rapine (finestra lunga sì, corta no), Toscana/Campania, che cosa non sappiamo.
- Grafici (generatore `scripts/trend_articles/figures.py`, forma `scatter`): variazioni furti/rischio, evidenziando Toscana e Campania, e variazioni rapine/rischio sulla finestra 2019-25. Il generatore calcola Pearson: se si cita un numero dal grafico va dichiarata la differenza con lo Spearman del testo.
- Rispettare `content/STYLE.md`: nessun em-dash, en-dash, punto e virgola, `…`.
- Lunghezza: articolo di dati, 700-1100 parole. Da stabilire con la direzione se serve più spazio.
- Prima del merge: bozza HTML con `bin/py -m scripts.editoriale.bozza_html furti-sicurezza-percepita --radice <worktree> --pr 358`, ok della direzione, poi merge. Gate B dopo la bozza.

## Limiti, accanto a ogni affermazione

- Dati regionali aggregati: nessuna inferenza su famiglie o persone, nessun caso individuale dedotto dalle medie. Le medie sono medie semplici delle 20 regioni, mai medie nazionali.
- Spearman descrittivo su N=20: non sono test inferenziali, non c'è correzione per confronti multipli. Il lavoro di scelta del candidato è stato guidato dai risultati (sondaggio di Astra), e i controlli aggiunti dopo sono esplorativi.
- Errore campionario regionale delle stime BES: non trovato in fonti ufficiali aperte, quindi variazioni piccole (specie rapine, passo 0,1) non sono distinguibili dal rumore. Non scrivere come "sale" una variazione di 0,1 per mille senza dirlo.
- Riconciliazione con l'ultima cella ufficiale non riuscita: la cella 2025 dell'aggiornamento BES aprile 2026 sta nell'appendice Istat in ZIP, che il browser non ha aperto. Calcoli fatti sul CSV locale e riverificati direttamente qui, ma non certificati cella per cella contro Istat. Il pezzo deve dire "dati dell'aggiornamento Istat di aprile 2026 nella copia del progetto".
- Il 2023 è un minimo del rischio: nessuna frase deve leggere il 2023-25 come inversione di tendenza.
- BES misura vittime con correzione del sommerso, le serie provinciali (bes-07SIC004P ecc.) misurano denunce: non si mescolano.
- Un possibile errore di stampa in `numeri.md` (sezione "Controllo serie percettive sovrapposte": "Spearman ... = 0 (ρ=1.000)", contraddittorio): il brief non usa quel passaggio e il valore corretto per `fonti.md` è ρ=1,000. Il file non è di questo ruolo, non è modificato qui.

## Domande aperte per Gate A e per la direzione

1. La tesi stretta (distacco nei cambiamenti, non conteggio delle divergenti) è accettata come lettura corretta della scelta di Astra?
2. Il terzo indicatore (rapine) basta come "indicatore che fa avanzare il racconto", sapendo che la sua relazione dipende dalla finestra?
3. Accettabile scrivere un pezzo con una conclusione in parte negativa ("non spieghiamo il distacco")?

## File simili

- `content/indicators/bes__07SIC020.md`: Percezione di sicurezza camminando da soli quando è buio

## Regole

Seguire `content/STYLE.md`. Articolo di dati: 700-1100 parole. Analisi lunga: 1400-2000 parole.
Prima del merge la bozza si rende in HTML con `bin/py -m scripts.editoriale.bozza_html <slug> --radice <worktree> --pr <n>` e va nell'indice delle bozze; il merge, che e' la pubblicazione, solo dopo l'ok della direzione (docs/WORKFLOW_ARTICOLI_TREND.md, 8bis).
