"""Curated mappings for the national BES regional workbook.

The intermediate BES release is the freshest official regional quality-of-life
source available to the project.  Categories are deliberately mapped to the
site's public quality-of-life dimensions, while directions are reviewed per
indicator for the 2025 release.  Unknown indicators stay contextual until a
human reviews them: an automatic refresh must never guess the sign of a score.
"""

from __future__ import annotations

from scripts.province_sources import CURATED_DIRECTION_BES


DOMAIN_TO_CATEGORY = {
    "Salute": "salute_cura",
    "Istruzione e formazione": "istruzione_capitale_umano",
    "Lavoro e conciliazione dei tempi di vita": "lavoro_opportunita",
    "Benessere economico": "reddito_accessibilita",
    "Relazioni sociali": "sicurezza_istituzioni",
    "Politica e istituzioni": "sicurezza_istituzioni",
    "Sicurezza": "sicurezza_istituzioni",
    "Benessere soggettivo": "benessere_soggettivo",
    "Paesaggio e patrimonio culturale": "cultura_digitale",
    "Ambiente": "ambiente_mobilita_servizi",
    "Innovazione, ricerca e creatività": "istruzione_capitale_umano",
    "Qualità dei servizi": "ambiente_mobilita_servizi",
}


# Reviewed against the indicator definitions in the May 2026 BES metadata.
# Only these explicit entries may enter the regional score.
CURATED_DIRECTION_BES_NATIONAL = {
    "01SAL001": "higher_better",
    "01SAL002": "higher_better",
    "01SAL003": "higher_better",
    "01SAL021": "lower_better",
    "01SAL008": "higher_better",
    "01SAL009": "lower_better",
    "01SAL010": "lower_better",
    "01SAL011": "lower_better",
    "01SAL012": "lower_better",
    "01SAL013": "higher_better",
    "02IST002-N22": "higher_better",
    "02IST026-N22": "higher_better",
    "02IST005-N22": "lower_better",
    "02IST006-N22": "lower_better",
    "02IST007-N22": "higher_better",
    "SDG-311": "lower_better",
    "SDG-310": "lower_better",
    "02IST022": "higher_better",
    "02IST023": "higher_better",
    "02IST024": "higher_better",
    "03LAV001-N22": "higher_better",
    "03LAV002-N22": "lower_better",
    "03LAV003": "higher_better",
    "03LAV004-N22": "lower_better",
    "03LAV006-N25": "lower_better",
    "03LAV009-N22": "higher_better",
    "03LAV022-N22": "higher_better",
    "03LAV013-N22": "lower_better",
    "03LAV014-N22": "lower_better",
    # Working from home is useful context, but more is not always better.
    "03LAV021-N22": "contextual",
    "04BEC003": "lower_better",
    "04BEC007-N23": "lower_better",
    "04BEC008": "lower_better",
    "04BEC009": "lower_better",
    "04BEC010-N23": "lower_better",
    "SDG-222": "lower_better",
    # The workbook label does not state which response category is measured.
    "04BEC020": "contextual",
    "05REL001": "higher_better",
    "05REL002": "higher_better",
    "05REL003": "higher_better",
    "05REL010": "higher_better",
    "05REL009": "higher_better",
    "05REL006": "higher_better",
    "05REL007": "higher_better",
    "06POL002": "higher_better",
    "06POL003": "higher_better",
    "06POL004": "higher_better",
    "06POL005": "higher_better",
    "06POL007": "higher_better",
    "06POL011": "lower_better",
    "07SIC002": "lower_better",
    "07SIC003": "lower_better",
    "07SIC004": "lower_better",
    "07SIC020": "higher_better",
    "07SIC021": "lower_better",
    "07SIC022": "lower_better",
    "08BSO001": "higher_better",
    "08BSO002": "higher_better",
    "08BSO003": "higher_better",
    "08BSO004": "lower_better",
    "09PAE010": "lower_better",
    "10AMB009": "higher_better",
    "11RIC003-N22": "higher_better",
    "11RIC006-N22": "higher_better",
    "11RIC023": "higher_better",
    "12SER006": "lower_better",
    "12SER020": "higher_better",
}


def category_for(domain):
    return DOMAIN_TO_CATEGORY.get((domain or "").strip())


def direction_for(indicator_id, name=""):
    # Reuse only already reviewed BES dei Territori polarities. Keyword
    # heuristics are deliberately not used here: a newly published indicator
    # must land as contextual until its meaning is reviewed.
    return CURATED_DIRECTION_BES_NATIONAL.get(
        indicator_id, CURATED_DIRECTION_BES.get(indicator_id, "contextual")
    )
