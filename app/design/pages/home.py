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
import random
import re
import struct
from functools import lru_cache

from app import indicator_notes, profiles, quality_life_bes
from app.blog import STATIC_DIR, social_image_size
from app.data import REGION_GEO_AREA
from app.design import charts, maps, numfmt
from app.design.common import (
    LOWER_BETTER,
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
# La striscia della home prende tutta la larghezza della scheda che la
# contiene: a 1920 pixel sono circa 1360, a 1440 circa 1300. Il taglio si
# disegna a questa misura e scala di poco nelle due direzioni.
HOME_STRIP_WIDTH = 1320
LEVEL_TAB = {"regione": "Regioni", "provincia": "Province"}


def level_panel(meta: dict, level: dict, code: str) -> dict | None:
    """Un livello dell'indicatore in evidenza, con la regia della scheda: la
    striscia del divario, poi la mappa che nomina i suoi estremi accanto alla
    classifica. Regioni e province hanno la stessa forma: per le province la
    classifica tiene le prime e le ultime dieci, con una riga che dice quante
    ne restano in mezzo.

    Legge il livello che `indicator_view` costruisce per la scheda, lo stesso
    che `test_v1_pages` passa su ogni istanza: la home non ricalcola niente,
    sceglie."""
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
                                 mean, unit, stats.get("gap_ratio"), xl_width=HOME_STRIP_WIDTH)
    shapes = maps.paths(key)
    callouts = charts.map_callouts(shapes, [(high["key"], high["name"], with_unit(high["value"], unit, decimals)),
                                            (low["key"], low["name"], with_unit(low["value"], unit, decimals))])
    # Le classi della rampa: quelle della scheda per le regioni, le stesse sei
    # a intervalli uguali calcolate qui per le province, che la scheda non
    # disegna su una mappa.
    colors = level.get("map_colors") or indicator_notes.ds_choropleth_colors(
        [{"region_key": o["key"], "value": o["value"]} for o in observations])
    # Solo i territori con un dato: "Trova la tua provincia" offriva anche quelli
    # senza, e sceglierli non accendeva niente.
    names = {o["key"]: o["name"] for o in observations}
    territory_areas = {o["key"]: areas.get(o["key"]) for o in observations}

    # La classifica in due colonne da dieci, per tutti e due i livelli: le
    # regioni dalla 1a alla 10a e dalla 11a alla 20a, con la riga della media
    # dove cade, le province le prime e le ultime dieci. In una colonna sola
    # le venti righe facevano la fascia lunga il doppio della mappa.
    rows = ranking({**level, "observations": observations}, unit)
    middle = None
    if n > FULL_RANKING_MAX:
        ranked = [r for r in rows if not r.get("ref")]
        middle = n - 2 * RANK_EDGE
        columns = [{"caption": "Le prime dieci", "rows": ranked[:RANK_EDGE]},
                   {"caption": "Le ultime dieci", "rows": ranked[-RANK_EDGE:]}]
    else:
        half = math.ceil(sum(1 for r in rows if not r.get("ref")) / 2)
        seen, split = 0, len(rows)
        for i, r in enumerate(rows):
            if not r.get("ref"):
                seen += 1
                if seen == half:
                    split = i + 1
                    break
        columns = [{"caption": None, "rows": rows[:split]}, {"caption": None, "rows": rows[split:]}]
        columns = [c for c in columns if c["rows"]]

    return {
        "key": key, "tab": LEVEL_TAB.get(key, plural.capitalize()), "year": year, "n": n,
        "plural": plural, "singular": singular,
        # Senza JavaScript il selettore e' questo link: #dato riporta al pannello.
        "href": f"/?indicatore={code}&livello={key}#dato",
        "unit_note": unit_note(unit, meta["name"]), "values_note": values_note(unit),
        "short_unit": short_unit(unit),
        "lead_claim": lead_claim, "table_claim": table_claim,
        "lower_better": direction in LOWER_BETTER,
        "columns": columns, "middle": middle, "decimals": decimals,
        "areas": territory_areas, "area_label": charts.AREA_LABEL,
        "profile_path": level.get("profile_path"),
        "strip": strip, "callouts": callouts,
        "map_classes": map_classes({"map_colors": colors}),
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in observations},
        "names": names,
        # Sulla mappa ci sono anche i territori senza dato: il tooltip ne dice
        # il nome, non la chiave ("reggio-calabria n.d.").
        "map_names": {**level_names(key), **names},
        "legend": legend(values, unit),
        "missing": bool(set(shapes) - set(names)),
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


