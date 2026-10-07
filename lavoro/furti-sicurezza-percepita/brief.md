# Meno furti in casa, ma sentirsi sicuri è un'altra cosa

Tipo: blog
Issue: #357 · PR draft: #358
Chiave: `furti-sicurezza-percepita`
Stato: brief corretto dopo il Gate A FERMO del 7 ottobre 2026 (SHA esaminato `26053d28`). Non è una bozza. Il Gate A resta FERMO finché un nuovo giudice indipendente non lo chiude: lo scrittore non parte prima.

Autore: Claude Sonnet 5.5 (leader). Giudice atteso: Astra, contesto nuovo, famiglia diversa.
Numeri, formule e chiavi: `lavoro/furti-sicurezza-percepita/numeri.md`. Fonti: `fonti.md`. Censimento: `copertura.csv`.

## Domanda del lettore

"Meno furti in casa significa sempre meno rischio percepito nella regione?"

La domanda è territoriale e descrittiva. Il perché di una singola persona non è identificabile con questi dati e il pezzo non lo promette.

## Lettura da correggere

La lettura è quella della sola classifica dei furti in abitazione: la regione che sale o scende di posto sui furti dovrebbe salire o scendere anche nel senso di sicurezza. Nei livelli la lettura regge in parte (2025, N=20, Spearman furti/rischio ρ=0,635). Nei cambiamenti la mancata coincidenza è evidente, ed è questo che il pezzo descrive.

## Tesi provvisoria (circoscritta, entro il limite del Gate A)

Nelle venti regioni, il calo dei furti in casa non coincide sempre con un calo del rischio percepito. I cambiamenti dei furti e del rischio mostrano una debole associazione fra i ranghi nelle due finestre considerate (2023-25 e 2019-25). Per le rapine l'associazione è maggiore dal 2019 al 2025 e molto più debole dal 2023 al 2025. Questi confronti regionali non spiegano perché una persona si senta insicura.

Che cosa la tesi NON dice: non dice che i furti non contano per la percezione, non dice che la criminalità cala, non propone una causa, non descrive nessuna persona o famiglia, non è una prova di indipendenza fra le misure e non esclude altri legami o una capacità predittiva. L'analisi è esplorativa e scelta sui risultati.

### Restringimento rispetto alla tesi scelta da Astra

Astra ha scelto: "il calo dei furti non coincide sempre con una diminuzione del rischio percepito, e gli altri reati impediscono di ridurre la sicurezza a una sola classifica". I numeri la sostengono come descrizione, con queste correzioni che lo scrittore non può aggirare:

1. Il conteggio delle regioni divergenti (furti giù e rischio su) è una descrizione dei casi, mai una prova. Nel 2023-25 sono 8/20, con furti in calo in 13/20 e rischio in aumento in 15/20: a margini fissi se ne attenderebbero 9,75 (13×15/20), e 8 non li supera. Nel 2019-25 sono 11/20, con furti in calo in 17/20 e rischio in aumento in 13/20: attese 11,05. Questo confronto è stato calcolato dopo la pre-registrazione di Astra ed è esplorativo.
2. I coefficienti sono descrittivi, senza p-value, e non provano né indipendenza né assenza di altri legami. Spearman sulle variazioni furti/rischio: ρ=-0,001 (2023-25) e ρ=0,108 (2019-25), N=20 in entrambi: associazione monotona debole nel campione osservato. Ranghi medi sugli ex aequo (decimali pubblicati), da `numeri.md` e `ricalcolo.py`.
3. Il 2023 è il minimo del rischio percepito soltanto fra i tre anni confrontati (media semplice 18,83%, contro 22,10% nel 2019 e 22,61% nel 2025), non della serie: nella serie disponibile 2005-2025 il minimo è il 2021 (16,64%). La risalita è già in corso prima del 2023 (2022: 18,03%) e nel 2025 la media è vicina a quella del 2019. Il pezzo lo dice con la finestra 2019-25 accanto, non usa 2023-25 da solo e non lo legge come inversione di tendenza, senza attribuirne la causa.

H2 di Astra (borseggi, rapine o degrado diversi dai furti nelle regioni divergenti) non viene confermata come specifica delle divergenti: vedi "Controllo contrario". Si conserva il risultato negativo.

## Le tre misure realmente incrociate

