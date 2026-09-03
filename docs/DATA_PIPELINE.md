# Pipeline dati e procedura di ricontrollo

Questo documento spiega come è fatto lo strato dati e, soprattutto, **cosa va
ricontrollato e riaggiornato ogni volta che si inseriscono nuovi indicatori o
dataset**. Le categorie, i punteggi delle tematiche, i profili regionali e le
macro-aree sono tutti derivati dai dati: se aggiungi righe senza fare i controlli
qui sotto, il sito continua a funzionare ma rischi tematiche non valutate,
indicatori mal orientati o macro-aree incomplete.

## Da dove arrivano i dati

- Backbone territoriale: `app/static/data/Assoluti_Regione.csv` (delimitatore `;`,
  12 colonne, 20 regioni). Generato da `scripts/update_data.py`, che scarica
  l'archivio Istat, normalizza i nomi regione e scrive il CSV.
- La colonna `Tema` conserva il **sottotema della fonte** verbatim. La tassonomia
  pubblica in `app/taxonomy.py` armonizza i 36 sottotemi territoriali e BES in
  12 categorie canoniche e 4 aree di navigazione. Un sottotema nuovo resta
  tracciabile, ma deve essere mappato prima di essere pubblicato.
- Il **catalogo territoriale** (`app/data.py:get_catalog`) aggrega il CSV legacy
  per indicatore e tema, calcola completezza, anni, sparkline e `macro_area`.
- I **profili regionali e le tematiche valutabili** (`app/profiles.py`) sono
  calcolati **a runtime** e messi in cache (`@cache.memoize(timeout=3600)`).
  Non c'è nessun artefatto precalcolato su disco: il "ricalcolo" avviene da solo
  alla scadenza della cache o al riavvio del processo.
- Le **fonti verticali 2025** non entrano in questo CSV. Sono normalizzate in
  `app/static/data/external/normalized_external_indicators.csv`, con manifest in
  `app/static/data/external_indicator_manifest.csv`. Il loader è
  `app/external_data.py`.
- La qualità della vita regionale usa un terzo strato separato:
  `Assoluti_BES_Regione.csv`, generato dall'appendice regionale del BES nazionale
  con `scripts/update_bes_regions.py`. Il punteggio regionale ammette solo
  indicatori con ultimo anno almeno 2025, copertura almeno 80%, categoria e
  direzione revisionate. Le province continuano a usare BES dei Territori.
- Una **quarta famiglia** copre l'Indagine Multiscopo Istat (Aspetti della vita
  quotidiana, ICT nelle famiglie, condizioni abitative, reddito e disagio
  economico, spesa delle famiglie), tutta a livello regionale (NUTS2, 21 unità
  con Bolzano+Trento mediati in una sola regione, come per il BES nazionale).
  Fonte SDMX Istat (`scripts/istat_sdmx.py`, stesso client rate-limited della
  pipeline provinciale), selezione e curatela in `scripts/multiscopo_sources.py`,
  fetch/normalizzazione in `scripts/update_multiscopo_regions.py` (scrive
  `Assoluti_Multiscopo_Regione.csv` e `multiscopo_regione_manifest.csv`), loader
  in `app/multiscopo_data.py`. Namespace id `multiscopo:*`. Ogni indicatore è
  una singola serie SDMX ben definita (nessuna euristica sui codici Istat, solo
  scelte curate a mano). Il manifest separa `proposed_direction`, utile a leggere
  la serie, da `scoreable`, che autorizza esplicitamente l'uso nell'indice. Anche
  una serie direzionale resta descrittiva se duplica il BES, scompone una stessa
  domanda o non aggiunge una dimensione autonoma. Nel punteggio servono inoltre
  ultimo anno almeno 2023 e copertura almeno 80%.
- Il **catalogo pubblico federato** (`app/atlas_catalog.py:get_atlas_catalog`)
  presenta insieme il catalogo territoriale, gli indicatori BES regionali e
  quelli Multiscopo, tranne i BES in `app/taxonomy.py:DUPLICATE_BES_IDS`. Gli id
  BES hanno namespace `bes:*`, quelli Multiscopo `multiscopo:*`. L'adattatore
  alimenta le stesse mappe, classifiche e serie storiche della SPA, ma non
  modifica il CSV legacy e non modifica i profili regionali descrittivi
  calcolati da `app/profiles.py`. Quando aggiungi un indicatore BES, controlla
  se esiste già una serie territoriale con lo stesso nome e con gli stessi
  valori (stesso fenomeno Istat ingerito due volte): se sì, aggiungi il suo id
  BES a `DUPLICATE_BES_IDS` così non compare due volte nel catalogo/ricerca/quiz.
  `app/quiz.py` legge la stessa lista. Il motore di
  punteggio (`app/quality_life_selection.py`) ha una deduplica separata, che
  preferisce BES: non toccarla.
