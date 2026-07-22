"""Curated selection of Istat "Indagine Multiscopo" regional dataflows.

Source: Istat SDMX (esploradati.istat.it), annual social surveys (Aspetti
della vita quotidiana, ICT nelle famiglie, condizioni abitative, reddito e
disagio economico, spesa delle famiglie), all published at NUTS2 (regional)
level. Selected after checking live that each dataflow reaches 2024 or 2025
with full 21/21 NUTS2 coverage (20 project regions, Bolzano+Trento averaged
into Trentino Alto Adige as elsewhere in this codebase).

Every entry below is a real Istat SDMX observation: `filters` pins the
non-varying dimensions to the exact code confirmed present in the live data
(so we always read a single, well-defined series), `direction` and `tema`
are the hand-curated, reviewed choices (no keyword heuristic: an indicator
this codebase has not reviewed stays `contextual`, same rule as
`scripts/bes_national_sources.py`).
"""

from __future__ import annotations


# One entry per output indicator. `flow_id` is the Istat SDMX dataflow id,
# `filters` pins every dimension besides FREQ/REF_AREA/TIME_PERIOD to the
# code confirmed present in the live data (empty dict = DATA_TYPE alone
# identifies the series). `id` is our own id, namespaced to avoid any clash
# with the legacy/BES catalogs.
MULTISCOPO_INDICATORS = [
    # -- Benessere soggettivo: soddisfazione per la vita (0-10) ----------------
    *[
        {
            "flow_id": "83_63_DF_DCCV_AVQ_PERSONE_141",
            "filters": {"DATA_TYPE": f"14_SAT_LIFE_{n}"},
            "id": f"MULTI_SATLIFE_{n}",
            "name": f"Persone di 14 anni e più con un livello di soddisfazione per la vita pari a {n} (scala 0-10)",
            "tema": "Benessere soggettivo",
            "unit": "%",
            "direction": direction,
        }
        for n, direction in {
            0: "lower_better", 1: "lower_better", 2: "lower_better", 3: "lower_better",
            4: "contextual", 5: "contextual", 6: "contextual",
            7: "higher_better", 8: "higher_better", 9: "higher_better", 10: "higher_better",
        }.items()
    ],

    # -- Ambiente ed energia: soddisfazione per il servizio elettrico --------
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_TELECTR"},
        "id": "MULTI_ELETTR_TOT", "name": "Famiglie molto o abbastanza soddisfatte del servizio elettrico nel complesso",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_CONT_SERV"},
        "id": "MULTI_ELETTR_CONT", "name": "Famiglie soddisfatte della continuità del servizio elettrico",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_VOLT_STAB"},
        "id": "MULTI_ELETTR_VOLT", "name": "Famiglie soddisfatte della stabilità della tensione elettrica",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_ECOMP_BILL"},
        "id": "MULTI_ELETTR_BOLL", "name": "Famiglie che comprendono la bolletta elettrica",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_COUNT_DISPL"},
        "id": "MULTI_ELETTR_DISPLAY", "name": "Famiglie che comprendono il display del contatore elettronico",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "82_87_DF_DCCV_AVQ_FAMIGLIE_101", "filters": {"DATA_TYPE": "HOUS_EINF_ESERV"},
        "id": "MULTI_ELETTR_INFO", "name": "Famiglie soddisfatte dell'informazione sul servizio elettrico",
        "tema": "Energia", "unit": "%", "direction": "higher_better",
    },

    # -- Salute: indice di massa corporea -------------------------------------
    {
        "flow_id": "83_85_DF_DCCV_AVQ_PERSONE1_231", "filters": {"DATA_TYPE": "18_BMI_NORMO"},
        "id": "MULTI_BMI_NORMO", "name": "Persone di 18 anni e più normopeso",
        "tema": "Salute", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "83_85_DF_DCCV_AVQ_PERSONE1_231", "filters": {"DATA_TYPE": "18_BMI_SOTTO"},
        "id": "MULTI_BMI_SOTTO", "name": "Persone di 18 anni e più sottopeso",
        "tema": "Salute", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "83_85_DF_DCCV_AVQ_PERSONE1_231", "filters": {"DATA_TYPE": "18_BMI_SOVRA"},
        "id": "MULTI_BMI_SOVRA", "name": "Persone di 18 anni e più sovrappeso",
        "tema": "Salute", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "83_85_DF_DCCV_AVQ_PERSONE1_231", "filters": {"DATA_TYPE": "18_BMI_OBE"},
        "id": "MULTI_BMI_OBESI", "name": "Persone di 18 anni e più obese",
        "tema": "Salute", "unit": "%", "direction": "lower_better",
    },

    # -- Ricerca, innovazione e digitale: connessione a internet -------------
    {
        "flow_id": "60_130_DF_DCCV_ICT_3", "filters": {"DATA_TYPE": "FAM_CONN_BROAD"},
        "id": "MULTI_ICT_BANDA_LARGA", "name": "Famiglie con connessione a banda larga",
        "tema": "Società dell'informazione", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "60_130_DF_DCCV_ICT_3", "filters": {"DATA_TYPE": "FAM_CONN_BROAD_FIX"},
        "id": "MULTI_ICT_BANDA_LARGA_FISSA", "name": "Famiglie con connessione fissa a banda larga",
        "tema": "Società dell'informazione", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "60_130_DF_DCCV_ICT_3", "filters": {"DATA_TYPE": "FAM_CONN_MOBI"},
        "id": "MULTI_ICT_BANDA_LARGA_MOBILE", "name": "Famiglie con connessione mobile a banda larga",
        "tema": "Società dell'informazione", "unit": "%", "direction": "higher_better",
    },
    {
        "flow_id": "60_130_DF_DCCV_ICT_3", "filters": {"DATA_TYPE": "FAM_CONN_NARRO"},
        "id": "MULTI_ICT_BANDA_STRETTA", "name": "Famiglie con connessione a banda stretta (fissa o mobile)",
        "tema": "Società dell'informazione", "unit": "%", "direction": "lower_better",
    },

    # -- Abitazione: sovraffollamento, spesa, titolo, problemi ---------------
    {
        "flow_id": "33_179_DF_DCCV_ABITAFFOLL_6", "filters": {"DATA_TYPE": "ABITAZ_AFFOLL_MED"},
        "id": "MULTI_ABIT_AFFOLLAMENTO",
        "name": "Indice di affollamento delle abitazioni (componenti per 100 m2)",
        "tema": "Abitazione", "unit": "numero", "direction": "lower_better",
    },
    {
        "flow_id": "33_225_DF_DCCV_ABITSPESA_6", "filters": {"DATA_TYPE": "ABITAZ_SPESA_M"},
        "id": "MULTI_ABIT_SPESA_EURO", "name": "Spesa media mensile per l'abitazione",
        "tema": "Abitazione", "unit": "euro", "direction": "contextual",
    },
    {
        "flow_id": "33_225_DF_DCCV_ABITSPESA_6", "filters": {"DATA_TYPE": "ABITAZ_SPESA_REDD"},
        "id": "MULTI_ABIT_SPESA_REDDITO",
        "name": "Spesa media mensile per l'abitazione (per 100 euro di reddito medio mensile)",
        "tema": "Abitazione", "unit": "per 100 euro di reddito", "direction": "lower_better",
    },
    {
        "flow_id": "33_290_DF_DCCV_TITGODABIT_6",
        "filters": {"DATA_TYPE": "FAM_TITOLO_GODIM_ABITAZ", "TENURE_STATUS": "1"},
        "id": "MULTI_ABIT_AFFITTO", "name": "Famiglie in affitto",
        "tema": "Abitazione", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "33_290_DF_DCCV_TITGODABIT_6",
        "filters": {"DATA_TYPE": "FAM_TITOLO_GODIM_ABITAZ", "TENURE_STATUS": "2"},
        "id": "MULTI_ABIT_PROPRIETA", "name": "Famiglie proprietarie dell'abitazione",
        "tema": "Abitazione", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "33_4_DF_DCCV_ABITPROBL_6", "filters": {"DATA_TYPE": "ABITAZ_PROBLEMI"},
        "id": "MULTI_ABIT_PROBLEMI", "name": "Famiglie con problemi nell'abitazione",
        "tema": "Abitazione", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "33_291_DF_DCCV_PROBLZONRES_2_6",
        "filters": {"MEASURE": "10", "PROBL_DWELLING_PLACE": "1"},
        "id": "MULTI_ZONA_INQUINAMENTO", "name": "Famiglie che lamentano inquinamento nella zona di residenza",
        "tema": "Ambiente", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "33_291_DF_DCCV_PROBLZONRES_2_6",
        "filters": {"MEASURE": "10", "PROBL_DWELLING_PLACE": "2"},
        "id": "MULTI_ZONA_RUMORI", "name": "Famiglie che lamentano rumori nella zona di residenza",
        "tema": "Ambiente", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "33_291_DF_DCCV_PROBLZONRES_2_6",
        "filters": {"MEASURE": "10", "PROBL_DWELLING_PLACE": "3"},
        "id": "MULTI_ZONA_CRIMINALITA", "name": "Famiglie che lamentano criminalità nella zona di residenza",
        "tema": "Sicurezza", "unit": "%", "direction": "lower_better",
    },

    # -- Reddito e ricchezza ---------------------------------------------------
    {
        "flow_id": "32_223_DF_DCCV_FONTEPRED_6",
        "filters": {"DATA_TYPE": "FAM_FONTE_REDD", "MEASURE": "1", "FAM_MAIN_INCOME_SOURCE": "1"},
        "id": "MULTI_REDD_FONTE_LAVDIP", "name": "Famiglie con fonte principale di reddito da lavoro dipendente",
        "tema": "Reddito e ricchezza", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "32_223_DF_DCCV_FONTEPRED_6",
        "filters": {"DATA_TYPE": "FAM_FONTE_REDD", "MEASURE": "1", "FAM_MAIN_INCOME_SOURCE": "2"},
        "id": "MULTI_REDD_FONTE_LAVAUT", "name": "Famiglie con fonte principale di reddito da lavoro autonomo",
        "tema": "Reddito e ricchezza", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "32_223_DF_DCCV_FONTEPRED_6",
        "filters": {"DATA_TYPE": "FAM_FONTE_REDD", "MEASURE": "1", "FAM_MAIN_INCOME_SOURCE": "3"},
        "id": "MULTI_REDD_FONTE_TRASF", "name": "Famiglie con fonte principale di reddito da trasferimenti pubblici",
        "tema": "Reddito e ricchezza", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "32_223_DF_DCCV_FONTEPRED_6",
        "filters": {"DATA_TYPE": "FAM_FONTE_REDD", "MEASURE": "1", "FAM_MAIN_INCOME_SOURCE": "4"},
        "id": "MULTI_REDD_FONTE_CAPITALE", "name": "Famiglie con fonte principale di reddito da capitale e altri redditi",
        "tema": "Reddito e ricchezza", "unit": "%", "direction": "contextual",
    },
    {
        "flow_id": "32_292_DF_DCCV_REDNETFAMFONTERED_9",
        "filters": {
            "DATA_TYPE": "REDD_MEDIANO_FAM", "MEASURE": "9",
            "IMPUTED_RENTS": "1", "FAM_MAIN_INCOME_SOURCE": "9",
        },
        "id": "MULTI_REDD_MEDIANO", "name": "Reddito netto mediano annuale delle famiglie",
        "tema": "Reddito e ricchezza", "unit": "euro", "direction": "higher_better",
    },
    {
        "flow_id": "32_292_DF_DCCV_REDNETFAMFONTERED_9",
        "filters": {
            "DATA_TYPE": "REDD_MEDIO_FAM", "MEASURE": "9",
            "IMPUTED_RENTS": "1", "FAM_MAIN_INCOME_SOURCE": "9",
        },
        "id": "MULTI_REDD_MEDIO", "name": "Reddito netto medio annuale delle famiglie",
        "tema": "Reddito e ricchezza", "unit": "euro", "direction": "higher_better",
    },

    # -- Disagio economico -------------------------------------------------------
    {
        "flow_id": "34_216_DF_DCCV_IMPREV_6", "filters": {"DATA_TYPE": "FAM_RISP"},
        "id": "MULTI_DISAGIO_RISPARMIO", "name": "Famiglie che non riescono a risparmiare",
        "tema": "Benessere economico", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "34_216_DF_DCCV_IMPREV_6", "filters": {"DATA_TYPE": "FAM_SPESE_IMPR"},
        "id": "MULTI_DISAGIO_IMPREVISTI", "name": "Famiglie che non riescono a far fronte a spese impreviste",
        "tema": "Benessere economico", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "34_226_DF_PERCEPIT_6",
        "filters": {"DATA_TYPE": "FAM_GIUD_PERCEP", "ECON_SITUATION_PERCEIVED": "1"},
        "id": "MULTI_DISAGIO_GRANDE_DIFFICOLTA",
        "name": "Famiglie che arrivano a fine mese con grande difficoltà",
        "tema": "Benessere economico", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "34_226_DF_PERCEPIT_6",
        "filters": {"DATA_TYPE": "FAM_GIUD_PERCEP", "ECON_SITUATION_PERCEIVED": "2"},
        "id": "MULTI_DISAGIO_DIFFICOLTA",
        "name": "Famiglie che arrivano a fine mese con difficoltà",
        "tema": "Benessere economico", "unit": "%", "direction": "lower_better",
    },
    {
        "flow_id": "34_226_DF_PERCEPIT_6",
        "filters": {"DATA_TYPE": "FAM_GIUD_PERCEP", "ECON_SITUATION_PERCEIVED": "4"},
        "id": "MULTI_DISAGIO_FACILITA",
        "name": "Famiglie che arrivano a fine mese con facilità o molta facilità",
        "tema": "Benessere economico", "unit": "%", "direction": "higher_better",
    },

    # -- Spesa delle famiglie: disuguaglianza dei consumi ------------------------
    {
        "flow_id": "31_740_DF_DCCV_SPEMEFAM_COICOP_2018_11", "filters": {"DATA_TYPE": "DISUG_CONSUMI_GINI"},
        "id": "MULTI_SPESA_GINI", "name": "Indice di concentrazione di Gini della spesa per consumi",
        "tema": "Reddito e ricchezza", "unit": "indice", "direction": "lower_better",
    },
    {
        "flow_id": "31_740_DF_DCCV_SPEMEFAM_COICOP_2018_11", "filters": {"DATA_TYPE": "DISUG_CONSUMI_ID"},
        "id": "MULTI_SPESA_INTERQUINTILE", "name": "Rapporto interquintilico della spesa per consumi",
        "tema": "Reddito e ricchezza", "unit": "rapporto", "direction": "lower_better",
    },
]

# Trentino-Alto Adige is split into two NUTS2-equivalent codes in this survey
# family (unlike the BES NUTS3 pipeline): average them into one region, same
# convention used across the project.
TRENTINO_PARTS = ("ITD1", "ITD2")
TRENTINO_CODE = "_TRENTINO"

SOURCE_URL = "https://esploradati.istat.it/databrowser/#/it"
ARCHIVE_LABEL = "Indagine Multiscopo sulle famiglie, Istat SDMX"
