"""Il modello dati della pagina /divari-regionali.

Un hub editoriale, non una seconda tassonomia. /temi e /regioni servono a
sfogliare il catalogo; questa pagina sostiene una tesi e la misura: il divario
italiano non e' una linea sola tra Nord e Sud, sono geografie diverse che non si
sovrappongono. Reddito e lavoro ordinano il paese in un modo, cultura e servizi
digitali in un altro, sicurezza percepita e rinnovabili in un terzo.

Tutti i numeri arrivano dal catalogo federato e vengono ricalcolati a ogni
render, quindi la prosa in pagina non puo' invecchiare rispetto ai dati: le
frasi contengono i valori, non li ripetono a mano.

Una avvertenza che vale per tutta la pagina: le medie di ripartizione qui sono
medie semplici dei valori regionali, non pesate per popolazione. Servono a
confrontare i territori tra loro, non a stimare il valore vero della
ripartizione, che per un indicatore per abitante richiederebbe i denominatori.
"""

from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator, get_atlas_indicator_year
from app.data import REGION_GEO_AREA
from app import indicator_notes
from app import profiles


# Le tre ripartizioni della pagina, nell'ordine in cui si leggono. Istat separa
# Sud e Isole: qui stanno insieme come Mezzogiorno, che e' il modo in cui il
# divario viene raccontato e cercato. La mappa chiave->ripartizione e' quella
# gia' in app/data.py, non una seconda.
AREA_ORDER = ("Nord", "Centro", "Mezzogiorno")

_AREA_BY_KEY = {
    key: ("Mezzogiorno" if area in ("Sud", "Isole") else area)
    for key, area in REGION_GEO_AREA.items()
}

# I tre divari che aprono la pagina, uno per dimensione: quanto si produce,
# quanti lavorano, quanto si vive. Sono i tre su cui ogni ripartizione viene
# misurata nella sua sezione, cosi' le tre sezioni si possono confrontare.
CORE_DIVARI = ("901", "13", "910")

# Gli altri divari della tabella finale. Set curato, non i primi N del catalogo:
# copre le quattro macro-aree e tutte le famiglie di fonti (Istat territoriali,
# Istat benessere, Istat vita quotidiana, Eurostat), e ogni voce ha una direzione
# dichiarata, copertura piena sulle venti regioni e un anno recente.
OTHER_DIVARI = (
    "902",                                    # reddito disponibile per abitante
    "930",                                    # indice di Gini del reddito
    "multiscopo:MULTI_REDD_MEDIO",            # reddito netto medio delle famiglie
    "12",                                     # tasso di disoccupazione
    "15",                                     # tasso di disoccupazione giovanile
    "408",                                    # giovani NEET
    "57",                                     # divario di genere nell'occupazione
    "bes:01SAL002",                           # speranza di vita in buona salute
    "590",                                    # emigrazione ospedaliera
    "142",                                    # servizi per l'infanzia
    "bes:02IST026-N22",                       # laureati 25-34 anni
    "102",                                    # abbandono scolastico
    "eur:rd_e_gerdreg",                       # spesa in ricerca e sviluppo sul PIL
    "multiscopo:MULTI_ICT_BANDA_LARGA_FISSA",  # banda larga fissa in famiglia
    "269",                                    # trasporto pubblico nei capoluoghi
    "52",                                     # raccolta differenziata
)

# Gli indicatori offerti dal selettore della mappa: gli stessi tre divari
# d'apertura piu i NEET, che e' la query con cui questa pagina viene cercata.
MAP_DIVARI = ("901", "13", "910", "408")

_MIN_YEAR = 2022
_BETTER_LOW = ("lower_better", "higher_worse")


def _area_of(region_key):
    return _AREA_BY_KEY.get(region_key)


def _direction(meta_or_item):
    return (meta_or_item.get("explain") or {}).get("direction")


def _area_means(values):
    """Media semplice per ripartizione, piu il numero di regioni che la compone."""
    buckets = {}
    for row in values:
        area = _area_of(row["region_key"])
        if area is None or row.get("value") is None:
            continue
        buckets.setdefault(area, []).append(row["value"])
    if any(area not in buckets for area in AREA_ORDER):
        return None
    return {
        area: {"mean": sum(buckets[area]) / len(buckets[area]), "regions": len(buckets[area])}
        for area in AREA_ORDER
    }


