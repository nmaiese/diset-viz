# Pipeline di discovery multifonte

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
                (fase 1: watchlist)                         (gate umano, in PR)
 fonti istituzionali  ─►  scripts/discover_candidates.py  ─►  data/discovery/candidates.csv
   (allowlist)              │  classifica vs catalogo             │  triage_status:
                            │  (new/compatible/proxy)             │   new → approved / rejected
                            │  punteggio priorità                 ▼
                            ▼                            scripts/promote_candidates.py
                (fase 2: scouting, raro, opt-in)          (solo candidati approved)
   nuovi domini  ─►  proposta di allowlist  ─►ok umano─►  watchlist          │
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
2. **Scouting (raro, opt-in).** Cerca fonti istituzionali non ancora conosciute e
   le **propone** per l'allowlist. Un dominio nuovo entra in watchlist solo dopo
   approvazione umana. Non è ancora implementato: è il gancio per la crescita
   controllata del bacino di fonti.

## Il gate: niente va live senza PR

Il cacciatore scrive **solo** in `data/discovery/candidates.csv` (versionato).
`promote_candidates.py` agisce **solo** sui candidati con `triage_status=approved`
e scrive nel layer esterno con `status=proposed`. La pubblicazione avviene al
**merge** della pull request, non prima. Questo rispetta le regole già scritte in
`DATA_PIPELINE.md`: `exact` è l'unico caso che può sostituire una serie, e niente
entra nello scoring senza direzione revisionata, copertura e fonte citabile. Il
cacciatore, per prudenza, **non dichiara mai `exact`** da solo: al massimo
`compatible`/`proxy`, e la conferma la dà un umano nella PR.

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
| `triage_status` | `new` → `approved`/`rejected`/`needs-info` → `promoted` |

## Cosa succede in promozione, per tipo di match

- **`compatible` / `proxy` con `duplicate_of`**: arricchisce l'indicatore esistente
  (`target_indicator_id = duplicate_of`), aggiunge freschezza e provenienza
  multifonte. `score_eligible=false` sempre (la valutazione resta manuale).
- **`new`**: diventa una **voce d'atlante autonoma** con id nel namespace
  `eur:<dataset>` e `atlas_eligible=true`. Resta fuori dai profili regionali
  (`profile_eligible=false`) e dallo scoring (`score_eligible=false`) finché la
  direzione non è revisionata a mano.

## Fase 2 (implementata): indicatori nuovi come voci di catalogo di prima classe

`app/external_data.py` **arricchisce** indicatori già presenti (freschezza, fonti,
badge). Per pubblicare un indicatore Eurostat **nuovo** come voce autonoma c'è
`app/eurostat_atlas.py`: legge dal layer esterno le righe con
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

## Fase 4: lo scrittore, il testo editoriale

Dopo che il curatore ha integrato e orientato un indicatore, manca il testo che
l'utente legge. Lo **scrittore** (`.claude/agents/indicator-writer.md`, agente
Claude Code invocabile via subagent) scrive l'intero articolo della pagina
(`lead` piu le quattro sezioni `definizione`/`quadro`/`dinamica`/`limiti`, con
`fonti` e `vintage`) in `app/static/data/indicator_texts.json`, seguendo
`content/STYLE.md`, con **solo numeri reali** presi dal brief
(`scripts/indicator_brief.py`), le fonti verificate per le affermazioni
comparative e il `vintage` uguale all'`year_max` corrente (drift guard). Apre una
PR, niente merge. È lo step che trasforma un indicatore appena integrato in una
pagina che si legge come scritta da un giornalista.

La catena completa degli agenti:

    cacciatore -> [approvazione umana] -> curatore -> scrittore -> PR -> merge -> live

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

## Runtime: agente Claude Code schedulato

La discovery gira come **agente Claude Code schedulato** (Routine). Le due Routine
sono attive: cacciatore lunedì `0 6 * * 1` UTC, curatore giovedì `0 6 * * 4` UTC,
environment `divarioitalia`, sessione nuova a ogni firing. Id e gestione in
[`DISCOVERY_STATUS.md`](DISCOVERY_STATUS.md). Contratto dell'agente a ogni firing:

1. `python3 scripts/discover_candidates.py --source eurostat_regional` (live,
   cache-first) per ogni fonte watchlist abilitata.
2. Leggere `data/discovery/candidates.csv`, esaminare i candidati `new` ordinati
   per `priority_score`, e proporre una decisione di triage con motivazione
   (freschezza, copertura, novità, licenza, rischio duplicato).
