"""La classifica della qualita' della vita della 1.0, e i pezzi che l'indice riusa.

Il contesto della rotta porta la classifica gia' calcolata dall'app
(`quality_life_bes.build_bes_ranking`: punteggio, dimensioni piu' forti e piu'
deboli, classifiche per dimensione, conteggi delle fonti). Qui si compongono le
frasi e le righe che la pagina chiede in piu': la risposta con prima, ultima e
distanza, il titolo-affermazione sul Mezzogiorno, le tessere, le righe della
tabella con la barra 0-100, la mappa.

Due cose il contesto non le porta e si chiedono all'app:
- gli anni dei dati, che `build_bes_ranking` non espone. Si leggono dagli
  stessi indicatori che il punteggio usa, e si accettano solo se il numero
  degli indicatori e i conteggi di freschezza coincidono con quelli della
  classifica: se non tornano, la pagina non dice gli anni, non ne inventa;
- per l'indice, la classifica di ogni profilo, per dire chi sale e chi scende.
  `build_bes_ranking` e' memoizzata in `app.cache`, quindi le dodici
  classifiche si calcolano una volta e non a ogni richiesta.

Le cifre non si scrivono qui: le righe portano i valori grezzi e il template
li passa ai filtri `num` e `rank` di `numfmt`. I punteggi da 0 a 100 hanno il
ruolo `score`, un decimale fisso. Dove la cifra sta dentro una frase composta
qui, o in un testo che non e' HTML (i richiami della mappa, il suggerimento al
passaggio del mouse, la legenda), passa da `points`, che e' lo stesso ruolo.

Una cifra che manca toglie la frase, non la sostituisce: nessuna funzione qui
restituisce `common.PLACEHOLDER`.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter

from app import sources
from app.data import REGION_GEO_AREA
from app.design import charts, common, numfmt
from app.indicator_notes import choropleth_scale
from app.design.common import PATHS, count_word, of_place, ordinal, with_unit
from app.seo_titles import of_region

LEVELS = {
    "regione": {"url": "regioni", "singular": "regione", "plural": "regioni", "label": "Regioni",
                "profile": "/regione/", "index": "/regioni", "adj": "regionali"},
    "provincia": {"url": "province", "singular": "provincia", "plural": "province", "label": "Province",
                  "profile": "/provincia/", "index": "/province", "adj": "provinciali"},
}
SOUTH_AREAS = ("Sud", "Isole")
# Oltre questa lunghezza la classifica mostra le prime e le ultime EDGE righe e
# tiene le altre nello stesso documento, dentro un details (SISTEMA.md).
SPLIT_OVER = 30
EDGE = 10
BASE = "/qualita-della-vita/classifica/"


# ---------------------------------------------------------------- cifre e parole

def points(value) -> str:
    """Un punteggio 0-100 come testo, con il ruolo `score` di numfmt: 71,6, 0,0, 100,0."""
    return numfmt.text(value, numfmt.FIXED["score"])


def bar_width(value) -> float:
    """La lunghezza della barra, in percento della scala 0-100."""
    return round(max(0.0, min(100.0, float(value or 0))), 1)


def join_names(names: list[str]) -> str:
    """`A`, `A e B`, `A, B e C`."""
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def split_prep(phrase: str, name: str) -> str:
    """La sola preposizione di `of_place`, per mettere il link sul nome."""
    return phrase[: len(phrase) - len(name)] if phrase.endswith(name) else phrase + " "


def profile_href(level: str, slug: str, default: str) -> str:
    return BASE + LEVELS[level]["url"] + ("" if slug == default else f"?profilo={slug}")


def downloads(level: str, slug: str, default: str) -> dict:
    query = "" if slug == default else f"?profilo={slug}"
    root = "/download/quality-life/" + LEVELS[level]["url"]
    return {"csv": root + query, "json": root + ".json" + query}


def safe_category_path(slug: str) -> str | None:
    """Il percorso del tema di una dimensione, o None se la dimensione non ha
    un tema: la cella resta testo invece di far cadere la pagina."""
    from app.taxonomy import category_path

    try:
        return category_path(slug)
    except KeyError:
        return None


# ---------------------------------------------------------------- territori

def region_paths(ranking: list[dict]) -> dict[str, str]:
    """{nome della regione: /regione/<chiave>} per le righe provinciali.

    La stessa regola della vista della classifica (`quality_life_classifica`):
    `region_key_for` slugifica qualunque stringa, quindi la chiave si accetta
    solo se e' una regione vera. Serve all'indice, che la vista non la passa.
    """
    from app import profiles

    out = {}
    for row in ranking:
        name = row.get("region")
        if not name or name in out:
            continue
        key = profiles.region_key_for(name)
        if key and profiles.region_name(key):
            out[name] = f"/regione/{key}"
    return out


def region_key_of(row: dict, level: str, paths: dict) -> str | None:
    """La chiave della regione di una riga: la riga stessa per le regioni, il
    percorso validato dalla vista (`region_paths`) per le province."""
    if level == "regione":
        return row["key"]
    path = (paths or {}).get(row.get("region") or "")
    return path.rsplit("/", 1)[-1] if path else None


def is_south(row: dict, level: str, paths: dict) -> bool | None:
    key = region_key_of(row, level, paths)
    area = REGION_GEO_AREA.get(key) if key else None
    return None if area is None else area in SOUTH_AREAS


def table_rows(ranking: list[dict], level: str, paths: dict, with_delta: bool) -> list[dict]:
    """Le righe della classifica, pronte per il template: il punteggio resta
    grezzo, lo scrive il filtro `num` con il ruolo `score`."""
    spec = LEVELS[level]
    areas = charts.area_map()
    out = []
    for row in ranking:
        strong = (row.get("strongest_categories") or [None])[0]
        weak = (row.get("weakest_categories") or [None])[0]
        item = {
            "rank": row["rank"], "key": row["key"], "name": row["name"],
            "href": spec["profile"] + row["key"],
            "score": row["score"], "width": bar_width(row["score"]),
            "area": areas.get(row["key"]),
            "strong": strong["name"] if strong else None,
            "weak": weak["name"] if weak else None,
            "region": None, "metro": bool(row.get("metro_city")),
        }
        if level == "provincia" and row.get("region"):
            item["region"] = {"name": row["region"], "href": (paths or {}).get(row["region"])}
        if with_delta:
            item["delta"] = movement(row["rank"], row.get("delta_rank") or 0)
        out.append(item)
    return out


def movement(rank: int, delta: int) -> dict:
    """Il segno di movimento rispetto al profilo Equilibrato: la direzione e le
    due posizioni, che il template scrive con il filtro `rank`."""
    before = rank + delta
    if delta > 0:
        return {"dir": "up", "verb": "sale", "before": before, "after": rank}
    if delta < 0:
        return {"dir": "down", "verb": "scende", "before": before, "after": rank}
    return {"dir": None, "verb": None, "before": before, "after": rank}


def from_to(first: int, last: int) -> str:
    """`Dall'11ª alla 97ª`: l'articolo si elide davanti a ottava, undicesima,
    ottantesima e simili."""
    def art(prep: str, n: int) -> str:
        vowel = n in (8, 11) or 80 <= n <= 89 or 800 <= n <= 899
        return f"{prep}ll'{ordinal(n)}" if vowel else f"{prep}lla {ordinal(n)}"
    text = f"{art('da', first)} {art('a', last)}"
    return text[:1].upper() + text[1:]


def split(rows: list[dict], plural: str) -> dict:
    """Prime e ultime EDGE righe in vista, le altre nel details."""
    if len(rows) <= SPLIT_OVER:
        return {"head": rows, "middle": [], "tail": [], "middle_label": None}
    middle = rows[EDGE:-EDGE]
    label = f"{from_to(middle[0]['rank'], middle[-1]['rank'])}: le altre {len(middle)} {plural}"
    return {"head": rows[:EDGE], "middle": middle, "tail": rows[-EDGE:], "middle_label": label}


def subject(name: str, level: str) -> tuple[str, bool]:
    """Il territorio come soggetto di una frase: "il Lazio", "le Marche",
    "Biella". Il secondo valore dice se il verbo va al plurale. L'articolo
    viene da `of_region`, che conosce il genere delle regioni."""
    if level != "regione":
        return name, False
    phrase = of_region(name)
    for prep, article in (("delle ", "le "), ("della ", "la "), ("dell'", "l'"), ("del ", "il ")):
        if phrase.startswith(prep):
            return article + name, prep == "delle "
    return name, False


def positions(steps: int) -> str:
    return f"{count_word(steps, feminine=True)} {'posizione' if steps == 1 else 'posizioni'}"


def movers(ranking: list[dict], level: str, denominator: str | None = None) -> dict:
    """Chi sale e chi scende di piu' rispetto al profilo Equilibrato.

    I pari merito si nominano tutti: "sale di piu'" su uno solo di tre che
    salgono delle stesse posizioni sarebbe falso. `denominator` e' come si
    chiude la posizione: "su 20 regioni" di norma, "su 20" dove la frase ha
    gia' detto di che territori parla, e allora non si ripete il nome.
    """
    plural = LEVELS[level]["plural"]
    total = len(ranking)
    short = denominator is not None
    denominator = denominator or f"su {total} {plural}"
    out = {}
    for kind, pick in (("up", max), ("down", min)):
        deltas = [r.get("delta_rank") or 0 for r in ranking]
        best = pick(deltas) if deltas else 0
        if (kind == "up" and best <= 0) or (kind == "down" and best >= 0):
            out[kind] = None
            continue
        tied = [r for r in ranking if (r.get("delta_rank") or 0) == best]
        one, many = ("sale", "salgono") if kind == "up" else ("scende", "scendono")
        steps = abs(best)
        if len(tied) == 1:
            r = tied[0]
            who, is_plural = subject(r["name"], level)
            text = (f"{many if is_plural else one} di più {who}, da {ordinal(r['rank'] + best)} a "
                    f"{ordinal(r['rank'])} {denominator}")
        elif len(tied) <= 3:
            who = join_names([subject(r["name"], level)[0] for r in tied])
            text = f"{many} di più, di {positions(steps)}, {who}"
        else:
            who = count_word(len(tied)) + ("" if short else f" {plural}")
            text = f"{who} {many} di {positions(steps)}"
        out[kind] = {"text": text, "names": [r["name"] for r in tied], "steps": steps}
    return out


# ---------------------------------------------------------------- dati dall'app

def scored_years(level: str, data: dict) -> dict | None:
    """Gli anni del dato piu' recente degli indicatori nel punteggio.

    `build_bes_ranking` non li restituisce: si leggono dalle stesse funzioni
    dell'app da cui il punteggio parte (memoizzate in `app.cache`). Si
    accettano solo se il numero degli indicatori e i conteggi di freschezza
    coincidono con la classifica, cosi' la pagina non mescola due letture dei
    dati. Se non coincidono, None: la pagina tace gli anni.
    """
    from app.external_data import count_freshness
    from app.quality_life_bes import _indicators_by_category, _matrix_and_meta

    _, meta = _matrix_and_meta(level)
    ids = [i for group in _indicators_by_category(level).values() for i in group]
    items = [meta[i] for i in ids if i in meta]
    method = data.get("methodology") or {}
    if len(items) != method.get("total_indicators") or count_freshness(meta.values()) != data.get("data_freshness"):
        return None
    years = Counter(int(item["year_max"]) for item in items if item.get("year_max"))
    if not years:
        return None
    return {"min": min(years), "max": max(years), "counts": sorted(years.items())}


def years_text(years: dict | None) -> str | None:
    """`dal 2023 al 2025`, oppure `del 2024` se l'anno e' uno solo."""
    if not years:
        return None
    if years["min"] == years["max"]:
        return f"del {years['min']}"
    return f"dal {years['min']} al {years['max']}"


def years_span(years: dict | None) -> str | None:
    """`2023-2025` per l'occhiello e la citazione."""
    if not years:
        return None
    return str(years["min"]) if years["min"] == years["max"] else f"{years['min']}-{years['max']}"


