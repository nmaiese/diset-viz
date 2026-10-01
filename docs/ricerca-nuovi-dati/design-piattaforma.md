# Indicatori ufficiali non-BES: disegno minimo

## Verdetto

Usare lo strato esterno già normalizzato per entrambi i livelli. Lasciare intatti i
loader BES. Aggiungere `app/provincial_families.py` come adapter unico delle sole
righe esterne provinciali; il regionale continua in `app/external_atlas.py`.
Flusso alimenta scheda, `/province`, `/atlante`, `/confronto`,
`/provincia/<key>` e `/regione/<key>` senza duplicare loader per istituzione.

Identità logica: `(family, raw_id)`. Se definizione regionale e provinciale è
identica, stesso id e stessa scheda: base regionale più `/province`. Se definizione,
unità o popolazione differiscono, id distinti: mai unione per nome. Esempio:
`family=mef`, `raw_id=reddito-irpef-medio`, id catalogo
`mef:reddito-irpef-medio`, codice URL `mef-reddito-irpef-medio`, pagina
`/indicatore/<slug>/mef-reddito-irpef-medio` e vista
`/indicatore/<slug>/mef-reddito-irpef-medio/province`
(`app/sources.py:235-274`, `app/sources.py:280-296`).

Motivo: `app/external_data.py:22-46` possiede già contratto normalizzato,
provenienza, ammissibilità e scoring. `app/external_atlas.py:84-95` lo limita alle
regioni. Forzare MEF/ISPRA/MIM/Salute/ACI/Unioncamere dentro `bes_data` legherebbe
schema, etichetta Istat e regole BES (`app/bes_data.py:29-44`,
`app/bes_data.py:282-327`): rischio alto e attribuzione falsa.

## Contratto dati concreto

### Osservazioni

Estendere senza cambiare colonne
`app/static/data/external/normalized_external_indicators.csv`, delimitatore `;`:

```text
source;source_dataset;source_indicator_id;target_indicator_id;name;territory_level;territory_code;territory_name;year;value;unit;theme;quality_life_category;direction;definition_match;atlas_eligible;profile_eligible;score_eligible;coverage;retrieved_at;source_url;license;notes
```

Vincoli nuovi:

- `target_indicator_id` è sempre id interno completo, per esempio
  `mef:reddito-irpef-medio`; prefisso registrato, mai famiglia generica.
- `territory_level` è `regione` o `provincia`.
- `territory_code` è chiave canonica del sito. Per provincia deve appartenere a
  `province_codes.csv`; `territory_name` deve coincidere col registro. Codice
  originario resta in `source_indicator_id`, non sostituisce la chiave territoriale.
- `direction` ammette `higher_better`, `lower_better` o `contextual`.
- `score_eligible=true` non basta: categoria canonica, direzione scoreable,
  copertura e freschezza devono passare i gate. `profile_eligible` governa pagine
  territorio; `atlas_eligible` scheda/atlante.
- Metadati ripetuti sulle righe devono essere identici per
  `(target_indicator_id, territory_level)`. Loader fallisce su divergenza, id
  duplicato tra famiglie, territorio ignoto, anno/valore illeggibile.

### Manifesto di pubblicazione

Aggiungere
`app/static/data/external/external_indicator_levels.csv`, delimitatore `;`, una
riga per `(target_indicator_id, territory_level)`:

```text
target_indicator_id;territory_level;name;theme;quality_life_category;direction;scoreable;sample_survey;year_min;year_max;territory_count_latest;coverage_latest;source_dataset;source_indicator_id;source_url;license;definition_match;reviewed_at;notes
```

Questo è proprietario delle decisioni umane `direction`, `scoreable`,
`sample_survey` e mappatura tema. CSV osservazioni conserva campi esistenti per
compatibilità; loader valida che coincidano col manifesto. `scoreable` è per
livello: stesso fenomeno può essere scoreable nelle regioni e solo contestuale
nelle province. Non riusare `external_indicator_manifest.csv`: oggi è audit di
ammissione con stati anche non pubblicati e colonne diverse
(`app/external_data.py:48-63`, `app/external_data.py:101-149`).

### Loader unico provinciale

Nuovo `app/provincial_families.py`, circa 180-230 righe:

```text
has_data()
all_indicators()                         # catalogo provinciale cross-family
indicator_page(family, raw_id)           # meta + livelli, anche province-only
series(family, raw_id)                    # righe year/value/region/region_key
indicators_for_province(province_key)     # valore, rango, trend, fonte
scoreables()                              # solo gate espliciti superati
cache_clear()
```

