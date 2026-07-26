"""Everything an editor needs about one indicator, on one screen.

This exists because of *why* the indicator prose reads as banal. The writer used
to hunt for figures through the JSON API, one call at a time, and ended up
writing against a thin slice of the data: the top region, the bottom region, the
mean. That is exactly the slice the cockpit already prints, so the prose could
only restate it.

With the whole distribution in front of you the requirement to carry "one fact a
template could not generate" becomes satisfiable instead of aspirational. The
brief deliberately surfaces the things that are invisible from a top-three
listing:

- the full ranking with each territory's change since the first year, so a
  divide that is not north/south is visible
- where the big jumps in the sorted values are, which is what "two speeds"
  actually means
- which territories moved against the general direction
- what the page will already say on its own, so you do not write it twice
- which other indicators of the same theme draw the same map as this one, which
  draw the opposite one, and which draw a map that has nothing to do with it,
  each with the canonical path to link it

That last block is the one that lets an article stop living inside its own
series. It exists because every article written before it did: the brief was
mono-indicator, so the prose had no handle on anything beyond its own ranking,
and no article in the catalogue linked to another one.

Usage:

    .venv/bin/python -m scripts.indicator_brief ter-178
    .venv/bin/python -m scripts.indicator_brief bes-01SAL001 --level provincia
    .venv/bin/python -m scripts.indicator_brief ter-178 --json

Every figure printed here is computed from the same code path that renders the
page, so a number quoted from this brief cannot disagree with the page.
"""

import argparse
import json
import sys

from app import sources
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator
from app.indicator_texts import DEFAULT_HEADINGS, ROLE_ORDER, build_article, get_text
from app.indicator_view import build_indicator_view

# How many indicators to show per relationship group (same map, opposite map,
# unrelated map). Three groups of four is a menu an editor can read; the whole
# theme, which can be eighty indicators, is a table nobody uses.
RELATED_PER_GROUP = 4
# Below this many shared regions a rank correlation says nothing, it just
# describes the handful of territories both series happen to cover.
MIN_COMMON_REGIONS = 12
# Where "same map" starts and "different map" ends. Deliberately wide in the
# middle: an indicator at rho 0,45 shares a tendency with this one and no more,
# and presenting that as a shape is how a co-occurrence turns into a claim.
SAME_MAP = 0.6
DIFFERENT_MAP = 0.3
# Above this, the two series are usually two cuts of the same measurement (the
# same rate on a different age band, the male and the female version), and
# "cammina di pari passo con" is a tautology dressed as a finding.
TWIN_RHO = 0.95


def _num(value, decimals=2):
    if value is None:
        return "n.d."
    return f"{value:,.{decimals}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _signed(value, decimals=2):
    return ("+" if value >= 0 else "") + _num(value, decimals)


def _resolve(code):
    """Accept the URL form (ter-178, bes-01SAL001) or a bare territorial id."""
    parsed = sources.parse_indicator_code(code)
    if parsed is not None:
        return parsed
    return "territorial", code


def _text_for_level(indicator_id, level_key):
    """The stored entry only if it was written for this level, else None."""
    from app.indicator_texts import DEFAULT_LEVEL

    entry = get_text(indicator_id)
    if not entry:
        return None
    return entry if (entry.get("level") or DEFAULT_LEVEL) == level_key else None


def build_brief(family, raw_id, level_key=None):
    view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    meta = view["meta"]
    level = next((lv for lv in view["levels"] if lv["key"] == level_key), view["levels"][0])
    stats = level["stats"]

    first_year = stats["year_min"]
    first_values = {}
    for key, value in (level["matrix"].get(str(first_year)) or {}).items():
        first_values[key] = value

    rows = []
    for position, row in enumerate(level["observations"], start=1):
        start = first_values.get(row["key"])
        rows.append({
            "rank": position,
            "name": row["name"],
            "value": row["value"],
            "first_value": start,
            "delta": None if start is None else row["value"] - start,
        })

    return {
        "meta": meta,
        "view": view,
        "level": level,
        "stats": stats,
        "rows": rows,
        # Both keyed on the level actually being briefed. Without it, asking for
        # `--level provincia` printed the state of the *regional* article: on a
        # two-level BES the brief said "lead scritto, quadro scritto" while the
        # provincial page was still the composed skeleton from top to bottom.
        "article": build_article(meta["id"], level["key"]),
        "has_text": _text_for_level(meta["id"], level["key"]) is not None,
        "breaks": _distribution_breaks(rows),
        "against_the_grain": _against_the_grain(rows, stats),
        # Always computed over the regions, whatever level is being briefed:
        # the sibling series are regional, so a provincial brief still gets the
        # relationships, stated as what they are.
        "related": _related_indicators(meta, _anchor_territories(view)),
    }


