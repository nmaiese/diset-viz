#!/usr/bin/env python3
"""Curated selection of Istat SDMX sources for the provincial dataset.

This is the human-in-the-loop layer chosen after discovery (see
scripts/discover_provinces.py and the codelists under data/provincia/). It keeps
the download surface small and declares, for every source, the **proposed**
mapping to a quality-of-life category and a **proposed** direction.

"Proposed" is the key word: scoring happens in a later phase. Here we only record
a defensible first guess so the manifest is auditable. Directions come from a
keyword heuristic and are meant to be reviewed, exactly like
`app/indicator_notes.CURATED_DIRECTION` is for the regional data.

First campaign sources (decided with the user):
1. BES dei Territori (NUTS3) -> the bulk dataflow DF_BES_TERRIT_0T, one query per
   BES domain.
2. Tavole provinciali degli Indicatori territoriali per le politiche di sviluppo.
3. Demografia / popolazione provinciale.
Only (1) is wired below; (2) and (3) plug into the same generic fetch/build by
adding dataflows to OTHER_PROVINCIAL_FLOWS once their DSDs are inspected.
"""

from __future__ import annotations

import re

# -- BES dei Territori (backbone) -------------------------------------------

BES_DATAFLOW = "DF_BES_TERRIT_0T"   # "All indicators - All territories"
BES_DSD = "BES_TERRIT"
BES_START_PERIOD = 2015
# DSD key order: FREQ.REF_AREA.DOMAIN.DATA_TYPE.SEX.EDITION
BES_DOMAINS = [f"BES_{n:02d}" for n in range(1, 13)]

# BES domain (CL_SUS_DOMAIN) -> our quality-of-life category slug.
# BES_08 (subjective well-being) has no clean fit in the 7 categories, so it is
# left unmapped (kept as context, never scored) for now.
BES_DOMAIN_TO_CATEGORY = {
    "BES_01": "salute_cura",                 # Salute
    "BES_02": "istruzione_capitale_umano",   # Istruzione e formazione
    "BES_03": "lavoro_opportunita",          # Lavoro e conciliazione dei tempi di vita
    "BES_04": "reddito_accessibilita",       # Benessere economico
    "BES_05": "sicurezza_istituzioni",       # Relazioni sociali (capitale sociale)
    "BES_06": "sicurezza_istituzioni",       # Politica e istituzioni
    "BES_07": "sicurezza_istituzioni",       # Sicurezza
    "BES_08": None,                          # Benessere soggettivo (contesto)
    "BES_09": "cultura_digitale",            # Paesaggio e patrimonio culturale
    "BES_10": "ambiente_mobilita_servizi",   # Ambiente
    "BES_11": "istruzione_capitale_umano",   # Innovazione, ricerca e creatività
    "BES_12": "ambiente_mobilita_servizi",   # Qualità dei servizi
}

# Per-indicator category overrides, consulted before the domain->category map.
# The BES domains don't isolate "digitale": the digital and cultural-employment
# indicators sit in BES_11/BES_12, so without these overrides "Cultura e
# digitale" would be museums + agritourism only (no digital at all).
INDICATOR_CATEGORY_OVERRIDE = {
    "12SER020": "cultura_digitale",   # copertura rete internet ultra veloce
    "11RIC022": "cultura_digitale",   # comuni con servizi per le famiglie online
    "11RIC004P": "cultura_digitale",  # addetti nelle imprese culturali
}


def category_for(indicator_id, domain):
    """Override-first category slug for a BES indicator."""
    return INDICATOR_CATEGORY_OVERRIDE.get(indicator_id) or BES_DOMAIN_TO_CATEGORY.get(domain)


# CL_SEXISTAT1 codes that mean "total" (we keep only the total breakdown).
SEX_TOTAL_CODES = {"9", "T"}

# NUTS3 province codes are IT + letter + digit + alphanumeric (4 chars): ITC11,
# ITF33, ITH10, and the letter-suffixed ones like ITC4A (Cremona), ITG2C
# (Carbonia-Iglesias). The trailing [0-9A-Z] is what keeps Cremona/Mantova/
# Grosseto and the Sardinian provinces in, while staying distinct from the
# 3-char NUTS2 region codes.
NUTS3_PATTERN = re.compile(r"^IT[A-Z]\d[0-9A-Z]$")
# NUTS2 region codes look like ITC1, ITF3 (IT + letter + 1 digit): kept as a
# bonus regional comparison layer.
NUTS2_PATTERN = re.compile(r"^IT[A-Z]\d$")

# Pre-2016 Sardinian provinces, abolished and merged (mostly into Sud Sardegna).
# This BES vintage still codes them but has no recent data for them, and it does
# NOT carry Sud Sardegna at all. To align with the current layout we drop these
# four and document that Sud Sardegna is not covered by this dataflow.
DEFUNCT_PROVINCES = {
    "Olbia-Tempio",
    "Ogliastra",
    "Medio Campidano",
    "Carbonia-Iglesias",
}

# Other provincial dataflows to add after inspecting their DSDs (phase-2 of the
# same campaign). Left empty on purpose so the first run stays focused on BES.
OTHER_PROVINCIAL_FLOWS = []


# -- proposed direction heuristic -------------------------------------------

