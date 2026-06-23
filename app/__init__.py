from flask import Flask
from flask_compress import Compress

from app import config
from app.cache import cache

app = Flask(__name__, static_url_path="/static")

Compress(app)
cache.init_app(app)


@app.after_request
def add_security_headers(response):
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.context_processor
def inject_site_config():
    return {
        "SITE_NAME": config.SITE_NAME,
        "SITE_URL": config.SITE_URL,
        "GA_MEASUREMENT_ID": config.GA_MEASUREMENT_ID,
        "GOOGLE_TAG_MANAGER_ID": config.GOOGLE_TAG_MANAGER_ID,
        "ADSENSE_CLIENT": config.ADSENSE_CLIENT,
        "ADSENSE_SLOT_BANNER": config.ADSENSE_SLOT_BANNER,
        "FORCE_FUNDING_CHOICES_CMP": config.FORCE_FUNDING_CHOICES_CMP,
        "ENABLE_CONSENT_BANNER": config.ENABLE_CONSENT_BANNER,
        "GOOGLE_SITE_VERIFICATION": config.GOOGLE_SITE_VERIFICATION,
        "BING_SITE_VERIFICATION": config.BING_SITE_VERIFICATION,
    }


from app import views