def _anchor_territories(view):
    """The two regions an article is most likely to name: top and bottom."""
    regional = next((lv for lv in view["levels"] if lv["key"] == "regione"), None)
    if regional is None:
        return []
    return [item for item in (regional.get("best"), regional.get("worst")) if item]


def _distribution_breaks(rows, top=3):
    """The widest gaps between consecutive values in the ranking.

    A "two speeds" claim means the sorted values have a step in them. This finds
    where, so the claim can be made about a real discontinuity or dropped.
    """
    gaps = []
    for previous, current in zip(rows, rows[1:]):
        gaps.append({
            "after_rank": previous["rank"],
            "between": (previous["name"], current["name"]),
            "size": abs(previous["value"] - current["value"]),
        })
    gaps.sort(key=lambda gap: gap["size"], reverse=True)
    return gaps[:top]


def _against_the_grain(rows, stats):
    """Territories that moved opposite to the overall average movement.

    These are the counter-examples that stop a sentence like "it grew
    everywhere" from being written when it is not true.
    """
    overall = stats.get("avg_change_abs")
    if overall is None:
        return []
    moved = [row for row in rows if row["delta"] is not None]
    if overall >= 0:
        return [row for row in moved if row["delta"] < 0]
    return [row for row in moved if row["delta"] > 0]


def _regional_vector(payload):
    """{region_key: value} in the most recent year the series covers."""
    series = (payload or {}).get("series") or []
    years = [row["year"] for row in series if row.get("value") is not None]
    if not years:
        return {}, None
    year = max(years)
    vector = {
        row["region_key"]: row["value"]
        for row in series
        if row["year"] == year and row.get("value") is not None
    }
    return vector, year


def _average_ranks(values):
    """Ranks from 1, ties sharing their average rank.

    Ties are not a corner case here: several series are percentages rounded to
    one decimal over twenty regions, so two regions land on the same value
    regularly, and ranking them arbitrarily would move rho by a tenth.
    """
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        shared = (position + end) / 2 + 1
        for index in order[position:end + 1]:
            ranks[index] = shared
        position = end + 1
    return ranks


def _spearman(first, second):
    """Rank correlation of two {region: value} maps over the regions they share.

    Rank rather than linear on purpose: these series carry different units and
    very different distributions, several of them skewed by one alpine outlier,
    and the question an editor is asking is about the order of the territories,
    not about a linear fit.
    """
    common = sorted(set(first) & set(second))
    if len(common) < MIN_COMMON_REGIONS:
        return None, len(common)
    left = _average_ranks([first[key] for key in common])
    right = _average_ranks([second[key] for key in common])
    count = len(common)
    mean_left = sum(left) / count
    mean_right = sum(right) / count
    covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    spread_left = sum((a - mean_left) ** 2 for a in left) ** 0.5
    spread_right = sum((b - mean_right) ** 2 for b in right) ** 0.5
    if not spread_left or not spread_right:
        # A constant series has no order to correlate with.
        return None, count
    return covariance / (spread_left * spread_right), count


def _placement(vector, region_key):
    """Position of one region on another indicator's scale, by value descending.

    Descending value, never the page's merit order: the merit order flips on a
    `lower_better` indicator, so "#2" would mean the second highest here and the
    second lowest there, and the sentence built on it would be backwards.
    """
    if region_key not in vector:
        return None
    ordered = sorted(vector.values(), reverse=True)
    return {
        "value": vector[region_key],
        "rank": ordered.index(vector[region_key]) + 1,
        "of": len(ordered),
    }


