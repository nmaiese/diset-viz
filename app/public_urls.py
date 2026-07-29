"""Canonical public URL inventory shared by discovery surfaces.

Keep URL construction here rather than teaching the sitemap, page views and
machine-readable feeds independently which query-string variants are documents.
"""

from app import quality_life_bes as qb
from app.blog import SITE_URL


QUALITY_LIFE_LEVELS = {"regioni": "regione", "province": "provincia"}


def quality_life_public_urls(url_level=None, profile_slug=None):
    """Enumerate ranking documents that exist and may enter public indexes.

    Optional filters let the page view obtain its canonical from this same
    inventory instead of rebuilding the URL with separate rules.
    """
    urls = []
    for candidate_level, level in QUALITY_LIFE_LEVELS.items():
        if url_level is not None and candidate_level != url_level:
            continue
        for profile in qb.get_quality_life_profiles():
            slug = profile["slug"]
            if profile_slug is not None and slug != profile_slug:
                continue
            if qb.bes_ranking_exists(level, slug):
                suffix = "" if slug == qb.DEFAULT_PROFILE else f"?profilo={slug}"
                urls.append({
                    "loc": f"{SITE_URL}/qualita-della-vita/classifica/{candidate_level}{suffix}",
                    "url_level": candidate_level,
                    "profile_slug": slug,
                    "profile_name": profile["name"],
                })
    return urls
