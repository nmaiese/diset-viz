# Proposta: pipeline editoriale delle schede indicatore

Stato: proposta, non implementata.

## Decisione in breve

La nuova pipeline deve vivere dentro Divario Italia, senza dipendere dalla
vecchia redazione esterna e senza condividere codice, code o prompt con il
blog. Deve trattare la prosa come una trasformazione revisionabile di dati e
fonti già verificati dal progetto:

1. il sito e le pipeline dati producono un dossier strutturato per indicatore
   e livello territoriale
2. un modello genera una bozza in formato strutturato, senza accesso libero al
   web e senza poter introdurre URL o calcoli propri
3. controlli deterministici confrontano ogni cifra, fonte, livello e link con
   il dossier
4. un editor umano rilegge e approva il diff
5. solo il passaggio di promozione scrive, tramite lo store esistente, un file
   in `content/indicators/`

La pipeline non mantiene un proprio stato `pending`, `done` o `stale`.
`app/editorial_state.py` resta il criterio unico. Gli artefatti delle run sono
prove e log, non una seconda coda.

Prerequisito documentale: `content/STYLE.md` contiene ancora un rimando al
contratto `REDAZIONE.md` e alla skill `voce` del repository esterno dismesso.
Prima di attivare questa pipeline, un cambio separato deve sostituire quel
rimando con il contratto interno di `docs/INDICATOR_PAGES.md` e col prompt
versionato qui proposto. Le tecniche giornalistiche e gli assoluti tipografici
che `content/STYLE.md` possiede restano validi. La pipeline non deve caricare
file, skill o istruzioni dal vecchio repository neppure durante la transizione.

## Perimetro e non obiettivi

Il perimetro è l'universo di 634 indicatori costruito da
`app/indicator_universe.py`, organizzato nelle quattro corsie operative del
task:

- indicatori territoriali Istat
- serie regionali normalizzate dal layer esterno, comprese Eurostat e
  demografia Istat
- BES regionale e BES dei Territori
- Multiscopo Istat

La pipeline scrive solo il livello predefinito di ogni indicatore. Il modello
editoriale corrente conserva un solo file per indicatore e una prosa vale per
un solo livello. Le altre viste territoriali continuano a usare il testo
composto dal sito. Una futura prosa distinta per regione e provincia richiede
prima una decisione sullo schema dello store, non una scorciatoia nella
pipeline.

Non sono obiettivi di questa proposta:

- generare o aggiornare post in `content/posts/`
- scoprire nuovi dataset o promuoverli nello scoring
- modificare numeri, direzioni, tassonomie o definizioni
- pubblicare senza revisione umana
- sostituire `app/editorial_state.py` con un database di workflow
- riportare in vita agenti, skill o contratti della vecchia pipeline esterna

## Principi

### Separare calcolo e scrittura

Il modello non deve calcolare medie, variazioni, estremi, parità o coperture.
Questi valori devono arrivare dal view model unico, cioè
`app/indicator_view.py`, oppure da funzioni deterministiche che applicano le
stesse regole. Il dossier contiene sia il valore macchina sia la forma già
pronta per la prosa.

### Separare bozza e pubblicazione

Una chiamata riuscita al modello non modifica `content/`. La bozza vive in un
artefatto di run. La promozione avviene solo dopo tutti i gate e produce un diff
di un solo file per indicatore, leggibile e reversibile in una PR.

### Consentire solo fonti già ammesse

Il modello non cerca fonti durante la scrittura. Riceve identificatori di fonti
primarie e, quando pertinenti, identificatori di claim del corpus secondario.
Gli URL vengono risolti dal codice a partire dai registri del progetto. Un URL
restituito dal modello è sempre un errore.

### Automatizzare la prova, non il giudizio

Le guardie deterministiche provano struttura, identità dei numeri, provenienza,
URL, livello e forma. Non possono stabilire da sole se una definizione è chiara,
se un confronto è giornalisticamente onesto o se una cautela è sufficiente.
Questi restano compiti dell'editor.

