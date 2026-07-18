"""Canonical public taxonomy shared by atlas and quality-of-life views.

Istat source datasets use several overlapping classifications.  We keep each
original label in ``source_theme`` for traceability, but expose one stable
category hierarchy throughout the product.  The category slugs are application
identifiers: changing them would also change ranking configuration and URLs.
"""

from __future__ import annotations

import re
import unicodedata


CANONICAL_CATEGORIES = {
    "reddito_accessibilita": {
        "name": "Reddito, inclusione e accessibilità",
        "description": (
            "Reddito, condizioni economiche, inclusione sociale e accesso alle "
            "opportunità offerte dai territori."
        ),
        "macro_area": "Economia e opportunità",
        "themes": ["Benessere economico", "Reddito e ricchezza", "Inclusione sociale"],
    },
    "lavoro_opportunita": {
        "name": "Lavoro e conciliazione",
        "description": (
            "Occupazione, continuità del lavoro, partecipazione e possibilità di "
            "conciliare tempi di vita e attività professionale."
        ),
        "macro_area": "Economia e opportunità",
        "themes": ["Lavoro", "Lavoro e conciliazione dei tempi di vita"],
    },
    "imprese_competitivita": {
        "name": "Imprese e competitività",
        "description": (
            "Struttura produttiva, dinamica delle imprese, internazionalizzazione "
            "e accesso ai capitali."
        ),
        "macro_area": "Economia e opportunità",
        "themes": [
            "Competitività",
            "Demografia di impresa",
            "Dinamiche settoriali",
            "Internazionalizzazione",
            "Mercato dei capitali e finanza d'impresa",
        ],
    },
    "salute_cura": {
        "name": "Salute, demografia e cura",
        "description": (
            "Condizioni di salute, struttura demografica, assistenza e servizi di "
            "cura disponibili sul territorio."
        ),
        "macro_area": "Persone e conoscenza",
        "themes": ["Salute", "Servizi di cura", "Demografia e popolazione"],
    },
    "istruzione_capitale_umano": {
        "name": "Istruzione e formazione",
        "description": (
            "Percorsi scolastici, competenze, partecipazione all'istruzione e "
            "apprendimento lungo tutto l'arco della vita."
        ),
        "macro_area": "Persone e conoscenza",
        "themes": ["Istruzione e formazione"],
    },
    "ricerca_innovazione_digitale": {
        "name": "Ricerca, innovazione e digitale",
        "description": (
            "Ricerca, capacità innovativa, creatività e accesso alle reti e ai "
            "servizi digitali."
        ),
        "macro_area": "Persone e conoscenza",
        "themes": [
            "Innovazione, ricerca e creatività",
            "Ricerca ed innovazione",
            "Società dell'informazione",
        ],
    },
    "ambiente_energia": {
        "name": "Ambiente ed energia",
        "description": (
            "Qualità dell'ambiente, aria, acqua, rifiuti, risorse naturali ed "
            "energia."
        ),
        "macro_area": "Territorio e servizi",
        "themes": [
            "Ambiente",
            "Ambiente, altro",
            "Energia",
            "Qualità dell'aria",
            "Rifiuti",
            "Risorse idriche",
        ],
    },
    "mobilita_servizi_territoriali": {
        "name": "Mobilità e servizi territoriali",
        "description": (
            "Trasporti, mobilità, servizi essenziali e condizioni di accesso alle "
            "funzioni urbane."
        ),
        "macro_area": "Territorio e servizi",
        "themes": ["Trasporti e mobilità", "Qualità dei servizi", "Città"],
    },
    "sicurezza_legalita": {
        "name": "Sicurezza e legalità",
        "description": (
            "Criminalità, sicurezza personale, legalità e condizioni che incidono "
            "sulla vita quotidiana."
        ),
        "macro_area": "Comunità e benessere",
        "themes": ["Sicurezza", "Legalità e sicurezza"],
    },
    "istituzioni_partecipazione": {
        "name": "Istituzioni e partecipazione",
        "description": (
            "Qualità delle amministrazioni, partecipazione civica, fiducia, reti "
            "sociali e capitale sociale."
        ),
        "macro_area": "Comunità e benessere",
        "themes": [
            "Politica e istituzioni",
            "Pubblica Amministrazione",
            "Relazioni sociali",
            "Capitale sociale",
        ],
    },
    "cultura_patrimonio_turismo": {
        "name": "Cultura, patrimonio e turismo",
        "description": (
            "Offerta e partecipazione culturale, tutela del patrimonio, paesaggio "
            "e attività turistiche."
        ),
        "macro_area": "Territorio e servizi",
        "themes": ["Cultura", "Paesaggio e patrimonio culturale", "Turismo"],
    },
    "benessere_soggettivo": {
        "name": "Benessere soggettivo",
        "description": (
            "Soddisfazione per la vita, il tempo libero, le relazioni e le "
            "aspettative dichiarate per il futuro."
        ),
        "macro_area": "Comunità e benessere",
        "themes": ["Benessere soggettivo"],
    },
}

