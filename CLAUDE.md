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
| account utente, login Google, preferiti, statistiche/achievements, confronti salvati, GDPR | [`docs/ACCOUNT.md`](docs/ACCOUNT.md) |
| la catena autonoma, gli agenti, il cancello, le Routine | [`docs/AUTONOMOUS_PIPELINE.md`](docs/AUTONOMOUS_PIPELINE.md) |
| come apre e chiude una run un agente qualsiasi | [`docs/AGENT_CONTRACT.md`](docs/AGENT_CONTRACT.md) |
| una pagina indicatore, la sua prosa, le sue guardie | [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md) |
| che cosa serve per scrivere un indicatore: cifre, angoli, contesto citabile | `packs/` (`angles.py`, `build.py`, `context.py`), [`docs/SECONDARY_SOURCES.md`](docs/SECONDARY_SOURCES.md) |
| scrivere articoli indicatore adesso: il workflow, il lint, i pacchetti | `.claude/workflows/produci-indicatori.js`, `officina/` (`pacchetti.py`, `brief.py`, `pubblica.py`, `lint.py`) |
| scrivere o cambiare un file di agente (contratto, non cronaca) | `.claude/rules/pipeline.md`, e il verdetto in [`docs/OFFICINA_EDITORIALE_PROPOSTA.md`](docs/OFFICINA_EDITORIALE_PROPOSTA.md) |
| quanto costa una run, e come si misura senza sbagliare | `scripts/baseline_tokens.py` (il contratto sta nel suo docstring) |
| scoperta e promozione di indicatori multifonte | [`docs/DISCOVERY_PIPELINE.md`](docs/DISCOVERY_PIPELINE.md) |
| stato corrente del sistema, id delle Routine, cosa manca | [`docs/DISCOVERY_STATUS.md`](docs/DISCOVERY_STATUS.md) |
| aggiungere indicatori, temi o un dataset regionale | [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) |
| dati provinciali | [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md) |
| freschezza dei dati e monitoraggio delle fonti | [`docs/DATA_FRESHNESS.md`](docs/DATA_FRESHNESS.md), [`docs/SOURCE_MONITORING.md`](docs/SOURCE_MONITORING.md) |
| la voce editoriale, blog e pagine indicatore | [`content/STYLE.md`](content/STYLE.md) |
| come si misura un articolo, i dieci criteri | [`docs/WRITING_RUBRIC.md`](docs/WRITING_RUBRIC.md) |
| i piani gia' eseguiti, con le misure e le ipotesi cadute | [`docs/archive/`](docs/archive/) (non sono fonti di verita': se contraddicono il codice, ha ragione il codice) |
| quali fonti secondarie si possono citare | [`docs/SECONDARY_SOURCES.md`](docs/SECONDARY_SOURCES.md) |
| cambiare modello, prompt o hook degli agenti | [`docs/CANARY.md`](docs/CANARY.md), `evals/README.md` |
| priorita' e lacune sulle domande che un motore o un assistente puo' porre | [`docs/LLM_QUERY_MAP.md`](docs/LLM_QUERY_MAP.md) |
| tracciamento, consenso, versione GTM | [`docs/tracking_spec.md`](docs/tracking_spec.md) |

Le regole con uno scope stanno in `.claude/rules/` (app, editorial, pipeline,
frontend, data) e si caricano da sole quando tocchi i file a cui si applicano.
Le procedure condivise dagli agenti stanno in `.claude/skills/`
(`pipeline-close-run`, `untrusted-web`, `indicator-review`, e `canary`, che
scatta prima di ogni cambio a modelli, prompt o hook degli agenti).

Per guardare la catena senza aprire file:

```bash
python3 scripts/pipeline_monitor.py            # dov'e' fermo e perche', in una schermata (nell'app: /_pipeline)
python3 scripts/pipeline_launch.py             # cosa lanciare adesso, e in che ordine (per-indicatore)
python3 scripts/practice_timeline.py           # la storia per indicatore (il dossier, read-only)
python3 scripts/pipeline_status.py             # le code per (vecchio) stadio, ancora lette da pipeline_launch.py
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

**L'interprete Python di questo progetto e' `bin/py`, sempre.** Non `python3`,
che in questo ambiente e' una funzione di shell e senza `$VIRTUAL_ENV` cade su
un interprete privo delle dipendenze; non `.venv/bin/python`, che in molti
worktree non esiste. Nella prima run del workflow tutti e quattro gli scrittori
hanno speso quattro turni a testa a cercarlo, e un pubblicatore ha eseguito il
lint con l'interprete di **un altro worktree**: due codici possibili per lo
stesso verdetto. `bin/py` risolve in un posto solo e fallisce dicendo perche'.

```bash
# scrivere articoli indicatore: il workflow, dalla lista dei codici
#   Workflow({scriptPath: ".claude/workflows/produci-indicatori.js", args: ["ter-30"]})
bin/py -m officina.pacchetti ter-30              # il pacchetto, a mano
bin/py -m officina.pubblica ter-30 < bozza.json  # la bozza diventa un articolo (rifiuta invece di scrivere male)
bin/py -m officina.lint ter-30                   # il cancello editoriale (11s su tutti)
bin/py scripts/tool_failures.py                  # i guasti che si ripetono (il file aveva solo chi lo scriveva)
bin/py -m scripts.calibra_prosa --confronto      # gli esempi contro i pubblicati
bin/py scripts/baseline_tokens.py --workflow wf_… --articles 1   # quanto e' costata una run

# stato della catena editoriale, tutti gli stadi (vecchia catena)
python3 scripts/pipeline_status.py

# build the SPA (required after changing anything in frontend/)
cd frontend && npm run build && cd ..

# run locally (from the repo root)
.venv/bin/gunicorn run:app -b 127.0.0.1:5050

# tests, audit, whitespace
bin/py -m unittest discover -s tests -v          # tutta la suite (1348 test, ~52s), prima di commit/push
bin/py -m unittest discover -s tests/unit -v      # solo veloci (~700 test, ~4s), durante lo sviluppo
bin/py -m unittest discover -s tests/integration -v  # solo la parte pesante (~650 test, ~51s): Flask/HTTP e catena e2e
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

An indicator goes from a source catalogue to a published page like this:
**ammissione** (agent: what enters, with auto-refutation) -> **l'officina**
(`.claude/workflows/produci-indicatori.js`: writes the article) ->
**verificatore** and **reader-editor** (agents: two independent critics, facts
and readability).

**The `produttore` agent is gone**, and so is the `launcher` agent. Writing an
article moved into the workshop, where four narrow types do it inside a
workflow at a twentieth of the cost, and coordination inside a workflow costs
zero tokens. What is left as an agent is what exercises a judgement no workflow
can make deterministic. `scripts/pipeline_launch.py` still computes the launch
plan, and `scripts/pipeline_gate.py` still decides whether a run may publish.

The constitution of the chain (one launcher, work per-indicator in parallel, one
file per record, `run_id` over PR number, the gate's perimeter, no human in the
loop, never `gh pr merge --auto`, data-driven re-entry, stdlib-pure scripts)
lives in `.claude/rules/pipeline.md` and, in full, in the two documents above.
Do not act on this paragraph: it is a table of contents.

## Writing — READ [`content/STYLE.md`](content/STYLE.md)

One voice for the blog and the indicator pages, owned by `content/STYLE.md`.
The absolutes: no em-dash `—`, no en-dash `–`, no semicolon `;`, no `…`; only
real, verified numbers, never an invented source; canonical indicator links
only (`/indicatore/<slug>/ter-105`, never `/?indicator=`). The bar is
[`docs/WRITING_RUBRIC.md`](docs/WRITING_RUBRIC.md): ten criteria on four axes,
each with its own floor (an axis below its floor fails the article whatever the
total), and under 14 out
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
