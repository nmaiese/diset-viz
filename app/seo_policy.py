"""SEO policy overrides for public indicator landing pages."""

from app.data import get_catalog


MIN_INDEXABLE_YEAR = 2020
MIN_COMPLETENESS = 0.98
REQUIRED_REGION_COUNT = 20

# Exploration query parameters that put an indicator or region page into an
# in-page state (a chosen year, a focused region). They never create a new
# document: the canonical stays the base URL and the variant is kept out of the
# index and the sitemap. Keeping the list here makes it the single source of
# truth shared by the views and any future sitemap check.
EXPLORE_PARAMS = ("anno", "regione")


def has_explore_params(args):
    """True when the request carries an in-page exploration state.

    ``args`` is a Werkzeug ``MultiDict`` (``request.args``). A page in this
    state renders the same content as its canonical base URL, so it must be
    served ``noindex, follow`` while pointing its canonical back to the base.
    """
    return any(args.get(name) for name in EXPLORE_PARAMS)


def is_search_indexable_indicator(original_policy, item):
    """Return True only for complete, fresh, canonical indicator pages.

    The baseline policy in ``app.profiles`` excludes gender variants, incomplete
    regional coverage and old series. This wrapper keeps that threshold instead
    of exposing every indicator, so sitemap contents match the public
    methodology note about not pushing stale, incomplete or duplicative pages.
    """
    if not original_policy(item):
        return False
    if item.get("region_count") is None or item.get("completeness") is None:
        catalog_item = next(
            (entry for entry in get_catalog()["indicators"] if str(entry["id"]) == str(item.get("id"))),
            None,
        )
        if catalog_item:
            item = {**item, **catalog_item}
    if item.get("region_count", len(item.get("regions", []))) < REQUIRED_REGION_COUNT:
        return False
    if item.get("completeness", 0) < MIN_COMPLETENESS:
        return False
    return int(item.get("year_max") or 0) >= MIN_INDEXABLE_YEAR
