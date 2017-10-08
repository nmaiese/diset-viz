from flask import Flask
from flask_compress import Compress
from app.cache import cache

app = Flask(__name__, static_url_path='/static')


Compress(app)
cache.init_app(app)

from app import views
