# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

This file is a **router**. It carries what is true everywhere and short enough
to be worth repeating; everything with depth lives in the document that owns
the subject, and the path-scoped rules in `.claude/rules/` load the details
exactly where they apply. That split is deliberate: a rule copied into two
places goes out of sync without anyone noticing, and this project has already
paid for that once (a scheduled agent spent weeks writing into a file the app
no longer read, because its prompt repeated a contract instead of pointing at
it).

**So: if a topic below has a doc, read the doc. Do not act on the summary here.**

## The map

| se stai lavorando su... | leggi |
| --- | --- |
| la catena autonoma, gli agenti, il cancello, le Routine | [`docs/AUTONOMOUS_PIPELINE.md`](docs/AUTONOMOUS_PIPELINE.md) |
| come apre e chiude una run un agente qualsiasi | [`docs/AGENT_CONTRACT.md`](docs/AGENT_CONTRACT.md) |
| una pagina indicatore, la sua prosa, le sue guardie | [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md) |
| scoperta e promozione di indicatori multifonte | [`docs/DISCOVERY_PIPELINE.md`](docs/DISCOVERY_PIPELINE.md) |
| stato corrente del sistema, id delle Routine, cosa manca | [`docs/DISCOVERY_STATUS.md`](docs/DISCOVERY_STATUS.md) |
| aggiungere indicatori, temi o un dataset regionale | [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) |
| dati provinciali | [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md) |
| freschezza dei dati e monitoraggio delle fonti | [`docs/DATA_FRESHNESS.md`](docs/DATA_FRESHNESS.md), [`docs/SOURCE_MONITORING.md`](docs/SOURCE_MONITORING.md) |
| la voce editoriale, blog e pagine indicatore | [`content/STYLE.md`](content/STYLE.md) |
| come si misura un articolo, i dieci criteri | [`docs/WRITING_RUBRIC.md`](docs/WRITING_RUBRIC.md) |
| che cosa ha misurato il primo lotto, e il giro dopo | [`docs/WRITING_QUALITY_PLAN.md`](docs/WRITING_QUALITY_PLAN.md), Parte terza |
| quali fonti secondarie si possono citare | [`docs/SECONDARY_SOURCES.md`](docs/SECONDARY_SOURCES.md) |
| cambiare modello, prompt o hook degli agenti | [`docs/CANARY.md`](docs/CANARY.md), `evals/README.md` |

Le regole con uno scope stanno in `.claude/rules/` (app, editorial, pipeline,
frontend, data) e si caricano da sole quando tocchi i file a cui si applicano.
Le procedure condivise dagli agenti stanno in `.claude/skills/`
(`pipeline-close-run`, `untrusted-web`, `indicator-review`, e `canary`, che
scatta prima di ogni cambio a modelli, prompt o hook degli agenti).

Per guardare la catena senza aprire file:

```bash
python3 scripts/pipeline_dashboard.py --open   # tutto in una pagina
python3 scripts/pipeline_status.py             # solo dove si e' fermata
python3 scripts/pipeline_log.py                # solo che cosa hanno fatto gli agenti
python3 scripts/pipeline_dispatch.py           # solo chi tocca adesso
```

## What this is

**Divario Italia** (divarioitalia.it) is a Flask + React atlas of the Istat
territorial development indicators, plus a server-rendered SEO blog and a
quality-of-life section for regions and provinces. The atlas lives at `/`
(source in `frontend/`, built into `app/static/dist/`); every indicator from
every source family at `/indicatore/<slug>/<acronimo>-<id>`, served by **one
template over one view model**; the blog at `/blog`; the editorial hub at
`/divari-regionali`; the compare tool at `/confronto`; internal search at
`/ricerca`; the original D3 dashboard at `/legacy` (do not break it); the JSON
API under `/api/`. The route-by-route truths (what is canonical, what is
noindex and why, what recomputes at render time) live in
`.claude/rules/app.md`.

**Source naming has a single source of truth in `app/sources.py`**, stated
here because breaking it is invisible: user-facing labels are institution-first
plain names, never a bare internal acronym, and no family label or indicator
URL may be hardcoded anywhere else. The code that did published an Istat
series under Eurostat's name.

