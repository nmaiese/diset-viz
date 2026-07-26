# Stato aggregatore multifonte (handoff)

Documento di passaggio: cosa è stato fatto sul branch
`claude/aggregatore-indicatori-multifonte-4en56u`, com'è messo il sistema ora, e
cosa manca. Per il dettaglio operativo vedi
[`docs/DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md); per lo strato dati
[`docs/DATA_PIPELINE.md`](DATA_PIPELINE.md).

## Obiettivo

Trasformare l'app in un **aggregatore multifonte** che dà priorità ai dati
freschi e regionali (poi provinciali): un processo ricorrente scopre indicatori
presso fonti istituzionali, li mette in coda, un curatore fa il lavoro
qualitativo (verso, descrizioni) e pubblica la mappatura così l'indicatore entra
in atlante, quiz e qualità della vita. Tutto sotto **gate PR**: niente va live
senza merge.

## Le tre fasi, tutte implementate

### Fase 1 — Scoperta (hunter)
- `scripts/discover_candidates.py` (watchlist) scansiona le fonti in
  `config/external_sources.yaml`, classifica ogni indicatore contro le serie
  esistenti (`new`/`compatible`/`proxy`, mai `exact` in automatico), assegna un
  `priority_score` (fresco + regionale + copertura + novità) e scrive in
  `data/discovery/candidates.csv`.
- Lib: `scripts/discovery.py`. Adapter pilota: `scripts/eurostat_source.py`
  (Eurostat NUTS2, cache-first, fixture offline, Bolzano+Trento combinati con
  media pesata per popolazione).
- Stdlib puro: gira senza il venv dell'app.

### Fase 2 — Promozione + Eurostat come famiglia d'atlante
- `scripts/promote_candidates.py` agisce solo sui candidati `triage_status=approved`.
  Un indicatore `new` diventa voce d'atlante autonoma con id `eur:<dataset>`;
  un `compatible`/`proxy` arricchisce l'indicatore Istat che punta.
- `app/eurostat_atlas.py` adatta le righe `eur:` del layer esterno al contratto
  API dell'atlante, federato in `app/atlas_catalog.py`
  (`get_atlas_catalog`/`get_atlas_indicator`/`source_families`).
- URL unificati **keyword-first**: `/indicatore/<slug>/<acr>-<id>`
  (`ter`/`bes`/`ims`/`eur`). Lo slug (keyword) apre l'URL per la SEO, il codice
  con l'id è l'ultimo segmento e risolve in modo stabile anche se il nome cambia.
  I vecchi URL fanno 301. Naming e URL centralizzati in `app/sources.py`
  (etichette istituzione-first, niente gergo).

### Fase 3 — Curatore (lavoro qualitativo)
- `scripts/curate.py` mostra l'evidenza sul **verso** (regioni in cima/in fondo).
- `data/discovery/curation.csv` = decisione rivista (verso, categoria,
  `score_eligible`, descrizione).
- `scripts/apply_curation.py` pubblica nel layer esterno + manifest +
  `app/static/data/external/curated_descriptions.csv`.
- Aggancio consumatori: quiz (`app/quiz.py`), selezione e motore qualità della
  vita (`app/quality_life_selection.py`, `app/quality_life_bes.py`).

## Stato attuale dei dati (pilota)

- Fonte pilota: **Eurostat regionale (NUTS2)**, registrata in
  `config/external_sources.yaml` come `eurostat_regional`.
- **`eur:rd_e_gerdreg`** (spesa R&S sul PIL): scoperto, promosso come voce
  d'atlante nuova, **curato** (verso `higher_better` confermato dai dati,
  categoria `ricerca_innovazione_digitale`, descrizione rivista) e quindi attivo
  in atlante, ricerca, quiz e **punteggio qualità della vita**.
- **PIL pro capite Eurostat** (`nama_10r_2gdp`): riconosciuto `proxy` dell'id
  territoriale 901, arricchisce quell'indicatore (freschezza EU), non è una voce
  separata.

## Comandi

```bash
# ambiente (container fresco): serve un venv per l'app; gli script discovery no
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# hunter -> coda
python3 scripts/discover_candidates.py --source eurostat_regional          # live
python3 scripts/discover_candidates.py --source eurostat_regional --offline # fixture

# promozione (solo approved)
python3 scripts/promote_candidates.py --offline

# curatore
python3 scripts/curate.py                       # evidenza sul verso
python3 scripts/apply_curation.py               # pubblica curation.csv

# test (tutta la suite: 183 verdi)
.venv/bin/python -m unittest discover -s tests -v
```

Dopo modifiche ai dati serve **riavviare gunicorn** (loader in `lru_cache` per la
vita del processo). Il frontend NON va ricostruito per i soli dati (la SPA legge
`/api/catalog` a runtime; filtri ed etichette fonti sono data-driven).

## Agenti

Tre agenti, catena: **cacciatore -> [approvazione umana] -> curatore -> scrittore**.
Il cacciatore e il curatore hanno il contratto in `docs/DISCOVERY_PIPELINE.md`;
lo **scrittore** è definito in `.claude/agents/indicator-writer.md` (scrive
l'articolo completo della pagina con numeri reali presi da
`scripts/indicator_brief.py`, stile `content/STYLE.md`, vintage e fonti).

## Schedulazione (fatta)

Cacciatore e curatore girano come **Routine Claude Code** (agenti cloud, sessione
nuova a ogni firing, checkout git proprio, PR-gated). Create il 2026-07-24
sull'environment `divarioitalia`, modello `claude-opus-4-8`:

| agente | cron (UTC) | routine id |
| --- | --- | --- |
| cacciatore (watchlist) | `0 6 * * 1` (lun) | `trig_01VizeycZocZoeDE1RxjWj1f` |
| curatore (verso, categoria) | `0 6 * * 4` (gio) | `trig_019EP6TnEbYnKz8VpKFaRm4g` |
| scrittore (note d'analista) | `0 6 * * 6` (sab) | *da registrare* |

Lo **scrittore** ha ora un innesco deterministico: `scripts/pending_notes.py`
elenca gli indicatori integrati senza nota (e le note col vintage indietro), così
la Routine sa su cosa lavorare invece di ripartire da zero. La cadenza sabato sta
due giorni dopo il curatore (giovedì), lo stesso sfasamento cacciatore->curatore,
perché lo scrittore ha senso solo dopo che una integrazione del curatore è a
monte. La Routine va registrata a mano su <https://claude.ai/code/routines> come
le altre due (contratto in [`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md),
sezione "Runtime", passi 1-3 dello scrittore); il prompt non apre una PR vuota
quando `pending_notes.py` non elenca nulla.

