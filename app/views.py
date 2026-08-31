from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts, posts_for_indicator
from app.data import get_catalog
from app.atlas_catalog import (
    all_atlas_themes_index,
    atlas_themes_by_macro_area,
    catalog_summary,
    get_atlas_catalog,
    get_atlas_indicator,
    get_atlas_indicator_year,
    get_atlas_theme_profile,
    search_atlas_indicators,
)
from app import divari
from app import profiles
from app import sources
from app import seo_policy
from app import indicator_notes
from app import indicator_texts
from app import indicator_universe
from app import indicator_view
from app import editorial_state
from app import quality_life_bes as qb
from app.quality_life_config import QUALITY_LIFE_PROFILES
from app import bes_data
from app import multiscopo_data
from app import external_atlas
from app import external_manifest
from app import game
from app import quiz
from app import quiz_tokens
from app import leaderboard
from app import auth
from app import moderation
from app import public_urls
from app import publisher
from app import agent_discovery
from app.taxonomy import DUPLICATE_BES_IDS, PROVINCE_ONLY_TITLE_COLLISIONS

from flask import Response, abort, make_response, redirect, render_template, request, send_from_directory, url_for
from flask.json import jsonify

import csv, hmac, io, json, os, re, time, unicodedata
import threading
from functools import lru_cache
from urllib.parse import quote_plus

from app import config


_HOME_FEATURED_INDICATORS = ("901", "104", "105", "910")

# Indicators shown as the selectable choropleth in the homepage map hero.
# Same flagship set used elsewhere (llms.txt, the /atlante SEO fallback), so
# "featured" means the same thing everywhere on the site.
_HOME_MAP_INDICATORS = _HOME_FEATURED_INDICATORS

# Indicators behind the "Storie dai dati" cards: real, already-published
# indicators (three overlap with existing blog posts) with a declared
# higher_better/lower_better direction, so "guida"/"resta indietro" framing is
# supported by the data instead of asserted for a contextual indicator.
_HOME_STORY_INDICATORS = ("901", "408", "910", "102")

# "Confronta" preview: a North / Centre / South contrast on three scoreable
# indicators (PIL pro capite, NEET, speranza di vita), so bars and ranking are
# something the data supports rather than a placeholder.
_HOME_COMPARE_INDICATORS = ("901", "408", "910")
_HOME_COMPARE_REGIONS = ("lombardia", "lazio", "campania")
_HOME_COMPARE_COLORS = ("var(--ink)", "var(--accent)", "var(--positive-ink)")

# --- Homepage 2026 design system ------------------------------------------
# The indicator whose regional time series drives the homepage comparison
# module, and the regions offered as toggles. Three are selected on load; the
# module accepts at most three at a time, like /confronto.
_HOME_SERIES_INDICATOR = "901"
_HOME_SERIES_CHOICES = (
    "lombardia", "emilia-romagna", "lazio", "campania", "sicilia", "piemonte",
)
_HOME_SERIES_DEFAULT = ("lombardia", "lazio", "campania")

# Categorical data-viz palette (tokens --cat-1..4). Series colours, not brand:
# a line's colour identifies a region, it does not rate it.
_HOME_SERIES_COLORS = ("var(--cat-1)", "var(--cat-2)", "var(--cat-3)", "var(--cat-4)")

# Sequential teal ramp of the 2026 design system. These are emitted as CSS
# custom properties, not as hex: --seq-1..6 are redefined under
# <html data-theme="dark">, so a baked colour would leave the choropleth stuck
# on the light ramp while the rest of the page goes dark. Every page still on
# the legacy stylesheet keeps the old blue ramp until it is migrated in turn.
_DS_SEQ_RAMP = tuple(f"var(--seq-{step})" for step in range(1, 7))

# Production contract consumed by scripts/audit_public_discoverability.py.  Keep
# this literal (rather than deriving it inside the audit): app/views.py owns the
# public routes and the external check must fail when what is deployed no longer
# matches that contract.  ``marker`` is visible without running JavaScript and
# therefore also proves that the useful part of each page is server-rendered.
PUBLIC_DISCOVERABILITY_EXPECTATIONS = {
    "site_url": "https://divarioitalia.it",
    "index_header": "index, follow, max-snippet:-1, max-image-preview:large",
    "machine_header": "noindex, nofollow, noarchive",
    "link_relations": ("api-catalog", "service-doc", "service-desc"),
    "pages": (
        {"path": "/robots.txt", "content_type": "text/plain", "marker": "User-agent: *", "kind": "robots"},
        {"path": "/sitemap.xml", "content_type": "application/xml", "marker": "<urlset", "kind": "document"},
        {"path": "/llms.txt", "content_type": "text/plain", "marker": "# Divario Italia", "kind": "document"},
        {"path": "/llms-full.txt", "content_type": "text/plain", "marker": "# Divario Italia", "kind": "document"},
        {"path": "/.well-known/api-catalog", "content_type": "application/linkset+json", "marker": "\"linkset\"", "kind": "document", "x_robots": "noindex, nofollow, noarchive"},
        {"path": "/openapi.json", "content_type": "application/json", "marker": "\"openapi\"", "kind": "document", "x_robots": "noindex, nofollow, noarchive"},
        {"path": "/.well-known/agent-skills/index.json", "content_type": "application/json", "marker": "\"skills\"", "kind": "document", "x_robots": "noindex, nofollow, noarchive"},
        {"path": "/.well-known/agent-skills/query-divario-italia/SKILL.md", "content_type": "text/markdown", "marker": "# Consultare Divario Italia", "kind": "document", "x_robots": "noindex, nofollow, noarchive"},
        {"path": "/", "content_type": "text/html", "marker": "Un atlante per leggere l'Italia", "kind": "html", "markdown_marker": "# Divario Italia"},
        {"path": "/atlante", "content_type": "text/html", "marker": "Atlante degli indicatori territoriali italiani", "kind": "html", "markdown_marker": "# Atlante degli indicatori territoriali italiani"},
        {"path": "/catalogo-dati", "content_type": "text/html", "marker": "Catalogo dati di Divario Italia", "kind": "html", "markdown_marker": "# Catalogo dati di Divario Italia"},
        {"path": "/blog", "content_type": "text/html", "marker": "Analisi brevi e basate sui dati", "kind": "html", "markdown_marker": "# Storie dai dati"},
        {"path": "/blog/pil-pro-capite-regioni-divario-2024", "content_type": "text/html", "marker": "PIL pro capite per regione", "kind": "html", "markdown_marker": "# PIL pro capite per regione"},
        {"path": "/metodologia", "content_type": "text/html", "marker": "Metodologia e fonti", "kind": "html", "markdown_marker": "# Metodologia e fonti"},
        {"path": "/indicatore/tasso-di-turisticita/ter-105", "content_type": "text/html", "marker": "page-indicator", "kind": "html", "markdown_marker": "# Tasso di turisticità"},
        {"path": "/regione/lombardia", "content_type": "text/html", "marker": "page-region", "kind": "html", "markdown_marker": "# Lombardia: profilo territoriale"},
        {"path": "/tema/lavoro-e-conciliazione", "content_type": "text/html", "marker": "page-theme", "kind": "html", "markdown_marker": "# Lavoro e conciliazione"},
    ),
    "robots": {
        "shared_disallow": ("/api/", "/data", "/legacy", "/legacy-reddito"),
        "answer_bots": ("OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User", "Claude-SearchBot", "Claude-User", "Google-Extended"),
        "training_bots": ("Amazonbot", "Applebot-Extended", "Bytespider", "CCBot", "ClaudeBot", "CloudflareBrowserRenderingCrawler", "GPTBot", "meta-externalagent"),
    },
}


@app.context_processor
def _inject_license():
    """Licenza dei dati in ogni template, presa da `app/sources.py`.

    Il JSON-LD della pagina regione, quello della classifica e la FAQ della
    metodologia dicono tutti la stessa cosa: se la scrivono ognuno per conto suo,
    la prossima correzione ne trova due su tre. `data_licenses_label` è una
    funzione perché la classifica sa solo a render time quali famiglie sono
    davvero nel punteggio."""
    return {
        "data_license_url": sources.LICENSE_URL,
        "data_license_label": sources.LICENSE_LABEL,
        "data_licenses_label": sources.licenses_label,
        "publisher": publisher.ORGANIZATION,
        "publisher_jsonld": publisher.organization_json(),
        "corrections_url": publisher.CORRECTIONS_URL,
    }


