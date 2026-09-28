"""Il dossier di una scheda indicatore, da cui il team leader compone il brief.

    bin/py -m scripts.editoriale.brief ter-12 --out /tmp/ter-12.json
    bin/py -m scripts.editoriale.brief bes:06POL012P --out /tmp/carceri.json

Accetta il codice nelle quattro forme che circolano (`ter-12`, `12`,
`bes-06POL012P`, `bes:06POL012P`) e scrive un JSON deterministico: stessi dati,
stesso file, byte per byte.

Il pilota sulle carceri ha mostrato il difetto da evitare: 39 fatti statistici
e nessun materiale per spiegare. Qui ci sono la forma della serie, le
dimensioni (i fratelli di genere, il livello gemello), le ripartizioni, il
contesto economico dei territori agli estremi e gli avvisi su cio' che non si
puo' scrivere. Non ci sono frasi fatte e non ci sono giudizi: nessun "migliore"
o "peggiore", nessuna cornice del verso. L'ordine e' sempre per valore, e il
verso della classifica del sito e' dichiarato come fatto.

Ogni numero e' `{"valore": 9.83, "testo": "9,8%"}`: il testo esce da
`app/design/numfmt.py` (tramite `app/design/common.py`), la stessa regola delle
pagine, cosi' la cifra del brief e' quella che il lettore trova nella scheda.

Niente di questo ricalcola cio' che il view model della scheda
(`app.indicator_view.build_indicator_view`) calcola gia': media, mediana,
variazioni, pannello fisso vengono da li'. Il modulo aggiunge solo cio' che la
scheda non ha: forma della serie, ripartizioni, confronto di genere,
correlazioni di rango.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from app import sources
from app.design import common, numfmt

# Decimali tenuti nel campo `valore`: gli stessi del golden di
# `scripts/dump_indicator_stats.py`, molto oltre quelli che una pagina stampa.
PRECISION = 6
TOP_N = 3

# Sotto questo numero di territori una correlazione di rango descrive due o tre
# punti: la stessa soglia `SMALL_N` di `data.indicator_trend_stats`.
MIN_CORRELATION_N = 5

# Il contesto economico dei territori agli estremi: PIL pro capite, reddito
# disponibile per abitante, tasso di occupazione, occupazione 20-64 anni.
CONTEXT_CODES = ("ter-901", "ter-902", "ter-13", "ter-345")

# Le soglie che una misura porta nella sua definizione. Curate a mano e tenute
# corte di proposito: una soglia scelta da noi sarebbe un giudizio. 06POL012P
# e' detenuti su posti regolamentari per cento, quindi a 100 i detenuti sono
# pari ai posti.
THRESHOLDS = {
    "bes-06POL012P": {
        "valore": 100,
        "motivo": "detenuti su posti regolamentari per cento: a 100 i detenuti sono pari ai posti",
    },
}

# L'estremo non verificato di ogni scheda in `seo_titles.UNVERIFIED_EXTREMES`:
# quale territorio, in quale anno. Quel set dice che il sito non scrive
# l'intervallo fra gli estremi in title, description e Dataset, non quale capo
# e' il sospetto: quello lo sa solo la fonte, e sta in due commenti che la
# spiegano. In `app/seo_titles.py` la scheda e' elencata e si legge che gli zeri
# di Macerata e Savona dal 2016 non erano una misura; nel commento a
# `NOT_MEASURED` di `app/bes_data.py` si legge che il 358,1 di Fermo nel 2024
# non sta fra quelli, e quindi resta un valore, non un buco. Un solo capo: il
# minimo rimasto e' un valore vero, e segnarlo farebbe scrivere al lettore un
# dubbio che il dato non ha. Il valore non e' scritto qui perche' esce dai dati
# del sito, che sono la fonte; se l'anno della fonte cambia, questa tabella
# cambia con lui.
UNVERIFIED_OBSERVATION = {
    "bes-06POL012P": {"territorio": "Fermo", "anno": 2024},
}

AREA_ORDER = ("Nord", "Centro", "Mezzogiorno")

# Il segno sulla riga del territorio non verificato e sulle cifre che dipendono
# dagli estremi della sua serie: chi copia "10,2 volte" deve vedere che la
# cifra poggia su un valore non verificato, senza cercare l'avviso altrove.
EXTREME_FLAG = "vedi_avviso_estremi"


# --- funzioni pure ----------------------------------------------------------


def rounded(value):
    """Il valore per le macchine, arrotondato a PRECISION decimali."""
    if value is None:
        return None
    return round(float(value), PRECISION)


def figure(value, unit):
    """Una cifra con la sua unita', come si scrive in una frase."""
    if value is None:
        return None
    return {"valore": rounded(value), "testo": common.with_unit(value, unit)}