def feature(pick: dict | None) -> dict | None:
    """L'indicatore in evidenza: cio' che vale per tutti e due i livelli (nome,
    tema, fonte, verso) e un pannello per livello. Il primo e' quello estratto,
    il secondo c'e' quando lo stesso indicatore sta nel pool anche all'altro
    livello: la pagina li disegna tutti e due e il selettore passa dall'uno
    all'altro senza ricaricare. Senza JavaScript il selettore e' un link."""
    if not pick:
        return None
    meta = pick["meta"]
    code = meta["canonical_path"].rstrip("/").rsplit("/", 1)[-1]
    first = level_panel(meta, pick["level"], code)
    if first is None:
        return None
    second = level_panel(meta, pick["other"], code) if pick.get("other") else None
    direction = meta.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso",
             "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")
    shown = {first["key"]} | ({second["key"]} if second else set())
    available = pick.get("available") or [first["key"]]
    elsewhere = next((k for k in available if k not in shown), None)

    # La scheda si apre sul suo primo livello: per l'altro serve `?livello=`,
    # o il pannello delle province mandava alla classifica delle regioni.
    def scheda(key):
        path = meta["canonical_path"]
        return path if key == available[0] else f"{path}?livello={key}"

    for panel in (first, second):
        if panel:
            panel["scheda"] = scheda(panel["key"])
    elsewhere_href, elsewhere_twin = (scheda(elsewhere) if elsewhere else None), False
    # L'altro livello puo' stare in una scheda gemella (la speranza di vita
    # regionale e quella con le province): la frase porta li'.
    if not elsewhere and not second:
        from app.indicator_view import twin_level

        twin = twin_level(meta, [{"key": key} for key in available])
        if twin:
            elsewhere, elsewhere_href, elsewhere_twin = twin["key"], twin["path"], True
    return {
        "name": meta["name"], "path": meta["canonical_path"], "code": code,
        "level": first["key"], "requested": bool(pick.get("requested")),
        "elsewhere": {"regione": "regione", "provincia": "provincia"}.get(elsewhere),
        "elsewhere_href": elsewhere_href, "elsewhere_twin": elsewhere_twin,
        "source_label": meta.get("source_label"), "source_url": meta.get("source_url"),
        "theme": meta.get("theme"), "theme_path": meta.get("theme_path"), "verso": verso,
        "levels": [first] + ([second] if second else []),
    }


# ---------------------------------------------------------------- regioni e province

def region_names() -> dict[str, str]:
    """Le venti regioni col loro nome, a prescindere dall'indicatore in
    evidenza: quando esce una serie provinciale le sezioni che parlano di
    regioni non devono restare vuote."""
    return {key: name for key in REGION_GEO_AREA if (name := profiles.region_name(key))}


@lru_cache(maxsize=1)
def province_names() -> dict[str, str]:
    """Le 107 province col loro nome, dalla tabella dei codici del BES."""
    import csv

    from app import bes_data

    with bes_data.PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        return {row["province_key"]: row["name"] for row in csv.DictReader(handle, delimiter=";")}


def level_names(level_key: str) -> dict[str, str]:
    return region_names() if level_key == "regione" else province_names()


def _ordinal(rank: int, total: int | None) -> str:
    return f"{rank}ª su {total}" if total else f"{rank}ª"


