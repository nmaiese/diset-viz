# AGENTS.md

Instructions for coding agents (Codex and others) in this repository. Claude
Code reads `CLAUDE.md`; this file mirrors the essentials for everyone else.

## Dove sta scritto cosa

Questo file è un router, come `CLAUDE.md`. Per i temi con profondità leggi il
documento che li possiede, non il riassunto qui:

| se stai lavorando su... | leggi |
| --- | --- |
| la catena autonoma, gli agenti, il cancello, le Routine | `docs/AUTONOMOUS_PIPELINE.md` |
| come apre e chiude una run un agente qualsiasi | `docs/AGENT_CONTRACT.md` |
| una pagina indicatore e le sue guardie | `docs/INDICATOR_PAGES.md` |
| scoperta e promozione multifonte | `docs/DISCOVERY_PIPELINE.md` |
| stato corrente, id delle Routine, cosa manca | `docs/DISCOVERY_STATUS.md` |
| dati regionali / provinciali | `docs/DATA_PIPELINE.md`, `docs/PROVINCE_PIPELINE.md` |
| la voce editoriale | `content/STYLE.md` |
| cambiare modello, prompt o hook degli agenti | `docs/CANARY.md`, `evals/README.md` |

Le regole con uno scope stanno in `.claude/rules/` (app, editorial, pipeline,
frontend, data) e le procedure condivise dagli agenti della catena in
`.claude/skills/`: Claude Code le carica da solo, chiunque altro le legge come
documenti normali, e valgono per tutti.

Per guardare la catena senza aprire file:

```bash
python3 scripts/pipeline_monitor.py            # dov'e' fermo e perche' (nell'app: /_pipeline)
python3 scripts/pipeline_launch.py             # cosa lanciare adesso, per-indicatore
python3 scripts/practice_timeline.py           # la storia per indicatore (il dossier, read-only)
python3 scripts/pipeline_status.py             # le code per (vecchio) stadio
```

## Se tocchi la catena autonoma

Quattro cose che non si intuiscono dal codice e che costa caro scoprire da soli.
Il resto sta in `docs/AUTONOMOUS_PIPELINE.md`, che le possiede.

- **Un lanciatore, lavoro per-indicatore in parallelo.** `scripts/pipeline_launch.py`
  legge il dossier per-indicatore e le code e restituisce la lista prioritizzata
  di lanci: tre ruoli (ammissione = scout+hunter+promoter, produttore =
  curator+writer+reviewer, verificatore), produttore e verificatore
  per-indicatore, ammissione batch. Niente piu' dispatcher a uno-stadio-per-tick
  ne' lock una-PR-aperta: indicatori diversi toccano file diversi e non
  contendono.
- **Ogni registro è uno store a un file per record**, e quello toglie il
  conflitto invece di gestirlo: `content/indicators/` (uno per articolo),
  `data/pipeline/runs/` (uno per run), `data/pipeline/verifiche/` (uno per
  verifica). Non ricompattarne nessuno in un file solo.
- **Una run si identifica dal `run_id`, mai dal numero della pull request.** La
  riga di diario dell'agente viene committata prima che la pull request esista,
  quindi non può portarne il numero: `pipeline_log.py --write` conia e stampa
  l'id, `pipeline_merge.py --run-id` unisce le due metà.
- **Il perimetro sta in `pipeline_gate.STAGE_PATHS`**, non nei prompt, e non si
  allarga per far passare qualcosa. Una voce che finisce con `/` è un prefisso
  di directory, e la barra è ciò che le impedisce di allargarsi da sola. Lo
  stesso perimetro è applicato al momento del gesto da `scripts/agent_guard.py`
  (hook per-agente) e ri-verificato in CI sui branch `automation/*`.

## Project

**Divario Italia** (divarioitalia.it): a Flask + React atlas of Istat territorial
indicators, a server-rendered SEO blog (`content/posts/*.md`, rendered at
`/blog`) and a quality-of-life section for regions and provinces. The React app
lives in `frontend/` and builds into `app/static/dist/`. Do not break `/legacy`.

Three server-rendered pages have rules worth knowing before touching them:
`/divari-regionali` (the editorial hub, every figure recomputed from the catalog
in `app/divari.py`, never hardcoded), `/confronto` (the compare tool's only public
URL, mounts the SPA view via `window.__diInitialView`), and `/ricerca` (internal
search, `noindex, follow` set in the view, out of the sitemap and out of the
robots disallow list). See `CLAUDE.md` for the why of each.

## Commands

