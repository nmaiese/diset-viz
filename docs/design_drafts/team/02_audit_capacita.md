# Audit delle capacità già presenti per la redazione delle schede indicatore

## Perimetro e conclusione

Questo audit fotografa il repository al 28 settembre 2026. Il problema da non
ricreare è misurato: il vecchio sistema aveva 21 agent, cinque riscritture della
pipeline, costi osservati fra 18,6 e 33,6 dollari per pagina e un brief che
consegnava statistica descrittiva prima del significato per il lettore
(`git show 9730a3fc:docs/RIPARTENZA.md`:24-87). Il traffico indicava invece come
leva le schede già visibili su Google, soprattutto `ter-104`, `ter-281`,
`ter-13`, `ter-901` e `ter-12` (`git show 9730a3fc:docs/RIPARTENZA.md`:89-105).

La base utile esiste già. Il repository sa costruire la fotografia numerica di
una scheda, collegare alcune famiglie per sesso, conservare fonti verificate,
scrivere in forma libera e inserire due tipi di grafico nel testo. Non esiste
però un unico pacchetto editoriale che unisca dimensioni, contesto, fonti e
domanda per il lettore. Soprattutto, la guardia locale che verificava struttura
e cifre degli articoli, `tests/integration/test_indicator_texts.py`, non è più
presente: il documento di contratto continua a descriverla come attiva
(`docs/INDICATOR_PAGES.md`:475-531), mentre il test storico dichiarava che i
controlli numerici erano nati da errori realmente pubblicati
(`git show eb2c2f72^:tests/integration/test_indicator_texts.py`:1-13).

## SCOUT

### 1. Come ottenere tutte le dimensioni di una misura

Non c'è una sola strada, perché le fonti conservano le dimensioni in tre forme
diverse (`docs/FAMIGLIE_INDICATORI.md`:27-32).

1. **Catalogo territoriale storico (`ter-*`).** Il CSV è piatto: sesso ed età
   possono stare nel titolo di id distinti, non in colonne strutturate
   (`docs/FAMIGLIE_INDICATORI.md`:32-51). Per il sesso esiste già
   `config/indicator_families.csv`: 30 famiglie e 89 indicatori, ricavati dai
   suffissi totale/maschi/femmine e verificati contro il campo ufficiale di
   articolazione di genere (`docs/FAMIGLIE_INDICATORI.md`:56-82). La pagina legge
   quella mappa e restituisce gli altri valori della stessa misura tramite
   `_dimension_siblings` (`app/indicator_view.py`:963-1014). La mappa copre oggi
   solo `sesso`; non rappresenta fasce d'età alternative come dimensione
   navigabile (`config/indicator_families.csv`:1-90).
2. **Serie SDMX.** `dimension_order` e `dimension_values` esistono già, ma le
   query fissano i codici totali `SESSO=9` ed `ETA1=99`; sesso, età, tipo di
   nucleo e gerarchia regione/provincia esistono a monte e sono filtrati nella
   chiave (`docs/FAMIGLIE_INDICATORI.md`:109-138). Per uno scout questo significa
   che scoprire la dimensione non richiede inferenza dal testo; esporla nel sito
   richiede però una nuova query/configurazione e un percorso dati.
3. **BES.** Il file usato contiene `SESSO` strutturato e il refresh produce già
   un CSV separato per Totale/Maschi/Femmine con manifest di copertura, ma la
   vista indicatore non lo collega ancora (`docs/FAMIGLIE_INDICATORI.md`:161-216).
   Gli Excel per età, sesso più età e titolo di studio sono presenti nello ZIP
   della fonte ma non vengono aperti (`docs/FAMIGLIE_INDICATORI.md`:150-159).
