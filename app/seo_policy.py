"""SEO policy overrides for public indicator landing pages."""

from app.data import get_catalog


MIN_INDEXABLE_YEAR = 2020
MIN_COMPLETENESS = 0.98
REQUIRED_REGION_COUNT = 20


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
