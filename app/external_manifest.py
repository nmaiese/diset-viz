"""Thin accessors for the auditable external indicator manifest."""

from app.external_data import get_external_manifest, external_summary_for_indicator


def rows():
    return get_external_manifest()


def for_indicator(indicator_id):
    return [
        row for row in get_external_manifest()
        if row.get("target_indicator_id") == str(indicator_id)
    ]


def summary(indicator_id):
    return external_summary_for_indicator(indicator_id)
