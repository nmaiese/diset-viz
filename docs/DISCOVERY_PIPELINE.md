# Pipeline di discovery multifonte

> **Come gira tutto insieme, senza intervento umano, sta in
> [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).** Questo documento descrive
> il **meccanismo** della scoperta: gli adapter, lo schema della coda, il
> punteggio di priorità, cosa succede in promozione. Quello descrive **chi lo
> muove**: i sette stadi, gli agenti, il cancello, la politica di merge e il
> rientro sul pubblicato. Se cerchi "chi decide e quando", vai lì.

Questo documento descrive lo strato di **scoperta e messa in coda** degli
indicatori, cioè il pezzo che rende Divario Italia un aggregatore multifonte con
priorità ai dati freschi e regionali (poi provinciali). È il livello che sta
**davanti** alla pipeline dati già esistente
([`DATA_PIPELINE.md`](DATA_PIPELINE.md), [`PROVINCE_PIPELINE.md`](PROVINCE_PIPELINE.md)),
non la sostituisce.

## Perché

L'atlante integra già quattro famiglie di dati (backbone territoriale, esterni
verticali, BES regionale, Multiscopo) più le province SDMX, con un catalogo
federato e regole di gate. Mancava il passo iniziale: un processo ricorrente che
**cerca** nuovi indicatori validi presso fonti istituzionali, li **normalizza in
candidati** e li mette in una **coda revisionabile**, prima di qualsiasi
integrazione. La discovery riempie quella coda. La promozione, sotto gate PR, la
svuota nel layer esterno esistente.

## Flusso

```
                (fase 1: watchlist)                       (triage dell'agente, sotto cancello)
 fonti istituzionali  ─►  scripts/discover_candidates.py  ─►  data/discovery/candidates.csv
   (allowlist)              │  classifica vs catalogo             │  triage_status:
                            │  (new/compatible/proxy)             │   new → approved / rejected
                            │  punteggio priorità                 ▼
                            ▼                            scripts/promote_candidates.py
                (fase 2: scouting, raro, opt-in)          (solo candidati approved)
   nuovi domini  ─►  proposta di allowlist  ─►ok umano─►  config/istat_series.yaml │
                                                                             ▼
                                            app/static/data/external/normalized_external_indicators.csv
                                            app/static/data/external_indicator_manifest.csv (status=proposed)
                                                                             │  merge PR
                                                                             ▼  → live
```

Principio di priorità (codificato in `discovery.priority_score`): a parità di
tutto, vince il dato più **fresco**, **regionale**, con **copertura** alta e più
**additivo** (un indicatore nuovo pesa più di un duplicato). Provinciale e datato
non vengono scartati: scendono solo in fondo alla coda.

## Le due fasi della scoperta

1. **Watchlist (default operativo).** Sorveglia solo le fonti già in
   `config/external_sources.yaml` (allowlist istituzionale) e rileva nuove uscite
   e nuovi indicatori dentro quelle fonti. Alta qualità, poco rumore. È ciò che
   gira a ogni run schedulata.
2. **Scouting.** Cerca fonti istituzionali non ancora conosciute e le
   **propone**. Un dominio nuovo entra in watchlist solo dopo approvazione umana,
   ed è l'unico punto della catena in cui questo è ancora vero: la fonte decide
   quale istituzione e quale licenza legge un utente in pagina. Implementato per
   Istat da `scripts/scout_sources.py`, che legge il catalogo dataflow SDMX e
   scrive i dataflow regionali non ancora coperti in
   `data/discovery/source_candidates.csv` (vedi "Fase 2b" sotto). L'agente che lo
   guida è `source-scout`, e per un dataflow approvato **cabla la fonte scrivendo
   una riga in `config/istat_series.yaml`**, senza toccare codice.

## Il gate: niente va live senza passare dal cancello

