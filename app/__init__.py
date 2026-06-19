from flask import Flask
from flask_compress import Compress

from app import config
from app.cache import cache

app = Flask(__name__, static_url_path="/static")

Compress(app)
cache.init_app(app)


@app.context_processor
def inject_site_config():
    return {
        "SITE_NAME": config.SITE_NAME,
        "SITE_URL": config.SITE_URL,
        "GA_MEASUREMENT_ID": config.GA_MEASUREMENT_ID,
        "ADSENSE_CLIENT": config.ADSENSE_CLIENT,
        "ADSENSE_SLOT_BANNER": config.ADSENSE_SLOT_BANNER,
        "ENABLE_CONSENT_BANNER": config.ENABLE_CONSENT_BANNER,
        "GOOGLE_SITE_VERIFICATION": config.GOOGLE_SITE_VERIFICATION,
        "BING_SITE_VERIFICATION": config.BING_SITE_VERIFICATION,
    }


from app import views