## Fonte dati e trigger di aggiornamento

### Fonti per famiglia

| Famiglia | Dati autorevoli già nel progetto | Aggiornamento | Metadati e definizioni |
| --- | --- | --- | --- |
| Territoriali | `app/static/data/Assoluti_Regione.csv` | `scripts/update_data.py`, normalmente dentro `scripts/refresh_official_local.sh` | definizioni territoriali in `data/definitions/istat_territoriali.csv`, fonte pubblica risolta da `app/sources.py` |
| BES | `Assoluti_BES_Regione.csv` e `Assoluti_Provincia.csv`, letti dal layer BES | `scripts/update_bes_regions.py` e pipeline provinciale | archivio federato in `data/definitions/federated.csv`, metadati BES e BES dei Territori |
| Multiscopo | `Assoluti_Multiscopo_Regione.csv` e `multiscopo_regione_manifest.csv` | `scripts/update_multiscopo_regions.py`, incluso nel refresh ufficiale completo | dataflow e codelist SDMX curati in `scripts/multiscopo_sources.py`, definizioni federate |
| Eurostat e layer esterno | `normalized_external_indicators.csv` e `external_indicator_manifest.csv` | build del layer esterno dopo un refresh o una promozione approvata | manifest, `app/sources.py` e definizioni federate |

I file grezzi sono fonti di acquisizione. Il dossier editoriale deve leggere
la proiezione resa dal sito, non ricostruire un quinto catalogo dai CSV. La
catena proposta è:

```text
fonti ufficiali -> pipeline dati esistenti -> indicator_view
                 -> indicator_universe.projection -> dossier editoriale
```

Questo mantiene identici anni, osservazioni, unità, livelli, source label,
canonical path, copertura e regole di ordinamento tra pagina e prosa.

### Quando si apre una run editoriale

Il controllo delle fonti resta manuale e segue `docs/SOURCE_MONITORING.md`:

- territoriali Istat: controllo mensile, circa il giorno 20
- BES regionale: aggiornamenti intermedi e rapporto annuale
- BES dei Territori: rilascio annuale
- Multiscopo e layer esterno: durante il refresh ufficiale completo o dopo una
  promozione dati approvata

Il solo cambio remoto non avvia la scrittura. Prima si esegue il refresh dati,
si revisiona il diff e si superano i test del dataset. Poi si riavvia il
processo, perché cataloghi e proiezioni sono in cache per la vita del processo.
Solo a quel punto la pipeline editoriale legge la coda.

Trigger ammessi:

1. nuovo indicatore senza lead o con sezioni mancanti
2. `vintage` della prosa inferiore a `year_max`
3. nuova definizione ufficiale o modifica della serie nello stesso anno, dopo
   l'estensione di stato descritta più avanti
4. rigenerazione mirata richiesta da un editor per uno o più id

Un cambio di prompt o modello non mette automaticamente 634 schede in coda.
Prima passa da un canary e da una valutazione comparata. La rigenerazione
massiva richiede una decisione editoriale esplicita.

## Unica coda: integrazione con `editorial_state.py`

### Regola iniziale

Il produttore importa direttamente le funzioni del sito:

```python
from app import editorial_state

queue = [
    row for row in editorial_state.build_queue()
    if row["level"] == row["default_level"]
    and editorial_state.da_scrivere(row)
]
```

Non ricalcola `missing`, `stale`, priorità, indicizzabilità o livello. L'ordine
è quello già prodotto da `build_queue()`. Il filtro sul livello predefinito
evita di mettere in coda viste per cui lo store corrente non può conservare una
seconda prosa.

Dopo la promozione, test e riavvio, `editorial_state` rilegge il file. Se lead,
ruoli e `vintage` sono corretti, la voce esce dalla coda. Non serve una chiamata
`mark_done`.

### Revisioni nello stesso anno e definizioni cambiate