Ogni stadio scrive **solo** dentro il proprio perimetro (il cacciatore in
`data/discovery/candidates.csv`, e basta) e chiude con
`scripts/pipeline_gate.py`, che calcola il verdetto dal diff e dalla suite e
decide se e come la PR si fonde. La politica non è uniforme: la prosa si fonde da
sola, la promozione e la curatela passano dai check remoti perché muovono numeri
vivi, **ammettere una fonte resta una firma umana**. Regole complete e motivazioni
in [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md) e
[`AGENT_CONTRACT.md`](AGENT_CONTRACT.md).

Restano vere le regole già scritte in `DATA_PIPELINE.md`: `exact` è l'unico caso
che può sostituire una serie, e niente entra nello scoring senza direzione
revisionata, copertura e fonte citabile. Il cacciatore **non dichiara mai
`exact`** da solo, e il cancello lo rifiuta se ci prova. Un'approvazione sotto la
copertura minima o senza licenza dichiarata viene rifiutata allo stesso modo:
sono le cose che rendono una serie inutilizzabile, e vanno respinte senza dover
leggere il ragionamento di chi l'ha approvata.

## Schema della coda

Colonne in `scripts/discovery.py:CANDIDATE_COLUMNS`. I campi chiave:

| campo | significato |
| --- | --- |
| `candidate_id` | chiave stabile `<source>:<source_indicator_id>` |
| `discovery_mode` | `watchlist` o `scouting` |
| `territory_level` | `regione` (priorità) o `provincia` |
| `year_max` / `coverage` | anno recente con copertura sufficiente, e copertura sulle 20 regioni |
| `definition_match` | `new` / `compatible` / `proxy` / `different` (mai `exact` in automatico) |
| `duplicate_of` | id dell'indicatore esistente più simile, se c'è, **qualificato per famiglia** (`bes:<id>`, `multiscopo:<id>`, o id numerico per i territoriali) |
| `freshness_status` | `current` ≥2025, `recent` ≥2023, `dated` ≥2020, `stale` prima |
| `priority_score` | 0..1, fresco + regionale + copertura + novità |
| `triage_status` | `new` → `approved`/`rejected`/`needs-info` → `promoted` (scritto da `promote_candidates.py`, non a mano) |

## Cosa succede in promozione, per tipo di match

- **`compatible` / `proxy` con `duplicate_of`**: arricchisce l'indicatore esistente
  (`target_indicator_id = duplicate_of`), aggiunge freschezza e provenienza
  multifonte. `score_eligible=false` sempre (la valutazione resta manuale).
- **`new`**: diventa una **voce d'atlante autonoma** con id nel namespace della
  **famiglia della sua fonte** (`eur:` per Eurostat, `dem:` per gli indicatori
  demografici Istat) e `atlas_eligible=true`. Resta fuori dai profili regionali
  (`profile_eligible=false`) e dallo scoring (`score_eligible=false`) finché la
  direzione non è revisionata a mano.

  Il namespace non è un dettaglio estetico: decide l'istituzione, l'etichetta e
  la licenza che il lettore vede in pagina. Era cablato a `eur:`, quindi con un
  secondo adapter attivo una serie Istat sarebbe uscita sotto il nome di
  Eurostat. La mappa fonte -> famiglia sta in `discovery.FEED_FAMILY`, rispecchia
  i `feeds` di `app/sources.py`, e i due mirror sono appaiati da
  `tests/test_discovery.py`.

## Fase 2 (implementata): indicatori nuovi come voci di catalogo di prima classe

`app/external_data.py` **arricchisce** indicatori già presenti (freschezza, fonti,
badge). Per pubblicare un indicatore Eurostat **nuovo** come voce autonoma c'è
`app/external_atlas.py`: legge dal layer esterno le righe con
`target_indicator_id` nel namespace `eur:` e `atlas_eligible=true` e le adatta al
**contratto API dell'atlante** identico a quello territoriale/BES, così mappa,
pagina, ricerca, categoria, direzione, URL e sitemap funzionano senza casi
speciali. È federato in `app/atlas_catalog.py` (`get_atlas_catalog`,
`get_atlas_indicator`, `source_families`) e la pagina è servita dalla route
unificata keyword-first `/indicatore/<slug>/eur-<dataset>`. Le righe *enriching* (Eurostat che
duplica un indicatore Istat) NON diventano voci separate: restano agganciate all'id
Istat che puntano.