4. **Regione/provincia.** `build_indicator_view` normalizza una serie regionale e
   aggiunge il livello provinciale quando la famiglia BES lo possiede
   (`app/indicator_view.py`:108-135). Alcune misure equivalenti stanno invece in
   due schede gemelle collegate esplicitamente, non in una famiglia generale
   (`app/indicator_view.py`:196-229; `app/taxonomy.py`:340-366).

Quindi, per un indicatore, lo scout dovrebbe prima leggere
`build_indicator_view(family, id)`, poi `dimension_siblings`, poi la gemella di
livello e infine le dimensioni ancora non cablate indicate da
`docs/FAMIGLIE_INDICATORI.md`. Limitarsi al titolo o agli id adiacenti perde
famiglie reali (`docs/FAMIGLIE_INDICATORI.md`:41-51,103-107).

### 2. Cosa danno già i moduli numerici

- **`app/indicator_view.py`.** È il pacchetto più vicino al brief della scheda:
  `meta` porta nome, unità, verso, fonte, tema, canonico e licenza
  (`app/indicator_view.py`:246-308); ogni livello porta anni, classifica
  dell'ultimo anno, estremi, statistiche, variazione annuale, copertura, matrice
  territorio/anno e medie annuali semplici (`app/indicator_view.py`:629-718).
  Aggiunge correlate tematiche, fratelli di dimensione, livelli e payload del
  cruscotto (`app/indicator_view.py`:138-171). Non formula da solo la domanda
  editoriale né sceglie una fonte di contesto.
- **`app/indicator_universe.py`.** Enumera tutte le pagine pubbliche partendo dai
  registri di famiglia, comprese le 40 BES solo provinciali che il catalogo
  regionale perderebbe (`app/indicator_universe.py`:29-43). La sua proiezione è
  una coda compatta: metadati, livello predefinito, estremi temporali, numero di
  territori e pannello della sparkline, non tutta la matrice
  (`app/indicator_universe.py`:46-89). È adatta a scegliere e ordinare il lavoro,
  non basta da sola per scrivere.
- **`scripts/trend_articles/dossier.py`.** Per gli indicatori richiesti produce
  fonte, archivio, unità, anni, URL canonico, classifica, serie completa,
  variazioni, medie semplici e un elenco di cifre già formattate e attribuite
  (`scripts/trend_articles/dossier.py`:1-21,57-130). Scrive anche un CSV
  scaricabile e un `dossier.json` (`scripts/trend_articles/dossier.py`:133-168).
  È riutilizzabile come calcolatore, ma il suo contratto è quello degli articoli
  trend: non raccoglie automaticamente sesso/età/fratelli né apre con una
  spiegazione in lingua comune.
- **`derive_*`.** Sono quattro elaborazioni specialistiche, non un motore
  generico: valori ufficiali Italia/Nord/Centro/Mezzogiorno per BES
  (`scripts/trend_articles/derive_bes_areas.py`:1-19), quota regionale di alunni
  stranieri in terza media (`scripts/trend_articles/derive_foreign_pupils.py`:1-22),
  media regionale semplice di dati provinciali, dichiarata non ufficiale
  (`scripts/trend_articles/derive_province_mean.py`:1-10), e regressione degli
  infortuni provinciali sulle quote settoriali
  (`scripts/trend_articles/derive_sector_injuries.py`:1-28). Producono CSV e
  metadati di metodo utilizzabili dal dossier
  (`scripts/trend_articles/derive_bes_areas.py`:61-84;
  `scripts/trend_articles/derive_foreign_pupils.py`:81-110;
  `scripts/trend_articles/derive_province_mean.py`:24-57;
  `scripts/trend_articles/derive_sector_injuries.py`:102-134).

### 3. Fonti secondarie già disponibili

Il registro ammette contesto, non sostituisce il numero primario della scheda;
serve per commenti dell'istituzione, confronti esterni o claim comparativi
(`docs/SECONDARY_SOURCES.md`:1-17). La fonte di verità è
`data/corpus/sources.json`, con fonti istituzionali italiane, UE e territoriali
e un livello di citabilità (`docs/SECONDARY_SOURCES.md`:41-55;
`data/corpus/sources.json`:1-127).

