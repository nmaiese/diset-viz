"""La pagina provincia della 1.0: cio' che il template chiede in piu' ai dati.

Parte dal contesto che `province_page` passa al template: il profilo della
qualita' della vita (`profile`), i valori veri degli indicatori
(`indicatori`), le vicine in classifica e le sorelle della stessa regione. La
striscia d'apertura mette la provincia fra tutte le altre, e le altre le da'
la classifica delle province, `quality_life_bes.build_bes_ranking`, gia'
memoizzata nella cache dell'app: qui si legge e si confronta col profilo
prima di usarla, e se i due non coincidono la striscia si toglie.

Qui si contano e si mettono in ordine le cose, e i valori restano numeri: li
scrive il template con i filtri `num`, `rank` e `delta` di `numfmt`, con i
decimali della grandezza di ogni cifra, come la scheda indicatore e la pagina
regione. I decimali della fonte erano una seconda regola, e scrivevano la
stessa cifra in due modi a un clic di distanza. Nelle frasi composte qui
i conteggi passano da `count_word` e le posizioni da `ordinal`.

Un dato che manca toglie la frase o la sezione, non ferma la pagina.
"""

from __future__ import annotations

from app import quality_life_bes as qb
from app import sources
from app.design import charts, numfmt
from app.design.common import count_word, of_place, ordinal, the_place
from app.seo_titles import at_place, of_region, to_place
from app.taxonomy import CANONICAL_CATEGORIES, slugify_taxonomy

LEVEL = "provincia"


def _plain_id(ident: str) -> str:
    """`bes:12SER022` -> `12SER022`: il profilo porta il prefisso della
    famiglia, la tabella degli indicatori no."""
    return ident.split(":", 1)[1] if ":" in ident else ident


def _join(names: list[str]) -> str:
    """"A", "A e B", "A, B e C"."""
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]


def _source_label(methodology: dict) -> str:
    """L'etichetta pubblica della fonte, da `app/sources.py` e da nessun altro
    posto: "Istat, benessere e qualita' della vita", mai la sigla interna.

    Se il metodo non nomina una famiglia nota resta la fonte che il metodo
    dichiara, la stessa che scriveva la pagina di prima."""
    families = [f for f in (methodology.get("source_counts") or {}) if f in sources.SOURCES]
    if families:
        return _join([sources.family_label(f) for f in families])
    return methodology.get("source") or "Istat, BES dei Territori"


def _share(row: dict) -> float:
    """La posizione relativa, perche' il denominatore cambia da riga a riga."""
    return row["rank"] / (row.get("province_count") or 1)


def _track(position: int | None, total: int | None) -> float:
    """Dove cade una posizione sulla traccia da 1 a N, in percentuale."""
    if not position or not total or total < 2:
        return 0.0
    return round((position - 1) / (total - 1) * 100, 1)


def _ranking(profile: dict) -> list[dict] | None:
    """Tutte le province col loro punteggio, dalla classifica viva.

    La classifica e il profilo vengono dallo stesso calcolo, ma per due strade
    e con due voci di cache diverse: se il profilo, il numero di province o la
    posizione e il punteggio della provincia non coincidono, una delle due e'
    vecchia, e la pagina toglie la striscia invece di mostrare due classifiche.
    """
    slug = (profile.get("profile") or {}).get("slug") or qb.DEFAULT_PROFILE
    payload = qb.build_bes_ranking(LEVEL, slug)
    if not payload:
        return None
    rows = payload.get("ranking") or []
    me = next((r for r in rows if r.get("key") == profile["key"]), None)
    if ((payload.get("profile") or {}).get("slug") != slug or len(rows) != profile.get("total")
            or me is None or me.get("rank") != profile.get("rank") or me.get("score") != profile.get("score")):
        return None
    return rows