## Fase 3 (implementata): il curatore, il lavoro qualitativo

Lo scouting propone verso e categoria dai soli nomi. Il **curatore** (agente
schedulato o umano) fa il lavoro qualitativo che manca: verifica il **verso**
contro i dati veri, rivede la descrizione, e pubblica la mappatura così
l'indicatore entra nel punteggio, nel quiz e nella qualità della vita.

Strumenti (stdlib):

- `scripts/curate.py` produce l'**evidenza sul verso**: per ogni indicatore
  esterno non ancora curato mostra le regioni in cima e in fondo nell'ultimo anno
  e il verso proposto. Se il verso è `higher_better`, in cima devono esserci le
  regioni che chiameremmo "migliori": se non è così, il verso va corretto.
  Esempio reale (R&S sul PIL): in cima Emilia-Romagna, Piemonte, Lazio; in fondo
  Calabria, Valle d'Aosta. Verso `higher_better` confermato.
- Il curatore scrive la decisione in `data/discovery/curation.csv`: verso
  revisionato, verdetto (`confermato`/`corretto`), categoria, `score_eligible`
  (solo se il verso è davvero direzionale) e una descrizione rivista opzionale.
  La decisione è identificata da **target più fonte più serie di origine**, non
  dal solo target: due fonti possono arricchire lo stesso indicatore, e
  revisionarne una non deve riscrivere verso e `score_eligible` dell'altra. Una
  riga senza fonte vale ancora per tutte le righe del target, per compatibilità
  con le decisioni scritte prima che le colonne facessero parte della chiave.
- `scripts/apply_curation.py` **pubblica** la decisione nel layer esterno e nel
  manifest (direzione, categoria, `score_eligible`, `status=integrated`) e scrive
  la descrizione rivista in `app/static/data/external/curated_descriptions.csv`,
  che l'atlante usa come override. `score_eligible=true` è rifiutato se la
  direzione non è direzionale (guardia in `apply_curation`).

Dove entra l'indicatore dopo la cura:

- **Atlante e ricerca**: già dalla fase 2 (`atlas_eligible`).
- **Quiz** (`app/quiz.py`): entra appena è `atlas_eligible` e ha abbastanza valori
  distinti; il verso non serve al quiz (confronta solo i valori).
- **Qualità della vita** (`app/quality_life_selection.py` +
  `app/quality_life_bes.py`): entra solo dopo la cura, quando `score_eligible=true`
  con verso direzionale, categoria e copertura sufficiente. Il motore orienta lo
  z-score con il verso curato, come per BES, territoriali e Multiscopo.

Tutto sotto gate PR: la modifica al punteggio è visibile nel diff e va live solo
al merge.

### Osservazioni non definitive

Gli adapter scartano le osservazioni marcate come stima, provvisorio o previsione
(`e`, `p`, `f` in `OBS_STATUS` per Istat, nella mappa `status` JSON-stat per
Eurostat). Il campo non era letto da nessuna parte, e le proiezioni Istat del
2026 sugli indicatori demografici, tutte flaggate `e`, portavano `year_max` a
2026 e `priority_score` a 1.0: il principio "vince il dato più fresco" veniva
aggirato da una cifra che Istat rivedrà. La lista è volutamente stretta, perché
`b` (rottura di serie), `d` (definizione diversa) e `u` (bassa affidabilità)
sono valori definitivi con un'avvertenza e scartarli butterebbe via dati buoni.

### Aggiungere un adapter

Tre righe, in tre posti che i test tengono allineati:

1. la famiglia in `app/sources.py` (`acronym`, `institution`, `label`, `license`,
   `internal_prefix`, `feeds`), oppure il nome della fonte nei `feeds` di una
   famiglia che esiste già,
2. `discovery.FEED_FAMILY`, il mirror stdlib della stessa mappa,
3. il parser in `promote_candidates.PROMOTION_PARSERS`.

Ne manca uno e la promozione si rifiuta con un messaggio che dice quale. Se
l'adapter porta un tema nuovo, va registrato in
`CANONICAL_CATEGORIES[...]["themes"]` (`app/taxonomy.py`): un tema sconosciuto
finisce nella macro-area "Altro" e l'indicatore sparisce dai totali per
macro-area pur restando in catalogo.

## Fase 4: lo scrittore, il testo editoriale

Dopo che il curatore ha integrato e orientato un indicatore, manca il testo che
l'utente legge. Lo **scrittore** (`.claude/agents/indicator-writer.md`, agente
Claude Code invocabile via subagent) scrive l'intero articolo della pagina
(`lead` piu le quattro sezioni `definizione`/`quadro`/`dinamica`/`limiti`, con
`fonti` e `vintage`) in `content/indicators/`, un file per articolo, seguendo
`content/STYLE.md`, con **solo numeri reali** presi dal brief
(`scripts/indicator_brief.py`), le fonti verificate per le affermazioni
comparative e il `vintage` uguale all'`year_max` corrente (drift guard). Apre una
PR, niente merge. È lo step che trasforma un indicatore appena integrato in una
pagina che si legge come scritta da un giornalista.

La catena completa degli agenti, tutti definiti in `.claude/agents/`:

    scout -> cacciatore -> promozione -> curatore -> scrittore -> revisore
                                                                      |
                                                       cancello -> merge -> live

| agente | file | coda deterministica |
| --- | --- | --- |
| scout | `source-scout.md` | `data/discovery/source_candidates.csv` |
| cacciatore | `indicator-hunter.md` | `data/discovery/candidates.csv` |
| curatore | `indicator-curator.md` | `scripts/curate.py --include-recheck` |
| scrittore | `indicator-writer.md` | `scripts/pending_notes.py`, `scripts/text_queue.py` |
| revisore | `indicator-reviewer.md` | `scripts/review_queue.py` |

Lo stato di tutti gli stadi insieme:

```bash
python3 scripts/pipeline_status.py
```

Ogni stadio ha una coda che si calcola dai file committati, non dalla memoria di
una sessione precedente. È la condizione perché un agente schedulato sappia su
che cosa lavorare partendo da zero, e perché due run non si pestino i piedi.

## Fase 5: il revisore, i testi che esistono già

Lo scrittore produce articoli, il revisore è il motivo per cui ci si può fidare.
Le guardie meccaniche coprono struttura, stile, `vintage`, le cifre decimali
attribuite a una regione e le soglie asserite su un elenco di regioni. Quello che
non possono coprire, elencato in `docs/INDICATOR_PAGES.md`, è esattamente dove si
nascondono gli errori, e `scripts/review_queue.py` lo cerca:

    universale   "ovunque", "sempre", "da anni": basta un controesempio
    causale      "grazie a", "dipende dalle": l'indicatore non mostra meccanismi
    esterno      un confronto fuori dal dataset senza fonte in `fonti`
    provincia    cifre provinciali, che la regex delle regioni non legge
    eco          una cifra che il cruscotto stampa già

Nessuno di questi è un difetto di per sé. Sono le frasi in cui un difetto si
nasconde, quindi decidono l'ordine di lettura, non un esito. Un articolo firmato
porta `reviewed_at` (`YYYY-MM-DD`, sotto guardia) ed esce dalla coda.

### Il trigger dello scrittore (worklist deterministica)