Oggi `stale` confronta `vintage` e `year_max`. Non rileva una revisione di dati
o definizione che conserva lo stesso anno massimo. La soluzione non deve stare
nel produttore. In una fase successiva si estende una volta sola
`app/editorial_state.py` con:

- `data_fingerprint`, calcolato dai valori e metadati del livello scritto
- `definition_fingerprint`, calcolato dalla definizione ufficiale usata
- confronto con le impronte registrate nel frontmatter dell'articolo
- un solo predicato `da_scrivere()` che includa anche questi due tipi di
  arretrato

Cruscotto, coda e riepilogo continueranno a leggere la stessa valutazione. La
pipeline conserverà le impronte solo come provenienza del testo, non come stato
parallelo.

`prompt_version`, modello, id della risposta e costo appartengono invece al log
della run. Un cambio tecnico non rende falsa una prosa già pubblicata.

## Architettura proposta

### 1. Selettore

Input: filtri facoltativi per id, famiglia, tema e limite di lotto.

Default: righe predefinite restituite da `editorial_state.build_queue()` per
cui `editorial_state.da_scrivere()` è vero.

Output: lista ordinata di unità `{family, raw_id, id, level, reason}`. `reason`
è copiato dallo stato esistente, non interpretato di nuovo.

### 2. Costruttore del dossier

Per ogni unità produce JSON immutabile con:

- identità: id interno, codice pubblico, nome, famiglia, tema, livello e path
  canonico
- fonte primaria: `source_id`, etichetta pubblica, URL risolto dal registro,
  data di acquisizione se presente
- definizione: testo ufficiale, archivio, riferimento preciso, impronta e stato
  `covered` o `uncovered`
- perimetro: unità, popolazione, età, genere, numeratore e denominatore quando
  la fonte li dichiara
- serie: anni realmente disponibili, copertura e osservazioni del livello
- fatti calcolati: ultimo anno, confronto con il precedente anno disponibile,
  trend lungo, conteggio della base comune, aumenti, diminuzioni, stabilità,
  estremi, parità e missing
- semantica: direzione revisionata o `contextual`, `percentage_like`, numero di
  decimali e distinzione tra percentuali e punti percentuali
- media: solo il campo `regional_mean_simple`, mai chiamato `national_mean`
- relazioni: famiglia di misura, indicatori strettamente collegati, eventuale
  gemella di livello e percorsi già risolti
- prosa corrente: entry esistente, livello, vintage, ruoli mancanti e
  differenze rispetto al nuovo dossier
- fonti secondarie: al massimo due claim pertinenti dal corpus, con `claim_id`,
  citazione verificabile, URL, data di lettura, temi e chiavi di pertinenza
- `facts_hash`, `definition_fingerprint` e versione dello schema del dossier

Ogni fatto ha un id stabile nella run, per esempio
`latest.max.value`, `recent.common_count` o `long.delta_simple_mean`. Le
trasformazioni ammesse, compresi arrotondamento e punti percentuali, sono già
calcolate. Il modello non riceve istruzioni per rifarle.

Un dossier con definizione non coperta, fonte senza URL, livello incoerente o
serie vuota si ferma prima della chiamata LLM.

### 3. Scrittore

Responsabilità divise:

- il comando locale orchestra, costruisce il dossier e conserva gli artefatti
- il modello produce una bozza, non pubblica
- un editor umano possiede giudizio, approvazione e firma della pubblicazione

Modello iniziale candidato: `gpt-5.6-terra`, Responses API, reasoning `low` per
la baseline e `medium` come variante da valutare. La documentazione OpenAI lo
posiziona come bilanciamento tra qualità e costo e raccomanda di scegliere lo
sforzo tramite test rappresentativi. Il nome del modello e lo sforzo sono
configurazione della run, non costanti sparse nel codice. Un cambio di alias o
versione richiede il canary del rollout.

La scelta non è definitiva per reputazione. Il modello viene promosso solo se
batte la baseline sul golden set, con zero regressioni fattuali bloccanti. Una
versione più economica può sostituirlo se supera lo stesso gate.