Data layer: `app/data.py` (reads `app/static/data/Assoluti_Regione.csv`).
Blog layer: `app/blog.py` (reads `content/posts/*.md`).

## Commands

```bash
# stato della catena editoriale, tutti gli stadi
python3 scripts/pipeline_status.py

# build the SPA (required after changing anything in frontend/)
cd frontend && npm run build && cd ..

# run locally (from the repo root)
.venv/bin/gunicorn run:app -b 127.0.0.1:5050

# tests, audit, whitespace
.venv/bin/python -m unittest discover -s tests -v          # tutta la suite (695 test, ~65s), prima di commit/push
.venv/bin/python -m unittest discover -s tests/unit -v      # solo veloci (249 test, ~2s), durante lo sviluppo
.venv/bin/python -m unittest discover -s tests/integration -v  # solo la parte pesante (446 test, ~65s): Flask/HTTP e catena e2e
cd frontend && npm audit --audit-level=low
git diff --check
```

`tests/` e' pacchetto Python (ha `__init__.py`) apposta: e' cosi' che `tests/conftest.py`
si aggancia sotto `unittest` (che, a differenza di pytest, non lo carica da solo). Un file va
in `tests/integration/` se ha bisogno di un giro reale (client Flask, catena end-to-end su
file temporanei, lettura di tutti gli articoli committati); il resto sta in `tests/unit/`.
Un file che mescola le due cose va spaccato, non spostato per intero: e' successo a
`test_indicator_view.py`, ora due file, uno per meta'.

After editing `frontend/src/*`, always rebuild before testing the served app.
After changing data, **restart gunicorn**: the core loaders cache for the life
of the process (`lru_cache`, not a TTL).

## The autonomous chain — READ [`docs/AUTONOMOUS_PIPELINE.md`](docs/AUTONOMOUS_PIPELINE.md)

Seven stages take an indicator from a source catalogue to a published page and
come back when the data moves: **scout** -> **hunter** -> **promoter** ->
**curator** -> **writer** -> **reviewer** -> **verificatore** (which repairs
nothing: its refutations go back to the reviewer's queue). Each stage has an
agent in `.claude/agents/`, a deterministic queue computed from committed
files, and a verdict from `scripts/pipeline_gate.py` that decides whether it
may publish.

The constitution of the chain (one dispatcher and one stage per tick, one file
per record, `run_id` over PR number, the gate's perimeter, no human in the
loop, never `gh pr merge --auto`, data-driven re-entry, stdlib-pure scripts)
lives in `.claude/rules/pipeline.md` and, in full, in the two documents above.
Do not act on this paragraph: it is a table of contents.

## Writing — READ [`content/STYLE.md`](content/STYLE.md)

One voice for the blog and the indicator pages, owned by `content/STYLE.md`.
The absolutes: no em-dash `—`, no en-dash `–`, no semicolon `;`, no `…`; only
real, verified numbers, never an invented source; canonical indicator links
only (`/indicatore/<slug>/ter-105`, never `/?indicator=`). The bar is
[`docs/WRITING_RUBRIC.md`](docs/WRITING_RUBRIC.md): ten criteria, under 14 out
of 20 is not ready. The deterministic tooling (brief, definition check,
queues, prose lint) is listed in `.claude/rules/editorial.md`, and the error
classes only a reading catches are the `indicator-review` skill.

## Data — READ [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md)

Themes, theme scores, region profiles and macro-areas are all **derived** from
the data and recomputed at runtime; the wiring (directions in
`CURATED_DIRECTION`, theme mapping in `config/theme_categories.csv`,
provincial separation) is in `.claude/rules/data.md`. The quiet failure worth
knowing everywhere: an unmapped theme keeps its indicator in the catalogue and
drops it from every macro-area total, with nothing failing.

## Constraints

- Do not break `/legacy` or the data schema (`tests/integration/test_app.py` guards both).
- Keep technical SEO intact (the list is in `.claude/rules/app.md`).
- Keep the cartographic identity: navy `#15233b`, paper `#fbfaf7`, single
  accent `#e4572e`, fonts Archivo / Inter / Space Mono.
- Do not commit secrets (`.gitignore` already excludes `client_secret_*.json`).
- Commit messages: no `Co-Authored-By` trailer.