- La **selezione qualità della vita** (`app/quality_life_selection.py`) opera
  sul catalogo federato. Include BES regionali almeno al 2025 e indicatori
  territoriali core almeno al 2023, tutti con direzione revisionata e copertura
  sufficiente. Gli indicatori territoriali restano esclusi dal punteggio
  provinciale. Per Multiscopo richiede anche `scoreable=1`. I duplicati esatti
  per nome vengono contati una sola volta.

## Come funziona la valutazione delle tematiche

1. Solo gli indicatori **core** entrano nel punteggio: completi su tutte e 20 le
   regioni (`completeness >= 0.98`) e recenti (`year_max >= CORE_MIN_YEAR`, oggi
   2023). Vedi `profiles.is_core`.
2. Ogni indicatore core viene normalizzato in **percentile** dentro se stesso
   (stesso anno, tutte le regioni) e **orientato** in base alla direzione
   (`higher_better` / `lower_better` / `higher_worse`). Gli indicatori
   `contextual` non hanno un verso migliore/peggiore: restano visibili in modo
   descrittivo ma **non entrano nel punteggio**.
3. Il punteggio di un tema per una regione è la media degli indicatori
   direzionali di quel tema, ma solo se sono almeno `MIN_THEME_INDICATORS` (3).
   Sotto questa soglia il tema compare come "non valutabile".

La direzione di ogni indicatore viene da `app/indicator_notes.py`:
prima il dizionario curato `CURATED_DIRECTION` (per id), poi un'euristica a
parole chiave (`_direction`). **L'euristica spesso ritorna `contextual`**: i nuovi
indicatori vanno quindi quasi sempre aggiunti a mano a `CURATED_DIRECTION`.

## Tassonomia pubblica (overlay non distruttivo)

I temi del backbone territoriale e i 12 domini BES sono raggruppati nelle stesse
12 categorie canoniche in `app/taxonomy.py:CANONICAL_CATEGORIES`. Le categorie
sono raccolte in 4 aree tramite `MACRO_AREAS`. È un overlay: non modifica le
etichette Istat, che restano disponibili come `source_theme`, e viene usato da
Atlante, pagine SEO, profili regionali, qualità della vita e minigiochi.

Se un sottotema non è mappato, `category_metadata` ritorna la categoria
`"Altro"`: è un campanello d'allarme da correggere aggiungendo il sottotema a una
sola categoria canonica. Le vecchie URL dei sottotemi fanno redirect alla pagina
della categoria, così i link già indicizzati non si perdono.

## Checklist quando aggiungi indicatori o dataset

1. **Schema** invariato: 12 colonne nell'ordine atteso (lo verifica
   `test_dataset_schema`). Non aggiungere/rimuovere colonne.
