# AGENTS.md

Instructions for coding agents (Codex and others) in this repository. Claude
Code reads `CLAUDE.md`; this file mirrors the essentials for everyone else.

## Project

**Divario Italia** (divarioitalia.it): a Flask + React atlas of Istat territorial
indicators, a server-rendered SEO blog (`content/posts/*.md`, rendered at
`/blog`) and a quality-of-life section for regions and provinces. The React app
lives in `frontend/` and builds into `app/static/dist/`. Do not break `/legacy`.

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
  the atlas via the `indicator` frontmatter field and `/?indicator=...` links.
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
one canonical category in `CANONICAL_CATEGORIES` (`app/taxonomy.py`), then
restart gunicorn, rebuild the frontend and run the tests.

When working on provincial quality-of-life data, keep it separate from the
regional atlas. Follow [`docs/PROVINCE_PIPELINE.md`](docs/PROVINCE_PIPELINE.md),
respect the Istat SDMX rate limit, and do not merge provincial rows into
`Assoluti_Regione.csv` or `app/data.py`.

## Other constraints

- Keep the cartographic identity (navy `#15233b`, paper `#fbfaf7`, accent
  `#e4572e`; fonts Archivo / Inter / Space Mono).
- Never commit secrets. No `Co-Authored-By` trailer in commit messages.
