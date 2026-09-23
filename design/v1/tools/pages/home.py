"""Le frasi e le cifre della home 1.0, composte dal contesto catturato.

La home di oggi mostra il PIL pro capite tre volte (mappa, storia in evidenza,
confronto). Qui compare una volta sola, nel dato in evidenza, con la regia della
scheda: prima la striscia del divario, poi la mappa che nomina i suoi estremi
accanto alla classifica. Le cifre vengono tutte da `hero_map`, la media semplice
da `series_module`.

Qui non si formatta: i template scrivono le cifre con i filtri `num`, `rank` e
`delta` di numfmt, e le poche frasi composte in Python passano da
`derive.num` e `derive.with_unit`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import charts
import derive as common
import numfmt

from app.data import REGION_GEO_AREA

DATA = Path(__file__).resolve().parents[2] / "data"

# Le regioni che non vogliono "in": "nel Lazio", "nelle Marche".
IN_REGION = {"Lazio": "nel Lazio", "Marche": "nelle Marche"}


def in_region(name: str) -> str:
    """"in Calabria", "nel Lazio", "nelle Marche"."""
    return IN_REGION.get(name, f"in {name}")


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


def source_decimals(text: str | None) -> int | None:
    """I decimali con cui la fonte scrive una cifra: `7,65` -> 2, `54.637` -> 0."""
    if text is None:
        return None
    return len(str(text).split(",", 1)[1]) if "," in str(text) else 0


def join_names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]


def sibling(name: str) -> dict:
    """Il contesto catturato di un'altra pagina del prototipo. Se manca e'
    un errore: la home non ha un'altra fonte per quelle cifre."""
    path = DATA / f"{name}.context.json"
    if not path.exists():
        raise FileNotFoundError(f"la home legge le cifre da {path}, che manca: catturalo con tools/extract.py")
    return json.loads(path.read_text(encoding="utf-8"))["context"]


# ---------------------------------------------------------------- il dato in evidenza

def split_claim(observations: list[dict], year) -> str | None:
    """Il Mezzogiorno tutto da una parte del Centro-Nord, se lo e': nella
    striscia si vede come due gruppi di colore che non si toccano."""
    south = [o["value"] for o in observations if o["key"] in common.MEZZOGIORNO]
    north = [o["value"] for o in observations if o["key"] not in common.MEZZOGIORNO]
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
    south = [o for o in observations if o["key"] in common.MEZZOGIORNO]
    if not south:
        return None
    below = [o for o in observations if o["value"] < mean]
    south_below = [o for o in below if o["key"] in common.MEZZOGIORNO]
    others = [o for o in below if o["key"] not in common.MEZZOGIORNO]
    words = common.count_word(len(south))
    if len(south_below) == len(south):
        if not others:
            return f"Nel {year} sotto la media semplice stanno tutte e sole le {words} regioni del Mezzogiorno"
        if len(others) <= 3:
            names = join_names([common.the_place(o["name"], "regione") for o in others])
            # L'anno sta nella riga sotto il titolo: qui resta fuori, per stare nei 90 caratteri.
            return f"Sotto la media semplice stanno le {words} regioni del Mezzogiorno, più {names}"
        return f"Nel {year} tutte le {words} regioni del Mezzogiorno stanno sotto la media semplice"
    if not south_below:
        return f"Nel {year} tutte le {words} regioni del Mezzogiorno stanno sopra la media semplice"
    return (f"Nel {year} {common.count_word(len(south_below))} regioni del Mezzogiorno su {words} "
            f"stanno sotto la media semplice")


def extremes_claim(high: dict, low: dict, unit: str | None, year) -> str:
    return (f"Nel {year} si va da {common.with_unit(low['value'], unit)} {in_region(low['name'])} "
            f"a {common.with_unit(high['value'], unit)} {in_region(high['name'])}")


