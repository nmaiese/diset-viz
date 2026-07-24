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
| `duplicate_of` | id dell'indicatore esistente più simile, se c'è |
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
unificata `/indicatore/eur-<dataset>/<slug>`. Le righe *enriching* (Eurostat che
duplica un indicatore Istat) NON diventano voci separate: restano agganciate all'id
Istat che puntano.

## Fonte pilota: Eurostat regionale (NUTS2)

Prima istituzione oltre Istat, per validare il flusso end-to-end.

- Adattatore: `scripts/eurostat_source.py` (stdlib puro, cache-first, API JSON-stat).
- Selezione curata `EUROSTAT_SERIES`: PIL pro capite (`nama_10r_2gdp`) e spesa
  R&S sul PIL (`rd_e_gerdreg`). Un dataflow = un indicatore, nessuna euristica sui
  codici.
- Mappa `NUTS2_TO_REGION`: 21 NUTS2 italiane sulle 20 regioni, con Bolzano+Trento
  mediati in Trentino Alto Adige (come nel BES nazionale). `ITZZ` (Extra-Regio)
  scartato.
- "Anno recente onesto": si sceglie l'anno più recente che supera la soglia di
  copertura (`MIN_COVERAGE=0.8`), non l'ultimo assoluto (spesso sparso).

Esempio reale di coda prodotta: R&S sul PIL classificato `new` (0.88), PIL pro
capite `proxy` dell'id 901 dei conti economici territoriali (0.78), entrambi
copertura 20/20.

## Runtime: agente Claude Code schedulato

La discovery gira come **agente Claude Code schedulato** (Routine). Contratto
dell'agente a ogni firing:

1. `python3 scripts/discover_candidates.py --source eurostat_regional` (live,
   cache-first) per ogni fonte watchlist abilitata.
2. Leggere `data/discovery/candidates.csv`, esaminare i candidati `new` ordinati
   per `priority_score`, e proporre una decisione di triage con motivazione
   (freschezza, copertura, novità, licenza, rischio duplicato).
3. Aprire una **pull request** con la coda aggiornata (e, per i candidati che
   l'agente ritiene solidi, `triage_status` proposto). Nessun merge automatico.
4. Su approvazione umana della PR, eseguire `promote_candidates.py` per generare
   il diff del layer esterno (seconda PR o stessa PR), sempre sotto gate.

Note operative:

- Gli script sono **stdlib puri**: girano senza il venv dell'app.
- **Rate limit**: una richiesta per dataset, cache-first. Rispettare i limiti
  Istat SDMX (5/min) quando si aggiungeranno fonti Istat alla watchlist.
- **Network policy**: l'accesso web dipende dalla policy dell'ambiente. In una
  sessione senza rete, usare `--offline` sui fixture committati.
- Le colonne del layer esterno in `promote_candidates.py` (`EXTERNAL_COLUMNS`,
  `MANIFEST_COLUMNS`) sono una **copia** di quelle in `app/external_data.py`:
  tenerle allineate se cambia lo schema.

## Test

`tests/test_discovery.py` (stdlib, offline): schema e policy di priorità, dedup
conservativa, collasso Bolzano+Trento, anno recente per copertura, e il round
trip cacciatore → coda → (approvazione) → promozione su file temporanei, così i
dati di produzione non vengono mai toccati.

## Prossime fasi

- Estendere la watchlist ad altre fonti Eurostat e istituzionali, poi al livello
  provinciale (NUTS3), sempre con priorità al regionale fresco.
- Implementare lo scouting opt-in per proporre nuovi domini all'allowlist.
- Collegare la coda alla selezione qualità della vita
  (`app/quality_life_selection.py`) per i candidati regionali `score_eligible`
  dopo revisione manuale della direzione.