def region_preview(key: str, profile: dict, answer: dict, quality_ranks: dict, quality_total: int | None) -> dict:
    """L'anteprima della scheda di una regione, con le frasi della sua testata:
    la posizione media sugli indicatori confrontabili, il tema dove va meglio e
    quello dove va peggio, la posizione nella qualita' della vita. Le cifre
    escono dalle stesse funzioni della pagina (`profiles.region_profile`,
    `regione._answer`), cosi' l'anteprima non contraddice la scheda."""
    name = profile["region"]
    total = profile.get("region_total")
    area = charts.area_map().get(key)
    the_name = the_place(name, "regione")
    verb = "sono" if name == "Marche" else "è"
    if profile.get("avg_rank") and profile.get("comparable_count"):
        lead = (f"In media {the_name} {verb} {profile['avg_rank']}ª su {total} regioni "
                f"sui {profile['comparable_count']} indicatori confrontabili.")
    else:
        lead = f"Il profilo {of_place(name, 'regione')} su {len(profile.get('all_indicators') or [])} indicatori."
    facts = []
    if answer.get("strong"):
        a = answer["strong"]
        facts.append({"label": "Va meglio in", "text": a["theme"], "href": a["path"], "note": _ordinal(a["rank"], a["total"])})
    if answer.get("weak"):
        a = answer["weak"]
        facts.append({"label": "Va peggio in", "text": a["theme"], "href": a["path"], "note": _ordinal(a["rank"], a["total"])})
    if quality_ranks.get(key):
        facts.append({"label": "Qualità della vita", "text": _ordinal(quality_ranks[key], quality_total),
                      "href": None, "note": None})
    return {"key": key, "name": name, "href": f"/regione/{key}", "area": area,
            "kicker": charts.AREA_LABEL.get(area), "lead": lead[:1].upper() + lead[1:], "facts": facts,
            "cta": f"Il profilo {of_place(name, 'regione')}"}


def province_preview(key: str, profile: dict) -> dict:
    """L'anteprima della scheda di una provincia, con le frasi della sua
    testata: la posizione per qualita' della vita, il punteggio col profilo, la
    dimensione dove va meglio e quella dove va peggio. Dalla stessa
    `province_profile.profilo` della pagina."""
    name = profile["name"]
    the_name = the_place(name, "provincia")
    categories = [c for c in profile.get("categories") or [] if c.get("score") is not None]
    facts = [{"label": "Punteggio", "text": f"{numfmt.text(profile['score'], 1)} su 100",
              "href": None, "note": f"profilo {((profile.get('profile') or {}).get('name') or '').lower()}".strip()}]
    if categories:
        facts.append({"label": "Va meglio su", "text": categories[0]["name"], "href": None,
                      "note": numfmt.text(categories[0]["score"], 1)})
    if len(categories) > 1:
        facts.append({"label": "Va peggio su", "text": categories[-1]["name"], "href": None,
                      "note": numfmt.text(categories[-1]["score"], 1)})
    area = charts.area_map().get(key)
    # La regione e' un link, come sulla pagina: l'anteprima della provincia
    # porta anche un piano piu' su. Sopra il nome la ripartizione, come per
    # le regioni.
    if profile.get("region"):
        facts.insert(0, {"label": "Regione", "text": profile["region"], "href": profile.get("region_path"),
                         "note": None})
    return {"key": key, "name": name, "href": f"/provincia/{key}", "area": area,
            "kicker": charts.AREA_LABEL.get(area),
            "lead": f"{the_name[:1].upper() + the_name[1:]} è {profile['rank']}ª su {profile['total']} province per qualità della vita.",
            "facts": facts, "cta": f"Il profilo {of_place(name, 'provincia')}"}


@lru_cache(maxsize=1)
def territory_previews() -> dict[str, dict[str, dict]]:
    """Le anteprime di tutte le regioni e le province, una volta per processo:
    la home non sta nella cache di pagina (l'indicatore cambia a ogni visita),
    e le venti schede regionali costano circa un secondo e mezzo a freddo. I
    dati cambiano solo col deploy, come per i loader con `lru_cache`."""
    from app import province_profile
    from app.design.pages import regione

    quality = regione._region_quality()
    ranks = quality["ranks"] if quality else {}
    regions = {}
    for key in REGION_GEO_AREA:
        profile = profiles.region_profile(key)
        if profile:
            regions[key] = region_preview(key, profile, regione._answer(profile), ranks, len(ranks) or None)
    provinces = {}
    for key in province_profile.chiavi():
        profile = province_profile.profilo(key)
        if profile and profile.get("rank") and profile.get("score") is not None:
            provinces[key] = province_preview(key, profile)
    return {"regione": regions, "provincia": provinces}