def source_ref(institutions: str, span: str | None) -> str:
    """`Istat ed Eurostat (2023-2025)`, o solo le istituzioni se gli anni mancano."""
    return f"{institutions} ({span})" if span else institutions


def profile_rankings(level: str, profiles: list[dict]) -> dict[str, list[dict]]:
    """La classifica di ogni profilo, dall'app (memoizzata in `app.cache`)."""
    from app.quality_life_bes import build_bes_ranking

    return {p["slug"]: (build_bes_ranking(level, p["slug"]) or {}).get("ranking") or [] for p in profiles}


# ---------------------------------------------------------------- pezzi condivisi

def measured_categories(data: dict) -> list[dict]:
    """Le dimensioni che a questo livello hanno dati, nell'ordine del sito."""
    present = data.get("category_rankings") or {}
    return [c for c in data.get("categories") or [] if c["slug"] in present]


def missing_categories(data: dict) -> list[dict]:
    present = data.get("category_rankings") or {}
    return [c for c in data.get("categories") or [] if c["slug"] not in present]


def profile_weights(profile: dict, categories: list[dict]) -> list[dict]:
    """I pesi del profilo ridistribuiti sulle sole dimensioni misurate, come
    fa `_final_raw` nell'app."""
    weights = profile.get("weights") or {}
    total = sum(weights.get(c["slug"], 0) for c in categories) or 1
    return [{"name": c["name"], "share": weights.get(c["slug"], 0) / total * 100} for c in categories]