### 4. Compilatore

Il modello restituisce JSON conforme a schema, non Markdown libero. Forma
minima:

```json
{
  "lead": [{"text": "...", "support": ["fact-id"]}],
  "sections": [
    {
      "role": "quadro",
      "h": "...",
      "sentences": [
        {"text": "...", "support": ["fact-id", "claim-id"]}
      ]
    }
  ],
  "source_ids": ["source-id"],
  "roles_covered": ["quadro", "dinamica", "limiti"]
}
```

Il compilatore:

1. verifica schema e supporti
2. ricostruisce `fonti` da `source_id` e `claim_id`
3. inserisce `vintage`, livello e impronte dal dossier
4. rende il formato posseduto da `scripts/indicator_store.py`
5. produce bozza, report e diff senza scrivere in `content/`

Il modello non restituisce `reviewed_at` o `reviewed_vintage`. Questi campi
sono aggiunti solo dal passaggio umano che ha davvero svolto la revisione.

### 5. Promotore

Il promotore accetta una bozza verificata e un'approvazione esplicita. Rilegge
il dossier corrente e confronta `facts_hash` prima di scrivere. Se dati o
definizione sono cambiati nel frattempo, la bozza è scaduta e torna in coda.

La scrittura usa `scripts/indicator_store.write()` e tocca un solo file. Non
esistono scritture dirette concorrenti sullo stesso indicatore. La PR contiene
bozza compilata, report delle guardie e una nota sintetica sui claim secondari
usati.

## Prompt e contesto

### Prompt di sistema, versionato nel repository

Il prompt deve essere corto, esplicito e testabile. Contratto proposto:

```text
Scrivi una bozza di scheda indicatore Divario Italia usando soltanto dossier e
claim forniti. Non calcolare numeri. Non inventare fonti, URL, cause, soglie,
territori o confronti. Ogni frase fattuale indica gli id che la sostengono.
Chiama regional_mean_simple "media semplice dei valori regionali". Non
chiamarla media italiana o nazionale. Usa dato nazionale solo se il dossier
porta un national_aggregate distinto e compatibile. Mantieni totale, uomini,
donne, regioni e province separati. Per percentuali, variazioni in punti
percentuali. Per indicatori contextual non usare migliore o peggiore. Se il
dossier non basta, restituisci needs_human con il campo mancante. Rispetta
schema, INDICATOR_PAGES.md e gli assoluti tipografici di content/STYLE.md.
```

Seguono istruzioni sulla forma:

- lead di una o due frasi, leggibile da solo
- ruoli e forma libera ammessi dal contratto corrente
- una cifra mostrata una volta, senza riscrivere il cruscotto
- metodo fuori dal racconto
- un filo editoriale, non inventario di massimo, minimo e media
- nessuna attribuzione causale senza `claim_id`
- nessun H2 copiato da un catalogo di titoli fissi
- restituzione `needs_human` quando definizione, compatibilità o fonte sono
  ambigue

### Contesto dato al modello

Per ogni chiamata entrano solo:

1. prompt di sistema e schema di output
2. dossier dell'indicatore
3. entry corrente, se esiste
4. un esempio editoriale in-repo scelto per forma narrativa simile, senza i suoi
   numeri e senza usarlo come fonte
5. massimo due claim secondari già selezionati e verificati

Non entrano l'intero repository, post del blog, risultati grezzi di ricerca web
o pagine recuperate al momento. Questo riduce costo, prompt injection e fonti
non tracciate.

Modalità:

- `create`: lead e parti mancanti da zero
- `refresh`: conserva il più possibile la prosa revisionata e cambia solo le
  frasi dipendenti dai fatti mutati
- `repair`: una sola seconda chiamata, con errori delle guardie e stesso
  dossier. Se fallisce ancora, `needs_human`

## Verifica di numeri e fonti

### Gate 0: input

Bloccante prima della chiamata:

