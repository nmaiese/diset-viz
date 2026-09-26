"""La scheda indicatore della 1.0: cio' che il template chiede in piu' ai dati.

Tessere, titolo-affermazione della classifica, la striscia del divario, la
serie a fascia, i richiami sulla mappa e i dati del modulo interattivo. Sulle
province anche la classifica piegata (prime e ultime dieci, le altre in un
`details`) e "Dentro le regioni". Prende il contesto che `_render_indicator`
passa al template, e non ne cambia niente.
"""

from __future__ import annotations

import re

from app.design import charts, maps, numfmt
from app.design.common import (
    MEZZOGIORNO,
    PATHS,
    count_word,
    date_it,
    del_,
    legend,
    map_classes,
    num,
    of_place,
    ranking,
    short_unit,
    signed,
    the_place,
    unit_note,
    values_note,
    with_unit,
)
from app.design.pages.classifica import EDGE, SPLIT_OVER, from_to
from app.indicator_notes import ds_choropleth_colors
from app.profiles import region_key_for
from app.seo_titles import (
    UNVERIFIED_EXTREMES,
    _code,
    _is_percentage,
    _widest_within_region,
    from_place,
    in_region,
    region_gaps,
    to_place,
)

# L'id di una riga della classifica provinciale: `/provincia/<key>` porta a
# `...#p-<key>`, e la riga si accende con `:target` anche senza JavaScript.
ROW_ID = {"provincia": "p-"}
VERSO_WORDS = {"higher_better": "Qui un valore più alto è migliore.",
               "lower_better": "Qui un valore più basso è migliore.",
               "higher_worse": "Qui un valore più basso è migliore."}


def fold(rows: list[dict], plural: str) -> dict | None:
    """La classifica lunga piegata come quella della qualita' della vita
    (`classifica.split`, stesse soglie): le prime e le ultime EDGE righe in
    vista, le altre nello stesso documento dentro un `details` (SISTEMA.md).

    La riga della media semplice va nel pezzo della riga che la segue, dove la
    classifica la incrocia: la stessa regola che v1.js usa quando ridisegna le
    righe al cambio d'anno. None quando le righe sono SPLIT_OVER o meno."""
    n = sum(1 for row in rows if not row.get("ref"))
    if n <= SPLIT_OVER:
        return None
    parts = {"head": [], "middle": [], "tail": []}
    seen = 0
    for row in rows:
        part = "head" if seen < EDGE else "tail" if seen >= n - EDGE else "middle"
        parts[part].append(row)
        if not row.get("ref"):
            seen += 1
    return {**parts,
            "head_caption": f"Le prime {EDGE} {plural}",
            "tail_caption": f"Le ultime {EDGE} {plural}",
            "label": f"{from_to(EDGE + 1, n - EDGE)}: le altre {n - 2 * EDGE} {plural}"}


def _ends(members: list[dict], pick: dict, profile_path: str | None) -> dict:
    """Un estremo di una regione: il valore e chi lo tiene. Un pari merito si
    dice tutto, come nella frase-risposta: due nomi, o "5 province"."""
    tied = sorted((o for o in members if o["value"] == pick["value"]), key=lambda o: o["name"])
    places = [{"name": o["name"], "href": (profile_path + o["key"]) if profile_path else None} for o in tied]
    return {"value": pick["value"], "places": places if len(tied) <= 2 else None, "count": len(tied)}


def _in_regions(regions: list[str]) -> str:
    """"nel Lazio e in Veneto": lo stato in luogo davanti a ogni regione, fino
    a tre. Oltre, quante sono ("in 4 regioni")."""
    if len(regions) > 3:
        return f"in {len(regions)} regioni"
    words = [in_region(region) for region in regions]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " e " + words[-1]


def _ends_phrase(row: dict) -> str | None:
    """"da Prato a Grosseto e Massa-Carrara": gli estremi di una regione come
    li dice la cella, a pari merito tutti e due i nomi. None quando il titolo
    non li puo' dire: oltre due a pari merito la cella dice "3 province", e
    due nomi di cui uno ha gia' una "e" ("da Ancona e Pesaro e Urbino") non si
    leggono in una riga. Il titolo dice allora la regione e la cifra.

    "da A a B" e non "fra A e B": con "fra Monza e della Brianza e Sondrio" la
    "e" dentro il nome si leggeva come quella fra le due."""
    phrases = []
    for end, place in ((row["high"], from_place), (row["low"], to_place)):
        names = [p["name"] for p in end["places"] or []]
        if not names or (len(names) > 1 and any(" e " in name for name in names)):
            return None
        phrases.append(place(names[0]) + "".join(f" e {name}" for name in names[1:]))
    return " ".join(phrases)