Stesso livello (regione), stessa fonte (Istat, BES, CSV locale `app/static/data/Assoluti_BES_Regione.csv`), anni comuni 2019, 2023, 2025, 20 regioni (Trentino-Alto Adige unità unica). Finestre: 2023-25 e 2019-25, variazioni assolute (valore 2025 meno valore iniziale), N=20, poi N=18 senza Toscana e Campania. Riconciliazione: 360/360 celle (6 codici, 20 regioni, 3 anni) identiche all'appendice statistica 2 Istat, aggiornamento intermedio BES 2026 (ZIP ufficiale, `fonti.md`). La riconciliazione copre queste celle, non l'intero CSV né l'incertezza delle stime.

| Misura | Codice | Unità | Che cosa misura |
| --- | --- | --- | --- |
| Furti in abitazione | bes-07SIC002 | vittime per 1.000 famiglie | stima Istat, corretta per le mancate denunce |
| Rischio di criminalità percepito | bes-07SIC022 | % di famiglie che dichiarano rischio molto o abbastanza elevato nella zona | percezione soggettiva |
| Rapine | bes-07SIC004 | vittime per 1.000 abitanti | stima Istat, corretta per le mancate denunce |

Popolazioni e unità sono diverse (famiglie, famiglie, abitanti). Non si sommano e non si confrontano come livelli fra misure. Si confrontano solo i ranghi delle variazioni regione per regione (Spearman, ranghi medi sugli ex aequo), e il pezzo lo scrive in chiaro. Il confronto è ecologico: stesse regioni, non stesse persone.

Misure di contesto, NON del test centrale: degrado (bes-07SIC021) e sicurezza camminando al buio (bes-07SIC020), perché si comportano allo stesso modo nei due gruppi (vedi sotto). Borseggi (bes-07SIC003) solo in nota. `ter-43` (quasi gemello del rischio) e `ims-MULTI_ZONA_CRIMINALITA` non si contano come conferme: censimento in `numeri.md`.

## Insight

Le tre misure non coincidono nelle stesse 20 regioni, e la classifica dei soli furti lo nasconde:

| Variazione fra regioni | Spearman 2023-25 (N=20) | Spearman 2019-25 (N=20) |
| --- | ---: | ---: |
| furti vs rischio | -0,001 | +0,108 |
| rapine vs rischio | +0,136 | +0,510 |
| furti vs rapine | +0,133 | -0,094 |

Medie semplici delle 20 regioni (non medie nazionali): furti 9,38 → 6,86 per 1.000 famiglie fra 2019 e 2025 (-26,9% sulla media semplice), rischio 22,10% → 22,61% (22,095 arrotondato a due decimali), rapine 0,680 → 0,775 per 1.000 abitanti.

Lettura che il pezzo può fare, e solo questa: in media i furti calano (17 regioni su 20 scendono dal 2019, 2 salgono, 1 è invariata), il rischio percepito medio nel 2025 è vicino al livello del 2019, e fra le regioni il cambiamento dei furti e quello del rischio mostrano una debole associazione fra i ranghi. Le rapine, che salgono in 13/20 regioni sul 2019-25, hanno con il rischio un'associazione maggiore (ρ=0,51 contro 0,11), ma sul 2023-25 è molto più debole (ρ=0,14). La relazione dipende dalla finestra, ed è un risultato da dichiarare, non da nascondere. Non è una spiegazione del rischio: gli esiti sono esplorativi.

### Perché fa avanzare il racconto: il confronto Toscana-Campania

Il confronto esplicito, già fissato da Astra, serve a mostrare due direzioni opposte dello stesso scostamento. Va usato come coppia di casi regionali, non come famiglie o persone (nessuna scena individuale dedotta dalle medie):

- Toscana: furti 14,8 → 12,6 per 1.000 famiglie (2023-25), rischio 20,5% → 27,8%, rapine 1,4 → 1,2 per 1.000 abitanti. Dal 2019: furti 18,1 → 12,6, rischio 25,9% → 27,8%.
- Campania: furti 6,2 → 5,5, rischio 39,0% → 38,0%, rapine 1,5 → 1,1. Dal 2019: furti 7,0 → 5,5, rischio 36,4% → 38,0%.