def the_percent(value: float) -> str:
    """`il 10,0%`, `l'8,3%`: l'articolo si elide davanti a uno, undici, otto e
    ottanta."""
    digits = str(int(abs(value)))
    article = "l'" if digits in ("1", "11") or digits.startswith("8") else "il "
    return article + with_unit(value, "%")


def weights_text(profile: dict, categories: list[dict]) -> str | None:
    rows = profile_weights(profile, categories)
    if not rows:
        return None
    shares = {round(r["share"], 6) for r in rows}
    n = len(rows)
    if len(shares) == 1:
        return f"Ognuna delle {n} dimensioni pesa {the_percent(rows[0]['share'])}."
    ordered = sorted(rows, key=lambda r: -r["share"])
    parts = [f"{lower_first(r['name'])} {with_unit(r['share'], '%')}" for r in ordered]
    return "Pesi sulle " + str(n) + " dimensioni, dal più alto: " + ", ".join(parts) + "."


def breakdown(data: dict) -> list[dict]:
    """Da dove vengono gli indicatori: famiglia di fonti con il nome del
    registro `app.sources`, mai l'etichetta interna."""
    method = data.get("methodology") or {}
    out = []
    for item in method.get("source_breakdown") or []:
        family = item.get("family")
        label = sources.family_label(family) if family in sources.SOURCES else item.get("label")
        if label and item.get("count") is not None:
            out.append({"label": label, "count": item["count"]})
    return out