Legge `external_data.get_external_rows()`, filtra `territory_level=provincia`,
indicizza una volta per processo. Riusa il registro territori BES solo come
anagrafica canonica, non come provenienza. Espone righe nella stessa forma del
payload regionale; evita scansioni quadratiche già documentate per BES in
`app/indicator_view.py:461-491` e `app/province_profile.py:265-289`.

Regole pubbliche per livello: `year_max >= 2023`, copertura `>= 0,80`, almeno tre
territori con valore; completezza UI separata (`107` e `>= 0,98`). Costanti
centralizzate accanto al loader/`seo_policy`, non riscritte nei consumer. Il
numero 107 è consistenza del dataset corrente, non numero amministrativo da
aggiornare per ogni nuova serie.

### Registro fonti

Ogni istituzione è famiglia propria in `app/sources.py:SOURCES` (`37-85`), per
esempio:

```python
"mef": {
    "acronym": "mef",
    "institution": "Ministero dell'Economia e delle Finanze",
    "label": "Ministero dell'Economia e delle Finanze, dichiarazioni fiscali",
    "short_label": "Dichiarazioni fiscali",
    "internal_prefix": "mef:",
    "license": "<testo ufficiale verificato>",
    "license_url": "<URL ufficiale verificato>",
    "feeds": ("mef_irpef",),
}
```

Stesso schema per `ispra`, `mim`, `salute`, `aci`, `unioncamere`. Acronimi unici;
prefisso non vuoto; feed dell'adapter associato. Mai copiare CC BY 4.0 Istat:
registro vieta già default di licenza (`app/sources.py:30-36`). Finché testo e URL
ufficiali non sono verificati, famiglia non pubblicabile. Tutti label, institution,
licenza e JSON-LD devono derivare dal registro (`app/sources.py:137-155`,
`app/sources.py:163-227`).

Tema deve risolversi in `taxonomy.CANONICAL_CATEGORIES`; nessuna categoria nuova
nel primo pilot. Categoria ignota: errore di ammissione, non voce “Altro”.

## Superfici da integrare

Stime: righe applicative modificate/aggiunte, esclusi fixture CSV e test.

