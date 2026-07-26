# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

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
  family, lives here. Keyword-first for SEO: the human slug leads, the resolving
  code trails under a source acronym (`ter` Istat territoriali, `bes` Istat
  benessere, `ims` Istat vita quotidiana delle famiglie, `eur` Eurostat, `dem`
  Istat indicatori demografici). Le famiglie servite dallo strato esterno stanno
  in `sources.EXTERNAL_FAMILIES`: aggiungerne una e' una riga in `app/sources.py`
  piu una in `discovery.FEED_FAMILY` e un parser in
  `promote_candidates.PROMOTION_PARSERS`, e i tre mirror sono appaiati da
  `tests/test_discovery.py`. Non cablare mai un prefisso: il codice che lo faceva
  ha pubblicato una serie Istat sotto il nome di Eurostat, l'ha tenuta fuori dal
  quiz e l'ha resa invisibile al curatore. The code
  is the id-carrying last segment, so the page survives a name (slug) change; the
  slug is decorative and a wrong one 301s to canonical. Legacy URLs
  (`/indicatore/<num>-<slug>` and `/qualita-della-vita/indicatore/...`) 301 to it.
  Source naming and URL building have a single source of truth in `app/sources.py`:
  user-facing labels are institution-first plain names, never a bare internal
  acronym. Do not hardcode family labels or indicator URLs elsewhere.
  **One template serves all four families** (`app/templates/indicator_page.html`)
  over one view model (`app/indicator_view.py`), in three zones: an interactive
  cockpit that owns every number, an article of four fixed sections that owns
  every sentence, and an apparatus (sources, citation, related). A figure is
  shown once, in the cockpit, and the prose interprets it. See
  [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md) before touching either.
- `/legacy` — original D3 dashboard (do not break it).
- `/api/catalog`, `/api/search`, `/api/indicator/<id>`,
  `/api/indicator/<id>/year/<year>` — JSON API for the atlas.
- `/api/quality-life/*` and `/api/quality-life/province/*` — JSON API for the
  quality-of-life pages.
- `/sitemap.xml`, `/robots.txt` — SEO.

Data layer: `app/data.py` (reads `app/static/data/Assoluti_Regione.csv`).
Blog layer: `app/blog.py` (reads `content/posts/*.md`).

## Commands

```bash
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

## Writing indicator pages — READ THIS

The prose of an indicator page lives in
`app/static/data/indicator_texts.json`: one `lead` plus four ordered sections
(`definizione`, `quadro`, `dinamica`, `limiti`), written by
`.claude/agents/indicator-writer.md`. A section nobody has written yet is
composed from the data at render time, so every page has the same skeleton while
only some have been through an editor.

Always start from the deterministic data brief, never from ad-hoc API calls:

```bash
.venv/bin/python -m scripts.indicator_brief ter-178     # everything about one indicator
.venv/bin/python -m scripts.text_queue                  # what still needs an editor
.venv/bin/python -m scripts.review_queue                # what still needs a reader
```

An article is written for **one territorial level** and used only there, so it
declares `"level"` and both queues have one row per (indicator, level). Four
agents own the chain, each with a file in `.claude/agents/` and a deterministic
queue: `indicator-hunter`, `indicator-curator`, `indicator-writer`,
`indicator-reviewer`.

Rules, guards and the "who owns what" table are in
[`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md). The editorial voice is
`content/STYLE.md`, same as the blog.

## Writing blog articles — READ THIS

When you create or edit anything under `content/posts/`, follow
[`content/STYLE.md`](content/STYLE.md). It is the single source of truth for the
editorial voice. The non-negotiable rules:

- **No em-dash `—` and no en-dash `–`** in prose. Use commas or two sentences;
  write ranges as "dal 1981 al 2024" (or `1981-2024` with a plain hyphen inside
  tables).
- **No semicolons `;`** and **no `…` ellipsis character** (use `...` only if
  truly needed).
- Write like a human journalist: varied sentence length, one idea per paragraph,
  active voice, concrete numbers. Avoid bot tells (repeated "non solo X ma anche
  Y", dramatic colons, "In conclusione", inflated adverbs, slogan sentences).
- Use only **real, verified numbers** from the indicators (via the API or the
  data layer). Never invent figures. Link the article to the catalog with the
  `indicator` frontmatter field and internal links using the indicator's
  **canonical path**, e.g. `/indicatore/tasso-di-turisticita/ter-105`. Never
  `/?indicator=...` or `/atlante?indicator=...` (`tests/test_url_migration.py`
  fails on those).
- Keep it SEO-friendly but natural: keyword in the title and description, sensible
  `##`/`###` headings, relevant tags.
- Use optional `seo_title` when the visible H1 should stay editorial but the
  browser title should be shorter or closer to the search query.
- Before publishing, leave a claim table with source, period, geography, unit,
  transformation and confidence for every headline number.
- Include a caveat, methodology/source link, atlas or indicator link, schema
  candidate, and concrete next step for the reader.

The Markdown engine has `smarty` disabled on purpose, so `--` and `...` are NOT
converted into typographic dashes or ellipses. Keep the source text clean.

## Adding indicators or datasets — READ THIS

When you add indicators, themes, or a new dataset to
`app/static/data/Assoluti_Regione.csv`, follow the checklist in
[`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md). The short version: themes,
theme scores, region profiles and macro-areas are all **derived** from the data
and recomputed at runtime. The core loaders in `app/data.py`
(`get_rows`/`get_catalog`/`get_indicator`) cache for the life of the process
(`lru_cache`, not a TTL); most other derived views still use `cache.memoize`
(1h TTL). For each new indicator id set its direction
in `CURATED_DIRECTION` (`app/indicator_notes.py`), and for each new theme map it
to a macro-area in `MACRO_AREAS` (same file). Then restart gunicorn to clear the
cache, rebuild the frontend, run the tests, and re-check which themes are now
"valutabili" vs descriptive with the diagnostic snippet in that doc.

Provincial data is separate. Follow
[`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md), keep the SDMX cache out
of git, commit only normalized CSV artifacts, and never mix provincial rows into
the regional CSV or `app/data.py`.

## Discovering new multi-source indicators — READ THIS

The app is a multi-source aggregator that prefers fresh, regional data (then
provincial). New indicators are **discovered** into a reviewable staging queue
before any integration. Follow [`docs/DISCOVERY_PIPELINE.md`](docs/DISCOVERY_PIPELINE.md).
The short version: a scheduled hunter (`scripts/discover_candidates.py`, stdlib
only) scans allowlisted institutional sources (`config/external_sources.yaml`)
and writes candidates to `data/discovery/candidates.csv`; a human approves them
in a PR (`triage_status=approved`); then `scripts/promote_candidates.py` writes
rows into the external layer (a new indicator becomes a standalone atlas entry
under the `eur:` id namespace via `app/eurostat_atlas.py`). A second **curator**
step (`scripts/curate.py` for the direction evidence, `data/discovery/curation.csv`
for the reviewed decision, `scripts/apply_curation.py` to publish) verifies the
verso against the data, reviews the description, and sets `score_eligible` so the
indicator enters the quiz and the quality-of-life score. Nothing goes live without
a merged PR. The hunter never claims `definition_match=exact` (humans confirm that).
Eurostat regional (NUTS2) is the pilot source; its raw cache (`data/eurostat_cache/`)
stays out of git, only the offline fixtures under `data/discovery/fixtures/` are committed.

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
