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
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        # Quoting is the only way to write a value YAML would otherwise eat, and
        # `"%"` is exactly that: an indicator unit that has to survive the round
        # trip intact or the atlas prints a bare quote next to every figure.
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def load_flat_list(path, top_key):
    """A list of flat mappings from a small YAML file, without PyYAML.

    The discovery chain is stdlib-pure on purpose: a scheduled agent runs it on
    a fresh checkout before any venv exists. That rules out PyYAML, so the config
    files it reads stay inside the subset this parses, one level of scalars under
    a list. Anything deeper belongs in code, not in config.
    """
    entries = []
    current = None
    header = f"{top_key}:"
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#") or line.strip() == header:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                entries.append(current)
            current = {}
            stripped = stripped[2:]
        if ":" not in stripped or current is None:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = _parse_value(value)
    if current:
        entries.append(current)
    return entries


def load_registry(path=REGISTRY_PATH):
    return load_flat_list(path, "sources")


def source_by_id(source_id, path=REGISTRY_PATH):
    for source in load_registry(path):
        if source.get("source") == source_id:
            return source
    return None