def _strip(profile: dict) -> dict | None:
    """La striscia delle province per punteggio, con la provincia in evidenza.

    Ogni provincia ha il colore della ripartizione della sua regione, la
    distanza fra prima e ultima si legge in punti, e il titolo e' un fatto
    contato sulla ripartizione della provincia: la sua posizione fra le
    province della stessa ripartizione e quante di queste stanno sotto la media.
    """
    ranking = _ranking(profile)
    if not ranking or profile.get("score") is None:
        return None
    areas = charts.area_map()
    rows = [{"key": r["key"], "name": r["name"], "value": r["score"], "area": areas.get(r["key"])}
            for r in ranking if r.get("score") is not None]
    if len(rows) < 2:
        return None
    values = [r["value"] for r in rows]
    avg = sum(values) / len(values)
    gap = max(values) - min(values)
    strip = charts.divario_strip(rows, avg, None, highlight=profile["key"],
                                 gap_label=f"{numfmt.text(gap, 1)} punti fra prima e ultima")
    if not strip.get("svg"):
        return None

    name, total = profile["name"], len(rows)
    area = areas.get(profile["key"])
    title = f"Le {count_word(total)} province sulla stessa scala, e {name} fra loro"
    if area:
        same = sorted((r for r in ranking if areas.get(r["key"]) == area and r.get("score") is not None),
                      key=lambda r: r["rank"])
        pos = next(i for i, r in enumerate(same, 1) if r["key"] == profile["key"])
        below = sum(1 for r in same if r["score"] < avg)
        where = f"province del {charts.AREA_LABEL[area]}"
        if profile["score"] < avg:
            tail = ("e tutte stanno sotto la media" if below == len(same)
                    else f"dove {count_word(below)} stanno sotto la media")
        else:
            above = len(same) - below
            tail = ("e tutte stanno sopra la media" if above == len(same)
                    else f"dove {count_word(above)} stanno sopra la media")
        title = f"{name} è {ordinal(pos)} fra le {count_word(len(same))} {where}, {tail}"

    # Niente tabella delle province qui: la striscia porta alla classifica,
    # che e' la sua casa (il perche' sta nel template).
    # charts.py scrive il nome della provincia verso destra quando il punto sta
    # nella meta' sinistra: sotto la media quel nome attraversa la linea della
    # media e, nel taglio stretto, finisce sull'etichetta "Media". Si gira
    # verso sinistra, lontano dalla media, se a sinistra c'e' posto.
    lo, hi = min(values), max(values)
    label_left = profile["score"] < avg and (profile["score"] - lo) / ((hi - lo) or 1) > 0.2
    return {**strip, "title": title, "count": total, "label_left": label_left}


def _dimensions(profile: dict) -> dict:
    """Le dimensioni misurate, con la barra divergente attorno a 50 sulla scala
    fissa 0-100: la stessa scala per tutte le province, cosi' due pagine si
    confrontano a occhio."""
    cats = [c for c in profile.get("categories") or [] if c.get("score") is not None]
    rows = []
    for cat in cats:
        score = cat["score"]
        rows.append({
            "name": cat["name"],
            "slug": cat["slug"],
            "score": score,
            "diff": round(score - 50, 1),
            "left": round(min(score, 50), 1),
            "width": round(abs(score - 50), 1),
        })
    measured = {cat["slug"] for cat in cats}
    weights = (profile.get("profile") or {}).get("weights") or {}
    missing = [CANONICAL_CATEGORIES[slug]["name"] for slug in weights
               if slug not in measured and slug in CANONICAL_CATEGORIES]
    above = [c for c in cats if c["score"] > 50]
    n, total = len(rows), count_word(profile.get("total") or 0)
    dims = count_word(n)
    if not rows or not profile.get("total"):
        claim = None
    elif not above:
        claim = f"Nessuna delle {dims} dimensioni supera la media delle {total} province"
    elif len(above) == n:
        claim = f"Tutte le {dims} dimensioni stanno sopra la media delle {total} province"
    elif len(above) == 1:
        claim = f"{above[0]['name']} è l'unica delle {dims} dimensioni sopra la media delle {total} province"
    else:
        claim = f"{count_word(len(above))} dimensioni su {dims} stanno sopra la media delle {total} province"
        claim = claim[:1].upper() + claim[1:]
    lead = ("Manca una dimensione del profilo," if len(missing) == 1
            else f"Mancano {count_word(len(missing))} dimensioni del profilo,")
    return {"rows": rows, "count": n, "missing": missing, "missing_text": _join([f"«{m}»" for m in missing]),
            "missing_lead": lead, "claim": claim}