La Campania ha il rischio più alto del campione in entrambi gli anni con furti sotto la mediana (5,5 contro una mediana regionale di circa 6,9 nel 2025): il livello del rischio non segue il livello dei furti (la mediana regionale 2025 è circa 6,9). Anche la variazione si distanzia: è una descrizione dei due casi, non una regola. La Toscana ha i furti più alti del campione e un rischio sotto quello campano, che però cresce di 7,3 punti nel 2023-25. Nel 2019-25 anche la Campania entra fra le regioni divergenti, e per questo il contrasto Toscana/Campania vale per 2023-25 e non va esteso alla finestra lunga (lo dice `numeri.md`).

## Controllo contrario (scelto prima del calcolo da Astra) e controllo aggiunto dopo

Pre-registrati: esclusione di Toscana e Campania, finestra 2019-25. Ricalcolo diretto dal CSV locale (`ricalcolo.py`, Decimal, ranghi medi sugli ex aequo; coefficienti corretti dopo il Gate A):

| Controllo | N | Divergenti | ρ furti/rischio (variazioni) | ρ rapine/rischio (variazioni) |
| --- | ---: | ---: | ---: | ---: |
| 2023-25, tutte | 20 | 8 | -0,001 | +0,136 |
| 2023-25, senza Toscana e Campania | 18 | 7 | +0,103 | +0,127 |
| 2019-25, tutte | 20 | 11 | +0,108 | +0,510 |
| 2019-25, senza Toscana e Campania | 18 | 9 | +0,148 | +0,580 |

Conferma i casi: 8/20, 11/20, 7/18, 9/18. Il conteggio delle divergenti e la debole associazione furti/rischio non dipendono dalle due regioni scelte, e ρ furti/rischio resta fra -0,001 e 0,148 in tutte le righe. Il valore di ρ cambia, quindi non si scrive "il risultato regge" come fosse un test di tenuta, né si parla di indipendenza.