Il corpus verificato è piccolo ma già operativo: ogni claim conserva testo
verbatim, URL, data di lettura, temi e indicatori; le chiavi lessicali evitano
che un claim tematico arrivi a una misura solo vagamente vicina
(`docs/SECONDARY_SOURCES.md`:57-106). Oggi contiene cinque claim: ciclo e
disoccupazione di lunga durata
(`data/corpus/claims/eurostat-lunga-durata-ciclo.json`:1-20), occupazione e
produttività nel divario del PIL
(`data/corpus/claims/istat-coesione-occupazione.json`:1-23;
`data/corpus/claims/istat-coesione-produttivita.json`:1-23), ricambio naturale
(`data/corpus/claims/istat-ricambio-naturale-2026.json`:1-10) e particolato nel
bacino padano (`data/corpus/claims/snpa-bacino-padano-2025.json`:1-15).

`scripts/fetch_corpus.py` riscarica HTML con la libreria standard, normalizza
solo spazi e segni tipografici e cerca la citazione come stringa; segnala PDF e
blocchi HTTP invece di aggirarli (`scripts/fetch_corpus.py`:1-23,48-103). Questo
prova che la citazione compare nell'URL, non che la parafrasi dell'articolo sia
fedele o pertinente.

### 4. Contesto economico regionale già nel catalogo

Per dare contesto economico senza cercare subito un nuovo dataset, lo scout ha
già almeno questi `ter-*`:

- `ter-901`, PIL pro capite (`app/static/data/Assoluti_Regione.csv`:102812);
- `ter-345`, occupazione 20-64 anni, con famiglia totale/maschi/femmine
  (`app/static/data/Assoluti_Regione.csv`:71907;
  `config/indicator_families.csv`:70-72), e `ter-13`, occupazione 15-64 anni,
  anch'esso con le tre varianti (`app/static/data/Assoluti_Regione.csv`:1962;
  `config/indicator_families.csv`:67-69);
- `ter-902`, reddito disponibile delle famiglie per abitante
  (`app/static/data/Assoluti_Regione.csv`:103412), `ter-906`, reddito primario
  per abitante (`app/static/data/Assoluti_Regione.csv`:105812), `ter-907`, saldo
  della redistribuzione per abitante (`app/static/data/Assoluti_Regione.csv`:106412),
  e `ter-930`, indice di Gini del reddito
  (`app/static/data/Assoluti_Regione.csv`:110892).

Questi sono contesti, non spiegazioni causali. Il grafico già pubblicato su
`ter-901` mette infatti il PIL accanto a `ter-345`, ma il testo separa il pattern
dalla spiegazione istituzionale (`content/indicators/901.md`:25-43).

## SCRITTORE

### 1. Contratto della pagina e formato su disco

Il contratto distingue cruscotto, articolo e apparato; i numeri stanno nel
cruscotto e la prosa li interpreta senza ricopiare massimo, minimo e media
(`docs/INDICATOR_PAGES.md`:7-21,140-151). La forma storica dell'articolo è:

1. `definizione`, cosa misura e perimetro;
2. `quadro`, distribuzione attuale;
3. `dinamica`, serie lunga e ultimo passaggio;
4. `limiti`, ciò che il numero non cattura.

L'ordine e i quattro ruoli sono definiti in
`docs/INDICATOR_PAGES.md`:211-233. Un ruolo mancante viene composto dal template,
quindi una pagina che rende non è necessariamente una pagina finita
(`docs/INDICATOR_PAGES.md`:225-233).