def category_table(data: dict, level: str, top: int = 3) -> list[dict]:
    """Dove eccelle ogni territorio: per ogni dimensione i primi `top` e l'ultimo."""
    spec = LEVELS[level]
    rankings = data.get("category_rankings") or {}

    def cell(entry):
        return {"name": entry["territory"], "href": spec["profile"] + entry["key"], "score": entry["score"]}

    out = []
    for cat in measured_categories(data):
        block = rankings[cat["slug"]]
        out.append({
            "name": cat["name"], "href": safe_category_path(cat["slug"]),
            "top": [cell(e) for e in (block.get("top") or [])[:top]],
            "last": cell(block["bottom"][0]) if block.get("bottom") else None,
        })
    return out


def category_leaders(data: dict) -> dict[str, list[dict]]:
    """Chi ha il punteggio piu' alto in ogni dimensione, con i pari merito.

    `champions` dell'app ne tiene uno solo anche quando due territori hanno lo
    stesso punteggio pubblicato (Istruzione e formazione, 65,0 e 65,0): qui si
    tengono tutti, perche' la pagina mostra i punteggi e il lettore li vede.
    """
    out = {}
    for slug, block in (data.get("category_rankings") or {}).items():
        top = block.get("top") or []
        if top:
            out[slug] = [e for e in top if e["score"] == top[0]["score"]]
    return out


def champions_claim(data: dict, level: str) -> str | None:
    """Il titolo-affermazione di "dove eccelle": chi ha il punteggio piu' alto
    in piu' dimensioni, contando i pari merito."""
    leaders_by_dim = category_leaders(data)
    if not leaders_by_dim:
        return None
    counts = Counter(e["territory"] for group in leaders_by_dim.values() for e in group)
    best = max(counts.values())
    leaders = [name for name, c in counts.items() if c == best]
    total = len(leaders_by_dim)
    spec = LEVELS[level]
    if best == 1:
        return f"Ognuna delle {total} dimensioni ha una {spec['singular']} diversa in testa"
    dims = f"{count_word(best, feminine=True)} dimensioni su {total}"
    if len(leaders) == 1:
        who, is_plural = subject(leaders[0], level)
        others = sorted({c for n, c in counts.items() if n != leaders[0]}, reverse=True)
        tail = ""
        if others:
            tail = f", nessun'altra {spec['singular']} in più di {count_word(others[0], feminine=True)}"
        verb = "hanno" if is_plural else "ha"
        return f"{who[:1].upper() + who[1:]} {verb} il punteggio più alto in {dims}{tail}"
    who = join_names([subject(n, level)[0] for n in leaders])
    dims = f"{count_word(best, feminine=True)} dimensioni ciascuna su {total}"
    return f"{who[:1].upper() + who[1:]} hanno il punteggio più alto in {dims}"


