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
from app.indicator_texts import DEFAULT_HEADINGS, ROLE_ORDER, build_article, get_text
from app.indicator_view import build_indicator_view


def _num(value, decimals=2):
    if value is None:
        return "n.d."
    return f"{value:,.{decimals}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _resolve(code):
    """Accept the URL form (ter-178, bes-01SAL001) or a bare territorial id."""
    parsed = sources.parse_indicator_code(code)
    if parsed is not None:
        return parsed
    return "territorial", code


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
        "article": build_article(meta["id"]),
        "has_text": get_text(meta["id"]) is not None,
        "breaks": _distribution_breaks(rows),
        "against_the_grain": _against_the_grain(rows, stats),
    }


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
        }
        print(json.dumps(payload, ensure_ascii=False, indent=1, default=str))
    else:
        print(render(brief))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
