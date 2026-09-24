"""La home della 1.0: le frasi e le cifre che il template chiede in piu' al contesto.

L'indicatore in evidenza cambia a ogni visita (`app/home_pick.py` lo pesca dal
catalogo indicizzabile, per regione o per provincia) e ha la regia della
scheda: prima la striscia del divario, poi la mappa che nomina i suoi estremi
accanto alla classifica. Le cifre vengono tutte dal livello che
`indicator_view` costruisce per la scheda, niente si ricalcola qui.

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

from app import profiles, quality_life_bes
from app.blog import STATIC_DIR, social_image_size
from app.data import REGION_GEO_AREA
from app.design import charts, numfmt
from app.design.common import (
    LOWER_BETTER,
    PATHS,
    count_word,
    date_it,
    legend,
    map_classes,
    of_place,
    ranking,
    short_unit,
    the_place,
    unit_note,
    values_note,
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

# I titoli dei grafici stanno in circa 90 caratteri (SISTEMA.md, "Regole di
# contenuto"). Una frase piu' lunga si ripiega su una piu' corta.
CLAIM_MAX = 90


def expected_areas(level_key: str) -> dict[str, set[str]]:
    """{nord|centro|sud: chiavi} di tutti i territori del livello, anche quelli
    che l'indicatore non misura: le frasi su un insieme si scrivono solo se
    l'insieme c'e' tutto."""
    areas = charts.area_map()
    regions = set(REGION_GEO_AREA)
    keys = regions if level_key == "regione" else set(areas) - regions
    return {a: {k for k in keys if areas.get(k) == a} for a in ("nord", "centro", "sud")}


def split_claim(observations: list[dict], year, areas: dict, singular: str) -> str | None:
    """Il Mezzogiorno tutto da una parte del Centro-Nord, se lo e': nella
    striscia si vede come due gruppi di colore che non si toccano. Il chiamante
    la chiede solo quando ci sono tutti i territori: "nessuna regione del
    Mezzogiorno" su un insieme che ne ignora una puo' essere falsa."""
    south = [o["value"] for o in observations if areas.get(o["key"]) == "sud"]
    north = [o["value"] for o in observations if areas.get(o["key"]) in ("nord", "centro")]
    if not south or not north:
        return None
    if max(south) < min(north):
        return f"Nel {year} nessuna {singular} del Mezzogiorno arriva al valore più basso del Centro-Nord"
    if min(south) > max(north):
        return f"Nel {year} nessuna {singular} del Mezzogiorno scende al valore più alto del Centro-Nord"
    return None


def average_claim(observations: list[dict], mean: float | None, year, areas: dict,
                  level_key: str, plural: str, all_present: bool) -> str | None:
    """Chi sta sotto la media semplice, a partire dal Mezzogiorno: si legge nella
    classifica, dove la riga della media divide i territori. Il chiamante la
    chiede solo quando il Mezzogiorno c'e' tutto, e le frasi che dicono chi
    altro sta sotto ("tutte e sole", "piu' le Marche") solo se c'e' tutto
    l'insieme (`all_present`)."""
    if mean is None:
        return None
    south = [o for o in observations if areas.get(o["key"]) == "sud"]
    if not south:
        return None
    below = [o for o in observations if o["value"] < mean]
    south_below = [o for o in below if areas.get(o["key"]) == "sud"]
    others = [o for o in below if areas.get(o["key"]) != "sud"]
    words = count_word(len(south))
    if len(south_below) == len(south):
        if all_present and not others:
            return f"Nel {year} sotto la media semplice stanno tutte e sole le {words} {plural} del Mezzogiorno"
        if all_present and len(others) <= 3:
            names = join_names([the_place(o["name"], level_key) for o in others])
            # L'anno sta nella riga sotto il titolo: qui resta fuori, per stare nei 90 caratteri.
            claim = f"Sotto la media semplice stanno le {words} {plural} del Mezzogiorno, più {names}"
            if len(claim) <= CLAIM_MAX:
                return claim
        return f"Nel {year} tutte le {words} {plural} del Mezzogiorno stanno sotto la media semplice"
    if all(o["value"] > mean for o in south):
        return f"Nel {year} tutte le {words} {plural} del Mezzogiorno stanno sopra la media semplice"
    if len(south_below) == 1:
        one = the_place(south_below[0]["name"], level_key)
        return f"Nel {year} nel Mezzogiorno solo {one} sta sotto la media semplice"
    # "Nel 2023 31 province" mette due cifre una accanto all'altra: il verbo va prima.
    return (f"Nel {year} stanno sotto la media semplice {count_word(len(south_below))} "
            f"{plural} del Mezzogiorno su {words}")


