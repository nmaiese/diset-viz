from app import app
from flask import render_template
import csv, io, os

@app.route('/hello')
def index():
    return "Hello"

@app.route("/")
def main():

    filepath = os.path.join(os.path.dirname(__file__),'static/data/Assoluti_Regione.csv')
    with io.open(filepath, 'rb') as f:
        reader = csv.DictReader(f, delimiter=";")
        return render_template('index.html', data=list(reader))