Lo scrittore aveva l'unico stadio della catena senza un innesco automatico: il
cacciatore e il curatore girano come Routine, ma nulla diceva allo scrittore
quali indicatori il curatore avesse appena integrato e lasciato senza nota. Per
questo `scripts/pending_notes.py` produce la **coda dello scrittore**, come
`curate.uncurated_targets` fa per il curatore:

- **da scrivere** (`missing`): un indicatore integrato nel manifest
  (`status=integrated`) senza articolo. È il passaggio di consegne
  curatore -> scrittore.
- **da aggiornare** (`stale`): un articolo il cui `vintage` è rimasto indietro
  rispetto all'`year_max` corrente dell'indicatore (il caso di refresh, la stessa
  deriva che controlla `tests/test_indicator_texts.py`).

`pending_notes.py` copre gli indicatori tracciati dal manifest. Per lo stato
editoriale dell'intero catalogo, incluse le sezioni ancora composte dal template,
si usa `.venv/bin/python -m scripts.text_queue`.

```bash
python3 scripts/pending_notes.py            # coda leggibile
python3 scripts/pending_notes.py --json      # coda per l'agente
```

Lo script è stdlib puro come i fratelli (cacciatore, curatore): sia la coda sia
l'`year_max` corrente arrivano da file committati (il `new_year`, o in mancanza
il `current_year`, del manifest), quindi la Routine dello scrittore non richiede
Flask. Il controllo `stale` si
restringe così agli indicatori esterni/integrati che il manifest traccia, cioè
proprio il perimetro dello scrittore come innesco della pipeline di discovery.
La logica è testata (`tests/test_pending_notes.py`) senza toccare alcun file.

## Fonte pilota: Eurostat regionale (NUTS2)

Prima istituzione oltre Istat, per validare il flusso end-to-end.

- Adattatore: `scripts/eurostat_source.py` (stdlib puro, cache-first, API JSON-stat).
- Selezione curata `EUROSTAT_SERIES`: PIL pro capite (`nama_10r_2gdp`) e spesa
  R&S sul PIL (`rd_e_gerdreg`). Un dataflow = un indicatore, nessuna euristica sui
  codici.
- Mappa `NUTS2_TO_REGION`: 21 NUTS2 italiane sulle 20 regioni. Bolzano e Trento
  vengono combinati in Trentino Alto Adige con **media pesata per popolazione**
  (`fetch_weights`, dataset `nama_10r_3popgdp`), non con media semplice: per un
  rapporto come il PIL pro capite la media non pesata sarebbe un valore sintetico
  sbagliato. `ITZZ` (Extra-Regio) scartato. Nota cross-famiglia: BES e
  territoriali non hanno questo problema perché Istat pubblica già Trentino Alto
  Adige come regione unica; Multiscopo ora usa la stessa media pesata per
  popolazione (`scripts/multiscopo_sources.py:TRENTINO_WEIGHTS`).
- "Anno recente onesto": per la coda si mostra l'anno più recente che supera la
  soglia di copertura (`MIN_COVERAGE=0.8`), non l'ultimo assoluto (spesso sparso).
- **Serie storica**: la promozione (`normalized_rows`) pubblica **tutti** gli anni
  con copertura sufficiente, non solo l'ultimo, così la scheda atlante ha il
  grafico pluriennale come le altre famiglie. Gli anni più recenti troppo sparsi
  restano esclusi; la combinazione pesata di Trentino si applica a ogni anno.

Esempio reale di coda prodotta: R&S sul PIL classificato `new` (0.88), PIL pro
capite `proxy` dell'id 901 dei conti economici territoriali (0.78), entrambi
copertura 20/20.

## Runtime: le Routine

La catena gira come **Routine Claude Code** (agenti cloud, sessione nuova a ogni
firing, checkout git proprio). Le cadenze, gli id e lo stato stanno in
[`DISCOVERY_STATUS.md`](DISCOVERY_STATUS.md); il contratto che ogni agente segue a
ogni run sta in [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md); come stanno insieme i
sette stadi sta in [`AUTONOMOUS_PIPELINE.md`](AUTONOMOUS_PIPELINE.md).