3. Aprire una **pull request** con la coda aggiornata (e, per i candidati che
   l'agente ritiene solidi, `triage_status` proposto). Nessun merge automatico.
4. Su approvazione umana della PR, eseguire `promote_candidates.py` per generare
   il diff del layer esterno (seconda PR o stessa PR), sempre sotto gate.

Il **curatore** è un secondo agente (o passo umano) che gira dopo la promozione:

1. `python3 scripts/curate.py` per leggere l'evidenza sul verso di ogni
   indicatore esterno non ancora curato.
2. Per ciascuno: confermare o correggere il verso, scegliere la categoria,
   rivedere la descrizione e decidere `score_eligible`, scrivendo la riga in
   `data/discovery/curation.csv`.
3. `python3 scripts/apply_curation.py` per pubblicare le decisioni nel layer
   esterno, poi aprire la PR. Al merge l'indicatore entra nel punteggio.

Lo **scrittore** è un terzo agente (o passo umano) che gira dopo la curation:

1. `python3 scripts/pending_notes.py` per leggere la coda: gli indicatori
   integrati senza nota (`missing`) e le note col vintage indietro (`stale`).
2. Per ciascuno: leggere il brief
   (`.venv/bin/python -m scripts.indicator_brief <codice>`), scrivere l'articolo
   completo seguendo `.claude/agents/indicator-writer.md` e `content/STYLE.md`,
   con solo numeri reali e le fonti verificate per le affermazioni comparative.
3. Aggiornare `app/static/data/indicator_texts.json` (solo la chiave di quell'id),
   lanciare `.venv/bin/python -m unittest tests.test_indicator_texts` e aprire la
   PR. Nessun merge automatico.

Note operative:

- Gli script sono **stdlib puri**: girano senza il venv dell'app.
- **Rate limit**: una richiesta per dataset, cache-first. Rispettare i limiti
  Istat SDMX (5/min) quando si aggiungeranno fonti Istat alla watchlist.
- **Scadenza della cache**: la cache serve a non rifare la stessa richiesta
  dentro una run, non a congelare la fonte. Le risposte dati scadono dopo
  `CACHE_MAX_AGE` (Eurostat, `scripts/eurostat_source.py`) e `DATA_MAX_AGE`
  (Istat, `scripts/istat_sdmx.py`), sei giorni, appena sotto la cadenza
  settimanale. Le **strutture** SDMX (dataflow, DSD, codelist) restano invece
  in cache senza scadenza, perché cambiano di rado e rifarle consuma solo
  budget di richieste. In locale le mtime dei file di cache sono reali, quindi
  la scadenza a sei giorni funziona da sola: un refresh eseguito a mano riscarica
  i dati e riusa le strutture senza flag aggiuntivi. Se un domani questa
  pipeline girasse dentro un runner che ripristina una cache di lungo periodo,
  quella cache andrebbe invalidata a ogni run (le mtime ripristinate non sono
  affidabili), o passando `--refresh`/`--refresh-data`, o ruotando la chiave di
  cache: senza, il job rileggerebbe per sempre la prima risposta salvata.
- **Network policy**: l'accesso web dipende dalla policy dell'ambiente. In una
  sessione senza rete, usare `--offline` sui fixture committati.
- Le colonne del layer esterno in `promote_candidates.py` (`EXTERNAL_COLUMNS`,
  `MANIFEST_COLUMNS`) sono una **copia** di quelle in `app/external_data.py`:
  tenerle allineate se cambia lo schema.

## Test

`tests/test_discovery.py` (stdlib, offline): schema e policy di priorità, dedup
conservativa, combinazione pesata Bolzano+Trento, anno recente per copertura, e il round
trip cacciatore → coda → (approvazione) → promozione su file temporanei, così i
dati di produzione non vengono mai toccati.

## Prossime fasi

- Estendere la watchlist ad altre fonti Eurostat e istituzionali, poi al livello
  provinciale (NUTS3), sempre con priorità al regionale fresco.
- Implementare lo scouting opt-in per proporre nuovi domini all'allowlist.
- Far entrare gli indicatori esterni anche nei profili regionali
  (`app/profiles.py`), oggi calcolati sui soli territoriali core.
- Dare al cacciatore un adapter per fonte: oggi l'unico implementato è
  `eurostat_regional`, quindi la Routine scansiona una sola delle fonti
  dell'allowlist.
