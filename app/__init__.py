from flask import Flask, jsonify, redirect, render_template, request
from flask_compress import Compress

from app import config
from app.cache import cache

app = Flask(__name__, static_url_path="/static")

Compress(app)
cache.init_app(app)


@app.before_request
def redirect_www_to_apex():
    host_header = request.host
    host_name, sep, port = host_header.partition(":")
    if not host_name.lower().startswith("www."):
        return None

    target_host = host_name[4:] + (sep + port if port else "")
    scheme = "https" if config.SITE_URL.startswith("https://") else request.scheme
    target_url = request.url.replace(f"{request.scheme}://{host_header}", f"{scheme}://{target_host}", 1)
    return redirect(target_url, code=301)


@app.after_request
def add_security_headers(response):
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    request_path = request.path
    if (
        request_path == "/data"
        or request_path.startswith("/api/")
        or request_path in {"/legacy", "/legacy-reddito"}
    ):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.errorhandler(404)
def not_found(error):
    request_path = request.path
    if request_path == "/data" or request_path.startswith("/api/"):
        response = jsonify({"error": "not_found"})
        response.status_code = 404
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response

    return (
        render_template(
            "404.html",
            site_url=config.SITE_URL,
            site_name=config.SITE_NAME,
            canonical=f"{config.SITE_URL}{request_path}",
        ),
        404,
        {"X-Robots-Tag": "noindex, follow"},
    )


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
