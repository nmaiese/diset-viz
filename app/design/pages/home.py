"""La home della 1.0: le frasi e le cifre che il template chiede in piu' al contesto.

La home di prima mostrava il PIL pro capite tre volte (mappa, storia in
evidenza, confronto). Qui compare una volta sola, nell'indicatore in evidenza,
con la regia della scheda: prima la striscia del divario, poi la mappa che
nomina i suoi estremi accanto alla classifica. Le cifre vengono tutte da
`hero_map`, la media semplice da `series_module`.

Qui non si formatta: il template scrive le cifre con i filtri `num`, `rank` e
`delta` di numfmt, e le poche frasi composte in Python passano da
`common.with_unit`. Un dato che manca toglie la frase o la sezione, mai la
pagina.
"""

from __future__ import annotations

import math
import re
import struct
from functools import lru_cache

from app import quality_life_bes
from app.blog import STATIC_DIR, social_image_size
from app.data import REGION_GEO_AREA
from app.design import charts, numfmt
from app.design.common import (
    LOWER_BETTER,
    MEZZOGIORNO,
    PATHS,
    count_word,
    date_it,
    legend,
    map_classes,
    ranking,
    short_unit,
    the_place,
    with_unit,
)

# Le regioni che non vogliono "in": "nel Lazio", "nelle Marche".
IN_REGION = {"Lazio": "nel Lazio", "Marche": "nelle Marche"}

# Il livello della qualita' della vita come lo chiama la home (quello delle
# URL delle classifiche) e come lo chiama quality_life_bes.
QOL_LEVEL = {"regioni": "regione", "province": "provincia"}


def in_region(name: str) -> str:
    """"in Calabria", "nel Lazio", "nelle Marche"."""
    return IN_REGION.get(name, f"in {name}")


def lower_first(text: str | None) -> str | None:
    """"Assegna lo stesso peso" -> "assegna lo stesso peso", per metterlo dopo i due punti."""
    return text[:1].lower() + text[1:] if text else text


def parse_it(text) -> float | None:
    """`54.636,70` -> 54636.7: le cifre di `hero_map` e delle schede arrivano gia' scritte."""
    if text is None:
        return None
    try:
        value = float(str(text).replace(".", "").replace(",", "."))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def join_names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]


# ---------------------------------------------------------------- l'indicatore in evidenza

def split_claim(observations: list[dict], year) -> str | None:
    """Il Mezzogiorno tutto da una parte del Centro-Nord, se lo e': nella
    striscia si vede come due gruppi di colore che non si toccano."""
    south = [o["value"] for o in observations if o["key"] in MEZZOGIORNO]
    north = [o["value"] for o in observations if o["key"] not in MEZZOGIORNO]
    if not south or not north:
        return None
    if max(south) < min(north):
        return f"Nel {year} nessuna regione del Mezzogiorno arriva al valore più basso del Centro-Nord"
    if min(south) > max(north):
        return f"Nel {year} nessuna regione del Mezzogiorno scende al valore più alto del Centro-Nord"
    return None


def average_claim(observations: list[dict], mean: float | None, year) -> str | None:
    """Chi sta sotto la media semplice, a partire dal Mezzogiorno: si legge nella
    classifica, dove la riga della media divide le regioni."""
    if mean is None:
        return None
    south = [o for o in observations if o["key"] in MEZZOGIORNO]
    if not south:
        return None
    below = [o for o in observations if o["value"] < mean]
    south_below = [o for o in below if o["key"] in MEZZOGIORNO]
    others = [o for o in below if o["key"] not in MEZZOGIORNO]
    words = count_word(len(south))
    if len(south_below) == len(south):
        if not others:
            return f"Nel {year} sotto la media semplice stanno tutte e sole le {words} regioni del Mezzogiorno"
        if len(others) <= 3:
            names = join_names([the_place(o["name"], "regione") for o in others])
            # L'anno sta nella riga sotto il titolo: qui resta fuori, per stare nei 90 caratteri.
            return f"Sotto la media semplice stanno le {words} regioni del Mezzogiorno, più {names}"
        return f"Nel {year} tutte le {words} regioni del Mezzogiorno stanno sotto la media semplice"
    if not south_below:
        return f"Nel {year} tutte le {words} regioni del Mezzogiorno stanno sopra la media semplice"
    return (f"Nel {year} {count_word(len(south_below))} regioni del Mezzogiorno su {words} "
            f"stanno sotto la media semplice")