def south_split(ranking: list[dict], level: str, paths: dict) -> dict:
    """Centro-Nord e Mezzogiorno: quante righe, che media semplice del punteggio."""
    groups = {"north": [], "south": [], "unknown": []}
    for row in ranking:
        flag = is_south(row, level, paths)
        groups["unknown" if flag is None else ("south" if flag else "north")].append(row)
    return {
        k: {"rows": v, "n": len(v), "mean": statistics.fmean(r["score"] for r in v) if v else None}
        for k, v in groups.items()
    }


def south_claim(ranking: list[dict], level: str, paths: dict) -> str | None:
    """Il titolo-affermazione della classifica, verificato sulle righe."""
    spec = LEVELS[level]
    groups = south_split(ranking, level, paths)
    if groups["unknown"]["n"] or not groups["south"]["n"]:
        return None
    south_keys = {r["key"] for r in groups["south"]["rows"]}
    k = len(south_keys)
    if level == "regione":
        if {r["key"] for r in ranking[-k:]} == south_keys:
            return f"Le {count_word(k)} regioni del Mezzogiorno occupano le ultime {count_word(k)} posizioni"
        below = [r for r in groups["south"]["rows"] if r["score"] < 50]
        if not below:
            return None
        verb = "sta" if len(below) == 1 else "stanno"
        return f"{count_word(len(below)).capitalize()} regioni del Mezzogiorno su {count_word(k)} {verb} sotto 50"
    if len(ranking) < 2 * EDGE:
        return None
    tail = sum(r["key"] in south_keys for r in ranking[-EDGE:])
    head = sum(r["key"] in south_keys for r in ranking[:EDGE])
    if tail == EDGE:
        text = f"Le ultime {count_word(EDGE)} {spec['plural']} sono tutte del Mezzogiorno"
    elif tail == 0:
        text = f"Nessuna delle ultime {count_word(EDGE)} {spec['plural']} è del Mezzogiorno"
    else:
        verb = "è" if tail == 1 else "sono"
        text = f"{count_word(tail).capitalize()} delle ultime {count_word(EDGE)} {spec['plural']} {verb} del Mezzogiorno"
    if head == 0:
        return text + f", nessuna fra le prime {count_word(EDGE)}"
    return text + f", {count_word(head)} fra le prime {count_word(EDGE)}"


def map_block(ranking: list[dict]) -> dict | None:
    """Classi, nomi, valori e legenda della mappa regionale.

    I gradini sono quelli di tutte le mappe (`choropleth_scale`): uguali di
    norma, quantili quando un punteggio fuori scala schiaccerebbe gli altri.
    """
    scored = {r["key"]: r["score"] for r in ranking if r.get("score") is not None}
    if not scored:
        return None
    classes = {k: f"q{step}" for k, step in common.map_steps(scored).items()}
    scale = choropleth_scale(list(scored.values()))
    lo, hi = scale["lo"], scale["hi"]
    mid = scale["median"] if scale["mode"] == "quantile" else lo + (hi - lo) / 2
    first, last = ranking[0], ranking[-1]
    # I due estremi nominati sulla mappa, con il filo dal baricentro.
    callouts = charts.map_callouts(PATHS, [(r["key"], r["name"], f"{points(r['score'])} punti")
                                           for r in (first, last)])
    return {
        "classes": classes,
        "names": {r["key"]: r["name"] for r in ranking},
        "tips": {r["key"]: f"{points(r['score'])} punti" for r in ranking},
        "legend": {"min": points(lo), "mid": points(mid), "max": points(hi), "unit": None, "mode": scale["mode"]},
        "callouts": callouts,
    }


def display_spread() -> str:
    """Quanti punti della scala 0-100 vale una deviazione standard, dall'app."""
    from app.quality_life_bes import _DISPLAY_SPREAD

    value = float(_DISPLAY_SPREAD)
    return numfmt.text(value, 0 if value.is_integer() else None)