- indicatore e livello esistono in `indicator_universe.projection()`
- il livello è quello predefinito
- definizione ufficiale coperta
- fonte primaria con etichetta e URL risolti dal progetto
- almeno un anno e una osservazione valida
- dossier coerente con id, unità, anno massimo e copertura del view model
- claim secondari pertinenti secondo tema, `indicators` e `chiavi`

### Gate 1: struttura

Bloccante dopo la chiamata:

- JSON conforme allo schema
- lead presente quando richiesto
- ruoli noti, non duplicati, ordine e `roles_covered` validi
- ogni sezione libera ha un titolo
- livello e vintage uguali al dossier
- testo renderizzabile e rileggibile tramite `indicator_store`

### Gate 2: numeri

Ogni frase con cifra, quantità scritta in parole, graduatoria, confronto,
superlativo o affermazione universale deve portare uno o più `fact-id`.

Il verificatore:

- confronta valori e territori con il fatto citato
- accetta solo forme numeriche già previste dal dossier
- verifica anno, unità, arrotondamento e base comune
- distingue variazione percentuale da punti percentuali
- controlla parità ed eccezioni a "tutte", "nessuna" e formule equivalenti
- rifiuta calcoli nuovi introdotti dal modello
- rifiuta un fatto regionale usato nella vista provinciale o viceversa
- rifiuta confusione tra totale, uomini e donne

Gli attuali test della prosa restano un secondo livello, non la prova primaria.
Il nuovo ledger di supporti copre anche interi e quantità espresse senza
decimali, che oggi sfuggono ad alcune regex.

### Gate 3: media regionale e dato nazionale

Il dossier usa nomi non ambigui:

- `regional_mean_simple`: media aritmetica non ponderata dei territori
- `national_aggregate`: eventuale valore nazionale pubblicato da una fonte
  ufficiale

Regole bloccanti:

- `regional_mean_simple` può diventare solo "media semplice dei valori
  regionali" o provinciale secondo il livello
- le espressioni "media nazionale", "media italiana", "media dell'Italia" e
  "dato nazionale" sono vietate se il supporto è `regional_mean_simple`
- `national_aggregate` entra solo con fonte, definizione, anno, unità e
  compatibilità espliciti
- media semplice e aggregato ponderato non possono essere accostati come
  conferma reciproca

### Gate 4: fonti

Le fonti visibili sono compilate, non generate:

- `source_id` primari devono esistere in `app/sources.py` o nel manifest della
  famiglia
- `claim_id` secondari devono esistere in `data/corpus/claims/` ed essere
  pertinenti all'indicatore
- testo e URL vengono copiati dai registri
- ogni URL secondario viene riverificato con
  `bin/py -m scripts.fetch_corpus --verify`
- fonte non raggiungibile, claim non verificato o definizione `uncovered`
  bloccano la promozione o richiedono revisione manuale documentata
- nessun URL libero e nessuna fonte citata soltanto per riempire il campo

### Gate 5: semantica e stile

Comandi già esistenti:

```bash
bin/py scripts/prose_lint.py --show <id>
bin/py -m unittest tests.integration.test_indicator_texts -v
bin/py -m unittest tests.integration.test_indicator_view -v
git diff --check
```

Prima di ogni lotto pubblicabile si eseguono anche i test di duplicazione. Prima
del merge si esegue la suite richiesta dal repository.

La rilettura umana usa una checklist avversaria:

- cercare il territorio che smentisce ogni claim universale
- confrontare definizione, popolazione, soglia, numeratore e denominatore con la
  fonte
- controllare che una correlazione non sia diventata causa
- controllare dato nazionale e media semplice come grandezze distinte
- controllare anno precedente disponibile, non anno civile presunto
- controllare famiglia, livello e dimensione di genere
- aprire fonti e link visibili
- leggere il pezzo senza cruscotto e poi con il cruscotto, cercando ripetizioni
- verificare che il testo dica qualcosa e non riempia quattro contenitori