Su disco ogni articolo è `content/indicators/<chiave>.md`: frontmatter, lead e
sezioni aperte da `<!-- sezione: ruolo -->`, con H2 scritto dall'autore
(`docs/INDICATOR_PAGES.md`:174-180). `scripts/indicator_store.py` possiede la
codifica: il lead precede la prima sezione, i campi aggiuntivi di sezione sono
commenti JSON e ogni sezione richiede un ruolo
(`scripts/indicator_store.py`:327-364,302-323). Il conteggio parole canonico del
repository usa lead più corpi, escludendo frontmatter e titoli
(`app/editorial_state.py`:23-33).

### 2. Voce e modelli

`content/STYLE.md` non è oggi un contratto autosufficiente per le schede: dice
esplicitamente che il suo scope principale è il blog e rimanda le pagine
indicatore al repo esterno `nmaiese/redazione-ai`, oggi dismesso; conserva però
le tecniche giornalistiche comuni (`content/STYLE.md`:1-16). Quelle tecniche
chiedono un punto solo, un filo deciso prima della scrittura, apertura sul
significato, scala umana, un contrasto concreto e una sola idea per frase
(`content/STYLE.md`:72-129). Vietano inoltre caratteri tipografici specifici e
privilegiano leggibilità su ornamento (`content/STYLE.md`:18-30,41-57).

`content/esempi/` è la parte più direttamente riutilizzabile: si sceglie un
solo testo con forma narrativa simile, lo si legge ad alta voce e se ne copia il
movimento, non le parole (`content/esempi/README.md`:25-38). La cartella esiste
proprio perché i divieti e le guardie precedenti producevano testi corretti ma
faticosi e non misuravano la necessità di rilettura
(`content/esempi/README.md`:1-23).

### 3. Il contratto impedisce un articolo più lungo e discorsivo?

**Non più.** I quattro ruoli restano il default, ma una sezione `libera` attiva
la forma interamente autorata: mantiene ordine e titoli scelti dall'autore e non
compone fermate mancanti (`docs/INDICATOR_PAGES.md`:292-324). `ter-901` la usa
già con quattro sezioni narrative e un grafico nel mezzo
(`content/indicators/901.md`:18-50). Non esiste un tetto parole nel formato; le
schede ad alto traffico arrivano già a 711 e 737 parole secondo la funzione
canonica (`app/editorial_state.py`:23-33; `content/indicators/901.md`:16-50;
`content/indicators/104.md`:18-53).

I vincoli reali per un pezzo discorsivo sono qualitativi: una cifra compare una
volta, il metodo sta fuori dal racconto, i grafici non duplicano il cruscotto e
la scheda deve restare comprensibile se una figura sparisce
(`docs/INDICATOR_PAGES.md`:140-156,326-375). Nessuno di questi impone quattro
fermate o una lunghezza corta. Il problema è invece documentale: l'apertura di
`INDICATOR_PAGES.md` continua a dire «quattro sezioni in ordine fisso», mentre
la sezione successiva documenta la forma libera
(`docs/INDICATOR_PAGES.md`:13-20,292-324).

## GRAFICO

### 1. Figure dentro una scheda indicatore

Il percorso è interamente runtime:

1. il marcatore `<!-- grafico: dispersione ... -->` oppure
   `<!-- grafico: ritratto ... -->` vive nel corpo di una sezione in
   `content/indicators/<chiave>.md` (`app/charts.py`:9-28);
2. `indicator_store` lo conserva come testo, purché non sia la prima riga del
   corpo, dove verrebbe scambiato per un campo extra
   (`scripts/indicator_store.py`:270-299);
3. il template converte Markdown in HTML e alla riga 66 applica il filtro
   `figures(meta.id, level.key)` (`app/templates/_indicator_article.html`:58-71);
4. `app/charts.py` sostituisce il commento con `<figure>` e `<figcaption>`,
   rileggendo i dati correnti; in caso di errore restituisce stringa vuota
   (`app/charts.py`:256-271).

