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


def _load_post(path):
    post = frontmatter.load(path)
    meta = post.metadata
    if meta.get("draft"):
        return None

    title = (meta.get("title") or path.stem).strip()
    slug = _slugify(meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem))
    md = markdown.Markdown(extensions=_MD_EXTENSIONS, output_format="html5")
    body_html = md.convert(post.content)

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