def _strongest(rows):
    """The group, with the probable duplicates pushed to the back.

    Sorting a "same map" group by rho alone fills it with the same measurement
    cut a second way: on female employment the top four were the 20-64 band, the
    activity rate, overall participation and the over-54 band, all above 0,97,
    and an article that cross-references one of those has said nothing. Distinct
    indicators lead, the near-twins stay visible only to backfill.
    """
    distinct = [row for row in rows if abs(row["rho"]) < TWIN_RHO]
    twins = [row for row in rows if abs(row["rho"]) >= TWIN_RHO]
    return (distinct + twins)[:RELATED_PER_GROUP]


def _related_indicators(meta, anchors):
    """Theme siblings grouped by the shape of the divide they draw.

    The page's own "related" list is the theme in alphabetical order, truncated
    at eight, which is a fine table and a useless starting point for a
    cross-reference: it answers "what else is filed here", not "what does this
    number travel with". Here the whole theme is ranked by rank correlation and
    split into three groups, because the editorially interesting one is not the
    strongest correlation. It is the indicator that draws a *different* map,
    the one that breaks the north-south reflex the atlas trains.

    `anchors` are the two territories the article will most likely name, the
    extremes of this indicator's own ranking, placed on each sibling's scale so
    a comparison can be written without a second command.
    """
    theme = meta.get("theme")
    if not theme:
        return {"hub": None, "groups": {}, "self_year": None}

    own_payload = get_atlas_indicator(meta["id"])
    own_vector, own_year = _regional_vector(own_payload)
    scored = []
    for item in get_atlas_catalog()["indicators"]:
        if item["theme"] != theme or str(item["id"]) == str(meta["id"]):
            continue
        vector, year = _regional_vector(get_atlas_indicator(item["id"]))
        if not vector:
            continue
        rho, common = (None, 0) if not own_vector else _spearman(own_vector, vector)
        scored.append({
            "id": item["id"],
            "name": item["name"],
            # Never rebuilt: the families truncate the slug differently and the
            # catalog is the only place that knows how (app/indicator_view.py).
            "path": item["path"],
            "direction": (item.get("explain") or {}).get("direction"),
            "year": year,
            "rho": rho,
            "common": common,
            "anchors": [
                {"name": anchor["name"], **(_placement(vector, anchor["key"]) or {})}
                for anchor in anchors
            ],
        })

    ranked = [row for row in scored if row["rho"] is not None]
    ranked.sort(key=lambda row: abs(row["rho"]), reverse=True)
    groups = {
        "stessa": _strongest([row for row in ranked if row["rho"] >= SAME_MAP]),
        "opposta": _strongest([row for row in ranked if row["rho"] <= -SAME_MAP]),
        # Weakest first: rho near zero is the cleanest "these two have nothing
        # to do with each other", which is the claim this group is for.
        "diversa": sorted(
            (row for row in ranked if abs(row["rho"]) < DIFFERENT_MAP),
            key=lambda row: abs(row["rho"]),
        )[:RELATED_PER_GROUP],
    }
    return {
        "hub": {"path": meta.get("theme_path"), "name": theme},
        "groups": groups,
        "self_year": own_year,
        "theme_size": len(scored),
    }


GROUP_TITLES = {
    "stessa": ("DISEGNANO LA STESSA MAPPA", "gli stessi territori in alto e in basso"),
    "opposta": ("DISEGNANO LA MAPPA OPPOSTA", "dove uno sale l'altro scende"),
    "diversa": ("DISEGNANO UNA MAPPA DIVERSA",
                "la geografia qui non c'entra, ed e' spesso la cosa piu interessante da dire"),
}