Le Routine si gestiscono da <https://claude.ai/code/routines> (elenco, modifica,
esecuzione manuale, disattivazione). Il prompt di ciascuna riproduce il contratto
in [`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md) (sezione "Runtime"): il
cacciatore esegue i passi 1-3 e si ferma prima della promozione, il curatore
esegue i passi 1-3 del suo contratto e lancia la suite completa perché tocca il
punteggio qualità della vita. Nessuno dei due fa merge, e nessuno dei due apre una
PR vuota quando non c'è nulla da revisionare.

Cadenza sfalsata di tre giorni per un motivo: il curatore ha senso solo dopo che
un umano ha approvato la coda del cacciatore e ha girato la promozione.

### Niente workflow GitHub per i dati: tutto in locale

Scelta operativa: la pipeline dati non gira su GitHub Actions. Il refresh dei
backbone e del Multiscopo si esegue a mano con `scripts/refresh_official_local.sh`
(`--check` per il solo controllo hash), come gli altri passi della pipeline
(promote, curate, apply). Il vecchio `data-refresh.yml` è stato rimosso.

Di conseguenza il branch `claude/discovery-schedule-action` (commit `22902fa`),
che schedulava il cacciatore come workflow GitHub, **non va unito**: contraddice
questa scelta. Il cacciatore si lancia a mano con
`python3 scripts/discover_candidates.py --source eurostat_regional`, esattamente
come nel contratto della Routine (vedi "Runtime" in
[`DISCOVERY_PIPELINE.md`](DISCOVERY_PIPELINE.md)).

## Fatto di recente

- **Secondo adapter del cacciatore**: `istat_demografia`
  (`scripts/istat_regional_source.py`), indicatori demografici via SDMX Istat
  (indice di dipendenza degli anziani e strutturale), con fixture offline. La
  watchlist non gira più su un'unica fonte.
- **Scouting delle fonti**: `scripts/scout_sources.py` propone i dataflow SDMX
  regionali non ancora coperti in `data/discovery/source_candidates.csv`
  (PR-gated, non tocca l'allowlist). Vedi "Fase 2b" in `DISCOVERY_PIPELINE.md`.

## Cosa NON è ancora fatto (prossimi passi)

1. **Cablare le fonti proposte dallo scout**: dopo l'approvazione umana di una
   proposta in `source_candidates.csv`, scrivere l'adapter del cacciatore per
   quel dominio (come `istat_regional_source` per la demografia).
2. **Estendere la watchlist**: altre serie Eurostat/istituzionali, poi livello
   provinciale (NUTS3), sempre priorità al regionale fresco.
3. **Profili regionali** (`app/profiles.py`): oggi calcolati sui soli territoriali
   core, non includono ancora le famiglie esterne.
4. **Migrazione URL**: se serve, ripulire eventuali link storici residui; i 301
   coprono territoriali, BES e Multiscopo.

## Gotcha per la prossima sessione

- Gli id BES contengono trattini (es. `09PAE009-N25`): per questo il codice
  `<acr>-<id>` è un **segmento separato in coda** (`/indicatore/<slug>/bes-09PAE009-N25`),
  e lo slug non è mai fuso con l'id.
- Non hardcodare etichette fonte o URL indicatore: passano tutti da
  `app/sources.py`.
- Gli script `scripts/*discovery*/curate/promote/eurostat_source` sono **stdlib
  puri** (niente import di `app.*` a load-time): devono girare nell'agente
  schedulato senza Flask.
- Cache grezza Eurostat (`data/eurostat_cache/`) gitignorata; committati solo i
  fixture in `data/discovery/fixtures/`.
- Il curatore non dichiara mai `exact`; `score_eligible=true` è rifiutato se il
  verso non è direzionale.
- **Bolzano+Trento**: BES e territoriali ricevono già da Istat l'aggregato
  Trentino Alto Adige. Eurostat e Multiscopo lo combinano con **media pesata per
  popolazione** (`multiscopo_sources.TRENTINO_WEIGHTS`,
  `eurostat_source` via `nama_10r_3popgdp`), non con media semplice.
- `indicator_page.html` è condiviso da territoriali ed Eurostat: usa
  `meta.institution` e `meta.license_url` (fallback Istat), quindi le pagine
  Eurostat mostrano licenza CC BY 4.0 e "fonte Eurostat", non Istat.