Nessun gate LLM è prova di verità. Un eventuale modello revisore può proporre
domande all'editor, ma non può promuovere una bozza né sostituire i gate
deterministici.

## Artefatti e audit

Ogni run conserva fuori da `content/`:

- `run.json`: id, ora, commit, modello, reasoning, prompt version, token e costo
- `dossier.json`: input completo e impronte
- `response.json`: risposta originale del provider
- `draft.md`: forma compilata
- `verification.json`: esito di ogni gate e supporti per frase
- `diff.patch`: modifica proposta

Gli artefatti sono immutabili e possono essere rimossi secondo una retention
decisa dal progetto. Non partecipano a `editorial_state`, non vengono letti dal
sito e non autorizzano la pubblicazione.

## Piano di rollout, con stop verificabili

### Step 0: contratto e golden set

Costruire un set di 24 schede già revisionate, distribuite tra quattro famiglie
e casi difficili: percentuale, assoluto, rapporto, unità per abitante,
contestuale, un solo anno, parità, dati mancanti, genere, livello provinciale,
serie lunga, definizione con soglia.

Acceptance:

- lista e motivazione dei 24 casi versionate
- output atteso dei fatti deterministici congelato
- rubriche binarie per errori di numero, fonte, livello, causalità e media
- nessun modello scelto prima di aver eseguito la baseline

Stop: se il golden set non copre ogni famiglia e forma critica, non si scrive il
produttore.

### Step 1: dossier e coda, senza LLM

Implementare selettore, dossier, impronte e report read-only.

Acceptance:

- insieme e ordine della coda coincidono con `editorial_state.build_queue()` e
  `da_scrivere()` dopo il filtro sul livello predefinito
- nessun file in `content/` cambia
- ogni fatto del golden set coincide col view model
- ogni fonte e definizione porta provenienza risolvibile
- seconda esecuzione sugli stessi input produce lo stesso dossier e hash

Stop: una sola divergenza numerica o una seconda definizione di stato blocca lo
step successivo.

### Step 2: shadow mode su 24 schede

Generare bozze e report, senza promotore abilitato. Confrontare reasoning `low`
e `medium` sullo stesso dossier.

Acceptance:

- zero fonti o URL non presenti nel dossier
- zero numeri, livelli o dimensioni errati dopo le guardie
- zero usi di media nazionale per la media semplice
- ogni `needs_human` conserva il motivo
- due editor valutano alla cieca utilità, chiarezza e ripetitività
- modello e sforzo scelti su risultato, costo e latenza misurati

Stop: qualunque errore fattuale non intercettato dalle guardie richiede una
nuova guardia e la ripetizione completa dello shadow set.

### Step 3: pilota pubblicabile da 10 schede

Scegliere dieci schede ad alta priorità dalla coda, massimo tre per famiglia,
una modifica per file e revisione umana completa.

Acceptance:

- tutte le guardie verdi
- dieci approvazioni umane esplicite
- suite indicatori, lint e duplicazione verdi
- nessuna regressione delle soglie di somiglianza
- tempi, token, costo, numero di repair e motivi di rifiuto registrati

Stop: nessun merge in blocco. Ogni scheda deve poter essere esclusa senza
fermare o trascinare le altre.

### Step 4: lotti da 25, poi 50

Due lotti da 25. Solo dopo, lotti massimi da 50. Le schede complete non vengono
rigenerate.

Acceptance per lotto:

- zero errori bloccanti pubblicati
- 100 per cento di revisione umana
- tasso di repair, rifiuto e `needs_human` entro soglie fissate dal pilota
- costo e tempo per scheda non peggiorano oltre il 25 per cento senza causa
- test completi del repository verdi prima del merge

Stop: un errore di fonte, cifra, livello o media sospende il lotto successivo e
riapre il gate che avrebbe dovuto intercettarlo.

### Step 5: aggiornamenti reali

Eseguire un refresh dati controllato e verificare tre casi:

1. anno nuovo
2. revisione nello stesso anno
3. definizione cambiata senza numero nuovo