def within_regions(meta: dict, level: dict, unit: str | None) -> dict | None:
    """"Dentro le regioni": per ogni regione con il dato di almeno due province,
    la provincia piu' alta, la piu' bassa e la distanza fra le due. E' cio' che
    la vista regionale non puo' dire.

    Le righe vengono da `seo_titles.region_gaps`, la stessa funzione da cui la
    frase-risposta prende la sua distanza: distanze arrotondate ai decimali
    della colonna, dalla piu' ampia, a pari distanza per nome della regione.
    Cosi' il titolo-affermazione nomina la regione della frase-risposta e ne
    ripete la cifra con la sua unita', e la testata e il blocco non dicono due
    cose. Dove la frase non scrive la cifra (un tasso su una base lunga) il
    titolo dice la regione e gli estremi, e la cifra resta nella tabella. Le
    celle hanno i decimali della colonna dei valori, cosi' la distanza e' la
    differenza che si legge accanto: sopra i cento il titolo la arrotonda come
    ogni cifra del sito (443 punti, 449,6 meno 6,5 in tabella).

    Il titolo non dice mai "la piu' ampia" di una regione sola quando un'altra
    ha la stessa distanza scritta: le nomina tutte, fino a tre, e senza
    province. Gli estremi li dice come la cella (`_ends_phrase`), anche a
    pari merito.

    Su `UNVERIFIED_EXTREMES` niente titolo: la frase-risposta e il title non
    dicono gli estremi finche' non sono verificati, e un titolo qui li
    direbbe. La tabella resta, come la classifica.
    """
    if level["key"] != "provincia" or not level.get("region_of"):
        return None
    observed = [o for o in level.get("observations") or [] if o.get("value") is not None]
    profile_path = level.get("profile_path")
    rows = [{"region": region, "href": "/regione/" + region_key_for(region), "gap": gap,
             "high": _ends(members, upper, profile_path), "low": _ends(members, lower, profile_path)}
            for gap, region, upper, lower, members in region_gaps(level, observed)]
    if not rows:
        return None

    claim = None
    if _code(meta) not in UNVERIFIED_EXTREMES and rows[0]["gap"] > 0:
        widest = _widest_within_region(meta, level, observed, _is_percentage(meta))
        figure = widest[0] if widest else None
        top = [row["region"] for row in rows if row["gap"] == rows[0]["gap"]]
        if len(top) > 1:
            # "nel Lazio e in Veneto, 0,50 punti": a pari distanza nessuna
            # delle due e' "la" piu' ampia. La frase-risposta nomina la prima
            # per nome, che qui c'e'.
            claim = f"La distanza più ampia è {_in_regions(top)}"
            tail = figure
        else:
            claim = f"La distanza più ampia è {in_region(top[0])}"
            tail = " ".join(part for part in (figure, _ends_phrase(rows[0])) if part)
        if tail:
            claim += f", {tail}"
    percent = numfmt.is_percent(unit)
    note = unit_note(unit, meta["name"])
    return {
        "claim": claim, "rows": rows, "year": level.get("year_max"),
        "decimals": numfmt.column_decimals([o["value"] for o in observed]),
        "subline": (f"{meta['name']}{', ' + note if note else ''}, {level.get('year_max')}. "
                    "Per ogni regione con il dato di almeno due province, la provincia con il valore più alto, "
                    f"quella con il più basso e la distanza fra le due{', in punti percentuali' if percent else ''}."
                    + (f" {VERSO_WORDS[meta.get('direction')]}" if meta.get("direction") in VERSO_WORDS else "")),
    }


def family_paths(ctx: dict) -> list[str]:
    """Le pagine della stessa famiglia: questa, le sue dimensioni (genere, eta')
    e gli altri livelli. Fra queste la striscia del divario si ricompone invece
    di ricomparire (v1.js, pageswap e pagereveal), e il territorio scelto resta
    scelto."""
    from urllib.parse import urlsplit

    paths = [urlsplit(ctx.get("canonical") or "").path]
    for item in (ctx.get("dimension_siblings") or []) + (ctx.get("other_views") or []):
        path = urlsplit(item.get("path") or "").path
        if path.startswith("/indicatore/") and path not in paths:
            paths.append(path)
    return [p for p in paths if p]


