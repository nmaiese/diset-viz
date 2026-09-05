# Regole per le pagine indicatore

Le pagine indicatore devono aiutare una persona a capire il dato, confrontare i
territori, verificare la fonte e riusare la serie. Non sono contenitori SEO
riempiti con frasi intercambiabili.

## La pagina, in tre zone

Un solo template (`app/templates/indicator_page.html`) serve tutte e quattro le
famiglie: indicatori territoriali, Eurostat, BES e Multiscopo. Prima ce n'erano
due, con due modelli dati diversi, e le pagine sono andate alla deriva.

1. **Il cruscotto.** Tutti i numeri della pagina, una volta sola, in alto.
   Riga dei fatti, switch di livello territoriale dove esistono regioni e
   province, slider dell'anno, selettore del territorio a fuoco, una riga di KPI
   e le tre viste (mappa, classifica, serie storica). È l'unica parte interattiva.
2. **L'articolo.** Quattro sezioni in ordine fisso, un unico blocco di prosa,
   nessuna card o tessera in mezzo ai paragrafi.
3. **L'apparato.** Fonti, definizione originale, come citare, immagine da
   condividere, indicatori correlati, percorso.

La regola che tiene insieme il tutto: **una cifra si mostra una volta**. Il
cruscotto la mostra, la prosa la interpreta. Un paragrafo che rilegge il massimo,
il minimo e la media è la duplicazione che questo layout ha eliminato.

## Chi possiede che cosa

| | proprietario | dove |
|---|---|---|
| numeri, aggregati, ordinamenti | `app/indicator_view.py` | cruscotto |
| prosa scritta | `content/indicators/<chiave>.json` | articolo |
| prosa composta, quando manca la scritta | `app/templates/_indicator_article.html` | articolo |
| fonte, copertura, citazione, disclaimer sulla media | template | apparato |

`app/indicator_view.py` è il modello dati unico. Espone `meta` (tutto ciò che non
dipende da un territorio) e `levels` (una voce per livello territoriale, ciascuna
con i propri anni, osservazioni, aggregati e confronto annuale). Non duplicare
quei calcoli altrove.

## Dove vive la prosa: un file per articolo

`content/indicators/<chiave>.json`, con i due punti della chiave scritti `__`:
`bes:10AMB004` sta in `content/indicators/bes__10AMB004.json`. Lo store è
`scripts/indicator_store.py`, che possiede la codifica e la spiega per intero.

Era un JSON unico da 365 voci sotto `app/static/data/`, e il formato costava due
cose distinte. Scrittore e revisore (due agenti che allora esistevano)
condividevano il perimetro e giravano tutti e due ogni giorno, quindi ogni loro
modifica riscriveva l'intero file e due run vicine su articoli diversi finivano
in conflitto su qualcosa che nessun agente
può risolvere leggendolo. E il diff di una revisione non diceva di quale
indicatore parlasse, perché la chiave che possiede le righe cambiate poteva
stare cento righe più su.

Adesso `git log content/indicators/920.json` è la storia editoriale di
quella pagina, e due stadi che lavorano su articoli diversi non hanno niente da
fondere.

Quello che **non** è cambiato: una voce vale per un livello territoriale solo, e
il livello resta un campo dentro la voce. Il modello è ancora una voce per
indicatore, non una per coppia (indicatore, livello).

```bash
python3 scripts/indicator_store.py --list
python3 scripts/indicator_store.py --show ter-920
```

## L'articolo: quattro ruoli

Ordine fisso, titolo `h2` scritto dall'autore. La struttura è uniforme su tutte
le pagine, la superficie no: `content/STYLE.md` vieta lo stesso telaio ripetuto,
e 621 pagine con gli stessi identici H2 si leggono come uno stampo.

- `definizione` — che cosa misura, il perimetro, che cosa vale un singolo valore
- `quadro` — come si distribuisce oggi e che forma ha quella distribuzione
- `dinamica` — come si è mosso, serie lunga e ultimo passaggio tenuti distinti
- `limiti` — che cosa il numero non cattura

Più `lead` (una o due frasi, che sono anche la meta description in SERP), `fonti`
e `vintage`.

