"""Canonical public URL inventory shared by discovery surfaces.

Keep URL construction here rather than teaching the sitemap, page views and
machine-readable feeds independently which query-string variants are documents.
"""

from app import quality_life_bes as qb
from app.blog import SITE_URL


QUALITY_LIFE_LEVELS = {"regioni": "regione", "province": "provincia"}


def _default_profile_name():
    for profile in qb.get_quality_life_profiles():
        if profile["slug"] == qb.DEFAULT_PROFILE:
            return profile["name"]
    return qb.DEFAULT_PROFILE


def quality_life_public_urls(url_level=None):
    """Enumerate the ranking documents that may enter public indexes.

    Only the default profile is a document of its own: a `?profilo=` state
    re-orders the same rows, so it is an in-page exploration state (the atlas
    equivalent is `seo_policy.EXPLORE_PARAMS`) served `noindex, follow` with a
    canonical back to the base URL. The optional filter lets the page view
    obtain its canonical from this same inventory.
    """
    urls = []
    for candidate_level, level in QUALITY_LIFE_LEVELS.items():
        if url_level is not None and candidate_level != url_level:
            continue
        if qb.bes_ranking_exists(level, qb.DEFAULT_PROFILE):
            urls.append({
                "loc": f"{SITE_URL}/qualita-della-vita/classifica/{candidate_level}",
                "url_level": candidate_level,
                "profile_slug": qb.DEFAULT_PROFILE,
                "profile_name": _default_profile_name(),
            })
    return urls