def ranking_claim(level: dict) -> str | None:
    """Il titolo-affermazione della classifica: un fatto verificato sul
    Mezzogiorno, o quante stanno sopra e quante sotto la media semplice."""
    stats = level.get("stats") or {}
    year, plural = level.get("year_max"), level["plural"]
    claim = None
    if level["key"] == "regione" and stats.get("year_avg") is not None:
        south = [o for o in level["observations"] if o["key"] in MEZZOGIORNO]
        below = [o for o in south if o["value"] < stats["year_avg"]]
        if south and len(below) == len(south):
            claim = f"Nel {year} tutte le {count_word(len(south))} regioni del Mezzogiorno stanno sotto la media semplice"
        elif south and not below:
            claim = f"Nel {year} tutte le {count_word(len(south))} regioni del Mezzogiorno stanno sopra la media semplice"
        elif south:
            claim = f"Nel {year} {count_word(len(below))} regioni del Mezzogiorno su {count_word(len(south))} stanno sotto la media semplice"
    if claim is None and stats.get("above_avg_count") is not None:
        claim = f"Nel {year} {stats['above_avg_count']} {plural} stanno sopra la media semplice e {stats['below_avg_count']} sotto"
    return claim


def level_tabs(meta: dict, level: dict, levels: list[dict], twin: dict | None) -> list[dict]:
    """Le voci del selettore di livello della scheda: i suoi livelli e, se ne
    manca uno, quello della gemella. Prima le regioni, come in tutto il sito.
    Ogni voce porta all'URL del suo livello (`level["preferred_path"]`): la
    base per il primo, la `/province` per le province di una scheda a due
    livelli, e ter-910 per le regioni di bes-01SAL001, che hanno li' il
    canonical (`indicator_view.canonical_elsewhere`). La voce corrente il
    template non la rende come link."""
    tabs = [{"key": lv["key"], "label": lv["label"], "current": lv["key"] == level["key"],
             "href": lv["preferred_path"]}
            for lv in levels]
    if twin and tabs:
        tabs.append({"key": twin["key"], "label": twin["label"], "current": False, "href": twin["path"]})
    tabs.sort(key=lambda t: 0 if t["key"] == "regione" else 1)
    return tabs