def extremes_claim(low: dict, high: dict, unit: str | None, year, level_key: str,
                   decimals: int | None = None) -> str | None:
    """"Nel 2024 si va da 21.702 euro in Calabria a 54.637 euro in Trentino Alto
    Adige". Le cifre con i decimali della colonna, come in tabella. Se con
    l'unita' non sta nei 90 caratteri si prova senza (la dice la riga sotto),
    e se non sta nemmeno cosi' non si scrive."""
    def place(o):
        return in_region(o["name"]) if level_key == "regione" else of_place(o["name"], level_key)

    for u in (unit, None):
        claim = (f"Nel {year} si va da {with_unit(low['value'], u, decimals)} {place(low)} "
                 f"a {with_unit(high['value'], u, decimals)} {place(high)}")
        if len(claim) <= CLAIM_MAX:
            return claim
    return None


# Oltre questa soglia la classifica della home si ferma alle prime e alle
# ultime dieci (SISTEMA.md, "Classifica a barre"): le 107 province intere
# stanno nella scheda, a un clic.
FULL_RANKING_MAX = 25
RANK_EDGE = 10


def feature(pick: dict | None) -> dict | None:
    """L'indicatore in evidenza con la regia della scheda: la striscia del
    divario, poi la mappa che nomina i suoi estremi accanto alla classifica
    per le regioni, le prime e le ultime dieci per le province.

    Legge il livello che `indicator_view` costruisce per la scheda, lo stesso
    che `test_v1_pages` passa su ogni istanza: la home non ricalcola niente,
    sceglie."""
    if not pick:
        return None
    meta, level = pick["meta"], pick["level"]
    observations = [o for o in level.get("observations") or [] if o.get("value") is not None]
    year = level.get("year_max")
    if len(observations) < 2 or year is None:
        return None
    key, plural, singular = level["key"], level["plural"], level["singular"]
    unit = meta.get("value_unit") or meta.get("unit")
    stats = level.get("stats") or {}
    mean = stats.get("year_avg")
    areas = charts.area_map()
    n = len(observations)

    direction = meta.get("direction")
    values = [o["value"] for o in observations]
    decimals = numfmt.column_decimals(values)
    # Gli estremi sono le due righe in cima e in fondo alla classifica, che e'
    # ordinata per verso: a parita' di valore titolo, mappa e tabella nominano
    # lo stesso territorio.
    if direction in LOWER_BETTER:
        low, high = observations[0], observations[-1]
    else:
        high, low = observations[0], observations[-1]

    # Le frasi sul Mezzogiorno valgono su un insieme: si scrivono solo se i
    # territori che nominano ci sono tutti. Con il Molise senza dato, "tutte le
    # sette regioni del Mezzogiorno" era falsa.
    present = {o["key"] for o in observations}
    expected = expected_areas(key)
    south_present = bool(expected["sud"]) and expected["sud"] <= present
    all_present = south_present and all(keys <= present for keys in expected.values())
    by_value = sorted(observations, key=lambda o: o["value"], reverse=True)

    # Due titoli, uno per grafico, mai la stessa frase: la striscia dice come
    # stanno le ripartizioni, la classifica chi sta sotto la media.
    split = split_claim(by_value, year, areas, singular) if all_present else None
    avg_claim = average_claim(by_value, mean, year, areas, key, plural, all_present) if south_present else None
    extremes = extremes_claim(low, high, unit, year, key, decimals)
    lead_claim = split or avg_claim or extremes or f"Il divario nel {year}: le {n} {plural} sulla stessa scala"
    table_claim = avg_claim if split else extremes
    if table_claim == lead_claim:
        table_claim = None

    strip = charts.divario_strip([{**o, "area": areas.get(o["key"])} for o in observations],
                                 mean, unit, stats.get("gap_ratio"))
    has_map = bool(level.get("has_map"))
    callouts = charts.map_callouts(PATHS, [(high["key"], high["name"], with_unit(high["value"], unit, decimals)),
                                           (low["key"], low["name"], with_unit(low["value"], unit, decimals))]) if has_map else ""
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso",
             "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")
    # Solo i territori con un dato: "Trova la tua provincia" offriva anche quelli
    # senza, e sceglierli non accendeva niente.
    names = {o["key"]: o["name"] for o in observations}
    territory_areas = {o["key"]: areas.get(o["key"]) for o in observations}

    rows = ranking({**level, "observations": observations}, unit)
    top = bottom = None
    if n > FULL_RANKING_MAX:
        ranked = [r for r in rows if not r.get("ref")]
        top, bottom = ranked[:RANK_EDGE], ranked[-RANK_EDGE:]
        rows = []

    code = meta["canonical_path"].rstrip("/").rsplit("/", 1)[-1]
    other = pick.get("other_level")
    return {
        "name": meta["name"], "path": meta["canonical_path"], "year": year, "n": n,
        "level": key, "plural": plural, "singular": singular, "requested": bool(pick.get("requested")),
        "unit_note": unit_note(unit, meta["name"]), "values_note": values_note(unit),
        "short_unit": short_unit(unit), "source_label": meta.get("source_label"),
        "source_url": meta.get("source_url"), "theme": meta.get("theme"), "theme_path": meta.get("theme_path"),
        "lead_claim": lead_claim, "table_claim": table_claim, "verso": verso,
        "lower_better": direction in LOWER_BETTER,
        "rows": rows, "top": top, "bottom": bottom, "decimals": decimals,
        "middle": n - 2 * RANK_EDGE if top else None,
        "areas": territory_areas, "area_label": charts.AREA_LABEL,
        "profile_path": level.get("profile_path"),
        "strip": strip, "callouts": callouts, "has_map": has_map,
        "map_classes": map_classes(level) if has_map else {},
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in observations},
        "names": names,
        "legend": legend(values, unit) if has_map else None,
        # L'altro livello dello stesso indicatore, quando c'e': un link vero,
        # che funziona senza JavaScript e non offre ai motori copie della home.
        "other_level": {"key": other, "href": f"/?indicatore={code}&livello={other}",
                        "label": "Lo stesso indicatore per provincia" if other == "provincia"
                        else "Lo stesso indicatore per regione"} if other else None,
        # Lo stesso contratto del modulo della scheda, con un anno solo: basta
        # perche' v1.js accenda "Trova la tua regione", il clic sulla mappa e
        # il punto della striscia.
        "explore_js": {
            "years": [year], "matrix": {str(year): {o["key"]: o["value"] for o in observations}},
            "names": names, "unit": numfmt.phrase_unit(unit), "direction": direction,
            "plural": plural, "profile": level.get("profile_path"), "south": [],
            "decimals": decimals, "areas": territory_areas,
        },
    }