```bash
cd frontend && npm run build && cd ..        # rebuild SPA after frontend/ edits
.venv/bin/gunicorn run:app -b 127.0.0.1:5050 # run (from repo root)
.venv/bin/python -m unittest discover -s tests -v
cd frontend && npm audit --audit-level=low
```

## Writing blog articles

Any file under `content/posts/` must follow the editorial style in
[`content/STYLE.md`](content/STYLE.md). Hard rules, repeated here so they are not
missed:

- **No em-dash `—`, no en-dash `–`.** Use commas or separate sentences. Ranges:
  "dal 1981 al 2024" (plain `-` only inside tables).
- **No semicolons `;`. No `…` ellipsis** (use `...` if unavoidable).
- Human, journalistic voice. Varied sentence length, one idea per paragraph,
  active voice. Avoid bot patterns: repeated "non solo X ma anche Y", dramatic
  colons, closings like "In conclusione", inflated adverbs, slogan sentences.
- `In breve` and `Dati usati` can repeat because they help trust. Do not repeat
  the same full article skeleton across a cluster. Vary narrative H2s and make the
  closing point to a concrete next step.
- Only real, verified numbers from the indicators. Never invent figures. Link to
  the catalog via the `indicator` frontmatter field and canonical indicator
  paths (`/indicatore/<slug>/<acr>-<id>`), never `/?indicator=...`.
- SEO but natural: keyword in title and `description`, sensible headings, tags.
- Use optional `seo_title` when the visible H1 is editorial but the SERP title
  should be shorter or closer to the query.
- Before publishing, fill a claim table with source, period, geography, unit,
  transformation and confidence for every headline number.
- Include a caveat, a methodology/source link, an atlas or indicator link, and a
  concrete next step for the reader.

The Markdown engine has `smarty` disabled, so `--`/`...` are not auto-converted.
Keep the source clean.

Before publishing article batches, run `rg -n "[—–;]" content/posts` and inspect
repeated H2 sequences. For templates, frontend strings and SVG text, distinguish
visible copy from CSS, JS, JSON-LD and CSV syntax.

## Writing indicator pages

Every public indicator page must follow [`docs/INDICATOR_PAGES.md`](docs/INDICATOR_PAGES.md).
The common page generator must make every sheet answer these questions with data
from the indicator itself:

- What does the indicator measure, and what population, denominator or unit does
  it use?
- What does a concrete value mean?
- How should high and low values be read, and what can the indicator not prove?
- How did the latest value change from the previous available year on the same
  territorial base?
- What is the long-term movement, source, coverage and next useful action?

For percentages, annual changes are percentage points. Never call an unweighted
mean of regional values the Italian or national average. Compare only territories
present in both years, keep observation separate from causality, and omit claims
that the data cannot support. Add a regression test when a page exposes a new
indicator family or a special interpretation rule.

## Technical SEO checks

- `www.divarioitalia.it` must redirect to `https://divarioitalia.it` with `301`.
- Public 404 pages must be HTML, useful, and `noindex, follow`.
- API and data endpoints must carry `X-Robots-Tag: noindex, nofollow, noarchive`.
- `Strict-Transport-Security`, canonical, OG/Twitter tags, sitemap and robots
  must be checked after SEO changes.
- JSON-LD must match visible content. Do not add schema only for rich results.

## Adding indicators or datasets

When you change `app/static/data/Assoluti_Regione.csv` (new indicators, themes or
a new dataset), follow [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md). Themes,
theme scores, region profiles and macro-areas are derived from the data and
recomputed at runtime (cache 1h). Set each new indicator's direction in
`CURATED_DIRECTION` (`app/indicator_notes.py`) and map each new source theme to
one of the 12 canonical categories with a row in `config/theme_categories.csv`.
The categories themselves and the four macro-areas live in `CANONICAL_CATEGORIES`
and `MACRO_AREAS` (`app/taxonomy.py`): mapping a theme is data, inventing a
category is code. Then restart gunicorn, rebuild the frontend and run the tests.

A theme nobody mapped fails quietly: the indicator stays in the catalogue and
vanishes from every macro-area total.

When working on provincial quality-of-life data, keep it separate from the
regional atlas. Follow [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md),
respect the Istat SDMX rate limit, and do not merge provincial rows into
`Assoluti_Regione.csv` or `app/data.py`.

## Other constraints

- Keep the cartographic identity (navy `#15233b`, paper `#fbfaf7`, accent
  `#e4572e`; fonts Archivo / Inter / Space Mono).
- Never commit secrets. No `Co-Authored-By` trailer in commit messages.
