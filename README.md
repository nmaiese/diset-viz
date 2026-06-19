# Divario Italia

**Divario Italia** ([divarioitalia.it](https://divarioitalia.it)) is a Flask + React
atlas for exploring the territorial divide between Italian regions, built on the
Istat territorial development indicators.

It combines an interactive atlas (maps, rankings, time series) with a
data-driven blog about regional disparities.

## Features

- **Atlas explorer**: a browsable index of all 377 indicators with per-indicator
  national-trend sparklines, coverage badges, theme spine, search, sort and a
  "complete data only" filter (on by default).
- **Indicator detail**: choropleth map, regional ranking and historical series,
  with year/region selectors, contextual insights (value + rank) and in-theme
  previous/next navigation.
- **Blog**: server-rendered, SEO-oriented articles written in Markdown
  (`content/posts/*.md`) — meant to be published automatically by an AI agent.
  Includes per-article meta tags, Open Graph, JSON-LD, `sitemap.xml` and
  `robots.txt`.
- Shareable URLs across both atlas views (`view`, `indicator`, `year`, `region`,
  `theme`, `q`, `sort`, `partial`).
- Flask backend serving a filtered API (no full dataset download in the SPA).

## Stack

- Python
- Flask
- React
- Vite
- D3.js

## App Structure

- `/` serves the React atlas (single-page app).
- `/blog` and `/blog/<slug>` are server-rendered (Jinja) for SEO.
- `/sitemap.xml` and `/robots.txt` expose the site to crawlers.
- `/legacy` keeps the original D3.js dashboard available as an archive view.
- `/data` still returns the full legacy dataset for the archived D3 view.
- `/api/catalog`, `/api/search`, `/api/indicator/<id>` and
  `/api/indicator/<id>/year/<year>` power the atlas.

## Writing blog articles

Drop a Markdown file in `content/posts/` — it is published automatically. Use
YAML frontmatter:

```markdown
---
title: "Headline (keep it SEO-friendly)"
slug: optional-custom-slug          # otherwise derived from the filename
description: "Meta description, ~155 chars, used for SEO and Open Graph."
date: 2026-06-19
author: "Redazione Divario Italia"
cover: /static/img/blog/your-cover.svg
cover_alt: "Accessible description of the cover"
tags: [Turismo, Divario Nord-Sud]
indicator: 105                      # optional: links to /?indicator=105 in the atlas
indicator_label: "Tasso di turisticità (2024)"
draft: false                        # set true to hide
---

Body in Markdown. Tables, lists and `> blockquotes` are supported. Add
`{: .data-callout}` after a paragraph to render it as a highlighted data box,
and link into the atlas with `[text](/?indicator=105&year=2024)`.
```

See `content/posts/2026-06-19-divario-turistico-nord-sud-2024.md` for a full
example, and [`content/STYLE.md`](content/STYLE.md) for the editorial style
(human voice, no em-dashes/semicolons, real data only). Agents should also read
`CLAUDE.md` / `AGENTS.md`.

## Data

The legacy DiSET dataset has been replaced with the current Istat dataset
"Indicatori territoriali per le politiche di sviluppo".

- Source page: https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/
- Download used by the updater: https://www.istat.it/storage/politiche-sviluppo/Archivio_unico_indicatori_regionali.zip
- Current generated dataset: 101,970 rows, 377 indicators, 20 regions, 1981-2025.

The app keeps the original CSV schema expected by the D3 frontend. The updater
maps `Valle d'Aosta/Vallée d'Aoste` to `Valle d'Aosta` and
`Trentino-Alto Adige/Südtirol` to `Trentino Alto Adige`, because the current map
uses 20 regional geometries. Province-level rows for `Bolzano/Bozen` and
`Trento` are excluded.

Missing and non-finite values (empty cells, `-`, and Istat `INF` placeholders for
undefined ratios) are treated as missing throughout the data layer, so they never
break the API or the charts. `/api/catalog` enriches each indicator with
`region_count`, `completeness`, `complete` (≥98% of region×year cells over 20
regions) and a downsampled national-average `spark` series, which power the atlas
index, badges, sorting and filtering without shipping the full dataset.

The atlas UI loads three Google Fonts (Archivo, Inter, Space Mono) via `<link>`,
with system-font fallbacks if they are unavailable.

Regenerate the dataset with:

```bash
python3 scripts/update_data.py
```

### Data source evaluation

The Istat *Indicatori territoriali per le politiche di sviluppo* archive remains
the best fit and is kept as the single source. Alternatives were reviewed:

- **OpenCoesione** ([opencoesione.gov.it](https://opencoesione.gov.it/it/opendata/))
  publishes cohesion-policy *projects, funding and payments*, not the broad set of
  regional context indicators this app needs; its "indicatori di contesto" simply
  republish the same Istat series. Not a replacement.
- **ISTAT SDMX / IstatData API** is an access *method*, not a richer dataset.
  Rebuilding 377 indicators by stitching individual dataflows would reduce coverage
  and stability versus the single curated archive.

The Istat archive is official, citable, updated monthly (~20th of each month), and
the download URL was verified live (HTTP 200, `Last-Modified: 2026-05-20`). Re-running
`scripts/update_data.py` produced a file byte-identical to the committed dataset, so
the indicators are already current (through 2025) — no data change was required.

## Run Locally

Use Python 3.12 or a compatible Python 3 version.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python3 run.py
```

The production entrypoint remains compatible with PaaS deployments:

```bash
gunicorn run:app
```

Run the backend smoke tests with:

```bash
python3 -m unittest discover -s tests -v
```

Build the frontend with:

```bash
cd frontend
npm run build
```

## Deploy

The app can be deployed on any Python web host that supports gunicorn. For
Render, the included `render.yaml` can be used as a blueprint.

Manual settings:

- Build command: `pip install -r requirements.txt && cd frontend && npm ci && npm run build`
- Start command: `gunicorn run:app`
- Runtime: Python 3.12

## Project Status

This repository is a revived portfolio/archive project. The backend dependency
set and the regional data pipeline have been updated, while the original D3
interface has intentionally been kept close to the historical version.

## License

Apache License 2.0. See [LICENSE](LICENSE).