def score_strip(ranking: list[dict]) -> dict:
    """La striscia dei punteggi: ogni territorio un punto nel colore della sua
    ripartizione, la distanza fra primo e ultimo in punti, la media semplice
    con il decimale dei punteggi."""
    areas = charts.area_map()
    rows = [{"key": r["key"], "name": r["name"], "value": r["score"], "area": areas.get(r["key"])}
            for r in ranking if r.get("score") is not None]
    if len(rows) < 2:
        return {"svg": "", "legend": []}
    scores = [r["value"] for r in rows]
    avg = statistics.fmean(scores)
    return charts.divario_strip(rows, avg, None,
                                gap_label=f"{points(max(scores) - min(scores))} punti",
                                avg_label=f"Media semplice {points(avg)}")


def group_mean_tiles(groups: dict, spec: dict) -> list[dict]:
    """Le medie semplici di Centro-Nord e Mezzogiorno: la striscia le colora ma
    non le dice."""
    if not (groups["north"]["n"] and groups["south"]["n"]) or groups["unknown"]["n"]:
        return []
    return [
        {"label": "Media semplice del Centro-Nord", "value": groups["north"]["mean"], "unit": "punti",
         "role": "score", "sub": f"{groups['north']['n']} {spec['plural']}"},
        {"label": "Media semplice del Mezzogiorno", "value": groups["south"]["mean"], "unit": "punti",
         "role": "score", "sub": f"{groups['south']['n']} {spec['plural']}"},
    ]


def count_tile(label: str, value, sub: str | None) -> dict | None:
    """Una tessera di conteggio, o None se il conteggio manca: la tessera si
    toglie, non si scrive "n.d."."""
    if value is None:
        return None
    return {"label": label, "value": value, "unit": None, "role": "count", "sub": sub}


def dimensions_claim(ranking: list[dict], level: str) -> str | None:
    """Il titolo-affermazione della tabella, dalle due colonne che mostra: la
    dimensione che e' piu' spesso il punto forte, e per quanti altri territori
    e' il punto debole. Con un pari merito in testa non si afferma niente."""
    spec = LEVELS[level]

    def first_name(row, key):
        return ((row.get(key) or [None])[0] or {}).get("name")

    strong = Counter(first_name(r, "strongest_categories") for r in ranking)
    weak = Counter(first_name(r, "weakest_categories") for r in ranking)
    strong.pop(None, None)
    if not strong:
        return None
    top = max(strong.values())
    leaders = [name for name, c in strong.items() if c == top]
    if len(leaders) != 1 or top < 2:
        return None
    dim, others = leaders[0], weak.get(leaders[0], 0)
    # Dove la prima e la seconda dimensione hanno lo stesso punteggio la scelta
    # dell'app e' arbitraria: se il pari merito tocca la dimensione del titolo,
    # il conteggio non e' un fatto e il titolo non si scrive.
    for row in ranking:
        for key in ("strongest_categories", "weakest_categories"):
            cats = row.get(key) or []
            tied = [c["name"] for c in cats if cats and c.get("score") == cats[0].get("score")]
            if len(tied) > 1 and dim in tied:
                return None
    k = count_word(top)
    if others:
        return f"{dim} è il punto forte di {k} {spec['plural']} e il punto debole di altre {count_word(others)}"
    return f"{dim} è il punto forte più frequente, di {k} {spec['plural']} su {len(ranking)}"


def mean_is_fifty(ranking: list[dict]) -> bool:
    """Il 50 e' la media solo se lo e' davvero: si controlla sulle righe."""
    scores = [r["score"] for r in ranking if r.get("score") is not None]
    return bool(scores) and abs(statistics.fmean(scores) - 50) < 0.5


def end(row: dict | None, level: str) -> dict | None:
    """Un estremo della classifica per la risposta: preposizione, nome, link, punteggio."""
    if not row:
        return None
    phrase = of_place(row["name"], level)
    return {"prep": split_prep(phrase, row["name"]), "name": row["name"],
            "href": LEVELS[level]["profile"] + row["key"], "score": row["score"]}


# ---------------------------------------------------------------- la pagina

