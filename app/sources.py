"""Single source of truth for indicator provenance: naming and URLs.

Two audiences, kept deliberately separate:

- **Users** see a plain, institution-first label (e.g. "Istat, indicatori
  territoriali"), never internal jargon like "BES" or "Multiscopo" on its own.
- **URLs** use a short, stable acronym we control (``ter``/``bes``/``ims``/
  ``eur``) so every indicator lives under one coherent ``/indicatore/`` space.

Every family label and every indicator URL is built from here, so renaming a
source or adding one is a one-file change. Before this module the labels were
hardcoded in six places in ``atlas_catalog`` and the views.
"""

from __future__ import annotations

import re


# family key -> provenance metadata. `institution` + `label` are user-facing;
# `acronym` is the URL/id code; `internal_prefix` is the public-id namespace the
# atlas dispatcher already uses (bes:/multiscopo:), extended to eurostat.
SOURCES = {
    "territorial": {
        "acronym": "ter",
        "institution": "Istat",
        "label": "Istat, indicatori territoriali",
        "short_label": "Indicatori territoriali",
        "internal_prefix": "",
    },
    "bes": {
        "acronym": "bes",
        "institution": "Istat",
        "label": "Istat, benessere e qualità della vita",
        "short_label": "Benessere e qualità della vita",
        "internal_prefix": "bes:",
    },
    "multiscopo": {
        "acronym": "ims",
        "institution": "Istat",
        "label": "Istat, vita quotidiana delle famiglie",
        "short_label": "Vita quotidiana delle famiglie",
        "internal_prefix": "multiscopo:",
    },
    "eurostat": {
        "acronym": "eur",
        "institution": "Eurostat",
        "label": "Eurostat, statistiche regionali",
        "short_label": "Statistiche regionali europee",
        "internal_prefix": "eur:",
    },
}

FAMILY_BY_ACRONYM = {meta["acronym"]: family for family, meta in SOURCES.items()}
_ACRONYMS = "|".join(meta["acronym"] for meta in SOURCES.values())
# The first path segment is "<acronym>-<raw_id>". Raw ids can themselves contain
# dashes (BES variant suffixes like "09PAE009-N25"), so the human-readable slug
# lives in a SEPARATE path segment, never merged with the id. Everything after
# the acronym and its separating dash is the raw id, verbatim.
_CODE_RE = re.compile(rf"^({_ACRONYMS})-(.+)$")
# Legacy territorial URL: a single segment starting with a bare numeric id
# ("61" or "61-differenza-..."), from before the unified acronym scheme.
_LEGACY_TERRITORIAL_RE = re.compile(r"^(\d+)(?:-.*)?$")

INDICATOR_ROOT = "/indicatore"


def family_label(family):
    return SOURCES[family]["label"]


def family_short_label(family):
    return SOURCES[family]["short_label"]


def family_institution(family):
    return SOURCES[family]["institution"]


def acronym(family):
    return SOURCES[family]["acronym"]


def internal_id(family, raw_id):
    """Public catalog id used by get_atlas_indicator (e.g. 'bes:10AMB002')."""
    return f"{SOURCES[family]['internal_prefix']}{raw_id}"


def indicator_code(family, raw_id):
    """The resolving segment: <acronym>-<raw_id> (e.g. 'eur-rd_e_gerdreg')."""
    return f"{acronym(family)}-{raw_id}"


def indicator_url(family, raw_id, slug_tail=""):
    """Canonical unified URL, keyword-first for SEO: the human slug leads and the
    resolving code trails so the id is stable even if the name (slug) changes.

        /indicatore/<slug>/<acronym>-<raw_id>

    With no slug we fall back to the code alone; the page then 301s to the
    canonical slug-first form."""
    code = indicator_code(family, raw_id)
    return f"{INDICATOR_ROOT}/{slug_tail}/{code}" if slug_tail else f"{INDICATOR_ROOT}/{code}"


def parse_indicator_code(code):
    """(family, raw_id) for a unified first-segment code, or None otherwise."""
    match = _CODE_RE.match(code)
    if not match:
        return None
    return FAMILY_BY_ACRONYM[match.group(1)], match.group(2)


def legacy_territorial_id(code):
    """Raw numeric id for a pre-migration territorial URL segment, else None."""
    match = _LEGACY_TERRITORIAL_RE.match(code)
    return match.group(1) if match else None