def territories(rng: random.Random | None = None) -> list[dict]:
    """I due blocchi della fascia Regioni e province: una mappa che si puo'
    cliccare, un territorio scelto a caso con l'anteprima della sua scheda, e
    tutte le altre anteprime per passare da uno all'altro senza ricaricare.
    `rng` serve alle prove, come in `home_pick`."""
    choice = (rng or random).choice
    previews = territory_previews()
    blocks = []
    for level, title, index, word in (("regione", "Le regioni", "/regioni", "regioni"),
                                      ("provincia", "Le province", "/province", "province")):
        items = previews.get(level) or {}
        if not items:
            continue
        selected = choice(sorted(items))
        blocks.append({
            "level": level, "title": title, "index": index, "count": len(items), "word": word,
            "singular": "regione" if level == "regione" else "provincia",
            "selected": items[selected], "names": {k: v["name"] for k, v in items.items()},
            "previews": items,
        })
    return blocks


# ---------------------------------------------------------------- qualita' della vita

def quality(ctx: dict) -> dict | None:
    """La porta della qualita' della vita: quanti territori, quali dimensioni,
    quali profili di priorita'. Niente classifica: la home non la svela, la
    mostra la pagina dedicata. I profili portano alla classifica delle regioni
    col profilo scelto (`?profilo=`, che la pagina indice non legge), e accanto
    ci sono le due classifiche, regioni e province.

    Le dimensioni si contano per livello: le province non hanno indicatori su
    due di esse (imprese, benessere soggettivo), e la frase lo dice. La fonte
    viene dalla metodologia della classifica, non dal template."""
    qol = ctx.get("qol_module")
    if not qol:
        return None
    slug = qol.get("default_slug")
    levels = qol.get("levels") or {}
    totals = {}
    for url_level, level_key in QOL_LEVEL.items():
        if url_level in levels:
            rows = ((quality_life_bes.build_bes_ranking(level_key, slug) or {}).get("ranking")) or []
            if rows:
                totals[url_level] = len(rows)
    if "regioni" not in totals:
        return None
    base = quality_life_bes.build_bes_ranking("regione", slug) or {}
    measured = {lv: {k for k, v in quality_life_bes._indicators_by_category(lv).items() if v}
                for lv in ("regione", "provincia")}
    dimensions = [{"name": c["name"], "regions_only": c["slug"] not in measured["provincia"]}
                  for c in base.get("categories") or [] if c.get("name") and c["slug"] in measured["regione"]]
    classifica = "/qualita-della-vita/classifica/regioni"
    profiles_list = [{"name": p["name"], "slug": p["slug"], "text": p.get("description"),
                      "href": classifica if p["slug"] == slug else f"{classifica}?profilo={p['slug']}"}
                     for p in qol.get("profiles") or []]
    province_dims = sum(1 for d in dimensions if not d["regions_only"])
    # I profili portano alle regioni: le due classifiche, una per livello,
    # stanno accanto, cosi' chi cerca la sua provincia non passa dalle regioni.
    rankings = [{"href": f"/qualita-della-vita/classifica/{url_level}", "n": totals[url_level],
                 "plural": url_level}
                for url_level in QOL_LEVEL if url_level in totals]
    return {"regions": totals.get("regioni"), "provinces": totals.get("province"),
            "dimensions": dimensions, "profiles": profiles_list, "rankings": rankings,
            "dims_regions": len(dimensions),
            "dims_provinces": province_dims if totals.get("province") and province_dims < len(dimensions) else None,
            "institutions": (base.get("methodology") or {}).get("catalog_institutions"),
            "profile_word": count_word(len(profiles_list), feminine=False) if profiles_list else None}


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


