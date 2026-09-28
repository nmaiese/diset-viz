Revisione dello strumento 2b su `3e37b9a6` (SHA di `git rev-parse HEAD` e di `gh pr view 290 --json headRefOid` coincidono). `bin/py -m unittest tests.integration.test_editoriale_guardia`: 23 test, OK, 5,3 s. Nessun file toccato.

## Risposte alle cinque domande

**1) Fa i cinque controlli, e nel modo descritto.** Sì, tutti e cinque, e tre su cinque sono solidi.

- **2 (link) è il più rigoroso.** Non confronta stringhe: risolve il codice con `sources.parse_indicator_code`, costruisce la scheda con `build_indicator_view` e confronta con `canonical_path`. Verificato che regge anche la forma a due livelli `/province` (bes-01SAL001 va verde sulle due forme canoniche e rossa su `/province/` in coda e su `/province/` nel mezzo).
- **3 (marcatori) disegna davvero**, con la stessa chiamata che fa la pagina (`app/views.py:323` → `charts.render`), stesse firme, stesso `level_key`.
- **4 e 5** bloccano, e i caratteri di 5 sono esattamente i quattro di `content/STYLE.md:20-25`.
- **1 (cifre)** implementa esattamente la regola dell'issue sul valore assoluto quando la direzione è a parole (`guardia.py:190-193`), ed è provata. Ma vedi il punto 2: è proprio questo controllo a non reggere.

**2) Ci sono casi in cui dà verde su un difetto vero o rosso su un testo corretto?** Sì, entrambi. Il rosso su testo corretto è grave e misurabile.

### 2a. [bloccante] Con il dossier vero, il controllo 1 si rosso sul 24% degli articoli pubblicati

Ho passato il dossier vero (`brief.build`) agli articoli committati, tutti:

```
articoli: 383  verdi col dossier reale: 291  rossi: 90  dossier non costruibile: 2
cifre segnalate sugli articoli rossi: 408
```

90 articoli su 381, con 408 cifre segnalate. Non sono errori degli articoli: è il dossier a non contenere le cifre che un articolo corretto può legittimamente citare. Esempio verificato, ter-17:

```
l'articolo scrive: "Nel 2018 la Calabria stava al 15,1%"
il dato:           matrix/2018/calabria = 15.0688  -> arrotonda a 15,1  (articolo CORRETTO)
il dossier:        244 cifre, 15,1 non c'e'       -> la guardia lo segnala
```