2. **Direzione** di ogni nuovo id: aggiungi una voce in `CURATED_DIRECTION`
   (`higher_better` / `lower_better` / `higher_worse` / lascia `contextual` se non
   c'è un verso onesto). Senza questo, l'indicatore quasi sempre resta
   `contextual` e non viene valutato.
3. **Categoria** di ogni nuovo sottotema: mappalo in
   `CANONICAL_CATEGORIES[...]["themes"]`. Controlla che nessun tema finisca in
   `"Altro"` e che non compaia in due categorie.
4. **Ricalcolo**: è runtime + cache 1h. Per vederlo subito **riavvia gunicorn**
   (o aspetta la scadenza). I test girano senza cache, quindi sono sempre freschi.
5. **Frontend**: `cd frontend && npm run build && cd ..` (il catalogo cambia, la
   SPA va ricostruita).
6. **Test**: `.venv/bin/python -m unittest discover -s tests -v` (tutti verdi).
7. **Verifica tematiche**: controlla quali temi sono ora valutabili (>= 3
   indicatori core + direzionali) e quali restano descrittivi. Usa la diagnostica
   qui sotto.

## Scoperta di nuovi indicatori (a monte)

Il passo che *trova* nuovi indicatori presso fonti istituzionali e li mette in
una coda revisionabile prima di qualsiasi integrazione è descritto in
[`docs/archive/DISCOVERY_PIPELINE.md`](archive/DISCOVERY_PIPELINE.md) (archiviato:
gli script restano, la catena di agenti che vi girava attorno no). In breve: il cacciatore
(`scripts/discover_candidates.py`) scrive candidati in
`data/discovery/candidates.csv`, un umano li approva in PR, e
`scripts/promote_candidates.py` li porta nel layer esterno con `status=proposed`.
Niente va live senza merge. La fonte pilota è Eurostat regionale (NUTS2).

## Fonti verticali e freschezza

Per fonti 2025 diverse dal backbone Istat regionale usa il layer esterno, non il
CSV legacy:

```bash
.venv/bin/python scripts/discover_external_sources.py
.venv/bin/python scripts/fetch_external_data.py --source istat_lavoro --year 2025 --offline
.venv/bin/python scripts/build_external_dataset.py --source all --year 2025
.venv/bin/python scripts/audit_external_indicators.py
```

Per aggiornare insieme i due backbone regionali e i fingerprint delle fonti:

```bash
.venv/bin/python scripts/refresh_official_data.py --check-only
.venv/bin/python scripts/refresh_official_data.py
```

Il refresh completo si esegue a mano, come gli altri passi della pipeline, con
`scripts/refresh_official_local.sh` (`--check` per il solo controllo). Replica i
passi storici del workflow: controllo hash, aggiornamento dei backbone e del
Multiscopo regionale, e se qualcosa cambia rigenera il layer esterno e l'audit,
poi test e build. Il diff resta da revisionare a mano: nessun commit e nessuna
pull request automatici quando cambiano definizioni, copertura o punteggi.

Regole:

- `definition_match=exact` è l'unico caso in cui una serie può sostituirne una
  esistente.
- `compatible` richiede revisione manuale.
- `proxy` non sostituisce mai il dato BES o atlas.
- `different` resta descrittivo.
- Nessun nuovo dato entra nello scoring se non è relativo/standardizzato,
  completo almeno al 95%, con direzione revisionata e fonte ufficiale citabile.

Le API e le pagine leggono `freshness_status` da `app/external_data.py`:
`current` per anni dal 2025, `recent` dal 2023, `dated` dal 2020, `stale` prima
del 2020. I badge sono solo informativi e non modificano score o ordinamenti.

## Diagnostica: temi valutabili vs descrittivi

Comando read-only per rigenerare la tabella "tema -> indicatori totali / core /
direzionali / valutabile":

```bash
.venv/bin/python - <<'PY'
from collections import defaultdict
from app.data import get_catalog
from app.profiles import is_core, SCOREABLE_DIRECTIONS, MIN_THEME_INDICATORS
tot, core, score = defaultdict(int), defaultdict(int), defaultdict(int)
for it in get_catalog()["indicators"]:
    th = it["theme"]; tot[th] += 1
    if is_core(it):
        core[th] += 1
        if (it.get("explain") or {}).get("direction") in SCOREABLE_DIRECTIONS:
            score[th] += 1
for th in sorted(tot, key=lambda t: -score[t]):
    rated = "valutabile" if score[th] >= MIN_THEME_INDICATORS else "descrittivo"
    print(f"{th:42} tot={tot[th]:>3} core={core[th]:>3} dir={score[th]:>3}  {rated}")
PY
```

Esempio di lettura: un tema con `dir=0` (come "Demografia e popolazione", i cui
indicatori 920-923 sono tutti `contextual` per scelta) resta descrittivo; un tema
con `dir>=3` viene classificato e compare nei punti di forza/debolezza regionali.

## Cosa NON cambiare

- Le 20 regioni (`REGION_ORDER`) e la mappatura nomi in `scripts/update_data.py`.
- Lo schema CSV (12 colonne, ordine).
- `/legacy` e `/legacy-reddito`.
- Gli attributi `data-key` della mappa SVG, che devono combaciare con gli slug
  regione (lo verifica `test_regions_map_data_matches_geometry`).