**Un ruolo assente non è una sezione vuota.** Il template lo compone dai dati, e
la pagina mantiene lo stesso scheletro. È un fallback funzionante, non una pagina
finita: serve perché il layout sia uniforme su tutti i 621 indicatori mentre solo
una parte è passata da un editor. Lo stato di ciascuno lo calcola
`app/editorial_state.py`, ed è quello che legge la coda della redazione
(`motore coda divarioitalia`, nel repo `redazione-ai`).

Il testo composto **non** viene congelato nel file, di proposito: così non può
invecchiare in silenzio dietro un aggiornamento dei dati, e la guardia sul
`vintage` si applica solo alle frasi davvero scritte da qualcuno.

### `roles_covered`: la definizione può non aprire l'articolo

I quattro ruoli qui sopra sono il default, non l'unica forma possibile. Con la
`definizione` sempre in prima posizione ogni articolo apriva sulla contabilità
prima che sulla notizia, ed è il difetto che il criterio 8 della rubrica
(leggibilità) punisce.

Un'entrata può quindi dichiarare `roles_covered`: la lista dei ruoli che scrive
come `h2`. Se la `definizione` non è fra quelli, non apre più l'articolo, e la
sua meccanica va nel blocco **«Come leggere il dato»** (`id="come-leggere"`),
composto server-side dai metadati `explain` e reso **dopo** la narrazione, mai
prima: il blocco esiste per togliere la contabilità dall'apertura, non per
rinominarla.

Le regole, tutte meccaniche:

- **Solo la `definizione` è omettibile.** `quadro`, `dinamica` e `limiti`
  restano sempre, anche se una dichiarazione parziale non li nomina: il blocco
  copre quel ruolo lì e nessun altro.
- **Il campo è opt-in e additivo.** Senza `roles_covered` la pagina rende i
  quattro ruoli come ha sempre fatto, e i trecento articoli esistenti non
  cambiano di un byte.
- **Ed è usabile.** Fino ad agosto 2026 non lo era: un test asseriva che
  l'elenco degli articoli opt-in fosse *vuoto*, quindi il solo meccanismo
  costruito per non aprire sulla definizione era progettato, implementato,
  documentato qui, e vietato. Zero file su 375 lo usavano, mentre 52 articoli
  su 52 aprivano allo stesso modo: il freno di sicurezza di un rilascio
  graduale era diventato il motivo per cui il rilascio non partiva. Adesso la
  guardia controlla la coerenza di chi opta, non il fatto che qualcuno opti.
- **Un ruolo assorbito non è un ruolo mancante.** La coda della redazione e
  `scripts/pending_notes.py` contano contro i ruoli emessi, altrimenti chi
  scrive troverebbe per sempre la `definizione` «da scrivere» e la
  riscriverebbe a ogni giro.
- **Assorbire la definizione cambia l'impronta della prosa.** Cambia cosa la
  pagina mostra senza toccare una parola, quindi
  `app/editorial_state.impronta_prosa` mescola l'insieme dei ruoli emessi: due
  entry con le stesse parole e `roles_covered` diverso non sono la stessa
  pagina, e il cruscotto non deve leggerle "in linea" l'una per l'altra.
  Dichiarare tutti e quattro i ruoli invece non muove l'impronta, perché la
  sequenza emessa resta quella di sempre.
- **La navigazione segue.** La domanda di definizione punta a `#come-leggere`
  invece che a `#sezione-definizione`, che in quella forma non esiste.

**Un articolo vale per un livello territoriale solo.** Cita le cifre di quel
livello, quindi non può viaggiare sull'altro: i 31 BES a due livelli avevano un
lead che nominava l'Umbria e dava la media delle regioni sopra un cruscotto di
province. Un'entrata dichiara il livello che descrive con il campo `level`, che
vale `regione` quando manca, e viene usata solo lì. Su ogni altro livello la
pagina ricade sullo scheletro composto, che legge il livello che gli viene dato.
Lo garantisce `ProseStaysOnTheLevelItWasWrittenFor` in `tests/integration/test_indicator_texts.py`.

## Scrivere un articolo

Si comincia sempre da qui, e **non da questo repo**: il dossier e il brief li
calcola la redazione, in `nmaiese/redazione-ai`.