def change(value, unit):
    """Una variazione: col segno, e "invariato" quando la cifra arrotondata e' zero."""
    if value is None:
        return None
    shown = numfmt.change_text(value)
    text = shown if shown == numfmt.UNCHANGED else common.signed(value, unit)
    return {"valore": rounded(value), "testo": text}


def count(n):
    """Un conteggio: sempre intero."""
    if n is None:
        return None
    return {"valore": int(n), "testo": numfmt.text(n, numfmt.FIXED["count"])}


def ratio(value):
    """Un rapporto, "7,0 volte": sempre un decimale."""
    if value is None:
        return None
    return {"valore": rounded(value), "testo": f"{numfmt.text(value, numfmt.FIXED['ratio'])} volte"}


def coefficient(value):
    """Un coefficiente di correlazione, sempre con due decimali: la regola della
    grandezza ne darebbe quattro vicino allo zero, dove non dicono niente."""
    if value is None:
        return None
    return {"valore": rounded(value), "testo": numfmt.text(value, 2)}


def average_ranks(values):
    """I ranghi di `values` (1 al piu' piccolo), con la media dei ranghi sui pari."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        mean_rank = (start + end) / 2 + 1
        for position in range(start, end + 1):
            ranks[order[position]] = mean_rank
        start = end + 1
    return ranks


def rank_correlation(xs, ys):
    """Il rho di Spearman fra due liste appaiate, o None.

    None con meno di tre coppie o quando una delle due liste e' costante: una
    correlazione non si definisce."""
    if len(xs) != len(ys):
        raise ValueError(f"liste di lunghezza diversa: {len(xs)} e {len(ys)}")
    if len(xs) < 3:
        return None
    rx, ry = average_ranks(xs), average_ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def series_shape(points):
    """La forma di una serie `[(anno, valore), ...]` in ordine di anno.

    Torna massimo e minimo (a parita', l'anno piu' vecchio), le svolte (l'anno
    in cui la serie cambia verso: un tratto piatto non e' una svolta, e la
    svolta cade alla fine del piano) e i tratti, cioe' le corse consecutive
    nello stesso verso. Descrive e basta: salire non e' ne' bene ne' male.
    """
    points = sorted(points)
    if not points:
        return None
    maximum = max(points, key=lambda p: (p[1], -p[0]))
    minimum = min(points, key=lambda p: (p[1], p[0]))
    turns = []
    runs = []
    last_sign = 0
    for i in range(1, len(points)):
        delta = points[i][1] - points[i - 1][1]
        sign = (delta > 0) - (delta < 0)
        if runs and runs[-1]["sign"] == sign:
            runs[-1]["to"] = points[i][0]
        else:
            runs.append({"sign": sign, "from": points[i - 1][0], "to": points[i][0]})
        if sign == 0:
            continue
        if last_sign and sign != last_sign:
            turns.append({
                "year": points[i - 1][0],
                "kind": "massimo locale" if last_sign > 0 else "minimo locale",
                "value": points[i - 1][1],
            })
        last_sign = sign
    verbs = {1: "sale", -1: "scende", 0: "piatto"}
    return {
        "max": {"year": maximum[0], "value": maximum[1]},
        "min": {"year": minimum[0], "value": minimum[1]},
        "turns": turns,
        "runs": [{"from": r["from"], "to": r["to"], "direction": verbs[r["sign"]]} for r in runs],
    }


def movers(start, end, k=TOP_N):
    """I territori che si sono mossi di piu' fra due fotografie `{chiave: valore}`.

    Solo i territori presenti in tutte e due. Torna `(aumenti, cali)`, ciascuno
    una lista di `(chiave, prima, dopo, delta)` di al massimo `k` elementi: gli
    aumenti dal piu' grande, i cali dal piu' profondo. A parita', la chiave.
    """
    deltas = [(key, start[key], end[key], end[key] - start[key]) for key in sorted(set(start) & set(end))]
    increases = sorted((d for d in deltas if d[3] > 0), key=lambda d: (-d[3], d[0]))[:k]
    decreases = sorted((d for d in deltas if d[3] < 0), key=lambda d: (d[3], d[0]))[:k]
    return increases, decreases


def territory_changes(start, end):
    """La variazione di **ogni** territorio presente in entrambe le fotografie.

    Una lista sola di `(chiave, prima, dopo, delta)`, dalla variazione piu'
    ampita' in valore assoluto alla piu' stretta e, a parita', dalla chiave:
    l'ordine non cambia fra due esecuzioni ne' fra due versioni dei dati, e il
    primo di lista e' il territorio che si e' mosso di piu'. `movers` tiene i
    soli tre di ciascun verso, e non basta: il lettore dell'articolo spesso
    scrive di una provincia che non e' fra i tre.
    """
    deltas = [(key, start[key], end[key], end[key] - start[key]) for key in sorted(set(start) & set(end))]
    return sorted(deltas, key=lambda d: (-abs(d[3]), d[0]))


def year_values(level, year):
    """`{chiave: valore}` di un livello in un anno, solo le celle numeriche."""
    row = (level.get("matrix") or {}).get(str(year)) or {}
    return {key: value for key, value in row.items() if isinstance(value, (int, float))}


# --- risoluzione del codice -------------------------------------------------


def _known_keys():
    """Le chiavi interne di ogni scheda: l'atlante, piu' BES e Multiscopo interi.

    Il catalogo dell'atlante non basta: le serie BES solo provinciali (come
    06POL012P) non ci entrano, ma hanno una scheda."""
    from app.atlas_catalog import get_atlas_catalog
    from app.bes_data import all_bes_indicators
    from app.multiscopo_data import all_multiscopo_indicators

    keys = {str(item["id"]) for item in get_atlas_catalog()["indicators"]}
    keys |= {sources.internal_id("bes", item["id"]) for item in all_bes_indicators()}
    keys |= {sources.internal_id("multiscopo", item["id"]) for item in all_multiscopo_indicators()}
    return keys


def resolve(code):
    """`(famiglia, id)` di un codice in una delle quattro forme, o LookupError."""
    from scripts.indicator_store import resolve_key

    code = str(code).strip()
    keys = _known_keys()
    key = resolve_key(keys, code)
    parsed = sources.parse_indicator_code(code)
    # `resolve_key` confronta solo la parte dopo il trattino: `ims-12` gli
    # basterebbe per tornare la territoriale 12. L'acronimo scritto vince.
    if parsed and (key is None or sources.split_internal_id(key)[0] != parsed[0]):
        expected = sources.internal_id(*parsed)
        key = expected if expected in keys else None
    if key is None:
        raise LookupError(f"nessuna scheda per {code!r} (forme accettate: ter-12, 12, bes-06POL012P, bes:06POL012P)")
    return sources.split_internal_id(key)


# --- il dossier -------------------------------------------------------------


def build(code):
    """Il dossier di una scheda, come dict pronto per `json.dumps`."""
    from app.indicator_view import build_indicator_view

    family, raw_id = resolve(code)
    view = build_indicator_view(family, raw_id)
    if view is None:
        raise LookupError(f"{code!r} risolve in {family}/{raw_id}, ma la scheda non si costruisce")
    return _dossier(view)


def _dossier(view):
    from app.indicator_notes import figure_unit

    meta = view["meta"]
    code = sources.indicator_code(meta["family"], meta["raw_id"])
    units = {
        "value": figure_unit(meta["name"], meta["unit"]),
        "change": meta["change_unit"],
    }
    official = _official_areas(meta)
    levels = []
    for level in view["levels"]:
        universe = _universe(level)
        area_of = _area_lookup(level)
        levels.append({
            "livello": level["key"],
            "fotografia": _snapshot(meta, code, level, universe, area_of, units, official),
            "serie": _series(meta, level, units),
        })
    return {
        "identita": _identity(meta, code, view, units),
        "livelli": levels,
        "dimensioni": _dimensions(meta, view, units),
        "avvisi": _warnings(meta, code, view),
        "contesto_economico": _economic_context(view, units),
    }


def _identity(meta, code, view, units):
    ascending = meta["direction"] in ("lower_better", "higher_worse")
    return {
        "chiave": str(meta["id"]),
        "codice": code,
        "nome": meta["name"],
        "percorso": meta["canonical_path"],
        "tema": meta.get("theme"),
        "sottotema_fonte": meta.get("source_theme"),
        "definizione_fonte": meta.get("archive"),
        "unita": {
            "fonte": meta.get("unit"),
            "cifra": units["value"],
            "variazione": units["change"],
        },
        # Il verso come fatto: in che ordine la scheda del sito mette i
        # territori, non quale valore sia desiderabile.
        "verso": {
            "classifica_del_sito": "dal valore piu' basso" if ascending else "dal valore piu' alto",
            "classifica_attiva": bool(meta["scoreable"]),
        },
        "livelli": [
            {
                "livello": level["key"],
                "percorso": level["canonical_path"],
                "primo_anno": level["year_min"],
                "ultimo_anno": level["year_max"],
                "anni": level["years"],
                "territori_ultimo_anno": count(len(level["observations"])),
                "territori_totali": count(level["territory_total"]),
            }
            for level in view["levels"]
        ],
        "anni": {"primo": meta["year_min"], "ultimo": meta["year_max"]},
        "fonte": {
            "etichetta": meta["source_label"],
            "famiglia": sources.family_label(meta["family"]),
            "istituzione": meta["institution"],
            "url": meta.get("source_url"),
            "url_dati": meta.get("source_data_url"),
            "licenza": dict(zip(("etichetta", "url"), sources.family_license(meta["family"]))),
        },
    }


def _universe(level):
    """`{chiave: nome}` dei territori che il livello dovrebbe avere."""
    from app.bes_data import get_bes_territories
    from app.data import REGION_ORDER
    from app.profiles import region_key_for

    if level["key"] == "provincia":
        return {key: info["name"] for key, info in get_bes_territories("provincia").items()}
    return {region_key_for(name): name for name in REGION_ORDER}


def _area_lookup(level):
    """`{chiave: (ripartizione, regione o None)}` per ogni territorio del livello.

    Per le province la ripartizione e' quella della regione. Una provincia che
    non si aggancia a nessuna delle venti regioni e' un errore, non un buco."""
    from app.divari import _AREA_BY_KEY
    from app.profiles import region_key_for

    if level["key"] != "provincia":
        return {t["key"]: (_AREA_BY_KEY[t["key"]], None) for t in level["territories"]}
    out = {}
    for key, region in (level.get("region_of") or {}).items():
        area = _AREA_BY_KEY.get(region_key_for(region or ""))
        if area is None:
            raise ValueError(f"provincia {key!r}: regione {region!r} senza ripartizione")
        out[key] = (area, region)
    missing = [t["key"] for t in level["territories"] if t["key"] not in out]
    if missing:
        raise ValueError(f"province senza regione: {missing}")
    return out