Non esiste quindi un file SVG della scheda da salvare o versionare. I percorsi
sono il Markdown sorgente in `content/indicators/`, il filtro nel template e il
renderer `app/charts.py`; il disegno cambia con i dati
(`app/charts.py`:30-41). Esempi reali: dispersione PIL/occupazione in
`content/indicators/901.md`:31-35 e ritratto regionale multi-indicatore in
`content/indicators/bes__01SAL010.md`:46-51.

La dispersione richiede almeno otto territori comuni e produce una didascalia
che nomina indicatori, anni, numerosità ed evidenze
(`app/charts.py`:52-60,175-199). Il ritratto colloca una regione fra minimo e
massimo su almeno due indicatori, senza confrontare unità incompatibili
(`app/charts.py`:202-253).

### 2. Cosa sa fare `scripts/trend_articles/figures.py`

Questo script appartiene agli articoli trend/blog, non alle schede. Genera SVG
committibili in `content/figures/<slug>/<nome>.svg`, richiamati dal marcatore
diverso `<!-- figura: nome -->` (`scripts/trend_articles/figures.py`:1-27,
385-388). Offre quattro figure:

- classifica completa a barre e versione soli estremi
  (`scripts/trend_articles/figures.py`:92-158);
- linee temporali di territori, medie semplici oppure ripartizioni ufficiali
  (`scripts/trend_articles/figures.py`:161-238);
- dispersione su livelli o variazioni, con correlazioni complessive e separate
  fra Centro-Nord e Mezzogiorno (`scripts/trend_articles/figures.py`:241-275);
- accessibilità e autonomia della figura tramite titolo, descrizione, fonte,
  unità e anno nell'SVG (`scripts/trend_articles/figures.py`:52-89).

Lo script non alimenta oggi il filtro `figures` delle schede: usa un marcatore,
una directory e un renderer diversi. Riutilizzarlo nelle schede richiederebbe
integrazione di codice, non solo copiare un comando
(`scripts/trend_articles/figures.py`:1-8;
`app/templates/_indicator_article.html`:58-71).

### 3. Colori dei dati

La regola è netta: arancio bruciato per interazione o unica evidenza, mai come
scala di dati; dati quantitativi sulla rampa blu; ripartizioni fisse Nord blu,
Centro oliva e Mezzogiorno prugna; niente verde/rosso per giudicare
(`design/v1/SISTEMA.md`:17-36). Il CSS espone sei `--seq-*`, `--data-focus`,
`--data-reference`, null, bordi mappa e `--area-*`
(`app/static/css/ds/system.css`:23-95). I nomi semantici per mappa, assi, griglia,
mediana e highlight rimandano ai token, non a esadecimali locali
(`app/static/css/ds/system.css`:247-269). Il tema scuro ridefinisce la rampa e le
ripartizioni (`app/static/css/ds/system.css`:423-477). Colore non significa mai
meglio/peggio e la rampa segue la grandezza indipendentemente dal verso
(`design/v1/SISTEMA.md`:536-543,559-573).

## REVISORE

### 1. Guardie rimaste

- **`scripts/prose_lint.py`.** Conta lessico spia, falsi intervalli, riassunti,
  numeri duplicati, slogan, domande finali e ripetizioni numeriche; include
  titoli, lead e corpi e restituisce anche link interni e conteggio parole
  (`scripts/prose_lint.py`:57-146,175-277). È esplicitamente un report, non un
  gate, e lascia a una persona filo, nut graf, digressione e regola del tre
  (`scripts/prose_lint.py`:19-32).
- **`tests/integration/test_indicator_texts.py`.** Al `HEAD` non esiste. La
  documentazione gli attribuisce struttura, ruoli, vintage, prima frase, H2,
  cifre decimali regionali, soglie territoriali e link canonici
  (`docs/INDICATOR_PAGES.md`:475-500), ma quella capacità era nel file storico
  poi rimosso (`git show eb2c2f72^:tests/integration/test_indicator_texts.py`:49-159).
  L'attuale `tests/integration/test_indicator_text.py` verifica invece articoli
  grammaticali generati, resa delle fonti e assenza della vecchia FAQ
  (`tests/integration/test_indicator_text.py`:1-8,22-41,119-147): non è un
  sostituto del fact-check degli articoli scritti.