def _atlas_door_text(ctx: dict) -> str:
    """La porta dell'atlante dice le due cifre che l'atlante mostra.

    All'apertura, senza `partial=1` e con fonte e area su "tutte", la SPA
    elenca solo le serie complete e lo scrive ("solo dati completi (447)").
    Una porta che diceva "594 indicatori" apriva una lista di 447: il totale
    da solo e' la promessa sbagliata, quindi senza il conto delle complete la
    porta resta senza cifre."""
    total, complete = ctx.get("total_indicators"), ctx.get("complete_indicators")
    tail = "da filtrare per tema, fonte e anni"
    if not total or complete is None:
        return f"Tutti gli indicatori, {tail}"
    if complete >= total:
        return f"{numfmt.text(total, 0)} indicatori, tutti con i dati completi, {tail}"
    return f"{numfmt.text(total, 0)} indicatori, {numfmt.text(complete, 0)} con i dati completi, {tail}"


def doors(ctx: dict, qol: dict | None = None) -> dict:
    """Le porte d'ingresso, con le cifre calcolate: "20 regioni" era scritto a
    mano in sei posti, e le province non comparivano in nessuno. Dove la cifra
    e il titolo dicono la stessa cosa ("20", "Regioni") l'unita' non si ripete."""
    counts = ctx.get("territories") or {}
    ranked = sum(n for n in (qol["regions"], qol["provinces"]) if n) if qol else None
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
    # La mappa dell'atlante si colora con uno di sei indicatori, e solo
    # all'ultimo anno: "sulla mappa, anno per anno" prometteva quello che la
    # pagina non fa. Quello che fa davvero e' l'elenco, con i filtri per tema,
    # fonte e anni.
    more = {
        "/atlante": {"title": "L'atlante", "text": _atlas_door_text(ctx)},
        "/confronto": {"title": "Confronta le regioni", "text": "Due o tre regioni fianco a fianco su un indicatore"},
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


# I tre giochi del quiz con la loro illustrazione e il lavaggio della scheda.
GAME_LOOK = {
    "indovina-la-regione": {"icon": "game-map", "tone": "blue"},
    "chi-e-maggiore": {"icon": "game-versus", "tone": "green"},
    "ordina": {"icon": "game-sort", "tone": "red"},
}

# Le quattro aree dei temi con la loro icona e il lavaggio del distintivo. Non
# sono colori dei dati (rampa, ripartizioni) ne' l'accento: servono solo a
# riconoscere l'area a colpo d'occhio.
AREA_LOOK = {
    "Economia e opportunità": {"icon": "economy", "tone": "amber"},
    "Persone e conoscenza": {"icon": "people", "tone": "green"},
    "Territorio e servizi": {"icon": "territory", "tone": "blue"},
    "Comunità e benessere": {"icon": "community", "tone": "red"},
}


# ---------------------------------------------------------------- tutta la pagina

def derive(ctx: dict) -> dict:
    """Tutto cio' che il template della home chiede in piu' rispetto al contesto."""
    counts = ctx.get("territories") or {}
    feat = feature(ctx.get("feature_pick"))
    qol = quality(ctx)
    posts = sorted(ctx.get("posts") or [], key=lambda p: p["slug"])
    posts = sorted(posts, key=lambda p: str(p.get("date") or ""), reverse=True)[:4]
    names = region_names()
    areas = [{
        **area,
        **AREA_LOOK.get(area.get("area"), {"icon": "catalog", "tone": "neutral"}),
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
        "territories": territories(ctx.get("territory_rng")),
        "region_names": names,
        "quality": qol,
        "quiz_try": quiz_try(ctx, (feat or {}).get("path")),
        "games": [{**g, **GAME_LOOK.get(g["href"].rsplit("/", 1)[-1], {"icon": "bolt", "tone": "amber"})}
                  for g in ctx.get("quiz_games") or []],
        "areas": areas,
        "stories": [story(p) for p in posts],
        "citation": citation,
        "games_word": count_word(len(ctx.get("quiz_games") or []), feminine=False).capitalize(),
        # Le schede di fiducia di prima, per chiave. "Copertura" ripete la
        # definizione in testa alla pagina, quindi il template ne usa solo il testo.
        "trust": {card["kicker"]: card for card in ctx.get("trust_cards") or []},
    }