def _render_related(brief):
    related = brief["related"]
    out = []
    add = out.append
    add("INDICATORI CORRELATI  (la materia prima di un incrocio e dei link interni)")
    if not related.get("groups"):
        add("  questo indicatore non ha un tema, quindi non ha fratelli con cui incrociarlo")
        add("")
        return "\n".join(out)

    hub = related["hub"] or {}
    if hub.get("path"):
        add(f"  hub del tema  {hub['path']}   ({hub['name']}, {related['theme_size']} indicatori)")
    add("  rho e' la correlazione di rango sui valori regionali dell'ultimo anno di ciascuna")
    add("  serie. Dice se due indicatori mettono i territori nello stesso ordine, non che")
    add("  uno causi l'altro: e' una co-occorrenza e va scritta come tale. Le posizioni")
    add("  sono per valore decrescente, non per merito.")
    add(f"  Sopra {_num(TWIN_RHO)} guarda il nome prima di scrivere: di solito e' lo stesso")
    add("  fenomeno misurato su un'altra fascia o sull'altro sesso, e dirlo non e' una notizia.")
    if brief["level"]["key"] != "regione":
        add(f"  ATTENZIONE: rho e' calcolata sulle regioni, e tu stai scrivendo sul livello "
            f"{brief['level']['key']}.")
    add("")

    empty = True
    for group in ("stessa", "opposta", "diversa"):
        rows = related["groups"].get(group) or []
        if not rows:
            continue
        empty = False
        title, gloss = GROUP_TITLES[group]
        add(f"  {title}  ({gloss})")
        for row in rows:
            verso = row["direction"] or "senza verso"
            twin = "  <- forse la stessa cosa misurata due volte" if row["rho"] >= TWIN_RHO else ""
            add(f"    rho {_signed(row['rho'])} su {row['common']} regioni   {row['name']}{twin}")
            add(f"      {row['path']}   ({verso}, ultimo anno {row['year']})")
            placements = [
                f"{anchor['name']} {_num(anchor['value'])} (#{anchor['rank']} su {anchor['of']})"
                for anchor in row["anchors"] if anchor.get("rank")
            ]
            if placements:
                add(f"      le due estreme di qui, la: {', '.join(placements)}")
        add("")
    if empty:
        add("  nessun fratello di tema con abbastanza regioni in comune per un confronto")
        add("")
    return "\n".join(out)