def _official_areas(meta):
    """I valori ufficiali Istat per Italia e ripartizioni, se il repo li ha.

    Stanno in `data/derived/bes_areas_<codice>` (`scripts/trend_articles/
    derive_bes_areas.py`), solo per le BES regionali per cui un articolo li ha
    chiesti. Sono medie pesate dell'Istat, non medie semplici delle regioni."""
    if meta["family"] != "bes":
        return None
    from scripts.trend_articles import common as trend

    name = f"bes_areas_{meta['raw_id']}"
    if not (trend.DERIVED_DIR / f"{name}.json").exists():
        return None
    return trend.derived_series(name)


def _snapshot(meta, code, level, universe, area_of, units, official):
    unit = units["value"]
    year = level["year_max"]
    stats = level["stats"]
    by_value = sorted(level["observations"], key=lambda o: (-o["value"], o["name"]))
    unverified = _unverified_observation(code, level)

    def row(position, obs):
        area, region = area_of[obs["key"]]
        out = {
            "posizione_per_valore": position,
            "territorio": obs["name"],
            "chiave": obs["key"],
            "ripartizione": area,
        }
        if region:
            out["regione"] = region
        out["valore"] = figure(obs["value"], unit)
        if unverified is not None and obs["key"] == unverified["key"]:
            out[EXTREME_FLAG] = True
        return out

    rows = [row(i + 1, obs) for i, obs in enumerate(by_value)]
    values = [obs["value"] for obs in by_value]
    high, low = (values[0], values[-1]) if values else (None, None)
    points_unit = numfmt.phrase_unit(unit) == numfmt.POINTS or "differenza" in meta["name"].lower()
    plural = level["plural"]

    areas = []
    for name in AREA_ORDER:
        members = [r for r, obs in zip(rows, by_value) if r["ripartizione"] == name]
        member_values = [obs["value"] for r, obs in zip(rows, by_value) if r["ripartizione"] == name]
        if not members:
            continue
        areas.append({
            "ripartizione": name,
            "territori": count(len(members)),
            "media_semplice": figure(sum(member_values) / len(member_values), unit),
            "piu_alto": {"territorio": members[0]["territorio"], "valore": members[0]["valore"]},
            "piu_basso": {"territorio": members[-1]["territorio"], "valore": members[-1]["valore"]},
        })

    return {
        "anno": year,
        "ordine": "dal valore piu' alto al piu' basso",
        "territori_con_dato": count(len(rows)),
        "territori_totali": count(len(universe)),
        "valori": rows,
        "media_semplice_territori": {
            "etichetta": f"media semplice dei valori delle {len(rows)} {plural}, non la media nazionale",
            **(figure(stats["year_avg"], unit) or {}),
        },
        "valore_italia": _italy(official, year, unit, level["key"]),
        "mediana": figure(stats["median"], unit),
        "sopra_la_media_semplice": count(stats["above_avg_count"]),
        "sotto_la_media_semplice": count(stats["below_avg_count"]),
        "piu_alti": rows[:TOP_N],
        "piu_bassi": list(reversed(rows[-TOP_N:])),
        "distanza_fra_estremi": _flagged(figure(high - low, units["change"]) if values else None, unverified),
        "rapporto_fra_estremi": _flagged(
            ratio(high / low) if values and low > 0 and not points_unit else None, unverified
        ),
        "ripartizioni": {
            "metodo": f"media semplice dei valori delle {plural} di ogni ripartizione, Mezzogiorno = Sud e Isole",
            "valori": areas,
        },
        "soglia": _threshold(code, by_value, unit),
    }