- **`scripts/duplicazione.py`.** Renderizza le pagine, separa racconto e blocco
  metodo e misura quante parole cadono in sequenze di otto parole condivise da
  più di cinque pagine (`scripts/duplicazione.py`:1-39,52-103). Misura voce
  seriale e boilerplate, non verità, coerenza o leggibilità di una singola
  scheda.
- **`scripts/audit_link_interni.py`.** Su tutte le URL della sitemap controlla
  HTML, Markdown, JSON-LD e JSON; ogni destinazione interna deve rispondere 200
  senza redirect e ogni ancora deve esistere (`scripts/audit_link_interni.py`:1-23,
  47-106,133-157). Conta anche link entranti alle province
  (`scripts/audit_link_interni.py`:164-221). Non apre fonti esterne e non giudica
  se testo dell'anchor o frase circostante siano semanticamente corretti.

### 2. Cosa non viene misurato

Nessuna guardia locale attuale prova in modo generale che una cifra autorata
esista nella serie, che «ovunque» non abbia controesempi, che una causa sia
supportata, che un confronto estero sia omogeneo o che una correlazione non sia
raccontata come meccanismo. Il contratto stesso lascia queste verifiche alla
rilettura umana (`docs/INDICATOR_PAGES.md`:502-528). Anche il corpus verifica la
presenza letterale della citazione nella pagina, non il ragionamento che
l'articolo costruisce sopra (`scripts/fetch_corpus.py`:69-103).

Nessuno dei quattro strumenti misura il difetto osservato nel pilota, cioè
prosa corretta ma grezza: i modelli di registro furono aggiunti proprio perché
le vecchie guardie davano verde a testi che richiedevano rilettura
(`content/esempi/README.md`:14-23,25-44). Servono quindi due revisioni distinte:
una deterministica per struttura/cifre/link/fonti e una umana, breve, per filo,
chiarezza e utilità.

## Le cinque schede con più traffico citate in RIPARTENZA

Il conteggio seguente usa la funzione ufficiale `parole(entry)`: lead più corpi
delle sezioni, con semplice split sugli spazi
(`app/editorial_state.py`:23-33). «Sezioni» indica quelle autorate nel Markdown,
non eventuali fallback composti dal template.

| scheda | parole | sezioni autorate oggi | dimensioni della famiglia oggi |
| --- | ---: | ---: | --- |
| `ter-104` | 737 | 5: definizione, due quadri, dinamica, limiti (`content/indicators/104.md`:18-53) | Solo regioni; 25-64 anni è perimetro fisso della misura, non dimensione navigabile; nessun fratello in `config/indicator_families.csv` (`content/indicators/104.md`:18-23; `config/indicator_families.csv`:1-90). |
| `ter-281` | 266 | 2: quadro e limiti (`content/indicators/281.md`:12-20) | Solo regioni e nessun fratello di misura mappato (`config/indicator_families.csv`:1-90); la gemella provinciale nota è `bes-07SIC001`, non `ter-281` (`app/taxonomy.py`:349-359). |
| `ter-13` | 555 | 4: definizione, quadro, dinamica, limiti (`content/indicators/13.md`:14-50) | Regione × sesso: totale `13`, maschi `177`, femmine `178`; età 15-64 fissa nella misura (`config/indicator_families.csv`:67-69; `app/static/data/Assoluti_Regione.csv`:1962). |
| `ter-901` | 711 | 4 sezioni libere (`content/indicators/901.md`:16-50) | Solo regioni e nessun fratello di misura mappato (`config/indicator_families.csv`:1-90; `app/static/data/Assoluti_Regione.csv`:102812). |
| `ter-12` | 636 | 4: definizione, quadro, dinamica, limiti (`content/indicators/12.md`:7-29) | Regione × sesso: totale `12`, maschi `175`, femmine `176`; età 15+ fissa nel denominatore (`config/indicator_families.csv`:55-57; `app/static/data/Assoluti_Regione.csv`:1802). |

