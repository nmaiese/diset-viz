"""La pagina regione della 1.0: cifre e frasi composte dal profilo vero.

Il contesto della rotta /regione/<key> porta il profilo della regione (posizione
media, temi, indicatori, movimenti, regioni simili) e le sue province. Non porta
la qualita' della vita della regione ne' il numero delle province italiane: per
mostrarli si leggono dal contesto catturato, nello stesso momento, delle pagine
della qualita' della vita. Se quel contesto manca, la tessera e il denominatore
spariscono invece di diventare cifre inventate. Nella 1.0 la rotta della regione
dovra' portarli da se'.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import derive as common

from app.data import REGION_GEO_AREA, REGION_ORDER
from app.indicator_notes import is_percentage_unit
from app.profiles import MIN_THEME_INDICATORS, region_key_for
from app.seo_titles import of_region
from app.taxonomy import CATEGORY_NAME_TO_SLUG, MACRO_AREAS

V1 = Path(__file__).resolve().parents[2]
DATA = V1 / "data"
PATHS = V1 / "src" / "partials" / "italy_paths.json"

DIRECTION_WORDS = {
    "higher_better": "meglio se alto",
    "lower_better": "meglio se basso",
    "higher_worse": "meglio se basso",
}


def _sibling(name: str) -> dict:
    """Il contesto catturato di un'altra pagina del prototipo, o {} se non e' stato catturato.

    Solo il file assente e' un caso previsto: un JSON rotto e' un errore e si alza.
    """
    path = DATA / f"{name}.context.json"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    return json.loads(text).get("context") or {}


def _scale(methodology: dict) -> dict | None:
    """Minimo, massimo e centro della scala del punteggio, letti dal metodo.

    La classifica dichiara la scala in una frase ("display 0-100 con media 50"):
    la si legge da li' invece di riscriverla, cosi' se cambia cambia anche qui.
    """
    m = re.search(r"(\d+)-(\d+) con media (\d+)", (methodology or {}).get("normalization") or "")
    if not m:
        return None
    lo, hi, mid = (int(x) for x in m.groups())
    return {"min": lo, "max": hi, "mid": mid}


def _unit(unit: str | None) -> str:
    """L'unita' come va nella colonna: la percentuale diventa %, il resto resta
    com'e' nella fonte."""
    unit = (unit or "").strip()
    return "%" if unit and is_percentage_unit(unit) else unit


def _value_with_unit(value, unit: str | None) -> str:
    """`60,2%`, `24.328 euro`, `0,32 indice (0-1)`: la cifra isolata porta la sua unita'."""
    text = common.num(value)
    u = _unit(unit)
    if u == "%":
        return f"{text}%"
    return f"{text} {u}" if u else text


def _article(name: str, prep: str = "") -> str:
    """"la Puglia", "alla Puglia", "il Veneto", "all'Umbria", "le Marche".

    Parte da `of_region`, che sa gia' il genere e il numero di ogni regione, e
    cambia solo la preposizione articolata: "della" diventa "la" o "alla".
    """
    of = of_region(name)
    m = re.match(r"(della |del |dell'|delle )(.*)", of)
    if not m:
        return name
    article = {"della ": "la ", "del ": "il ", "dell'": "l'", "delle ": "le "}[m.group(1)]
    if prep == "a":
        article = {"la ": "alla ", "il ": "al ", "l'": "all'", "le ": "alle "}[article]
    return article + m.group(2)


def _lower_first(text: str) -> str:
    """L'iniziale minuscola per un nome dentro la frase, ma non in una sigla: "PIL" resta."""
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        return text[0].lower() + text[1:]
    return text


def _position(rank, total) -> str | None:
    return f"{common.ordinal(rank)} su {total}" if rank is not None and total else None


def _theme_order() -> dict[str, int]:
    """L'ordine dei temi della tassonomia, macro-area per macro-area."""
    slugs = [slug for area in MACRO_AREAS.values() for slug in area]
    return {name: slugs.index(slug) for name, slug in CATEGORY_NAME_TO_SLUG.items() if slug in slugs}


def _indicator_row(ind: dict, region_total: int) -> dict:
    rank, count = ind.get("rank"), ind.get("region_count")
    movement = ind.get("movement")
    before = None
    if rank is not None and movement is not None and ind.get("year_from"):
        # L'anno di confronto e' per costruzione uno con i dati di tutte le
        # regioni (`_core_stats`): il suo denominatore e' il totale, anche
        # quando l'ultimo anno ne copre meno.
        before = {"rank": rank + movement, "ordinal": common.ordinal(rank + movement),
                  "position": _position(rank + movement, region_total),
                  "year": ind["year_from"], "same": movement == 0}
    return {
        "id": ind["id"], "name": ind["name"], "path": ind["path"], "theme": ind["theme"],
        "value": common.num(ind.get("value")), "value_unit": _value_with_unit(ind.get("value"), ind.get("unit")),
        "unit": _unit(ind.get("unit")), "year": ind.get("year"),
        "rank": rank, "count": count, "position": _position(rank, count),
        "partial": count is not None and count != region_total,
        "movement": movement, "before": before,
        "verso": DIRECTION_WORDS.get(ind.get("direction")),
    }


