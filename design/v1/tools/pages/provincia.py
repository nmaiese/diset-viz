"""Le frasi e le cifre nuove della pagina provincia della 1.0.

Tutto parte dal contesto catturato dalla rotta `/provincia/<key>`: il profilo
della qualita' della vita (`profile`), i valori veri degli indicatori
(`indicatori`), le vicine in classifica e le sorelle della stessa regione. Qui
si contano e si mettono in ordine le cose; i valori della fonte restano numeri
e li scrive il template con `it_num` e `it_change`, con i decimali della fonte,
gli stessi che le prove della pagina di oggi fissano.

Le cifre calcolate qui (punteggi, scarti da 50, conteggi) passano da
`derive.num` (qui `common.num`), cioe' da `seo_titles.format_number`.
"""

from __future__ import annotations

import derive as common

from app import it_numbers, sources
from app.seo_titles import at_place, of_region
from app.taxonomy import CANONICAL_CATEGORIES, slugify_taxonomy


def _plain_id(ident: str) -> str:
    """`bes:12SER022` -> `12SER022`: il profilo porta il prefisso della
    famiglia, la tabella degli indicatori no."""
    return ident.split(":", 1)[1] if ":" in ident else ident


def _join(names: list[str]) -> str:
    """"A", "A e B", "A, B e C"."""
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]


def _score(value: float) -> str:
    """Un punteggio 0-100 in colonna: un decimale sempre, come nel dato.

    `common.num` calibra i decimali sulla grandezza e scriverebbe 0,50 accanto
    a 5,9, e una colonna di punteggi vuole i decimali uniformi (SISTEMA.md).
    Stessa funzione del filtro `it_num`."""
    return it_numbers.number(value, 1)


def _signed_score(value: float) -> str:
    """Lo scarto da 50 col segno, un decimale; lo zero senza segno."""
    value = round(value, 1)
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return sign + it_numbers.number(abs(value), 1)


def _source_label(methodology: dict) -> str:
    """L'etichetta pubblica della fonte, da `app/sources.py` e da nessun altro
    posto: "Istat, benessere e qualita' della vita", mai la sigla interna."""
    families = [f for f in (methodology.get("source_counts") or {}) if f in sources.SOURCES]
    if not families:
        raise LookupError(f"nessuna famiglia di fonti nota nel metodo: {methodology.get('source_counts')!r}")
    return _join([sources.family_label(f) for f in families])


def _share(row: dict) -> float:
    """La posizione relativa, perche' il denominatore cambia da riga a riga."""
    return row["rank"] / (row.get("province_count") or 1)


def _dimensions(profile: dict) -> dict:
    """Le dimensioni misurate, con la barra divergente attorno a 50 sulla scala
    fissa 0-100: la stessa scala per tutte le province, cosi' due pagine si
    confrontano a occhio."""
    rows = []
    for cat in profile.get("categories") or []:
        score = cat["score"]
        diff = score - 50
        rows.append({
            "name": cat["name"],
            "slug": cat["slug"],
            "score": _score(score),
            "diff": _signed_score(diff),
            "left": round(min(score, 50), 1),
            "width": round(abs(diff), 1),
        })
    measured = {cat["slug"] for cat in profile.get("categories") or []}
    weights = (profile.get("profile") or {}).get("weights") or {}
    missing = [CANONICAL_CATEGORIES[slug]["name"] for slug in weights
               if slug not in measured and slug in CANONICAL_CATEGORIES]
    above = [c for c in profile.get("categories") or [] if c["score"] > 50]
    n, total = len(rows), profile.get("total")
    if not rows:
        claim = None
    elif not above:
        claim = f"Nessuna delle {n} dimensioni supera la media delle {total} province"
    elif len(above) == n:
        claim = f"Tutte le {n} dimensioni stanno sopra la media delle {total} province"
    elif len(above) == 1:
        claim = f"{above[0]['name']} è l'unica delle {n} dimensioni sopra la media delle {total} province"
    else:
        claim = f"{len(above)} dimensioni su {n} stanno sopra la media delle {total} province"
    lead = ("Manca una dimensione del profilo," if len(missing) == 1
            else f"Mancano {common.count_word(len(missing), feminine=True)} dimensioni del profilo,")
    return {"rows": rows, "count": n, "missing": missing, "missing_text": _join([f"«{m}»" for m in missing]),
            "missing_lead": lead, "claim": claim}


