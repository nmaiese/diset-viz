"""Helpers shared between tests/unit and tests/integration (not a test module itself)."""

from app import sources


def family_and_raw(indicator_id):
    for family in ("bes", "multiscopo", "eurostat"):
        prefix = sources.SOURCES[family]["internal_prefix"]
        if indicator_id.startswith(prefix):
            return family, indicator_id[len(prefix):]
    return "territorial", indicator_id