def _flagged(fig, unverified):
    """La cifra col segno `EXTREME_FLAG` quando dipende da estremi non verificati."""
    if fig is None or not unverified:
        return fig
    return {**fig, EXTREME_FLAG: True}


def _italy(official, year, unit, level_key):
    note = "la fonte nei dati del sito non porta il valore Italia"
    if official is None or level_key != "regione":
        return {"valore": None, "nota": note}
    values = official["values"]
    italy = values.get("Italia") or {}
    shown_year = year if year in italy else max(italy, default=None)
    if shown_year is None:
        return {"valore": None, "nota": note}
    return {
        "anno": shown_year,
        **figure(italy[shown_year], unit),
        "ripartizioni_ufficiali": [
            {"ripartizione": name, **figure(values[name][shown_year], unit)}
            for name in AREA_ORDER
            if shown_year in (values.get(name) or {})
        ],
        "fonte": official["meta"]["file"],
        "metodo": official["meta"]["method"],
    }


def _threshold(code, by_value, unit):
    spec = THRESHOLDS.get(code)
    if spec is None:
        return None
    limit = spec["valore"]
    above = [obs for obs in by_value if obs["value"] > limit]
    return {
        "soglia": figure(limit, unit),
        "motivo": spec["motivo"],
        "sopra": count(len(above)),
        "pari": count(sum(1 for obs in by_value if obs["value"] == limit)),
        "sotto": count(sum(1 for obs in by_value if obs["value"] < limit)),
        "territori_sopra": [obs["name"] for obs in above],
    }