```bash
motore brief divarioitalia ter-178   # il testo che si mette davanti a chi scrive
```

Il dossier (cifre, angoli, contesto) lo costruisce `motore/dossier.py` di quel
repo e lo scrive qui in `data/lab/dossier/`. Chi scrive un articolo non lancia
niente a mano da questo repo:

Il pacchetto è per livello, in ogni sua parte: cifre, stato dell'articolo e
`vintage` richiesto. Chiudendo, stampa il valore che il campo `level` deve avere.
Prima ignorava il livello nel blocco finale, quindi su `--level provincia`
dichiarava scritte le sezioni dell'articolo *regionale* davanti a una pagina
vuota.

Il pacchetto stampa la graduatoria completa con la variazione di ogni territorio dal
primo anno, dove la distribuzione si spezza davvero, chi si è mosso in
controtendenza e che cosa la pagina dice già da sola. Esiste per una ragione
precisa: scrivendo contro due o tre cifre pescate dall'API si finisce per
riscrivere la stessa fetta che il cruscotto stampa già, ed è da lì che nasce la
prosa banale.

L'ultimo blocco, `INDICATORI CORRELATI`, è quello che permette a un articolo di
uscire dalla propria serie. Prende tutto il tema, non gli otto vicini in ordine
alfabetico che la pagina mostra in tabella, calcola la correlazione di rango sui
valori regionali e li divide in tre: chi disegna la stessa mappa, chi la mappa
opposta, chi una mappa che non c'entra. Il terzo gruppo è quasi sempre il più
interessante da scrivere, e sopra `rho` 0,95 il brief avverte che con ogni
probabilità è lo stesso fenomeno misurato due volte. Per ciascun correlato dà il
percorso canonico da linkare e la posizione, su quella scala, delle due regioni
agli estremi di questa.

Le regole editoriali complete stanno in `content/STYLE.md`. Le classi di
errore che solo una lettura trova non le trova uno strumento: le trova chi
rilegge. Quello che ferma un pezzo sono le tre guardie di `motore verifica`
nel repo della redazione, una cifra fuori dal dossier, un link interno
inesistente, una fonte che non risponde, e non c'è una rubrica a punti. Le
fonti secondarie ammesse stanno in
[`SECONDARY_SOURCES.md`](SECONDARY_SOURCES.md), insieme alla trappola che nessuna
guardia vede: un aggregato nazionale ponderato non è la nostra media semplice
delle venti regioni.

## Risposte obbligatorie

Ogni scheda deve rendere visibili, tra cruscotto e articolo:

1. Il nome dell'indicatore e una definizione comprensibile.
2. Il perimetro, compresi popolazione, fascia di età, genere, numeratore,
   denominatore e unità quando disponibili nella definizione della fonte.
3. Un esempio numerico che spieghi che cosa rappresenta il valore.
4. La direzione, oppure l'assenza di una direzione univoca.
5. Il limite principale e ciò che il dato non consente di concludere.
6. L'ultimo anno, la copertura territoriale, la fonte e i download disponibili.
7. Il confronto con l'anno precedente disponibile.
8. Il trend di lungo periodo, quando esistono almeno due anni confrontabili.
9. Un collegamento all'atlante, alla metodologia, al tema o a un indicatore
   strettamente collegato.

La denominazione amministrativa originale può restare nei metadati e nel blocco
della fonte. Il testo principale deve tradurla in italiano chiaro senza cambiare
il significato statistico.

## Confronto con l'ultimo anno

Il confronto usa l'ultimo anno pubblicato e l'anno precedente effettivamente
disponibile nella stessa serie. Se manca un anno intermedio, il testo deve indicare
entrambi gli anni e non deve chiamarlo confronto annuale.

Regole di calcolo e scrittura:

- Confrontare solo i territori con un valore in entrambi gli anni.
- Dichiarare quanti territori compongono la base comune.
- Chiamare il risultato `media semplice dei valori regionali`, non `media
  Italia` o `media nazionale`.
- Per tassi e quote percentuali, esprimere le variazioni in punti percentuali.
  Vale anche per la variazione di lungo periodo: accostare un "9,8% in più" a un
  livello del "54,87%" mette due percentuali di natura diversa nella stessa
  frase. Il modello espone `meta.percentage_like` proprio per questo.