| Superficie | Modifica minima | Stima | Rischio | Test esistenti |
|---|---|---:|---|---|
| Loader e fonte | Nuovo `provincial_families.py`; registro famiglia in `sources.SOURCES`; validazione prefisso, tema, territorio, metadati | 210-280 | Medio: chiavi provincia e licenza | `tests/integration/test_external_atlas.py:75-159`; `tests/integration/test_url_migration.py:16-49`; `tests/unit/test_source_admission.py:36-123` |
| Scheda e `/province` | `indicator_view.build_indicator_view` deve cercare fallback province-only esterno e allegare livello provinciale a ogni famiglia registrata, non solo BES (`108-135`). Generalizzare `provincial_series`/`_provincial_level` (`486-505`) e `level_passes_rule` (`383-398`) | 70-110 | Alto: canonical/noindex per livello | `tests/integration/test_indicator_view.py:52-276`; `test_indicator_view_pages.py:30-275`; `test_url_migration.py:93-244`; `test_doppioni.py:67-244` |
| Universo/API | Aggiungere refs provinciali unici in `indicator_universe.all_indicator_refs` (`29-43`); togliere vincolo `family != bes` e dispatch BES-only da `province_payload` (`177-215`) | 25-45 | Alto: doppia ref regionale+provinciale | `test_indicator_view_pages.py:211-275`; `test_confronto_province.py:269-329`; `test_search_territori.py:57-79` |
| Atlante | Rendere `design/pages/atlante.province_items`, `_province_row`, `province_path` family-neutral (`108-163`, `190-212`). Il regionale entra già da `atlas_catalog.get_atlas_catalog` (`297-418`) via external | 45-70 | Medio: tema/completezza/path | `tests/integration/test_atlante.py:364-606`; `test_external_atlas.py:17-159` |
| Confronto | Nessun nuovo adapter: `confronto.province_pages` e `payload_for` sono già sull'universo (`80-104`). Correggere solo assunzioni BES nei test/fixture | 0-15 | Basso dopo universo | `tests/integration/test_confronto.py:49-386`; `test_confronto_province.py:55-379` |
| Pagina provincia | `province_profile.indicatori` oggi costruisce solo manifesto/serie BES (`303-418`): concatenare `provincial_families.indicators_for_province`, stessi campi e fonte per riga. Aggiornare descrizione Istat-only in `views.py:1942-2000`; fonti UI in `design/pages/provincia.py:333-390` | 45-75 | Alto: rango, spark, fonte e cache | `tests/integration/test_province_body.py:49-270`; `test_province_pages.py`; `test_province_seo.py`; `tests/unit/test_og_territori.py` |
| Pagina regione | `profiles._region_indicators` legge solo backbone (`505-546`): aggiungere righe external con `profile_eligible=true`, senza cambiare `_core_stats`/temi score. Estendere `_region_series` oltre `data.get_rows` (`design/pages/regione.py:240-290`) o passare spark precomputata | 65-100 | Alto: classifiche e memoria | `tests/unit/test_theme_standings.py`; `tests/integration/test_v1_pages.py:479-613`; `test_hub_pages.py` |
| Temi | `province_indicators_by_theme` itera solo BES (`indicator_view.py:914-951`): iterare pagine provinciali dell'universo. Catalogo regionale già alimenta temi (`atlas_catalog.py:361-382`) | 15-30 | Medio: tema non mappato sparisce o genera errore tardivo | `tests/integration/test_doppioni.py:278-337`; `test_atlante.py:95-104,405-450` |
| Ricerca | Ricerca regionale già usa atlas; provinciale già `level_pages` (`views.py:864-906`). Nessun ramo nuova famiglia dopo universo | 0-10 | Basso: collisioni nome/path | `tests/integration/test_search_territori.py:33-84`; `test_doppioni.py:326-341` |
| Sitemap/canonical/noindex/JSON-LD | Rotta e render sono family-neutral (`views.py:1434-1475`, `1543-1660`); sitemap usa `level_pages` (`3484-3537`). Serve meta fonte/licenza corretto e gate per livello | 0-15 | Alto ma coperto end-to-end | `test_indicator_view_pages.py:211-275`; `test_url_migration.py:187-244`; `test_link_interni.py`; `test_transparency.py`; `test_seo_titles.py` |
| Gioco | `game_daily._indicator_rows` è BES-only (`296-323`): dispatch per famiglia. `provincial_id` (`282-283`) diventa `sources.split_internal_id`. `game_families` elimina unione hardcoded `{"bes"}` (`471-502`). `game_facts.direction` e `is_sample_survey` leggono manifesto/CSV, non assumono tutte le province BES (`190-218`) | 45-70 | Alto: fatti/ranghi falsi | `tests/integration/test_game_compare_daily.py:121-548`; `test_game_facts_payload.py:73-468`; `test_game_pages.py:32-120` |
| Quiz regionale | `quiz.py` gestisce già tutti `sources.EXTERNAL_FAMILIES` (`56-62`, `137-150`). Rinominare `_eurostat_*` è pulizia, non requisito. Etichette BES/Multiscopo hardcoded (`91`, `127`) restano debito fuori pilot | 0 | Basso | `tests/integration/test_external_atlas.py:126-138`; `test_game_pages.py:86-111` |
| Qualità vita | Regionale: selezione già deduplica, ma motore deve iterare tutte famiglie esterne. Provinciale: aggiungere scoreables esterni dopo BES, dedup per nome normalizzato, gate esplicito | 45-80 | Molto alto: peso doppio/attribuzione | `tests/integration/test_quality_life.py:121-195,222-309`; `test_doppioni.py:342-378`; `test_url_migration.py:24-35` |

## Qualità della vita: correzione obbligatoria

Selezione regionale è già ordinata BES, territoriale, Multiscopo, external e
deduplica per nome normalizzato (`app/quality_life_selection.py:38-104`). Ma
`quality_life_bes._matrix_and_meta` carica external solo se id inizia col prefisso
Eurostat (`app/quality_life_bes.py:253-257`) e scrive sempre
`source_family="eurostat"` (`274-286`). Quindi MEF può risultare selezionato ma
non entrare nel punteggio; se entrasse con patch parziale, apparirebbe sotto fonte
Eurostat. Silent failure certo.

Correzione: iterare gli id selezionati per cui
`sources.split_internal_id(id)[0] in sources.EXTERNAL_FAMILIES`; scrivere famiglia
risolta dal registro. Test parametrico con almeno Eurostat e MEF.