def _series(meta, level, units):
    from app.indicator_view import fixed_panel, panel_need

    unit = units["value"]
    coverage = {y: len(year_values(level, y)) for y in level["years"]}
    need = panel_need(level["key"])
    unverified = _unverified_observation(_unverified_code(meta), level)
    per_year = []
    for point in level["annual_means"]:
        snapshot = year_values(level, point["year"])
        per_year.append({
            "anno": point["year"],
            "media_semplice": figure(point["avg"], unit),
            "territori": count(coverage.get(point["year"], 0)),
            "copertura_parziale": coverage.get(point["year"], 0) < need,
            "distanza_fra_estremi": _flagged(
                figure(max(snapshot.values()) - min(snapshot.values()), units["change"]),
                point["year"] == level["year_max"] and unverified is not None,
            ),
        })

    panel = fixed_panel(level)
    if panel:
        points = [(p["year"], p["value"]) for p in panel["points"]]
        base = {
            "tipo": "pannello fisso",
            "territori": count(panel["members"]),
            "totale": count(panel["total"]),
            "anni_esclusi": count(panel["dropped"]),
            "metodo": "media semplice dei territori presenti in tutti gli anni in cui almeno l'80% dei territori ha il dato",
        }
    else:
        points = [(p["year"], p["avg"]) for p in level["annual_means"]]
        base = {
            "tipo": "media semplice anno per anno",
            "metodo": "media semplice dei territori presenti in ciascun anno: il gruppo puo' cambiare da un anno all'altro",
        }
    shape = series_shape(points)

    stats = level["stats"]
    first, last = level["year_min"], level["year_max"]
    long_run = None
    if stats["has_multi_year"]:
        long_run = {
            "da": first,
            "a": last,
            "media_semplice_da": figure(stats["year_min_avg"], unit),
            "media_semplice_a": figure(stats["year_avg"], unit),
            "assoluta": change(stats["avg_change_abs"], units["change"]),
            "relativa": None if meta["percentage_like"] else change(stats["avg_change_pct"], "%"),
            "territori_da": count(coverage[first]),
            "territori_a": count(coverage[last]),
        }
        if meta["percentage_like"]:
            long_run["nota_relativa"] = "unita' percentuale: la variazione si scrive in punti, non in percentuale"
        if coverage[first] != coverage[last]:
            long_run["nota_copertura"] = "le due medie stanno su gruppi di territori diversi"
        if panel and len(points) > 1:
            long_run["sul_pannello"] = {
                "da": points[0][0],
                "a": points[-1][0],
                "assoluta": change(points[-1][1] - points[0][1], units["change"]),
            }

    return {
        "media_semplice_per_anno": per_year,
        "forma": {
            "base": base,
            "punti": [{"anno": y, "valore": figure(v, unit)} for y, v in points],
            "massimo": {"anno": shape["max"]["year"], "valore": figure(shape["max"]["value"], unit)},
            "minimo": {"anno": shape["min"]["year"], "valore": figure(shape["min"]["value"], unit)},
            "svolte": [
                {"anno": t["year"], "tipo": t["kind"], "valore": figure(t["value"], unit)}
                for t in shape["turns"]
            ],
            "tratti": [{"da": r["from"], "a": r["to"], "verso": r["direction"]} for r in shape["runs"]],
        },
        "variazione_lungo_periodo": long_run,
        "variazione_ultimo_anno": _annual(level["annual_change"], unit, units["change"]),
        "territori_piu_mossi": _movers(level, units["change"]),
        "variazione_per_territorio": _changes(level, units["value"], units["change"]),
    }


