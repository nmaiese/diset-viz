"""La pagina regione della 1.0: cifre e frasi composte dal profilo vero.

Il contesto della rotta /regione/<key> porta il profilo della regione (posizione
media, temi, indicatori, movimenti, regioni simili) e le sue province. La
qualita' della vita delle regioni e la scala delle province non ci sono: si
chiedono alle classifiche della qualita' della vita del profilo predefinito
(`quality_life_bes.build_bes_ranking`), le stesse delle pagine
/qualita-della-vita/classifica/<livello>. Se una classifica manca o non
contiene la regione, la figura d'apertura, la scala o il denominatore
spariscono invece di diventare cifre inventate.

Le classifiche si leggono una volta per processo, come i loader dei dati: in
produzione `build_bes_ranking` e' memoizzato, ma la cache semplice ridà una
copia deserializzata a ogni lettura, e la pagina non deve rifare questo lavoro
a ogni richiesta. Tutto cio' che esce dalle cache di questo modulo e' condiviso
fra le richieste e non si modifica: chi ne vuole una versione diversa ne fa una
copia.

Qui le cifre restano grezze: le scrivono i filtri `num`, `rank` e `delta` nel
template. Le frasi composte qui (il titolo della figura, le etichette della
striscia) passano da `common.num`, e i conteggi da `numfmt.text(n, 0)`, perche'
`common.num(20)` scriverebbe "20,0".
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from app import quality_life_bes as qb
from app.data import REGION_GEO_AREA
from app.design import charts, common, numfmt
from app.indicator_notes import is_percentage_unit
from app.profiles import MIN_THEME_INDICATORS
from app.seo_titles import of_region
from app.taxonomy import CATEGORY_NAME_TO_SLUG, MACRO_AREAS

DIRECTION_WORDS = {
    "higher_better": "meglio se alto",
    "lower_better": "meglio se basso",
    "higher_worse": "meglio se basso",
}
QUALITY_PATH = "/qualita-della-vita/classifica/regioni"


def _scale(methodology: dict | None) -> dict | None:
    """Minimo, massimo e centro della scala del punteggio, letti dal metodo.

    La classifica dichiara la scala in una frase ("display 0-100 con media 50"):
    la si legge da li' invece di riscriverla, cosi' se cambia cambia anche qui.
    """
    m = re.search(r"(\d+)-(\d+) con media (\d+)", (methodology or {}).get("normalization") or "")
    if not m:
        return None
    lo, hi, mid = (int(x) for x in m.groups())
    if hi <= lo:
        return None
    return {"min": lo, "max": hi, "mid": mid}


def _divbar(score, scale: dict | None) -> dict | None:
    """La barra attorno al centro della scala: da dove parte e quanto e' lunga, in percentuale."""
    if score is None or not scale:
        return None
    span = (scale["max"] - scale["min"]) or 1
    return {"left": round((min(score, scale["mid"]) - scale["min"]) / span * 100, 1),
            "width": round(abs(score - scale["mid"]) / span * 100, 1)}


def _unit(unit: str | None) -> str:
    """L'unita' come va accanto alla cifra: la percentuale diventa %, il resto
    resta com'e' nella fonte. `numfmt.short_unit` non riconosce "percentuale"."""
    unit = (unit or "").strip()
    return "%" if unit and is_percentage_unit(unit) else unit


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


def _track(rank, total) -> float | None:
    """Dove cade una posizione sulla traccia da 1 a N, in percentuale."""
    return round((rank - 1) / (total - 1) * 100, 1) if rank and total and total > 1 else None


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]


def _verbs(name: str) -> dict[str, str]:
    """"la Puglia e'" ma "le Marche sono": verbi, pronome e possessivo seguono
    il numero della regione."""
    plural = of_region(name).startswith("delle ")
    return {"is": "sono" if plural else "è", "stays": "stanno" if plural else "sta",
            "goes": "vanno" if plural else "va", "obj": "le" if plural else "la",
            "poss": "loro" if plural else "suo"}


@lru_cache(maxsize=1)
def _theme_order() -> dict[str, int]:
    """L'ordine dei temi della tassonomia, macro-area per macro-area."""
    slugs = [slug for area in MACRO_AREAS.values() for slug in area]
    return {name: slugs.index(slug) for name, slug in CATEGORY_NAME_TO_SLUG.items() if slug in slugs}


# ---------------------------------------------------------------- qualita' della vita

