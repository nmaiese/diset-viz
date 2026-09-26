"""La metodologia della 1.0: la stessa prosa, con la regia delle pagine lunghe.

La vista passa gia' tutto cio' che la pagina dice (il metodo della classifica
per i due livelli, le categorie, i profili, le serie del punteggio). Qui si
compongono solo due cose: l'indice di pagina, con le voci delle sezioni che ci
sono davvero, e le serie del punteggio raggruppate per categoria, nello stesso
ordine del `groupby` del template di prima.

Le ancore restano quelle di prima (`#come-nasce-il-testo`,
`#qualita-della-vita`, `#indicatori-usati`), perche' le schede, la classifica e
l'indice della qualita' della vita ci linkano. Le sezioni che non avevano un
id ne prendono uno nuovo, per l'indice.
"""

from __future__ import annotations

from itertools import groupby


def _indicator_groups(items: list[dict]) -> list[dict]:
    """Le serie del punteggio per categoria, in ordine alfabetico di categoria
    come faceva `groupby` in Jinja, con l'ordine delle serie dentro invariato."""
    key = lambda item: item.get("quality_life_category_label") or ""  # noqa: E731
    return [
        {"name": name, "items": list(group)}
        for name, group in groupby(sorted(items, key=key), key=key)
    ]


def derive(ctx: dict) -> dict:
    indicators = ctx.get("quality_life_indicators") or []
    groups = _indicator_groups(indicators)
    toc = [
        ("fonte", "Fonte principale"),
        ("leggere", "Come leggere gli indicatori"),
        ("come-nasce-il-testo", "Come nasce il testo"),
        ("qualita-della-vita", "Qualità della vita"),
    ]
    if groups:
        toc.append(("indicatori-usati", "Gli indicatori del punteggio"))
    toc += [("limiti", "Limiti"), ("domande", "Domande frequenti")]
    return {
        "toc": [{"id": anchor, "label": label} for anchor, label in toc],
        "indicator_groups": groups,
        "indicator_count": len(indicators),
    }