def extremes_claim(high: dict, low: dict, unit: str | None, year) -> str:
    return (f"Nel {year} si va da {with_unit(low['value'], unit)} {in_region(low['name'])} "
            f"a {with_unit(high['value'], unit)} {in_region(high['name'])}")


def simple_mean(hero: dict, series: dict, computed: float | None) -> float | None:
    """La media semplice che l'app calcola per la serie del confronto, se e'
    lo stesso indicatore e il suo ultimo anno e' l'anno della mappa. Deve
    coincidere con la media delle cifre della mappa (che arrivano arrotondate
    al centesimo): se non coincide, vale quella della mappa, perche' e' la
    media delle cifre che la pagina mostra."""
    reference = series.get("reference") or {}
    years = series.get("years") or []
    values = reference.get("series") or []
    if (computed is None or not years or not values or years[-1] != hero.get("year")
            or series.get("indicator_path") != hero.get("indicator_path") or values[-1] is None):
        return computed
    mean = values[-1]
    return mean if abs(mean - computed) <= max(0.01, abs(computed) * 1e-4) else computed


def feature(ctx: dict) -> dict | None:
    """L'indicatore in evidenza: striscia del divario, mappa con i due estremi, classifica."""
    hero = ctx["hero_map"]
    unit = hero.get("unit")
    year = hero.get("year")
    plural = "regioni"
    areas = charts.area_map()

    observations = []
    for key, row in (hero.get("readout") or {}).items():
        value = parse_it(row.get("value"))
        if value is not None:
            observations.append({"key": key, "name": row["name"], "value": value})
    if len(observations) < 2 or year is None:
        return None
    observations.sort(key=lambda o: o["value"], reverse=True)
    n = len(observations)
    values = [o["value"] for o in observations]
    mean = simple_mean(hero, ctx.get("series_module") or {}, sum(values) / n)

    level = {"observations": observations, "stats": {"year_avg": mean}, "plural": plural}
    rows = ranking(level, unit)
    high, low = observations[0], observations[-1]
    ratio = high["value"] / low["value"] if low["value"] > 0 else None

    # Due titoli, uno per grafico, mai la stessa frase: la striscia dice come
    # stanno le ripartizioni, la classifica chi sta sotto la media.
    split = split_claim(observations, year)
    avg_claim = average_claim(observations, mean, year)
    lead_claim = split or avg_claim or extremes_claim(high, low, unit, year)
    table_claim = avg_claim if split else extremes_claim(high, low, unit, year)
    if table_claim == lead_claim:
        table_claim = None

    strip = charts.divario_strip([{**o, "area": areas.get(o["key"])} for o in observations], mean, unit, ratio)
    callouts = charts.map_callouts(PATHS, [(high["key"], high["name"], with_unit(high["value"], unit)),
                                           (low["key"], low["name"], with_unit(low["value"], unit))])
    direction = hero.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso",
             "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")
    names = {o["key"]: o["name"] for o in observations}
    decimals = numfmt.column_decimals(values)
    region_areas = {o["key"]: areas.get(o["key"]) for o in observations}
    options = hero.get("options") or []
    return {
        "name": hero["indicator_name"], "path": hero["indicator_path"], "year": year, "n": n,
        "unit": unit, "short_unit": short_unit(unit), "source_label": hero.get("source_label"),
        "lead_claim": lead_claim, "table_claim": table_claim, "verso": verso,
        "lower_better": direction in LOWER_BETTER,
        "options": [{"id": o["id"], "name": o["name"], "on": o["id"] == hero.get("selected_id")} for o in options],
        "rows": rows, "decimals": decimals, "areas": region_areas, "area_label": charts.AREA_LABEL,
        "strip": strip, "callouts": callouts,
        "map_classes": map_classes({"map_colors": hero.get("colors") or {}}),
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in observations},
        "names": names,
        "legend": legend(values, unit),
        # Lo stesso contratto del modulo della scheda, con un anno solo: basta
        # perche' v1.js accenda "Trova la tua regione", il clic sulla mappa e
        # il punto della striscia.
        "explore_js": {
            "years": [year], "matrix": {str(year): {o["key"]: o["value"] for o in observations}},
            "names": names, "unit": short_unit(unit), "direction": direction,
            "plural": plural, "profile": "/regione/", "south": sorted(MEZZOGIORNO),
            "decimals": decimals, "areas": region_areas,
        },
    }


# ---------------------------------------------------------------- regioni per ripartizione