**Il prompt di una Routine non riproduce il contratto, lo indica.** È la lezione
più cara di questo sistema: la Routine dello scrittore riproduceva il proprio
contratto per intero, il repo è andato avanti, e per settimane l'agente ha
scritto in `analyst_notes.json`, un file che l'app non legge più. Girava, non
falliva, e non arrivava in nessuna pagina.

Note operative che restano vere per tutti:

- Gli script sono **stdlib puri**: girano senza il venv dell'app.
- **Rate limit**: una richiesta per dataset, cache-first. Rispettare i limiti
  Istat SDMX (5/min).
- **Scadenza della cache**: la cache serve a non rifare la stessa richiesta
  dentro una run, non a congelare la fonte. Le risposte dati scadono dopo
  `CACHE_MAX_AGE` (Eurostat, `scripts/eurostat_source.py`) e `DATA_MAX_AGE`
  (Istat, `scripts/istat_sdmx.py`), sei giorni, appena sotto la cadenza
  settimanale. Le **strutture** SDMX (dataflow, DSD, codelist) restano invece in
  cache senza scadenza, perché cambiano di rado e rifarle consuma solo budget di
  richieste. In locale le mtime dei file di cache sono reali, quindi la scadenza
  a sei giorni funziona da sola. Se un domani questa pipeline girasse dentro un
  runner che ripristina una cache di lungo periodo, quella cache andrebbe
  invalidata a ogni run (le mtime ripristinate non sono affidabili), o passando
  `--refresh`/`--refresh-data`, o ruotando la chiave di cache: senza, il job
  rileggerebbe per sempre la prima risposta salvata.
- **Network policy**: l'accesso web dipende dalla policy dell'ambiente. In una
  sessione senza rete, usare `--offline` sui fixture committati, e dichiararlo:
  una coda prodotta offline non è una scoperta nuova.
- Le colonne del layer esterno in `promote_candidates.py` (`EXTERNAL_COLUMNS`,
  `MANIFEST_COLUMNS`) sono una **copia** di quelle in `app/external_data.py`:
  tenerle allineate se cambia lo schema.

## Fase 2b (implementata): lo scout, nuove fonti nel catalogo SDMX

`scripts/scout_sources.py` è lo scouting del punto 2 sopra, per Istat. Legge il
catalogo dei dataflow SDMX (una query cache-forever, condivisa con
`discover_provinces.py`) e propone i dataflow **regionali** che **non** sono
coperti da alcuna fonte in allowlist né da un adapter curato, così emergono
domini nuovi (sanità, edilizia, giustizia, violenza di genere, capitale umano).
È **livello-catalogo**: nessuna query dati per dataflow, quindi economico rispetto
al limite Istat di 5 query/minuto. Esclude i flow e le famiglie SDMX già coperte
(tutta la famiglia Multiscopo AVQ, non solo i flow curati; le famiglie Forze di
Lavoro che i nomi terse non rivelano), i domini già in allowlist per token del
nome, le tabelle di metadati e i nomi generici. Scrive **solo** in
`data/discovery/source_candidates.csv` (coda revisionabile): ammettere un dominio
all'allowlist resta un merge umano, e cablarne l'adapter è il passo successivo.

## Prossime fasi

- Estendere la watchlist ad altre fonti Eurostat e istituzionali, poi al livello
  provinciale (NUTS3), sempre con priorità al regionale fresco.
- Far entrare gli indicatori esterni anche nei profili regionali
  (`app/profiles.py`), oggi calcolati sui soli territoriali core.
- Dare al cacciatore un adapter per fonte: oggi sono implementati
  `eurostat_regional` e `istat_demografia` (`scripts/istat_regional_source.py`,
  indicatori demografici via SDMX). Restano da cablare le altre fonti in
  allowlist, partendo da quelle che lo scout propone e che un umano approva.
