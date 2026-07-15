"""External-source bridge for the quality-of-life engine.

This module deliberately does not alter scoring yet. It exposes eligible
external candidates so future integrations can compare them with BES indicators
before any replacement or deduplication.
"""

from app.external_data import get_external_manifest


def score_candidates():
    return [
        row for row in get_external_manifest()
        if row.get("score_eligible") == "true" and row.get("status") in {"candidate", "needs_review"}
    ]


def integrated_score_replacements():
    return [
        row for row in get_external_manifest()
        if row.get("score_eligible") == "true"
        and row.get("status") == "integrated"
        and row.get("definition_match") == "exact"
    ]