def _annual(annual, unit, change_unit):
    if not annual:
        return None

    def moves(items):
        return [
            {
                "territorio": item["name"],
                "prima": figure(item["previous_value"], unit),
                "dopo": figure(item["current_value"], unit),
                "variazione": change(item["delta"], change_unit),
            }
            for item in items
        ]

    return {
        "da": annual["previous_year"],
        "a": annual["year"],
        "territori_comuni": count(annual["common_count"]),
        "media_semplice_da": figure(annual["previous_avg"], unit),
        "media_semplice_a": figure(annual["current_avg"], unit),
        "variazione": change(annual["average_delta"], change_unit),
        "in_aumento": count(annual["increase_count"]),
        "in_calo": count(annual["decrease_count"]),
        "invariati": count(annual["stable_count"]),
        "aumenti_maggiori": moves(annual["largest_increases"]),
        "cali_maggiori": moves(annual["largest_decreases"]),
    }


def _movers(level, change_unit):
    """Fra il primo e l'ultimo anno del livello, sui territori presenti in tutti e due."""
    first, last = level["year_min"], level["year_max"]
    if first == last:
        return None
    names = {t["key"]: t["name"] for t in level["territories"]}
    start, end = year_values(level, first), year_values(level, last)
    increases, decreases = movers(start, end)

    def rows(items):
        return [{"territorio": names[key], "variazione": change(delta, change_unit)} for key, _, _, delta in items]

    return {
        "da": first,
        "a": last,
        "territori_comuni": count(len(set(start) & set(end))),
        "aumenti": rows(increases),
        "cali": rows(decreases),
    }


def _changes(level, value_unit, change_unit):
    """La variazione dal primo all'ultimo anno di ogni territorio, tutta intera.

    `territori_piu_mossi` tiene i tre di ciascun verso e serve a dire dove il
    movimento e' maggiore; questa lista e' quella completa, e ci sta perche' il
    pezzo che si scrive spesso e' proprio un territorio che non sta fra i tre.
    Ogni riga porta il valore di partenza, quello di arrivo e la variazione,
    gia' scritti: il team leader non ricalcola niente."""
    first, last = level["year_min"], level["year_max"]
    if first == last:
        return None
    names = {t["key"]: t["name"] for t in level["territories"]}
    rows = territory_changes(year_values(level, first), year_values(level, last))
    return {
        "da": first,
        "a": last,
        "ordine": "dalla variazione piu' ampita' alla piu' stretta, a parita' per territorio",
        "territori": count(len(rows)),
        "valori": [
            {
                "territorio": names[key],
                "prima": figure(before, value_unit),
                "dopo": figure(after, value_unit),
                "variazione": change(delta, change_unit),
            }
            for key, before, after, delta in rows
        ],
    }


