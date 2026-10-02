# Passaggio ai passi 6-8 (piattaforma indicatori non BES)

Non committato. Disegno di riferimento:
`.orca/worktrees/divarioitalia/nuovi-dati/docs/ricerca-nuovi-dati/design-piattaforma.md`
(il path `nd-architettura/lavoro/DESIGN.md` citato dalla spec non esiste piu').

Commit sul ramo `nmaiese/nd-piattaforma`: passo 1 `b8f12d90`, passo 2
`ce22209f`, passo 3 `d1e170ee` (Codex), passo 4 `3dccfe64`, passo 5 `32bf5652`. I CSV di produzione
(`app/static/data/external/external_indicator_levels.csv`) hanno solo l'header:
nessuna famiglia nuova e' visibile in produzione finche' il passo 9 non mette
dati reali. Fixture: `tests/fixtures/external_mef.py` (`rows()`, `levels()`,
20 regioni + 107 province, `scoreable=false`, `direction=contextual`).

## API del loader: `app/provincial_families.py`

Tutte in cache per processo (`lru_cache`); `cache_clear()` le svuota, e
`tests/conftest.py` la chiama all'avvio.

- `has_data() -> bool`
- `all_indicators() -> list[dict]`: una voce per serie esterna con livello
  provinciale. Ogni voce: `{"metadata": {...}, "levels": {"regione"?: info,
  "provincia": info}, "series": [righe provinciali]}`.
  - `metadata`: `id` (`mef:...`), `raw_id`, `family`, `name`, `theme`,
    `source_theme`, `quality_life_category`, `quality_life_category_label`,
    `macro_area`, `theme_path`, `unit`, `direction`, `scoreable` (bool, del
    livello provinciale), `sample_survey` (bool), `source`, `source_label`,
    `source_url`, `license`, `license_url`, `institution`, `path` (canonico
    della scheda), `base_level` (`"regione"` se il regionale ha valori, sennò
    `"provincia"`), `indexable` (regola del livello base), `explain`,
    `year_min`, `year_max`.
  - `levels[k]`: `key`, `label`, `year_min`, `year_max`, `coverage_latest`,
    `territory_count_latest` (dal manifesto), `count_latest` (contato),
    `indexable` (`year_max >= MIN_PUBLIC_YEAR` 2023, copertura `>= 0.8`,
    almeno 3 territori), `observations` (solo provincia).
- `indicator_page(family, raw_id) -> dict | None`: la voce sopra.
- `series(family, raw_id, level="provincia") -> list[dict]`: copie delle righe
  `{id, family, raw_id, year, value, region, region_key, territory,
  territory_key, unit}` (stessa forma del payload regionale).
- `indicators_for_province(province_key) -> list[dict]`: per una provincia,
  `{id, name, theme, unit, direction, value, year, year_from, rank,
  province_count, movement, source, source_url, path}`; `path` porta gia' alla
  vista provinciale (`/province` se la scheda si apre sulle regioni). Ordinate
  per rango. **Rango**: `contextual` e `higher_better` ordinano decrescente.
- `scoreables() -> list[dict]`: solo voci con `scoreable=true`, verso in
  `profiles.SCOREABLE_DIRECTIONS`, livello provinciale indicizzabile, copertura
  e anno sopra soglia. Oggi con la fixture: `[]`.
- Costanti: `MIN_PUBLIC_YEAR`, `MIN_PUBLIC_COVERAGE`, `MIN_SCOREABLE_TERRITORIES`,
  `PROVINCE_LEVEL`, `REGION_LEVEL`.

## Gia' family-neutral dopo i passi 4-5

- `indicator_view.build_indicator_view(family, raw_id)`: scheda a due livelli o
  solo provinciale per ogni famiglia esterna.
- `indicator_view.provincial_series(raw_id, family="bes")`: righe provinciali
  di qualunque famiglia (attenzione all'ordine: `raw_id` prima).
- `indicator_view.level_passes_rule(meta, level_key, base_key)` e
  `level_indexable(...)`: per le esterne legge `levels[k]["indexable"]`.
- `indicator_view.indexability(family, raw_id, source_meta)`: per le esterne
  con pagina provinciale usa la regola del livello base (motivo `vecchia` o
  `copertura` se fuori).
- `indicator_view.province_indicators_by_theme()`: BES + esterne.
- `indicator_universe.all_indicator_refs()`, `projection()`,
  `province_payload(indicator_id)`: comprendono le esterne provinciali.
- `app/design/pages/atlante.py`: `province_items()` ritorna voci
  `{"family", "id", "levels"}` per BES ed esterne; `_province_level_path(record)`
  da' il link alle province per ogni famiglia.
- Confronto e ricerca: nessuna modifica, leggono l'universo.
- Licenza in scheda: `meta.license` / `meta.license_url` dal registro
  (`sources.family_license`); riga omessa se la famiglia non dichiara URL.

## Passo 6, profili territorio

- `app/province_profile.py:indicatori` (oggi solo BES, ~righe 303-418):
  concatenare `provincial_families.indicators_for_province(key)`; i campi sono
  gia' allineati (fonte per riga in `source`/`source_url`). Non entrano in
  punteggi, forti/deboli o conteggi score.
- `app/profiles.py:_region_indicators` (~505-546): le righe regionali esterne
  vengono da `external_atlas`; filtrare su `profile_eligible=true` del CSV.
  Spark: `design/pages/regione.py:_region_series` legge solo `data.get_rows`.
- `views.py` (~1942-2000) descrizione provincia "Istat-only" e
  `design/pages/provincia.py` (~333-390) fonti UI: usare
  `sources.institutions_label(families)`.
- Frase "67 indicatori" resta vera solo se resta esplicitamente BES.

## Passo 7, qualita' della vita

- `quality_life_bes._matrix_and_meta` (~253-257, 274-286): prefisso Eurostat e
  `source_family="eurostat"` hardcoded. Iterare id con
  `sources.split_internal_id(id)[0] in sources.EXTERNAL_FAMILIES` e scrivere la
  famiglia risolta.
- Provinciale: dopo le BES aggiungere `provincial_families.scoreables()`,
  dedup per nome normalizzato tenendo BES.

## Passo 8, giochi

- `game_daily._indicator_rows` (~296-323): per le esterne
  `indicator_view.provincial_series(raw_id, family)` o
  `provincial_families.series(family, raw_id)`.
- `game_daily.provincial_id` (~282): `sources.split_internal_id`.
- `game_families` (~471-502): togliere `{"bes"}` hardcoded.
- `game_facts` (~190-218): verso e natura campionaria da
  `indicator_page(...)["metadata"]["direction"|"sample_survey"]`.
- `config/game_indicators.csv`: id completo `mef:...`.

## Rischi noti lasciati

- `tests/integration/test_game_order_daily.py::test_a_livello_province_la_fonte_viene_da_sources`
  fallisce anche su master dal 2/10/2026: la sfida del giorno cade su
  `bes-10AMB024P`, solo provinciale, e il test vuole sempre `/province`. Da
  sistemare nel passo 8 (giochi) o a parte.
- La riga "Licenza" della scheda ora mostra `meta.license` dal registro su tutte
  le schede (es. "CC BY 4.0 (Istat)" invece del vecchio `data_license_label`).
- MIM e Salute hanno nel registro una licenza "da verificare": comparirebbe
  visibile. Il passo 9 non pubblica dati di queste famiglie prima della verifica.
- Il test della slice (`tests/integration/test_external_platform.py`) svuota
  tutte le cache `app.*` tranne i loader CSV: chi aggiunge cache nuove nei
  passi 6-8 e' coperto se usa `lru_cache` o `synchronized_cache`.

- `publisher.dataset_updated(meta["family"])` (`views.py`) vuole stato fonte per
  la nuova famiglia: senza, la data di aggiornamento puo' mancare (passo 9).
- `provincial_families` usa `bes_data.get_bes_territories("provincia")` come
  anagrafica delle 107 province.
- Fallimenti preesistenti nel venv condiviso: `tests/unit/test_trend_articles_cli.py`
  e `test_foto_autore` (manca `requests`), non legati a questo lavoro.
