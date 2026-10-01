#!/usr/bin/env python3
"""Estrae dall'Indagine Multiscopo Istat "Aspetti della vita quotidiana" (AVQ)
le serie regionali non ancora in catalogo, e le scrive in
`app/static/data/nuovi/istat_avq.csv` (+ `istat_avq_manifest.csv`).

Legge SOLO la cache SDMX locale (`data/istat_cache`): l'endpoint Istat concede
5 richieste al minuto e blocca l'IP per giorni, quindi questo script non apre
mai la rete. Una chiave non in cache viene saltata e dichiarata. Il flag
`--offline` e' quindi il comportamento di default; `--rete` esiste solo per
completezza e va usato a mano, con il client che rispetta il limite.

Trentino Alto Adige = Bolzano (ITD1) + Trento (ITD2) con la media ponderata
sulla popolazione gia usata dal repo (`multiscopo_sources.TRENTINO_WEIGHTS`),
mai una media semplice. Se manca una delle due parti in un anno, l'anno del
Trentino Alto Adige si salta.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import istat_sdmx, multiscopo_sources  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "istat_cache"
DATA_DIR = PROJECT_ROOT / "app" / "static" / "data" / "nuovi"
OUTPUT = DATA_DIR / "istat_avq.csv"
MANIFEST = DATA_DIR / "istat_avq_manifest.csv"
CODELIST_PATH = PROJECT_ROOT / "data" / "provincia" / "codelist_CL_ITTER107.csv"

NUTS2_PATTERN = re.compile(r"^IT[A-Z]\d$")
TRENTINO_KEY = "trentino-alto-adige"
FIRST_YEAR = 2001

INSTITUTION = "Istat, Indagine Multiscopo sulle famiglie Aspetti della vita quotidiana"
LICENSE = "CC BY 4.0"
LICENSE_QUOTE = (
    "Salvo diversa indicazione, tutti i contenuti pubblicati su questo sito "
    "sono soggetti alla licenza Creative Commons – Attribuzione – versione 4.0"
)
LICENSE_URL_NOTE = "https://www.istat.it/note-legali/"
DATA_URL = "https://esploradati.istat.it/SDMXWS/rest/data/{flow}"
METHOD_URL = (
    "https://esploradati.istat.it/RefMeta/template/GenericMetadataTemplate.html"
    "?nodeId=DW&metadataSetId=MS_ISTAT_TOPMETA2&reportId={dsd}&lang=en"
    "&BaseUrlMDA=https://esploradati.istat.it/METADATA_API"
)

FLOW_PERSONE = "83_63_DF_DCCV_AVQ_PERSONE_{n}"
FLOW_PERSONE1 = "83_85_DF_DCCV_AVQ_PERSONE1_{n}"
FLOW_FAMIGLIE = "82_87_DF_DCCV_AVQ_FAMIGLIE_{n}"
DSD_PER_FLUSSO = {
    "83_63": "DCCV_AVQ_PERSONE",
    "83_85": "DCCV_AVQ_PERSONE1",
    "82_87": "DCCV_AVQ_FAMIGLIE",
}

SMALL_SAMPLE = "Campione piccolo, serie rumorosa: leggere la serie, non il singolo anno."

# id, flow, DATA_TYPE, MEASURE, unit, decimali, direction, theme, name, note
INDICATORS = [
    ("AVQ_PRONTO_SOCCORSO", FLOW_PERSONE.format(n=216), "0_FA", "TSC", "per 1000 persone", 1,
     "contextual", "Salute",
     "Persone che hanno usato il pronto soccorso negli ultimi 3 mesi",
     "Verso non onesto: un uso alto puo segnalare accesso come medicina territoriale debole. "
     + SMALL_SAMPLE),
    ("AVQ_GUARDIA_MEDICA", FLOW_PERSONE.format(n=216), "0_MG", "TSC", "per 1000 persone", 1,
     "contextual", "Salute",
     "Persone che hanno usato la guardia medica negli ultimi 3 mesi",
     "Verso non onesto. " + SMALL_SAMPLE),
    ("AVQ_ASL_FILA_OLTRE_20_MIN", FLOW_PERSONE1.format(n=104), "18_ASL_DUR_GE20", "HSC", "%", 1,
     "lower_better", "Salute",
     "Utenti della ASL con una fila di oltre 20 minuti",
     "Base: persone di 18 anni e piu che si sono recate alla ASL, non l'intera popolazione."),
    ("AVQ_BANCA_FILA_OLTRE_20_MIN", FLOW_PERSONE1.format(n=109), "18_BA_DUR_GE20", "HSC", "%", 1,
     "lower_better", "Benessere economico",
     "Utenti della banca con una fila di oltre 20 minuti",
     "Base: persone di 18 anni e piu che si sono recate in banca. Tema proposto, il piu vicino fra quelli Multiscopo."),
    ("AVQ_RICOVERO_ASSISTENZA_MEDICA", FLOW_PERSONE.format(n=256), "0_MED_CAREQ", "HSC", "%", 1,
     "higher_better", "Salute",
     "Ricoverati soddisfatti dell'assistenza medica",
     "Base: persone con un ricovero nei tre mesi precedenti l'intervista. "
     + SMALL_SAMPLE + " Non usare in indici compositi."),
    ("AVQ_INCIDENTI_DOMESTICI", FLOW_PERSONE1.format(n=235), "0_DOM_ACC", "TSC", "per 1000 persone", 1,
     "lower_better", "Salute",
     "Persone che hanno subito incidenti domestici negli ultimi 3 mesi",
     "Conteggio raro, valori piccoli e molto rumorosi: leggere la serie, non il singolo anno."),
    ("AVQ_BUS_FREQUENZA_CORSE", FLOW_PERSONE.format(n=160), "14_BUS_SAT_FC", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Utenti del bus soddisfatti della frequenza delle corse",
     "Base: utenti di autobus, filobus e tram di 14 anni e piu. Dettaglio dei composti BES sul trasporto pubblico."),
    ("AVQ_BUS_ATTESA_FERMATA", FLOW_PERSONE.format(n=160), "14_BUS_SAT_WAIT", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Utenti del bus soddisfatti della comodita dell'attesa alla fermata",
     "Base: utenti di autobus, filobus e tram di 14 anni e piu."),
    ("AVQ_BUS_COMODITA_ORARI", FLOW_PERSONE.format(n=160), "14_BUS_SAT_COMF", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Utenti del bus soddisfatti della comodita degli orari",
     "Base: utenti di autobus, filobus e tram di 14 anni e piu."),
    ("AVQ_LAVORO_AUTO_PRIVATA", FLOW_PERSONE.format(n=170), "15_EMPMOV_PCAR", "HSC", "%", 1,
     "contextual", "Ambiente",
     "Occupati che vanno al lavoro in auto privata come conducente",
     "Base: occupati che escono di casa per andare al lavoro."),
    ("AVQ_LAVORO_A_PIEDI", FLOW_PERSONE.format(n=170), "15_EMPMOV_FOOT", "HSC", "%", 1,
     "contextual", "Ambiente",
     "Occupati che vanno al lavoro a piedi",
     "Base: occupati che escono di casa per andare al lavoro."),
    ("AVQ_LAVORO_BICICLETTA", FLOW_PERSONE.format(n=170), "15_EMPMOV_BICYC", "HSC", "%", 1,
     "contextual", "Ambiente",
     "Occupati che vanno al lavoro in bicicletta",
     "Base: occupati che escono di casa per andare al lavoro. Valori molto bassi in alcune regions."),
    ("AVQ_GIOVANI_CON_GENITORI", FLOW_PERSONE.format(n=121), "18_YOUNG", "HSC", "%", 1,
     "contextual", "Abitazione",
     "Giovani di 18-34 anni, celibi e nubili, che vivono con almeno un genitore",
     "Verso non onesto: dipende anche dai costi di casa."),
    ("AVQ_TEATRO", FLOW_PERSONE.format(n=227), "6_THEATR", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Persone di 6 anni e piu che sono andate a teatro nell'ultimo anno",
     "Dettaglio per forma di spettacolo del composto BES sulla partecipazione culturale."),
    ("AVQ_CINEMA", FLOW_PERSONE.format(n=227), "6_CINEMA", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Persone di 6 anni e piu che sono andate al cinema nell'ultimo anno",
     "Dettaglio per forma di spettacolo del composto BES sulla partecipazione culturale."),
    ("AVQ_SITI_ARCHEOLOGICI", FLOW_PERSONE.format(n=227), "6_ARCHEO_MUSEUM", "HSC", "%", 1,
     "higher_better", "Benessere soggettivo",
     "Persone di 6 anni e piu che hanno visitato siti archeologici e monumenti nell'ultimo anno",
     "Dettaglio per forma di spettacolo del composto BES sulla partecipazione culturale."),
    ("AVQ_AMICI_OGNI_GIORNO", FLOW_PERSONE.format(n=107), "6_EVERYD", "HSC", "%", 1,
     "contextual", "Benessere soggettivo",
     "Persone di 6 anni e piu che incontrano gli amici ogni giorno",
     "Le categorie di frequenza sono esclusive: questa non e la quota di chi vede gli amici almeno una volta a settimana."),
    ("AVQ_CONDIZIONATORI", FLOW_FAMIGLIE.format(n=15), "HOUS_AIRCON", "HSC_F", "per 100 famiglie", 1,
     "contextual", "Energia",
     "Famiglie con condizionatore o climatizzatore",
     "Verso non onesto: dipende dal clima."),
    ("AVQ_PIU_DI_UN_AUTO", FLOW_FAMIGLIE.format(n=15), "HOUS_CARS", "HSC_F", "per 100 famiglie", 1,
     "contextual", "Benessere economico",
     "Famiglie con piu di un'automobile",
     "Verso non onesto."),
    ("AVQ_BICICLETTE", FLOW_FAMIGLIE.format(n=15), "HOUS_BICY", "HSC_F", "per 100 famiglie", 1,
     "contextual", "Ambiente",
     "Famiglie con almeno una bicicletta",
     "Verso non onesto."),
    ("AVQ_LAVASTOVIGLIE", FLOW_FAMIGLIE.format(n=15), "HOUS_DISH", "HSC_F", "per 100 famiglie", 1,
     "contextual", "Benessere economico",
     "Famiglie con lavastoviglie",
     "Dotazione durevole: direction non onesto."),
    ("AVQ_COLAZIONE_ADEGUATA", FLOW_PERSONE1.format(n=239), "3_ADEQ_BREAK", "HSC", "%", 1,
     "higher_better", "Salute",
     "Persone di 3 anni e piu che fanno una colazione adeguata",
     "Colazione adeguata: con latte e/o cibo. Dettaglio dell'alimentazione, non il composto BES."),
    ("AVQ_CINQUE_PORZIONI", FLOW_PERSONE1.format(n=251), "3_GE5_PORTION", "HSC", "%", 1,
     "higher_better", "Salute",
     "Persone di 3 anni e piu che mangiano 5 o piu porzioni di frutta e verdura al giorno",
     "Valori bassi e campione regionale con intervallo di confidenza non letto."),
]

OUTPUT_COLUMNS = ["indicator_id", "level", "territory_key", "year", "value"]
MANIFEST_COLUMNS = [
    "indicator_id", "name", "institution", "unit", "decimals", "direction", "theme",
    "source_url", "method_url", "license", "license_quote", "year_min", "year_max",
    "n_provincia", "n_regione", "note",
]


def region_key(name):
    """Stessa regola di `app.profiles.region_key_for` (copiata: qui niente Flask)."""
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return value.lower().replace("'", " ").replace(" ", "-")


def load_regions():
    """NUTS2 -> key regione, dal codelist ITTER107 gia versionato."""
    regions = {}
    with CODELIST_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            code = row["code"]
            if NUTS2_PATTERN.match(code) and code not in multiscopo_sources.TRENTINO_PARTS:
                regions[code] = region_key(row["name"].split("/", 1)[0].strip())
    return regions


def extract_indicator(rows, data_type, measure, regions):
    """{(chiave regione, anno): valore} per un DATA_TYPE, con Trentino ricomposto."""
    values = {}
    trentino_parts = defaultdict(dict)
    seen = set()
    for row in rows:
        if (row["DATA_TYPE"] != data_type or row["MEASURE"] != measure
                or row.get("SEX", "9") != "9"
                or row.get("NUMBER_HOUSEHOLD_COMP", "TOT") != "TOT"):
            continue
        area, year, raw = row["REF_AREA"], row["TIME_PERIOD"], row.get("OBS_VALUE")
        if raw in (None, "") or not year.isdigit() or int(year) < FIRST_YEAR:
            continue
        if (area, year) in seen:
            raise ValueError(f"{data_type}: osservazione duplicata per {area}, {year}")
        seen.add((area, year))
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError(f"{data_type}: valore non finito per {area}, {year}")
        if area in multiscopo_sources.TRENTINO_PARTS:
            trentino_parts[year][area] = number
        elif area in regions:
            values[(regions[area], int(year))] = number
    weights = multiscopo_sources.TRENTINO_WEIGHTS
    for year, parts in trentino_parts.items():
        if all(c in parts for c in multiscopo_sources.TRENTINO_PARTS):
            total = sum(weights[c] for c in multiscopo_sources.TRENTINO_PARTS)
            values[(TRENTINO_KEY, int(year))] = sum(
                parts[c] * weights[c] for c in multiscopo_sources.TRENTINO_PARTS
            ) / total
    return values


def format_value(number):
    """Valore con il punto decimale, arrotondato a 6 cifre come gli altri dataset."""
    return repr(round(number, 6))


def write_csv(rows, columns, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)
    tmp.replace(path)


def build(cache_dir=DEFAULT_CACHE, rete=False):
    client = istat_sdmx.SdmxClient(cache_dir=cache_dir, cache_only=not rete)
    regions = load_regions()
    by_flow = {}
    dataset, manifest, skipped = [], [], []
    for (ind, flow, data_type, measure, unit, decimals, direction, theme, name, note) in INDICATORS:
        if flow not in by_flow:
            try:
                by_flow[flow] = client.data(flow)
            except istat_sdmx.CacheMissError:
                by_flow[flow] = None
        rows = by_flow[flow]
        if rows is None:
            skipped.append((ind, "flusso non in cache"))
            continue
        values = extract_indicator(rows, data_type, measure, regions)
        if not values:
            skipped.append((ind, "nessun valore con i filtri dati"))
            continue
        for (key, year), number in sorted(values.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            dataset.append([ind, "regione", key, year, format_value(number)])
        years = [a for (_, a) in values]
        last_year = max(years)
        n_last = len({k for (k, a) in values if a == last_year})
        prefix = "_".join(flow.split("_")[:2])
        manifest.append([
            ind, name, INSTITUTION, unit, decimals, direction, theme,
            DATA_URL.format(flow=flow), METHOD_URL.format(dsd=DSD_PER_FLUSSO[prefix]),
            LICENSE, LICENSE_QUOTE, min(years), last_year, 0, n_last,
            f"{note} Flusso {flow}, DATA_TYPE {data_type}, MEASURE {measure}, SEX=9. "
            "Trentino Alto Adige: media ponderata sulla popolazione di Bolzano e Trento.",
        ])
    write_csv(dataset, OUTPUT_COLUMNS, OUTPUT)
    write_csv(manifest, MANIFEST_COLUMNS, MANIFEST)
    return dataset, manifest, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--offline", action="store_true",
                        help="legge solo la cache (comportamento di default)")
    parser.add_argument("--rete", action="store_true",
                        help="consente il client di rete (non usare: limite Istat)")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args(argv)
    dataset, manifest, skipped = build(args.cache_dir, rete=args.rete and not args.offline)
    print(f"{len(dataset)} righe, {len(manifest)} indicatori -> {OUTPUT.relative_to(PROJECT_ROOT)}")
    for ind, reason in skipped:
        print(f"SALTATO {ind}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
