#!/usr/bin/env python3
"""Estrae dall'Istat gli indicatori provinciali (e regionali) del flusso E.

Legge SOLO la cache `data/istat_cache` (stesso client di
`build_province_dataset.py`, sempre in `cache_only`): non chiama mai
esploradati.istat.it, che ammette 5 richieste al minuto e blocca l'IP per
giorni. Una chiave non presente in cache viene saltata e dichiarata, mai
scaricata. `--offline` e' accettato per uniformita' con gli altri moduli di
`scripts/nuovi_dati/` ed e' comunque il solo comportamento possibile.

Scrive:
  app/static/data/nuovi/istat_prov.csv           indicator_id;level;territory_key;year;value
  app/static/data/nuovi/istat_prov_manifest.csv  una riga per indicatore

Idempotente: stesso input in cache, stesso output byte per byte.
Solo libreria standard.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import istat_sdmx  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"
OUT_DIR = PROJECT_ROOT / "app" / "static" / "data" / "nuovi"
PROVINCE_CODES = PROJECT_ROOT / "app" / "static" / "data" / "province_codes.csv"

ANNO_MIN = 2015
INSTITUTION = "Istituto nazionale di statistica (Istat)"
LICENSE = "CC BY 4.0"
LICENSE_QUOTE = (
    "Salvo diversa indicazione, tutti i contenuti pubblicati su questo sito "
    "sono soggetti alla licenza Creative Commons – Attribuzione – versione 4.0."
)
METHOD_POP = "https://www.istat.it/statistiche-per-temi/popolazione/popolazione-e-famiglie/"
METHOD_LAVORO = "https://www.istat.it/statistiche-per-temi/istruzione-e-lavoro/lavoro-e-retribuzioni/"
METHOD_CONTI_TERRITORIALI = "https://www.istat.it/comunicato-stampa/conti-economici-territoriali-2022-2024/"
SOURCE_BASE = "https://esploradati.istat.it/SDMXWS/rest/data/"

FLUSSO_DEMOG = "22_293_DF_DCIS_INDDEMOG1_1"
FLUSSO_DISOCC = "151_914_DF_DCCV_TAXDISOCCU1_8"
FLUSSO_ATTIV = "150_916_DF_DCCV_TAXATVT1_5"
FLUSSO_CONTI_TERRITORIALI = "93_1227_DF_DCCN_TNA1_6"
CHIAVE_PIL_PRO_CAPITE = "A..B1GQ_B_W2_S1_R_POP.Z.Z.Z.V.N.Z.2025M12"

# Regioni: codice NUTS2 Istat -> nome come in province_codes.csv (colonna region).
# Il Trentino Alto Adige e' ITDA: il flusso lo porta gia' aggregato, quindi non si
# ricalcola nulla. ITD1/ITD2 sono Bolzano/Trento (province), non regioni.
REGIONI = {
    "ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria",
    "ITC4": "Lombardia", "ITD3": "Veneto", "ITD4": "Friuli-Venezia Giulia",
    "ITD5": "Emilia-Romagna", "ITDA": "Trentino Alto Adige", "ITE1": "Toscana",
    "ITE2": "Umbria", "ITE3": "Marche", "ITE4": "Lazio", "ITF1": "Abruzzo",
    "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia", "ITF5": "Basilicata",
    "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna",
}
# Nei flussi forze di lavoro Bolzano e Trento hanno il codice a 4 caratteri.
ALIAS_LAVORO = {"ITD1": "ITD10", "ITD2": "ITD20"}

# Filtro dei flussi lavoro: serie annuale, totale, nessuna disaggregazione.
FILTRO_DISOCC = {
    "FREQ": "A", "DATA_TYPE": "UNEM_R", "SEX": "9", "AGE": "Y15-74",
    "EDU_LEV_HIGHEST": "99", "CITIZENSHIP": "TOTAL", "DURATION_UNEMPLOYMENT": "TOTAL",
}
FILTRO_ATTIV = {
    "FREQ": "A", "DATA_TYPE": "ACT_R", "SEX": "9", "AGE": "Y15-64",
    "EDU_LEV_HIGHEST": "99", "CITIZENSHIP": "TOTAL",
}

# id, flusso, filtro (DATA_TYPE per i demografici), alias territori, metadati.
SERIE = [
    dict(id="ISTATP_LIFEEXP65", flusso=FLUSSO_DEMOG, data_type="LIFEEXP65T",
         name="Speranza di vita a 65 anni", unit="anni", decimals=1,
         direction="higher_better", theme="salute_cura", method=METHOD_POP,
         note="Totale maschi e femmine. Gli ultimi valori sono stimati (OBS_STATUS e)."),
    dict(id="ISTATP_FECONDITA", flusso=FLUSSO_DEMOG, data_type="TFR",
         name="Numero medio di figli per donna", unit="figli per donna", decimals=2,
         direction="contextual", theme="salute_cura", method=METHOD_POP,
         note="Misura la fecondita' del momento: va letta come descrizione, non come giudizio. Ultimo anno stimato (e)."),
    dict(id="ISTATP_INDICE_VECCHIAIA", flusso=FLUSSO_DEMOG, data_type="AGEINDEX",
         name="Indice di vecchiaia", unit="persone di 65 anni e piu' ogni 100 di 0-14 anni",
         decimals=1, direction="contextual", theme="salute_cura", method=METHOD_POP,
         note="Struttura per eta' al 1 gennaio: l'ultimo anno e' il 2026. Descrive la popolazione, non un merito."),
    dict(id="ISTATP_SALDO_MIGRATORIO_INTERNO", flusso=FLUSSO_DEMOG, data_type="NMIGRATEIN",
         name="Saldo migratorio interno", unit="per mille abitanti", decimals=1,
         direction="contextual", theme="lavoro_opportunita", method=METHOD_POP,
         note="Iscrizioni meno cancellazioni da altri comuni italiani. Ultimo anno provvisorio (p)."),
    dict(id="ISTATP_ETA_MEDIA_MADRE", flusso=FLUSSO_DEMOG, data_type="MEANAGECH",
         name="Età media della madre al parto", unit="anni", decimals=1,
         direction="contextual", theme="salute_cura", method=METHOD_POP,
         note="Ultimo anno stimato (e)."),
    dict(id="ISTATP_NATALITA", flusso=FLUSSO_DEMOG, data_type="BIRTHRATE",
         name="Tasso di natalità", unit="per mille abitanti", decimals=1,
         direction="contextual", theme="salute_cura", method=METHOD_POP,
         note="Dipende dalla struttura per eta' della popolazione. Ultimo anno provvisorio (p)."),
    dict(id="ISTATP_DISOCCUPAZIONE", flusso=FLUSSO_DISOCC, filtro=FILTRO_DISOCC,
         name="Tasso di disoccupazione 15-74 anni", unit="% delle forze di lavoro",
         decimals=1, direction="lower_better", theme="lavoro_opportunita",
         method=METHOD_LAVORO,
         note="Rilevazione sulle forze di lavoro, serie provinciale corrente. Campione provinciale: oscillazioni tra un anno e l'altro. Valori arrotondati a 3 decimali."),
    dict(id="ISTATP_ATTIVITA", flusso=FLUSSO_ATTIV, filtro=FILTRO_ATTIV,
         name="Tasso di attività 15-64 anni", unit="% della popolazione 15-64 anni",
         decimals=1, direction="higher_better", theme="lavoro_opportunita",
         method=METHOD_LAVORO,
         note="Da leggere insieme al tasso di occupazione: da solo non distingue chi lavora da chi cerca lavoro. Valori arrotondati a 3 decimali."),
    dict(id="ISTATP_PIL_PRO_CAPITE", flusso=FLUSSO_CONTI_TERRITORIALI,
         key=CHIAVE_PIL_PRO_CAPITE, start=ANNO_MIN, year_max=2023,
         levels=("provincia",), freshness_exception=True,
         filtro={"FREQ": "A", "DATA_TYPE_AGGR": "B1GQ_B_W2_S1_R_POP"},
         name="PIL per abitante", unit="euro per abitante, prezzi correnti", decimals=0,
         direction="higher_better", theme="reddito_accessibilita",
         method=METHOD_CONTI_TERRITORIALI,
         note="PIL per abitante a prezzi correnti. Ultimo anno 2023: stima semi-definitiva Istat, il 2024 provinciale arriva a dicembre 2026. Misura la produzione del territorio, non il reddito di chi ci abita."),
]

OUT_COLS = ["indicator_id", "level", "territory_key", "year", "value"]
MANIFEST_COLS = [
    "indicator_id", "name", "institution", "unit", "decimals", "direction", "theme",
    "source_url", "method_url", "license", "license_quote", "year_min", "year_max",
    "n_provincia", "n_regione", "note",
]


def carica_territori():
    """(codice Istat -> province_key, nome regione -> region_key) dai file del repo."""
    province = {}
    with PROVINCE_CODES.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            province[r["code"]] = r["province_key"]
    return province


def region_key_for(region):
    """Come `app.profiles.region_key_for` (copiata: lo script non importa Flask)."""
    import unicodedata
    value = unicodedata.normalize("NFKD", region).encode("ascii", "ignore").decode("ascii")
    return value.lower().replace("'", " ").replace(" ", "-")


def territorio(ref_area, province, alias):
    """(level, territory_key) per un REF_AREA, o None se non serve."""
    ref = alias.get(ref_area, ref_area)
    if ref in province:
        return "provincia", province[ref]
    if ref_area in REGIONI:
        return "regione", region_key_for(REGIONI[ref_area])
    return None


def estrai_serie(client, serie, province, mancanti):
    alias = ALIAS_LAVORO if serie["flusso"] in {FLUSSO_DISOCC, FLUSSO_ATTIV} else {}
    try:
        start = serie.get("start", ANNO_MIN if "filtro" not in serie else None)
        righe = client.data(serie["flusso"], serie.get("key", ""), start)
    except istat_sdmx.CacheMissError as exc:
        mancanti.append(f"{serie['id']}: chiave non in cache ({exc})")
        return []
    out = {}
    for r in righe:
        if "filtro" in serie:
            if any(r.get(k) != v for k, v in serie["filtro"].items()):
                continue
        elif r["DATA_TYPE"] != serie["data_type"]:
            continue
        anno = int(r["TIME_PERIOD"])
        if anno < ANNO_MIN or anno > serie.get("year_max", anno) or r["OBS_VALUE"] == "":
            continue
        t = territorio(r["REF_AREA"], province, alias)
        if t is None or t[0] not in serie.get("levels", ("provincia", "regione")):
            continue
        # Nei demografici Bolzano e' sia ITD1 che ITD10: ITD1 non e' una provincia
        # per `territorio` (non e' in province_codes), quindi nessun doppione.
        chiave = (serie["id"], t[0], t[1], anno)
        valore = round(float(r["OBS_VALUE"]), 3)
        if chiave in out and out[chiave] != valore:
            raise SystemExit(f"valori discordi per {chiave}: {out[chiave]} vs {valore}")
        out[chiave] = valore
    return [(*k, v) for k, v in out.items()]


def fmt(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true",
                    help="legge solo la cache (e' l'unico modo: la rete Istat non si chiama)")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE), help="cartella della cache SDMX")
    ap.add_argument("--out", default=str(OUT_DIR), help="cartella di uscita")
    args = ap.parse_args(argv)

    client = istat_sdmx.SdmxClient(cache_dir=args.cache, cache_only=True)
    province = carica_territori()
    mancanti = []
    tutte, manifest = [], []
    for serie in SERIE:
        righe = estrai_serie(client, serie, province, mancanti)
        if not righe:
            continue
        righe.sort(key=lambda r: (r[1], r[2], r[3]))
        tutte.extend(righe)
        anni = [r[3] for r in righe]
        ultimo = max(anni)
        n_prov = len({r[2] for r in righe if r[1] == "provincia" and r[3] == ultimo})
        n_reg = len({r[2] for r in righe if r[1] == "regione" and r[3] == ultimo})
        nota = serie["note"]
        if ultimo < 2025 and not serie.get("freshness_exception"):
            nota = f"ATTENZIONE ultimo anno {ultimo}, sotto il 2025. " + nota
        flusso = serie["flusso"]
        manifest.append({
            "indicator_id": serie["id"], "name": serie["name"], "institution": INSTITUTION,
            "unit": serie["unit"], "decimals": serie["decimals"], "direction": serie["direction"],
            "theme": serie["theme"], "source_url": f"{SOURCE_BASE}{flusso}",
            "method_url": serie["method"], "license": LICENSE, "license_quote": LICENSE_QUOTE,
            "year_min": min(anni), "year_max": ultimo, "n_provincia": n_prov,
            "n_regione": n_reg, "note": nota,
        })
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "istat_prov.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";", lineterminator="\n")
        w.writerow(OUT_COLS)
        for ind, lev, key, anno, v in tutte:
            w.writerow([ind, lev, key, anno, fmt(v)])
    with (out / "istat_prov_manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLS, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(manifest)
    for m in manifest:
        print(f"{m['indicator_id']}: {m['year_min']}-{m['year_max']} province {m['n_provincia']} regioni {m['n_regione']}")
    for m in mancanti:
        print("SALTATA", m, file=sys.stderr)
    print(f"{len(tutte)} righe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