# ---------------------------------------------------------------- regioni per ripartizione

def region_names() -> dict[str, str]:
    """Le venti regioni col loro nome, a prescindere dall'indicatore in
    evidenza: quando esce una serie provinciale le sezioni che parlano di
    regioni non devono restare vuote."""
    return {key: name for key in REGION_GEO_AREA if (name := profiles.region_name(key))}


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

def quiz_try(ctx: dict, feature_path: str | None = None) -> dict | None:
    """Una domanda di "Chi è maggiore?" fatta con una lettura in evidenza del
    contesto: due regioni, un indicatore, quale ha il valore piu' alto. Mai
    sull'indicatore che la pagina ha appena mostrato."""
    game = next((g for g in ctx.get("quiz_games") or [] if g["href"].endswith("chi-e-maggiore")), None)
    card = next((c for c in ctx.get("insight_cards") or [] if c.get("path") != feature_path), None)
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


# ---------------------------------------------------------------- le porte del sito

# Le destinazioni che la home mette in evidenza subito sotto la testata: le
# quattro grandi, con la cifra che le misura, e le altre in fila. I percorsi
# sono quelli di `app/nav.py`, e `tests/unit/test_home_doors.py` controlla che
# ognuno ci sia: una porta che porta a una pagina tolta dal menu e' una porta
# rotta che nessuna prova vedrebbe.
MAIN_DOORS = ("/regioni", "/province", "/temi", "/qualita-della-vita")
MORE_DOORS = ("/atlante", "/confronto", "/divari-regionali", "/blog", "/quiz", "/catalogo-dati")


