from flask import Flask
from flask_compress import Compress

app = Flask(__name__, static_url_path='/static')
Compress(app)

from app import views
