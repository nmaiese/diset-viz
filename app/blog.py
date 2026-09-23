"""File-based blog: Markdown posts with YAML frontmatter.

Drop a `.md` file in `content/posts/` and it is published automatically — this is
the surface an AI agent writes to. Posts are server-rendered (Jinja) so they are
fully crawlable and SEO-friendly. Frontmatter supports optional `seo_title` when
the browser title should be shorter than the visible H1.
"""

import datetime as dt
import re
from pathlib import Path

import frontmatter
import markdown

from app import sources
from app.cache import cache
from app.config import SITE_NAME, SITE_URL

POSTS_DIR = Path(__file__).resolve().parents[1] / "content" / "posts"
FIGURE_DIR = Path(__file__).resolve().parents[1] / "content" / "figure"
_FIGURA_RE = re.compile(r"<!--\s*figura:\s*([a-z0-9][a-z0-9-]*)\s*-->")
STATIC_DIR = Path(__file__).resolve().parent / "static"

# La figura di ripiego per chi condivide una pagina senza copertina propria.
# PNG e non SVG, per la ragione scritta in `social_image`.
SOCIAL_FALLBACK = "/static/img/og-divario-italia.png"

# How many articles an indicator page lists. Three is the whole point of the
# widget: enough to show the indicator has been written about, few enough that
# the apparatus stays an apparatus.
POSTS_PER_INDICATOR = 3

# No "smarty": it would auto-convert -- and ... into en/em dashes and ellipses,
# exactly the typographic artifacts we want to keep out of the prose.
_MD_EXTENSIONS = ["extra", "sane_lists", "toc", "attr_list"]


def _slugify(value):
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _read_time(text):
    words = len(re.findall(r"\w+", text))
    return max(1, round(words / 200))


def _coerce_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return dt.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _excerpt(meta, html):
    if meta.get("description"):
        return meta["description"]
    text = re.sub(r"<[^>]+>", "", html)
    text = " ".join(text.split())
    if len(text) <= 158:
        return text
    return text[:157].rsplit(" ", 1)[0] + "..."


def social_image(cover):
    """La copertina nella forma che un social sa disegnare, o il ripiego.

    Nessun lettore di anteprime apre un SVG: Facebook, LinkedIn, X, WhatsApp e
    Slack scartano l'immagine e mostrano il link nudo, e lo stesso vale per
    `image` dello schema `Article`, dove Google chiede un raster. Le copertine
    del blog erano tutte SVG, quindi ogni condivisione di ogni post usciva
    senza figura sotto un `twitter:card=summary_large_image`, cioe' il formato
    che esiste apposta per mostrarne una grande.

    Il PNG lo scrive `scripts/rasterize_og_images.py` accanto al sorgente e si
    committa. Qui si guarda se c'e': una copertina nuova senza la sua passata
    di conversione ripiega sulla figura del sito invece di far uscire una
    scheda rotta. In pagina la copertina resta l'SVG, che e' la forma giusta
    per uno schermo.
    """
    if not cover:
        return SOCIAL_FALLBACK
    if not cover.endswith(".svg"):
        return cover
    raster = cover[: -len(".svg")] + ".png"
    percorso = STATIC_DIR / raster.removeprefix("/static/")
    return raster if percorso.exists() else SOCIAL_FALLBACK