- Indicare quante regioni aumentano, diminuiscono o restano stabili.
- Mostrare la maggiore diminuzione e il maggiore aumento solo se esistono.
- Usare `migliora`, `peggiora` o `favorevole` solo quando la direzione
  dell'indicatore è revisionata.
- Per indicatori contestuali descrivere soltanto aumento, diminuzione o
  stabilità.
- Non attribuire cause a una variazione osservata.

Se la serie ha un solo anno, la pagina deve dichiarare che il confronto temporale
non è disponibile. Non va costruita una frase sostitutiva.

## Trend di lungo periodo

Il confronto tra primo e ultimo anno resta separato dalla variazione più recente.
Deve indicare gli anni, l'unità e la base territoriale.

Il primo anno è il primo con dati veri, non quello dichiarato nei metadati:
quattro indicatori dichiarano un anno iniziale per cui nessuna regione ha un
valore, e il vecchio codice per questo ometteva del tutto il trend.

## Ordinamento e parità

Un solo ordinamento per tutte le famiglie: valore più alto per primo, e la
direzione decide se il primo è il migliore. Gli indicatori contestuali non hanno
un migliore, quindi `best` e `worst` restano vuoti e la classifica ordina soltanto.

Le parità si rompono per nome. Non è un dettaglio estetico: prima i territori a
pari valore restavano nell'ordine del CSV e una delle due vecchie strade
rovesciava la lista, quindi quale di due regioni identiche venisse chiamata
"migliore" dipendeva dall'ordine delle righe in un file di dati e poteva cambiare
a ogni ricarico. Quel nome finisce nella prosa.

## Accuratezza

- La definizione della fonte è il riferimento principale.
- Numeratore e denominatore non vanno dedotti quando la fonte non li esplicita.
- Una media regionale non sostituisce un indicatore nazionale ponderato.
- Una correlazione territoriale non dimostra una causa.
- Una graduatoria non dimostra l'efficacia di una politica.
- Totale, uomini e donne sono perimetri distinti e non vanno confusi.
- Un divario tra due tassi va espresso in punti percentuali e non descrive da
  solo il livello complessivo dei due tassi.

## Che cosa è verificato e che cosa no

`tests/integration/test_indicator_texts.py` copre la parte meccanica:

- struttura, ruoli noti e non duplicati, punteggiatura editoriale, `vintage` e
  risoluzione dell'indicatore,
- lunghezza della prima frase del `lead`, che deve reggere da sola in SERP,
- H2 scritti a mano non riutilizzati su più indicatori,
- **ogni cifra con decimale attribuita a una regione** ("il 24,3% del Molise")
  confrontata con il dato di quell'anno,
- **ogni soglia asserita su un elenco di regioni** ("supera il 78% in A, B e C")
  verificata regione per regione,
- **ogni link interno nella prosa**: forma canonica (mai `/?indicator=` né
  `/atlante?indicator=`, che arrivano alla scheda solo via JavaScript), un
  indicatore che esiste davvero, un percorso che il sito serve, e un'anchor che
  dice dove porta invece di "clicca qui".

Le ultime due nascono da errori reali: una nota diceva che l'affollamento
carcerario supera "ovunque" la capienza mentre tre regioni erano sotto, e
un'altra metteva la Sardegna sopra il 78% di differenziata quando stava al
76,6%. Un intero senza decimale non viene controllato, perché in questa prosa è
quasi sempre un'approssimazione ("circa 27%", "quasi 78%").

`tests/integration/test_indicator_view.py` copre i numeri: ogni aggregato di tutti i 621
indicatori è confrontato con una fixture estratta dal codice precedente, e ogni
pagina viene resa per verificare che non ci siano 500.

Restano **fuori dai test**, e vanno rivisti a mano. Non a memoria, però:
`motore coda divarioitalia` cerca esattamente questi pattern e
mette in fila gli articoli per quanto è probabile che siano sbagliati. Li
rilegge la redazione, dove chi scrive si rilegge il proprio testo e a valle il
verificatore indipendente prova a smentirlo.

