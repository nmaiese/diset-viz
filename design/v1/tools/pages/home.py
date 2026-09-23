"""Le frasi e le cifre della home 1.0, composte dal contesto catturato.

La home di oggi mostra il PIL pro capite tre volte (mappa, storia in evidenza,
confronto). Qui compare una volta sola, nel modulo dato: la frase, la mappa e la
classifica vengono tutte da `hero_map`, la media semplice da `series_module`.
Ogni altra cifra (conteggi, punteggi della qualita' della vita, domanda del
quiz) arriva dal contesto e passa dagli aiuti di `derive.py`, cosi' si scrive
in un modo solo.
"""

from __future__ import annotations

import math

import derive as common

from app import it_numbers
from app.data import REGION_GEO_AREA

# Le regioni che non vogliono "in": "nel Lazio", "nelle Marche".
IN_REGION = {"Lazio": "nel Lazio", "Marche": "nelle Marche"}
AREA_ORDER = ("Nord", "Centro", "Sud", "Isole")


def in_region(name: str) -> str:
    """"in Calabria", "nel Lazio", "nelle Marche"."""
    return IN_REGION.get(name, f"in {name}")


def integer(value) -> str:
    """Conteggi e punteggi interi: `72`, non `72,0`. format_number darebbe un
    decimale a ogni numero sotto 100, che su un punteggio intero e' rumore."""
    return it_numbers.number(value, 0) if value is not None else common.PLACEHOLDER


def lower_first(text: str | None) -> str | None:
    """"Assegna lo stesso peso" -> "assegna lo stesso peso", per metterlo dopo i due punti."""
    return text[:1].lower() + text[1:] if text else text


def parse_it(text: str | None) -> float | None:
    """`54.636,70` -> 54636.7: le cifre del contesto arrivano gia' formattate."""
    if text is None:
        return None
    try:
        return float(str(text).replace(".", "").replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------------------- il dato in evidenza

def feature(ctx: dict) -> dict:
    """Il modulo dato della home: frase, mappa, classifica dallo zero, legenda."""
    hero = ctx["hero_map"]
    series = ctx.get("series_module") or {}
    unit = hero.get("unit")
    year = hero["year"]
    plural = "regioni"

    observations = []
    for key, row in (hero.get("readout") or {}).items():
        value = parse_it(row.get("value"))
        if value is not None:
            observations.append({"key": key, "name": row["name"], "value": value})
    observations.sort(key=lambda o: o["value"], reverse=True)
    n = len(observations)
    values = [o["value"] for o in observations]

    # La media semplice e' quella che l'app calcola per la serie del confronto,
    # se l'ultimo anno della serie e' l'anno della mappa. Deve coincidere con la
    # media delle cifre della mappa: se non coincide, uno dei due dati e' sbagliato.
    computed = sum(values) / n if n else None
    mean = computed
    reference = series.get("reference") or {}
    years = series.get("years") or []
    if years and years[-1] == year and reference.get("series") and series.get("indicator_path") == hero.get("indicator_path"):
        mean = reference["series"][-1]
        if computed is not None and abs(mean - computed) > max(0.01, abs(computed) * 1e-4):
            raise ValueError(f"media semplice della serie {mean} diversa da quella della mappa {computed}")

    level = {"observations": observations, "stats": {"year_avg": mean}, "plural": plural}
    rows = common.ranking(level, unit)

    high, low = (observations[0], observations[-1]) if observations else (None, None)
    ratio = None
    if high and low and low["value"] > 0:
        ratio = common.ratio_text(high["value"] / low["value"])
    claim = None
    if high and low:
        claim = (f"Nel {year} si va da {common.with_unit(low['value'], unit)} {in_region(low['name'])} "
                 f"a {common.with_unit(high['value'], unit)} {in_region(high['name'])}")
        claim += f", {ratio} volte tanto" if ratio else ""

    # La nota sotto la classifica: un fatto verificato sul Mezzogiorno, che la
    # frase in testa non dice.
    note = None
    if mean is not None:
        south = [o for o in observations if o["key"] in common.MEZZOGIORNO]
        below = [o for o in south if o["value"] < mean]
        words = common.count_word(len(south))
        if south and len(below) == len(south):
            note = f"Tutte le {words} regioni del Mezzogiorno stanno sotto la media semplice delle {n} regioni."
        elif south and not below:
            note = f"Tutte le {words} regioni del Mezzogiorno stanno sopra la media semplice delle {n} regioni."
        elif south:
            note = (f"{common.count_word(len(below)).capitalize()} regioni del Mezzogiorno su {words} "
                    f"stanno sotto la media semplice delle {n} regioni.")

    direction = hero.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso",
             "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")
    names = {o["key"]: o["name"] for o in observations}
    return {
        "name": hero["indicator_name"], "path": hero["indicator_path"], "year": year, "n": n,
        "unit": unit, "short_unit": common.short_unit(unit), "source_label": hero.get("source_label"),
        "claim": claim, "note": note, "verso": verso,
        "lower_better": direction in common.LOWER_BETTER,
        "options": [{"id": o["id"], "name": o["name"], "on": o["id"] == hero.get("selected_id")}
                    for o in hero.get("options") or []],
        "rows": rows, "map_classes": common.map_classes({"map_colors": hero.get("colors") or {}}),
        "map_values": {o["key"]: common.with_unit(o["value"], unit) for o in observations},
        "names": names,
        "legend": common.legend(values, unit) if values else None,
        # Lo stesso contratto del modulo della scheda, con un anno solo: basta
        # perche' proto.js accenda "Trova la tua regione" e il clic sulla mappa.
        "explore_js": {
            "years": [year], "matrix": {str(year): {o["key"]: o["value"] for o in observations}},
            "names": names, "unit": common.short_unit(unit), "direction": direction,
            "plural": plural, "profile": "/regione/", "south": sorted(common.MEZZOGIORNO),
        },
    }


