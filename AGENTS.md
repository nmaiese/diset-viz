# AGENTS.md

Instructions for coding agents (Codex and others) in this repository. Claude
Code reads `CLAUDE.md`; this file mirrors the essentials for everyone else.

## Project

**Divario Italia** (divarioitalia.it): a Flask + React atlas of Istat territorial
indicators plus a server-rendered SEO blog (`content/posts/*.md`, rendered at
`/blog`). The React app lives in `frontend/` and builds into `app/static/dist/`.
Do not break `/legacy`.

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
- Only real, verified numbers from the indicators. Never invent figures. Link to
  the atlas via the `indicator` frontmatter field and `/?indicator=...` links.
- SEO but natural: keyword in title and `description`, sensible headings, tags.

The Markdown engine has `smarty` disabled, so `--`/`...` are not auto-converted.
Keep the source clean.

## Other constraints

- Keep the cartographic identity (navy `#15233b`, paper `#fbfaf7`, accent
  `#e4572e`; fonts Archivo / Inter / Space Mono).
- Never commit secrets. No `Co-Authored-By` trailer in commit messages.
