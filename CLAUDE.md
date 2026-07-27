# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

This file is a **router**. It carries what is true everywhere and short enough to
be worth repeating, and for anything with depth it points at the document that
owns the subject. That split is deliberate: a rule copied into two places goes
out of sync without anyone noticing, and this project has already paid for that
once (a scheduled agent spent weeks writing into a file the app no longer read,
because its prompt repeated a contract instead of pointing at it).

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

Per guardare la catena senza aprire file:

```bash
python3 scripts/pipeline_dashboard.py --open   # tutto in una pagina
python3 scripts/pipeline_status.py             # solo dove si e' fermata
python3 scripts/pipeline_log.py                # solo che cosa hanno fatto gli agenti
```

## What this is

**Divario Italia** (divarioitalia.it) is a Flask + React atlas of the Istat
territorial development indicators, plus a server-rendered SEO blog and a
quality-of-life section for regions and provinces.

- `/` — React/Vite single-page atlas (source in `frontend/`, built into
  `app/static/dist/`).
- `/blog`, `/blog/<slug>` — server-rendered (Jinja) blog from Markdown in
  `content/posts/`.
- `/qualita-della-vita`, `/qualita-della-vita/classifica`,
  `/qualita-della-vita/metodologia` — regional quality-of-life pages.
- `/qualita-della-vita/province` — provincial quality-of-life ranking from Istat
  BES dei Territori, available when the provincial artifacts are present.
- `/indicatore/<slug>/<acronimo>-<id>` — every atlas indicator, from every source
  family. Keyword-first for SEO: the human slug leads, the resolving code trails
  under a source acronym (`ter` Istat territoriali, `bes` Istat benessere, `ims`
  Istat vita quotidiana delle famiglie, `eur` Eurostat, `dem` Istat indicatori
  demografici). The code is the id-carrying last segment, so the page survives a
  name change; the slug is decorative and a wrong one 301s to canonical. Legacy
  URLs 301 here. **One template serves every family**
  (`app/templates/indicator_page.html`) over one view model
  (`app/indicator_view.py`). See [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md)
  before touching either.
- `/divari-regionali` — the editorial hub on the territorial divide, server
  rendered from `app/divari.py`. Not a second taxonomy over `/temi` and
  `/regioni`: it argues one thesis (the divide is not a single line) and measures
  it, so **every number and every share in its prose is recomputed from the
  catalog at render time**. Never hardcode a figure into that template. It reuses
  the homepage map component through `_map_panel.html` (`_map_hero` in
  `app/views.py`), and its partition means are plain averages of regional values,
  a limit the page states in full.
- `/confronto` — the canonical home of the compare tool: a server-rendered page
  that mounts the SPA's compare view through `window.__diInitialView`. The SPA
  state `/atlante?view=confronto` still works, but nothing links to it: one tool,
  one public URL. Add a path-scoped view by setting that flag in the template,
  never by teaching `frontend/src/main.jsx` about Flask routes.
- `/ricerca?q=` — internal search, server rendered, **`noindex, follow` on
  purpose** (an unbounded `?q=` space would be thin duplicate pages of the cards
  it lists). The header is set in the view because `add_security_headers`
  stamps `index, follow` on anything that does not declare otherwise. It is out of
  the sitemap and deliberately *not* in the robots.txt disallow list, since a
  disallowed page never gets its noindex read. The masthead search icon, the
  mobile menu form and the homepage `SearchAction` all point here.
- `/legacy` — original D3 dashboard (do not break it).
- `/api/catalog`, `/api/search`, `/api/indicator/<id>`,
  `/api/indicator/<id>/year/<year>` — JSON API for the atlas.
- `/api/quality-life/*` and `/api/quality-life/province/*` — JSON API for the
  quality-of-life pages.
- `/sitemap.xml`, `/robots.txt` — SEO.

Data layer: `app/data.py` (reads `app/static/data/Assoluti_Regione.csv`).
Blog layer: `app/blog.py` (reads `content/posts/*.md`).

**Source naming and URL building have a single source of truth in
`app/sources.py`**, and this one is worth stating here because breaking it is
invisible: user-facing labels are institution-first plain names, never a bare
internal acronym, and no family label or indicator URL may be hardcoded anywhere
else. The families served by the external layer live in
`sources.EXTERNAL_FAMILIES`; adding one is a line in `app/sources.py`, one in
`discovery.FEED_FAMILY` and a parser in `promote_candidates.PROMOTION_PARSERS`,
and `tests/test_discovery.py` pins the three mirrors together. Never hardcode a
prefix: the code that did published an Istat series under Eurostat's name, kept
it out of the quiz and made it invisible to the curator.

## Commands

```bash
# stato della catena editoriale, tutti gli stadi
python3 scripts/pipeline_status.py

# build the SPA (required after changing anything in frontend/)
cd frontend && npm run build && cd ..

# run locally (from the repo root)
.venv/bin/gunicorn run:app -b 127.0.0.1:5050

# tests, audit, whitespace
.venv/bin/python -m unittest discover -s tests -v
cd frontend && npm audit --audit-level=low
git diff --check
```

After editing `frontend/src/*`, always rebuild before testing the served app.
After changing data, **restart gunicorn**: the core loaders cache for the life of
the process (`lru_cache`, not a TTL).

## The autonomous chain — READ [`docs/AUTONOMOUS_PIPELINE.md`](docs/AUTONOMOUS_PIPELINE.md)

