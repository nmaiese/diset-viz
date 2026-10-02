"""Fixture MEF sintetica per la slice piattaforma.

Nessuna riga entra nei dati dell'applicazione. Le chiavi territoriali vengono
lette dall'anagrafica del worktree, così la fixture esercita davvero 20 regioni
e 107 province senza copiare dati amministrativi in produzione.
"""

from app import bes_data
from app.data import REGION_ORDER
from app.profiles import region_key_for


TARGET = "mef:reddito-irpef-medio"
SOURCE_ID = "MEF_REDDITO_IRPEF_MEDIO"
NAME = "Reddito imponibile medio per contribuente"
THEME = "Reddito e ricchezza"
CATEGORY = "reddito_accessibilita"


def levels():
    common = {
        "target_indicator_id": TARGET,
        "name": NAME,
        "theme": THEME,
        "quality_life_category": CATEGORY,
        "direction": "contextual",
        "scoreable": "false",
        "sample_survey": "false",
        "year_min": "2023",
        "year_max": "2024",
        "source_dataset": "MEF IRPEF fixture",
        "source_indicator_id": SOURCE_ID,
        "source_url": "https://www.finanze.gov.it/",
        "license": "CC BY 3.0 IT",
        "definition_match": "new",
        "reviewed_at": "2026-10-01",
        "notes": "Fixture sintetica, non dato di produzione",
    }
    return [
        {**common, "territory_level": "regione", "territory_count_latest": "20", "coverage_latest": "1.0"},
        {**common, "territory_level": "provincia", "territory_count_latest": "107", "coverage_latest": "1.0"},
    ]


def rows():
    result = []
    regions = [(region_key_for(name), name) for name in REGION_ORDER]
    provinces = [
        (key, info["name"])
        for key, info in bes_data.get_bes_territories("provincia").items()
    ]
    for year in (2023, 2024):
        for index, (key, name) in enumerate(regions, start=1):
            result.append(_row("regione", key, name, year, index))
        for index, (key, name) in enumerate(provinces, start=1):
            result.append(_row("provincia", key, name, year, index))
    return result


def _row(level, key, name, year, index):
    return {
        "source": "mef_fixture",
        "source_dataset": "MEF IRPEF fixture",
        "source_indicator_id": SOURCE_ID,
        "target_indicator_id": TARGET,
        "name": NAME,
        "territory_level": level,
        "territory_code": key,
        "territory_name": name,
        "year": str(year),
        "value": str(index * 100 + year - 2020),
        "unit": "euro per contribuente",
        "theme": THEME,
        "quality_life_category": CATEGORY,
        "direction": "contextual",
        "definition_match": "new",
        "atlas_eligible": "true",
        "profile_eligible": "true",
        "score_eligible": "false",
        "coverage": "1.0",
        "retrieved_at": "2026-10-01T00:00:00+00:00",
        "source_url": "https://www.finanze.gov.it/",
        "license": "CC BY 3.0 IT",
        "notes": "Fixture sintetica, non dato di produzione",
    }