MACRO_AREAS = {
    "Economia e opportunità": (
        "reddito_accessibilita",
        "lavoro_opportunita",
        "imprese_competitivita",
    ),
    "Persone e conoscenza": (
        "salute_cura",
        "istruzione_capitale_umano",
        "ricerca_innovazione_digitale",
    ),
    "Territorio e servizi": (
        "ambiente_energia",
        "mobilita_servizi_territoriali",
        "cultura_patrimonio_turismo",
    ),
    "Comunità e benessere": (
        "sicurezza_legalita",
        "istituzioni_partecipazione",
        "benessere_soggettivo",
    ),
}
MACRO_AREA_ORDER = tuple(MACRO_AREAS)

SOURCE_THEME_TO_CATEGORY = {
    theme: slug
    for slug, category in CANONICAL_CATEGORIES.items()
    for theme in category["themes"]
}
SOURCE_INDICATOR_CATEGORY_OVERRIDES = {
    "12SER020": "ricerca_innovazione_digitale",  # copertura internet ultraveloce
    "11RIC022": "ricerca_innovazione_digitale",  # servizi comunali online
    "11RIC004P": "cultura_patrimonio_turismo",   # imprese culturali
}

# National BES regional indicators that are exact duplicates of an existing
# territorial-backbone series: identical name and identical values in every
# region and year (verified against the CSVs, not just the label). Excluded
# from general browsing (atlas catalog, search, theme pages, quiz pool) so the
# same measure does not appear twice; the territorial id is kept as canonical
# there. The BES id stays fully reachable on its own page and keeps being used
# by the quality-of-life score, which prefers the BES release for exact-name
# duplicates (see quality_life_selection.regional_quality_life_selection) -
# this is a browsing-only dedup, not a data change.
DUPLICATE_BES_IDS = {
    "01SAL001",  # Speranza di vita alla nascita -> territoriale 910
    "10AMB007",  # Coste marine balneabili -> territoriale 539
    "10AMB008",  # Disponibilità di verde urbano -> territoriale 592
    "12SER006",  # Irregolarità nella distribuzione dell'acqua -> territoriale 6
    "12SER025",  # Emigrazione ospedaliera in altra regione -> territoriale 590
    "SDG-310",   # Competenza numerica non adeguata (III media) -> territoriale 618
    "SDG-311",   # Competenza alfabetica non adeguata (III media) -> territoriale 617
}
CATEGORY_NAME_TO_SLUG = {
    category["name"]: slug for slug, category in CANONICAL_CATEGORIES.items()
}


def slugify_taxonomy(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", " ")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def category_for_source_theme(source_theme):
    """Return the canonical category slug for an exact Istat source label."""
    return SOURCE_THEME_TO_CATEGORY.get((source_theme or "").strip())


def category_for_indicator(indicator_id, source_theme):
    """Apply the few reviewed indicator-level exceptions before the source theme."""
    return SOURCE_INDICATOR_CATEGORY_OVERRIDES.get(indicator_id) or category_for_source_theme(source_theme)


def category_for_name(category_name):
    return CATEGORY_NAME_TO_SLUG.get((category_name or "").strip())


def category_metadata(source_theme):
    """Public category metadata, retaining the original Istat source label."""
    slug = category_for_source_theme(source_theme) or category_for_name(source_theme)
    if slug is None:
        return {
            "category_slug": None,
            "theme": source_theme,
            "source_theme": source_theme,
            "macro_area": "Altro",
        }
    category = CANONICAL_CATEGORIES[slug]
    return {
        "category_slug": slug,
        "theme_slug": slugify_taxonomy(category["name"]),
        "theme": category["name"],
        "source_theme": source_theme,
        "macro_area": category["macro_area"],
    }


def canonical_category_slug(path_slug):
    """Resolve canonical and legacy source-theme URL slugs to a category id."""
    for slug, category in CANONICAL_CATEGORIES.items():
        if path_slug in {slug, slugify_taxonomy(category["name"])}:
            return slug
    for source_theme, slug in SOURCE_THEME_TO_CATEGORY.items():
        if path_slug == slugify_taxonomy(source_theme):
            return slug
    return None


def category_path(category_slug):
    category = CANONICAL_CATEGORIES[category_slug]
    return f"/tema/{slugify_taxonomy(category['name'])}"