Lo stesso per i valori di una serie storica di un territorio, per le medie delle ripartizioni (`repartizioni.valori` è vuoto per ter-167, che l'articolo cita lo stesso: "dal 5,4% del Nord-ovest all'8,6% del Centro"), per le serie per sesso, per gli assoluti in milioni e per i separatori delle migliaia. Sono tutte cifre che la pagina rende e il dossier non porta.

Il punto è che **questa classe di errore non la può vedere la suite**, per costruzione: `AllCommittedArticles` chiama `check_article(key, article)` senza dossier (`test_editoriale_guardia.py:38`), quindi il "verde su tutti gli articoli committati" che la issue chiama vincolo decisivo è asserito su un ramo di codice in cui il controllo 1 non gira mai. E `Figures` usa un dossier giocattolo da un solo valore (`:128`), mai uno vero.

Perché la issue non lo impedisce: il vincolo decisivo è dichiarato per gli articoli **senza** dossier ("su di loro girano solo i controlli 2-5"). Il fatto che il vincolo valga è confermato: 383 articoli verdi senza dossier, ter-901 e ter-12 verdi. Ma la consequence è che il controllo 1, che è metà della guardia, non è mai stato girato una volta contro un articolo vero. Va deciso col team leader, e per me la correzione minima non sta nella guardia: sta nel dossier, che dovrebbe portare la `matrix` (o la guardia, che la può già costruire perché `build_indicator_view` è già importato). La issue dice di non ammorbidire la guardia e di portare i difetti trovati al team leader: questo è esattamente il caso, e la strada che risolve è allargare la sorgente, non allentare il confronto.

### 2b. [bloccante] `--fonti` da solo viene ignorato in silenzio

La CLI pubblica `--fonti` e la issue dice che le previsioni 2026 e il dato fuori catalogo stanno in `fonti.md`. Ma il controllo gira solo se c'è il dossier:

```
scripts/editoriale/guardia.py:359   source_values = source_figures(args.fonti) if args.fonti is not None else []
scripts/editoriale/guardia.py:332   if dossier is not None:
                                       defects += check_figures(fields, dossier, source_values or [])
```

Chi prepara `fonti.md` e passa solo `--fonti` ottiene `guardia: ter-12 pulito`, rc=0, senza una riga che dica che il controllo non è girato. La via d'uscita esiste ma è una trappola, perché la documentazione della CLI non dice che `--fonti` da solo non fa niente. Correzione minima: `if dossier is not None or source_values:`, così il confronto gira sul pool delle fonti anche senza dossier.

### 2c. Verde su un difetto vero: il punto decimale inglese non è controllabile

```
"Il tasso e' 99.8 per mille."   -> 0 difetti
"il valore e' 12.5%"             -> 0 difetti
```

`NUMBER_RE` (`:104`) accetta solo `\d{1,3}(\.\d{3})+` o `\d+`, quindi su "9.8" aggancia "9", e `_is_checkable` (`:116-118`) per un intero pretende un "%" subito dopo. Un numero che la guardia non sa leggere è un numero che non controlla, e qui il verde è silenzioso. È una forma che i modelli producono, e il sito scrive sempre la virgola. Correzione minima: in `_is_checkable`, trattare come controllabile anche `\d{1,3}\.\d{1,2}` non seguito da una terza cifra.

### 2d. Rosso su un testo corretto: nessun altro trovato

Ho provato slug sbagliato, codice inesistente, ancore, slash finale, `/province` nelle due posizioni, marker senza `con=`, marker `ritratto` con nome di regione sbagliato, sezioni libera vuote, cifre derivate, conteggi, ranghi, anni: tutti verdi o rossi come devono. La guardia non straripa sui dati veri.

## 3) Riuso: buono, non c'è riscrittura

`indicator_store.read`/`load_all` (che tira dentro `analizza` per `_read_file`), `prose_lint.LINK`/`prose_fields`, `charts.MARKER_RE`/`parse_args`/`figure`/`portrait` con le firme della pagina, `numfmt.text` per il suggerimento dei valori vicini, più `brief.resolve`, `indicator_texts.LIBERA`/`DEFAULT_LEVEL`, `sources`, `build_indicator_view`. Niente da rivedere.

Una sola nota: i test dei marcatori passano chiavi nude (`"12"`, `"901"`) mentre la CLI passa `"ter:12"`. Entrambe funzionano solo perché `charts._values` (`:90`) ripiega su `split_internal_id`, quindi il test verde dei marcatori non esercita la forma di chiave che usa la produzione.

## 4) Copertura dei test: buona sui controlli 2-5, cieca sul controllo 1

Coperti bene: tipografia (rosso e verde), sezioni libera (rosso, verde, corpo vuoto), link (quattro rossi e un verde), bozza costruita coi tre difetti insieme, verde su tutti gli articoli committati.

Lacune, tutte sul controllo 1 e tutte per lo stesso motivo del punto 2a:

- `Figures` non gira mai contro un dossier vero e un articolo vero: è la ragione per cui 2a è invisibile ai test. Il test che manca è uno solo e costa poche righe: costruire il dossier di un articolo del catalogo e asserire che quell'articolo, come è oggi, è verde. Se quel test passasse, il problema sarebbe risolto; se rosse, lo dice subito e con un numero.
- Nessun caso rosso sui separatori delle migliaia, nessun caso rosso in cui la cifra sta solo in `fonti.md` (c'è solo il verde, `:167`).
- `Markers` (`:108-122`) copre solo `dispersione`: il ramo `ritratto` (`:269`) non è provato, e non c'è il caso rosso "marcatore che non produce SVG perché ha meno di otto punti", che è un modo di morire tipico del renderer.
- `Cli` non ha il caso rosso: non c'è un test che asserisca il codice di uscita 1 né che l'elenco contenga la frase citata, che la issue chiede esplicitamente ("Esce con un codice diverso da zero e con l'elenco dei difetti, ciascuno con la frase citata"). C'è solo il verde e il codice 2.
- Nessun test per `--fonti` da solo né per un `--dossier` illeggibile.

## 5) Problemi di codice

**`scripts/editoriale/guardia.py:231`** — il messaggio dice il contrario di quello che va fatto:

> `defects.append(Defect("link", field, quote, f"{url!r} non e' un link canonico: usa /?indicator="))`

È l'unico punto in cui la guardia dice allo scrittore cosa scrivere, e gli dice di usare la forma che sta rifiutando in quel momento. Minimo: `usa /indicatore/<slug>/<codice>`.

**`scripts/editoriale/guardia.py:294`** — il controllo 4 scrive il nome del campo nella casella del controllo:

> `field, field, _excerpt(body, 0, min(60, len(body))),`

`Defect.check` è documentata come "il controllo che l'ha visto" e gli altri quattro controlli la riempiono con un nome di controllo; qui diventa `sections.libera[1]`. In uscita l'etichetta esce due volte (`[sections.libera[1]] sections.libera[1]: ...`), e ogni aggregazione per `check` perde il controllo 4: è il motivo per cui i test lo cercano su `d.field` invece che su `d.check`, cioè una firma sbagliata che i test hanno imparato invece di segnalare. Minimo: `Defect("sezione", field, ...)` e due asserzioni da spostare su `d.check`.

**`scripts/editoriale/guardia.py:358`** — un `--dossier` che non esiste esce con traceback e codice 1:

> `dossier = json.loads(args.dossier.read_text(encoding="utf-8")) if args.dossier is not None else None`

Il `FileNotFoundError` non è catturato, e il codice 1 per eccezione è indistinguibile dal codice 1 per difetti trovati. `source_figures` già tratta il file mancante come "nessuna fonte" (`:150`); qui va lo stesso, o `parser.error`.

**`scripts/editoriale/guardia.py:302`** — `TYPO_RE = re.compile(r"[—–;…]")` è fedele alla spec, ma `content/STYLE.md:43-44` vieta anche i caporali e le lineette spaziate. Non lo segnalo come difetto: la issue elenca quattro caratteri e aggiungerne altri cambierebbe il contratto, quindi è una domanda per il team leader, non un bug.

## Verdetto

**DA CORREGGERE**, su `3e37b9a69f16829053d6c20defcdfcd1bca7ba1b`.

Non per la forma, che è buona e riusa bene il codice esistente: per due cose che valgono un rosso o un verde sbagliato. Il controllo 1, con il dossier vero, blocca 90 articoli pubblicati corretti su 381, e la suite non lo può vedere perché lo esercita solo con un dossier da un valore. E `--fonti` da solo dice "pulito" senza controllare niente. Il resto sono tre correzioni di poche righe (il messaggio invertito sul link, l'etichetta del controllo 4, il traceback sul dossier illeggibile) più la casella dei test mancanti.

Il primo punto non lo risolvo io: è una decisione sul contratto fra dossier e guardia, e la issue la assegna al team leader. Quello che chiedo è che la decisione sia presa con il numero in mano, perché il numero è 90 e non una percezione.