Acceptance:

- entrano in coda soltanto le schede impattate
- una bozza costruita prima del refresh non può essere promossa
- `editorial_state` e cruscotto mostrano gli stessi arretrati
- dopo promozione, test e riavvio, le schede corrette escono dalla coda

### Step 6: esercizio ordinario

Avvio manuale dopo un refresh approvato. Nessun cron di pubblicazione. Report
mensile con backlog letto da `editorial_state`, costo, tempo, rifiuti, errori
intercettati e schede pubblicate.

Una futura automazione può preparare dossier e shadow draft. Il merge resta
umano finché una decisione successiva non ridefinisce responsabilità e rischio.

## Rischi e mitigazioni

| Rischio | Effetto | Mitigazione |
| --- | --- | --- |
| Allucinazione di fonte | attribuzione falsa, danno reputazionale | allowlist di `source_id` e `claim_id`, URL compilati, nessun web nel writer |
| Numero corretto con significato sbagliato | definizione falsa ma aritmetica verde | definizione ufficiale nel dossier, fingerprint, gate lessicale esistente e revisione umana |
| Media regionale chiamata nazionale | confronto statisticamente falso | campi distinti, lessico bloccante, test dedicato |
| Confusione regione, provincia, genere o totale | prosa applicata alla popolazione sbagliata | livello predefinito dalla coda, tag dimensionali nel dossier, supporto per frase |
| Causalità inventata | spiegazione non sostenuta dai dati | cause ammesse solo con claim del corpus pertinente, revisione umana |
| Prosa seriale e duplicata | perdita di qualità e rischio SEO | golden set per forme diverse, esempio singolo per forma, test di duplicazione, lotti piccoli |
| Revisione dati nello stesso anno | testo vecchio non rilevato dal `vintage` | `data_fingerprint` dentro `editorial_state`, non nella pipeline |
| Definizione cambiata | testo semanticamente obsoleto | `definition_fingerprint`, refresh definizioni insieme ai dati |
| Modello o alias cambia comportamento | regressione silenziosa | modello registrato, canary obbligatorio, golden set, rollback configurazione |
| Prompt injection da fonte esterna | istruzioni estranee nel contesto | niente pagine web grezze, corpus strutturato trattato come dati non istruzioni |
| Dati cambiano tra bozza e merge | bozza coerente con snapshot vecchio | controllo di `facts_hash` nel promotore |
| Stato duplicato | cruscotto e produttore divergono | solo `editorial_state.build_queue()` e `da_scrivere()`, log senza stato operativo |
| Costi umani sottostimati | backlog che cresce malgrado API economica | misurare minuti reali nel pilota, limitare lotti, priorità della coda esistente |

## Costi stimati

### Chiamate LLM

Assunzioni prudenti per una scheda:

- una chiamata di scrittura
- 8.000 token input tra prompt, dossier, entry corrente ed esempio
- 1.200 token output fatturati, compresi eventuali token di reasoning
- una sola chiamata `repair` al massimo, prevista sul 25 per cento delle bozze

Al prezzo pubblicato per `gpt-5.6-terra` al 28 settembre 2026, 2 dollari per un
milione di token input e 12 dollari per un milione di token output, una prima
bozza costa circa:

```text
(8.000 / 1.000.000 * $2) + (1.200 / 1.000.000 * $12) = $0,0304
```

Scenario massimo teorico su tutti i 634 indicatori:

- 634 chiamate iniziali: circa 19,27 dollari
- 25 per cento di repair con dimensione simile: circa 4,82 dollari
- totale token: circa 24,09 dollari

Budget operativo consigliato: 25-40 dollari per un passaggio completo, per
assorbire output più lunghi, retry di rete e variazioni di contesto. Non include
ricerca web, che il writer non usa, né storage. Il costo reale normale sarà
inferiore perché la coda contiene soltanto schede mancanti o arretrate.