def regions_by_area(names: dict[str, str]) -> list[dict]:
    """Le regioni nelle tre ripartizioni della striscia (Nord, Centro,
    Mezzogiorno), nell'ordine Istat, con il loro colore."""
    areas = charts.area_map()
    groups = {a: [] for a in ("nord", "centro", "sud")}
    for key in REGION_GEO_AREA:
        if key in names and areas.get(key) in groups:
            groups[areas[key]].append({"key": key, "name": names[key]})
    # Una ripartizione con piu' di quattro regioni prende due colonne, cosi' il
    # Nord (otto regioni) non fa una colonna lunga il doppio delle altre.
    return [{"area": a, "label": charts.AREA_LABEL[a], "regions": regions, "wide": len(regions) > 4}
            for a, regions in groups.items() if regions]


# ---------------------------------------------------------------- qualita' della vita

def live_ranking(level_key: str, profile: dict, slug: str) -> list[dict] | None:
    """La classifica intera di un profilo, dalla stessa funzione che serve le
    pagine delle classifiche (`quality_life_bes.build_bes_ranking`, gia' in
    cache per processo con `cache.memoize`).

    Il modulo della home porta i punteggi arrotondati all'intero: scritti col
    ruolo "punteggio" (un decimale) direbbero 72,0 dove il dato e' 71,6. Qui ci
    sono i valori veri, e si accettano solo se le righe coincidono con quelle
    del modulo: se non coincidono il podio si toglie."""
    payload = quality_life_bes.build_bes_ranking(QOL_LEVEL[level_key], slug)
    rows = (payload or {}).get("ranking") or []
    if len(rows) < 6:
        return None
    by_rank = {r["rank"]: r for r in rows}
    for r in profile.get("top", []) + profile.get("bottom", []):
        twin = by_rank.get(r["rank"])
        if not twin or not r["path"].endswith("/" + twin["key"]) or abs(twin["score"] - r["score"]) > 0.5:
            return None
    return rows


def podium(level: dict, level_key: str, slug: str, unit_word: str, singular: str) -> dict | None:
    """Le prime tre e le ultime tre di un profilo, con quante ne restano in mezzo."""
    profile = next((p for p in level.get("profiles") or [] if p["slug"] == slug), None)
    if profile is None:
        return None
    precise = live_ranking(level_key, profile, slug)
    if precise is None:
        return None

    def row(r):
        return {"rank": r["rank"], "name": r["name"], "path": f"/{QOL_LEVEL[level_key]}/{r['key']}",
                "score": r["score"], "where": r.get("region") or None, "width": max(0, min(100, r["score"]))}

    top = [row(r) for r in precise[:3]]
    bottom = [row(r) for r in precise[-3:]]
    total = len(precise)
    middle = total - len(top) - len(bottom)
    gap = precise[0]["score"] - precise[-1]["score"]
    if profile.get("gap") is not None and abs(gap - profile["gap"]) > 1:
        return None
    return {
        "label": level["label"], "classifica": level["classifica"], "cta": level["cta"],
        "profile": profile["name"], "total": total, "unit_word": unit_word, "singular": singular,
        "top": top, "bottom": bottom, "gap": gap,
        "middle": middle if middle > 0 else None,
        "middle_from": top[-1]["rank"] + 1,
        "middle_to": bottom[0]["rank"] - 1,
    }


def quality(ctx: dict) -> dict | None:
    qol = ctx.get("qol_module")
    if not qol:
        return None
    slug = qol.get("default_slug")
    levels = qol.get("levels") or {}
    regions = podium(levels["regioni"], "regioni", slug, "regioni", "Regione") if "regioni" in levels else None
    provinces = podium(levels["province"], "province", slug, "province", "Provincia") if "province" in levels else None
    if not regions and not provinces:
        return None
    default = next((p for p in qol.get("profiles") or [] if p["slug"] == slug), None)
    others = [{"name": p["name"], "slug": p["slug"]} for p in qol.get("profiles") or [] if p["slug"] != slug]
    return {"regions": regions, "provinces": provinces, "others": others,
            "has_gaps": bool(regions and provinces),
            "profile": default["name"] if default else None,
            "profile_text": lower_first(default.get("description")) if default else None}


# ---------------------------------------------------------------- quiz

