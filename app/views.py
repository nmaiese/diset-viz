from app import app
from flask import render_template


@app.route('/hello')
def index():
    return "Hello"

@app.route("/")
def main():
    return render_template('index.html')

