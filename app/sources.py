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
        "license": "CC BY 4.0 (Eurostat)",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "feeds": ("eurostat_regional",),
    },
    "istat_demografia": {
        "acronym": "dem",
        "institution": "Istat",
        "label": "Istat, indicatori demografici",
        "short_label": "Indicatori demografici",
        "internal_prefix": "dem:",
        "license": "CC BY 4.0 (Istat)",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "feeds": ("istat_demografia",),
    },
}

# Families whose indicators are published through the normalized external layer
# (discovery -> promotion -> app.external_atlas), rather than from a committed
# backbone CSV. `feeds` names the hunter adapters that write into them: several
# adapters can land in one family, so adding a second demographic dataflow does
# NOT mint a new URL acronym.
EXTERNAL_FAMILIES = tuple(family for family, meta in SOURCES.items() if meta.get("feeds"))
FAMILY_BY_FEED = {
    feed: family
    for family, meta in SOURCES.items()
    for feed in meta.get("feeds", ())
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


def institutions_label(families):
    """Plain Italian list of the institutions behind `families`, in registry
    order and without repetitions: "Istat", "Istat ed Eurostat", and so on.

    Public copy says who the data comes from, so it has to be derived from the
    families actually present. Hardcoding "Istat" is what made the pages claim a
    single source after Eurostat had already landed in the catalog."""
    seen = [
        SOURCES[family]["institution"]
        for family in SOURCES
        if family in set(families)
    ]
    names = list(dict.fromkeys(seen))
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    last = names[-1]
    joiner = " ed " if last[:1].lower() in "aeiou" else " e "
    return ", ".join(names[:-1]) + joiner + last


def acronym(family):
    return SOURCES[family]["acronym"]


def family_for_feed(feed):
    """The catalog family a hunter adapter promotes into, e.g.
    'istat_demografia' -> 'istat_demografia', 'eurostat_regional' -> 'eurostat'.

    The promotion step needs this to mint the public id, and it lives here
    rather than in scripts/ because the id namespace and the user-facing
    institution have to agree: an Istat series published under the Eurostat
    namespace would carry Eurostat's name and licence on the page. Returns None
    for a feed with no family, which the promoter refuses rather than guesses.
    """
    return FAMILY_BY_FEED.get(feed)


def family_license(family):
    """(license, license_url) for an external family, empty strings if unset."""
    meta = SOURCES[family]
    return meta.get("license", ""), meta.get("license_url", "")


def internal_id(family, raw_id):
    """Public catalog id used by get_atlas_indicator (e.g. 'bes:10AMB002')."""
    return f"{SOURCES[family]['internal_prefix']}{raw_id}"


def split_internal_id(indicator_id):
    """Inverse of ``internal_id``: 'bes:10AMB002' -> ('bes', '10AMB002').

    Territorial ids carry no prefix, so a bare id resolves to that family. This
    is the only correct way back from a catalog id to the pair the page and the
    editorial tooling need, and it used to be reimplemented ad hoc wherever it
    was wanted.
    """
    value = str(indicator_id)
    for family, meta in SOURCES.items():
        prefix = meta["internal_prefix"]
        if prefix and value.startswith(prefix):
            return family, value[len(prefix):]
    return "territorial", value


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