def explore_module(meta: dict, level: dict, *, tabs: list[dict] | None = None,
                   claim: str | None = None, strip: dict | None = None) -> dict:
    """Il modulo dato ("Chi e' in testa"): tutto cio' che la macro `ui.explore`
    legge, in un dizionario solo, per un indicatore su un livello.

    Lo compongono la scheda e l'atlante, dallo stesso livello che
    `indicator_view` costruisce. Qui si mette insieme, non si ricalcola: ogni
    cifra e' quella che la scheda mostrava prima che il modulo fosse un
    componente. `tabs` sono le voci del selettore di livello (la scheda passa
    le sue, `level_tabs`), `claim` il titolo sopra la classifica
    (`ranking_claim` se manca), `strip` la striscia del divario quando chi
    chiama l'ha gia' disegnata: del modulo fa parte solo la sua legenda delle
    ripartizioni."""
    stats = level.get("stats") or {}
    unit = meta.get("value_unit") or meta.get("unit")
    direction = meta.get("direction")
    plural, year = level["plural"], level.get("year_max")
    obs = level.get("observations") or []
    best, worst = level.get("best"), level.get("worst")
    areas = charts.area_map()
    if claim is None:
        claim = ranking_claim(level)
    if strip is None:
        rows = [{**o, "area": areas.get(o["key"])} for o in obs]
        strip = charts.divario_strip(rows, stats.get("year_avg"), unit, stats.get("gap_ratio"))
    # La mappa c'e' per tutti e due i livelli. `LEVELS["provincia"]["has_map"]`
    # resta falso perche' lo leggono il template di ripiego e il vecchio
    # esploratore, che hanno solo le regioni: qui le province hanno i loro
    # contorni (maps.PROVINCE_PATHS) e la stessa rampa a sei gradini
    # calcolata come in home.
    show_map = bool(level.get("has_map")) or level["key"] == "provincia"
    classes = map_classes(level)
    map_names = {t["key"]: t["name"] for t in level.get("territories") or []}
    if show_map and not level.get("has_map"):
        from app.design.pages.home import level_names

        classes = map_classes({"map_colors": ds_choropleth_colors(
            [{"region_key": o["key"], "value": o["value"]} for o in level.get("observations") or []])})
        map_names = {**level_names(level["key"]), **map_names}
    callouts = ""
    if show_map and best and worst:
        shapes = PATHS if level["key"] == "regione" else maps.paths(level["key"])
        callouts = charts.map_callouts(shapes, [(best["key"], best["name"], with_unit(best["value"], unit)),
                                                (worst["key"], worst["name"], with_unit(worst["value"], unit))])
    values = [o["value"] for o in level.get("observations") or [] if o.get("value") is not None]
    explore_js = {
        "years": [int(y) for y in sorted(level.get("matrix") or {}, key=int)],
        "matrix": level.get("matrix") or {},
        "names": {t["key"]: t["name"] for t in level.get("territories") or []},
        "unit": numfmt.phrase_unit(unit), "direction": direction, "plural": plural,
        "decimals": numfmt.column_decimals([o["value"] for o in obs]), "areas": {o["key"]: areas.get(o["key"]) for o in obs},
        "profile": level.get("profile_path"), "south": sorted(MEZZOGIORNO) if level["key"] == "regione" else [],
    }
    rank_rows = ranking(level, unit)
    folded = fold(rank_rows, plural) if level["key"] in ROW_ID else None
    if level["key"] in ROW_ID:
        # v1.js ridisegna le righe al cambio d'anno: con l'id, e piegate con
        # le stesse soglie quando il server le ha piegate.
        explore_js["row_id"] = ROW_ID[level["key"]]
        explore_js["fold"] = {"edge": EDGE, "over": SPLIT_OVER} if folded else None
    map_missing = show_map and bool(set(maps.paths(level["key"])) - {o["key"] for o in obs})
    downloads = meta.get("downloads") or {}
    return {
        "name": meta["name"], "level": level["key"], "year": year, "year_min": level.get("year_min"),
        "years": level.get("years") or [], "n": len(obs), "plural": plural, "singular": level["singular"],
        "lower_better": direction in ("lower_better", "higher_worse"),
        "claim": claim, "unit_note": unit_note(unit, meta["name"]), "short_unit": short_unit(unit),
        "level_tabs": tabs or [], "territories": level.get("territories") or [],
        "show_map": show_map, "map_classes": classes, "map_names": map_names,
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in level.get("observations") or []},
        "callouts": callouts, "legend": legend(values, unit) if values else None,
        "legend_nd": level["key"] == "regione" or map_missing,
        "area_legend": strip.get("legend"), "ranking": rank_rows, "fold": folded,
        "row_id": ROW_ID.get(level["key"]),
        "decimals": numfmt.column_decimals([o["value"] for o in obs]),
        "areas": {o["key"]: areas.get(o["key"]) for o in obs}, "area_label": charts.AREA_LABEL,
        "profile_path": level.get("profile_path"),
        "source_url": meta.get("source_url"), "source_label": meta.get("source_label"),
        "csv": downloads.get("csv") if level["key"] == "regione" else None,
        "js": explore_js,
        "mini": _mini_map(level["key"], classes, map_names,
                          {o["key"]: with_unit(o["value"], unit) for o in level.get("observations") or []}) if show_map else None,
    }


def _mini_map(level_key: str, classes: dict, names: dict, values: dict) -> dict:
    """La mappa piccola accanto all'analisi: gli stessi gradini della mappa
    del modulo, per l'ultimo anno, con il valore nel nome sotto il mouse e il
    clic che porta al profilo del territorio."""
    steps = {}
    for key, cls in classes.items():
        m = re.search(r"\bq([1-6])\b", cls or "")
        if m:
            steps[key] = int(m.group(1))
    return {
        "level": level_key,
        "steps": steps,
        # Solo i territori col dato portano un link: gli altri la mappa li
        # disegna in grigio (un link a una provincia non misurata sarebbe uno
        # zero che il dato non dice).
        "names": {k: f"{n}, {values[k]}" for k, n in names.items() if values.get(k)},
        "base": "/regione/" if level_key == "regione" else "/provincia/",
    }