Il campione smentisce già due assunzioni utili da evitare: una pagina di valore
può avere due, quattro o cinque sezioni, e quattro sezioni non implicano la
vecchia struttura perché `ter-901` usa solo ruoli `libera`
(`content/indicators/281.md`:12-20; `content/indicators/104.md`:18-53;
`content/indicators/901.md`:18-50).

## Gap per ruolo

| ruolo | cosa manca | serve codice (PR) o solo contenuto? |
| --- | --- | --- |
| **Scout** | Un comando unico che, dato un `ter-*`, unisca view completa, fratelli per sesso, eventuale gemella provinciale, dimensioni SDMX/BES non cablate, indicatori economici correlati e claim pertinenti. Oggi questi pezzi vivono in moduli separati (`app/indicator_view.py`:108-171; `docs/FAMIGLIE_INDICATORI.md`:109-216; `docs/SECONDARY_SOURCES.md`:57-106). | **PR** per aggregatore e per esporre sesso/età/provincia mancanti. **Contenuto** per ampliare registro e claim del corpus. |
| **Scrittore** | Un contratto locale coerente: `STYLE.md` rimanda a una redazione esterna dismessa e `INDICATOR_PAGES.md` afferma sia ordine fisso sia forma libera (`content/STYLE.md`:1-16; `docs/INDICATOR_PAGES.md`:13-20,292-324). Manca inoltre un brief che apra con significato e fotografia, non con statistiche, difetto già diagnosticato (`git show 9730a3fc:docs/RIPARTENZA.md`:64-83). | **Solo contenuto/documentazione e prompt** per scrivere pezzi da 500-900 parole usando `libera`; lunghezza e libertà erano l'obiettivo dichiarato della ripartenza e il renderer lo supporta già (`git show 9730a3fc:docs/RIPARTENZA.md`:178-182; `docs/INDICATOR_PAGES.md`:292-324). |
| **Grafico** | Le schede hanno solo dispersione e ritratto runtime; barre, estremi e linee di `trend_articles/figures.py` usano un formato blog incompatibile (`app/charts.py`:9-41; `scripts/trend_articles/figures.py`:1-27). Manca una guardia che fallisca se un marcatore di scheda non si disegna, mentre oggi il renderer lo elimina (`app/charts.py`:256-271). | **PR** per nuovi tipi di figura condivisi e validazione pre-pubblicazione. **Solo contenuto** se bastano dispersione/ritratto già disponibili. |
| **Revisore** | Ripristinare una guardia locale unica per formato, livello, vintage, marcatori, cifre territoriali, asserti universali, link e pertinenza dei claim. Il test che la documentazione descrive non esiste più e quello corrente copre altro (`docs/INDICATOR_PAGES.md`:475-531; `tests/integration/test_indicator_text.py`:1-8). Resta comunque necessaria una lettura umana per cause, filo e fatica (`docs/INDICATOR_PAGES.md`:502-528; `content/esempi/README.md`:14-23). | **PR** per guardie deterministiche. **Contenuto/processo** per checklist umana breve, senza rubrica a punti. |

Priorità consigliata: prima guardia deterministica e brief unico dello scout,
poi una run su tre schede usando `libera`, infine solo i tipi di grafico che le
tre storie dimostrano necessari. Questo rispetta il limite storico di massimo
tre agenti e due giri di correzione, proposto proprio per evitare un'altra
pipeline costosa (`git show 9730a3fc:docs/RIPARTENZA.md`:164-194).