def doors(ctx: dict, qol: dict | None = None) -> dict:
    """Le porte d'ingresso, con le cifre calcolate: "20 regioni" era scritto a
    mano in sei posti, e le province non comparivano in nessuno. Dove la cifra
    e il titolo dicono la stessa cosa ("20", "Regioni") l'unita' non si ripete."""
    counts = ctx.get("territories") or {}
    ranked = sum(p["total"] for p in (qol["regions"], qol["provinces"]) if p) if qol else None
    main = {
        "/regioni": {"num": counts.get("regions"), "unit": None, "title": "Regioni",
                     "text": "Il profilo di ogni regione: dove stacca, dove resta indietro, i valori di ogni indicatore."},
        "/province": {"num": counts.get("provinces"), "unit": None, "title": "Province",
                      "text": "Posizione, dimensioni del benessere e tutti gli indicatori di ogni provincia."},
        "/temi": {"num": ctx.get("theme_total"), "unit": None, "title": "Temi",
                  "text": "Gli indicatori raccolti per argomento, con la mappa e chi sta in testa su ognuno."},
        "/qualita-della-vita": {"num": ranked or None, "unit": "territori in classifica", "title": "Qualità della vita",
                                "text": "Dove si vive meglio: la classifica delle regioni e quella delle province, con il profilo di priorità che scegli tu."},
    }
    more = {
        "/atlante": {"title": "L'atlante", "text": f"{numfmt.text(ctx.get('total_indicators'), 0)} indicatori sulla mappa, anno per anno"
                     if ctx.get("total_indicators") else "Tutti gli indicatori sulla mappa, anno per anno"},
        "/confronto": {"title": "Confronta i territori", "text": "Due o tre regioni fianco a fianco su un indicatore"},
        "/divari-regionali": {"title": "Divari regionali", "text": "Nord, Centro e Mezzogiorno messi a confronto"},
        "/blog": {"title": "Storie", "text": f"{ctx['post_total']} articoli costruiti sui dati" if ctx.get("post_total")
                  else "Gli articoli costruiti sui dati"},
        "/quiz": {"title": "Quiz", "text": f"{count_word(len(ctx.get('quiz_games') or []), feminine=False).capitalize()} giochi sugli stessi indicatori"
                  if ctx.get("quiz_games") else "Giochi sugli stessi indicatori"},
        "/catalogo-dati": {"title": "Catalogo dati", "text": "Le schede principali in un elenco, con la loro fonte"},
    }
    return {
        "main": [{"path": path, **main[path]} for path in MAIN_DOORS],
        "more": [{"path": path, **more[path]} for path in MORE_DOORS],
    }


# ---------------------------------------------------------------- tutta la pagina

def derive(ctx: dict) -> dict:
    """Tutto cio' che il template della home chiede in piu' rispetto al contesto."""
    counts = ctx.get("territories") or {}
    feat = feature(ctx.get("feature_pick"))
    qol = quality(ctx)
    posts = sorted(ctx.get("posts") or [], key=lambda p: p["slug"])
    posts = sorted(posts, key=lambda p: str(p.get("date") or ""), reverse=True)[:3]
    names = region_names()
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
        "doors": doors(ctx, qol),
        "feature": feat,
        "areas_regions": regions_by_area(names),
        "quality": qol,
        "quiz_try": quiz_try(ctx, (feat or {}).get("path")),
        "areas": areas,
        "stories": [story(p) for p in posts],
        "citation": citation,
        "games_word": count_word(len(ctx.get("quiz_games") or []), feminine=False).capitalize(),
        # Le schede di fiducia di prima, per chiave. "Copertura" ripete la
        # definizione in testa alla pagina, quindi il template ne usa solo il testo.
        "trust": {card["kicker"]: card for card in ctx.get("trust_cards") or []},
    }
