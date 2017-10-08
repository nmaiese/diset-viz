from app import app
from flask import render_template
from collections import OrderedDict
import csv, io, os


@app.route('/hello')
def index():
    return "Hello"

@app.route("/")
def main():

    filepath = os.path.join(os.path.dirname(__file__),'static/data/Assoluti_Regione.csv')
    with io.open(filepath, 'r', encoding='ISO-8859-1') as f:
        reader = csv.DictReader(f, delimiter=";")
        data = [dict(x) for x in reader]
        return render_template('index.html', data=data)