def _dimensions(meta, view, units):
    from app.indicator_view import build_indicator_view

    siblings = []
    levels = {}
    for sibling in view["dimension_siblings"]:
        family, raw_id = sources.split_internal_id(sibling["id"])
        sibling_view = build_indicator_view(family, raw_id)
        level = _level(sibling_view, "regione")
        if level is None:
            continue
        levels[sibling["value"]] = level
        siblings.append({
            "codice": sources.indicator_code(family, raw_id),
            "nome": sibling["name"],
            "dimensione": sibling["value"],
            "percorso": sibling["path"],
            "ultimo_anno": level["year_max"],
            "media_semplice_ultimo_anno": figure(level["stats"]["year_avg"], units["value"]),
        })
    # La famiglia elenca gli altri membri: questo e' quello che resta.
    own = None
    if siblings:
        rest = {"totale", "maschi", "femmine"} - {s["dimensione"] for s in siblings}
        own = rest.pop() if len(rest) == 1 else None
        if own:
            levels.setdefault(own, _level(view, "regione"))

    twin = view["twin"]
    return {
        "dimensione_di_questa_scheda": own,
        "fratelli": siblings,
        "confronto_per_territorio": _gender_gap(levels, units),
        "livelli_nella_scheda": [level["key"] for level in view["levels"]],
        "gemello_di_livello": {
            "livello": twin["key"],
            "codice": twin["code"],
            "percorso": twin["path"],
            "ancora": twin["anchor"],
        } if twin else None,
    }


def _level(view, key):
    if view is None:
        return None
    return next((level for level in view["levels"] if level["key"] == key), None)


def _gender_gap(levels, units):
    """Femmine meno maschi, territorio per territorio, sull'ultimo anno comune."""
    men, women = levels.get("maschi"), levels.get("femmine")
    if men is None or women is None:
        return None
    common_years = set(men["years"]) & set(women["years"])
    if not common_years:
        return None
    year = max(common_years)
    m, f = year_values(men, year), year_values(women, year)
    total = year_values(levels["totale"], year) if levels.get("totale") else {}
    names = {t["key"]: t["name"] for t in men["territories"]}
    rows = []
    for key in sorted(set(m) & set(f)):
        rows.append({
            "territorio": names[key],
            "totale": figure(total.get(key), units["value"]),
            "maschi": figure(m[key], units["value"]),
            "femmine": figure(f[key], units["value"]),
            "distanza": change(f[key] - m[key], units["change"]),
        })
    rows.sort(key=lambda r: (-r["distanza"]["valore"], r["territorio"]))
    gaps = [r["distanza"]["valore"] for r in rows]
    return {
        "anno": year,
        "distanza": "femmine meno maschi",
        "ordine": "dalla distanza piu' alta alla piu' bassa",
        "territori": count(len(rows)),
        "distanza_media_semplice": change(sum(gaps) / len(gaps), units["change"]) if gaps else None,
        "valori": rows,
    }


def _warnings(meta, code, view):
    from app.bes_data import NOT_MEASURED
    from app.indicator_view import panel_need
    unit = _value_unit(meta)
    extremes, missing, partial = [], [], []
    for level in view["levels"]:
        unverified = _unverified_observation(code, level)
        if unverified is not None:
            extremes.append({
                "livello": level["key"],
                "anno": level["year_max"],
                "territorio": unverified["name"],
                "valore": figure(unverified["value"], unit),
                "motivo": "codice in seo_titles.UNVERIFIED_EXTREMES: il sito non scrive in title, description e "
                          "Dataset l'intervallo fra gli estremi di questa serie. L'estremo non verificato e' solo "
                          "quello qui indicato, l'altro capo e' un valore vero e non porta il segno. La ragione "
                          "e' nel commento a UNVERIFIED_EXTREMES in app/seo_titles.py, il valore nel commento a "
                          "NOT_MEASURED in app/bes_data.py",
                "cifre_segnate": f"la riga di questo territorio e le cifre derivate dagli estremi portano {EXTREME_FLAG}",
            })
        present = {o["key"] for o in level["observations"]}
        for key, name in sorted(_universe(level).items(), key=lambda item: item[1]):
            if key in present:
                continue
            not_measured = (meta["raw_id"], name, level["year_max"]) in NOT_MEASURED
            missing.append({
                "livello": level["key"],
                "anno": level["year_max"],
                "territorio": name,
                "motivo": "la fonte scrive una cella che non e' una misura (bes_data.NOT_MEASURED)"
                if not_measured else "nessun valore nella fonte",
            })
        need = panel_need(level["key"])
        for year in level["years"]:
            n = len(year_values(level, year))
            if n < need:
                partial.append({
                    "livello": level["key"],
                    "anno": year,
                    "territori": count(n),
                    "soglia": count(need),
                    "totale": count(len(_universe(level))),
                })
    return {
        "estremi_non_verificati": extremes,
        "territori_non_misurati": missing,
        "anni_copertura_parziale": partial,
    }


def _unverified_code(meta):
    return sources.indicator_code(meta["family"], meta["raw_id"])


def _unverified():
    from app.seo_titles import UNVERIFIED_EXTREMES

    return UNVERIFIED_EXTREMES