def derive(ctx: dict) -> dict:
    meta, level = ctx["meta"], ctx["level"]
    stats = level.get("stats") or {}
    annual = level.get("annual_change") or None
    unit = meta.get("value_unit") or meta.get("unit")
    change_unit = meta.get("change_unit") or unit
    plural, n = level["plural"], len(level.get("observations") or [])
    lede = ctx.get("page_lead") or ""
    best, worst = level.get("best"), level.get("worst")
    year = level.get("year_max")

    def said(extreme):
        """La frase-risposta nomina gia' questo estremo? Anche quando e' un pari
        merito: "(Lecco e Treviso)" nomina Lecco, "(16 province)" le sedici
        insieme, e una tessera "In coda: Agrigento" direbbe una delle sedici."""
        tied = [o for o in level.get("observations") or [] if o.get("value") == extreme["value"]]
        return (any(o["name"] in lede for o in tied or [extreme])
                or (len(tied) > 2 and f"({len(tied)} {plural})" in lede))

    tiles = []
    if best and not said(best):
        tiles.append({"label": f"In testa nel {year}", "value": best["value"], "unit": unit, "role": "figure",
                      "sub": best["name"], "href": (level.get("profile_path") or "") + best["key"] if level.get("profile_path") else None})
    if worst and not said(worst):
        tiles.append({"label": f"In coda nel {year}", "value": worst["value"], "unit": unit, "role": "figure",
                      "sub": worst["name"], "href": (level.get("profile_path") or "") + worst["key"] if level.get("profile_path") else None})
    if stats.get("year_avg") is not None:
        tiles.append({"label": f"Media semplice delle {stats.get('year_count', n)} {plural}", "value": stats["year_avg"], "unit": unit, "role": "figure",
                      "sub": "non pesata per popolazione"})
    if stats.get("gap_ratio"):
        tiles.append({"label": "Fra prima e ultima", "value": stats["gap_ratio"], "unit": "volte", "role": "ratio",
                      "sub": f"una distanza di {with_unit(stats['gap_abs'], unit)}"})
    if annual:
        more, less = annual.get("increase_count", 0), annual.get("decrease_count", 0)
        trend = f"in aumento in {more} {plural} su {annual['common_count']}" if more >= less else f"in calo in {less} {plural} su {annual['common_count']}"
        tiles.append({"label": f"Dal {annual['previous_year']} al {annual['year']}", "value": annual["average_delta"], "unit": change_unit, "role": "delta",
                      "sub": f"di media semplice, {trend}"})
    tiles = tiles[:4]

    direction = meta.get("direction")
    verso = {"higher_better": "Meglio se alto", "lower_better": "Meglio se basso", "higher_worse": "Meglio se basso"}.get(direction, "Senza un verso")

    claim = ranking_claim(level)

    areas = charts.area_map()
    obs = level.get("observations") or []
    rows = [{**o, "area": areas.get(o["key"])} for o in obs]
    series = charts.band_series(level, areas) if len(level.get("matrix") or {}) >= 2 else {"svg": "", "single_year": True}
    strip = charts.divario_strip(rows, stats.get("year_avg"), unit, stats.get("gap_ratio"))
    series_claim = None
    what = None
    change_abs = stats.get("avg_change_abs")
    if stats.get("has_multi_year") and meta.get("percentage_like") and change_abs is not None:
        # Una percentuale cambia in punti, come nella prosa della stessa scheda
        # ("1,48 punti percentuali in meno") e come la distanza fra prima e
        # ultima qui sotto. La variazione relativa diceva "scesa dell'8,2%"
        # accanto a un livello in "%": due percentuali che non c'entrano fra
        # loro nella stessa frase, e su una differenza fra tassi (ter-61) una
        # cifra diversa da quella della prosa. Per la stessa ragione niente
        # "raddoppiata": e' una misura relativa.
        # Su un livello minuscolo lo spostamento arrotondato fa zero anche
        # quando la media si e' mossa: ter-163 va da 0,0107 a 0,0095, l'11,6% in
        # meno, e "rimasta la stessa" smentiva la prosa ("una variazione media
        # sfavorevole"). Si aggiungono decimali finche' la cifra non e' zero.
        decimals = numfmt.magnitude_decimals(change_abs)
        while change_abs and round(abs(change_abs), decimals) == 0 and decimals < 4:
            decimals += 1
        if round(abs(change_abs), decimals) == 0:
            what = "rimasta la stessa"
        else:
            what = f"{'cresciuta' if change_abs > 0 else 'scesa'} di {with_unit(abs(change_abs), change_unit, decimals)}"
    elif stats.get("has_multi_year") and stats.get("avg_change_pct") is not None:
        r = 1 + stats["avg_change_pct"] / 100
        if r >= 3:
            what = "più che triplicata"
        elif r >= 2:
            what = "più che raddoppiata"
        elif stats["avg_change_pct"] > 0:
            pct = num(stats["avg_change_pct"]) + "%"
            what = f"cresciuta {del_(pct)}{pct}"
        else:
            pct = num(abs(stats["avg_change_pct"])) + "%"
            what = f"scesa {del_(pct)}{pct}"
    if what:
        gap = stats.get("gap_trend")
        gap_text = ""
        if gap is not None and stats.get("year_min_gap_abs"):
            if abs(gap) < 0.01 * abs(stats["year_min_gap_abs"]):
                gap_text = ", e la distanza fra prima e ultima è rimasta la stessa"
            elif gap > 0:
                gap_text = f", e la distanza fra prima e ultima è cresciuta di {with_unit(gap, change_unit)}"
            else:
                gap_text = f", e la distanza fra prima e ultima si è ridotta di {with_unit(abs(gap), change_unit)}"
        series_claim = f"Dal {stats['year_min']} al {stats['year_max']} la media semplice è {what}{gap_text}"
    series_note = None
    hd, ld = stats.get("highest_delta"), stats.get("lowest_delta")
    lk = level["key"]
    if hd and ld and hd.get("kind") == "aumento" and ld.get("kind") == "aumento":
        series_note = (f"Su tutto il periodo l'aumento più forte è {of_place(hd['name'], lk)} ({signed(hd['delta'], change_unit)}), "
                       f"il più debole {of_place(ld['name'], lk)} ({signed(ld['delta'], change_unit)}).")
    elif hd and ld:
        series_note = (f"Su tutto il periodo la variazione va da {signed(ld['delta'], change_unit)} {of_place(ld['name'], lk)} "
                       f"a {signed(hd['delta'], change_unit)} {of_place(hd['name'], lk)}.")

    # Con la striscia del divario gli estremi, la media e la distanza stanno nel
    # grafico: le tessere dicono solo cio' che il grafico non dice.
    if strip.get("svg"):
        facts = [t for t in tiles if t["role"] == "delta"]
        if stats.get("above_avg_count") is not None:
            facts.append({"label": "Sopra la media semplice", "value": stats["above_avg_count"], "unit": None, "role": "count",
                          "sub": f"{plural} su {stats.get('year_count', n)}, le altre sotto"})
        years_n = len(level.get("years") or [])
        if years_n > 1:
            facts.append({"label": "Anni della serie", "value": years_n, "unit": None, "role": "count",
                          "sub": f"dal {level['year_min']} al {level['year_max']}"})
        tiles = facts
    citation = (f"Divario Italia, «{meta['name']}», elaborazione su dati {meta.get('source_label') or meta.get('source')} "
                f"({year}). {ctx.get('canonical')}")
    module = explore_module(meta, level, claim=claim, strip=strip,
                            tabs=level_tabs(meta, level, ctx.get("levels") or [], ctx.get("twin")))
    # Il confronto fra province, dalla `/province` di una scheda che il
    # confronto offre (la regola dell'indice, `confronto.province_ids`): lo
    # stesso ingresso che la vista regionale ha verso `/confronto`.
    compare = None
    if level["key"] == "provincia":
        from app.design.pages import confronto

        compare = confronto.compare_path(meta, "provincia")
    return {
        "compare_path": compare,
        "fmt": num, "fmt_unit": with_unit, "date_it": date_it, "citation": citation,
        "unit": numfmt.lower_first(unit) if unit else unit, "tiles": tiles, "verso": verso,
        "unit_note": unit_note(unit, meta["name"]), "values_note": values_note(unit),
        "series": series, "strip": strip, "module": module, "within": within_regions(meta, level, unit),
        "strip_mini": charts.mini_strip(rows, stats.get("year_avg")) if strip.get("svg") else "",
        "family": family_paths(ctx),
        "series_claim": series_claim, "series_note": series_note,
        "updated": date_it(ctx.get("dataset_updated")),
        "subtitle": f"{meta['name']}, {('in ' + unit) if unit else ''}, {year}. {n} {plural} dal valore più alto al più basso.".replace(", ,", ","),
    }