# ---------------------------------------------------------------- regioni per ripartizione

def regions_by_area(names: dict[str, str]) -> list[dict]:
    """Le regioni nelle ripartizioni dell'app, nell'ordine Istat di REGION_GEO_AREA."""
    groups = {area: [] for area in AREA_ORDER}
    for key, area in REGION_GEO_AREA.items():
        if key in names:
            groups.setdefault(area, []).append({"key": key, "name": names[key]})
    # Una ripartizione con piu' di quattro regioni prende due colonne, cosi' il
    # Nord (otto regioni) non fa una colonna lunga il doppio delle altre.
    return [{"area": area, "regions": regions, "wide": len(regions) > 4}
            for area, regions in groups.items() if regions]


# ---------------------------------------------------------------- qualita' della vita

def podium(level: dict, slug: str, total: int, unit_word: str, singular: str) -> dict | None:
    """Le prime tre e le ultime tre di un profilo, con quante ne restano in mezzo."""
    profile = next((p for p in level.get("profiles") or [] if p["slug"] == slug), None)
    if profile is None:
        return None

    def row(r):
        return {"rank": common.ordinal(r["rank"]), "name": r["name"], "path": r["path"],
                "score": integer(r["score"]), "width": max(0, min(100, r["score"]))}

    top = [row(r) for r in profile["top"]]
    bottom = sorted(profile["bottom"], key=lambda r: r["rank"])
    middle = total - len(profile["top"]) - len(bottom)
    return {
        "label": level["label"], "classifica": level["classifica"], "cta": level["cta"],
        "profile": profile["name"], "total": total, "unit_word": unit_word, "singular": singular,
        "top": top, "bottom": [row(r) for r in bottom],
        "middle": f"Altre {middle} {unit_word}" if middle > 0 else None,
        "gap": profile.get("gap"),
    }