def _synthesis(ctx: dict, by_id: dict) -> dict:
    """Una sintesi sola al posto delle tre coppie della pagina di prima.

    Da una parte gli indicatori che alzano di piu' il punteggio e quelli in cui
    la provincia e' la prima fra le province della sua regione, dall'altra gli
    indicatori che lo abbassano di piu' e quelli in cui e' l'ultima. Ogni
    indicatore compare una volta sola: le liste del punteggio decidono il lato,
    quelle della regione aggiungono solo cio' che manca.
    """
    profile = ctx["profile"]
    pos_ids = [_plain_id(x["id"]) for x in profile.get("top_positive") or [] if x.get("id")]
    neg_ids = [_plain_id(x["id"]) for x in profile.get("top_negative") or [] if x.get("id")]
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
                for r in items if r.get("rank") is not None and r.get("movement")]

    up = [r for r in rows if r.get("movement") and r["movement"] > 0]
    down = [r for r in rows if r.get("movement") and r["movement"] < 0]
    same = [r for r in rows if r.get("movement") == 0]

    def on(n):
        return f"{count_word(n, feminine=False)} {'indicatore' if n == 1 else 'indicatori'}"

    # La frase dice solo i versi che ci sono: "e scesa su 0" non e' un fatto.
    if up and down:
        claim = f"Nell'ultima rilevazione è salita in classifica su {on(len(up))} e scesa su {count_word(len(down), feminine=False)}"
    elif up:
        claim = f"Nell'ultima rilevazione è salita in classifica su {on(len(up))} e non è scesa su nessuno"
    elif down:
        claim = f"Nell'ultima rilevazione è scesa in classifica su {on(len(down))} e non è salita su nessuno"
    else:
        claim = None
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
    if profile.get("rank") is None or profile.get("score") is None:
        return {"near": [], "sisters": []}
    me = {"key": profile["key"], "name": profile["name"], "path": profile["path"],
          "rank": profile["rank"], "score": profile["score"], "region": profile.get("region"),
          "metro_city": profile.get("metro_city"), "is_me": True}

    def with_me(items):
        rows = [{**x, "is_me": False} for x in items
                if x.get("rank") is not None and x.get("score") is not None]
        if not rows:
            return []
        rows.append(me)
        rows.sort(key=lambda r: (r["rank"], r["name"]))
        return [{**r, "width": round(max(0, min(r["score"], 100)), 1)} for r in rows]

    return {"near": with_me(ctx.get("vicine") or []), "sisters": with_me(ctx.get("sister_provinces") or [])}


def _tiles(ctx: dict, rows: list[dict], sisters: list[dict], covered: int | None) -> list[dict]:
    """Tre cifre che l'H1, la risposta e la striscia non dicono.

    La posizione in regione e' un `numfmt.rank` gia' composto: la macro delle
    tessere lo stampa com'e' dal campo `num`, perche' il suo ramo `value`
    scriverebbe la posizione senza la ª.
    """
    profile = ctx["profile"]
    tiles = []
    if sisters and profile.get("region"):
        place = next(i for i, r in enumerate(sisters, 1) if r["is_me"])
        before = sisters[place - 2] if place > 1 else None
        after = sisters[place] if place < len(sisters) else None
        tile = {"label": f"Fra le province {of_region(profile['region'])}", "num": numfmt.rank(place, len(sisters))}
        if before:
            tile["sub"], tile["href"] = f"dopo {the_place(before['name'], LEVEL)}", before["path"]
        elif after:
            tile["sub"], tile["href"] = f"davanti {to_place(after['name'])}", after["path"]
        tiles.append(tile)
    compared = [r for r in rows if r.get("in_regione")]
    if compared and profile.get("region"):
        first = sum(1 for r in compared if r["in_regione"]["posizione"] == 1)
        last = sum(1 for r in compared if r["in_regione"]["posizione"] == r["in_regione"]["quante"])
        tail = "fra le province che hanno un dato"
        if first:
            sub = (f"e ultima in {count_word(last, feminine=False)}, {tail}" if last
                   else f"e ultima in nessuno, {tail}")
            tiles.append({"label": f"Prima in {profile['region']}", "value": first, "role": "count",
                          "unit": "indicatore" if first == 1 else "indicatori", "sub": sub})
        elif last:
            tiles.append({"label": f"Ultima in {profile['region']}", "value": last, "role": "count",
                          "unit": "indicatore" if last == 1 else "indicatori",
                          "sub": f"e prima in nessuno, {tail}"})
    if rows:
        tiles.append({"label": "Indicatori misurati", "value": len(rows), "role": "count", "unit": None,
                      "sub": f"{count_word(covered, feminine=False)} entrano nel punteggio" if covered else None})
    return tiles


