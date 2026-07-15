"""Utilities for the external-source registry.

The registry is intentionally a small YAML subset so the project does not need a
runtime YAML dependency.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "config" / "external_sources.yaml"


def _parse_value(value):
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    return value


def load_registry(path=REGISTRY_PATH):
    sources = []
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#") or line.strip() == "sources:":
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                sources.append(current)
            current = {}
            stripped = stripped[2:]
        if ":" not in stripped or current is None:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = _parse_value(value)
    if current:
        sources.append(current)
    return sources


def source_by_id(source_id, path=REGISTRY_PATH):
    for source in load_registry(path):
        if source.get("source") == source_id:
            return source
    return None
