# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this is

**Divario Italia** (divarioitalia.it) is a Flask + React atlas of the Istat
territorial development indicators, plus a server-rendered SEO blog about the
territorial divide between Italian regions.

- `/` — React/Vite single-page atlas (source in `frontend/`, built into
  `app/static/dist/`).
- `/blog`, `/blog/<slug>` — server-rendered (Jinja) blog from Markdown in
  `content/posts/`.
- `/legacy` — original D3 dashboard (do not break it).
- `/api/catalog`, `/api/search`, `/api/indicator/<id>`,
  `/api/indicator/<id>/year/<year>` — JSON API for the atlas.
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
  data layer). Never invent figures. Link the article to the atlas with the
  `indicator` frontmatter field and internal links like
  `/?indicator=105&year=2024`.
- Keep it SEO-friendly but natural: keyword in the title and description, sensible
  `##`/`###` headings, relevant tags.

The Markdown engine has `smarty` disabled on purpose, so `--` and `...` are NOT
converted into typographic dashes or ellipses. Keep the source text clean.

## Constraints

- Do not break `/legacy` or the data schema (`tests/test_app.py` guards both).
- Keep the cartographic identity (see `frontend/src/styles.css` and
  `app/static/css/site.css`): navy `#15233b`, paper `#fbfaf7`, single accent
  `#e4572e`, fonts Archivo / Inter / Space Mono.
- Do not commit secrets (`.gitignore` already excludes `client_secret_*.json`).
- Commit messages: no `Co-Authored-By` trailer.