def _with_units(rows: list[dict]) -> list[dict]:
    """Ogni valore con la posizione sulla traccia da 1 a N, e con l'unita'
    intera quando la forma corta di `numfmt` non la puo' scrivere accanto alla
    cifra ("tasso standardizzato per 10.000")."""
    return [{**r, "unit_after": r.get("unit") if r.get("unit") and not numfmt.short_unit(r["unit"]) else None,
             "track": _track(r.get("rank"), r.get("province_count"))}
            for r in rows if r.get("rank") is not None]


def _score_coverage(key: str) -> tuple[int, int] | None:
    """(quanti indicatori del punteggio hanno un valore per la provincia, quanti sono).

    Si conta sulla stessa matrice che fa il punteggio, non si ricava dalla
    `coverage` del profilo: quella e' la quota di **dimensioni** con un
    punteggio, e moltiplicata per gli indicatori diceva "tutti i 64" anche a
    Sud Sardegna, che ne ha 59. Le due funzioni sono interne a
    `quality_life_bes` e memoizzate: qui si fanno solo sessantaquattro
    ricerche in un dizionario.
    """
    matrix, _ = qb._matrix_and_meta(LEVEL)
    ids = [i for group in qb._indicators_by_category(LEVEL).values() for i in group]
    if not ids:
        return None
    return sum(1 for i in ids if key in (matrix.get(i) or {})), len(ids)


def derive(ctx: dict) -> dict:
    profile = ctx["profile"]
    rows = _with_units(ctx.get("indicatori") or [])
    by_id = {r["id"]: r for r in rows}
    methodology = profile.get("methodology") or {}

    categories = [c for c in profile.get("categories") or [] if c.get("score") is not None]
    best = categories[0] if categories else None
    worst = categories[-1] if len(categories) > 1 else None

    macro_areas = list(ctx.get("macro_aree") or [])
    groups = []
    for area in macro_areas:
        items = [r for r in rows if r.get("macro_area") == area]
        if items:
            groups.append({"name": area, "anchor": "area-" + slugify_taxonomy(area), "rows": items})
    orphans = [r for r in rows if r.get("macro_area") not in macro_areas]
    if orphans:
        groups.append({"name": "Altri indicatori", "anchor": "area-altri", "rows": orphans})

    neighbours = _neighbours(ctx)
    years = [r["year"] for r in rows if r.get("year")]
    first_years = [r["year_from"] for r in rows if r.get("year_from")]
    year_from = min(first_years) if first_years else None
    year_to = max(years) if years else None

    coverage = _score_coverage(profile["key"])
    covered, in_score = coverage if coverage else (None, None)

    weights = [w for w in ((profile.get("profile") or {}).get("weights") or {}).values() if w is not None]
    equal_weights = bool(weights) and max(weights) - min(weights) < 1e-9

    source = _source_label(methodology)
    span = f"{year_from}-{year_to}" if year_from and year_to and year_from != year_to else str(year_to or "")
    citation = (f"Divario Italia, «Qualità della vita {at_place(profile['name'])}», "
                f"elaborazione su dati {source}{', ' + span if span else ''}. {ctx.get('canonical') or ''}").rstrip()

    region_path = profile.get("region_path")
    return {
        "best": best, "worst": worst,
        # "Provincia dell'Aquila", "della Spezia": la preposizione si elide
        # davanti al nome, come negli altri punti del sito che lo compongono.
        "of_name": of_place(profile["name"], LEVEL),
        "profile_name": ((profile.get("profile") or {}).get("name") or "").lower(),
        "equal_weights": equal_weights,
        "region_key": region_path.rstrip("/").rsplit("/", 1)[-1] if region_path else None,
        "strip": _strip(profile),
        "tiles": _tiles(ctx, rows, neighbours["sisters"], covered),
        "dims": _dimensions(profile),
        "synthesis": _synthesis(ctx, by_id),
        "moves": _moves(ctx, rows),
        "groups": groups,
        "near": neighbours["near"],
        "sisters": neighbours["sisters"],
        "year_from": year_from, "year_to": year_to,
        "source": source,
        "dataset": methodology.get("source"),
        "in_score": in_score, "covered": covered,
        "citation": citation,
    }
