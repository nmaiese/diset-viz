"""La scheda indicatore della 1.0: cio' che il template chiede in piu' ai dati.

Tessere, titolo-affermazione della classifica, la striscia del divario, la
serie a fascia, i richiami sulla mappa e i dati del modulo interattivo. Prende
il contesto che `_render_indicator` passa al template, e non ne cambia niente.
"""

from __future__ import annotations

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
from app.indicator_notes import ds_choropleth_colors


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

    tiles = []
    if best and best["name"] not in lede:
        tiles.append({"label": f"In testa nel {year}", "value": best["value"], "unit": unit, "role": "figure",
                      "sub": best["name"], "href": (level.get("profile_path") or "") + best["key"] if level.get("profile_path") else None})
    if worst and worst["name"] not in lede:
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

    # Il titolo-affermazione della classifica: un fatto verificato sul Mezzogiorno.
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

    areas = charts.area_map()
    obs = level.get("observations") or []
    rows = [{**o, "area": areas.get(o["key"])} for o in obs]
    series = charts.band_series(level, areas) if len(level.get("matrix") or {}) >= 2 else {"svg": "", "single_year": True}
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
        series_note = (f"Su tutto il periodo cresce di più {the_place(hd['name'], lk)} ({signed(hd['delta'], change_unit)}), "
                       f"di meno {the_place(ld['name'], lk)} ({signed(ld['delta'], change_unit)}).")
    elif hd and ld:
        series_note = (f"Su tutto il periodo la variazione va da {signed(ld['delta'], change_unit)} {of_place(ld['name'], lk)} "
                       f"a {signed(hd['delta'], change_unit)} {of_place(hd['name'], lk)}.")

    values = [o["value"] for o in level.get("observations") or [] if o.get("value") is not None]
    explore_js = {
        "years": [int(y) for y in sorted(level.get("matrix") or {}, key=int)],
        "matrix": level.get("matrix") or {},
        "names": {t["key"]: t["name"] for t in level.get("territories") or []},
        "unit": numfmt.phrase_unit(unit), "direction": direction, "plural": plural,
        "decimals": numfmt.column_decimals([o["value"] for o in obs]), "areas": {o["key"]: areas.get(o["key"]) for o in obs},
        "profile": level.get("profile_path"), "south": sorted(MEZZOGIORNO) if level["key"] == "regione" else [],
    }
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
    # Le voci del selettore di livello: quelli della scheda e, se ne manca uno,
    # quello della gemella. Prima le regioni, come in tutto il sito.
    level_tabs = [{"key": lv["key"], "label": lv["label"], "current": lv["key"] == level["key"],
                   "href": f"{meta['canonical_path']}?livello={lv['key']}"} for lv in ctx.get("levels") or []]
    twin = ctx.get("twin")
    if twin and level_tabs:
        level_tabs.append({"key": twin["key"], "label": twin["label"], "current": False, "href": twin["path"]})
    level_tabs.sort(key=lambda t: 0 if t["key"] == "regione" else 1)
    citation = (f"Divario Italia, «{meta['name']}», elaborazione su dati {meta.get('source_label') or meta.get('source')} "
                f"({year}). {ctx.get('canonical')}")
    return {
        "fmt": num, "fmt_unit": with_unit, "date_it": date_it, "citation": citation,
        "map_values": {o["key"]: with_unit(o["value"], unit) for o in level.get("observations") or []},
        "unit": numfmt.lower_first(unit) if unit else unit, "short_unit": short_unit(unit), "tiles": tiles, "verso": verso,
        "unit_note": unit_note(unit, meta["name"]), "values_note": values_note(unit),
        "claim": claim, "map_classes": classes, "show_map": show_map, "map_names": map_names,
        "map_missing": show_map and bool(set(maps.paths(level["key"])) - {o["key"] for o in obs}),
        "legend": legend(values, unit) if values else None,
        "ranking": ranking(level, unit), "series": series, "strip": strip, "callouts": callouts,
        "areas": {o["key"]: areas.get(o["key"]) for o in obs}, "area_label": charts.AREA_LABEL,
        "decimals": numfmt.column_decimals([o["value"] for o in obs]), "series_claim": series_claim, "series_note": series_note,
        "updated": date_it(ctx.get("dataset_updated")), "explore_js": explore_js, "level_tabs": level_tabs,
        "subtitle": f"{meta['name']}, {('in ' + unit) if unit else ''}, {year}. {n} {plural} dal valore più alto al più basso.".replace(", ,", ","),
    }
