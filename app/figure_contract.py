"""G5: controlli sui testi effettivamente visibili di una figura."""

from __future__ import annotations

import re
from html import unescape


def missing_fields(*, title: str, subtitle: str, axis_labels: tuple[str, ...],
                   source: str) -> list[str]:
    missing = []
    if not title.strip():
        missing.append("titolo")
    parts = [part.strip() for part in subtitle.split(" · ")]
    for index, field in enumerate(("misura", "popolazione", "territorio", "periodo")):
        if index >= len(parts) or not parts[index] or re.search(r"non (?:specificat[ao]|disponibile)", parts[index], re.I):
            missing.append(field)
    unit = re.search(r"\bunità\s*:\s*([^;)·]+)", subtitle, re.I)
    if not unit or not unit[1].strip() or unit[1].strip().casefold() == "non disponibile":
        missing.append("unità")
    denominator = re.search(r"\bdenominatore\s*:\s*([^;)·]+)", subtitle, re.I)
    if not denominator or not denominator[1].strip() or denominator[1].strip().casefold() == "non disponibile":
        missing.append("denominatore")
    if not axis_labels or any(not label.strip() or label.strip().casefold() == "valore" for label in axis_labels):
        missing.append("asse")
    if not re.search(r"^Fonte:\s*\S[^.]*,\s*\S", source.strip(), re.I):
        missing.append("fonte")
    release = re.search(r"\brelease\s*:\s*([^.;]+)", source, re.I)
    if not release or re.fullmatch(r"(?:non disponibile|da verificare|n\.d\.)", release[1].strip(), re.I):
        missing.append("release")
    return missing


def visible_svg_fields(svg: str) -> dict:
    def one(css: str) -> str:
        found = re.search(r'<text class="' + css + r'"[^>]*>(.*?)</text>', svg, re.S)
        return unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip() if found else ""

    axes = tuple(unescape(value).strip() for value in re.findall(
        r'<text class="fig__axis-name"[^>]*>(.*?)</text>', svg, re.S))
    return {"title": one("fig__title"), "subtitle": one("fig__subtitle"),
            "axis_labels": axes or (one("fig__subtitle"),), "source": one("fig__source")}
