"""SEO policy overrides for public indicator landing pages."""


def is_search_indexable_indicator(original_policy, item):
    """Expose every existing public indicator page to search and sitemap discovery."""
    return bool(str(item.get("id") or "").strip())
