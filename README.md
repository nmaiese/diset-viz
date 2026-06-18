# DiSET Viz

DiSET Viz is a Flask and D3.js dashboard for exploring socio-economic indicators
about Italian regions and provinces from the former DiSET public data source.

The project combines maps, bar charts and metric selectors to make territorial
statistics easier to inspect.

## Features

- Interactive map of Italian regions.
- Metric and year selectors.
- Bar chart and time-series views.
- Flask backend for serving processed data.

## Stack

- Python
- Flask
- D3.js
- DataTables
- Select2
- Bootstrap

## Run Locally

This is a legacy project with pinned dependencies from the original development
period.

```bash
python -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Project Status

This repository is kept public as a portfolio/archive project. It is not
actively maintained, but it shows a complete public-data dashboard built with
Flask and D3.js.

## License

Apache License 2.0. See [LICENSE](LICENSE).