def _client_ip():
    """IP del client, rispettando X-Forwarded-For dietro il proxy Cloud Run."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_limit_ok(bucket, limit, window_s):
    """Rate limit a finestra fissa, in-process, appoggiato alla cache dell'app.
    Per-worker (leggermente lasco con più worker), senza dipendenze esterne né Redis:
    sufficiente a frenare lo spam su un endpoint pubblico di logging."""
    now = time.time()
    key = f"rl:{bucket}"
    entry = cache.get(key)
    if entry is None or now - entry[0] >= window_s:
        cache.set(key, (now, 1), timeout=window_s)
        return True
    start, count = entry
    if count >= limit:
        return False
    cache.set(key, (start, count + 1), timeout=window_s)
    return True


@app.template_filter("it_num")
def it_num(value, decimals=1):
    """Format a number Italian-style: dot thousands, comma decimals."""
    if value is None:
        return "n.d."
    try:
        formatted = f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


@app.template_filter("it_plural")
def it_plural_filter(count, singular, plural):
    """Italian singular/plural agreement for a count: `{{ n | it_plural('regione',
    'regioni') }}`. Delegates to the shared helper so prose and templates agree."""
    return indicator_notes.it_plural(count, singular, plural)


def _markdown_html(text):
    """Prose with inline markdown links, rendered to safe HTML."""
    import markdown as _markdown
    from markupsafe import Markup

    if not text:
        return ""
    return Markup(_markdown.markdown(str(text), output_format="html5").strip())


@app.template_filter("analyst_html")
def analyst_html(text):
    """An inline fragment, for a template that already opened a <p>.

    Strips the single wrapping <p>, because nesting one inside another is
    invalid HTML and the browser closes the outer one early. Use it only where
    the template supplies the block element, which today is the page lead.
    """
    html = str(_markdown_html(text))
    if not html:
        return ""
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        from markupsafe import Markup

        return Markup(html[3:-4])
    return _markdown_html(text)


@app.template_filter("prose_html")
def prose_html(text):
    """Block content that supplies its own paragraphs. Nothing is stripped.

    The article sections used `analyst_html`, which was written for the old
    analyst note that sat inside a <p> the template had already opened. The
    section body does not: the macro emits it directly into the article div. So
    a section of a single paragraph lost its wrapper and rendered as a bare text
    node, and `.prose > * + *` in site.css gives its 1.1em only to *elements*.
    The result was a one-paragraph section pinned to its own h2 while the
    multi-paragraph ones below it kept the gap, on 710 sections across 355 of
    the 364 articles. Invisible in the JSON, invisible in the diff, and visible
    on every page.
    """
    return _markdown_html(text)


@app.template_filter("sparkline")
def sparkline(series, width=140, height=36):
    """Inline SVG sparkline for a {year, value} series, server-side.

    The React atlas has its own <Sparkline> component, but the indicator page is
    server-rendered Jinja: this emits the same shape (a polyline plus a dot on
    the last point, styled by .spark in site.css) without a second bundle. The
    viewBox is fixed and CSS sizes it; a flat series draws a centred line.
    """
    from markupsafe import Markup
    points = [p for p in (series or []) if p.get("value") is not None]
    if len(points) < 2:
        return Markup("")
    values = [p["value"] for p in points]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    # Inset on every side so the 2px stroke and the end dot never cross the box
    # (the card container also clips with overflow:hidden as a safety net).
    m = 4.0
    inner_w = width - 2 * m
    inner_h = height - 2 * m
    n = len(points)
    coords = [
        (
            m + (i / (n - 1)) * inner_w,
            m + inner_h * (1 - (0.5 if hi == lo else (p["value"] - lo) / span)),
        )
        for i, p in enumerate(points)
    ]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    lx, ly = coords[-1]
    return Markup(
        f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'aria-hidden="true" focusable="false">'
        f'<polyline class="spark__line" fill="none" points="{poly}"/>'
        f'<circle class="spark__dot" cx="{lx:.1f}" cy="{ly:.1f}" r="2"/>'
        f'</svg>'
    )


def get_all_data():
    filepath = os.path.join(os.path.dirname(__file__), 'static/data/Assoluti_Regione.csv')
    with open(filepath, 'r', encoding='utf8') as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


@app.route("/data")
def data():
    # /data is the full CSV (~111k rows, ~46 MB of JSON) consumed only by the
    # legacy D3 dashboard. It used to cache that whole 46 MB Response in each
    # worker's SimpleCache (standing memory) and memoize the raw row list on top.
    # Compression and encoding negotiation are already handled app-wide by
    # Flask-Compress (same as every /api/* route), so we only build the payload,
    # let Flask-Compress gzip it on the wire, and add Cache-Control so the browser
    # stops re-fetching it. Nothing large is held standing: the rows are built per
    # request and freed.
    response = jsonify(get_all_data())
    response.headers["Cache-Control"] = "public, max-age=600"
    return response


@app.route("/")
@cache.cached(timeout=300, query_string=True, unless=agent_discovery.prefers_markdown)
def home():
    # The federated catalog, not the territorial family alone: the themes below
    # already aggregate every source, so counting one family here made the same
    # page show two different sizes for the same catalog.
    summary = catalog_summary()
    total_indicators = summary["total"]
    featured = _home_featured_indicator_links()
    recent_posts = get_posts()[:3]
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.home_markdown(summary, featured, recent_posts, SITE_URL),
            f"{SITE_URL}/",
        )
    themes_preview = _home_themes_preview()
    return render_template(
        "home.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/",
        total_indicators=total_indicators,
        sources_label=summary["institutions_label"],
        year_min=summary["year_min"],
        year_max=summary["year_max"],
        themes_preview=themes_preview,
        qol=_home_qol_preview(),
        quiz_games=_home_quiz_games(),
        posts=recent_posts,
        # 2026 design system modules
        hero_map=_home_hero_map(),
        paths=_home_paths(summary, themes_preview),
        featured_story=_home_featured_story(),
        insight_cards=_home_insight_cards(),
        series_module=_home_series_module(),
        qol_module=_home_qol_module(),
        trust_cards=_home_trust_cards(summary),
    )


@app.route("/atlante")
@cache.cached(timeout=300, unless=agent_discovery.prefers_markdown)
def atlante():
    featured = _home_featured_indicator_links()
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.atlas_markdown(featured, SITE_URL),
            f"{SITE_URL}/atlante",
        )
    return render_template('app.html', featured_indicators=featured)


@app.route("/catalogo-dati")
@cache.cached(timeout=300, unless=agent_discovery.prefers_markdown)
def data_catalog():
    """Indexable, human-readable inventory behind the DataCatalog entity.

    Costruito dalla **stessa** proiezione di sitemap e llms-full
    (`_indexable_indicator_catalog`), non dal solo inventario regionale
    (`get_atlas_catalog`): quest'ultimo non vede gli indicatori BES con sole
    osservazioni provinciali, che però hanno una pagina indicizzabile ed entrano
    negli altri due export. Prenderli da fonti diverse lasciava decine di dataset
    validi fuori dal catalogo pubblico e dal suo grafo `DataCatalog.dataset`.
    """
    datasets = []
    for record in _indexable_indicator_catalog():
        meta = record["meta"]
        datasets.append({
            "name": meta["name"],
            "url": f"{SITE_URL}{meta['canonical_path']}",
            "path": meta["canonical_path"],
            "source": meta.get("source_label") or meta.get("family_label") or "",
        })
    description = (
        "Catalogo pubblico degli indicatori territoriali di Divario Italia, "
        "con schede, fonti e serie scaricabili."
    )
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.data_catalog_markdown(datasets, description, SITE_URL),
            f"{SITE_URL}/catalogo-dati",
        )
    catalog_jsonld = {
        "@context": "https://schema.org",
        "@type": "DataCatalog",
        "@id": f"{SITE_URL}/catalogo-dati#catalogo",
        "name": "Catalogo dati di Divario Italia",
        "description": description,
        "url": f"{SITE_URL}/catalogo-dati",
        # L'entità editore condivisa (con @id /chi-siamo#organizzazione), la
        # stessa delle schede indicatore e della pagina Chi siamo, non una seconda
        # Organization anonima: un solo publisher, collegato, in tutto il grafo.
        "publisher": publisher.ORGANIZATION,
        "dataset": [
            {"@type": "Dataset", "name": item["name"], "url": item["url"]}
            for item in datasets
        ],
    }
    return render_template(
        "data_catalog.html",
        datasets=datasets,
        catalog_description=description,
        catalog_jsonld=catalog_jsonld,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/catalogo-dati",
    )


@app.route("/divari-regionali")
@cache.cached(timeout=300, query_string=True)
def divari_regionali():
    """L'hub editoriale sui divari territoriali.

    Non è una seconda tassonomia sopra /temi e /regioni: quelle pagine servono a
    sfogliare, questa sostiene una tesi (il divario non è una linea sola) e la
    misura sul catalogo, ripartizione per ripartizione. Ogni numero in pagina è
    ricalcolato dai dati a ogni render, così la prosa non può invecchiare.
    """
    view = divari.build_divari_view()
    if view is None:
        abort(404)
    return render_template(
        "divari_regionali.html",
        divari=view,
        map_hero=_map_hero(divari.MAP_DIVARI),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/divari-regionali",
    )


@app.route("/confronto")
@cache.cached(timeout=300)
def confronto():
    """La casa canonica del comparatore.

    Il confronto tra regioni era solo uno stato della SPA (/atlante?view=confronto):
    funzionava, ma non aveva una URL da condividere né un titolo suo. Qui la
    pagina è server-rendered, quindi chi arriva senza JavaScript legge un
    confronto vero con numeri reali, e il bundle monta sopra la vista giusta.
    """
    return render_template(
        "confronto.html",
        compare_preview=_home_compare_preview(),
        featured_indicators=_home_featured_indicator_links(),
    )


@app.route("/legacy")
@cache.cached(timeout=300)
def legacy():
    return render_template('legacy.html')


@app.route("/legacy-reddito")
@cache.cached(timeout=300)
def legacy_reddito():
    return render_template('legacy_reddito.html')


@app.route("/api/catalog")
def catalog():
    return jsonify(get_atlas_catalog())


@app.route("/.well-known/api-catalog")
def api_catalog_discovery():
    """RFC 9727 Linkset for the deliberately small public data contract."""
    response = jsonify(agent_discovery.api_catalog_document(SITE_URL))
    response.headers["Content-Type"] = agent_discovery.api_catalog_content_type()
    response.headers.add(
        "Link",
        f'<{SITE_URL}/openapi.json>; rel="service-desc"; '
        'type="application/vnd.oai.openapi+json;version=3.1"',
    )
    response.headers.add(
        "Link",
        f'<{SITE_URL}/catalogo-dati>; rel="service-doc"; type="text/html"',
    )
    return response


@app.route("/openapi.json")
def openapi_spec():
    return jsonify(agent_discovery.openapi_document(SITE_URL))


@app.route("/.well-known/agent-skills/index.json")
def agent_skills_index():
    return jsonify(agent_discovery.skill_index_document(SITE_URL))


@app.route("/.well-known/agent-skills/query-divario-italia/SKILL.md")
def divario_agent_skill():
    return Response(
        agent_discovery.skill_text(),
        content_type="text/markdown; charset=utf-8",
    )


@app.route("/api/external-indicators/manifest")
def external_indicator_manifest_api():
    return jsonify({"manifest": external_manifest.rows()})


@app.route("/api/search")
def search():
    return jsonify({
        "results": search_atlas_indicators(
            query=request.args.get("q", ""),
            theme=request.args.get("theme"),
        )
    })


_SEARCH_PAGE_SIZE = 50
# Oltre questo tetto la ricerca smette di raccogliere: una query di una lettera
# altrimenti impaginerebbe l'intero catalogo, e nessuno arriva a pagina dodici.
_SEARCH_MAX_RESULTS = 300


def _search_fold(value):
    """Minuscolo, senza accenti, spazi compattati: la forma su cui confrontare."""
    folded = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.lower().split())


def _search_rank(title, secondary, query):
    """3 se la query apre il titolo, 2 se sta nel titolo, 1 se sta nel resto.

    Serve solo a ordinare, non a filtrare: chi cerca "neet" deve trovare in cima
    l'indicatore che si chiama NEET, non un articolo che lo nomina di passaggio.
    """
    title_folded = _search_fold(title)
    if title_folded.startswith(query):
        return 3
    if query in title_folded:
        return 2
    if query in _search_fold(secondary):
        return 1
    return 0


def _search_results(query):
    """Indicatori e articoli che rispondono alla query, ordinati per pertinenza."""
    folded = _search_fold(query)
    if not folded:
        return []

    results = []
    for item in search_atlas_indicators(query=query, limit=_SEARCH_MAX_RESULTS):
        explain = item.get("explain") or {}
        results.append({
            "kind": "indicatore",
            "kind_label": "Indicatore",
            "title": item["name"],
            "url": item["path"],
            "summary": explain.get("plain") or "",
            "meta": f"{item['theme']} · {item['catalog_family_label']} · ultimo anno {item['year_max']}",
            "rank": _search_rank(item["name"], f"{item['theme']} {explain.get('plain', '')}", folded),
        })

    for post in get_posts():
        haystack = " ".join([
            post["title"],
            post.get("description") or "",
            " ".join(post.get("tags") or []),
            re.sub(r"<[^>]+>", " ", post.get("body_html") or ""),
        ])
        if folded not in _search_fold(haystack):
            continue
        results.append({
            "kind": "articolo",
            "kind_label": "Articolo",
            "title": post["title"],
            "url": f"/blog/{post['slug']}",
            "summary": post.get("description") or "",
            "meta": f"Blog · {post['date'].strftime('%d.%m.%Y')} · {post['read_time']} min di lettura",
            "rank": _search_rank(post["title"], haystack, folded),
        })

    # Ordine stabile: prima la pertinenza, poi l'ordine in cui le due fonti li
    # hanno prodotti (catalogo per gli indicatori, data per gli articoli).
    results.sort(key=lambda row: -row["rank"])
    return results


@app.route("/ricerca")
def ricerca():
    """Ricerca interna server-rendered, `noindex, follow` per scelta.

    Uno spazio `?q=` è illimitato per costruzione: indicizzarlo produrrebbe un
    numero arbitrario di pagine sottili, ognuna un sottoinsieme di righe che
    esistono già sulle schede. Qui la pagina serve a chi cerca, non a Google:
    funziona senza JavaScript, si condivide, e i suoi link restano `follow`
    così l'equity scorre verso le pagine indicatore e gli articoli.
    """
    query = (request.args.get("q") or "").strip()
    try:
        page = max(1, int(request.args.get("pagina", 1)))
    except (TypeError, ValueError):
        page = 1

    results = _search_results(query)
    total = len(results)
    # Il tetto vale sulla raccolta degli indicatori: contare anche gli articoli
    # farebbe annunciare "ci fermiamo qui" con qualche risultato di anticipo.
    truncated = sum(1 for row in results if row["kind"] == "indicatore") >= _SEARCH_MAX_RESULTS
    pages = max(1, (total + _SEARCH_PAGE_SIZE - 1) // _SEARCH_PAGE_SIZE)
    page = min(page, pages)
    start = (page - 1) * _SEARCH_PAGE_SIZE
    visible = results[start:start + _SEARCH_PAGE_SIZE]

    canonical_query = f"?q={quote_plus(query)}" if query else ""
    canonical = f"{SITE_URL}/ricerca{canonical_query}"
    if page > 1:
        canonical = f"{canonical}{'&' if canonical_query else '?'}pagina={page}"

    response = make_response(render_template(
        "ricerca.html",
        query=query,
        results=visible,
        total=total,
        page=page,
        pages=pages,
        first_index=start + 1,
        last_index=start + len(visible),
        page_size=_SEARCH_PAGE_SIZE,
        truncated=truncated,
        indicator_count=sum(1 for row in results if row["kind"] == "indicatore"),
        post_count=sum(1 for row in results if row["kind"] == "articolo"),
        query_param=canonical_query,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=canonical,
    ))
    # L'after_request mette "index, follow" su tutto quello che non si dichiara:
    # qui l'header va scritto a mano, altrimenti la pagina direbbe noindex nel
    # meta e index nell'header.
    response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


def _pipeline_published_url(indicator_id):
    """L'URL assoluto e canonico della pagina pubblicata di un indicatore, o None.

    Riusa il path precomputato dal catalogo (`build_indicator_view`), preferito
    al ricalcolo dello slug come vuole `.claude/rules/app.md`. La view Flask può
    importare il catalogo, così `pipeline_monitor` resta stdlib-puro. Se l'id non
    si risolve, niente link invece di un errore: il cruscotto non deve cadere per
    una riga.

    Assoluto (SITE_URL + path), non relativo: `/_pipeline/console` è servita
    su `monitor.divarioitalia.it`, un host diverso dal dominio pubblico, quindi
    un path relativo risolverebbe il link sul host sbagliato invece di aprire
    la pagina canonica."""
    try:
        from app import indicator_view, sources
        family, raw_id = sources.split_internal_id(indicator_id)
        view = indicator_view.build_indicator_view(family, raw_id)
        path = (view or {}).get("meta", {}).get("canonical_path")
        return f"{SITE_URL}{path}" if path else None
    except Exception:  # noqa: BLE001
        return None


@app.route("/_pipeline")
def pipeline_dashboard():
    """La porta del cruscotto: manda alla console, che è il cruscotto.

    Non c'è una seconda pagina server-rendered, e non deve esserci: due viste
    sullo stesso stato divergono, e questa ha già divergiuto una volta.

    Protetta: se `PIPELINE_TOKEN` è impostato, serve solo con `?token=` giusto,
    altrimenti 404, non 403, perché una pagina interna non deve nemmeno
    confermare di esistere. Il noindex lo mette `add_security_headers` sul
    prefisso `/_pipeline`.
    """
    token = config.PIPELINE_TOKEN
    if token and request.args.get("token") != token:
        abort(404)
    return redirect(url_for("pipeline_console"))


@app.route("/_pipeline/console")
def pipeline_console():
    """La console di monitoraggio in tempo reale (Supabase Realtime). Sostituisce
    il ?token= e il full-reload di /_pipeline: la guardia è il login Google
    ristretto via RLS su Postgres, non un segreto in URL. La pagina è servibile
    a chiunque (noindex per prefisso /_pipeline), ma senza la mail admin nel JWT
    la RLS non restituisce alcuna riga."""
    return render_template("pipeline_console.html", site_name=SITE_NAME,
                           monitor_admin_email=config.MONITOR_ADMIN_EMAIL)


# --- le due viste del cruscotto ----------------------------------------------
# Il vivo arriva alla console anche in push (Supabase Realtime sulle due tabelle,
# letto diritto dal browser). Questi endpoint servono la stessa storia già
# montata, dietro il confine mail-admin: la vista per workflow, e quella per
# indicatore, che è la stessa cosa guardata dall'altro lato.
#
# La cache sta su un helper memoizzato, non su `@cache.cached` della view: quel
# decoratore corto-circuita il corpo della view su un hit, saltando il controllo
# auth, e servirebbe il dato all'anonimo. Così invece l'auth gira sempre nella
# view, e solo la lettura si riusa per 30s.

# La forma dell'esito di `.claude/workflows/indicatore-lite.js`: `articoli` per
# quelli scritti, `fermati` per quelli che non hanno raggiunto il disco. Un
# indicatore fermato **non è** un guasto, e il cruscotto non deve confonderli.
def _articoli_da_esito(esito, run):
    """Le righe per-indicatore che una run ha prodotto.

    Derivate, non copiate in una tabella: il `result` del workflow le assembla
    già tutte, e una seconda copia in Postgres sarebbe una verità in più da
    tenere allineata. A questi volumi (poche run al giorno) la proiezione al
    momento della richiesta costa niente.
    """
    if not isinstance(esito, dict):
        return []
    comune = {"run_id": run.get("run_id"), "workflow": run.get("workflow"),
              "at": run.get("avviata_il"), "durata_ms": run.get("durata_ms"),
              "costo": run.get("costo"), "costo_pavimento": run.get("costo_pavimento")}
    righe = []
    for voce in esito.get("articoli") or []:
        if not isinstance(voce, dict):
            continue
        rilievi_aperti = voce.get("rilievi_aperti") or []
        righe.append({
            **comune,
            "indicatore": voce.get("codice") or "",
            "esito": "scritto con rilievi" if rilievi_aperti else "scritto",
            "scritto": bool(voce.get("scritto")),
            "sovrascritto": voce.get("sovrascritto"),
            "vintage_precedente": voce.get("vintage_precedente"),
            "percorso": voce.get("percorso"),
            "parole": voce.get("parole"),
            "impronta_prosa": voce.get("impronta_prosa"),
            "angolo": voce.get("angolo"),
            "giri_di_correzione": voce.get("giri_di_correzione"),
            "cifre_verificate": voce.get("cifre_verificate"),
            "sezioni": voce.get("sezioni") or [],
            "impaginazione": voce.get("impaginazione") or [],
            "rilievi": voce.get("rilievi") or [],
            "rilievi_aperti": rilievi_aperti,
            "motivo": None,
        })
    for voce in esito.get("fermati") or []:
        if not isinstance(voce, dict):
            continue
        righe.append({
            **comune,
            "indicatore": voce.get("codice") or "",
            "esito": "fermato",
            "scritto": False,
            "sovrascritto": None,
            "vintage_precedente": None,
            "percorso": None, "parole": None, "impronta_prosa": None,
            "angolo": (voce.get("bozza") or {}).get("angolo") if isinstance(voce.get("bozza"), dict) else None,
            "giri_di_correzione": voce.get("giri"),
            "cifre_verificate": (voce.get("verdetto") or {}).get("verificate")
            if isinstance(voce.get("verdetto"), dict) else None,
            "sezioni": [], "impaginazione": [], "rilievi": [],
            "rilievi_aperti": (voce.get("verdetto") or {}).get("smentite") or []
            if isinstance(voce.get("verdetto"), dict) else [],
            "motivo": voce.get("motivo"),
        })
    return righe


@cache.memoize(timeout=30)
def _pipeline_runs_payload():
    """Le run con dentro i loro agenti, la vista per workflow."""
    from app import pipeline_store
    return {"runs": pipeline_store.run()}


@cache.memoize(timeout=30)
def _pipeline_indicatori_payload():
    """La vista per indicatore: una riga per (indicatore, run), la più recente
    per prima, con il link alla pagina pubblica quando l'id si risolve."""
    from app import pipeline_store
    righe = []
    for run in pipeline_store.run():
        righe.extend(_articoli_da_esito(run.get("esito"), run))
    righe.sort(key=lambda r: (r.get("at") or ""), reverse=True)
    urls = {}
    for riga in righe:
        codice = riga["indicatore"]
        if codice and codice not in urls:
            urls[codice] = _pipeline_published_url(_id_da_codice(codice))
        riga["published_url"] = urls.get(codice)
    return {"indicatori": righe}