def derive(ctx: dict) -> dict:
    data = ctx["data"]
    level = data["level"]
    spec = LEVELS[level]
    ranking = data.get("ranking") or []
    paths = ctx.get("region_paths") or {}
    method = data.get("methodology") or {}
    profile = data["profile"]
    default = ctx.get("default_profile") or "standard"
    active = ctx.get("active_profile") or profile["slug"]
    is_default = active == default
    n = len(ranking)
    first, last = (ranking[0], ranking[-1]) if ranking else (None, None)

    years = scored_years(level, data)
    categories = measured_categories(data)
    missing = missing_categories(data)
    groups = south_split(ranking, level, paths)
    fifty = mean_is_fifty(ranking)
    institutions = method.get("catalog_institutions") or "Istat"

    move = None if is_default else movers(ranking, level)
    default_name = next((p["name"] for p in ctx.get("profiles") or [] if p["slug"] == default), "Equilibrato")

    # La striscia dice estremi, media e distanza: le tessere dicono le medie
    # delle due parti del paese, che la striscia colora ma non scrive.
    tiles = group_mean_tiles(groups, spec)
    count = count_tile("Indicatori nel punteggio", method.get("total_indicators"),
                       f"in {len(categories)} dimensioni" if categories else None)
    if count:
        tiles.append(count)

    levels = [{"label": LEVELS[k]["label"], "href": profile_href(k, active, default), "current": k == level}
              for k in ("regione", "provincia")]
    profile_links = [{"name": p["name"], "href": profile_href(level, p["slug"], default), "current": p["slug"] == active}
                     for p in ctx.get("profiles") or []]

    dims_note = dims_short = None
    if missing and categories:
        names = join_names([f"su {lower_first(c['name'])}" for c in missing])
        dims_note = (f"Per le {spec['plural']} mancano i dati {names}: "
                     f"i pesi si ridistribuiscono sulle altre {count_word(len(categories), feminine=True)} dimensioni.")
        dims_short = (f"Per le {spec['plural']} le dimensioni con dati sono "
                      f"{count_word(len(categories), feminine=True)}.")

    unmeasured = ctx.get("unmeasured_provinces") or []
    coverage = None
    if level == "provincia" and n:
        coverage = f"{n} {spec['plural']}, tutte quelle coperte dagli indicatori usati qui."
        if unmeasured:
            coverage += (f" Nella codifica Istat ci sono anche {join_names(list(unmeasured))}, "
                         "che questi indicatori non coprono ancora.")
        coverage += " Le vecchie province sarde soppresse sono escluse."

    rows = table_rows(ranking, level, paths, with_delta=not is_default)
    other = next(k for k in LEVELS if k != level)
    h1 = f"Qualità della vita nelle {spec['plural']} italiane: la classifica con il profilo {profile['name']}"
    title = f"Qualità della vita nelle {spec['plural']} italiane, profilo {profile['name']}"
    span = years_span(years)
    ref = source_ref(institutions, span)
    return {
        "level": level, "spec": spec, "n": n, "is_default": is_default, "default_name": default_name,
        "h1": h1,
        "institutions": institutions, "years": years, "years_text": years_text(years), "years_span": span,
        "source_ref": ref,
        "first": end(first, level), "last": end(last, level),
        "gap": (first["score"] - last["score"]) if first else None,
        "movers": move, "fifty": fifty, "tiles": tiles,
        "claim": south_claim(ranking, level, paths),
        "strip": score_strip(ranking), "area_label": charts.AREA_LABEL,
        "table_claim": dimensions_claim(ranking, level),
        "levels": levels, "profiles": profile_links, "profile": profile,
        "dims_total": len(categories), "dims_note": dims_note, "dims_short": dims_short,
        "rows": split(rows, spec["plural"]),
        "spread": display_spread(),
        "map": map_block(ranking) if level == "regione" and ranking else None,
        "categories": category_table(data, level), "champions_claim": champions_claim(data, level),
        "weights": weights_text(profile, categories),
        "breakdown": breakdown(data),
        "year_counts": [{"year": y, "n": c} for y, c in reversed((years or {}).get("counts", []))],
        "coverage": coverage, "unrated": [u["name"] for u in data.get("unrated") or []],
        "downloads": downloads(level, active, default),
        "other_level": LEVELS[other],
        "other_level_href": profile_href(other, active, default),
        "citation": f"Divario Italia, «{title}», elaborazione su dati {ref}. {ctx.get('canonical') or ''}".rstrip(),
    }