Un articolo firmato porta **due** campi, `reviewed_at` e `reviewed_vintage`, e
solo con entrambi esce dalla coda. I due campi restano vivi anche adesso che
nessun agente firma: li scrivevano il revisore e poi il produttore della catena
ritirata, e oggi la redazione riscrive l'articolo intero con `motore pubblica`. Il
secondo è il `vintage` che chi ha riletto aveva davanti: quando l'articolo si
aggiorna su un anno nuovo tutte le
cifre cambiano, i due valori smettono di combaciare e l'articolo **rientra** in
coda col segnale `rilettura`, che pesa più di ogni segnale di rischio. Gli altri
marcano una frase che potrebbe essere sbagliata, quello marca un articolo in cui
non è stato controllato niente.

- le affermazioni universali su un andamento ("è cresciuto ovunque"): il brief
  ha un blocco apposta, `SI MUOVONO CONTROCORRENTE`,
- le attribuzioni causali ("grazie a", "spinto da"): o si documentano o si
  riformulano come contesto, non come causa accertata,
- i confronti con l'estero ("tra i più alti d'Europa"): richiedono una fonte in
  `fonti`, verificata, altrimenti vanno tolti,
- **una provincia scritta con un nome che il dataset non usa** ("Reggio Emilia"
  per "Reggio nell'Emilia"): la guardia non trova il nome e passa. Manca
  copertura, non inventa un errore. Fino ad agosto 2026 qui c'era un buco molto
  più largo, cioè l'intero livello provinciale: la regex elencava a mano le venti
  regioni, quindi 67 indicatori su 103 province non erano verificati da niente e
  le guardie restavano verdi senza incontrare un solo nome. Ora l'elenco dei
  territori si deriva dai dati, e `test_the_guard_actually_reaches_the_provinces`
  fallisce se la copertura si rispegne,
- **se l'incrocio con un altro indicatore è onesto**: il verbo calibrato sulla
  prova (una correlazione di rango è una co-occorrenza, non un meccanismo), il
  confondente nominato, almeno un'eccezione al pattern. Le guardie controllano
  che il link funzioni, non che la frase intorno regga.

A metà strada c'è `scripts/prose_lint.py`, che non fa fallire niente e conta: i
tell da bot che `content/STYLE.md` nomina, articolo per articolo, e il totale del
catalogo. Serve a scegliere il lotto da rileggere e a misurare se un giro di
riscritture ha spostato qualcosa, invece di stabilirlo a occhio.

```bash
python3 scripts/prose_lint.py --show 178
python3 scripts/prose_lint.py --summary
```

## La definizione, che è un'altra cosa dai numeri

Tutto quello che sta qui sopra confronta l'articolo con **la serie**. Nessuna di
quelle guardie confronta l'articolo con la **definizione della fonte**, e questa
è la distinzione che conta: un numero sbagliato muore al primo lettore che apre
il brief, una definizione sbagliata sopravvive a ogni rilettura che controlla
l'aritmetica, perché l'aritmetica è giusta.

Non è un'ipotesi. Rileggendo undici articoli contro i dati non è uscito **un
solo errore di calcolo**, e sono uscite quattro descrizioni sbagliate di che
cosa l'indicatore conta. `ter-402` chiamava "imprese a guida femminile" quello
che Istat definisce come titolari donne di imprese individuali, e lo ripeteva
nella sezione `limiti`, cioè nel punto che serve a dire che cosa l'indicatore
non misura. `ter-72` scriveva "almeno dieci addetti" dove la fonte dice "più di
dieci addetti", che è un'altra popolazione con le stesse parole.

Le definizioni di fonte sono in due archivi committati. Il primo viene dal
foglio `Metadati` di `Metainformazione.xls` della Banca dati territoriale. Il
secondo federa i metadati BES e BES dei Territori, le codelist SDMX delle
indagini Multiscopo e demografiche, i metadati Eurostat e le serie locali che
il vecchio foglio territoriale non contiene:

```bash
python3 scripts/fetch_definitions.py            # riscrive data/definitions/istat_territoriali.csv
.venv/bin/python scripts/fetch_federated_definitions.py  # riscrive data/definitions/federated.csv
python3 scripts/definition_check.py --show ter-402
python3 scripts/definition_check.py --summary
```

