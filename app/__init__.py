import hashlib
import os
import secrets
from functools import lru_cache

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_compress import Compress

from app import config
from app import agent_discovery
from app.cache import cache

app = Flask(__name__, static_url_path="/static")
# Without SECRET_KEY set in the environment, a fresh key is generated on every
# process start: quiz session tokens issued before a restart stop validating.
# Fine for local dev, must be set explicitly in production.
app.secret_key = config.SECRET_KEY or secrets.token_hex(32)

Compress(app)
cache.init_app(app)


@lru_cache(maxsize=64)
def _asset_hash(rel):
    """Hash breve del contenuto di un file statico, per il cache-busting. In
    cache per la vita del processo: un deploy ricrea il processo (immagine nuova),
    quindi l'hash si aggiorna a ogni rilascio."""
    try:
        with open(os.path.join(app.static_folder, rel), "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:10]
    except OSError:
        return ""


def asset_url(filename):
    """`url_for('static')` più un `?v=<hash>` sul contenuto. Gli entry bundle
    (index.js, game.js, site.js) hanno nome fisso ma i chunk che importano hanno
    hash che cambiano: senza cache-busting, un browser con l'entry vecchio in
    cache importa chunk spariti e la SPA resta bianca dopo un deploy. Il query
    param rende l'URL unico per rilascio."""
    ver = _asset_hash(filename)
    return url_for("static", filename=filename, v=ver) if ver else url_for("static", filename=filename)


app.jinja_env.globals["asset_url"] = asset_url


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


_NOINDEX_EXACT_PATHS = {
    "/data", "/legacy", "/legacy-reddito", "/quiz/classifica", "/openapi.json",
    "/_keepalive", "/account",
}
_NOINDEX_PATH_PREFIXES = ("/api/", "/download/", "/.well-known/")


def _supabase_connect_origins():
    # Supabase Auth (fetch REST) e Realtime (websocket) verso il progetto: vanno
    # in connect-src, altrimenti la CSP blocca login e tick della console. Il
    # client @supabase/supabase-js è bundlato in locale, quindi script-src non
    # cambia. Vuoto se Supabase non è configurato.
    url = (config.SUPABASE_URL or "").strip().rstrip("/")
    if "://" not in url:
        return ""
    host = url.split("://", 1)[1]
    return f" https://{host} wss://{host}"


def _build_content_security_policy():
    # Divario Italia usa ancora diversi inline script nei template server-side,
    # quindi una CSP strict a nonce richiederebbe una refactor più ampia.
    # Per ora teniamo una allowlist esplicita che lascia lavorare GTM, GA4,
    # AdSense, Iubenda, i font Google e Tag Assistant senza blocchi.
    supabase = _supabase_connect_origins()
    return "; ".join(
        [
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "form-action 'self'",
            "frame-ancestors 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://*.googletagmanager.com https://tagmanager.google.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.google.com https://*.google.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net https://www.googletagservices.com https://*.adtrafficquality.google https://ep2.adtrafficquality.google https://embeds.iubenda.com https://cdn.iubenda.com https://cs.iubenda.com https://idb.iubenda.com https://www.iubenda.com https://static.cloudflareinsights.com",
            "script-src-elem 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://*.googletagmanager.com https://tagmanager.google.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.google.com https://*.google.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net https://www.googletagservices.com https://*.adtrafficquality.google https://ep2.adtrafficquality.google https://embeds.iubenda.com https://cdn.iubenda.com https://cs.iubenda.com https://idb.iubenda.com https://www.iubenda.com https://static.cloudflareinsights.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.googletagmanager.com https://tagmanager.google.com https://embeds.iubenda.com https://cdn.iubenda.com https://cs.iubenda.com https://www.iubenda.com",
            "img-src 'self' data: blob: https://www.googletagmanager.com https://*.googletagmanager.com https://tagmanager.google.com https://ssl.gstatic.com https://www.gstatic.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.google.com https://*.google.com https://www.google.it https://*.google.it https://googleads.g.doubleclick.net https://pagead2.googlesyndication.com https://stats.g.doubleclick.net https://*.adtrafficquality.google https://ep1.adtrafficquality.google https://idb.iubenda.com https://*.cloudflareinsights.com",
            "font-src 'self' data: https://fonts.gstatic.com",
            "connect-src 'self' https://www.googletagmanager.com https://*.googletagmanager.com https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.google.com https://*.google.com https://googleads.g.doubleclick.net https://pagead2.googlesyndication.com https://ad.doubleclick.net https://stats.g.doubleclick.net https://*.adtrafficquality.google https://ep1.adtrafficquality.google https://cdn.iubenda.com https://idb.iubenda.com https://cpl.iubenda.com https://cs.iubenda.com https://embeds.iubenda.com https://static.cloudflareinsights.com" + supabase,
            "frame-src 'self' https://www.googletagmanager.com https://tagmanager.google.com https://googleads.g.doubleclick.net https://pagead2.googlesyndication.com https://tpc.googlesyndication.com https://www.google.com https://*.google.com https://*.googletagmanager.com https://*.adtrafficquality.google https://ep2.adtrafficquality.google https://www.iubenda.com https://*.iubenda.com",
        ]
    )


@app.after_request
def add_security_headers(response):
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = _build_content_security_policy()
    request_path = request.path
    if request_path in _NOINDEX_EXACT_PATHS or request_path.startswith(_NOINDEX_PATH_PREFIXES):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    elif "X-Robots-Tag" not in response.headers:
        # Default-deny: force an explicit index signal on every public response
        # unless something upstream (the 404 handler) already set its own
        # X-Robots-Tag. Without this, a Cloudflare-injected restrictive default
        # can silently noindex any path (this is what happened to /blog and
        # /indicatore/* before 2026-07-12) with nothing in our own responses to
        # override it.
        response.headers["X-Robots-Tag"] = "index, follow, max-snippet:-1, max-image-preview:large"

    # Every HTML page exposes the same machine-readable entry points. Relative
    # targets survive the apex/www redirect and local test hosts, while the
    # registered relations remain parseable without inspecting the markup.
    if response.status_code == 200 and (request.path == "/" or response.mimetype == "text/html"):
        for link_value in agent_discovery.discovery_link_values():
            response.headers.add("Link", link_value)

    # Both variants must carry Vary, including cached HTML. Markdown responses
    # already set it in their constructor, but adding the value is idempotent.
    if response.status_code == 200 and agent_discovery.markdown_available(request.path):
        response.vary.add("Accept")
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
        "GOOGLE_SITE_VERIFICATION": config.GOOGLE_SITE_VERIFICATION,
        "BING_SITE_VERIFICATION": config.BING_SITE_VERIFICATION,
        # Identità Supabase pubbliche (Auth Google + Realtime): nei template
        # così cambiarle non richiede un rebuild del frontend. Vuote = auth off.
        "SUPABASE_URL": config.SUPABASE_URL,
        "SUPABASE_ANON_KEY": config.SUPABASE_ANON_KEY,
    }


from app import views as views
from app import profiles
from app.seo_policy import is_search_indexable_indicator as _seo_indicator_policy

_original_indicator_policy = profiles.is_search_indexable_indicator
profiles.is_search_indexable_indicator = lambda item: _seo_indicator_policy(_original_indicator_policy, item)
