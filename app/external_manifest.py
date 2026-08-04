"""Thin accessor for the auditable external indicator manifest."""

from app.external_data import get_external_manifest


def rows():
    return get_external_manifest()