def quality(ctx: dict) -> dict | None:
    qol = ctx.get("qol_module")
    if not qol:
        return None
    slug = qol.get("default_slug")
    counts = ctx.get("territories") or {}
    levels = qol.get("levels") or {}
    regions = podium(levels["regioni"], slug, counts["regions"], "regioni", "Regione") if "regioni" in levels else None
    provinces = podium(levels["province"], slug, counts["provinces"], "province", "Provincia") if "province" in levels else None
    default = next((p for p in qol.get("profiles") or [] if p["slug"] == slug), None)
    sentence = None
    if default and regions and provinces and regions["gap"] is not None and provinces["gap"] is not None:
        sentence = (f"Con il profilo {default['name'].lower()}, fra la prima e l'ultima regione ci sono "
                    f"{integer(regions['gap'])} punti sulla scala da 0 a 100, fra la prima e l'ultima provincia "
                    f"{integer(provinces['gap'])}.")
    others = [{"name": p["name"], "slug": p["slug"]} for p in qol.get("profiles") or [] if p["slug"] != slug]
    return {"regions": regions, "provinces": provinces, "sentence": sentence, "others": others,
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
    a = {"name": card["lead_region"], "value": parse_it(card["lead_value"])}
    b = {"name": card["lag_region"], "value": parse_it(card["lag_value"])}
    if a["value"] is None or b["value"] is None or math.isclose(a["value"], b["value"]):
        return None
    right, wrong = (a, b) if a["value"] > b["value"] else (b, a)
    options = sorted([a, b], key=lambda o: o["name"])
    unit = card.get("unit")
    return {
        "game": game, "indicator": card["name"], "path": card["path"], "year": card["year"],
        "source_label": card.get("source_label"),
        "options": [{"name": o["name"], "right": o is right} for o in options],
        "answer": (f"{right['name']} {common.with_unit(right['value'], unit)}, "
                   f"{wrong['name']} {common.with_unit(wrong['value'], unit)}."),
    }


# ---------------------------------------------------------------- tutta la pagina

def derive(ctx: dict) -> dict:
    """Tutto cio' che il template della home chiede in piu' rispetto al contesto."""
    counts = ctx.get("territories") or {}
    feat = feature(ctx) if ctx.get("hero_map") else None
    posts = sorted(ctx.get("posts") or [], key=lambda p: p["slug"])
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)[:3]
    stories = [{
        "slug": p["slug"], "title": p["title"], "description": p.get("description"),
        "date": p["date"], "date_label": common.date_it(p["date"]), "cover": p.get("cover"),
        "cover_alt": p.get("cover_alt") or "", "tag": (p.get("tags") or [None])[0],
        "read_time": f"{p['read_time']} minuti di lettura" if p.get("read_time") else None,
    } for p in posts]
    areas = [{
        **area,
        "count_label": f"{integer(area['count'])} indicatori, {area['theme_count']} "
                       f"{'tema' if area['theme_count'] == 1 else 'temi'}",
        "best_key": next((k for k, v in (feat or {}).get("names", {}).items() if v == area.get("best")), None),
        "worst_key": next((k for k, v in (feat or {}).get("names", {}).items() if v == area.get("worst")), None),
    } for area in ctx.get("themes_preview") or []]
    citation = (f"Divario Italia, «I numeri delle regioni e delle province italiane», elaborazione su dati "
                f"{ctx.get('sources_label')}. {ctx.get('canonical')}")
    return {
        "indicators": integer(ctx["total_indicators"]),
        "regions": counts.get("regions"), "provinces": counts.get("provinces"),
        "feature": feat,
        "areas_regions": regions_by_area(feat["names"]) if feat else [],
        "quality": quality(ctx),
        "quiz_try": quiz_try(ctx),
        "areas": areas,
        "stories": stories,
        "citation": citation,
        "games_word": common.count_word(len(ctx.get("quiz_games") or []), feminine=False).capitalize(),
        # Le schede di fiducia di oggi, per chiave. "Copertura" ripete la
        # definizione in testa alla pagina, quindi il template ne usa solo il testo.
        "trust": {card["kicker"]: card for card in ctx.get("trust_cards") or []},
    }
