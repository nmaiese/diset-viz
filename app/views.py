from app import app
from app.cache import cache

from flask import render_template, send_from_directory
from flask.json import jsonify

import csv, os


@cache.cached(300, key_prefix='data')
@app.route("/data")
def data():
    filepath = os.path.join(os.path.dirname(__file__),'static/data/Assoluti_Regione.csv')
    with open(filepath, 'r', encoding='ISO-8859-1') as f:
        reader = csv.DictReader(f, delimiter=";")
        #data = [dict(x) for x in reader]
        return jsonify(list(reader))


@cache.cached(300, key_prefix='index')
@app.route("/")
def main():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')