def _synthesis(ctx: dict, by_id: dict) -> dict:
    """Una sintesi sola al posto delle tre coppie di oggi.

    Da una parte gli indicatori che alzano di piu' il punteggio e quelli in cui
    la provincia e' la prima fra le province della sua regione, dall'altra gli
    indicatori che lo abbassano di piu' e quelli in cui e' l'ultima. Ogni
    indicatore compare una volta sola: le liste del punteggio decidono il lato,
    quelle della regione aggiungono solo cio' che manca.
    """
    profile = ctx["profile"]
    pos_ids = [_plain_id(x["id"]) for x in profile.get("top_positive") or []]
    neg_ids = [_plain_id(x["id"]) for x in profile.get("top_negative") or []]
    first_ids = [x["id"] for x in ctx.get("prime_in_regione") or []]
    last_ids = [x["id"] for x in ctx.get("ultime_in_regione") or []]

    strong, weak = [], []
    for ident in pos_ids + [i for i in first_ids if i not in neg_ids]:
        if ident in by_id and ident not in strong:
            strong.append(ident)
    for ident in neg_ids + [i for i in last_ids if i not in pos_ids]:
        if ident in by_id and ident not in weak and ident not in strong:
            weak.append(ident)
    strong_rows = sorted((by_id[i] for i in strong), key=_share)
    weak_rows = sorted((by_id[i] for i in weak), key=_share, reverse=True)
    return {"strong": strong_rows, "weak": weak_rows}


def _moves(ctx: dict, rows: list[dict]) -> dict:
    """Che cosa e' cambiato nell'ultima rilevazione: la posizione di prima e'
    quella di oggi piu' il movimento. L'anno e il denominatore di prima non
    sono nel contesto, e non si scrivono."""
    def enrich(items):
        # Una posizione di prima oltre il denominatore di oggi vuol dire che
        # allora le province con un dato erano di piu': la pagina lo dice,
        # invece di mostrare "32ª su 47, era 67ª" come fosse un errore.
        return [{**r, "previous": r["rank"] + r["movement"],
                 "fewer_now": r["rank"] + r["movement"] > (r.get("province_count") or 0)}
                for r in items]

    up = [r for r in rows if r.get("movement") and r["movement"] > 0]
    down = [r for r in rows if r.get("movement") and r["movement"] < 0]
    same = [r for r in rows if r.get("movement") == 0]
    claim = None
    if up or down:
        claim = (f"Nell'ultima rilevazione è salita in classifica su {len(up)} "
                 f"{'indicatore' if len(up) == 1 else 'indicatori'} e scesa su {len(down)}")
    return {
        "up": enrich(ctx.get("movimenti_su") or []),
        "down": enrich(ctx.get("movimenti_giu") or []),
        "claim": claim, "same": len(same),
        "without": sum(1 for r in rows if r.get("movement") is None),
    }


def _neighbours(ctx: dict) -> dict:
    """Le vicine in classifica e le sorelle di regione, ognuna con la provincia
    della pagina al suo posto, perche' la classifica si legge attorno a lei."""
    profile = ctx["profile"]
    me = {"key": profile["key"], "name": profile["name"], "path": profile["path"],
          "rank": profile["rank"], "score": profile["score"], "region": profile.get("region"),
          "metro_city": profile.get("metro_city"), "is_me": True}

    def with_me(items):
        rows = [{**x, "is_me": False} for x in items] + [me]
        rows.sort(key=lambda r: (r["rank"], r["name"]))
        return [{**r, "score_text": _score(r["score"]), "width": round(max(0, min(r["score"], 100)), 1)}
                for r in rows]

    near = with_me(ctx.get("vicine") or []) if ctx.get("vicine") else []
    sisters = with_me(ctx.get("sister_provinces") or []) if ctx.get("sister_provinces") else []
    return {"near": near, "sisters": sisters}