def _is_comparable(item):
    """Indicatori su cui un confronto tra ripartizioni ha senso.

    Serve una direzione dichiarata (senza verso "in testa" non vuol dire nulla),
    la copertura piena delle venti regioni e un anno recente. Le varianti di
    genere restano fuori: raddoppierebbero lo stesso divario.
    """
    if _direction(item) not in ("higher_better", "lower_better", "higher_worse"):
        return False
    if item.get("region_count", 0) < 20 or (item.get("completeness") or 0) < 0.98:
        return False
    if item.get("year_max", 0) < _MIN_YEAR:
        return False
    return not profiles.is_gender_variant(item)


def _scan_catalog():
    """Per ogni indicatore confrontabile: chi ha la media migliore, e di quanto.

    E' il conto che sostiene la tesi della pagina. Gira su tutto il catalogo
    federato, non su una selezione: 221 indicatori a oggi, sotto un decimo di
    secondo, perche' le serie sono gia' in cache di processo.
    """
    scanned = []
    for item in get_atlas_catalog()["indicators"]:
        if not _is_comparable(item):
            continue
        payload = get_atlas_indicator_year(item["id"], item["year_max"])
        if not payload:
            continue
        means = _area_means(payload["values"])
        if means is None:
            continue
        better_low = _direction(item) in _BETTER_LOW
        ranked = sorted(AREA_ORDER, key=lambda area: means[area]["mean"], reverse=not better_low)
        best, worst = means[ranked[0]]["mean"], means[ranked[-1]]["mean"]
        spread = abs(best - worst) / abs(worst) * 100 if worst else 0.0
        scanned.append({
            "id": item["id"],
            "name": item["name"],
            "path": item["path"],
            "theme": item["theme"],
            "year": item["year_max"],
            "leader": ranked[0],
            "last": ranked[-1],
            "spread_pct": spread,
        })
    return scanned


def _lead_tally(scanned):
    tally = {area: 0 for area in AREA_ORDER}
    for row in scanned:
        tally[row["leader"]] += 1
    return tally


def _examples_led_by(scanned, area, limit=3):
    """Gli indicatori su cui una ripartizione ha la media migliore, i piu netti.

    Ordinati per distanza dall'ultima ripartizione, cosi' gli esempi in pagina
    sono quelli dove il vantaggio e' evidente e non un decimale.
    """
    led = [row for row in scanned if row["leader"] == area]
    led.sort(key=lambda row: -row["spread_pct"])
    return led[:limit]


