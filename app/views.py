from app import app
from app.cache import cache
from app.blog import SITE_NAME, SITE_URL, all_tags, get_post, get_posts, posts_for_indicator
from app.data import (
    get_catalog,
    get_indicator,
    get_indicator_year,
    get_rows,
    indicator_trend_stats,
    indicator_year_over_year_stats,
)
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
from app import indicator_view
from app import quality_life_bes as qb
from app import bes_data
from app import multiscopo_data
from app import external_atlas
from app import external_manifest
from app import game
from app import quiz
from app import quiz_tokens
from app import leaderboard
from app import moderation
from app import public_urls
from app import publisher
from app import agent_discovery

from flask import Response, abort, make_response, redirect, render_template, request, send_from_directory, url_for
from flask.json import jsonify

import csv, hmac, io, json, os, re, time, unicodedata
from collections import defaultdict
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
    return render_template(
        "home.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/",
        total_indicators=total_indicators,
        sources_label=summary["institutions_label"],
        year_min=summary["year_min"],
        year_max=summary["year_max"],
        map_hero=_home_map_hero(),
        capabilities=_home_capabilities(total_indicators),
        stories=_home_story_cards(),
        themes_preview=_home_themes_preview(),
        compare_preview=_home_compare_preview(),
        qol=_home_qol_preview(),
        quiz_games=_home_quiz_games(),
        posts=recent_posts,
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
    osservazioni provinciali, che pero' hanno una pagina indicizzabile ed entrano
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
        # L'entita' editore condivisa (con @id /chi-siamo#organizzazione), la
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

    Non e' una seconda tassonomia sopra /temi e /regioni: quelle pagine servono a
    sfogliare, questa sostiene una tesi (il divario non e' una linea sola) e la
    misura sul catalogo, ripartizione per ripartizione. Ogni numero in pagina e'
    ricalcolato dai dati a ogni render, cosi' la prosa non puo' invecchiare.
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
    funzionava, ma non aveva una URL da condividere ne' un titolo suo. Qui la
    pagina e' server-rendered, quindi chi arriva senza JavaScript legge un
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

    Uno spazio `?q=` e' illimitato per costruzione: indicizzarlo produrrebbe un
    numero arbitrario di pagine sottili, ognuna un sottoinsieme di righe che
    esistono gia' sulle schede. Qui la pagina serve a chi cerca, non a Google:
    funziona senza JavaScript, si condivide, e i suoi link restano `follow`
    cosi' l'equity scorre verso le pagine indicatore e gli articoli.
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
    """Il path canonico della pagina pubblicata di un indicatore, o None.

    Riusa il path precomputato dal catalogo (`build_indicator_view`), preferito
    al ricalcolo dello slug come vuole `.claude/rules/app.md`. La view Flask puo'
    importare il catalogo, cosi' `pipeline_monitor` resta stdlib-puro. Se l'id non
    si risolve, niente link invece di un errore: il cruscotto non deve cadere per
    una riga."""
    try:
        from app import indicator_view, sources
        family, raw_id = sources.split_internal_id(indicator_id)
        view = indicator_view.build_indicator_view(family, raw_id)
        return (view or {}).get("meta", {}).get("canonical_path") or None
    except Exception:  # noqa: BLE001
        return None


@app.route("/_pipeline")
def pipeline_dashboard():
    """Cruscotto interno della catena editoriale, protetto e noindex.

    Vista di lettura viva sul dossier per-indicatore (`scripts/pipeline_monitor`):
    dov'e' fermo e perche' in testa, una riga per indicatore, le sessioni in volo
    dai battiti, la storia recente dal diario. Ricalcolata a ogni caricamento dai
    file committati, non da uno stato a parte: il monitoraggio e' una lettura
    dello stesso modello che la catena produce, non un secondo modello.

    Protetta: se `PIPELINE_TOKEN` e' impostato, serve solo con `?token=` giusto,
    altrimenti 404, non 403, perche' una pagina interna non deve nemmeno
    confermare di esistere. Vuoto (locale) = aperta. Il noindex lo mette
    `add_security_headers` sul prefisso `/_pipeline`.
    """
    token = config.PIPELINE_TOKEN
    if token and request.args.get("token") != token:
        abort(404)
    from scripts import pipeline_monitor
    from app import pipeline_state
    # Il vivo arriva dal SQLite (scritto dai POST degli agenti, replicato su GCS),
    # non piu' da file locali che sul server sarebbero sempre vuoti. La storia
    # (dossier + diario) resta committata, come prima.
    try:
        activity = pipeline_state.live()
    except Exception:  # noqa: BLE001  (il cruscotto non deve mai cadere per il vivo)
        activity = {"beats": [], "prs": []}
    board = pipeline_monitor.load_board(heartbeats=activity["beats"],
                                        open_runs=activity["prs"])
    # Telemetria token: durevole, dal SQLite, chiavata sul run_id del ruolo.
    try:
        tokens = pipeline_state.tokens_by_run()
    except Exception:  # noqa: BLE001  (la telemetria non deve far cadere il cruscotto)
        tokens = {}
    # I token si attribuiscono solo all'indicatore bersaglio della run (dal
    # record), non a ogni indicatore che la run cita come confronto: la logica
    # sta nel monitor stdlib-puro, cosi' e' testabile senza Flask.
    pipeline_monitor.attribute_tokens(board.get("rows", []), tokens)
    # Le righe pubblicate portano il link alla pagina: poche righe (published=True),
    # quindi il costo di build_indicator_view resta trascurabile.
    for row in board.get("rows", []):
        row["published_url"] = (_pipeline_published_url(row["id"])
                                if row.get("published") is True else None)
    return render_template("pipeline.html", board=board,
                           token=request.args.get("token", ""),
                           site_name=SITE_NAME)


@app.post("/_pipeline/beat")
def pipeline_beat_ingest():
    """Il vivo del cruscotto: gli agenti della catena POSTano qui i battiti.

    Autenticato con `PIPELINE_INGEST_TOKEN` (header `X-Pipeline-Key`), come
    l'endpoint admin della leaderboard: segreto sbagliato o assente -> 404, non
    403, perche' un endpoint interno non conferma nemmeno di esistere. Il corpo e'
    JSON con un campo `action`:

      {"action":"beat","run_id":...,"role":...,"indicator":...,"stage":...}
      {"action":"close","run_id":...}
      {"action":"prs","prs":[{"pr":..,"branch":..,"run_id":..,"ci":..,"mergeable":..,"title":..}]}
      {"action":"tokens","run_id":...,"tokens":N,"indicator":...,"stage":...,"role":...}

    Best effort per chi chiama: un agente che non riesce a battere non deve
    fallire la propria run, quindi qui si e' solo tolleranti e si risponde presto.
    """
    token = config.PIPELINE_INGEST_TOKEN
    provided = request.headers.get("X-Pipeline-Key", "")
    if not token or not hmac.compare_digest(provided, token):
        abort(404)
    from app import pipeline_state
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    try:
        if action == "beat":
            pipeline_state.record_beat(
                payload.get("run_id", ""), role=payload.get("role", ""),
                indicator=payload.get("indicator", ""), stage=payload.get("stage", ""))
        elif action == "close":
            pipeline_state.close_beat(payload.get("run_id", ""))
        elif action == "prs":
            pipeline_state.replace_prs(payload.get("prs") or [])
        elif action == "tokens":
            pipeline_state.record_tokens(
                payload.get("run_id", ""), payload.get("tokens"),
                indicator=payload.get("indicator", ""), stage=payload.get("stage", ""),
                role=payload.get("role", ""))
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
    return render_template(
        "methodology.html",
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/metodologia",
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

    response = make_response(render_template(
        "indicator_page.html",
        meta=meta,
        levels=view["levels"],
        level=level,
        related=view["related"],
        related_posts=posts_for_indicator(meta["id"]),
        siblings=view["siblings"],
        explore=view["explore"],
        page_article=article,
        page_lead=lead,
        noindex=noindex,
        seo_title=indicator_notes.seo_title(meta["name"], SITE_NAME),
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
    """Compact per-region summary for the SPA 'per regione' selection map.

    Same source as the /regioni page; no overall regional score is exposed here.
    """
    return jsonify(profiles.regions_overview())


@app.route("/api/region/<region_key>")
def region_api(region_key):
    """JSON del profilo regione, per la vista 'per regione' della SPA.

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
    regioni = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    province = qb.build_bes_ranking("provincia", qb.DEFAULT_PROFILE)
    return render_template(
        "quality_life_methodology.html",
        methodology_regioni=regioni["methodology"] if regioni else None,
        methodology_province=province["methodology"] if province else None,
        categories=qb.get_quality_life_categories(),
        profiles=qb.get_quality_life_profiles(),
        quality_life_indicators=[
            item for item in get_atlas_catalog()["indicators"]
            if item["quality_life_scored"]
        ],
        site_url=SITE_URL,
        site_name=SITE_NAME,
        canonical=f"{SITE_URL}/qualita-della-vita/metodologia",
    )


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
    return jsonify(result)


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
    entries = leaderboard.top(mode, period, limit)
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
    leaderboard.submit(mode, state["sid"], nickname, score, detail)
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
    return jsonify(result)


_indexable_catalog_lock = threading.Lock()


def _indexable_indicator_catalog():
    """Accessore single-flight al catalogo proiettato: serializza la prima
    costruzione a freddo.

    `lru_cache` non coalizza i miss concorrenti. Il worker gunicorn di produzione
    ha un thread solo per processo? No: un worker, **otto thread** (vedi
    `Dockerfile`), e `/sitemap.xml` e `/llms-full.txt` sono rotte non cached. Due
    richieste crawler simultanee a freddo entrerebbero entrambe nel corpo prima
    che il primo risultato sia in cache, e ognuna rifarebbe la traversata di
    centinaia di indicatori (secondi di CPU), moltiplicando il lavoro fino al
    timeout. Il lock fa costruire una volta sola: il primo popola la cache di
    `_build_indexable_indicator_catalog`, gli altri aspettano e leggono il
    risultato gia' pronto (un lookup, quindi il lock si tiene un istante)."""
    with _indexable_catalog_lock:
        return _build_indexable_indicator_catalog()


@lru_cache(maxsize=1)
def _build_indexable_indicator_catalog():
    """One deduplicated catalog for indicator pages, sitemap and LLM exports.

    ``build_indicator_view`` owns both canonical URLs and the family-specific
    indexability policy.  Starting from every family registry also retains BES
    series that only have provincial observations and therefore do not enter the
    regional atlas catalog.

    Building the full view for every indicator is expensive (hundreds of
    histories and matrices), and ``sitemap.xml``/``llms-full.txt`` are
    uncached crawler routes that would otherwise repeat that cost on every
    hit. The source loaders already cache for the life of the process, so this
    catalog is stable too: memoize it once instead of rebuilding per request.

    **Cached is a compact projection, not the full views.** A full view carries
    every level's observation history and year-by-territory explore matrix, and
    retaining all of them for the process lifetime added roughly 110 MiB per
    worker on the first crawler hit. The two callers only read ``meta`` and a
    small per-level summary (label, year span, territory count in the last year),
    so that is all this keeps: the heavy view is dropped as soon as the summary
    is taken. Callers must not mutate the result.
    """
    candidates = []
    candidates.extend(("territorial", str(item["id"])) for item in get_catalog()["indicators"])
    candidates.extend(("bes", str(item["id"])) for item in bes_data.all_bes_indicators())
    if multiscopo_data.has_multiscopo_data():
        candidates.extend(
            ("multiscopo", str(item["id"]))
            for item in multiscopo_data.all_multiscopo_indicators()
        )
    if external_atlas.has_external_data():
        candidates.extend(
            sources.split_internal_id(item["id"])
            for item in external_atlas.all_external_indicators()
        )

    catalog = []
    seen_paths = set()
    for family, raw_id in candidates:
        view = indicator_view.build_indicator_view(family, raw_id)
        if view is None or not view["meta"]["indexable"]:
            continue
        path = view["meta"]["canonical_path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        catalog.append({
            "meta": view["meta"],
            "levels": [
                {"label": level["label"], "year_min": level["year_min"],
                 "year_max": level["year_max"],
                 "territory_count": len(level["observations"])}
                for level in view["levels"]
            ],
        })
    return sorted(catalog, key=lambda record: record["meta"]["canonical_path"])


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
        {"loc": f"{SITE_URL}/qualita-della-vita/metodologia", "priority": "0.6"},
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
    if not config.ADSENSE_CLIENT:
        abort(404)
    pub = config.ADSENSE_CLIENT.replace("ca-", "")
    return Response(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", mimetype="text/plain")


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


def _home_map_hero():
    return _map_hero(_HOME_MAP_INDICATORS)


def _home_capabilities(total_indicators):
    return [
        {
            "kicker": "Atlante",
            "title": f"{total_indicators} indicatori esplorabili",
            "body": "Tutti gli indicatori Istat delle politiche di sviluppo, per tema e completezza.",
            "href": "/atlante",
            "cta": "Apri l'atlante",
        },
        {
            "kicker": "Regioni",
            "title": "Schede regione",
            "body": "Punti di forza, punti deboli e ranking tematico per tutte le 20 regioni.",
            "href": "/regioni",
            "cta": "Sfoglia le regioni",
        },
        {
            "kicker": "Confronta",
            "title": "Regione contro regione",
            "body": "Metti a confronto due o tre regioni su qualsiasi indicatore, con mappa e serie storica.",
            "href": "/confronto",
            "cta": "Confronta ora",
        },
        {
            "kicker": "Temi",
            "title": "Aree e temi",
            "body": "Economia, lavoro, salute, ambiente: ogni tema raccoglie i suoi indicatori in una pagina.",
            "href": "/temi",
            "cta": "Scopri i temi",
        },
        {
            "kicker": "Qualità della vita",
            "title": "Classifica composita",
            "body": "Un indice sperimentale che unisce salute, lavoro, istruzione e ambiente.",
            "href": "/qualita-della-vita",
            "cta": "Vedi la classifica",
        },
        {
            "kicker": "Quiz",
            "title": "Metti alla prova quello che sai",
            "body": "Tre giochi rapidi sui dati Istat, con una classifica settimanale.",
            "href": "/quiz",
            "cta": "Gioca ora",
        },
    ]


def _home_story_cards():
    """Real 'chi guida, chi resta indietro' highlights for the homepage,
    limited to indicators with a declared higher_better/lower_better
    direction so the framing is something the data actually supports."""
    cards = []
    for indicator_id in _HOME_STORY_INDICATORS:
        payload = get_atlas_indicator(indicator_id)
        if payload is None:
            continue
        meta = payload["metadata"]
        year = meta["year_max"]
        values = get_atlas_indicator_year(indicator_id, year)["values"]
        direction = (meta.get("explain") or {}).get("direction")
        ranked = list(reversed(values)) if direction in ("lower_better", "higher_worse") else values
        best, worst = ranked[0], ranked[-1]
        unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
        if direction == "lower_better":
            note = (
                f"{worst['region']} resta indietro con {it_num(worst['value'], 2)} {unit}, "
                f"{best['region']} fa meglio di tutte."
            )
        else:
            note = (
                f"{best['region']} guida con {it_num(best['value'], 2)} {unit}, "
                f"{worst['region']} chiude a {it_num(worst['value'], 2)} {unit}."
            )
        cards.append({
            "theme": meta["theme"],
            "name": meta["name"],
            "value": it_num(best["value"], 2),
            "unit": unit,
            "best_region": best["region"],
            "year": year,
            "note": note,
            "spark_points": indicator_notes.sparkline_points(meta.get("spark") or [], width=84, height=36),
            "path": profiles.indicator_path(indicator_id, meta["name"]),
        })
    return cards


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
    """'Temi e aree' cards: for each macro-area, its indicator/theme counts plus
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
    """Full '/temi' page: every macro-area with its themes, and for each theme
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
                # /confronto rende lo stesso confronto senza JavaScript, e la'
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
