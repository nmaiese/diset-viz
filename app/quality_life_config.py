"""Configuration for the "Qualità della vita" regional ranking.

This module is pure configuration: no logic. It declares the quality-of-life
categories (each mapped to one or more Istat themes that already exist in the
catalog) and the weight profiles that re-read the same scores under a different
lens. The active engine is ``app/quality_life_bes.py`` (BES-based, parametrised on
territorial level region|province); ``app/quality_life.py`` is the earlier
regional engine. Both consume these tables on top of ``app/profiles.py``.

Design rules:
- Theme names in ``themes`` must match the Istat catalog *verbatim* (see the
  "Tema" column of ``app/static/data/Assoluti_Regione.csv``). The engine ignores
  any theme that has no scoreable core indicator, so a typo silently drops a
  theme. ``app/quality_life.py`` exposes a diagnostic for unmapped/empty themes.
- Only directional indicators (``lower_better`` / ``higher_worse`` /
  ``higher_better``) feed the score. Contextual indicators never affect the
  ranking. "Turismo" is deliberately left out of the standard categories: more
  tourism can be an opportunity or a pressure, so it is not always "higher is
  better".
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

# Each category maps to one or more *exact* Istat theme names from the catalog.
QUALITY_LIFE_CATEGORIES = {
    "reddito_accessibilita": {
        "name": "Reddito e accessibilità",
        "description": (
            "Misura le condizioni economiche e sociali che rendono più o meno "
            "accessibile la vita quotidiana."
        ),
        "themes": ["Reddito e ricchezza", "Inclusione sociale", "Città"],
    },
    "lavoro_opportunita": {
        "name": "Lavoro e opportunità",
        "description": (
            "Misura partecipazione al lavoro, opportunità economiche e vitalità "
            "produttiva."
        ),
        "themes": [
            "Lavoro",
            "Competitività",
            "Demografia di impresa",
            "Dinamiche settoriali",
        ],
    },
    "salute_cura": {
        "name": "Salute e cura",
        "description": (
            "Misura salute, servizi di cura e condizioni demografiche legate al "
            "benessere delle persone."
        ),
        "themes": ["Salute", "Servizi di cura", "Demografia e popolazione"],
    },
    "istruzione_capitale_umano": {
        "name": "Istruzione e capitale umano",
        "description": (
            "Misura scuola, formazione, competenze e capacità di produrre "
            "conoscenza."
        ),
        "themes": ["Istruzione e formazione", "Ricerca ed innovazione"],
    },
    "ambiente_mobilita_servizi": {
        "name": "Ambiente, mobilità e servizi",
        "description": (
            "Misura qualità ambientale, mobilità, acqua, rifiuti, energia e "
            "servizi essenziali."
        ),
        "themes": [
            "Ambiente, altro",
            "Qualità dell'aria",
            "Rifiuti",
            "Risorse idriche",
            "Trasporti e mobilità",
            "Energia",
        ],
    },
    "sicurezza_istituzioni": {
        "name": "Sicurezza, legalità e istituzioni",
        "description": (
            "Misura sicurezza quotidiana, legalità, capitale sociale e "
            "funzionamento amministrativo."
        ),
        "themes": ["Legalità e sicurezza", "Pubblica Amministrazione", "Capitale sociale"],
    },
    "cultura_digitale": {
        "name": "Cultura e digitale",
        "description": (
            "Misura accesso culturale, partecipazione, digitalizzazione e società "
            "dell'informazione."
        ),
        "themes": ["Cultura", "Società dell'informazione"],
    },
}

# Raw weights per profile. The engine normalises them to sum to 1.0 and
# renormalises over the categories actually available for each region.
QUALITY_LIFE_PROFILES = {
    "standard": {
        "name": "Equilibrato",
        "description": "Dà peso simile alle principali dimensioni della qualità della vita.",
        "weights": {
            "reddito_accessibilita": 1.0,
            "lavoro_opportunita": 1.0,
            "salute_cura": 1.0,
            "istruzione_capitale_umano": 1.0,
            "ambiente_mobilita_servizi": 1.0,
            "sicurezza_istituzioni": 1.0,
            "cultura_digitale": 1.0,
        },
    },
    "opportunita": {
        "name": "Opportunità economica",
        "description": "Premia territori con più lavoro, reddito, istruzione e capacità produttiva.",
        "weights": {
            "reddito_accessibilita": 1.4,
            "lavoro_opportunita": 1.7,
            "salute_cura": 0.8,
            "istruzione_capitale_umano": 1.3,
            "ambiente_mobilita_servizi": 0.7,
            "sicurezza_istituzioni": 0.7,
            "cultura_digitale": 1.0,
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
            "salute_cura": 1.3,
            "istruzione_capitale_umano": 0.9,
            "ambiente_mobilita_servizi": 1.5,
            "sicurezza_istituzioni": 1.3,
            "cultura_digitale": 0.8,
        },
    },
    "famiglie": {
        "name": "Famiglie",
        "description": "Dà più peso a salute, cura, istruzione, ambiente e sicurezza.",
        "weights": {
            "reddito_accessibilita": 1.0,
            "lavoro_opportunita": 0.9,
            "salute_cura": 1.5,
            "istruzione_capitale_umano": 1.4,
            "ambiente_mobilita_servizi": 1.2,
            "sicurezza_istituzioni": 1.2,
            "cultura_digitale": 0.8,
        },
    },
    "giovani": {
        "name": "Giovani",
        "description": "Premia lavoro, formazione, digitale, cultura e opportunità.",
        "weights": {
            "reddito_accessibilita": 0.9,
            "lavoro_opportunita": 1.6,
            "salute_cura": 0.7,
            "istruzione_capitale_umano": 1.5,
            "ambiente_mobilita_servizi": 0.9,
            "sicurezza_istituzioni": 0.8,
            "cultura_digitale": 1.4,
        },
    },
    "servizi": {
        "name": "Servizi e territorio",
        "description": (
            "Guarda soprattutto a servizi essenziali, mobilità, ambiente, "
            "sicurezza e istituzioni."
        ),
        "weights": {
            "reddito_accessibilita": 0.7,
            "lavoro_opportunita": 0.7,
            "salute_cura": 1.3,
            "istruzione_capitale_umano": 0.9,
            "ambiente_mobilita_servizi": 1.7,
            "sicurezza_istituzioni": 1.5,
            "cultura_digitale": 1.0,
        },
    },
}

DEFAULT_PROFILE = "standard"