def _id_da_codice(codice):
    """`ter-105` -> `105`, `ims-MULTI_ABIT_AFFITTO` -> `multiscopo:MULTI_ABIT_AFFITTO`.

    I codici della catena usano l'acronimo col trattino, gli id del catalogo la
    **famiglia** con i due punti, e le due cose non coincidono: l'acronimo di
    `multiscopo` è `ims`. La traduzione la fa `app/sources.py`, che è l'unica
    verità su acronimi e famiglie.

    Scritto a mano la prima volta (`resto if famiglia == "ter" else
    f"{famiglia}:{resto}"`), sbagliava esattamente su `ims`, e sbagliava **in
    silenzio**: `_pipeline_published_url` inghiotte l'eccezione e restituisce
    None, quindi la riga usciva senza link invece che con un errore. È la stessa
    classe di difetto per cui `.claude/rules/app.md` vieta di hardcodare un
    prefisso, e che una volta ha pubblicato una serie Istat sotto il nome di
    Eurostat."""
    coppia = sources.parse_indicator_code(codice or "")
    if not coppia:
        return codice or ""
    return sources.internal_id(*coppia)


def _require_pipeline_admin():
    """Il confine mail-admin dei due endpoint. 404, non 403: un endpoint
    interno non conferma nemmeno di esistere, come `/_pipeline/beat`."""
    if not auth.is_admin(auth.current_user(request.headers)):
        abort(404)


@app.route("/_pipeline/api/runs")
def pipeline_api_runs():
    """Le run della catena, per workflow: fasi, agenti, modello, turni, token,
    costo ed esito di ognuno. Authed mail-admin."""
    _require_pipeline_admin()
    return jsonify(_pipeline_runs_payload())


@app.route("/_pipeline/api/indicatori")
def pipeline_api_indicatori():
    """La stessa storia per indicatore: che cosa è stato scritto o riscritto,
    con quale tesi, quanti giri, quali rilievi restano aperti, e se ha
    sovrascritto una pagina che esisteva. Authed mail-admin.

    Non è l'elenco degli indicatori, è **la storia delle run** su di essi: una
    riga esiste solo se una run l'ha prodotta, quindi qui si vedono gli ultimi
    due o tre. L'elenco è `/_pipeline/api/catalogo`."""
    _require_pipeline_admin()
    return jsonify(_pipeline_indicatori_payload())


def _stato_in_linea(riga, scritture):
    """`in linea` contro `scritto, non ancora in linea`, e quanto ne siamo certi.

    L'immagine servita porta `content/indicators/` **al commit del deploy**,
    mentre `pipeline_run.esito` può contenere un articolo scritto dopo: è
    l'unica differenza vera fra "scritto" e "pubblicato" in questo repo, dove
    `lab.pubblica` scrive direttamente sulla pagina pubblica e il merge è la
    pubblicazione.

    Si confronta l'**impronta della prosa** (`editorial_state.impronta`, che
    stampa anche `lab/pubblica.py`): lead più `sections[].{role,h,body}`, la
    stessa funzione dalle due parti, perché due definizioni diverse
    misurerebbero la differenza fra le definizioni invece che fra gli articoli.

    Le parole restano il **ripiego**, e con meno certezza: nessuna delle run già
    registrate porta l'impronta, e i conteggi dicono quanto, non che cosa. Due
    riscritture della stessa lunghezza si leggevano `in linea` con certezza
    `alta` mentre in produzione c'era ancora l'altra, cioè una pubblicazione in
    attesa che spariva dalla vista. Un conteggio **diverso** invece è una prova:
    di quella si può dire `alta`.

    `sovrascritto` e `vintage_precedente` non servono qui: un rimaneggiamento
    sullo stesso anno di dato lascia `vintage` identico anche dopo il deploy,
    quindi sembrano decisivi e non lo sono.
    """
    servito = bool(riga["scritte"]) or riga["lead"]
    scrittura = scritture.get(riga["codice"])
    if not servito:
        return ("scritto, non in linea", "esatta") if scrittura else ("mai scritto", "esatta")
    if scrittura is None:
        return "in linea", "assente"
    impronta_run = scrittura.get("impronta_prosa")
    if impronta_run and riga.get("impronta_prosa"):
        return (("in linea", "esatta") if impronta_run == riga["impronta_prosa"]
                else ("scritto, non in linea", "esatta"))
    parole_run = scrittura.get("parole")
    if parole_run is None:
        # La run non ha registrato niente di confrontabile, e `alta` direbbe che
        # si è guardato. `certezza` è un campo di prima classe proprio per non
        # sovrastimare quello che si sa.
        return "in linea", "assente"
    if parole_run == riga["parole"]:
        return "in linea", "debole"
    return "scritto, non in linea", "alta"


def _pipeline_catalogo_payload():
    """Tutti gli indicatori dell'atlante con il loro stato editoriale.

    La parte cara (la passata sui 634 e i rilievi) sta in
    `editorial_state.catalogo()`, in cache per la **vita del processo** perché è
    funzione pura del contenuto dell'immagine. Qui resta la sola giunzione con
    le run, che cambia mentre guardi.

    Niente `@cache.memoize` su questa: il backend è `simple`, che **pickla il
    valore**, e qui il valore è mezzo megabyte. Ripiccarlo ogni trenta secondi
    costerebbe più della giunzione che eviterebbe, che è un giro su un centinaio
    di run e la copia di 668 dizionari."""
    from app import pipeline_store

    base = editorial_state.catalogo()
    scritture, ultime = {}, {}
    for run in pipeline_store.run():
        for voce in _articoli_da_esito(run.get("esito"), run):
            codice = voce["indicatore"]
            if codice and codice not in scritture and voce["scritto"]:
                scritture[codice] = voce
            if codice and codice not in ultime:
                ultime[codice] = {"run_id": voce["run_id"], "at": voce["at"],
                                  "esito": voce["esito"]}
    righe = []
    for riga in base["righe"]:
        stato, certezza = _stato_in_linea(riga, scritture)
        ultima = ultime.get(riga["codice"])
        righe.append({**riga, "stato": stato, "certezza": certezza,
                      "url": f"{SITE_URL}{riga['percorso']}" if riga["percorso"] else None,
                      "ultima_run": (ultima or {}).get("run_id"),
                      "ultima_run_il": (ultima or {}).get("at")})
    predefinite = [r for r in righe if r["predefinito"]]
    totali = {**base["totali"],
              "in_linea": sum(1 for r in predefinite if r["stato"] == "in linea"),
              "scritti_non_in_linea": sum(1 for r in predefinite
                                          if r["stato"] == "scritto, non in linea"),
              "mai_scritti": sum(1 for r in predefinite if r["stato"] == "mai scritto")}
    return {"righe": righe, "totali": totali}


@app.route("/_pipeline/api/catalogo")
def pipeline_api_catalogo():
    """Tutti e 634 gli indicatori con una pagina, e che cosa è scritto di ognuno.

    Una riga per (indicatore, livello), che è l'unità della coda editoriale
    verbatim: 668 righe, di cui 634 al livello predefinito. Due unità diverse per
    la stessa cosa divergono. Authed mail-admin."""
    _require_pipeline_admin()
    return jsonify(_pipeline_catalogo_payload())


@app.route("/_keepalive")
def keepalive():
    """Ping schedulato (Cloud Scheduler) che tiene sveglio il progetto Supabase:
    dopo 7 giorni di inattività il free va in pausa, e con la Routine launcher
    in pausa nulla lo terrebbe caldo. Un SELECT 1 basta. Tollerante: risponde
    sempre 200, con lo stato del db, così lo scheduler non allarma per un
    guasto transitorio."""
    token = config.KEEPALIVE_TOKEN
    if token and not hmac.compare_digest(request.headers.get("X-Keepalive-Key", ""), token):
        abort(404)
    from sqlalchemy import text
    from app.db import get_engine
    status = "up"
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        status = "down"
    return jsonify({"ok": True, "db": status})


# Il protocollo della presa, in un posto solo: `ping` lo restituisce, e chi sta
# per spendere una run lo confronta con quello che ha intenzione di mandare.
PIPELINE_AZIONI = ("ping", "run", "agente", "consuntivo")


@app.post("/_pipeline/beat")
def pipeline_beat_ingest():
    """La presa del cruscotto: `lab/cruscotto.py` POSTa qui quello che legge.

    Non lo POSTa un agente della catena, ed è il punto: il monitoraggio non
    aggiunge un turno a nessuno. Il lettore gira di fianco al workflow, legge i
    trascritti che il runtime scrive comunque, e manda qui.

    Autenticato con `PIPELINE_INGEST_TOKEN` (header `X-Pipeline-Key`), come
    l'endpoint admin della leaderboard: segreto sbagliato o assente -> 404, non
    403, perché un endpoint interno non conferma nemmeno di esistere. Il corpo è
    JSON con un campo `action`:

      {"action":"ping"}
      {"action":"run","run_id":...,"fase_stimata":...,"agenti_visti":N,...}
      {"action":"agente","run_id":...,"agent_id":...,"agent_type":...,
       "stato_vivo":"aperto|chiuso","risultato":...}
      {"action":"consuntivo","run_id":...,"run":{...},"agenti":[{...}]}

    `run` e `agente` sono il **battito**, `consuntivo` è il consuntivo, e
    scrivono colonne disgiunte (vedi `app/pipeline_store.py`): possono arrivare
    in qualsiasi ordine, anche a rovescio, senza che l'una cancelli l'altra.

    `ping` **non scrive niente** ed esiste per questo. Chi sta per spendere una
    run vuole sapere tre cose prima di partire: che il segreto combaci, che
    l'immagine servita conosca il protocollo nuovo (una costruita da un master
    più vecchio risponde `bad_action` e perde ogni battito), e che cosa c'è già
    registrato. La domanda si faceva con un `run` finto, che però è un battito
    vero: lasciava una run fantasma in cima al cruscotto, senza agenti e per
    sempre in volo. Una domanda non deve avere effetti.

    E un `run_id` che non ha la forma di un runId viene rifiutato con 400
    (`pipeline_store.FORMA_RUN_ID`): la buona maniera non basta come difesa
    finché la porta accetta qualunque stringa, e `wf_precheck` è entrato due
    volte da lì.

    Best effort per chi chiama: un lettore che non riesce a postare non deve
    fermare niente, quindi qui si è tolleranti e si risponde presto.
    """
    token = config.PIPELINE_INGEST_TOKEN
    provided = request.headers.get("X-Pipeline-Key", "")
    if not token or not hmac.compare_digest(provided, token):
        abort(404)
    from app import pipeline_store
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    try:
        if action == "ping":
            # Elencare le azioni serve a chi chiama: sa se quello che sta per
            # mandare verra' capito, invece di scoprirlo mandandolo. E lo stato
            # serve perche' un controllo che risponde solo `ok` conferma il
            # segreto e nient'altro: chi lo chiama non ha nessun motivo di
            # preferirlo a una `run` finta, che invece lascia una riga fantasma.
            return jsonify({"ok": True, "azioni": PIPELINE_AZIONI,
                            "stato": pipeline_store.stato_presa()})
        if action == "run":
            pipeline_store.registra_run(payload.get("run_id", ""), payload)
        elif action == "agente":
            pipeline_store.registra_agente(
                payload.get("run_id", ""), payload.get("agent_id", ""), payload)
        elif action == "consuntivo":
            pipeline_store.registra_consuntivo(
                payload.get("run_id", ""), payload.get("run") or {},
                payload.get("agenti") or [])
        else:
            return jsonify({"error": "bad_action"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@app.route("/api/indicator/<indicator_id>")
def indicator(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/indicator/<indicator_id>/year/<int:year>")
def indicator_year(indicator_id, year):
    payload = get_atlas_indicator_year(indicator_id, year)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.post("/api/events")
def analytics_event():
    # Endpoint pubblico che scrive nei log: senza limite è vulnerabile a spam/abuso.
    if not _rate_limit_ok(f"events:{_client_ip()}", limit=30, window_s=60):
        abort(429)

    payload = request.get_json(silent=True) or {}
    name = _clean_event_name(payload.get("name"))
    if not name:
        abort(400)

    event = {
        "name": name,
        "path": _clean_event_value(payload.get("path")),
        "title": _clean_event_value(payload.get("title")),
        "params": _clean_event_params(payload.get("params")),
    }
    app.logger.info("analytics_event %s", json.dumps(event, ensure_ascii=False, sort_keys=True))
    return ("", 204)


@app.route("/blog")
def blog_index():
    posts = get_posts()
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.blog_index_markdown(posts, SITE_URL),
            f"{SITE_URL}/blog",
        )
    return render_template(
        "blog_list.html",
        posts=posts,
        tags=all_tags(),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/blog",
    )


@app.route("/blog/<slug>")
def blog_post(slug):
    post = get_post(slug)
    if post is None:
        abort(404)
    post = dict(post)
    if post.get("indicator"):
        indicator_payload = get_atlas_indicator(post["indicator"])
        if indicator_payload:
            meta = indicator_payload["metadata"]
            post["indicator_path"] = meta["path"]
            post["indicator_meta"] = meta
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.blog_post_markdown(post, SITE_URL),
            post["url"],
        )
    related = [p for p in get_posts() if p["slug"] != slug][:3]
    return render_template(
        "blog_post.html",
        post=post,
        related=related,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=post["url"],
    )


@app.route("/privacy")
def privacy():
    return render_template(
        "privacy.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/privacy",
    )


@app.route("/chi-siamo")
def about():
    return render_template(
        "about.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/chi-siamo",
    )


@app.route("/metodologia")
def methodology():
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.methodology_markdown(
                SITE_URL, sources.LICENSE_LABEL, sources.LICENSE_URL,
            ),
            f"{SITE_URL}/metodologia",
        )
    regioni = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    province = qb.build_bes_ranking("provincia", qb.DEFAULT_PROFILE)
    return render_template(
        "methodology.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/metodologia",
        methodology_regioni=regioni["methodology"] if regioni else None,
        methodology_province=province["methodology"] if province else None,
        categories=qb.get_quality_life_categories(),
        profiles=qb.get_quality_life_profiles(),
        quality_life_indicators=[
            item for item in get_atlas_catalog()["indicators"]
            if item["quality_life_scored"]
        ],
    )