@lru_cache(maxsize=1)
def _region_quality() -> dict | None:
    """La classifica regionale della qualita' della vita, profilo predefinito, una volta per processo.

    Le sole cose che la pagina ne usa: le righe con un punteggio in ordine di
    posizione, la media semplice, la scala, il nome del profilo, il numero di
    dimensioni e la fonte. None se la classifica non c'e' o ha meno di due
    regioni: un None resta per la vita del processo, come un dato che manca ai
    loader, e la pagina toglie la figura.
    """
    payload = qb.build_bes_ranking("regione", qb.DEFAULT_PROFILE)
    if not payload:
        return None
    rows = sorted(
        ({"key": r["key"], "name": r["name"], "rank": r["rank"], "score": r["score"]}
         for r in payload.get("ranking") or []
         if r.get("key") and r.get("rank") is not None and r.get("score") is not None),
        key=lambda r: r["rank"],
    )
    if len(rows) < 2:
        return None
    methodology = payload.get("methodology") or {}
    return {
        "rows": tuple(rows),
        "ranks": {r["key"]: r["rank"] for r in rows},
        "mean": sum(r["score"] for r in rows) / len(rows),
        "scale": _scale(methodology),
        "profile": ((payload.get("profile") or {}).get("name") or "").lower() or None,
        "dimensions": len(payload.get("categories") or []) or None,
        "source": methodology.get("source") or None,
    }


@lru_cache(maxsize=1)
def _province_quality() -> dict:
    """Della classifica provinciale servono solo il numero delle province, la
    scala e il nome del profilo: le posizioni delle province della regione le
    porta gia' la view (`province_profile.by_region`), dalla stessa classifica."""
    payload = qb.build_bes_ranking("provincia", qb.DEFAULT_PROFILE) or {}
    return {
        "total": len(payload.get("ranking") or []) or None,
        "scale": _scale(payload.get("methodology")),
        "profile": ((payload.get("profile") or {}).get("name") or "").lower() or None,
    }


def _quality_claim(the_name: str, is_: str, row: dict, ranking: tuple[dict, ...], mean: float) -> str:
    """Il titolo della figura d'apertura: un fatto sulla posizione, verificato
    sulla classifica. Nomina chi sta dietro o davanti solo quando sono pochi,
    con l'articolo: "davanti solo alla Calabria e alla Sicilia"."""
    total = len(ranking)
    rank = row["rank"]
    head = f"Qualità della vita: {the_name} {is_}"
    of_total = numfmt.text(total, 0)
    if rank == 1:
        return f"{head} al primo posto fra le {of_total} regioni"
    if rank == total:
        return f"{head} all'ultimo posto fra le {of_total} regioni"
    lead = f"{head} {common.ordinal(rank)} su {of_total}"
    after = [_article(r["name"], "a") for r in ranking if r["rank"] > rank]
    ahead = [_article(r["name"], "a") for r in ranking if r["rank"] < rank]
    if after and len(after) <= 3:
        return f"{lead}, davanti solo {_join(after)}"
    if ahead and len(ahead) <= 3:
        return f"{lead}, dietro solo {_join(ahead)}"
    if row["score"] == mean:
        return lead
    return f"{lead}, {'sopra' if row['score'] > mean else 'sotto'} la media delle regioni"


@lru_cache(maxsize=32)
def _quality(key: str, name: str) -> dict | None:
    """La qualita' della vita delle regioni con questa in evidenza: la striscia
    d'apertura, il suo titolo e la tabella con gli stessi dati. None se la
    regione non e' nella classifica."""
    base = _region_quality()
    if not base:
        return None
    ranking = base["rows"]
    row = next((r for r in ranking if r["key"] == key), None)
    if not row:
        return None
    scale, mean = base["scale"], base["mean"]
    areas = charts.area_map()
    scores = [r["score"] for r in ranking]
    gap = max(scores) - min(scores)
    strip = charts.divario_strip(
        [{"key": r["key"], "name": r["name"], "value": r["score"], "area": areas.get(r["key"])} for r in ranking],
        mean, None, highlight=key,
        gap_label=f"{common.num(gap)} punti fra prima e ultima",
        avg_label=f"Media delle regioni {common.num(mean)}",
    )
    rows = [{"rank": r["rank"], "key": r["key"], "name": r["name"], "score": r["score"],
             "area": areas.get(r["key"]), "area_label": charts.AREA_LABEL.get(areas.get(r["key"])),
             "bar": _divbar(r["score"], scale), "on": r["key"] == key}
            for r in ranking]
    return {
        "rank": row["rank"], "total": len(ranking), "score": row["score"], "mean": mean,
        "scale": scale, "strip": strip, "rows": rows,
        "claim": _quality_claim(_article(name), _verbs(name)["is"], row, ranking, mean),
        "profile": base["profile"], "dimensions": base["dimensions"], "source": base["source"],
        "path": QUALITY_PATH,
    }