_LOWER_IS_BETTER = (
    "mortalità", "mortalita", "abbandono", "povertà", "poverta", "deprivazione",
    "disoccupazione", "criminalità", "criminalita", "omicidi", "reati", "furti",
    "rapine", "infortuni", "rifiuti", "indifferenziata", "consumo di suolo",
    "consumo del suolo", "rischio", "frane", "frana", "emission", "sovraffollamento",
    "neet", "fragilità", "fragilita", "dipendenza", "bassa produttività",
    "bassa produttivita", "sedentarietà", "sedentarieta", "fumo", "alcol",
    "eccesso di peso", "sovrappeso", "obes", "abusivismo", "irregolarità",
    "irregolarita", "dispersione", "uscita precoce", "tasso di motorizzazione",
    "evitabile", "ritardo", "difficoltà", "difficolta", "esclusione",
)
_HIGHER_IS_BETTER = (
    "speranza di vita", "occupazione", "occupati", "istruzione", "laurea",
    "diploma", "universit", "reddito", "partecipazione", "differenziata",
    "aree protette", "verde", "banda", "competenze", "soddisfazione", "fiducia",
    "brevett", "innovazione", "accessibilità", "accessibilita",
    "mobilità sostenibile", "trasporto pubblico", "biblioteche", "musei",
    "posti letto", "asilo", "asili", "spesa per ricerca", "imprese innovatrici",
)


def _matches(text, tokens):
    # Start-of-word match so "reati" does not fire inside "lauREATI".
    return any(re.search(r"\b" + re.escape(token), text) for token in tokens)


# Hand-curated directions per BES indicator code, reviewed against the official
# BES polarities. Overrides the keyword heuristic, like
# app/indicator_notes.CURATED_DIRECTION does for the regional data. Fixes both
# heuristic mistakes (e.g. "mancata partecipazione" and "raccolta differenziata"
# were flipped) and indicators the heuristic could not classify.
CURATED_DIRECTION_BES = {
    # Istruzione e formazione
    "02IST010P": "lower_better",   # competenza numerica NON adeguata
    "02IST011P": "lower_better",   # competenza alfabetica NON adeguata
    "12SER002": "higher_better",   # bambini nei servizi per l'infanzia
    # Lavoro
    "03LAV002-N22": "lower_better",   # tasso di MANCATA partecipazione al lavoro
    "03LAV004P": "higher_better",     # giornate retribuite nell'anno
    "03LAV006P-N22": "lower_better",  # mancata partecipazione giovanile
    # Benessere economico
    "04BEC002P": "higher_better",  # retribuzione media annua
    "04BEC005P": "higher_better",  # importo medio redditi pensionistici
    "04BEC006P": "lower_better",   # pensionati con reddito di BASSO importo
    "04BEC009P": "lower_better",   # ingresso in sofferenza dei prestiti
    # Relazioni sociali
    "05REL007P": "higher_better",  # scuole accessibili
    "05REL008": "higher_better",   # organizzazioni non profit
    # Politica e istituzioni
    "06POL002P": "higher_better",  # amministratori comunali donne
    "06POL003P": "higher_better",  # amministratori comunali under 40
    "06POL007P": "higher_better",  # province: capacità di riscossione
    "06POL009P": "higher_better",  # comuni: capacità di riscossione
    "06POL012P": "lower_better",   # affollamento degli istituti di pena
    # Sicurezza
    "07SIC004P": "lower_better",   # furto in abitazione
    "07SIC005P": "lower_better",   # borseggio
    "07SIC006P": "lower_better",   # rapina
    "07SIC007P": "lower_better",   # altri delitti mortali
    # Paesaggio e patrimonio culturale
    "09PAE002": "higher_better",   # patrimonio museale
    "09PAE008": "higher_better",   # aziende agrituristiche
    # Ambiente
    "10AMB001P": "lower_better",   # PM10
    "10AMB002P": "lower_better",   # PM2.5
    "10AMB016": "higher_better",   # energia da rinnovabili
    "10AMB017": "higher_better",   # raccolta differenziata (heuristic flipped it)
    # Innovazione, ricerca
    "11RIC004P": "higher_better",  # addetti imprese culturali
    "11RIC022": "higher_better",   # comuni con servizi famiglie online
    # Qualità dei servizi
    "12SER002P": "higher_better",  # medici specialisti
    "12SER008": "higher_better",   # posti-km offerti dal TPL
    "12SER020": "higher_better",   # copertura rete internet ultra veloce
    "12SER024": "higher_better",   # raccolta differenziata (heuristic flipped it)
    "12SER025": "lower_better",    # emigrazione ospedaliera
}


def propose_direction(name):
    """Heuristic, provisional direction from the Italian indicator name."""
    text = (name or "").lower()
    if _matches(text, _LOWER_IS_BETTER):
        return "lower_better"
    if _matches(text, _HIGHER_IS_BETTER):
        return "higher_better"
    return "contextual"


def direction_for(indicator_id, name):
    """Curated direction if available, otherwise the keyword heuristic."""
    return CURATED_DIRECTION_BES.get(indicator_id) or propose_direction(name)


def bes_key(domain):
    """Dot key for a per-domain BES query (REF_AREA/DATA_TYPE/SEX/EDITION = all)."""
    return ".".join(["A", "", domain, "", "", ""])