def _divario(indicator_id):
    """Un divario: le tre medie di ripartizione, la media nazionale, gli estremi."""
    payload = get_atlas_indicator(indicator_id)
    if payload is None:
        return None
    meta = payload["metadata"]
    year = meta["year_max"]
    year_payload = get_atlas_indicator_year(indicator_id, year)
    if not year_payload:
        return None
    values = year_payload["values"]
    means = _area_means(values)
    if means is None:
        return None

    direction = _direction(meta)
    better_low = direction in _BETTER_LOW
    national = sum(row["value"] for row in values) / len(values)
    ordered = sorted(values, key=lambda row: row["value"], reverse=not better_low)
    unit = indicator_notes.value_unit_label(meta["name"], meta.get("unit"))
    # L'unita' di una differenza non e' quella di un valore: su un indicatore in
    # percentuale la distanza dalla media nazionale si misura in punti, non in %.
    change_unit = indicator_notes.change_unit_label(meta["name"], meta.get("unit"))

    areas = {}
    for area in AREA_ORDER:
        mean = means[area]["mean"]
        in_area = [row for row in values if _area_of(row["region_key"]) == area]
        ranked_in_area = sorted(in_area, key=lambda row: row["value"], reverse=not better_low)
        delta = mean - national
        areas[area] = {
            "mean": mean,
            "regions": means[area]["regions"],
            "delta": delta,
            "delta_pct": (delta / national * 100) if national else 0.0,
            # "meglio" e "peggio" vengono dal verso dell'indicatore, non dal segno:
            # su disoccupazione o NEET stare sotto la media nazionale e' un bene.
            "better_than_national": (delta < 0) if better_low else (delta > 0),
            "lead": {
                "name": ranked_in_area[0]["region"],
                "key": ranked_in_area[0]["region_key"],
                "value": ranked_in_area[0]["value"],
            },
            "lag": {
                "name": ranked_in_area[-1]["region"],
                "key": ranked_in_area[-1]["region_key"],
                "value": ranked_in_area[-1]["value"],
            },
        }

    ranked_areas = sorted(AREA_ORDER, key=lambda area: areas[area]["mean"], reverse=not better_low)
    gap = abs(areas[ranked_areas[0]]["mean"] - areas[ranked_areas[-1]]["mean"])
    # Le barre in pagina esprimono la grandezza del valore, non il merito: si
    # normalizzano sulla media piu alta delle tre, altrimenti su un indicatore
    # "meglio se basso" la ripartizione migliore avrebbe la barra piu lunga.
    bar_max = max(areas[area]["mean"] for area in AREA_ORDER)
    return {
        "id": meta["id"],
        "name": meta["name"],
        "path": meta["path"],
        "theme": meta["theme"],
        "family_label": meta.get("family_label") or meta.get("catalog_family_label", ""),
        "year": year,
        "unit": unit,
        "change_unit": change_unit,
        "direction": direction,
        "better_low": better_low,
        "national": national,
        "bar_max": bar_max,
        "areas": areas,
        "leader": ranked_areas[0],
        "last": ranked_areas[-1],
        "gap": gap,
        "gap_pct": (gap / areas[ranked_areas[-1]]["mean"] * 100) if areas[ranked_areas[-1]]["mean"] else 0.0,
        "national_lead": {"name": ordered[0]["region"], "key": ordered[0]["region_key"], "value": ordered[0]["value"]},
        "national_lag": {"name": ordered[-1]["region"], "key": ordered[-1]["region_key"], "value": ordered[-1]["value"]},
    }


def _region_names(area):
    return [
        {"key": key, "name": profiles.region_name(key)}
        for key, mapped in _AREA_BY_KEY.items()
        if mapped == area
    ]


def build_divari_view():
    """Tutto quello che la pagina /divari-regionali mostra, dai dati veri."""
    scanned = _scan_catalog()
    tally = _lead_tally(scanned)

    core = [divario for divario in (_divario(item_id) for item_id in CORE_DIVARI) if divario]
    others = [divario for divario in (_divario(item_id) for item_id in OTHER_DIVARI) if divario]
    if not core:
        return None

    areas = []
    for area in AREA_ORDER:
        cards_for_area = [divario["areas"][area] for divario in core]
        areas.append({
            "name": area,
            "regions": sorted(_region_names(area), key=lambda row: row["name"]),
            "leads": tally[area],
            # La quota, non la frazione a mano: "un indicatore su quattro"
            # invecchierebbe al primo aggiornamento del catalogo.
            "share": round(tally[area] / len(scanned) * 100) if scanned else 0,
            "above_national": sum(1 for card in cards_for_area if card["better_than_national"]),
            "examples": _examples_led_by(scanned, area),
            "cards": [
                {
                    "indicator": divario["name"],
                    "path": divario["path"],
                    "theme": divario["theme"],
                    "year": divario["year"],
                    "unit": divario["unit"],
                    "change_unit": divario["change_unit"],
                    **divario["areas"][area],
                }
                for divario in core
            ],
        })

    years = [divario["year"] for divario in core + others]
    return {
        "scanned": len(scanned),
        "tally": tally,
        "share": {area: round(tally[area] / len(scanned) * 100) if scanned else 0 for area in AREA_ORDER},
        "core": core,
        "others": sorted(others, key=lambda divario: -divario["gap_pct"]),
        "areas": areas,
        "year_min": min(years),
        "year_max": max(years),
        "indicator_links": len({divario["path"] for divario in core + others}),
    }
