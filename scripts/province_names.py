#!/usr/bin/env python3
"""Province name normalisation for the provincial dataset.

Istat SDMX territory codelists label provinces in ways that need cleaning before
they become stable display names and URL slugs: bilingual names (Bolzano/Bozen),
"Valle d'Aosta/Vallée d'Aoste", metropolitan-city wording, and hyphenated names
(Forlì-Cesena, Massa-Carrara). This module keeps that mapping in one place and
mirrors the slug logic of `app/profiles.py:region_key_for` so provincial keys are
built the same way as regional ones.

The map below is seeded with the well-known quirks and is refined against the
real territory codelist during discovery (see scripts/discover_provinces.py).
"""

from __future__ import annotations

import re
import unicodedata

# Clean (post-split) label -> stable display name. Bilingual labels such as
# "Valle d'Aosta / Vallée d'Aoste" or "Bolzano / Bozen" are split on the slash
# first, so the keys here are the Italian side only.
PROVINCE_NAME_MAP = {
    "Valle d'Aosta": "Aosta",
    "Reggio nell'Emilia": "Reggio Emilia",
    "Reggio di Calabria": "Reggio Calabria",
}

_METRO_PREFIXES = (
    "Città metropolitana di ", "Citta metropolitana di ", "Provincia di ",
    "Libero consorzio comunale di ",
)


def normalize_province_name(raw):
    """Clean a raw territory label into a stable display name."""
    name = " ".join((raw or "").split()).strip()
    # Bilingual labels: keep the Italian side ("Bolzano / Bozen" -> "Bolzano").
    if "/" in name:
        name = name.split("/", 1)[0].strip()
    for prefix in _METRO_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            break
    return PROVINCE_NAME_MAP.get(name, name)


def province_key(name):
    """Accent-stripped, hyphen-collapsed slug, matching region_key style."""
    value = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", " ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")