@app.route("/indicatore/<first>")
@app.route("/indicatore/<first>/<second>")
def indicator_page(first, second=None):
    """Unified, keyword-first indicator page: /indicatore/<slug>/<acr>-<id>.

    The resolving code (ter/bes/ims/eur + id) is the LAST segment; the slug leads
    for SEO. Dispatch by family and 301 any legacy or non-canonical URL to the
    canonical form."""
    # New canonical: code is the last segment. Also tolerate the transitional
    # code-first order (/indicatore/<code>/<slug>) so nothing 404s mid-rollout.
    parsed = sources.parse_indicator_code(second if second is not None else first)
    if parsed is None and second is not None:
        parsed = sources.parse_indicator_code(first)
    if parsed is None:
        # Pre-migration territorial URL (single bare numeric id): 301 to canonical.
        raw_id = sources.legacy_territorial_id(first)
        if raw_id is None:
            abort(404)
        payload = get_atlas_indicator(raw_id)
        if payload is None:
            abort(404)
        return redirect(
            sources.indicator_url("territorial", raw_id, profiles.indicator_slug(payload["metadata"]["name"])),
            code=301,
        )
    family, raw_id = parsed
    return _render_indicator(family, raw_id)


def _query_map_for_article(query_map, article):
    """Il query_map del livello, adattato agli anchor che l'articolo rende davvero.

    `query_map` (da `indicator_view._query_map`) è per-livello e non conosce
    l'articolo, quindi punta sempre a `sezione-definizione` e `sezione-dinamica`.
    Con le sezioni variabili quegli H2 possono non esistere: la definizione va nel
    blocco "Come leggere" (anchor `come-leggere`), e una domanda su una sezione
    non resa si toglie invece di puntare nel vuoto. Per un articolo a quattro
    sezioni (i trecento esistenti) non cambia niente.
    """
    emitted = {section["role"] for section in article["sections"]}
    absorbed = bool(article.get("come_leggere"))
    out = []
    for question in query_map:
        target = question["target"]
        if question["intent"] == "definizione":
            target = "come-leggere" if absorbed else "sezione-definizione"
        elif question["intent"] == "confronto" and "dinamica" not in emitted:
            continue
        out.append({**question, "target": target})
    return out


def _render_indicator(family, raw_id):
    """The one indicator page, for every source family.

    Everything numeric comes from app/indicator_view.py, everything editorial
    from app/indicator_texts.py. This function only resolves the URL, picks the
    territorial level to render, and decides what search engines see.
    """
    view = indicator_view.build_indicator_view(family, raw_id)
    if view is None:
        abort(404)

    meta = view["meta"]
    if request.path != meta["canonical_path"]:
        # Keep the query string across the canonicalization hop, otherwise a
        # shared link with a decorative slug silently drops the exploration
        # state it was pointing at (?livello=provincia lands on the regions).
        target = meta["canonical_path"]
        if request.query_string:
            target = f"{target}?{request.query_string.decode('utf-8')}"
        return redirect(target, code=301)

    # ?livello= picks which territorial level is server-rendered, so a reader
    # without JavaScript can still reach the provincial view. It is an
    # exploration state of the same page, never a second indexable URL.
    requested = request.args.get("livello")
    level = next((item for item in view["levels"] if item["key"] == requested), view["levels"][0])

    article = indicator_texts.build_article(meta["id"], level["key"])
    # Le domande-navigazione puntano ad anchor dell'articolo, che con le sezioni
    # variabili non sono più fisse: se la definizione è assorbita dal blocco
    # "Come leggere", il suo intent punta là, e una domanda su una sezione che
    # l'articolo non rende come H2 si toglie invece di puntare nel vuoto.
    query_map = _query_map_for_article(level["query_map"], article)
    lead = article["lead"] or indicator_texts.composed_lead(meta, level)
    # The lead is the SERP description as well as the first thing on the page,
    # so the two can never describe the indicator differently.
    seo_description = indicator_notes.meta_description_from_attacco(lead)

    explore_state = seo_policy.has_explore_params(request.args)
    noindex = (not meta["indexable"]) or explore_state

    if agent_discovery.prefers_markdown():
        response = agent_discovery.markdown_response(
            agent_discovery.indicator_markdown(meta, level, article, SITE_URL),
            f"{SITE_URL}{meta['canonical_path']}",
        )
        if noindex:
            response.headers["X-Robots-Tag"] = "noindex, follow"
        return response

    # A handful of BES ids are exact duplicates of an existing territorial
    # series (DUPLICATE_BES_IDS docstring): hidden from browsing, but the page
    # itself stays reachable and indexable, so its <title> must not collide
    # with its territorial twin's. Stays within the normal 60-char budget like
    # every other title, same as the crawler flags on any other page.
    if family == "bes" and raw_id in DUPLICATE_BES_IDS:
        source_qualifier = sources.family_short_label(family)
    # A handful of BES ids exist only at province level but share a name with a
    # regional twin (PROVINCE_ONLY_TITLE_COLLISIONS docstring): the same
    # collision as above, on the level dimension instead of the source, because
    # the title tail below is fixed to "per regione" regardless of the page's
    # actual level.
    elif family == "bes" and raw_id in PROVINCE_ONLY_TITLE_COLLISIONS:
        source_qualifier = "dati provinciali"
    else:
        source_qualifier = None

    # Titolo H1 e SERP: autorati se il file dell'articolo li porta, altrimenti il
    # derivato di oggi (H1 = nome amministrativo, title = boilerplate "per regione").
    # Un titolo autorato passa comunque dal budget SEO: `authored_seo_title` clampa
    # a `_TITLE_MAX` come il derivato, non è una scusa per sforare.
    page_h1 = article["h1"] or meta["name"]
    if article["seo_title"] or article["h1"]:
        seo_title_value = indicator_notes.authored_seo_title(
            article["seo_title"] or article["h1"], SITE_NAME,
            source_qualifier=source_qualifier,
        )
    else:
        seo_title_value = indicator_notes.seo_title(
            meta["name"], SITE_NAME, source_qualifier=source_qualifier
        )

    response = make_response(render_template(
        "indicator_page.html",
        meta=meta,
        levels=view["levels"],
        level=level,
        query_map=query_map,
        page_h1=page_h1,
        related=view["related"],
        related_posts=posts_for_indicator(meta["id"]),
        siblings=view["siblings"],
        explore=view["explore"],
        page_article=article,
        page_lead=lead,
        noindex=noindex,
        seo_title=seo_title_value,
        seo_description=seo_description,
        dataset_description=_dataset_description(lead, meta),
        dataset_updated=publisher.dataset_updated(meta["family"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{meta['canonical_path']}",
    ))
    if noindex:
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


def _dataset_description(lead, meta):
    """Dataset JSON-LD description, kept in step with the visible page.

    It used to concatenate two procedural sentences that appeared nowhere on the
    page. Now it is the lead the reader actually sees, with the plain definition
    as the fallback for indicators that have no written lead yet.
    """
    plain = (meta["explain"].get("plain") or "").strip()
    return lead or plain or meta["name"]


@app.route("/regione/<region_key>")
def region_page(region_key):
    profile = profiles.region_profile(region_key)
    if profile is None:
        abort(404)
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.region_markdown(profile, SITE_URL),
            f"{SITE_URL}/regione/{region_key}",
        )
    return render_template(
        "region_page.html",
        profile=profile,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/regione/{region_key}",
    )


@app.route("/api/regions/overview")
def regions_overview_api():
    """Compact per-region summary for the SPA 'per regioné selection map.

    Same source as the /regioni page; no overall regional score is exposed here.
    """
    return jsonify(profiles.regions_overview())


@app.route("/api/region/<region_key>")
def region_api(region_key):
    """JSON del profilo regione, per la vista 'per regioné della SPA.

    Riusa la stessa funzione che alimenta la pagina server /regione/<key>, così
    atlante interattivo e pagina SEO restano coerenti su un'unica fonte dati.
    L'after_request in app/__init__.py aggiunge già X-Robots-Tag: noindex.
    """
    profile = profiles.region_profile(region_key)
    if profile is None:
        abort(404)
    return jsonify(profile)


@app.route("/tema/<theme_slug>")
def theme_page(theme_slug):
    profile = get_atlas_theme_profile(theme_slug)
    if profile is None:
        abort(404)
    if request.path != profile["theme_path"]:
        return redirect(profile["theme_path"], code=301)
    if agent_discovery.prefers_markdown():
        return agent_discovery.markdown_response(
            agent_discovery.theme_markdown(profile, SITE_URL),
            f"{SITE_URL}{profile['theme_path']}",
        )
    return render_template(
        "theme_page.html",
        profile=profile,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}{profile['theme_path']}",
    )


@app.route("/regioni")
def regions_index():
    overview = profiles.regions_overview()
    regions = list(overview.values())
    return render_template(
        "regions_index.html",
        regions=regions,
        overview=overview,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/regioni",
    )


@app.route("/temi")
def themes_index():
    areas = _themes_index_areas()
    indicators = get_catalog()["indicators"]
    total = len(indicators)
    return render_template(
        "themes_index.html",
        areas=areas,
        total=total,
        theme_total=sum(area["theme_count"] for area in areas),
        year_min=min(item["year_min"] for item in indicators),
        year_max=max(item["year_max"] for item in indicators),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/temi",
    )


# User-facing URL level (plural) -> engine level (singular).
URL_LEVEL = public_urls.QUALITY_LIFE_LEVELS


def _quality_life_profile_arg():
    """Resolve the requested profile slug from ?profilo= (or ?profile=)."""
    return request.args.get("profilo") or request.args.get("profile") or qb.DEFAULT_PROFILE


def _profile_suffix(slug):
    return "" if slug == qb.DEFAULT_PROFILE else f"?profilo={slug}"