Per provincia, BES oggi ammette ogni serie con direzione e copertura; non esiste
flag curatoriale provinciale equivalente. Nuovo ordine:

1. serie BES correnti;
2. `provincial_families.scoreables()` con `scoreable=true`, categoria valida,
   direzione valida, `year_max >= 2023`, copertura `>= 0,80`;
3. deduplica prima dell'inserimento su nome normalizzato, mantenendo BES in caso
   di identico fenomeno;
4. id diversi con nome simile ma definizione diversa restano entrambi solo dopo
   review `definition_match`; niente dedup fuzzy automatico.

Profilo e pagina territorio possono mostrare indicatori `scoreable=false`; non
devono entrare in punteggi, temi forti/deboli o conteggio score.

## Rotture silenziose da impedire

- `indicator_view.py:118-133`, `383-398`, `486-505`, `914-951` e
  `indicator_universe.py:193-195`: quattro cancelli BES-only. Aggiungere solo CSV
  produce nessuna `/province`, nessun confronto, nessun tema provinciale.
- `external_atlas.py:92`: ignora deliberatamente `territory_level != regione`.
  Senza nuovo adapter dati provinciali esistono ma sono invisibili.
- `external_atlas.py:217,251`: denominatore/completo regionali hardcoded 20.
  Non riusare quel builder per province.
- `design/pages/atlante.py:117-118,140-163,190-212`: path, id, famiglia e catalogo
  provinciali BES-only.
- `province_profile.py:303-418` e `profiles.py:505-546`: pagine territorio non
  derivano dall'atlante federato. Scheda funzionante non implica profilo.
- `game_daily.py:309-323,497-499` e `game_facts.py:194-218`: dati, famiglie,
  direzione e natura campionaria provinciali assunti BES.
- `quality_life_bes.py:255,285`: prefisso e attribuzione Eurostat hardcoded.
- `taxonomy.category_metadata` deve risolvere il tema. Tema libero nel CSV può
  finire senza macro-area o fallire soltanto in atlante provinciale
  (`design/pages/atlante.py:209-211`). Gate all'ingest.
- Cache: aggiungere `provincial_families.cache_clear()` a fixture/reset insieme a
  `indicator_universe.cache_clear` e `tests/conftest.py:27-36`; altrimenti test
  dipendono dall'ordine.
- `Dockerfile:22` copia tutto `app/`, quindi entrambi i CSV sotto
  `app/static/data/external/` arrivano a runtime senza nuova `COPY`. Se manifesto
  viene messo sotto `config/`, non arriva: Docker copia soltanto
  `config/game_indicators.csv` (`Dockerfile:54-60`). Architettura proposta evita
  modifica Dockerfile; test immagine deve comunque verificare file presenti.
- `config/game_indicators.csv` è già copiato. Nuova riga deve usare id completo
  `mef:...`, `livello_provincia=1`, flag regione coerente e `campionario=0|1`.
- `publisher.dataset_updated(meta["family"])` in `views.py:1642` richiede stato
  fonte per nuova famiglia; altrimenti data aggiornamento può mancare pur con
  pagina valida.
- Collisions: `sources.FAMILY_BY_ACRONYM`/regex sono derivati dal registro
  (`149-155`); acronimo duplicato sovrascrive silenziosamente. Validazione unicità.
- URL raw id ammette trattini (`sources.py:151-155`); non fare split manuale sul
  primo/ultimo trattino.

## Conteggi hardcoded

Misura live, con interprete progetto: `all_indicator_refs=634`,
`atlas_catalog=597`, `level_pages=388` (371 basi, 17 `/province`), BES=178
(34 a due livelli, 33 solo provincia). Stato misurato sul worktree corrente;
non sono obiettivi del nuovo catalogo.

Da rendere dinamici o aggiornare nello stesso commit che aggiunge dati:

- `CLAUDE.md:40`: “634 indicatori”.
- `app/indicator_universe.py:3-6,48,99`: contratto/commenti 634 e differenza dal
  catalogo.
- `app/editorial_state.py:180`, `app/indicator_view.py:833`, `app/views.py:3432`,
  `app/templates/_indicator_article.html:114`: commenti/assunzioni operative 634.
- `tests/integration/test_v1_pages.py:4,153-166,245`: assertion esatta 634. Meglio
  confrontare percorsi con `indicator_universe.projection()`, non fissare totale.