# ---------------------------------------------------------------- profilo

def _indicator_row(ind: dict, region_total: int | None) -> dict:
    rank, count = ind.get("rank"), ind.get("region_count")
    movement = ind.get("movement")
    before = None
    if rank is not None and movement is not None and ind.get("year_from") and region_total:
        # L'anno di confronto e' per costruzione uno con i dati di tutte le
        # regioni (`_core_stats`): il suo denominatore e' il totale, anche
        # quando l'ultimo anno ne copre meno.
        before = {"rank": rank + movement, "total": region_total, "year": ind["year_from"], "same": movement == 0}
    unit = _unit(ind.get("unit"))
    return {
        "id": ind.get("id"), "name": ind.get("name"), "path": ind.get("path"), "theme": ind.get("theme"),
        "value": ind.get("value"), "unit": unit,
        # L'unita' troppo lunga per stare accanto alla cifra si scrive a parte.
        "unit_apart": unit if unit and numfmt.short_unit(unit) is None else None,
        "year": ind.get("year"),
        "rank": rank, "count": count, "track": _track(rank, count),
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
    rated = [t for t in profile.get("theme_table") or [] if t.get("rank") and t.get("theme_path")]
    strong = min(rated, key=lambda t: (t["rank"], -(t.get("score") or 0)), default=None)
    weak = max(rated, key=lambda t: (t["rank"], -(t.get("score") or 0)), default=None)
    top = (profile.get("themes_strong") or [{}])[0]
    out = {"strong": None, "weak": None, "netto": bool(top.get("netto"))}
    if strong:
        out["strong"] = {"theme": strong["theme"], "path": strong["theme_path"],
                         "rank": strong["rank"], "total": strong.get("rank_total") or total}
    if weak and weak is not strong:
        out["weak"] = {"theme": weak["theme"], "path": weak["theme_path"],
                       "rank": weak["rank"], "total": weak.get("rank_total") or total}
    return out


def _areas(indicators: list[dict], theme_paths: dict[str, str], total: int | None) -> list[dict]:
    """Tutti gli indicatori per macro-area, e dentro per tema nell'ordine della
    tassonomia. Dentro il tema, dalla posizione migliore alla peggiore."""
    order = _theme_order()
    rows_ok = [i for i in indicators if i.get("name") and i.get("path")]
    known = set(MACRO_AREAS)
    names = list(MACRO_AREAS) + sorted({i.get("macro_area") or "Altro" for i in rows_ok} - known)
    areas = []
    for area in names:
        rows = [i for i in rows_ok if (i.get("macro_area") or "Altro") == area]
        if not rows:
            continue
        groups = []
        for theme in sorted({i.get("theme") or "" for i in rows}, key=lambda t: (order.get(t, 99), t)):
            items = sorted((i for i in rows if (i.get("theme") or "") == theme),
                           key=lambda i: (i.get("rank") is None, i.get("rank") or 0, i["name"]))
            groups.append({"theme": theme or "Altri indicatori", "path": theme_paths.get(theme),
                           "rows": [_indicator_row(i, total) for i in items]})
        plain = unicodedata.normalize("NFKD", area.lower()).encode("ascii", "ignore").decode()
        areas.append({"name": area, "slug": re.sub(r"[^a-z]+", "-", plain).strip("-"),
                      "count": len(rows), "groups": groups})
    return areas


def derive(ctx: dict) -> dict:
    p = ctx["profile"]
    key, name = p["region_key"], p["region"]
    total = p.get("region_total")
    indicators = list(p.get("all_indicators") or [])
    by_id = {i["id"]: i for i in indicators if i.get("id")}
    the_name = _article(name)

    quality = _quality(key, name)
    base = _region_quality()
    qranks = base["ranks"] if base else {}
    pq = _province_quality()
    province_total, pscale = pq["total"], pq["scale"]

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
            "theme": t["theme"], "path": t.get("theme_path"), "count": t.get("count"), "rated": t.get("rated"),
            "rank": rank, "total": n, "track": _track(rank, n),
            "percentile": t["score"] * 100 if t.get("score") is not None else None,
        })

    # Dove stacca e dove resta indietro: gli indicatori del profilo con i
    # valori veri, presi dalla tabella completa per id.
    def picks(items):
        return [_indicator_row(by_id[e["id"]], total) for e in items if e.get("id") in by_id]

    excels, lags = picks(p.get("top_excels") or []), picks(p.get("top_lags") or [])

    gains = [_indicator_row(i, total) for i in (p.get("movement_gains") or [])[:4]]
    losses = [_indicator_row(i, total) for i in (p.get("movement_losses") or [])[:4]]
    moved_up = sum(1 for i in indicators if (i.get("movement") or 0) > 0)
    moved_down = sum(1 for i in indicators if (i.get("movement") or 0) < 0)
    moved_same = sum(1 for i in indicators if i.get("movement") == 0)

    # Le ultime cinque posizioni con lo stesso criterio di `top5_count` in
    # app/profiles.py: solo gli indicatori con i dati di tutte le regioni.
    comparable = [i["rank"] for i in indicators if i.get("rank") is not None and i.get("region_count") == total]
    bottom5 = sum(1 for r in comparable if total and r > total - 5) if comparable else None
    bottom5_share = bottom5 / len(comparable) * 100 if comparable else None

    # Le province per qualita' della vita, dalla prima all'ultima. Copie: le
    # righe della view vengono da una classifica memoizzata.
    provinces = [{**pr, "bar": _divbar(pr.get("score"), pscale)}
                 for pr in sorted(ctx.get("provinces") or [], key=lambda r: (r.get("rank") is None, r.get("rank") or 0))]

    theme_paths = {t["theme"]: t.get("theme_path") for t in p.get("theme_table") or []}
    areas = _areas(indicators, theme_paths, total)

    area_of = charts.area_map()
    similar = []
    for s in p.get("similar_regions") or []:
        if not s.get("region_key") or not s.get("region"):
            continue
        similar.append({"name": s["region"], "key": s["region_key"], "path": f"/regione/{s['region_key']}",
                        "geo": REGION_GEO_AREA.get(s["region_key"]), "area": area_of.get(s["region_key"]),
                        "q_rank": qranks.get(s["region_key"]), "q_total": len(qranks) or None})

    institutions = list(dict.fromkeys(s["label"].split(",")[0].strip() for s in sources))
    institution = " e ".join(institutions) if institutions else None
    year_min, year_max = (years[0], years[-1]) if years else (None, None)
    span = f" ({year_min}-{year_max})" if year_min and year_max and year_min != year_max else (f" ({year_max})" if year_max else "")
    on_data = f", elaborazione su dati {institution}" if institution else ""
    citation = f"Divario Italia, «Il profilo {of_region(name)}»{on_data}{span}. {ctx.get('canonical') or ''}".rstrip()

    best = excels[0] if excels else None
    best_pick = ({**best, "name_lc": _lower_first(best["name"])}
                 if best and best.get("rank") and best.get("value") is not None else None)

    geo = p.get("geo_area")
    return {
        "name": name, "key": key, "geo": geo, "area": area_of.get(key), "total": total,
        "area_in": ("nelle " if geo == "Isole" else "nel ") + geo if geo else None,
        "the_name": the_name, "to_name": _article(name, "a"), "of_name": of_region(name),
        "verb": _verbs(name),
        "institution": institution,
        "avg_rank": p.get("avg_rank"),
        "comparable": p.get("comparable_count"), "top5": p.get("top5_count"), "bottom5": bottom5, "bottom5_share": bottom5_share,
        "scored": p.get("scored_count"),
        "indicator_count": len(indicators), "contextual_count": sum(1 for i in indicators if i.get("rank") is None),
        "year_min": year_min, "year_max": year_max, "sources": sources,
        "answer": _answer(p), "best_pick": best_pick, "quality": quality, "themes": themes,
        "excels": excels, "lags": lags,
        "gains": gains, "losses": losses, "moved_up": moved_up, "moved_down": moved_down, "moved_same": moved_same,
        "provinces": provinces, "province_total": province_total,
        "province_profile": pq["profile"],
        "province_scale": pscale,
        "areas": areas, "similar": similar,
        "min_theme": MIN_THEME_INDICATORS, "citation": citation,
        "count_word": common.count_word,
    }