`scripts/xls_reader.py` legge il `.xls` con la sola libreria standard, perché
gli script della catena girano su un checkout pulito prima che esista un venv.
Il fetcher federato usa invece l'ambiente del progetto: legge i workbook `.xlsx`
e interroga le strutture SDMX con cache e rispetto del limite della fonte. Ogni
riga conserva URL e riferimento preciso al workbook, alla codelist o al dataset
da cui deriva.

Il confronto è **lessicale e lo dichiara**: cerca le parole su cui poggia la
definizione ufficiale e chiede se l'articolo le usa mai. Un sinonimo risulta
mancante, e un articolo può usare tutte le parole giuste e descrivere lo stesso
la cosa sbagliata. Quattro segnali, in ordine di quanto vale fidarsene:

| segnale | che cos'è |
| --- | --- |
| `contraddizione` | l'articolo dice una cosa **diversa**, non una in meno: la classe di età della fonte non compare e ne compare un'altra, oppure "almeno N" dove la fonte dice "più di N". È l'unico che afferma invece di suggerire |
| `base` | il denominatore che la fonte nomina non compare nella `definizione` scritta |
| `soglia` | una soglia o una classe di età della fonte non compare da nessuna parte nell'articolo |
| `termini` | l'articolo riprende meno di un terzo delle parole portanti della definizione. È la rete più larga e la più rumorosa, e per questo **non** entra nella coda |

I primi tre diventano il segnale `definizione` di `scripts/prose_lint.py`, che
pesa più di ogni altro, `rilettura` compreso. `scoperto` significa che il codice
non ha trovato una riga nell'archivio federato: non equivale mai a un controllo
superato e segnala che una fonte nuova o non aggiornata va recuperata.

## SEO e struttura

La pagina serve prima di tutto gli intenti di definizione, confronto, fonte e
riuso del dato. Titolo, descrizione, H1 e testo visibile devono essere coerenti.
Ogni pagina indicizzabile deve avere:

- titolo e descrizione unici
- una sola H1 descrittiva
- fonte, periodo, territorio e unità visibili
- HTML server-rendered con testo utile anche senza JavaScript, cruscotto compreso
- canonical autoreferenziale
- `Dataset` JSON-LD la cui `description` è il lead che il lettore vede davvero
- `BreadcrumbList` JSON-LD
- link alla metodologia e al contesto tematico

Niente `FAQPage`: la FAQ generata rileggeva massimo, minimo e media, cioè quello
che il cruscotto mostra già, ed è stata rimossa insieme al suo schema.

Gli stati di esplorazione (`?anno=`, `?regione=`, `?livello=`) sono stati della
stessa pagina, mai documenti nuovi: restano `noindex` e il canonical punta
all'URL base. L'elenco sta in `app/seo_policy.py:EXPLORE_PARAMS`, e va tenuto
aggiornato quando se ne aggiunge uno.

Non aggiungere paragrafi di riempimento. Le varianti quasi duplicate, incomplete
o obsolete seguono le regole di indicizzazione definite in `app/profiles.py`.

## Verifica

Prima della pubblicazione:

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/prose_lint.py --summary
git diff --check
```

L'audit editoriale è il controllo che conta sui trattini, e va usato al posto di
un `grep` sui sorgenti. Viveva in uno script fuori dal repo, sotto un percorso
assoluto della macchina di chi lo aveva scritto, quindi per chiunque altro il
comando qui sopra non esisteva. La parte che serve a questa verifica la fa
`scripts/prose_lint.py`, che sta in repo e gira ovunque. Un `grep -rn "[—–;]" app/templates` restituisce sempre
righe, perché i template contengono CSS e JavaScript pieni di punti e virgola, e
soprattutto **non vede le entity**: `&ndash;` rende un trattino medio vietato da
`content/STYLE.md` senza che il carattere compaia nel sorgente. È così che
"Copertura 2015 – 2024" è rimasto in pagina.

Controllare almeno una pagina per ciascuna famiglia e per ciascuna forma:
percentuale, rapporto, valore assoluto, unità per abitante, punteggio, differenza
tra tassi, serie con un solo anno, indicatore contestuale e indicatore BES a due
livelli territoriali.