def social_image_size(path):
    """(larghezza, altezza) di una figura sociale, o None se non si sanno.

    `og:image:width` e `og:image:height` servono a far disegnare la scheda
    prima che l'immagine sia scaricata, ma dichiararle sbagliate e' peggio che
    non dichiararle: le tre copertine in JPG sono 1376x768, non 1200x630, e
    scriverci sopra la misura dei PNG darebbe un ritaglio storto.

    Qui si leggono solo i PNG, dove la misura sta in otto byte a offset 16 e
    non serve nessuna libreria. Per gli altri formati si torna None e il
    template non dichiara niente, che e' il comportamento di prima.
    """
    if not path or not path.endswith(".png"):
        return None
    percorso = STATIC_DIR / path.removeprefix("/static/")
    try:
        with percorso.open("rb") as file:
            testa = file.read(24)
    except OSError:
        return None
    if len(testa) < 24 or testa[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(testa[16:20], "big"), int.from_bytes(testa[20:24], "big")


def _normalize_indicator(value):
    """Frontmatter `indicator:` -> the catalog id the atlas resolves.

    Two spellings are accepted, and both mean the same indicator:

        indicator: 408          a bare id, i.e. the territorial family
        indicator: ter-408      the unified URL code, any family

    The second form is the one the reader sees in the address bar, so an author
    can copy it straight out of the link they just pasted into the article. It
    is also the only way to point a post at a non-territorial family: a bare
    "01SAL001" would silently resolve to nothing.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    parsed = sources.parse_indicator_code(raw)
    if parsed is not None:
        return sources.internal_id(*parsed)
    return raw


def _figure(body_html, slug):
    """`<!-- figura: nome -->` -> l'SVG di `content/figure/<slug>/<nome>.svg`.

    Le figure le scrive `scripts/articoli_trend/grafici.py` dai numeri del
    dossier del pezzo. Vanno in linea e non in un `<img>` perche' i loro
    colori sono classi che leggono i token del design system: in un `<img>`
    la figura resterebbe chiara sotto il tema scuro. Un marcatore senza file
    sparisce e il testo resta intero, come per le figure delle schede.
    """

    def sostituisci(match):
        percorso = FIGURE_DIR / slug / f"{match.group(1)}.svg"
        if not percorso.is_file():
            return ""
        return f'<figure class="fig-articolo">{percorso.read_text(encoding="utf-8")}</figure>'

    return _FIGURA_RE.sub(sostituisci, body_html)


def _cover_credit(meta):
    """L'attribuzione della foto di copertina, o None.

    Una foto con licenza CC BY o CC BY-SA si usa solo dicendo chi l'ha fatta,
    con che licenza e dove sta l'originale: e' la condizione della licenza,
    non una cortesia. I campi li scrive `scripts/articoli_trend/foto.py`
    leggendoli da Wikimedia Commons, non chi redige.
    """
    credit = meta.get("cover_credit")
    if not isinstance(credit, dict) or not credit.get("autore") or not credit.get("licenza"):
        return None
    return {
        "autore": str(credit["autore"]).strip(),
        "licenza": str(credit["licenza"]).strip(),
        "licenza_url": str(credit.get("licenza_url") or "").strip(),
        "fonte_url": str(credit.get("fonte_url") or "").strip(),
        "fonte_nome": str(credit.get("fonte_nome") or "Wikimedia Commons").strip(),
        "modifiche": str(credit.get("modifiche") or "").strip(),
    }


def _dataset(meta, slug):
    """Il blocco `dataset:` del frontmatter, pronto per lo schema `Dataset`.

    Un articolo che mostra dati li dichiara: che cosa sono, da dove vengono,
    con che licenza, come sono stati elaborati e dove si scaricano.
    """
    ds = meta.get("dataset")
    if not isinstance(ds, dict) or not ds.get("name"):
        return None
    download = str(ds.get("download") or "").strip()
    return {
        "name": str(ds["name"]).strip(),
        "description": str(ds.get("description") or "").strip(),
        "license": str(ds.get("license") or sources.LICENSE_URL).strip(),
        "creator": str(ds.get("creator") or "Istat").strip(),
        "method": str(ds.get("method") or "").strip(),
        "temporal": str(ds.get("temporal") or "").strip(),
        "spatial": str(ds.get("spatial") or "Italia").strip(),
        "source_url": str(ds.get("source_url") or "").strip(),
        "download": download,
        "download_abs": f"{SITE_URL}{download}" if download.startswith("/") else download,
        "url": f"{SITE_URL}/blog/{slug}",
    }


def _load_post(path):
    post = frontmatter.load(path)
    meta = post.metadata
    if meta.get("draft"):
        return None

    title = (meta.get("title") or path.stem).strip()
    slug = _slugify(meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem))
    md = markdown.Markdown(extensions=_MD_EXTENSIONS, output_format="html5")
    body_html = _figure(md.convert(post.content), slug)

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    date = _coerce_date(meta.get("date")) or dt.date.today()
    updated = _coerce_date(meta.get("updated"))
    date_modified = updated if updated and updated >= date else date

    return {
        "slug": slug,
        "title": title,
        "seo_title": (meta.get("seo_title") or "").strip(),
        "description": _excerpt(meta, body_html),
        "date": date,
        "date_modified": date_modified,
        "author": (meta.get("author") or SITE_NAME).strip(),
        "cover": meta.get("cover"),
        "cover_alt": meta.get("cover_alt") or title,
        "cover_credit": _cover_credit(meta),
        "cover_caption": (meta.get("cover_caption") or "").strip(),
        "dataset": _dataset(meta, slug),
        # La stessa figura in un formato che un social e uno schema sanno
        # leggere: `cover` resta l'SVG che va in pagina.
        "social_image": social_image(meta.get("cover")),
        "social_image_size": social_image_size(social_image(meta.get("cover"))),
        "tags": tags,
        "indicator": _normalize_indicator(meta.get("indicator")),
        "indicator_label": meta.get("indicator_label"),
        "read_time": _read_time(post.content),
        # Keep the source representation beside the rendered HTML so content
        # negotiation can serve the article without reversing HTML back into
        # lossy Markdown.
        "body_markdown": post.content,
        "body_html": body_html,
        "url": f"{SITE_URL}/blog/{slug}",
    }


@cache.memoize(timeout=60)
def get_posts():
    if not POSTS_DIR.exists():
        return []
    posts = []
    for path in POSTS_DIR.glob("*.md"):
        loaded = _load_post(path)
        if loaded:
            posts.append(loaded)
    posts.sort(key=lambda item: item["date"], reverse=True)
    return posts


def get_post(slug):
    return next((post for post in get_posts() if post["slug"] == slug), None)


def posts_for_indicator(indicator_id, limit=POSTS_PER_INDICATOR):
    """Articles written about one indicator, newest first.

    The reverse of the link a post already declares in its frontmatter. The
    forward direction (post -> indicator) has always existed; without this one
    the two halves of the site never referred to each other, and an indicator
    page was a dead end for a reader who wanted the story behind the number.

    `indicator_id` is the catalog id (``meta["id"]``), so a page gets its own
    posts whatever family it belongs to.
    """
    if not indicator_id:
        return []
    wanted = str(indicator_id)
    matched = [post for post in get_posts() if post["indicator"] == wanted]
    return matched[:limit] if limit else matched


def all_tags():
    counts = {}
    for post in get_posts():
        for tag in post["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))