def feature(ctx: dict) -> dict:
    """Il dato in evidenza: striscia del divario, mappa con i due estremi, classifica."""
    hero = ctx["hero_map"]
    series = ctx.get("series_module") or {}
    unit = hero.get("unit")
    year = hero["year"]
    plural = "regioni"
    areas = charts.area_map()

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
    ratio = high["value"] / low["value"] if high and low and low["value"] > 0 else None

    # Due titoli, uno per grafico, mai la stessa frase: la striscia dice come
    # stanno le ripartizioni, la classifica chi sta sotto la media.
    split = split_claim(observations, year)
    avg_claim = average_claim(observations, mean, year)
    lead_claim = split or avg_claim or (extremes_claim(high, low, unit, year) if high else None)
    table_claim = avg_claim if split else (extremes_claim(high, low, unit, year) if high else None)
    if table_claim == lead_claim:
        table_claim = None

    strip = charts.divario_strip([{**o, "area": areas.get(o["key"])} for o in observations], mean, unit, ratio)
    callouts = ""
    if high and low:
        callouts = charts.map_callouts(common.PATHS, [(high["key"], high["name"], common.with_unit(high["value"], unit)),
                                                     (low["key"], low["name"], common.with_unit(low["value"], unit))])
    direction = hero.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso",
             "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")
    names = {o["key"]: o["name"] for o in observations}
    decimals = numfmt.column_decimals(values)
    region_areas = {o["key"]: areas.get(o["key"]) for o in observations}
    return {
        "name": hero["indicator_name"], "path": hero["indicator_path"], "year": year, "n": n,
        "unit": unit, "short_unit": common.short_unit(unit), "source_label": hero.get("source_label"),
        "lead_claim": lead_claim, "table_claim": table_claim, "verso": verso,
        "lower_better": direction in common.LOWER_BETTER,
        "options": [{"id": o["id"], "name": o["name"], "on": o["id"] == hero.get("selected_id")}
                    for o in hero.get("options") or []],
        "rows": rows, "decimals": decimals, "areas": region_areas, "area_label": charts.AREA_LABEL,
        "strip": strip, "callouts": callouts,
        "map_classes": common.map_classes({"map_colors": hero.get("colors") or {}}),
        "map_values": {o["key"]: common.with_unit(o["value"], unit) for o in observations},
        "names": names,
        "legend": common.legend(values, unit) if values else None,
        # Lo stesso contratto del modulo della scheda, con un anno solo: basta
        # perche' proto.js accenda "Trova la tua regione", il clic sulla mappa e
        # il punto della striscia.
        "explore_js": {
            "years": [year], "matrix": {str(year): {o["key"]: o["value"] for o in observations}},
            "names": names, "unit": common.short_unit(unit), "direction": direction,
            "plural": plural, "profile": "/regione/", "south": sorted(common.MEZZOGIORNO),
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

# Il contesto della home porta i punteggi arrotondati all'intero: scritti col
# ruolo "punteggio" (un decimale) direbbero 72,0 dove il dato e' 71,6. I valori
# veri stanno nelle classifiche catturate insieme, e si accettano solo se
# coincidono con quelli della home.
SIBLING = {"regioni": "classifica", "province": "classifica-province"}


def _precise_ranking(level_key: str, profile: dict, slug: str, total: int) -> list[dict]:
    data = sibling(SIBLING[level_key])["data"]
    ranking = data["ranking"]
    what = f"la classifica catturata delle {level_key}"
    if (data.get("profile") or {}).get("slug") != slug:
        raise ValueError(f"{what} non ha il profilo {slug}")
    if len(ranking) != total:
        raise ValueError(f"{what} ha {len(ranking)} righe invece di {total}")
    by_rank = {r["rank"]: r for r in ranking}
    for r in profile["top"] + profile["bottom"]:
        twin = by_rank.get(r["rank"])
        if not twin or not r["path"].endswith("/" + twin["key"]) or abs(twin["score"] - r["score"]) > 0.5:
            raise ValueError(f"{what} non coincide con la home alla posizione {r['rank']}: {twin} contro {r}")
    return ranking


def podium(level: dict, level_key: str, slug: str, total: int, unit_word: str, singular: str) -> dict | None:
    """Le prime tre e le ultime tre di un profilo, con quante ne restano in mezzo."""
    profile = next((p for p in level.get("profiles") or [] if p["slug"] == slug), None)
    if profile is None:
        return None
    precise = _precise_ranking(level_key, profile, slug, total)
    by_rank = {r["rank"]: r for r in precise}

    def row(r):
        twin = by_rank[r["rank"]]
        return {"rank": r["rank"], "name": r["name"], "path": r["path"], "score": twin["score"],
                "where": twin.get("region") or None, "width": max(0, min(100, twin["score"]))}

    top = [row(r) for r in sorted(profile["top"], key=lambda r: r["rank"])]
    bottom = [row(r) for r in sorted(profile["bottom"], key=lambda r: r["rank"])]
    middle = total - len(top) - len(bottom)
    gap = precise[0]["score"] - precise[-1]["score"]
    if profile.get("gap") is not None and abs(gap - profile["gap"]) > 1:
        raise ValueError(f"distanza fra prima e ultima delle {level_key}: {gap} contro {profile['gap']} della home")
    return {
        "label": level["label"], "classifica": level["classifica"], "cta": level["cta"],
        "profile": profile["name"], "total": total, "unit_word": unit_word, "singular": singular,
        "top": top, "bottom": bottom, "gap": gap,
        "middle": middle if middle > 0 else None,
        "middle_from": top[-1]["rank"] + 1 if top else None,
        "middle_to": bottom[0]["rank"] - 1 if bottom else None,
    }


def quality(ctx: dict) -> dict | None:
    qol = ctx.get("qol_module")
    if not qol:
        return None
    slug = qol.get("default_slug")
    counts = ctx.get("territories") or {}
    levels = qol.get("levels") or {}
    regions = podium(levels["regioni"], "regioni", slug, counts["regions"], "regioni", "Regione") if "regioni" in levels else None
    provinces = (podium(levels["province"], "province", slug, counts["provinces"], "province", "Provincia")
                 if "province" in levels else None)
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
    a = {"name": card["lead_region"], "value": parse_it(card["lead_value"]), "decimals": source_decimals(card["lead_value"])}
    b = {"name": card["lag_region"], "value": parse_it(card["lag_value"]), "decimals": source_decimals(card["lag_value"])}
    if a["value"] is None or b["value"] is None or math.isclose(a["value"], b["value"]):
        return None
    right, wrong = (a, b) if a["value"] > b["value"] else (b, a)
    options = sorted([a, b], key=lambda o: o["name"])
    return {
        "game": game, "indicator": card["name"], "path": card["path"], "year": card["year"],
        "source_label": card.get("source_label"), "unit": card.get("unit"),
        "options": [{"name": o["name"], "right": o is right} for o in options],
        # Le due cifre si scrivono con i decimali della fonte, come nella scheda.
        "right": right, "wrong": wrong,
    }


# ---------------------------------------------------------------- storie

def story(p: dict) -> dict:
    credit = p.get("cover_credit") or {}
    return {
        "slug": p["slug"], "title": p["title"], "description": p.get("description"),
        "date": p["date"], "date_label": common.date_it(p["date"]), "cover": p.get("cover"),
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
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)[:3]
    names = (feat or {}).get("names", {})
    areas = [{
        **area,
        "best_key": next((k for k, v in names.items() if v == area.get("best")), None),
        "worst_key": next((k for k, v in names.items() if v == area.get("worst")), None),
    } for area in ctx.get("themes_preview") or []]
    citation = (f"Divario Italia, «I numeri delle regioni e delle province italiane», elaborazione su dati "
                f"{ctx.get('sources_label')}. {ctx.get('canonical')}")
    return {
        "indicators": ctx["total_indicators"],
        "regions": counts.get("regions"), "provinces": counts.get("provinces"),
        "feature": feat,
        "areas_regions": regions_by_area(feat["names"]) if feat else [],
        "quality": quality(ctx),
        "quiz_try": quiz_try(ctx),
        "areas": areas,
        "stories": [story(p) for p in posts],
        "citation": citation,
        "games_word": common.count_word(len(ctx.get("quiz_games") or []), feminine=False).capitalize(),
        # Le schede di fiducia di oggi, per chiave. "Copertura" ripete la
        # definizione in testa alla pagina, quindi il template ne usa solo il testo.
        "trust": {card["kicker"]: card for card in ctx.get("trust_cards") or []},
    }