def render(brief):
    meta, level, stats = brief["meta"], brief["level"], brief["stats"]
    out = []
    add = out.append

    add("=" * 78)
    add(f"{meta['name']}")
    add(f"{sources.indicator_url(meta['family'], meta['raw_id'], 'slug')}  ({meta['id']})")
    add("=" * 78)
    add("")
    add("ANAGRAFICA")
    add(f"  famiglia        {meta['family_label']}")
    add(f"  tema            {meta['theme']}   (sottotema: {meta['source_theme'] or '-'})")
    add(f"  unita           {meta['value_unit']}   variazioni in: {meta['change_unit']}")
    add(f"  direzione       {meta['direction']}   {'(ha un verso)' if meta['scoreable'] else '(CONTESTUALE, nessun migliore)'}")
    add(f"  fonte           {meta['source_label']}")
    add(f"  definizione     {meta['archive'] or '-'}")
    add(f"  indicizzabile   {meta['indexable']}")
    add(f"  nel punteggio   {meta['quality_life_scored']}")
    add("")

    levels = ", ".join(f"{lv['label']} ({lv['year_min']}-{lv['year_max']}, {len(lv['observations'])})"
                       for lv in brief["view"]["levels"])
    add(f"LIVELLI DISPONIBILI  {levels}")
    add(f"LIVELLO IN QUESTO BRIEF  {level['label']}, anni {level['years']}")
    add("")

    add(f"DISTRIBUZIONE {level['year_max']}")
    add(f"  media {_num(stats['year_avg'])}   mediana {_num(stats['median'])}   "
        f"divario {_num(stats['gap_abs'])}"
        + (f" ({_num(stats['gap_ratio'], 1)}x)" if stats["gap_ratio"] else ""))
    if stats["above_avg_count"] is not None:
        add(f"  sopra la media {stats['above_avg_count']}, sotto {stats['below_avg_count']}")
    add("")
    add(f"  {'#':>3}  {'territorio':<28} {'valore':>10} {'dal ' + str(stats['year_min']):>12}")
    for row in brief["rows"]:
        delta = "" if row["delta"] is None else f"{'+' if row['delta'] > 0 else ''}{_num(row['delta'])}"
        add(f"  {row['rank']:>3}  {row['name']:<28} {_num(row['value']):>10} {delta:>12}")
    add("")

    if brief["breaks"]:
        add("SALTI PIU AMPI NELLA GRADUATORIA  (dove la distribuzione si spezza davvero)")
        for gap in brief["breaks"]:
            add(f"  dopo il #{gap['after_rank']}: {gap['between'][0]} -> {gap['between'][1]}, "
                f"stacco di {_num(gap['size'])}")
        add("")

    add("ANDAMENTO")
    if stats["has_multi_year"]:
        add(f"  media {stats['year_min']}: {_num(stats['year_min_avg'])}  ->  "
            f"{stats['year_max']}: {_num(stats['year_avg'])}   "
            f"({_num(stats['avg_change_abs'])} {meta['change_unit']})")
        if stats["gap_trend"] is not None:
            verb = "allargato" if stats["gap_trend"] > 0 else "ristretto"
            add(f"  il divario si e {verb} di {_num(abs(stats['gap_trend']))} {meta['change_unit']}")
        if stats["highest_delta"]:
            add(f"  delta massimo   {stats['highest_delta']['name']}  {_num(stats['highest_delta']['delta'])}")
        if stats["lowest_delta"]:
            add(f"  delta minimo    {stats['lowest_delta']['name']}  {_num(stats['lowest_delta']['delta'])}")
    else:
        add("  serie a un solo anno, nessun confronto temporale possibile")

    contrarian = brief["against_the_grain"]
    add("")
    if contrarian:
        add("SI MUOVONO CONTROCORRENTE  (smentiscono ogni 'e cresciuto ovunque')")
        for row in contrarian:
            add(f"  {row['name']}: {_num(row['first_value'])} -> {_num(row['value'])} ({_num(row['delta'])})")
    else:
        add("SI MUOVONO CONTROCORRENTE  nessuno: il movimento e nella stessa direzione ovunque")
    add("")

    annual = level["annual_change"]
    if annual:
        add(f"ULTIMO PASSAGGIO  {annual['previous_year']} -> {annual['year']}  "
            f"(base comune: {annual['common_count']})")
        add(f"  media {_num(annual['previous_avg'])} -> {_num(annual['current_avg'])} "
            f"({_num(annual['average_delta'])} {meta['change_unit']})")
        add(f"  in calo {annual['decrease_count']}, in aumento {annual['increase_count']}, "
            f"stabili {annual['stable_count']}")
        add("")

    add(_render_related(brief))

    add("-" * 78)
    add("GIA DETTO DALLA PAGINA, NON RISCRIVERLO")
    add("  Il cruscotto stampa da solo: valore del territorio a fuoco e suo rango,")
    add("  valore piu alto e piu basso con i nomi, media, divario (assoluto e")
    add(f"  rapporto), variazione rispetto al {annual['previous_year'] if annual else 'n.d.'}.")
    add("  Ripetere queste cifre in prosa e la duplicazione che il layout ha tolto.")
    add("")
    add("STATO DELL'ARTICOLO")
    article = brief["article"]
    add(f"  lead   {'scritto' if article['lead'] else 'DA SCRIVERE (ora composto dal template)'}")
    for section in article["sections"]:
        status = "scritto" if section["authored"] else "DA SCRIVERE (ora composto dal template)"
        heading = section["heading"]
        default = DEFAULT_HEADINGS[section["role"]]
        title = heading if heading != default else f"{default}  [titolo di default]"
        add(f"  {section['role']:<12} {status}")
        add(f"  {'':<12} h2: {title}")
    add(f"  vintage  {article['vintage'] or 'assente'}   (deve valere {level['year_max']})")
    add(f"  livello  {level['key']}   (l'articolo va scritto con \"level\": \"{level['key']}\")")
    if len(brief["view"]["levels"]) > 1:
        add("           un articolo vale per un livello solo, gli altri restano composti")
    add("-" * 78)
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("code", help="indicator code as in the URL, e.g. ter-178 or bes-01SAL001")
    parser.add_argument("--level", help="territorial level (regione, provincia)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    family, raw_id = _resolve(args.code)
    brief = build_brief(family, raw_id, args.level)
    if brief is None:
        print(f"indicatore non trovato: {args.code}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "id": brief["meta"]["id"],
            "name": brief["meta"]["name"],
            "unit": brief["meta"]["value_unit"],
            "direction": brief["meta"]["direction"],
            "level": brief["level"]["key"],
            "year_max": brief["level"]["year_max"],
            "stats": brief["stats"],
            "rows": brief["rows"],
            "breaks": brief["breaks"],
            "against_the_grain": brief["against_the_grain"],
            "annual_change": brief["level"]["annual_change"],
            "article": brief["article"],
            "related": brief["related"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=1, default=str))
    else:
        print(render(brief))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