Controllo aggiunto dopo (esplorativo, vedi sopra): leave-one-out sulla coppia rapine/rischio, 2019-25. ρ rapine/rischio resta fra 0,459 (senza Calabria) e 0,602 (senza Emilia-Romagna). Sul 2023-25 va da 0,012 (senza Umbria) a 0,236 (senza Toscana): sempre debole. Per furti/rischio, 2023-25 da -0,093 (senza Sicilia) a 0,145 (senza Molise); 2019-25 da 0,017 (senza Friuli-Venezia Giulia) a 0,230 (senza Valle d'Aosta). Non sono intervalli di confidenza né misure di stabilità inferenziale: indicano soltanto che la relazione rapine/rischio del 2019-25 non dipende da una regione sola.

Risultati negativi da conservare:
- Degrado e sicurezza al buio non separano le regioni divergenti dalle altre: nel 2023-25 il degrado sale in 8/8 divergenti e già in 10/12 non divergenti, la sicurezza al buio cala in 8/8 e in 11/12. Il segnale percettivo è generale, non specifico delle otto regioni. Non spiega la mancata coincidenza.
- Le rapine 2023-25 salgono in 4/8 divergenti e in 2/12 non divergenti, ma i valori sono a un decimale e 6 regioni su 20 hanno variazione esattamente 0,0 (molti ex aequo, trattati con i ranghi medi): non basta per un racconto.
- Nel 2019-25 le rapine salgono in 8/11 divergenti e in 5/9 non divergenti: nessuna specificità.
- La media delle rapine sale (0,680 → 0,775 nel 2019-25, in 13 regioni su 20; nel 2023-25 scende da 0,810 a 0,775), perciò non si può scrivere "la criminalità diminuisce". Le rapine sono una misura distinta, non una misura complessiva della criminalità.

## Meccanismo

Ignoto, dichiarato. Nessuna fonte aperta dimostra un nesso causale fra reati locali e percezione regionale (`fonti.md`, "Non trovato"). Il pezzo non propone spiegazioni (media, social, età, composizione) come cause. Può elencare ciò che questi dati non misurano.

## Piano per lo scrittore (solo vincoli, niente bozza)

- Apertura: la domanda del lettore, subito il numero che la illumina (furti in media -26,9% dal 2019 sulla media semplice delle 20 regioni, rischio medio nel 2025 vicino al 2019). Significato concreto nei primi due paragrafi. Dire "in media" o "17 regioni su 20", mai "ovunque" né "in tutte".
- Formulare con le parole della tesi: "non coincide sempre", "debole associazione fra i ranghi". Vietati: "prova", "dimostra", "indipendenti", "non dice", "spiega perché ti senti insicuro". Nessun p-value, nessuna previsione.
- Struttura: livelli (la classifica regge), cambiamenti (non regge), rapine (finestra lunga sì, corta no), Toscana/Campania, che cosa non sappiamo.
- Grafici (generatore `scripts/trend_articles/figures.py`, forma `scatter`): variazioni furti/rischio, evidenziando Toscana e Campania, e variazioni rapine/rischio sulla finestra 2019-25. Il generatore calcola Pearson: se si cita un numero dal grafico va dichiarata la differenza con lo Spearman del testo, e nel testo vanno solo i coefficienti di `numeri.md`.
- Rispettare `content/STYLE.md`: nessun em-dash, en-dash, punto e virgola, `…`.
- Lunghezza: articolo di dati, 700-1100 parole. Da stabilire con la direzione se serve più spazio.
- Prima del merge: bozza HTML con `bin/py -m scripts.editoriale.bozza_html furti-sicurezza-percepita --radice <worktree> --pr 358`, ok della direzione, poi merge. Gate B dopo la bozza.

## Limiti, accanto a ogni affermazione

- Analisi esplorativa, scelta sui risultati, N=20 (N=18 nei controlli) sempre dichiarato accanto al numero.
- Dati regionali aggregati: nessuna inferenza su famiglie o persone, nessun caso individuale dedotto dalle medie. Le medie sono medie semplici delle 20 regioni, mai medie nazionali.
- Spearman descrittivo su N=20 con ranghi medi sugli ex aequo: non sono test inferenziali, non c'è correzione per confronti multipli. Il lavoro di scelta del candidato è stato guidato dai risultati (sondaggio di Astra), e i controlli aggiunti dopo sono esplorativi.
- Errore campionario regionale delle stime BES: non trovato in fonti ufficiali aperte e non valutato qui. La precisione delle variazioni piccole (specie rapine, passo 0,1) non è stata valutata: non scrivere come "sale" una variazione di 0,1 per mille senza dirlo, e non affermare che sia rumore.
- Riconciliazione fatta: 360/360 celle (furti, rischio, rapine, borseggi, degrado, sicurezza al buio × 20 regioni × 2019, 2023, 2025) identiche all'appendice statistica 2 Istat dell'aggiornamento BES aprile 2026 (ZIP ufficiale, `fonti.md`). Non copre l'intero CSV né l'incertezza delle stime. Il pezzo dice "dati dell'aggiornamento Istat di aprile 2026".
- Reati 2025 provvisori: per furti, borseggi e rapine l'Istat scrive che i dati del 2025 sono provvisori e che la serie è ricostruita dal 2019 con il nuovo fattore di correzione dell'indagine Sicurezza dei cittadini 2022. Le variazioni che toccano il 2025 e il 2019 vanno scritte come tali. Per borseggi e rapine il tasso totale delle tavole regionali non corrisponde a quello delle tavole per età (persone di 14 anni e più).
- Il 2023 è un minimo del rischio solo fra i tre anni confrontati (minimo della serie: 2021): nessuna frase deve leggere il 2023-25 come inversione di tendenza.
- BES misura vittime con correzione del sommerso, le serie provinciali (bes-07SIC004P ecc.) misurano denunce: non si mescolano.

## Domande aperte per Gate A e per la direzione

1. La tesi ristretta (mancata coincidenza e debole associazione dei ranghi, senza prova di indipendenza) è accettata come lettura corretta della scelta di Astra?
2. Il terzo indicatore (rapine) basta come "indicatore che fa avanzare il racconto", sapendo che la sua relazione dipende dalla finestra?
3. Accettabile scrivere un pezzo con una conclusione in parte negativa ("non spieghiamo la mancata coincidenza")?

## File simili

- `content/indicators/bes__07SIC020.md`: Percezione di sicurezza camminando da soli quando è buio

## Regole

Seguire `content/STYLE.md`. Articolo di dati: 700-1100 parole. Analisi lunga: 1400-2000 parole.
Prima del merge la bozza si rende in HTML con `bin/py -m scripts.editoriale.bozza_html <slug> --radice <worktree> --pr <n>` e va nell'indice delle bozze; il merge, che e' la pubblicazione, solo dopo l'ok della direzione (docs/WORKFLOW_ARTICOLI_TREND.md, 8bis).