- `STATUS.md:36` descrive stato corrente: aggiornare solo come nuova fotografia,
  non riscrivere righe storiche `STATUS.md:78-98`.

Non cambiare automaticamente:

- 107 = territori nel dataset/profilo (`app/bes_data.py:132`, test provincia):
  resta valido finché anagrafica corrente resta 107.
- 67 = indicatori del solo CSV BES provinciale
  (`docs/PROVINCE_PIPELINE.md:79`, `app/province_profile.py:241-243`): resta vero
  se frase resta esplicitamente BES.
- 393 = backbone territoriale (`docs/FAMIGLIE_INDICATORI.md:57`): altra famiglia.
- Numeri in bozze storiche e fixture numeriche non sono conteggi catalogo.

## Piano committabile e ownership

Ogni passo chiude test propri. File posseduti non si sovrappongono tra worker
simultanei; dove sovrapposizione è inevitabile, passi sono seriali.

1. **Contratto e fixture pilot.** Owner: `app/static/data/external/*.csv`, nuovo
   test loader. Aggiungere manifesto livelli e poche righe MEF finte/fixture, non
   produzione. Validare schema, territorio, metadati, tema, direzione. Nessuna
   pagina cambia.
2. **Registro fonte.** Owner: `app/sources.py`, test registro/URL. Inserire una
   sola famiglia pilot con licenza verificata. Test round-trip id con trattini e
   unicità acronimo/prefisso/feed. Dipende da 1 solo per nome id.
3. **Loader provinciale.** Owner: nuovo `app/provincial_families.py`, suo unit
   test, `tests/conftest.py` per reset cache. Nessun consumer. Verificare catalogo,
   serie, provincia, ranking, scoreables.
4. **Scheda/universo/SEO.** Owner esclusivo:
   `app/indicator_view.py`, `app/indicator_universe.py`, relativi test. Collegare
   loader, fallback province-only, scheda a due livelli, API. Gate: 200,
   canonical, noindex, sitemap e JSON-LD concordi. Serializzare dopo 3.
5. **Atlante/confronto/temi/ricerca.** Owner:
   `app/design/pages/atlante.py`, `app/design/pages/confronto.py` solo se serve,
   ramo temi di `indicator_view.py`, test atlante/confronto/ricerca. Poiché tocca
   `indicator_view.py`, integrare sul commit 4, non in parallelo con esso.
6. **Profili territorio.** Owner: `app/province_profile.py`, `app/profiles.py`,
   `app/design/pages/{provincia,regione}.py`, porzione profili in `views.py`.
   Mostrare fonte per riga; non cambiare punteggi. Test su una provincia e una
   regione, più cache/memoria.
7. **Qualità vita.** Owner esclusivo:
   `app/quality_life_selection.py`, `app/quality_life_bes.py`, test quality.
   Prima correggere external non-Eurostat regionale; poi aggiungere scoreable
   provinciale e dedup. Commit separati se possibile.
8. **Giochi.** Owner: `config/game_indicators.csv`, `app/game_daily.py`,
   `app/game_facts.py`, test game. `app/quiz.py` invariato salvo test pilot
   regionale. Verificare JSON-LD fonte/licenza e fatti provinciali non
   campionari/campionari.
9. **Dati reali, deploy contract e conteggi.** Owner: CSV produzione,
   `data/source_state.json` se contratto publisher lo richiede, `Dockerfile` solo
   test/nessun cambio atteso, documenti e assertion conteggio. Eseguire suite
   mirata, build container e audit link/sitemap. Questo passo soltanto pubblica
   dati reali.

Primo vertical slice consigliato: un indicatore MEF presente in entrambe le
scale, `scoreable=false`, fuori giochi. Dimostra fonte, scheda, `/province`,
atlante, confronto, profili e SEO senza alterare classifiche. Commit successivo
abilita scoring; altro commit abilita gioco. Riduce blast radius.

## Verifiche non fatte

Non ho verificato URL, licenze, formati, frequenza, copertura o equivalenza
semantica delle fonti MEF/ISPRA/MIM/Salute/ACI/Unioncamere: richiedono dataset e
termini ufficiali scelti. Nessuna etichetta/licenza d'esempio sopra è pronta per
produzione. Non ho costruito immagine Docker né eseguito suite: incarico era
analisi read-only del codice. Ho eseguito soltanto import/misure read-only col
Python del progetto. Numeri possono cambiare se altri commit o CSV entrano prima
dell'implementazione; test devono derivarli dai registri.
