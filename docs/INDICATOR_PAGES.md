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
| prosa scritta | `app/static/data/indicator_texts.json` | articolo |
| prosa composta, quando manca la scritta | `app/templates/_indicator_article.html` | articolo |
| fonte, copertura, citazione, disclaimer sulla media | template | apparato |

`app/indicator_view.py` è il modello dati unico. Espone `meta` (tutto ciò che non
dipende da un territorio) e `levels` (una voce per livello territoriale, ciascuna
con i propri anni, osservazioni, aggregati e confronto annuale). Non duplicare
quei calcoli altrove.

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
una parte è passata da un editor. Lo stato di ciascuno si legge con
`.venv/bin/python -m scripts.text_queue`.

Il testo composto **non** viene congelato nel JSON, di proposito: così non può
invecchiare in silenzio dietro un aggiornamento dei dati, e la guardia sul
`vintage` si applica solo alle frasi davvero scritte da qualcuno.

**Un articolo vale per un livello territoriale solo.** Cita le cifre di quel
livello, quindi non può viaggiare sull'altro: i 31 BES a due livelli avevano un
lead che nominava l'Umbria e dava la media delle regioni sopra un cruscotto di
province. Un'entrata dichiara il livello che descrive con il campo `level`, che
vale `regione` quando manca, e viene usata solo lì. Su ogni altro livello la
pagina ricade sullo scheletro composto, che legge il livello che gli viene dato.
Lo garantisce `ProseStaysOnTheLevelItWasWrittenFor` in `tests/test_indicator_texts.py`.

## Scrivere un articolo

Si comincia sempre da qui:

```bash
.venv/bin/python -m scripts.indicator_brief ter-178
.venv/bin/python -m scripts.indicator_brief bes-01SAL001 --level provincia
```

Il brief è per livello, in ogni sua parte: cifre, stato dell'articolo e `vintage`
richiesto. Chiudendo, stampa il valore che il campo `level` deve avere. Prima
ignorava il livello nel blocco finale, quindi su `--level provincia` dichiarava
scritte le sezioni dell'articolo *regionale* davanti a una pagina vuota.

Il brief stampa la graduatoria completa con la variazione di ogni territorio dal
primo anno, dove la distribuzione si spezza davvero, chi si è mosso in
controtendenza e che cosa la pagina dice già da sola. Esiste per una ragione
precisa: scrivendo contro due o tre cifre pescate dall'API si finisce per
riscrivere la stessa fetta che il cruscotto stampa già, ed è da lì che nasce la
prosa banale.

Le regole editoriali complete stanno in `.claude/agents/indicator-writer.md` e in
`content/STYLE.md`.

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

`tests/test_indicator_texts.py` copre la parte meccanica:

- struttura, ruoli noti e non duplicati, punteggiatura editoriale, `vintage` e
  risoluzione dell'indicatore,
- lunghezza della prima frase del `lead`, che deve reggere da sola in SERP,
- H2 scritti a mano non riutilizzati su più indicatori,
- **ogni cifra con decimale attribuita a una regione** ("il 24,3% del Molise")
  confrontata con il dato di quell'anno,
- **ogni soglia asserita su un elenco di regioni** ("supera il 78% in A, B e C")
  verificata regione per regione.

Le ultime due nascono da errori reali: una nota diceva che l'affollamento
carcerario supera "ovunque" la capienza mentre tre regioni erano sotto, e
un'altra metteva la Sardegna sopra il 78% di differenziata quando stava al
76,6%. Un intero senza decimale non viene controllato, perché in questa prosa è
quasi sempre un'approssimazione ("circa 27%", "quasi 78%").

`tests/test_indicator_view.py` copre i numeri: ogni aggregato di tutti i 621
indicatori è confrontato con una fixture estratta dal codice precedente, e ogni
pagina viene resa per verificare che non ci siano 500.

Restano **fuori dai test**, e vanno rivisti a mano. Non a memoria, però:
`.venv/bin/python -m scripts.review_queue` cerca esattamente questi pattern e
mette in fila gli articoli per quanto è probabile che siano sbagliati, e
`.claude/agents/indicator-reviewer.md` è l'agente che li legge, e gira ogni
giorno.

Un articolo firmato porta **due** campi, `reviewed_at` e `reviewed_vintage`, e
solo con entrambi esce dalla coda. Il secondo è il `vintage` che il revisore
aveva davanti: quando lo scrittore aggiorna l'articolo su un anno nuovo tutte le
cifre cambiano, i due valori smettono di combaciare e l'articolo **rientra** in
coda col segnale `rilettura`, che pesa più di ogni segnale di rischio. Gli altri
marcano una frase che potrebbe essere sbagliata, quello marca un articolo in cui
non è stato controllato niente. Vedi
[`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).

- le affermazioni universali su un andamento ("è cresciuto ovunque"): il brief
  ha un blocco apposta, `SI MUOVONO CONTROCORRENTE`,
- le attribuzioni causali ("grazie a", "spinto da"): o si documentano o si
  riformulano come contesto, non come causa accertata,
- i confronti con l'estero ("tra i più alti d'Europa"): richiedono una fonte in
  `fonti`, verificata, altrimenti vanno tolti,
- **le cifre attribuite a una provincia**: la regex delle guardie conosce solo le
  venti regioni, quindi in un articolo BES a livello provinciale nessun controllo
  automatico le verifica.

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
python3 /home/nilo/dev/ai-agents/skills/italian-product-copywriter/references/audit_editorial_quality.py .
git diff --check
```

L'audit editoriale è il controllo che conta sui trattini, e va usato al posto di
un `grep` sui sorgenti. Un `grep -rn "[—–;]" app/templates` restituisce sempre
righe, perché i template contengono CSS e JavaScript pieni di punti e virgola, e
soprattutto **non vede le entity**: `&ndash;` rende un trattino medio vietato da
`content/STYLE.md` senza che il carattere compaia nel sorgente. È così che
"Copertura 2015 – 2024" è rimasto in pagina.

Controllare almeno una pagina per ciascuna famiglia e per ciascuna forma:
percentuale, rapporto, valore assoluto, unità per abitante, punteggio, differenza
tra tassi, serie con un solo anno, indicatore contestuale e indicatore BES a due
livelli territoriali.
