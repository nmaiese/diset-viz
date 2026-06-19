# DiSET Viz

DiSET Viz is a Flask and D3.js dashboard for exploring socio-economic indicators
about Italian regions from Istat territorial development indicators.

The project combines maps, bar charts and metric selectors to make territorial
statistics easier to inspect.

## Features

- **Atlas explorer**: a browsable index of all 377 indicators with per-indicator
  national-trend sparklines, coverage badges, theme spine, search, sort and a
  "complete data only" filter (on by default).
- **Indicator detail**: choropleth map, regional ranking and historical series,
  with year/region selectors, contextual insights (value + rank) and in-theme
  previous/next navigation.
- Shareable URLs across both views (`view`, `indicator`, `year`, `region`,
  `theme`, `q`, `sort`, `partial`).
- Flask backend serving a filtered API (no full dataset download in the SPA).

## Stack

- Python
- Flask
- React
- Vite
- D3.js

## App Structure

- `/` serves the new React data-magazine interface.
- `/legacy` keeps the original D3.js dashboard available as an archive view.
- `/data` still returns the full legacy dataset for the archived D3 view.
- `/api/catalog`, `/api/search`, `/api/indicator/<id>` and
  `/api/indicator/<id>/year/<year>` power the new filtered interface.

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