def _answer(profile: dict) -> dict:
    """La frase-risposta: il tema dove sta piu' in alto e quello dove sta piu'
    in basso fra le regioni, con la posizione.

    La frase stampa posizioni, quindi sceglie per posizione: se scegliesse per
    percentile medio (l'ordine di `themes_weak`) potrebbe dire "peggio in
    Lavoro, 17ª" accanto a una tabella con un tema 19ª. A parita' di posizione
    decide il percentile. `netto` del primo tema per percentile dice se
    qualcosa sta davvero sopra la meta' classifica: e' un fatto su tutti i
    temi, quindi resta vero qualunque tema la frase nomini.
    """
    total = profile.get("region_total")
    rated = [t for t in profile.get("theme_table") or [] if t.get("rank")]
    strong = min(rated, key=lambda t: (t["rank"], -t["score"]), default=None)
    weak = max(rated, key=lambda t: (t["rank"], -t["score"]), default=None)
    top = (profile.get("themes_strong") or [{}])[0]
    out = {"strong": None, "weak": None, "netto": bool(top.get("netto"))}
    if strong:
        out["strong"] = {"theme": strong["theme"], "path": strong["theme_path"],
                         "position": _position(strong["rank"], strong.get("rank_total") or total)}
    if weak and weak is not strong:
        out["weak"] = {"theme": weak["theme"], "path": weak["theme_path"],
                       "position": _position(weak["rank"], weak.get("rank_total") or total)}
    return out


def _quality(key: str, classifica: dict) -> dict | None:
    """La riga della regione nella classifica della qualita' della vita, se c'e'."""
    data = classifica.get("data") or {}
    ranking = data.get("ranking") or []
    row = next((r for r in ranking if r.get("key") == key), None)
    if not row or row.get("score") is None:
        return None
    scale = _scale(data.get("methodology"))
    width = round(row["score"] / scale["max"] * 100, 1) if scale else None
    return {
        "rank": row.get("rank"), "ordinal": common.ordinal(row["rank"]) if row.get("rank") else None,
        "total": len(ranking), "score": common.num(row["score"]), "width": width, "scale": scale,
        "profile": ((data.get("profile") or {}).get("name") or "").lower() or None,
        "dimensions": len(data.get("categories") or []) or None,
        "path": "/qualita-della-vita/classifica/regioni",
    }


