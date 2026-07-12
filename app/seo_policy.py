"""SEO policy overrides for public indicator landing pages."""

from app.data import get_catalog

# Older but still useful, complete regional series that should remain discoverable.
INDEXABLE_LEGACY_INDICATOR_IDS = {"103"}


def is_search_indexable_indicator(original_policy, item):
    """Keep the default policy, with reviewed exceptions for valuable legacy pages."""
    indicator_id = str(item.get("id") or "")
    if indicator_id in INDEXABLE_LEGACY_INDICATOR_IDS:
        if item.get("region_count") is None:
            catalog_item = next(
                (entry for entry in get_catalog()["indicators"] if entry["id"] == indicator_id),
                None,
            )
            if catalog_item:
                item = {**item, **catalog_item}
        return item.get("region_count", len(item.get("regions", []))) >= 20
    return original_policy(item)
