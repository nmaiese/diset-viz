"""Configuration for the "Qualità della vita" regional ranking.

The categories come from the same canonical taxonomy used by the atlas.  The
quality-of-life engines use only the directional indicators available inside
those categories, so this is a scoring subset of the catalog, not a separate
classification.

Design rules:
- Theme names in ``themes`` match the source labels verbatim. They are defined
  once in ``app.taxonomy`` and retain the source classification for auditing.
- Only directional indicators (``lower_better`` / ``higher_worse`` /
  ``higher_better``) feed the score. Contextual indicators never affect the
  ranking. Contextual tourism indicators remain in the catalog without being
  forced into the score.
- Weights here are raw; the engine normalises them to sum to 1.0 and renormalises
  over the categories actually available for each region.

PROVINCE (implemented — regional atlas + provincial BES both live)
------------------------------------------------------------------
The categories below are deliberately territory-agnostic and are now reused for
the provincial ranking too. Provinces are implemented, outside this file, via:
- the provincial dataset ``app/static/data/Assoluti_Provincia.csv`` (Istat "BES
  dei Territori" backbone);
- the BES engine ``app/quality_life_bes.py``, parametrised on level region|province,
  with ``app/quality_life_province.py`` for the provincial specifics;
- routes ``/qualita-della-vita/province`` and
  ``/qualita-della-vita/province/<slug>`` (see ``app/views.py``);
- see ``docs/PROVINCE_PIPELINE.md`` for the ingestion pipeline.
Still future work: additional provincial geometries/maps and the vertical
sources below. Vertical sources (OMI, ISPRA/SNPA, INAIL, Ministero della Salute,
AGCOM/Infratel, Ministero dell'Interno, Ministero della Giustizia) only in a later phase. Any
methodological benchmark against the Sole 24 Ore / ItaliaOggi rankings must stay
a separate section and never become a primary data source (CC BY-NC licence).
"""

from app.taxonomy import CANONICAL_CATEGORIES


QUALITY_LIFE_CATEGORIES = {
    slug: {
        "name": category["name"],
        "description": category["description"],
        "themes": list(category["themes"]),
        "macro_area": category["macro_area"],
    }
    for slug, category in CANONICAL_CATEGORIES.items()
}

# Raw weights per profile. The engine normalises them to sum to 1.0 and
# renormalises over the categories actually available for each region.
QUALITY_LIFE_PROFILES = {
    "standard": {
        "name": "Equilibrato",
        "description": "Assegna lo stesso peso alle dodici dimensioni della qualità della vita.",
        "weights": {slug: 1.0 for slug in QUALITY_LIFE_CATEGORIES},
    },
    "opportunita": {
        "name": "Opportunità economica",
        "description": "Aumenta il peso di lavoro, reddito, istruzione e capacità produttiva.",
        "weights": {
            "reddito_accessibilita": 1.4,
            "lavoro_opportunita": 1.7,
            "imprese_competitivita": 1.5,
            "salute_cura": 0.8,
            "istruzione_capitale_umano": 1.3,
            "ricerca_innovazione_digitale": 1.3,
            "ambiente_energia": 0.7,
            "mobilita_servizi_territoriali": 0.7,
            "sicurezza_legalita": 0.7,
            "istituzioni_partecipazione": 0.7,
            "cultura_patrimonio_turismo": 1.0,
            "benessere_soggettivo": 0.8,
        },
    },
    "accessibilita": {
        "name": "Accessibilità quotidiana",
        "description": (
            "Riduce il peso della sola ricchezza e dà più importanza a servizi, "
            "ambiente, inclusione e sicurezza."
        ),
        "weights": {
            "reddito_accessibilita": 1.1,
            "lavoro_opportunita": 0.8,
            "imprese_competitivita": 0.7,
            "salute_cura": 1.3,
            "istruzione_capitale_umano": 0.9,
            "ricerca_innovazione_digitale": 0.8,
            "ambiente_energia": 1.5,
            "mobilita_servizi_territoriali": 1.5,
            "sicurezza_legalita": 1.3,
            "istituzioni_partecipazione": 1.2,
            "cultura_patrimonio_turismo": 0.8,
            "benessere_soggettivo": 1.1,
        },
    },
    "famiglie": {
        "name": "Famiglie",
        "description": "Aumenta il peso di salute, cura, istruzione, ambiente e sicurezza.",
        "weights": {
            "reddito_accessibilita": 1.0,
            "lavoro_opportunita": 0.9,
            "imprese_competitivita": 0.7,
            "salute_cura": 1.5,
            "istruzione_capitale_umano": 1.4,
            "ricerca_innovazione_digitale": 0.8,
            "ambiente_energia": 1.2,
            "mobilita_servizi_territoriali": 1.2,
            "sicurezza_legalita": 1.2,
            "istituzioni_partecipazione": 1.0,
            "cultura_patrimonio_turismo": 0.8,
            "benessere_soggettivo": 1.1,
        },
    },
    "giovani": {
        "name": "Giovani",
        "description": "Aumenta il peso di lavoro, formazione, digitale, cultura e opportunità.",
        "weights": {
            "reddito_accessibilita": 0.9,
            "lavoro_opportunita": 1.6,
            "imprese_competitivita": 1.3,
            "salute_cura": 0.7,
            "istruzione_capitale_umano": 1.5,
            "ricerca_innovazione_digitale": 1.4,
            "ambiente_energia": 0.9,
            "mobilita_servizi_territoriali": 1.0,
            "sicurezza_legalita": 0.8,
            "istituzioni_partecipazione": 0.8,
            "cultura_patrimonio_turismo": 1.3,
            "benessere_soggettivo": 1.0,
        },
    },
    "servizi": {
        "name": "Servizi e territorio",
        "description": (
            "Aumenta il peso di servizi essenziali, mobilità, ambiente, "
            "sicurezza e istituzioni."
        ),
        "weights": {
            "reddito_accessibilita": 0.7,
            "lavoro_opportunita": 0.7,
            "imprese_competitivita": 0.7,
            "salute_cura": 1.3,
            "istruzione_capitale_umano": 0.9,
            "ricerca_innovazione_digitale": 0.8,
            "ambiente_energia": 1.7,
            "mobilita_servizi_territoriali": 1.7,
            "sicurezza_legalita": 1.5,
            "istituzioni_partecipazione": 1.5,
            "cultura_patrimonio_turismo": 1.0,
            "benessere_soggettivo": 0.9,
        },
    },
}

DEFAULT_PROFILE = "standard"
