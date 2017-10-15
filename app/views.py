from app import app
from app.cache import cache

from flask import render_template, send_from_directory
from flask.json import jsonify

import csv, os



@cache.memoize(timeout=100)
def get_all_data():
    filepath = os.path.join(os.path.dirname(__file__),'static/data/Assoluti_Regione.csv')
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
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')