@app.route("/download/indicator/<indicator_id>.csv")
def indicator_download_csv(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    meta = payload["metadata"]
    rows = []
    for point in payload["series"]:
        rows.append({
            "indicator_id": indicator_id,
            "indicator": meta["name"],
            "theme": meta["theme"],
            "region": point["region"],
            "region_key": point["region_key"],
            "year": point["year"],
            "value": point["value"],
            "unit": meta["unit"],
            "source": meta["source_label"] or meta["source"],
            "source_url": meta["source_url"],
        })
    return _csv_response(
        rows,
        ["indicator_id", "indicator", "theme", "region", "region_key", "year", "value", "unit", "source", "source_url"],
        f"divario-italia-indicatore-{indicator_id}.csv",
    )


@app.route("/download/indicator/<indicator_id>.json")
def indicator_download_json(indicator_id):
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/download/quality-life/<url_level>")
def quality_life_download_csv(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    rows = [_quality_life_export_row(row, payload) for row in payload["ranking"]]
    return _csv_response(
        rows,
        ["level", "profile", "rank", "territory", "territory_key", "region", "score", "delta_rank", "coverage"],
        f"divario-italia-qualita-vita-{url_level}-{payload['profile']['slug']}.csv",
    )


@app.route("/download/quality-life/<url_level>.json")
def quality_life_download_json(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


def _quality_life_export_row(row, payload):
    return {
        "level": payload["level"],
        "profile": payload["profile"]["slug"],
        "rank": row["rank"],
        "territory": row["name"],
        "territory_key": row["key"],
        "region": row.get("region") or "",
        "score": row["score"],
        "delta_rank": row["delta_rank"],
        "coverage": row["coverage"],
    }


def _csv_response(rows, fieldnames, filename):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    response = Response(buffer.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.route("/api/quality-life/profiles")
def quality_life_profiles_api():
    return jsonify({"profiles": qb.get_quality_life_profiles()})


@app.route("/api/quality-life/categories")
def quality_life_categories_api():
    return jsonify({"categories": qb.get_quality_life_categories()})


@app.route("/api/quality-life/<url_level>/rankings")
def quality_life_level_rankings_api(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/<url_level>/rankings/<profile_slug>")
def quality_life_level_ranking_profile_api(url_level, profile_slug):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_ranking(level, profile_slug)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/quality-life/<url_level>/<territory_key>")
def quality_life_level_territory_api(url_level, territory_key):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    payload = qb.build_bes_territory(level, territory_key, _quality_life_profile_arg())
    if payload is None:
        abort(404)
    return jsonify(payload)


# Back-compat aliases for the previous regional API paths.
@app.route("/api/quality-life/rankings")
def quality_life_rankings_api_legacy():
    payload = qb.build_bes_ranking("regione", _quality_life_profile_arg())
    return jsonify(payload) if payload else abort(404)


@app.route("/api/quality-life/rankings/<profile_slug>")
def quality_life_rankings_profile_api_legacy(profile_slug):
    payload = qb.build_bes_ranking("regione", profile_slug)
    return jsonify(payload) if payload else abort(404)


@app.route("/api/quality-life/region/<region_key>")
def quality_life_region_api_legacy(region_key):
    payload = qb.build_bes_territory("regione", region_key, _quality_life_profile_arg())
    return jsonify(payload) if payload else abort(404)


@app.route("/qualita-della-vita")
def quality_life_index():
    preview = qb.build_bes_ranking(URL_LEVEL["regioni"], qb.DEFAULT_PROFILE)
    preview_rows = preview["ranking"][:3] if preview else []
    return render_template(
        "quality_life_index.html",
        categories=qb.get_quality_life_categories(),
        profiles=qb.get_quality_life_profiles(),
        default_profile=qb.DEFAULT_PROFILE,
        preview_rows=preview_rows,
        has_province_data=qb.has_bes_data(URL_LEVEL["province"]),
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita",
    )


@app.route("/qualita-della-vita/classifica/<url_level>")
def quality_life_classifica(url_level):
    level = URL_LEVEL.get(url_level)
    if level is None:
        abort(404)
    slug = _quality_life_profile_arg()
    payload = qb.build_bes_ranking(level, slug)
    if payload is None:
        abort(404)
    quality_map_data = (
        {
            row["key"]: {"name": row["name"], "score": it_num(row["score"]), "rank": row["rank"]}
            for row in payload["ranking"]
        }
        if level == "regione" else {}
    )
    public_matches = public_urls.quality_life_public_urls(url_level, slug)
    if not public_matches:
        abort(404)
    canonical = public_matches[0]["loc"]
    response = make_response(render_template(
        "quality_life_classifica.html",
        data=payload,
        quality_map_data=quality_map_data,
        url_level=url_level,
        profiles=qb.get_quality_life_profiles(),
        active_profile=slug,
        default_profile=qb.DEFAULT_PROFILE,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=canonical,
    ))
    # Aliases and extra query state are useful for compatibility, but only the
    # exact URL in the public inventory is an autonomous indexable document.
    requested_path = request.full_path.removesuffix("?")
    if requested_path != canonical.removeprefix(SITE_URL):
        response.headers["X-Robots-Tag"] = "noindex, follow"
    return response


@app.route("/qualita-della-vita/classifica")
def quality_life_classifica_redirect():
    return redirect(f"/qualita-della-vita/classifica/regioni{_profile_suffix(_quality_life_profile_arg())}", code=301)


@app.route("/qualita-della-vita/province")
def quality_life_province_redirect():
    return redirect(f"/qualita-della-vita/classifica/province{_profile_suffix(_quality_life_profile_arg())}", code=301)


# Pre-migration quality-of-life URLs: 301 to the unified /indicatore/ space. The
# multiscopo-prefixed rule is matched ahead of the generic BES one.
@app.route("/qualita-della-vita/indicatore/multiscopo-<indicator_id>/<slug>")
def quality_life_multiscopo_indicator_legacy(indicator_id, slug):
    indicator = multiscopo_data.get_multiscopo_indicator_page(indicator_id)
    if indicator is None:
        abort(404)
    return redirect(multiscopo_data.multiscopo_indicator_path(indicator_id, indicator["name"]), code=301)


@app.route("/qualita-della-vita/indicatore/<indicator_id>/<slug>")
def quality_life_indicator_legacy(indicator_id, slug):
    indicator = bes_data.get_bes_indicator_page(indicator_id)
    if indicator is None:
        abort(404)
    return redirect(bes_data.bes_indicator_path(indicator_id, indicator["name"]), code=301)


@app.route("/qualita-della-vita/metodologia")
def quality_life_methodology():
    # La metodologia della qualità della vita è stata unificata nell'unica
    # pagina "Metodologia e fonti" (/metodologia#qualita-della-vita). Manteniamo
    # la vecchia URL con un 301 per non perdere link e indicizzazione.
    return redirect("/metodologia#qualita-della-vita", code=301)


@app.route("/gioco")
def game_page_legacy_redirect():
    return redirect("/quiz", code=301)


@app.route("/gioco/chi-e-maggiore")
def game_compare_page_legacy_redirect():
    return redirect("/quiz/chi-e-maggiore", code=301)


@app.route("/gioco/ordina")
def game_order_page_legacy_redirect():
    return redirect("/quiz/ordina", code=301)


@app.route("/quiz")
def game_hub_page():
    return render_template(
        "game_hub.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz",
    )


@app.route("/quiz/indovina-la-regione")
def game_page():
    return render_template(
        "game.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/indovina-la-regione",
    )


@app.route("/quiz/chi-e-maggiore")
def game_compare_page():
    return render_template(
        "game_compare.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/chi-e-maggiore",
    )


@app.route("/quiz/ordina")
def game_order_page():
    return render_template(
        "game_order.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/ordina",
    )


@app.route("/quiz/classifica")
def game_leaderboard_page():
    return render_template(
        "game_leaderboard.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/quiz/classifica",
    )


def _session_summary(session):
    if session is None:
        return None
    return {"streak": session["streak"], "best": session["best"], "rounds": session["rounds"]}


@app.route("/api/game/compare/round")
def game_compare_round_api():
    difficulty = request.args.get("difficulty", "0")
    result = quiz.compare_round(difficulty)
    state = quiz_tokens.load_state(request.args.get("token"), "compare")
    keys = [result["region_a"]["region_key"], result["region_b"]["region_key"]]
    result["token"] = quiz_tokens.bind_round(
        state, result["indicator"]["id"], result["indicator"]["year"], keys, result["difficulty"]
    )
    return jsonify(result)


@app.post("/api/game/compare/answer")
def game_compare_answer_api():
    payload = request.get_json(silent=True) or {}
    result = quiz.evaluate_compare(
        payload.get("indicator_id"),
        payload.get("year"),
        payload.get("region_a_key"),
        payload.get("region_b_key"),
        payload.get("choice"),
    )
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(payload.get("token"), "compare")
    keys = [payload.get("region_a_key"), payload.get("region_b_key")]
    session, token = quiz_tokens.apply_answer(
        state, payload.get("indicator_id"), payload.get("year"), keys, result["correct"]
    )
    result["session"] = _session_summary(session)
    result["token"] = token
    result["achievements"] = _record_quiz(request, "compare", result["correct"], result["session"])
    return jsonify(result)


@app.route("/api/game/order/round")
def game_order_round_api():
    try:
        count = int(request.args.get("count", ""))
    except ValueError:
        abort(400)
    result = quiz.order_round(count)
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(request.args.get("token"), "order")
    keys = [r["region_key"] for r in result["regions"]]
    result["token"] = quiz_tokens.bind_round(
        state, result["indicator"]["id"], result["indicator"]["year"], keys, count, count=count
    )
    return jsonify(result)


@app.post("/api/game/order/answer")
def game_order_answer_api():
    payload = request.get_json(silent=True) or {}
    region_keys = payload.get("region_keys")
    result = quiz.evaluate_order(
        payload.get("indicator_id"),
        payload.get("year"),
        region_keys,
    )
    if result is None:
        abort(400)
    state = quiz_tokens.load_state(payload.get("token"), "order")
    is_perfect = result["score"] == result["total"]
    session, token = quiz_tokens.apply_answer(
        state, payload.get("indicator_id"), payload.get("year"), region_keys or [], is_perfect
    )
    result["session"] = _session_summary(session)
    result["token"] = token
    result["achievements"] = _record_quiz(request, "order", is_perfect, result["session"])
    return jsonify(result)


def _record_quiz(req, mode, correct, session_summary):
    """Se la richiesta porta un JWT valido, aggiorna le statistiche account della
    modalità e valuta gli achievement, restituendo gli sblocchi appena ottenuti
    (per il toast). Anonimo o DB giù -> lista vuota, il gioco non cambia."""
    user = auth.current_user(req.headers)
    if not user:
        return []
    try:
        from app import player_stats, achievements
        best = (session_summary or {}).get("best", 0)
        player_stats.record_quiz_answer(user["id"], mode, correct, best)
        return achievements.evaluate(user["id"])
    except Exception:  # noqa: BLE001
        return []


@app.route("/api/player/me")
def player_me_api():
    """Statistiche e traguardi dell'utente per la vetrina del profilo. Solo con
    login (401 anonimo): non esistono stats server per gli anonimi (restano
    locali)."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import player_stats, achievements
    try:
        stats = player_stats.stats_map(user["id"])
        unlocked = achievements.list_for(user["id"])
    except Exception:  # noqa: BLE001
        stats, unlocked = {}, []
    return jsonify({"stats": stats, "achievements": unlocked})


@app.post("/api/player/merge")
def player_merge_api():
    """Fonde le statistiche locali (localStorage) nell'account, UNA volta al
    primo login (l'idempotenza la garantisce il client con un flag). Ritorna gli
    achievement sbloccati dalla fusione."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    local = (request.get_json(silent=True) or {}).get("stats") or {}
    from app import player_stats, achievements
    try:
        player_stats.merge_local(user["id"], local)
        unlocked = achievements.evaluate(user["id"])
    except Exception:  # noqa: BLE001
        unlocked = []
    return jsonify({"ok": True, "achievements": unlocked})


@app.patch("/api/player/nickname")
def player_nickname_api():
    """Aggiorna il nickname dell'account (moderato). Solo con login."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    raw = (request.get_json(silent=True) or {}).get("nickname", "")
    nickname, err = moderation.validate_nickname(raw)
    if err:
        return jsonify({"error": err}), 400
    from app import account
    account.set_nickname(user["id"], nickname)
    return jsonify({"ok": True, "nickname": nickname})


@app.route("/api/comparisons")
def comparisons_list_api():
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import comparisons
    try:
        items = comparisons.list_for(user["id"])
    except Exception:  # noqa: BLE001
        items = []
    return jsonify({"comparisons": items})


@app.post("/api/comparisons")
def comparisons_save_api():
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    payload = request.get_json(silent=True) or {}
    from app import comparisons
    item = comparisons.save(user["id"], payload.get("title", ""), payload.get("config") or {})
    if item is None:
        return jsonify({"error": "limit_or_invalid"}), 400
    return jsonify({"ok": True, "comparison": item})


@app.delete("/api/comparisons/<int:comparison_id>")
def comparisons_delete_api(comparison_id):
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import comparisons
    comparisons.remove(user["id"], comparison_id)
    return jsonify({"ok": True})


@app.route("/api/account/export")
def account_export_api():
    """Portabilità: tutti i dati dell'utente in JSON (download)."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import account
    data = account.export_data(user["id"])
    resp = jsonify(data)
    resp.headers["Content-Disposition"] = "attachment; filename=divario-italia-dati-account.json"
    return resp


@app.delete("/api/account")
def account_delete_api():
    """Diritto all'oblio: cancella tutte le righe dell'utente e l'utente Supabase."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import account
    return jsonify(account.delete_account(user["id"]))


@app.route("/account")
def account_page():
    """La pagina account: profilo, preferiti, dati (export/cancellazione). I dati
    sono per-utente, quindi la pagina si popola lato client col Bearer."""
    return render_template("account.html", site_name=SITE_NAME)


@app.route("/api/auth/me")
def auth_me_api():
    """Chi è l'utente di questa richiesta, secondo il Bearer JWT. Anonimo
    (`{"user": null}`) se il token è assente, invalido, o l'auth non è
    configurata: il frontend lo usa per mostrare stato login/logout.

    Effetto collaterale, quando c'è un utente valido: upsert del profilo e
    aggiornamento di last_seen_at. Best-effort: se il DB non risponde, si torna
    comunque l'identità dal token (la UI non deve cadere per il profilo)."""
    user = auth.current_user(request.headers)
    profile = None
    if user:
        try:
            from app import accounts
            profile = accounts.upsert_profile(
                user["id"], email=user.get("email", ""),
                nickname_seed=request.args.get("nick", ""))
        except Exception:  # noqa: BLE001
            profile = None
    return jsonify({"user": user, "profile": profile})


@app.route("/api/favorites")
def favorites_list_api():
    """Gli id indicatore preferiti dell'utente. Solo con login (401 se anonimo):
    non esistono preferiti anonimi. Tollerante sul DB (mai 500 sulla UI)."""
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import favorites
    try:
        ids = favorites.list_ids(user["id"])
    except Exception:  # noqa: BLE001
        ids = []
    return jsonify({"favorites": ids})


@app.post("/api/favorites")
def favorites_add_api():
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    indicator_id = (request.get_json(silent=True) or {}).get("indicator_id", "")
    if not isinstance(indicator_id, str) or not indicator_id or len(indicator_id) > 64:
        return jsonify({"error": "bad_indicator"}), 400
    from app import favorites
    favorites.add(user["id"], indicator_id)
    return jsonify({"ok": True})


@app.delete("/api/favorites/<path:indicator_id>")
def favorites_remove_api(indicator_id):
    user = auth.current_user(request.headers)
    if not user:
        return jsonify({"error": "auth_required"}), 401
    from app import favorites
    favorites.remove(user["id"], indicator_id)
    return jsonify({"ok": True})


@app.route("/api/game/leaderboard")
def leaderboard_get_api():
    mode = request.args.get("mode", "")
    period = request.args.get("period", "all")
    if mode not in leaderboard.MODES:
        return jsonify({"error": "bad_mode"}), 400
    if period not in leaderboard.PERIODS:
        return jsonify({"error": "bad_period"}), 400
    try:
        limit = int(request.args.get("limit", leaderboard.DEFAULT_LIMIT))
    except ValueError:
        limit = leaderboard.DEFAULT_LIMIT
    # Tollerante: la classifica ora vive su un backend di rete (Supabase), che
    # può andare in pausa. Un'outage è un widget vuoto, mai un 500 sulla pagina
    # del gioco. Stesso pattern del cruscotto (`pipeline_store.run()`).
    try:
        entries = leaderboard.top(mode, period, limit)
    except Exception:  # noqa: BLE001
        entries = []
    return jsonify({"mode": mode, "period": period, "entries": entries})


@app.post("/api/game/leaderboard")
def leaderboard_post_api():
    if not _rate_limit_ok(f"lb:{_client_ip()}", limit=5, window_s=60):
        return jsonify({"error": "rate_limited"}), 429

    payload = request.get_json(silent=True) or {}
    state = quiz_tokens.peek_state(payload.get("token"))
    if state is None:
        return jsonify({"error": "token_invalid"}), 400

    mode = state["m"]
    score = state.get("b", 0)
    if not score:
        return jsonify({"error": "score_missing"}), 400

    nickname, error = moderation.validate_nickname(payload.get("nickname"))
    if error:
        return jsonify({"error": error}), 400

    detail = {"count": state["c"]} if mode == "order" and state.get("c") else {}
    # Se c'è un JWT Supabase valido, la riga si lega all'account; senza, resta
    # anonima (il gioco non richiede registrazione). L'anti-cheat non cambia: il
    # punteggio viene sempre dal token quiz firmato, non dal client.
    user = auth.current_user(request.headers)
    user_id = user["id"] if user else None
    leaderboard.submit(mode, state["sid"], nickname, score, detail, user_id=user_id)
    rank_all, rank_week = leaderboard.ranks_for_session(mode, state["sid"])
    return jsonify({"ok": True, "mode": mode, "score": score, "rank_all": rank_all, "rank_week": rank_week})


@app.post("/api/game/leaderboard/admin/delete")
def leaderboard_admin_delete_api():
    """Rimozione manuale di una voce (moderazione), autenticata con
    SECRET_KEY invece che con un account: non c'è un pannello admin, questo
    endpoint serve solo per interventi occasionali via curl."""
    provided = request.headers.get("X-Admin-Key", "")
    if not hmac.compare_digest(provided, app.secret_key):
        abort(404)
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode")
    nickname = payload.get("nickname")
    if mode not in leaderboard.MODES or not nickname:
        return jsonify({"error": "bad_request"}), 400
    deleted = leaderboard.delete_entry(mode, nickname)
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/game/regions")
def game_regions_api():
    return jsonify({"regions": profiles.all_regions_index()})


@app.route("/api/game/daily")
def game_daily_api():
    return jsonify(game.daily_payload())


@app.route("/api/game/daily/<iso_date>")
def game_daily_archive_api(iso_date):
    payload = game.daily_payload_for_date(iso_date)
    if payload is None:
        abort(404)
    return jsonify(payload)


@app.route("/api/game/archive")
def game_archive_api():
    return jsonify({"puzzles": game.archive_list()})


@app.route("/api/game/practice")
def game_practice_api():
    return jsonify(game.practice_payload())


@app.post("/api/game/guess")
def game_guess_api():
    payload = request.get_json(silent=True) or {}
    puzzle_id = payload.get("puzzle_id")
    region_key = payload.get("region_key")
    attempt = payload.get("attempt")
    if not isinstance(region_key, str) or not isinstance(attempt, int) or isinstance(attempt, bool):
        abort(400)
    result = game.evaluate_guess(puzzle_id, region_key, attempt)
    if result is None:
        abort(400)
    # A partita finita, se loggato, registra la giornaliera e valuta i traguardi.
    result["achievements"] = []
    if result.get("finished"):
        user = auth.current_user(request.headers)
        if user:
            try:
                from app import player_stats, achievements
                if player_stats.record_daily(user["id"], puzzle_id, attempt, result.get("correct")):
                    result["achievements"] = achievements.evaluate(user["id"])
            except Exception:  # noqa: BLE001
                pass
    return jsonify(result)


def _indexable_indicator_catalog():
    """Il catalogo deduplicato delle pagine indicizzabili, per sitemap e LLM.

    La costruzione sta in `app/indicator_universe.py`, che fa **la stessa
    passata** anche per il cruscotto editoriale: prima la sitemap la faceva sui
    soli indicizzabili e chi doveva guardare tutto l'atlante ne avrebbe fatta una
    seconda, cioe' una seconda traversata e un secondo picco di memoria per gli
    stessi 634 indicatori. Allargarla e' costato 0,2 s.

    Il lock single-flight che stava qui e' dentro `synchronized_cache`: `lru_cache`
    non coalizza i miss concorrenti, e il worker gunicorn ha otto thread mentre
    `/sitemap.xml` e `/llms-full.txt` non sono cached. Due crawler simultanei a
    freddo rifacevano entrambi la traversata per intero."""
    return indicator_universe.indexable_catalog()


# Il nome vecchio, per i test che lo importano da qui: la funzione si e' spostata,
# la domanda che risponde no.
_build_indexable_indicator_catalog = _indexable_indicator_catalog


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": f"{SITE_URL}/", "priority": "1.0"},
        {"loc": f"{SITE_URL}/atlante", "priority": "0.9"},
        {"loc": f"{SITE_URL}/catalogo-dati", "priority": "0.7"},
        {"loc": f"{SITE_URL}/divari-regionali", "priority": "0.9"},
        {"loc": f"{SITE_URL}/confronto", "priority": "0.7"},
        {"loc": f"{SITE_URL}/blog", "priority": "0.8"},
        {"loc": f"{SITE_URL}/metodologia", "priority": "0.7"},
        {"loc": f"{SITE_URL}/chi-siamo", "priority": "0.6"},
        {"loc": f"{SITE_URL}/regioni", "priority": "0.7"},
        {"loc": f"{SITE_URL}/temi", "priority": "0.6"},
        {"loc": f"{SITE_URL}/quiz", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/indovina-la-regione", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/chi-e-maggiore", "priority": "0.7"},
        {"loc": f"{SITE_URL}/quiz/ordina", "priority": "0.7"},
        {"loc": f"{SITE_URL}/qualita-della-vita", "priority": "0.8"},
        {"loc": f"{SITE_URL}/privacy", "priority": "0.4"},
    ]
    pages.extend({"loc": item["loc"], "priority": "0.8"} for item in public_urls.quality_life_public_urls())
    for post in get_posts():
        pages.append({
            "loc": post["url"],
            "lastmod": post.get("date_modified", post["date"]).isoformat(),
            "priority": "0.7",
        })
    for region in profiles.all_regions_index():
        pages.append({"loc": f"{SITE_URL}{region['path']}", "priority": "0.7"})
    for theme in all_atlas_themes_index():
        pages.append({"loc": f"{SITE_URL}{theme['path']}", "priority": "0.5"})
    for view in _indexable_indicator_catalog():
        meta = view["meta"]
        # No synthetic lastmod from year_max: an indexable page is not "modified"
        # on 31 December of its last data year. Only posts carry a real date.
        pages.append({
            "loc": f"{SITE_URL}{meta['canonical_path']}",
            "priority": "0.6",
        })
    xml = render_template("sitemap.xml", pages=pages)
    return Response(xml, mimetype="application/xml")


# Content-Signals preamble + AI-bot blocklist. These were previously injected by
# Cloudflare's managed robots.txt; kept here so robots.txt has a single source of
# truth after the Cloudflare managed injection is disabled (2026-07-01). To change
# the Content-Signal policy or the AI-bot list, edit these constants.
_ROBOTS_CONTENT_SIGNALS_PREAMBLE = """\
# As a condition of accessing this website, you agree to abide by the following
# content signals:

# (a)  If a Content-Signal = yes, you may collect content for the corresponding
#      use.
# (b)  If a Content-Signal = no, you may not collect content for the
#      corresponding use.
# (c)  If the website operator does not include a Content-Signal for a
#      corresponding use, the website operator neither grants nor restricts
#      permission via Content-Signal with respect to the corresponding use.

# The content signals and their meanings are:

# search:   building a search index and providing search results (e.g., returning
#           hyperlinks and short excerpts from your website's contents). Search does not
#           include providing AI-generated search summaries.
# ai-input: inputting content into one or more AI models (e.g., retrieval
#           augmented generation, grounding, or other real-time taking of content for
#           generative AI search answers).
# ai-train: training or fine-tuning AI models.

# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
# RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT
# AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET."""

# search + real-time AI grounding (ai-input) are permitted so generative answer
# engines can cite the atlas, while model training (ai-train) stays reserved.
_ROBOTS_CONTENT_SIGNAL = "search=yes,ai-input=yes,ai-train=no"
# Generative answer engines allowed to fetch pages for real-time citation and
# grounding. These are the retrieval/citation crawlers, not the training ones:
# unblocking them is what makes the site eligible to be surfaced in AI answers.
_ROBOTS_AI_ANSWER_BOTS = (
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Perplexity-User",
    "Claude-SearchBot",
    "Claude-User",
    "Google-Extended",
)
# AI training crawlers kept blocked so the ai-train=no reservation stays
# enforceable. Anthropic and OpenAI split retrieval from training by user agent,
# so ClaudeBot/GPTBot are blocked here while their answer bots above are allowed.
_ROBOTS_AI_TRAINING_BOTS = (
    "Amazonbot",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "ClaudeBot",
    "CloudflareBrowserRenderingCrawler",
    "GPTBot",
    "meta-externalagent",
)
# Machine endpoints and duplicate legacy dashboards kept out of the crawl.
_ROBOTS_DISALLOW_PATHS = ("/api/", "/data", "/legacy", "/legacy-reddito")


@app.route("/robots.txt")
def robots():
    lines = [_ROBOTS_CONTENT_SIGNALS_PREAMBLE, ""]
    # Default group: content signals, then the shared path rules for all crawlers.
    lines += ["User-agent: *", f"Content-Signal: {_ROBOTS_CONTENT_SIGNAL}", "Allow: /"]
    lines += [f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS]
    lines.append("")
    # Answer-engine group: one group for all citation crawlers, so each reads its
    # own rules (ai-input allowed) and inherits the same crawl boundaries as "*".
    lines += [f"User-agent: {bot}" for bot in _ROBOTS_AI_ANSWER_BOTS]
    lines += [f"Content-Signal: {_ROBOTS_CONTENT_SIGNAL}", "Allow: /"]
    lines += [f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS]
    lines.append("")
    for bot in _ROBOTS_AI_TRAINING_BOTS:
        lines += [f"User-agent: {bot}", "Disallow: /", ""]
    lines.append(f"# Curated index for language models: {SITE_URL}/llms.txt")
    lines.append(f"# Extended corpus for language models: {SITE_URL}/llms-full.txt")
    lines.append(f"Sitemap: {SITE_URL}/sitemap.xml")
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    """Curated Markdown index for language models (llmstxt.org convention).

    Generated from the live catalog and blog so the entry points, featured
    indicators and recent articles a generative engine sees stay in sync with
    the site instead of drifting from a hand-maintained file.
    """
    featured = _home_featured_indicator_links()
    recent_posts = get_posts()[:8]
    lines = [
        "# Divario Italia",
        "",
        "> Atlante degli indicatori territoriali Istat: confronto tra regioni "
        "italiane su economia, lavoro, demografia, salute e qualita della vita, "
        "con serie storiche, fonti verificate e dati aperti in CSV e JSON.",
        "",
        "Divario Italia (divarioitalia.it) pubblica i dati Istat sullo sviluppo "
        "dei territori italiani. Ogni pagina indicatore espone la definizione, "
        "l'ultimo anno disponibile, la copertura regionale, la fonte primaria e "
        "i download strutturati. I numeri provengono dalla Banca dati "
        "territoriale per le politiche di sviluppo di Istat e dal BES dei "
        "Territori. I contenuti sono citabili con attribuzione a \"Divario "
        "Italia\" e alla fonte Istat.",
        "",
        "## Sezioni principali",
        f"- [Atlante degli indicatori]({SITE_URL}/atlante): mappa interattiva e catalogo regionale degli indicatori territoriali.",
        f"- [Regioni]({SITE_URL}/regioni): profilo di ogni regione italiana con i suoi indicatori chiave.",
        f"- [Temi]({SITE_URL}/temi): indicatori raggruppati per area, da economia e lavoro a demografia, salute e istruzione.",
        f"- [Qualita della vita]({SITE_URL}/qualita-della-vita): classifiche di regioni e province con pesi e metodo dichiarati.",
        f"- [Metodologia e fonti]({SITE_URL}/metodologia): metodo, fonti Istat, criteri di qualita e limiti dei confronti.",
        f"- [Blog]({SITE_URL}/blog): analisi data-driven sui divari territoriali, con numeri verificati e link all'atlante.",
        "",
        "## Classifiche per profilo",
    ]
    lines += [
        f"- [Classifica {item['url_level']}, profilo {item['profile_name']}]({item['loc']})"
        for item in public_urls.quality_life_public_urls()
    ]
    lines += ["", "## Indicatori in evidenza"]
    for item in featured:
        summary = " ".join((item.get("summary") or "").split())
        detail = f" {summary}" if summary else ""
        lines.append(
            f"- [{item['name']}]({SITE_URL}{item['path']}):{detail} Ultimo anno {item['year']}, tema {item['theme']}."
        )
    lines += ["", "## Articoli recenti"]
    for post in recent_posts:
        description = " ".join((post.get("description") or "").split())
        detail = f": {description}" if description else ""
        lines.append(f"- [{post['title']}]({post['url']}){detail}")
    lines += [
        "",
        "## Note per i modelli linguistici",
        "- Fonte primaria: Istat, Banca dati territoriale per le politiche di sviluppo e BES dei Territori. Alcuni indicatori provengono da altre istituzioni, indicate sulla singola scheda.",
        f"- Licenza dei dati: {sources.LICENSE_LABEL}. Cita \"Divario Italia\" e la fonte indicata per ciascun indicatore.",
        "- Per gli indicatori territoriali, i download seguono il pattern "
        f"`/download/indicator/ID.csv` e `/download/indicator/ID.json`. Esempio reale: "
        f"{SITE_URL}/download/indicator/{featured[0]['id']}.csv e "
        f"{SITE_URL}/download/indicator/{featured[0]['id']}.json.",
        f"- Indice completo delle pagine: {SITE_URL}/sitemap.xml.",
        f"- Versione estesa con definizioni e classifiche complete: {SITE_URL}/llms-full.txt.",
        "- I confronti descrivono differenze osservate, non rapporti di causa. Anni e coperture possono variare tra indicatori.",
        "",
    ]
    return Response("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def _llms_indicator_full_block(indicator_id):
    """Full-text block for one indicator: definition, source and live ranking.

    Reuses the same catalog loaders and direction ordering as the indicator
    landing page, so the numbers a model reads here match the published page.
    """
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        return None
    meta = payload["metadata"]
    explain = meta.get("explain") or {}
    year = meta["year_max"]
    year_view = get_atlas_indicator_year(indicator_id, year)
    values = year_view["values"]  # sorted by value desc
    if explain.get("direction") in ("lower_better", "higher_worse"):
        values = list(reversed(values))
    unit = meta.get("unit") or ""
    path = profiles.indicator_path(indicator_id, meta["name"])
    lines = [f"### {meta['name']}", f"{SITE_URL}{path}", ""]
    if explain.get("plain"):
        lines.append(explain["plain"])
    if explain.get("reading"):
        lines.append(f"Come si legge: {explain['reading']}")
    if explain.get("caveat"):
        lines.append(f"Limite: {explain['caveat']}")
    lines.append(
        f"Fonte: {meta.get('source', 'Istat')}. Unita di misura: {unit or 'n.d.'}. "
        f"Copertura: {meta['year_min']}-{meta['year_max']}, {len(meta['regions'])} regioni."
    )
    lines += ["", f"Classifica {year} (posizione. regione: valore):"]
    for position, row in enumerate(values, 1):
        lines.append(f"{position}. {row['region']}: {it_num(row['value'], 2)} {unit}".rstrip())
    lines.append("")
    return "\n".join(lines)


@app.route("/llms-full.txt")
def llms_full_txt():
    """Extended Markdown corpus for language models: full indicator text.

    Where /llms.txt is a curated map, this file carries the full definition and
    the complete regional ranking of the flagship indicators plus a compact
    catalogue of every indexable indicator, so a model can ground an answer in a
    single fetch without crawling each page.
    """
    lines = [
        "# Divario Italia, testo esteso per i modelli linguistici",
        "",
        "> Definizioni complete e classifiche regionali degli indicatori "
        "pubblicati su divarioitalia.it. I numeri coincidono "
        "con le pagine indicatore del sito. La fonte primaria e Istat, ma "
        "alcuni indicatori provengono da altre istituzioni indicate su ogni "
        "scheda. Cita \"Divario Italia\" e la fonte indicata per ciascun "
        "indicatore.",
        "",
        "## Metodologia in breve",
        "La fonte primaria e la Banca dati territoriale per le politiche di "
        "sviluppo di Istat, integrata dal BES e dal BES dei Territori per la "
        "qualita della vita. Ogni indicatore ha una direzione dichiarata: per "
        "alcuni un valore piu alto e positivo, per altri e negativo, per altri "
        "serve solo come contesto. I confronti descrivono differenze osservate "
        "tra territori e non dimostrano da soli un rapporto di causa. Anni e "
        "coperture possono variare tra indicatori. Licenza dei dati: "
        f"{sources.LICENSE_LABEL}.",
        "",
        "## Indicatori in evidenza, testo completo",
    ]
    for indicator_id in _HOME_FEATURED_INDICATORS:
        block = _llms_indicator_full_block(indicator_id)
        if block:
            lines.append(block)

    lines.append("## Catalogo completo degli indicatori indicizzabili")
    lines.append("")
    for view in _indexable_indicator_catalog():
        meta = view["meta"]
        plain = " ".join(((meta.get("explain") or {}).get("plain") or "").split())
        definition = plain or "Definizione sintetica non disponibile."
        coverage = ", ".join(
            f"{level['label'].lower()} {level['year_min']}-{level['year_max']} "
            f"({level['territory_count']} territori nell'ultimo anno)"
            for level in view["levels"]
        )
        source_label = meta["source_label"]
        source = (
            f"[{source_label}]({meta['source_url']})"
            if meta.get("source_url") else source_label
        )
        lines.append(
            f"- [{meta['name']}]({SITE_URL}{meta['canonical_path']}): "
            f"famiglia {meta['family_label']}; fonte {source}; "
            f"unita {meta.get('unit') or 'n.d.'}; copertura {coverage}; "
            f"definizione: {definition}"
        )
        if meta.get("downloads"):
            lines.append(
                f"  Download: CSV {SITE_URL}{meta['downloads']['csv']}; "
                f"JSON {SITE_URL}{meta['downloads']['json']}."
            )
    lines.append("")
    return Response("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


@app.route("/ads.txt")
def ads_txt():
    # ads.txt is a public publisher declaration, not runtime configuration.
    # Serving the committed file keeps it available to the AdSense crawler even
    # when a Cloud Run revision is deployed without the optional client env var.
    return send_from_directory(app.static_folder, "ads.txt", mimetype="text/plain")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico', mimetype='image/vnd.microsoft.icon')


def _home_featured_indicator_links():
    by_id = {str(item["id"]): item for item in get_catalog()["indicators"]}
    featured = []
    for indicator_id in _HOME_FEATURED_INDICATORS:
        item = by_id.get(indicator_id)
        if not item or not profiles.is_search_indexable_indicator(item):
            continue
        featured.append({
            "id": str(item["id"]),
            "name": item["name"],
            "theme": item["theme"],
            "year": item["year_max"],
            "path": profiles.indicator_path(item["id"], item["name"]),
            "summary": (item.get("explain") or {}).get("plain", ""),
        })
    return featured


def _map_hero(indicator_ids):
    """Data for an interactive choropleth panel: a curated indicator picker, the
    chosen indicator's per-region colors, and a JSON tooltip payload for the
    hover/click behaviour in home-map.js. The indicator choice lives in
    ?indicator= so picking one is a plain link, no JS required to change the map.

    Shared by the homepage and /divari-regionali through _map_panel.html: same
    component, different curated set, so there is one map behaviour on the
    server-rendered side of the site instead of two."""
    by_id = {str(item["id"]): item for item in get_catalog()["indicators"]}
    options = [
        {"id": indicator_id, "name": by_id[indicator_id]["name"]}
        for indicator_id in indicator_ids
        if indicator_id in by_id
    ]
    requested = request.args.get("indicator")
    selected_id = requested if requested in indicator_ids and requested in by_id else indicator_ids[0]

    payload = get_atlas_indicator(selected_id)
    meta = payload["metadata"]
    year = meta["year_max"]
    values = get_atlas_indicator_year(selected_id, year)["values"]
    direction = (meta.get("explain") or {}).get("direction")
    ranked = list(reversed(values)) if direction in ("lower_better", "higher_worse") else values
    unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
    total = len(ranked)

    tooltip_data = {
        row["region_key"]: {
            "name": row["region"],
            "value": it_num(row["value"], 2),
            "unit": unit,
            "rank": position,
            "total": total,
        }
        for position, row in enumerate(ranked, 1)
    }

    return {
        "options": options,
        "selected_id": selected_id,
        "indicator_name": meta["name"],
        "indicator_path": meta["path"],
        "theme": meta["theme"],
        "year": year,
        "colors": indicator_notes.region_choropleth_colors(values),
        "tooltip_data": tooltip_data,
    }


def _home_qol_preview():
    payload = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    if payload is None:
        return None
    ranking = payload["ranking"]
    return {
        "top5": ranking[:5],
        "bottom3": list(reversed(ranking[-3:])),
        "spread": it_num(ranking[0]["score"] - ranking[-1]["score"]),
        "leader": ranking[0]["name"],
        "last": ranking[-1]["name"],
    }


def _region_leaders(matrix, meta, keep):
    """Region in front and region trailing over the mean oriented score across
    the scoreable indicators for which keep(info) is true (best = 1.0). Returns
    (best_name, worst_name), or (None, None) when nothing matched is scoreable.
    Purely derived from the data, no placeholder leaders."""
    totals = {}  # region_key -> [sum_oriented, count]
    for ind_id, by_region in matrix.items():
        info = meta.get(ind_id)
        if not info or not keep(info):
            continue
        direction = info["direction"]
        if direction not in profiles.SCOREABLE_DIRECTIONS:
            continue
        for region_key, percentile in by_region.items():
            oriented = profiles._oriented(percentile, direction)
            acc = totals.setdefault(region_key, [0.0, 0])
            acc[0] += oriented
            acc[1] += 1
    ranked = sorted(
        ((key, total / n) for key, (total, n) in totals.items() if n),
        key=lambda kv: kv[1],
        reverse=True,
    )
    if not ranked:
        return None, None
    return profiles.region_name(ranked[0][0]), profiles.region_name(ranked[-1][0])


def _area_leaders(area, matrix, meta):
    """Region in front / trailing for a macro-area."""
    return _region_leaders(matrix, meta, lambda info: info["macro_area"] == area)


def _theme_leaders(theme, matrix, meta):
    """Region in front / trailing for a single theme."""
    return _region_leaders(matrix, meta, lambda info: info["theme"] == theme)


def _home_themes_preview():
    """'Temi e areè cards: for each macro-area, its indicator/theme counts plus
    the region in front and the region trailing."""
    matrix = profiles._percentile_matrix()
    meta = profiles._indicator_meta()
    cards = []
    for group in atlas_themes_by_macro_area():
        best, worst = _area_leaders(group["macro_area"], matrix, meta)
        if best is None:
            continue
        cards.append({
            "area": group["macro_area"],
            "count": group["indicator_count"],
            "theme_count": len(group["themes"]),
            "themes": [t["theme"] for t in group["themes"][:4]],
            "best": best,
            "worst": worst,
        })
    return cards


def _themes_index_areas():
    """Full '/temì page: every macro-area with its themes, and for each theme
    the indicator count, a preview of its indicators, an illustrative
    average-trend sparkline and the region in front / trailing (per-theme
    standings), matching the design's themes index."""
    matrix = profiles._percentile_matrix()
    meta = profiles._indicator_meta()
    # Card details from the unified atlas catalog (numeric + BES + Multiscopo),
    # the same source as the macro-area counts, so themes made only of BES/
    # Multiscopo indicators (e.g. Benessere soggettivo) get names and sparkline.
    by_theme = {}
    for item in get_atlas_catalog()["indicators"]:
        by_theme.setdefault(item["theme"], []).append(item)
    areas = []
    for group in atlas_themes_by_macro_area():
        themes = []
        for theme in group["themes"]:
            lead, lag = _theme_leaders(theme["theme"], matrix, meta)
            items = sorted(
                by_theme.get(theme["theme"], []),
                key=lambda i: (not i["complete"], i["name"].lower()),
            )
            names = [i["name"] for i in items]
            themes.append({
                "theme": theme["theme"],
                "path": theme["path"],
                "indicator_count": theme["indicator_count"],
                "indicators": names[:5],
                "extra_count": max(0, len(names) - 5),
                "spark_points": _theme_spark_points(items),
                "lead": lead,
                "lag": lag,
            })
        areas.append({
            "area": group["macro_area"],
            "count": group["indicator_count"],
            "theme_count": len(group["themes"]),
            "themes": themes,
        })
    return areas


def _theme_spark_points(items):
    """SVG polyline for a theme's illustrative average trend: each indicator's
    national-average series normalised to 0..1 (inverted so up = improving),
    averaged across indicators by point index. Illustrative composite, not an
    official series."""
    series = []
    for item in items:
        values = [p["value"] for p in (item.get("spark") or []) if p.get("value") is not None]
        if len(values) < 2:
            continue
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1.0
        invert = (item.get("explain") or {}).get("direction") in ("lower_better", "higher_worse")
        normalised = [(v - lo) / span for v in values]
        if invert:
            normalised = [1.0 - n for n in normalised]
        series.append(normalised)
    if not series:
        return ""
    length = min(len(s) for s in series)
    averaged = [
        {"year": index, "value": sum(s[index] for s in series) / len(series)}
        for index in range(length)
    ]
    return indicator_notes.sparkline_points(averaged, width=160, height=42)


def _home_compare_preview():
    """'Confronta' preview: three real regions across three scoreable indicators,
    with a bar filled by oriented position (best = full) and the real ranking."""
    rows = []
    for indicator_id in _HOME_COMPARE_INDICATORS:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        direction = (meta.get("explain") or {}).get("direction")
        invert = direction in ("lower_better", "higher_worse")
        ranked = list(reversed(values)) if invert else values
        rank_by_key = {row["region_key"]: pos for pos, row in enumerate(ranked, 1)}
        value_by_key = {row["region_key"]: row["value"] for row in values}
        vals = [row["value"] for row in values]
        low, high = min(vals), max(vals)
        span = (high - low) or 1
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
        entries = []
        for key, color in zip(_HOME_COMPARE_REGIONS, _HOME_COMPARE_COLORS):
            if key not in value_by_key:
                continue
            fraction = (value_by_key[key] - low) / span
            if invert:
                fraction = 1 - fraction
            entries.append({
                "name": profiles.region_name(key),
                "value": it_num(value_by_key[key], 2),
                "unit": unit,
                "rank": rank_by_key[key],
                "total": len(ranked),
                "pct": max(6, round(fraction * 100)),
                "color": color,
            })
        if entries:
            rows.append({
                "theme": meta["theme"],
                "name": meta["name"],
                # /confronto rende lo stesso confronto senza JavaScript, e là
                # ogni riga deve poter aprire la scheda dell'indicatore: il
                # percorso canonico viene dal catalogo, non ricostruito a mano.
                "path": meta["path"],
                "year": year,
                "entries": entries,
            })
    if not rows:
        return None
    legend = [
        {"name": profiles.region_name(key), "color": color}
        for key, color in zip(_HOME_COMPARE_REGIONS, _HOME_COMPARE_COLORS)
    ]
    return {"legend": legend, "rows": rows}


def _home_quiz_games():
    return [
        {
            "name": "Indovina la Regione",
            "desc": "Mappa e indizi Istat che si sbloccano a ogni tentativo sbagliato. Sei tentativi.",
            "meta": "circa 2 minuti",
            "href": "/quiz/indovina-la-regione",
        },
        {
            "name": "Chi è maggiore?",
            "desc": "Due regioni, un indicatore. Scegli quale ha il valore più alto.",
            "meta": "testa a testa",
            "href": "/quiz/chi-e-maggiore",
        },
        {
            "name": "Ordina le regioni",
            "desc": "Cinque regioni da ordinare dal valore più alto al più basso, con credito parziale.",
            "meta": "credito parziale",
            "href": "/quiz/ordina",
        },
    ]


# ===========================================================================
# Homepage 2026 — data for the redesigned surface.
#
# Every module below reads the real catalog. The design prototype shipped
# illustrative numbers; nothing here is illustrative, so what the page claims
# is always what the data says. The legacy _home_* helpers above still serve
# /divari-regionali and stay untouched.
# ===========================================================================


def _ds_ramp_color(fraction):
    """Bucket a 0..1 position into the six-stop sequential teal ramp."""
    steps = len(_DS_SEQ_RAMP)
    return _DS_SEQ_RAMP[min(steps - 1, max(0, int(fraction * steps)))]


def _ds_choropleth(values):
    """{region_key: hex} over the design system's sequential ramp.

    Colour encodes the VALUE, not a verdict: the ramp always runs pale-to-deep
    with the magnitude, whatever the indicator's direction. The legend and the
    prose carry the "meglio se piu alto / piu basso" reading instead."""
    numeric = [row["value"] for row in values if row.get("value") is not None]
    if not numeric:
        return {}
    low, high = min(numeric), max(numeric)
    span = (high - low) or 1.0
    return {
        row["region_key"]: _ds_ramp_color((row["value"] - low) / span)
        for row in values
        if row.get("value") is not None
    }


def _ds_short_value(value, unit):
    """Compact axis label for the map legend: thousands folded to k."""
    if value is None:
        return "n.d."
    if abs(value) >= 10000:
        return f"{round(value / 1000)}k"
    return it_num(value, 0 if abs(value) >= 100 else 1)


def _home_hero_map():
    """The hero choropleth: a curated indicator picker, per-region fills on the
    2026 sequential ramp, the two extremes the hero calls out, and a readout
    payload for ds-home.js.

    The chosen indicator lives in ?indicator= and the picker is a plain form,
    so the hero changes indicator without JavaScript."""
    by_id = {str(item["id"]): item for item in get_catalog()["indicators"]}
    options = [
        {"id": indicator_id, "name": by_id[indicator_id]["name"]}
        for indicator_id in _HOME_MAP_INDICATORS
        if indicator_id in by_id
    ]
    requested = request.args.get("indicator")
    selected_id = (
        requested
        if requested in _HOME_MAP_INDICATORS and requested in by_id
        else _HOME_MAP_INDICATORS[0]
    )

    payload = get_atlas_indicator(selected_id)
    meta = payload["metadata"]
    year = meta["year_max"]
    # already sorted by value, descending
    values = get_atlas_indicator_year(selected_id, year)["values"]
    if not values:
        return None

    explain = meta.get("explain") or {}
    direction = explain.get("direction")
    unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
    colors = _ds_choropleth(values)

    # Ranking is oriented by direction (1 = doing best), while high/low stay
    # purely about the value, matching what the two callouts actually say.
    ranked = list(reversed(values)) if direction in ("lower_better", "higher_worse") else values
    rank_by_key = {row["region_key"]: position for position, row in enumerate(ranked, 1)}
    total = len(ranked)

    readout = {
        row["region_key"]: {
            "name": row["region"],
            "value": it_num(row["value"], 2),
            "unit": unit,
            "rank": rank_by_key[row["region_key"]],
            "total": total,
        }
        for row in values
    }

    def extreme(row, label):
        return {
            "key": row["region_key"],
            "name": row["region"],
            "value": it_num(row["value"], 2),
            "color": colors.get(row["region_key"]),
            "label": label,
        }

    highest, lowest = values[0], values[-1]
    return {
        "options": options,
        "selected_id": selected_id,
        "indicator_name": meta["name"],
        "indicator_path": meta["path"],
        "theme": meta["theme"],
        "year": year,
        "unit": unit,
        "source_label": meta.get("catalog_family_label"),
        "direction": direction,
        "colors": colors,
        "readout": readout,
        "high": extreme(highest, "Valore più alto"),
        "low": extreme(lowest, "Valore più basso"),
        "scale_low": _ds_short_value(lowest["value"], unit),
        "scale_high": _ds_short_value(highest["value"], unit),
        "ramp": list(_DS_SEQ_RAMP[:5]),
    }


def _home_series_module():
    """The comparison module: one indicator's regional time series, a set of
    regions to toggle, and the simple mean of the regions as the reference.

    The three default regions are rendered server-side so the chart is already
    drawn without JavaScript; ds-home.js redraws it when the selection
    changes."""
    payload = get_atlas_indicator(_HOME_SERIES_INDICATOR)
    if payload is None:
        return None
    meta = payload["metadata"]
    unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))

    by_region = {}
    for row in payload["series"]:
        if row.get("value") is None:
            continue
        by_region.setdefault(row["region_key"], {})[row["year"]] = row["value"]

    available = [key for key in _HOME_SERIES_CHOICES if key in by_region]
    if len(available) < 2:
        return None

    # Only the years every offered region covers, so no line has a hole in it.
    years = sorted(set.intersection(*(set(by_region[key]) for key in available)))
    if len(years) < 2:
        return None

    # The reference is the simple mean of the regions, described as such: it is
    # not an official national aggregate and must never be labelled as one.
    all_regions = [key for key in by_region if set(years) <= set(by_region[key])]
    reference = [
        sum(by_region[key][year] for key in all_regions) / len(all_regions)
        for year in years
    ]

    latest = years[-1]
    direction = (meta.get("explain") or {}).get("direction")
    latest_values = get_atlas_indicator_year(_HOME_SERIES_INDICATOR, latest)["values"]
    ranked = list(reversed(latest_values)) if direction in ("lower_better", "higher_worse") else latest_values
    rank_by_key = {row["region_key"]: position for position, row in enumerate(ranked, 1)}

    regions = []
    for index, key in enumerate(available):
        series = [by_region[key][year] for year in years]
        regions.append({
            "key": key,
            "name": profiles.region_name(key),
            "color": _HOME_SERIES_COLORS[index % len(_HOME_SERIES_COLORS)],
            "series": series,
            "value": it_num(series[-1], 2),
            "rank": rank_by_key.get(key),
            "total": len(ranked),
        })

    defaults = [key for key in _HOME_SERIES_DEFAULT if key in by_region][:3]
    if not defaults:
        defaults = [region["key"] for region in regions[:3]]

    initial = _home_series_polylines(regions, reference, defaults)
    if initial is None:
        return None

    return {
        "indicator_name": meta["name"],
        "indicator_path": meta["path"],
        "theme": meta["theme"],
        "unit": unit,
        "source_label": meta.get("catalog_family_label"),
        "years": years,
        "regions": regions,
        "default_keys": defaults,
        "initial": initial,
        "reference": {
            "label": f"Media semplice delle {len(all_regions)} regioni",
            "short_label": "Media delle regioni",
            "series": reference,
            "value": it_num(reference[-1], 2),
        },
    }


# Geometria del grafico di confronto. Deve restare identica a quella in
# static/js/ds-home.js: il server disegna la selezione iniziale e il client
# ridisegna quando cambia, quindi le due versioni devono sovrapporsi esatte.
# Il viewBox e volutamente largo (260x60, circa 4.3:1) e il grafico lo rende
# con il preserveAspectRatio predefinito: con "none" le coordinate venivano
# schiacciate in orizzontale e i punti finali delle serie uscivano come ellissi.
_CHART_W, _CHART_H = 260.0, 60.0
_CHART_PAD_L, _CHART_PAD_R, _CHART_PAD_T, _CHART_PAD_B = 4.0, 30.0, 4.0, 6.0


def _home_series_polylines(regions, reference, selected_keys):
    """Polilinee della selezione iniziale, cosi il grafico e gia disegnato
    nell'HTML invece di restare un rettangolo vuoto senza JavaScript."""
    chosen = [region for region in regions if region["key"] in selected_keys]
    if not chosen or len(reference) < 2:
        return None

    numbers = [value for region in chosen for value in region["series"]] + list(reference)
    low, high = min(numbers), max(numbers)
    span = (high - low) or 1.0
    last_index = len(reference) - 1
    plot_w = _CHART_W - _CHART_PAD_L - _CHART_PAD_R
    plot_h = _CHART_H - _CHART_PAD_T - _CHART_PAD_B

    def position(index, value):
        x = _CHART_PAD_L + (index / last_index) * plot_w
        y = _CHART_PAD_T + (1 - (value - low) / span) * plot_h
        return x, y

    def points(series):
        return " ".join(
            "{:.1f},{:.1f}".format(*position(index, value))
            for index, value in enumerate(series)
        )

    return {
        "baseline": {
            "x1": f"{_CHART_PAD_L:.1f}",
            "x2": f"{_CHART_W - _CHART_PAD_R:.1f}",
            "y": f"{_CHART_H - _CHART_PAD_B:.1f}",
        },
        "reference": points(reference),
        "lines": [
            {
                "key": region["key"],
                "name": region["name"],
                "color": region["color"],
                "points": points(region["series"]),
                "end": dict(zip(("x", "y"), (
                    f"{position(last_index, region['series'][-1])[0]:.1f}",
                    f"{position(last_index, region['series'][-1])[1]:.1f}",
                ))),
            }
            for region in chosen
        ],
    }


def _home_qol_module():
    """Quality-of-life ranking for every published weighting profile, so the
    homepage can switch profile without a round trip. Each profile carries its
    own top three, bottom three and score spread: changing the weights changes
    the answer, which is the point the module is making."""
    profiles_payload = []
    for slug, config_entry in QUALITY_LIFE_PROFILES.items():
        payload = qb.build_bes_ranking("regione", slug)
        if payload is None:
            continue
        ranking = payload["ranking"]
        if len(ranking) < 6:
            continue
        profiles_payload.append({
            "slug": slug,
            "name": config_entry["name"],
            "description": config_entry["description"],
            "top": [
                {"rank": row["rank"], "name": row["name"], "score": round(row["score"])}
                for row in ranking[:3]
            ],
            "bottom": [
                {"rank": row["rank"], "name": row["name"], "score": round(row["score"])}
                for row in reversed(ranking[-3:])
            ],
            "gap": round(ranking[0]["score"] - ranking[-1]["score"]),
        })
    if not profiles_payload:
        return None
    return {"profiles": profiles_payload, "default_slug": qb.DEFAULT_PROFILE}


def _home_featured_story():
    """The lead data story: the first story indicator, with the two leading
    regions, the mean of the regions and the two trailing ones as bars, so the
    spread the headline talks about is visible in one glance."""
    for indicator_id in _HOME_STORY_INDICATORS:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        if len(values) < 6:
            continue

        explain = meta.get("explain") or {}
        direction = explain.get("direction")
        invert = direction in ("lower_better", "higher_worse")
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))

        numbers = [row["value"] for row in values]
        low, high = min(numbers), max(numbers)
        span = (high - low) or 1.0
        mean = sum(numbers) / len(numbers)

        def bar(name, value):
            fraction = (value - low) / span
            return {
                "name": name,
                "value": it_num(value, 2),
                "pct": max(4, round(fraction * 100)),
                "color": _ds_ramp_color(fraction),
            }

        rows = [bar(row["region"], row["value"]) for row in values[:2]]
        rows.append(bar("Media delle regioni", mean))
        rows.extend(bar(row["region"], row["value"]) for row in values[-2:])

        ranked = list(reversed(values)) if invert else values
        best, worst = ranked[0], ranked[-1]
        return {
            "theme": meta["theme"],
            "name": meta["name"],
            "path": meta["path"],
            "year": year,
            "unit": unit,
            "source_label": meta.get("catalog_family_label"),
            "rows": rows,
            "spread": it_num(high - low, 2),
            "lead_region": best["region"],
            "lead_value": it_num(best["value"], 2),
            "lag_region": worst["region"],
            "lag_value": it_num(worst["value"], 2),
            "summary": explain.get("plain") or "",
            "direction_note": (
                "Per questo indicatore un valore più basso indica una situazione migliore."
                if invert else
                "Per questo indicatore un valore più alto indica una situazione migliore."
                if direction in ("higher_better", "lower_worse") else
                "Questo indicatore non ha una direzione migliore o peggiore dichiarata."
            ),
        }
    return None


def _home_insight_cards():
    """Two secondary readings under the lead story, built from the remaining
    story indicators so nothing on the page is written by hand."""
    cards = []
    for indicator_id in _HOME_STORY_INDICATORS[1:]:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        if len(values) < 2:
            continue
        direction = (meta.get("explain") or {}).get("direction")
        invert = direction in ("lower_better", "higher_worse")
        ranked = list(reversed(values)) if invert else values
        best, worst = ranked[0], ranked[-1]
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
        cards.append({
            "theme": meta["theme"],
            "name": meta["name"],
            "path": meta["path"],
            "year": year,
            "unit": unit,
            "source_label": meta.get("catalog_family_label"),
            "lead_region": best["region"],
            "lead_value": it_num(best["value"], 2),
            "lag_region": worst["region"],
            "lag_value": it_num(worst["value"], 2),
            "summary": (meta.get("explain") or {}).get("plain") or "",
        })
        if len(cards) == 2:
            break
    return cards


def _home_paths(summary, themes_preview):
    """The four exploration entry points, with the counts each one actually
    opens onto. A path that cannot state its size is a path nobody trusts."""
    theme_count = sum(card["theme_count"] for card in themes_preview) if themes_preview else 0
    area_count = len(themes_preview or [])
    return [
        {
            "eyebrow": "Una regione",
            "body": "Apri il profilo di un territorio: dove emerge, dove fatica, come si è mosso.",
            "meta": "20 profili regionali",
            "href": "/regioni",
            "cta": "Sfoglia le regioni",
            "path": "regione",
        },
        {
            "eyebrow": "Un tema",
            "body": "Economia, lavoro, salute, ambiente e gli altri grandi ambiti territoriali.",
            "meta": f"{area_count} aree, {theme_count} temi",
            "href": "/temi",
            "cta": "Esplora i temi",
            "path": "tema",
        },
        {
            "eyebrow": "Un confronto",
            "body": "Metti due o tre territori sullo stesso indicatore e segui la loro evoluzione.",
            "meta": "Fino a 3 territori",
            "href": "/confronto",
            "cta": "Confronta le regioni",
            "path": "confronto",
        },
        {
            "eyebrow": "Il divario territoriale",
            "body": "Leggi le differenze tra Nord, Centro e Mezzogiorno oltre le semplificazioni.",
            "meta": "Nord, Centro, Mezzogiorno",
            "href": "/divari-regionali",
            "cta": "Esplora i divari",
            "path": "divari",
        },
    ]


def _home_trust_cards(summary):
    """Sources, updates, method and corrections: the four things a reader has
    to be able to check before trusting a number on this site."""
    return [
        {
            "kicker": "Fonti",
            "title": f"{summary['institutions_label']} e altre fonti istituzionali",
            "body": "Ogni serie riporta l'ente che la produce e l'ultimo anno disponibile.",
            "href": "/metodologia",
            "cta": "Tutte le fonti",
        },
        {
            "kicker": "Copertura",
            "title": f"{summary['total']} indicatori, 20 regioni, dal {summary['year_min']} al {summary['year_max']}",
            "body": "Il catalogo viene rivisto a ogni nuovo rilascio ufficiale.",
            "href": "/catalogo-dati",
            "cta": "Sfoglia il catalogo",
        },
        {
            "kicker": "Metodo",
            "title": "Definizione, unità, fonte e copertura restano su ogni indicatore",
            "body": "Le scelte metodologiche sono documentate e citabili.",
            "href": "/metodologia",
            "cta": "Consulta la metodologia",
        },
        {
            "kicker": "Correzioni",
            "title": "Segnala un errore o consulta le correzioni pubblicate",
            "body": "Le rettifiche restano tracciate e pubbliche.",
            "href": "/chi-siamo",
            "cta": "Correzioni e contatti",
        },
    ]


def _clean_event_name(value):
    value = str(value or "")[:64]
    return value if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", value) else ""


def _clean_event_params(value):
    if not isinstance(value, dict):
        return {}
    params = {}
    for key, raw in value.items():
        clean_key = _clean_event_name(key)
        if not clean_key:
            continue
        clean_value = _clean_event_value(raw)
        if clean_value != "":
            params[clean_key] = clean_value
        if len(params) >= 12:
            break
    return params


def _clean_event_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if value is None:
        return ""
    return " ".join(str(value).split())[:160]