Seven stages take an indicator from a source catalogue to a published page and
then come back to it when the data moves: **scout** (which sources) -> **hunter**
(which indicators) -> **promoter** -> **curator** (which verso, which score) ->
**writer** (the article) -> **reviewer** (reads it against the data) ->
**verificatore** (tries to falsify what the reviewer signed, and repairs
nothing: its refutations go back to the reviewer's queue). Each has an
agent in `.claude/agents/`, a deterministic queue computed from committed files,
and a verdict from `scripts/pipeline_gate.py` that decides whether it may publish.

What you need to know before touching any of it:

- **The gate is not advisory.** Every stage may write only a short list of paths
  (`pipeline_gate.STAGE_PATHS`). Do not widen it to make something pass.
- **No stage waits for a human.** Prose merges itself; everything that moves live
  numbers or names an institution merges once CI is green. Nobody reads these
  pull requests before they land, so the control is the perimeter, the gate and
  the suite, never an approval.
- **Never close a stage with `gh pr merge --auto`.** It does not wait on this
  repository, it merges immediately, and it did so for weeks while the docs said
  otherwise. The wait lives in `scripts/pipeline_merge.py`.
- **Re-entry is data-driven, never calendar-driven.** A curation decision expires
  when its source publishes a newer year (`data_year`); a review expires when the
  article's figures are refreshed (`reviewed_vintage`).
- **The scripts of the chain are stdlib-pure** and must stay so: a cloud agent
  runs them on a fresh checkout, before any venv exists.

## Writing indicator pages — READ [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md)

The prose of an indicator page lives in `app/static/data/indicator_texts.json`:
one `lead` plus four ordered sections (`definizione`, `quadro`, `dinamica`,
`limiti`). A section nobody has written is composed from the data at render time,
so every page has the same skeleton while only some have been through an editor.

Always start from the deterministic data brief, never from ad-hoc API calls:

```bash
.venv/bin/python -m scripts.indicator_brief ter-178     # everything about one indicator
python3 scripts/definition_check.py --show ter-178      # what the source says it counts
.venv/bin/python -m scripts.text_queue                  # what still needs an editor
.venv/bin/python -m scripts.review_queue                # what still needs a reader
python3 scripts/prose_lint.py --summary                 # how the prose is doing, as a number
```

The second line is the newest and the least obvious. Everything else compares
the prose to the **series**; that one compares it to Istat's own definition,
from the `Metadati` sheet of the Banca dati territoriale, normalized into
`data/definitions/istat_territoriali.csv` by `scripts/fetch_definitions.py`. It
exists because rereading eleven articles against the data turned up no
arithmetic error at all and four wrong descriptions of what the indicator
counts: a wrong figure dies at the first reader who opens the brief, a wrong
definition is confirmed as correct by every reading that checks the numbers.

The brief's last block ranks the whole theme by rank correlation and says which
indicators draw the same map as this one, which the opposite, and which one that
has nothing to do with it. That is where a cross-reference and its internal link
come from, and the guards check the link but never the sentence around it: a
rank correlation is a co-occurrence, so the verb has to be calibrated, the
confounder named and one exception given. The bar an article is measured against
is [`docs/WRITING_RUBRIC.md`](docs/WRITING_RUBRIC.md).

An article is written for **one territorial level** and used only there, so it
declares `"level"` and both queues have one row per (indicator, level).

## Writing blog articles — READ [`content/STYLE.md`](content/STYLE.md)

It is the single source of truth for the editorial voice, for the blog and for
indicator pages alike. The rules that are absolute and cheap to state:

- **No em-dash `—`, no en-dash `–`, no semicolon `;`, no `…`.** Use commas or two
  sentences; write ranges as "dal 1981 al 2024".
- Write like a human journalist: varied sentence length, one idea per paragraph,
  active voice, concrete numbers. Avoid bot tells (repeated "non solo X ma anche
  Y", dramatic colons, "In conclusione", inflated adverbs, slogan sentences).
- Use only **real, verified numbers**. Never invent figures, never invent a
  source. Link to an indicator with its **canonical path**, e.g.
  `/indicatore/tasso-di-turisticita/ter-105`, never `/?indicator=...` nor
  `/atlante?indicator=...` (`tests/test_url_migration.py` fails on those).

The Markdown engine has `smarty` disabled on purpose, so `--` and `...` are NOT
converted into typographic dashes or ellipses. Keep the source text clean.

## Adding indicators or datasets — READ [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md)

Themes, theme scores, region profiles and macro-areas are all **derived** from the
data and recomputed at runtime. For each new indicator id set its direction in
`CURATED_DIRECTION` (`app/indicator_notes.py`), and for each new theme map it to a
macro-area in `MACRO_AREAS` (same file). Then restart gunicorn, rebuild the
frontend, run the tests, and re-check which themes are now "valutabili".

Provincial data is separate: [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md).
Keep the SDMX cache out of git, commit only normalized CSV artifacts, and never
mix provincial rows into the regional CSV or `app/data.py`.

## Constraints

- Do not break `/legacy` or the data schema (`tests/test_app.py` guards both).
- Keep technical SEO intact: apex canonical host, public 404 HTML `noindex`,
  API/data `X-Robots-Tag`, HSTS, sitemap of canonical public URLs, and JSON-LD
  only where the visible page supports it.
- Keep the cartographic identity (see `frontend/src/styles.css` and
  `app/static/css/site.css`): navy `#15233b`, paper `#fbfaf7`, single accent
  `#e4572e`, fonts Archivo / Inter / Space Mono.
- Do not commit secrets (`.gitignore` already excludes `client_secret_*.json`).
- Commit messages: no `Co-Authored-By` trailer.