def _tiles(ctx: dict, rows: list[dict], sisters: list[dict]) -> list[dict]:
    """Tre cifre che l'H1 e la frase-risposta non dicono."""
    profile = ctx["profile"]
    tiles = []
    if sisters:
        place = next(i for i, r in enumerate(sisters, 1) if r["is_me"])
        before = sisters[place - 2] if place > 1 else None
        after = sisters[place] if place < len(sisters) else None
        tile = {"label": f"Fra le province {of_region(profile['region'])}",
                "num": common.ordinal(place), "unit": f"su {len(sisters)}"}
        if before:
            tile["pre"], tile["link"] = "dopo ", before
        elif after:
            tile["pre"], tile["link"] = "davanti a ", after
        tiles.append(tile)
    compared = [r for r in rows if r.get("in_regione")]
    if compared:
        first = sum(1 for r in compared if r["in_regione"]["posizione"] == 1)
        last = sum(1 for r in compared if r["in_regione"]["posizione"] == r["in_regione"]["quante"])
        tiles.append({"label": f"Prima in {profile['region']}",
                      "num": str(first),
                      "unit": "indicatore" if first == 1 else "indicatori",
                      "sub": f"e ultima in {last}, fra le province che hanno un dato"})
    methodology = profile.get("methodology") or {}
    in_score = methodology.get("score_indicators_total")
    tiles.append({"label": "Indicatori misurati", "num": str(len(rows)), "unit": None,
                  "sub": f"{in_score} entrano nel punteggio" if in_score else None})
    return tiles


def derive(ctx: dict) -> dict:
    profile = ctx["profile"]
    rows = ctx.get("indicatori") or []
    by_id = {r["id"]: r for r in rows}
    methodology = profile.get("methodology") or {}

    categories = profile.get("categories") or []
    best = categories[0] if categories else None
    worst = categories[-1] if len(categories) > 1 else None

    groups = []
    for area in ctx.get("macro_aree") or []:
        items = [r for r in rows if r.get("macro_area") == area]
        if items:
            groups.append({"name": area, "anchor": "area-" + slugify_taxonomy(area), "rows": items})
    orphans = [r for r in rows if r.get("macro_area") not in (ctx.get("macro_aree") or [])]
    if orphans:
        groups.append({"name": "Altri indicatori", "anchor": "area-altri", "rows": orphans})

    neighbours = _neighbours(ctx)
    years = [r["year"] for r in rows if r.get("year")]
    first_years = [r["year_from"] for r in rows if r.get("year_from")]
    year_from = min(first_years) if first_years else None
    year_to = max(years) if years else None

    in_score = methodology.get("score_indicators_total")
    coverage = profile.get("coverage")
    covered = round(coverage * in_score) if coverage is not None and in_score else None

    source = _source_label(methodology)
    span = f"{year_from}-{year_to}" if year_from and year_to and year_from != year_to else str(year_to or "")
    citation = (f"Divario Italia, «Qualità della vita {at_place(profile['name'])}», "
                f"elaborazione su dati {source}{', ' + span if span else ''}. {ctx.get('canonical')}")

    region_path = profile.get("region_path")
    return {
        "score": common.num(profile["score"]),
        "best": {"name": best["name"], "score": common.num(best["score"])} if best else None,
        "worst": {"name": worst["name"], "score": common.num(worst["score"])} if worst else None,
        "profile_name": ((profile.get("profile") or {}).get("name") or "").lower(),
        "region_key": region_path.rstrip("/").rsplit("/", 1)[-1] if region_path else None,
        "tiles": _tiles(ctx, rows, neighbours["sisters"]),
        "dims": _dimensions(profile),
        "synthesis": _synthesis(ctx, by_id),
        "moves": _moves(ctx, rows),
        "groups": groups,
        "near": neighbours["near"],
        "sisters": neighbours["sisters"],
        "year_from": year_from, "year_to": year_to,
        "latest_min": min(years) if years else None,
        "source": source,
        "dataset": methodology.get("source"),
        "in_score": in_score, "covered": covered,
        "citation": citation,
    }
