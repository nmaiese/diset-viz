#!/usr/bin/env python3
"""Estrattore per nuovi indicatori Eurostat regionali e provinciali.

Idempotente, stdlib-only.
Scarica (se online e cache mancante) o legge da lavoro/cache/ (con --offline).
Produce:
  - app/static/data/nuovi/eurostat_nuovi.csv
  - app/static/data/nuovi/eurostat_nuovi_manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "lavoro" / "cache"
DATA_DIR = PROJECT_ROOT / "app" / "static" / "data" / "nuovi"
PROV_CODES_FILE = PROJECT_ROOT / "app" / "static" / "data" / "province_codes.csv"

API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

NUTS2_TO_REGION = {
    "ITC1": "piemonte",
    "ITC2": "valle-d-aosta",
    "ITC3": "liguria",
    "ITC4": "lombardia",
    "ITH1": "trentino-alto-adige",
    "ITH2": "trentino-alto-adige",
    "ITH3": "veneto",
    "ITH4": "friuli-venezia-giulia",
    "ITH5": "emilia-romagna",
    "ITI1": "toscana",
    "ITI2": "umbria",
    "ITI3": "marche",
    "ITI4": "lazio",
    "ITF1": "abruzzo",
    "ITF2": "molise",
    "ITF3": "campania",
    "ITF4": "puglia",
    "ITF5": "basilicata",
    "ITF6": "calabria",
    "ITG1": "sicilia",
    "ITG2": "sardegna",
}

ALL_REGIONS = sorted(list(set(NUTS2_TO_REGION.values())))

# Specific NUTS3 mapping for Italy (NUTS 2021/2024 changes vs province_codes.csv NUTS 2016)
SPECIFIC_NUTS3_MAP = {
    "IT108": "ITC4D",  # Monza e della Brianza
    "IT109": "ITI34",  # Fermo
    "IT110": "ITF48",  # Barletta-Andria-Trani
    "IT111": "ITG2F",  # Sud Sardegna
    "ITC45": "ITC4C",  # Milano
    "ITF41": "ITF46",  # Foggia
    "ITF42": "ITF47",  # Bari
}


def fetch_or_load_dataset(cache_filename: str, query_url: str, offline: bool = False) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if offline:
        if not cache_path.exists():
            raise FileNotFoundError(f"Offline mode: cached file not found: {cache_path}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    request = urllib.request.Request(query_url, headers={"User-Agent": "divarioitalia/1.0"})
    with urllib.request.urlopen(request, timeout=60) as resp:
        payload = resp.read().decode("utf-8")

    cache_path.write_text(payload, encoding="utf-8")
    return json.loads(payload)


def get_cell_value(doc: dict, coord: dict) -> float | None:
    values = doc.get("value", {})
    dims = doc.get("id", [])
    sizes = doc.get("size", [])
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    dim_dict = doc.get("dimension", {})
    pos = 0
    for i, dim in enumerate(dims):
        cat_index = dim_dict.get(dim, {}).get("category", {}).get("index", {})
        if dim in coord:
            val_code = coord[dim]
            if val_code not in cat_index:
                return None
            idx = cat_index[val_code]
        else:
            idx = 0
        pos += idx * strides[i]

    v = values.get(str(pos))
    return float(v) if v is not None else None


def load_province_codes() -> list[dict]:
    rows = []
    with PROV_CODES_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            rows.append(r)
    return rows


def map_eurostat_nuts3(code: str, available_geos: set[str]) -> str | None:
    if code in SPECIFIC_NUTS3_MAP:
        target = SPECIFIC_NUTS3_MAP[code]
        if target in available_geos:
            return target
    if code in available_geos:
        return code
    if code.startswith("ITD"):
        c2 = "ITH" + code[3:]
        if c2 in available_geos:
            return c2
    if code.startswith("ITE"):
        c2 = "ITI" + code[3:]
        if c2 in available_geos:
            return c2
    return None


def extract_all(offline: bool = False):
    print("Loading datasets...")

    # Load population weights for Bolzano + Trento
    pop_url = f"{API_BASE}/nama_10r_3popgdp?format=JSON&lang=EN&unit=THS"
    pop_doc = fetch_or_load_dataset("nama_10r_3popgdp.json", pop_url, offline)

    def get_pop_weight(nuts: str, year: str) -> float | None:
        val = get_cell_value(pop_doc, {"geo": nuts, "time": year, "unit": "THS"})
        if val is not None:
            return val
        return get_cell_value(pop_doc, {"geo": nuts, "time": "2024", "unit": "THS"})

    # 1. EUROSTAT_CASA_NON_RISCALDATA
    url1 = f"{API_BASE}/ilc_mdes01_r?format=JSON&lang=EN&geoLevel=nuts2&unit=PC"
    doc1 = fetch_or_load_dataset("ilc_mdes01_r.json", url1, offline)

    # 2. EUROSTAT_SCIENZIATI_INGEGNERI
    url2 = f"{API_BASE}/hrst_st_rcat?format=JSON&lang=EN&geoLevel=nuts2&category=SE&unit=PC_ACT"
    doc2 = fetch_or_load_dataset("hrst_st_rcat.json", url2, offline)

    # 3. EUROSTAT_MADRI_MINORI_20
    url3 = f"{API_BASE}/demo_r_fagec3?format=JSON&lang=EN&geoLevel=nuts3&unit=NR&age=TOTAL&age=Y_LT20"
    doc3 = fetch_or_load_dataset("demo_r_fagec3.json", url3, offline)

    # 4. EUROSTAT_ORE_LAVORATE
    url4 = f"{API_BASE}/lfst_r_lfe2ehour?format=JSON&lang=EN&geoLevel=nuts2&age=Y20-64&sex=T&unit=HR"
    doc4 = fetch_or_load_dataset("lfst_r_lfe2ehour.json", url4, offline)

    # 5. EUROSTAT_NOTTI_ESTERO
    url5_pc = f"{API_BASE}/tour_occ_nin2?format=JSON&lang=EN&geoLevel=nuts2&c_resid=FOR&unit=PC_TOT&nace_r2=I551-I553"
    doc5_pc = fetch_or_load_dataset("tour_occ_nin2_pc.json", url5_pc, offline)
    url5_nr = f"{API_BASE}/tour_occ_nin2?format=JSON&lang=EN&geoLevel=nuts2&unit=NR&nace_r2=I551-I553&c_resid=FOR&c_resid=TOTAL"
    doc5_nr = fetch_or_load_dataset("tour_occ_nin2_nr.json", url5_nr, offline)

    # 6. EUROSTAT_AUTOVETTURE_1000
    url6 = f"{API_BASE}/tran_r_vehst?format=JSON&lang=EN&geoLevel=nuts2&vehicle=CAR&unit=P_THAB"
    doc6 = fetch_or_load_dataset("tran_r_vehst.json", url6, offline)

    # 7. EUROSTAT_OCCUPAZIONE_POSTI_LETTO
    url7 = f"{API_BASE}/tour_occ_anor2?format=JSON&lang=EN&geoLevel=nuts2&accomunit=BEDPL&unit=PC"
    doc7 = fetch_or_load_dataset("tour_occ_anor2.json", url7, offline)

    data_rows = []

    def process_nuts2(indicator_id: str, doc: dict, fixed_coords: dict, start_year: int = 2015, decimals: int = 1):
        time_index = doc["dimension"]["time"]["category"]["index"]
        years = sorted([y for y in time_index.keys() if int(y) >= start_year])

        for yr in years:
            for region_key in ALL_REGIONS:
                nuts_codes = [n for n, r in NUTS2_TO_REGION.items() if r == region_key]

                if len(nuts_codes) == 1:
                    coord = dict(fixed_coords)
                    coord["geo"] = nuts_codes[0]
                    coord["time"] = yr
                    v = get_cell_value(doc, coord)
                    if v is not None:
                        data_rows.append({
                            "indicator_id": indicator_id,
                            "level": "regione",
                            "territory_key": region_key,
                            "year": yr,
                            "value": f"{v:.{decimals}f}",
                        })
                elif len(nuts_codes) == 2:  # Bolzano + Trento
                    n1, n2 = nuts_codes[0], nuts_codes[1]
                    coord1, coord2 = dict(fixed_coords), dict(fixed_coords)
                    coord1["geo"], coord1["time"] = n1, yr
                    coord2["geo"], coord2["time"] = n2, yr
                    v1 = get_cell_value(doc, coord1)
                    v2 = get_cell_value(doc, coord2)

                    if v1 is not None and v2 is not None:
                        w1 = get_pop_weight(n1, yr)
                        w2 = get_pop_weight(n2, yr)
                        if w1 and w2:
                            comb = (v1 * w1 + v2 * w2) / (w1 + w2)
                            data_rows.append({
                                "indicator_id": indicator_id,
                                "level": "regione",
                                "territory_key": region_key,
                                "year": yr,
                                "value": f"{comb:.{decimals}f}",
                            })

    # 1. EUROSTAT_CASA_NON_RISCALDATA
    process_nuts2("EUROSTAT_CASA_NON_RISCALDATA", doc1, {"unit": "PC"}, start_year=2015, decimals=1)

    # 2. EUROSTAT_SCIENZIATI_INGEGNERI
    process_nuts2("EUROSTAT_SCIENZIATI_INGEGNERI", doc2, {"category": "SE", "unit": "PC_ACT"}, start_year=2015, decimals=1)

    # 4. EUROSTAT_ORE_LAVORATE
    process_nuts2("EUROSTAT_ORE_LAVORATE", doc4, {"age": "Y20-64", "sex": "T", "unit": "HR"}, start_year=2015, decimals=1)

    # 5. EUROSTAT_NOTTI_ESTERO
    time_index5 = doc5_pc["dimension"]["time"]["category"]["index"]
    years5 = sorted([y for y in time_index5.keys() if int(y) >= 2015])
    for yr in years5:
        for region_key in ALL_REGIONS:
            nuts_codes = [n for n, r in NUTS2_TO_REGION.items() if r == region_key]
            if len(nuts_codes) == 1:
                v = get_cell_value(doc5_pc, {"c_resid": "FOR", "unit": "PC_TOT", "nace_r2": "I551-I553", "geo": nuts_codes[0], "time": yr})
                if v is not None:
                    data_rows.append({
                        "indicator_id": "EUROSTAT_NOTTI_ESTERO",
                        "level": "regione",
                        "territory_key": region_key,
                        "year": yr,
                        "value": f"{v:.2f}",
                    })
            elif len(nuts_codes) == 2:  # Bolzano + Trento exact counts
                n1, n2 = nuts_codes[0], nuts_codes[1]
                f1 = get_cell_value(doc5_nr, {"c_resid": "FOR", "unit": "NR", "nace_r2": "I551-I553", "geo": n1, "time": yr})
                t1 = get_cell_value(doc5_nr, {"c_resid": "TOTAL", "unit": "NR", "nace_r2": "I551-I553", "geo": n1, "time": yr})
                f2 = get_cell_value(doc5_nr, {"c_resid": "FOR", "unit": "NR", "nace_r2": "I551-I553", "geo": n2, "time": yr})
                t2 = get_cell_value(doc5_nr, {"c_resid": "TOTAL", "unit": "NR", "nace_r2": "I551-I553", "geo": n2, "time": yr})
                if all(x is not None for x in [f1, t1, f2, t2]) and (t1 + t2) > 0:
                    comb = (f1 + f2) / (t1 + t2) * 100.0
                    data_rows.append({
                        "indicator_id": "EUROSTAT_NOTTI_ESTERO",
                        "level": "regione",
                        "territory_key": region_key,
                        "year": yr,
                        "value": f"{comb:.2f}",
                    })

    # 6. EUROSTAT_AUTOVETTURE_1000
    process_nuts2("EUROSTAT_AUTOVETTURE_1000", doc6, {"vehicle": "CAR", "unit": "P_THAB"}, start_year=2015, decimals=0)

    # 7. EUROSTAT_OCCUPAZIONE_POSTI_LETTO
    process_nuts2("EUROSTAT_OCCUPAZIONE_POSTI_LETTO", doc7, {"accomunit": "BEDPL", "unit": "PC"}, start_year=2015, decimals=1)

    # 3. EUROSTAT_MADRI_MINORI_20 (provincia & regione)
    prov_rows = load_province_codes()
    available_geos3 = set(doc3["dimension"]["geo"]["category"]["index"].keys())
    time_index3 = doc3["dimension"]["time"]["category"]["index"]
    years3 = sorted([y for y in time_index3.keys() if int(y) >= 2015])

    for yr in years3:
        # 1. Provincial level
        for p_row in prov_rows:
            pkey = p_row["province_key"]
            pcode = p_row["code"]
            e_nuts3 = map_eurostat_nuts3(pcode, available_geos3)
            if not e_nuts3:
                continue

            tot = get_cell_value(doc3, {"unit": "NR", "age": "TOTAL", "geo": e_nuts3, "time": yr})
            lt20 = get_cell_value(doc3, {"unit": "NR", "age": "Y_LT20", "geo": e_nuts3, "time": yr})

            if tot is not None and lt20 is not None and tot > 0:
                pct = (lt20 / tot) * 100.0
                data_rows.append({
                    "indicator_id": "EUROSTAT_MADRI_MINORI_20",
                    "level": "provincia",
                    "territory_key": pkey,
                    "year": yr,
                    "value": f"{pct:.2f}",
                })

        # 2. Regional level (sum of NUTS3 counts per region)
        regions_map = {
            "piemonte": lambda g: g.startswith("ITC1"),
            "valle-d-aosta": lambda g: g.startswith("ITC2"),
            "liguria": lambda g: g.startswith("ITC3"),
            "lombardia": lambda g: g.startswith("ITC4"),
            "trentino-alto-adige": lambda g: g in ("ITH10", "ITH20"),
            "veneto": lambda g: g.startswith("ITH3"),
            "friuli-venezia-giulia": lambda g: g.startswith("ITH4"),
            "emilia-romagna": lambda g: g.startswith("ITH5"),
            "toscana": lambda g: g.startswith("ITI1"),
            "umbria": lambda g: g.startswith("ITI2"),
            "marche": lambda g: g.startswith("ITI3"),
            "lazio": lambda g: g.startswith("ITI4"),
            "abruzzo": lambda g: g.startswith("ITF1"),
            "molise": lambda g: g.startswith("ITF2"),
            "campania": lambda g: g.startswith("ITF3"),
            "puglia": lambda g: g.startswith("ITF4"),
            "basilicata": lambda g: g.startswith("ITF5"),
            "calabria": lambda g: g.startswith("ITF6"),
            "sicilia": lambda g: g.startswith("ITG1"),
            "sardegna": lambda g: g.startswith("ITG2"),
        }

        for rkey, matcher in regions_map.items():
            r_geos = [g for g in available_geos3 if matcher(g)]
            sum_tot = 0.0
            sum_lt20 = 0.0
            has_data = False
            for g in r_geos:
                tot = get_cell_value(doc3, {"unit": "NR", "age": "TOTAL", "geo": g, "time": yr})
                lt20 = get_cell_value(doc3, {"unit": "NR", "age": "Y_LT20", "geo": g, "time": yr})
                if tot is not None and lt20 is not None:
                    sum_tot += tot
                    sum_lt20 += lt20
                    has_data = True

            if has_data and sum_tot > 0:
                pct = (sum_lt20 / sum_tot) * 100.0
                data_rows.append({
                    "indicator_id": "EUROSTAT_MADRI_MINORI_20",
                    "level": "regione",
                    "territory_key": rkey,
                    "year": yr,
                    "value": f"{pct:.2f}",
                })

    # Sort data_rows by indicator_id, level, territory_key, year
    data_rows.sort(key=lambda r: (r["indicator_id"], r["level"], r["territory_key"], r["year"]))

    # Write data CSV
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = DATA_DIR / "eurostat_nuovi.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["indicator_id", "level", "territory_key", "year", "value"], delimiter=";")
        writer.writeheader()
        writer.writerows(data_rows)
    print(f"Wrote {len(data_rows)} rows to {out_csv}")

    # Build and write manifest CSV
    manifest_rows = build_manifest(data_rows)
    out_manifest = DATA_DIR / "eurostat_nuovi_manifest.csv"
    manifest_fields = [
        "indicator_id", "name", "institution", "unit", "decimals", "direction",
        "theme", "source_url", "method_url", "license", "license_quote",
        "year_min", "year_max", "n_provincia", "n_regione", "note"
    ]
    with out_manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields, delimiter=";")
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"Wrote {len(manifest_rows)} manifest entries to {out_manifest}")


def build_manifest(data_rows: list[dict]) -> list[dict]:
    indicators_meta = {
        "EUROSTAT_CASA_NON_RISCALDATA": {
            "name": "Persone in abitazioni non riscaldate adeguatamente",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "%",
            "decimals": 1,
            "direction": "lower_better",
            "theme": "Abitazione",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/ilc_mdes01_r/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/ilc_sieusilc.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Indagine EU-SILC NUTS2. Trentino-Alto Adige ricomposto con media pesata per la popolazione.",
        },
        "EUROSTAT_SCIENZIATI_INGEGNERI": {
            "name": "Scienziati e ingegneri sulla popolazione attiva",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "% della popolazione attiva",
            "decimals": 1,
            "direction": "higher_better",
            "theme": "Ricerca e sviluppo (Eurostat)",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/hrst_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Dato HRST NUTS2. Flag 'u' di bassa affidabilità presente per Valle d'Aosta (2025).",
        },
        "EUROSTAT_MADRI_MINORI_20": {
            "name": "Nascite da madri con meno di 20 anni",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "% delle nascite",
            "decimals": 2,
            "direction": "lower_better",
            "theme": "Demografia e popolazione",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/demo_r_fagec3/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/demo_r_gind3_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Derivato da conteggi NUTS3 (madri <20 / nascite totali * 100). Aggregato a regione per somma dei conteggi. Dal 2017 103 province per codifica sarda Eurostat NUTS 2016.",
        },
        "EUROSTAT_ORE_LAVORATE": {
            "name": "Ore settimanali abituali nel lavoro principale",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "ore",
            "decimals": 1,
            "direction": "contextual",
            "theme": "Lavoro e conciliazione dei tempi di vita",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/lfst_r_lfe2ehour/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/reg_lmk_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Indagine EU-LFS NUTS2 (occupati 20-64 anni).",
        },
        "EUROSTAT_NOTTI_ESTERO": {
            "name": "Quota di pernottamenti di turisti residenti all'estero",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "%",
            "decimals": 2,
            "direction": "contextual",
            "theme": "Turismo",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/tour_occ_nin2/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/tour_occ_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Pernottamenti esteri su totale in strutture ricettive NUTS2. Trentino-Alto Adige ricomposto da somme dei conteggi di Bolzano e Trento.",
        },
        "EUROSTAT_AUTOVETTURE_1000": {
            "name": "Autovetture per 1.000 abitanti",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "per 1.000 abitanti",
            "decimals": 0,
            "direction": "contextual",
            "theme": "Trasporti e mobilità",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/tran_r_vehst/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/tran_r_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Parco autovetture NUTS2. Ultimo anno disponibile 2024. Influenzato da immatricolazioni di flotte aziendali.",
        },
        "EUROSTAT_OCCUPAZIONE_POSTI_LETTO": {
            "name": "Tasso netto di occupazione dei posti letto alberghieri",
            "institution": "Eurostat, ufficio statistico dell'Unione europea",
            "unit": "%",
            "decimals": 1,
            "direction": "contextual",
            "theme": "Turismo",
            "source_url": "https://ec.europa.eu/eurostat/databrowser/view/tour_occ_anor2/default/table?lang=en",
            "method_url": "https://ec.europa.eu/eurostat/cache/metadata/en/tour_occ_esms.htm",
            "license": "CC BY 4.0 (Eurostat)",
            "license_quote": "Reuse of statistical data [...] is authorised provided the source is acknowledged.",
            "note": "Tasso netto occupazione posti letto alberghieri NUTS2.",
        },
    }

    manifest_list = []
    for ind_id, meta in indicators_meta.items():
        rows_ind = [r for r in data_rows if r["indicator_id"] == ind_id]
        if not rows_ind:
            continue

        years = [int(r["year"]) for r in rows_ind]
        provs = set(r["territory_key"] for r in rows_ind if r["level"] == "provincia")
        regs = set(r["territory_key"] for r in rows_ind if r["level"] == "regione")

        m = dict(meta)
        m["indicator_id"] = ind_id
        m["year_min"] = str(min(years))
        m["year_max"] = str(max(years))
        m["n_provincia"] = str(len(provs))
        m["n_regione"] = str(len(regs))
        manifest_list.append(m)

    manifest_list.sort(key=lambda x: x["indicator_id"])
    return manifest_list


def main():
    parser = argparse.ArgumentParser(description="Eurostat data extractor")
    parser.add_argument("--offline", action="store_true", help="Read strictly from local cache directory")
    args = parser.parse_args()

    extract_all(offline=args.offline)


if __name__ == "__main__":
    main()