def _unverified_observation(code, level):
    """L'osservazione non verificata di questo livello, o None.

    Un solo capo per scheda, quello che `UNVERIFIED_OBSERVATION` indica, e solo
    se e' l'ultimo anno del livello: e' l'anno che la scheda mostra, quindi
    l'unico in cui l'estremo si vede. La scheda resta in `UNVERIFIED_EXTREMES`
    altrimenti: e' il sito a decidere se l'intervallo si scrive, e una tabella
    locale che lo contraddicesse direbbe il falso. Torna l'osservazione del
    livello, non il suo valore: la cifra esce dai dati.
    """
    spec = UNVERIFIED_OBSERVATION.get(code)
    if spec is None or spec["anno"] != level["year_max"] or code not in _unverified():
        return None
    return next((o for o in level["observations"] if o["name"] == spec["territorio"]), None)


def _value_unit(meta):
    from app.indicator_notes import figure_unit

    return figure_unit(meta["name"], meta["unit"])


def _economic_context(view, units):
    """I quattro indicatori economici per i territori agli estremi, e le
    correlazioni di rango con questo indicatore."""
    from app.indicator_view import build_indicator_view

    contexts = []
    for code in CONTEXT_CODES:
        family, raw_id = sources.parse_indicator_code(code)
        context_view = build_indicator_view(family, raw_id)
        level = _level(context_view, "regione")
        if level is None:
            raise LookupError(f"indicatore di contesto {code} senza livello regionale")
        contexts.append((code, context_view["meta"], level))

    base = view["levels"][0]
    by_value = sorted(base["observations"], key=lambda o: (-o["value"], o["name"]))
    picks = by_value[:TOP_N] + [o for o in by_value[-TOP_N:] if o not in by_value[:TOP_N]]
    provincial = base["key"] == "provincia"
    region_of = base.get("region_of") or {}
    unverified = _unverified_observation(_unverified_code(view["meta"]), base)
    from app.profiles import region_key_for

    territories = []
    for obs in picks:
        region = region_of.get(obs["key"]) if provincial else None
        region_key = region_key_for(region) if region else obs["key"]
        entry = {
            "territorio": obs["name"],
            "posizione_per_valore": by_value.index(obs) + 1,
            "valore": figure(obs["value"], units["value"]),
        }
        if provincial:
            entry["regione"] = region
        entry["contesto"] = {
            code: figure(year_values(level, level["year_max"]).get(region_key), _value_unit(meta))
            for code, meta, level in contexts
        }
        if unverified is not None and obs["key"] == unverified["key"]:
            entry[EXTREME_FLAG] = True
        territories.append(entry)

    if provincial:
        correlations = None
        reason = "livello provinciale: i quattro indicatori di contesto sono regionali"
    else:
        correlations = [_correlation(base, code, meta, level) for code, meta, level in contexts]
        reason = None

    return {
        "indicatori": [
            {
                "codice": code,
                "nome": meta["name"],
                "ultimo_anno": level["year_max"],
                "unita": _value_unit(meta),
                "fonte": meta["source_label"],
            }
            for code, meta, level in contexts
        ],
        "livello_dei_valori": "regione" + (", la regione della provincia" if provincial else ""),
        "territori": territories,
        "correlazioni_di_rango": correlations,
        "motivo_senza_correlazioni": reason,
    }


def _correlation(base, code, meta, level):
    """Spearman sull'ultimo anno che le due serie hanno in comune con abbastanza territori."""
    for year in sorted(set(base["years"]) & set(level["years"]), reverse=True):
        mine, theirs = year_values(base, year), year_values(level, year)
        keys = sorted(set(mine) & set(theirs))
        if len(keys) >= MIN_CORRELATION_N:
            rho = rank_correlation([mine[k] for k in keys], [theirs[k] for k in keys])
            return {
                "codice": code,
                "nome": meta["name"],
                "anno": year,
                "territori": count(len(keys)),
                "rho_spearman": coefficient(rho),
            }
    return {"codice": code, "nome": meta["name"], "anno": None, "territori": count(0), "rho_spearman": None}


def dumps(dossier):
    """Il JSON del dossier: stesso dossier, stessi byte."""
    return json.dumps(dossier, ensure_ascii=False, indent=2) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("code", help="codice della scheda: ter-12, 12, bes-06POL012P o bes:06POL012P")
    parser.add_argument("--out", type=Path, help="file JSON da scrivere (senza, stampa su stdout)")
    args = parser.parse_args(argv)
    try:
        dossier = build(args.code)
    except LookupError as error:
        print(f"brief: {error}", file=sys.stderr)
        return 2
    text = dumps(dossier)
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"{args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