def quiz_try(ctx: dict) -> dict | None:
    """Una domanda di "Chi è maggiore?" fatta con una lettura in evidenza del
    contesto: due regioni, un indicatore, quale ha il valore piu' alto."""
    game = next((g for g in ctx.get("quiz_games") or [] if g["href"].endswith("chi-e-maggiore")), None)
    card = next((c for c in ctx.get("insight_cards") or []
                 if c.get("path") != (ctx.get("hero_map") or {}).get("indicator_path")), None)
    if not game or not card:
        return None
    a = {"name": card["lead_region"], "value": parse_it(card.get("lead_value"))}
    b = {"name": card["lag_region"], "value": parse_it(card.get("lag_value"))}
    if a["value"] is None or b["value"] is None or math.isclose(a["value"], b["value"]):
        return None
    # Le cifre si scrivono coi decimali della grandezza, come nelle tessere
    # della scheda. Se scritte cosi' coincidono, la domanda non ha risposta.
    if numfmt.text(a["value"]) == numfmt.text(b["value"]):
        return None
    right, wrong = (a, b) if a["value"] > b["value"] else (b, a)
    options = sorted([a, b], key=lambda o: o["name"])
    return {
        "game": game, "indicator": card["name"], "path": card["path"], "year": card["year"],
        "source_label": card.get("source_label"), "unit": card.get("unit"),
        "options": [{"name": o["name"], "right": o is right} for o in options],
        "right": right, "wrong": wrong,
    }


# ---------------------------------------------------------------- storie

def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    """Larghezza e altezza dal segmento SOF di un JPEG, senza librerie."""
    i = 2
    while i + 9 <= len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        (length,) = struct.unpack(">H", data[i + 2:i + 4])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return (width, height) if width and height else None
        i += 2 + length
    return None


@lru_cache(maxsize=128)
def image_size(src: str | None) -> tuple[int, int] | None:
    """(larghezza, altezza) di una copertina, o None se non si sa: allora il
    template non dichiara misure. Non tutte le copertine sono 1200x630 come
    quelle disegnate (alcune foto sono 1376x768), e una misura sbagliata
    storce il riquadro prima che l'immagine arrivi."""
    if not src or not src.startswith("/static/"):
        return None
    if src.endswith(".png"):
        return social_image_size(src)
    path = STATIC_DIR / src.removeprefix("/static/")
    try:
        head = path.read_bytes()
    except OSError:
        return None
    if src.endswith((".jpg", ".jpeg")) and head[:2] == b"\xff\xd8":
        return _jpeg_size(head)
    if src.endswith(".svg"):
        m = re.search(rb'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"', head)
        if m:
            return round(float(m.group(1))), round(float(m.group(2)))
    return None


def story(p: dict) -> dict:
    credit = p.get("cover_credit") or {}
    return {
        "slug": p["slug"], "title": p["title"], "description": p.get("description"),
        "date": p.get("date"), "date_label": date_it(p.get("date")), "cover": p.get("cover"),
        "size": image_size(p.get("cover")),
        "cover_alt": p.get("cover_alt") or "", "caption": p.get("cover_caption"),
        "credit": {"author": credit.get("author"), "source": credit.get("source_name"), "source_url": credit.get("source_url"),
                   "license": credit.get("license"), "license_url": credit.get("license_url")} if credit.get("author") else None,
        "tag": (p.get("tags") or [None])[0], "read_time": p.get("read_time"),
    }


# ---------------------------------------------------------------- tutta la pagina

def derive(ctx: dict) -> dict:
    """Tutto cio' che il template della home chiede in piu' rispetto al contesto."""
    counts = ctx.get("territories") or {}
    feat = feature(ctx) if ctx.get("hero_map") else None
    posts = sorted(ctx.get("posts") or [], key=lambda p: p["slug"])
    posts = sorted(posts, key=lambda p: str(p.get("date") or ""), reverse=True)[:3]
    names = (feat or {}).get("names", {})
    areas = [{
        **area,
        "best_key": next((k for k, v in names.items() if v == area.get("best")), None),
        "worst_key": next((k for k, v in names.items() if v == area.get("worst")), None),
    } for area in ctx.get("themes_preview") or []]
    citation = (f"Divario Italia, «I numeri delle regioni e delle province italiane», elaborazione su dati "
                f"{ctx.get('sources_label')}. {ctx.get('canonical')}")
    return {
        "indicators": ctx.get("total_indicators"),
        "regions": counts.get("regions"), "provinces": counts.get("provinces"),
        "feature": feat,
        "areas_regions": regions_by_area(feat["names"]) if feat else [],
        "quality": quality(ctx),
        "quiz_try": quiz_try(ctx),
        "areas": areas,
        "stories": [story(p) for p in posts],
        "citation": citation,
        "games_word": count_word(len(ctx.get("quiz_games") or []), feminine=False).capitalize(),
        # Le schede di fiducia di prima, per chiave. "Copertura" ripete la
        # definizione in testa alla pagina, quindi il template ne usa solo il testo.
        "trust": {card["kicker"]: card for card in ctx.get("trust_cards") or []},
    }