def derive(ctx: dict) -> dict:
    p = ctx["profile"]
    key, name = p["region_key"], p["region"]
    total = p.get("region_total")
    indicators = p.get("all_indicators") or []
    by_id = {i["id"]: i for i in indicators}

    classifica = _sibling("classifica")
    qdv = _sibling("qualita-della-vita")
    province_rows = (_sibling("classifica-province").get("data") or {}).get("ranking") or []
    province_total = qdv.get("province_total") or len(province_rows) or None
    quality = _quality(key, classifica)
    qranks = {r["key"]: r for r in (classifica.get("data") or {}).get("ranking") or []}
    pdata = _sibling("classifica-province").get("data") or {}
    pscale = _scale(pdata.get("methodology"))

    years = sorted({i["year"] for i in indicators if i.get("year")})
    sources = []
    for i in indicators:
        label = i.get("source_label")
        if label and label not in [s["label"] for s in sources]:
            sources.append({"label": label, "url": i.get("source_url"),
                            "count": sum(1 for j in indicators if j.get("source_label") == label)})
    sources.sort(key=lambda s: -s["count"])

    # I temi nell'ordine del profilo, che e' anche l'ordine dell'ItemList: per
    # percentile medio. La posizione fra le regioni la dice la traccia accanto.
    themes = []
    for t in p.get("theme_table") or []:
        rank, n = t.get("rank"), t.get("rank_total") or total
        themes.append({
            "theme": t["theme"], "path": t["theme_path"], "count": t["count"], "rated": t.get("rated"),
            "rank": rank, "position": _position(rank, n),
            "track": round((rank - 1) / (n - 1) * 100, 1) if rank and n and n > 1 else None,
            "percentile": common.num(round(t["score"] * 100, 1)) if t.get("score") is not None else None,
        })

    # Dove stacca e dove resta indietro: gli indicatori del profilo con i
    # valori veri, presi dalla tabella completa per id.
    def picks(items):
        return [_indicator_row(by_id[e["id"]], total) for e in items if e["id"] in by_id]

    excels, lags = picks(p.get("top_excels") or []), picks(p.get("top_lags") or [])

    gains = [_indicator_row(i, total) for i in (p.get("movement_gains") or [])[:4]]
    losses = [_indicator_row(i, total) for i in (p.get("movement_losses") or [])[:4]]
    moved_up = sum(1 for i in indicators if (i.get("movement") or 0) > 0)
    moved_down = sum(1 for i in indicators if (i.get("movement") or 0) < 0)
    moved_same = sum(1 for i in indicators if i.get("movement") == 0)

    # Le province per qualita' della vita, dalla prima all'ultima.
    provinces = []
    for pr in sorted(ctx.get("provinces") or [], key=lambda r: (r.get("rank") is None, r.get("rank") or 0)):
        width = round(pr["score"] / pscale["max"] * 100, 1) if pscale and pr.get("score") is not None else None
        provinces.append({**pr, "position": _position(pr.get("rank"), province_total) if province_total else None,
                          "ordinal": common.ordinal(pr["rank"]) if pr.get("rank") else None,
                          "score_text": common.num(pr.get("score")), "width": width})

    # Tutti gli indicatori per macro-area, e dentro per tema nell'ordine della
    # tassonomia. Dentro il tema, dalla posizione migliore alla peggiore.
    order = _theme_order()
    areas = []
    area_names = list(MACRO_AREAS) + sorted({i["macro_area"] for i in indicators} - set(MACRO_AREAS))
    theme_paths = {t["theme"]: t["theme_path"] for t in p.get("theme_table") or []}
    for area in area_names:
        rows = [i for i in indicators if i["macro_area"] == area]
        if not rows:
            continue
        groups = []
        for theme in sorted({i["theme"] for i in rows}, key=lambda t: (order.get(t, 99), t)):
            items = sorted((i for i in rows if i["theme"] == theme),
                           key=lambda i: (i.get("rank") is None, i.get("rank") or 0, i["name"]))
            groups.append({"theme": theme, "path": theme_paths.get(theme),
                           "rows": [_indicator_row(i, total) for i in items]})
        areas.append({"name": area, "slug": re.sub(r"[^a-z]+", "-", area.lower()).strip("-"),
                      "count": len(rows), "groups": groups})

    # Il localizzatore: tutte le regioni della mappa nel grigio di contesto,
    # solo questa nel colore dell'elemento in evidenza. Le chiavi vengono dai
    # tracciati stessi, cosi' nessuna regione cade nel tratteggio del dato mancante.
    names = {region_key_for(r): r for r in REGION_ORDER}
    map_keys = list(json.loads(PATHS.read_text(encoding="utf-8")))
    locator = {k: ("regione-loc__on" if k == key else "regione-loc__ctx") for k in map_keys}

    similar = []
    for s in p.get("similar_regions") or []:
        q = qranks.get(s["region_key"])
        similar.append({"name": s["region"], "key": s["region_key"], "area": REGION_GEO_AREA.get(s["region_key"]),
                        "path": f"/regione/{s['region_key']}",
                        "quality": _position(q.get("rank"), len(qranks)) if q and q.get("rank") else None})

    institutions = list(dict.fromkeys(s["label"].split(",")[0].strip() for s in sources))
    institution = " e ".join(institutions) if institutions else None
    year_min, year_max = (years[0], years[-1]) if years else (None, None)
    span = f" ({year_min}-{year_max})" if year_min and year_max and year_min != year_max else (f" ({year_max})" if year_max else "")
    citation = (f"Divario Italia, «Il profilo {of_region(name)}», elaborazione su dati {institution or ''}"
                f"{span}. {ctx.get('canonical')}")

    best = excels[0] if excels else None
    best_pick = {**best, "name_lc": _lower_first(best["name"])} if best and best.get("position") else None

    area = p.get("geo_area")
    return {
        "name": name, "key": key, "area": area, "total": total,
        "area_in": ("nelle " if area == "Isole" else "nel ") + area if area else None,
        "the_name": _article(name), "to_name": _article(name, "a"), "of_name": of_region(name),
        "institution": institution,
        "avg_rank": p.get("avg_rank"), "avg_ordinal": common.ordinal(p["avg_rank"]) if p.get("avg_rank") else None,
        "comparable": p.get("comparable_count"), "top5": p.get("top5_count"), "scored": p.get("scored_count"),
        "indicator_count": len(indicators), "contextual_count": sum(1 for i in indicators if i.get("rank") is None),
        "year_min": year_min, "year_max": year_max, "sources": sources,
        "answer": _answer(p), "best_pick": best_pick, "quality": quality, "themes": themes,
        "track_first": common.ordinal(1) if total else None, "track_last": common.ordinal(total) if total else None,
        "excels": excels, "lags": lags,
        "gains": gains, "losses": losses, "moved_up": moved_up, "moved_down": moved_down, "moved_same": moved_same,
        "provinces": provinces, "province_total": province_total,
        "province_profile": ((pdata.get("profile") or {}).get("name") or "").lower() or None,
        "province_scale": pscale,
        "areas": areas, "names": names, "locator": locator, "similar": similar,
        "map_values": {k: REGION_GEO_AREA.get(k, "") for k in map_keys},
        "min_theme": MIN_THEME_INDICATORS, "citation": citation,
        "count_word": common.count_word, "ordinal": common.ordinal,
    }
