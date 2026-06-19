from app import app
from app.cache import cache
from app.data import get_catalog, get_indicator, get_indicator_year, get_rows, search_indicators

from flask import abort, render_template, request, send_from_directory
from flask.json import jsonify

import csv, os



@cache.memoize(timeout=100)
def get_all_data():
    filepath = os.path.join(os.path.dirname(__file__), 'static/data/Assoluti_Regione.csv')
    with open(filepath, 'r', encoding='utf8') as f:
        reader = csv.DictReader(f, delimiter=";")
        data = list(reader)
    return data

@cache.memoize(timeout=100)
@app.route("/data")
def data():
    data = get_all_data()
    return jsonify(data)


@cache.cached(timeout=300)
@app.route("/")
def main():
    return render_template('app.html')


@cache.cached(timeout=300)
@app.route("/legacy")
def legacy():
    return render_template('legacy.html')


@app.route("/api/catalog")
def catalog():
    return jsonify(get_catalog())


@app.route("/api/search")
def search():
    return jsonify({
        "results": search_indicators(
            query=request.args.get("q", ""),
            theme=request.args.get("theme"),
        )
    })


@app.route("/api/indicator/<indicator_id>")
def indicator(indicator_id):
    payload = get_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/indicator/<indicator_id>/year/<int:year>")
def indicator_year(indicator_id, year):
    payload = get_indicator_year(indicator_id, year)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')