Prezzi e disponibilità cambiano. Ogni run deve registrare listino assunto,
token effettivi e costo restituito dal provider. Il budget è un limite, non una
ragione per saltare verifiche.

### Tempo macchina

Stima da validare nello shadow mode:

- dossier e gate deterministici: secondi per scheda, parallelizzabili
- generazione: 20-60 secondi per chiamata
- 634 schede con concorrenza 5: circa 45 minuti-2 ore di sola generazione,
  oltre retry e test

La concorrenza deve essere limitata per non saturare API e memoria del processo.
Lo stato viene calcolato una volta per run, sfruttando la passata unica di
`indicator_universe`.

### Tempo umano

Stima iniziale:

- setup tecnico, dossier, gate, artefatti e promotore: 8-12 giornate di sviluppo
- golden set e shadow review: 3-5 giornate editoriali
- revisione ordinaria: 8-15 minuti per scheda dopo che i gate sono verdi
- revisione teorica di 634 schede: circa 85-159 ore

API non è costo dominante. Revisione umana lo è. Pilota deve misurare mediana,
percentile 90 e motivi di rifiuto. Se mediana supera 15 minuti, si riduce
perimetro o si migliora dossier prima di aumentare volume.

## Osservabilità e criteri di esercizio

Metriche per run e lotto:

- schede selezionate, saltate, `needs_human`, promosse e rifiutate
- motivi restituiti da `editorial_state`
- errori per gate
- claim primari e secondari usati
- token input, output, cached, costo e latenza
- numero di repair
- minuti di revisione e modifiche umane per scheda
- variazione delle metriche di duplicazione
- errori trovati dopo merge, obiettivo zero per fonte, numero, livello e media

La pipeline si considera utile solo se riduce il tempo per una scheda senza
aumentare errori o uniformità. Volume prodotto non è una metrica di qualità.

## Rollback

Ogni promozione modifica un file per indicatore. Il rollback è il revert di quel
file, seguito da test e deploy. Gli artefatti della run restano disponibili per
capire perché le guardie non hanno fermato il difetto. Un rollback non modifica
manualmente la coda: `editorial_state` ricalcola lo stato dal contenuto tornato
su disco.

## Pattern esterni usati

Questa proposta adatta pattern reali, senza copiarne l'architettura:

- Associated Press ha costruito le storie automatizzate sugli utili a partire
  da dati strutturati, con forma editoriale definita insieme ai giornalisti,
  etichetta di trasparenza e controllo di ogni output nella fase iniziale:
  [A leap forward in quarterly earnings stories](https://www.ap.org/the-definitive-source/announcements/a-leap-forward-in-quarterly-earnings-stories/)
- nel resoconto del rollout AP attribuisce la qualità alla verifica di ogni
  passaggio e a test rigorosi, e segnala che un dato errato in ingresso resta il
  principale punto di rottura:
  [Automated earnings stories multiply](https://www.ap.org/the-definitive-source/announcements/automated-earnings-stories-multiply/)
- gli standard AP 2026 mantengono giudizio, verifica e responsabilità in capo
  ai giornalisti e richiedono revisione umana dell'output generato:
  [AP updates newsroom standards for artificial intelligence](https://www.ap.org/the-definitive-source/announcements/ap-updates-newsroom-standards-for-artificial-intelligence/)
- BBC News Labs descrive la structured journalism come scenari narrativi
  scomposti in elementi riusabili, riempiti con dati, con persone nel circuito
  per i casi limite:
  [Automated news at the BBC, WHP 398](https://downloads.bbc.co.uk/rd/pubs/whp/whp-pdf-files/WHP398.pdf)
- documentazione OpenAI corrente descrive `gpt-5.6-terra` come modello che
  bilancia qualità e costo e raccomanda test su task rappresentativi per lo
  sforzo di reasoning:
  [Model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6)
  e [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)

La lezione comune è adatta al progetto: input strutturato, scenari previsti,
controlli prima della scala, trasparenza e responsabilità umana. La presenza di
un LLM non cambia il criterio di pubblicazione.
