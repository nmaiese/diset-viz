"""L'universo degli indicatori con una pagina pubblica, in una passata sola.

Sono 634, e non coincidono con i 594 del catalogo dell'atlante: 40 serie BES
hanno solo osservazioni provinciali, quindi non entrano nel catalogo regionale
ma la loro pagina esiste. Chi conta gli indicatori partendo dal catalogo ne
perde quaranta senza che niente diventi rosso.

Questa passata la faceva gia' la sitemap, che pero' scartava i non
indicizzabili subito e non lasciava niente per chi deve guardare **tutto**
l'atlante (il cruscotto editoriale). Allargarla e' costato 0,2 s e 1,5 MB,
perche' le viste erano gia' calde: affiancarne una seconda sarebbe costato
un'altra traversata e un altro picco di memoria.

**Si tiene una proiezione compatta, non le viste.** Una vista intera porta la
storia delle osservazioni di ogni livello e la matrice anno per territorio, e
tenerle tutte per la vita del processo costava ~110 MiB per worker al primo
passaggio di un crawler. Qui resta `meta` piu' un riassunto per livello, e la
vista pesante si butta appena preso il riassunto. Chi legge non deve mutare il
risultato.
"""

from app import external_atlas, indicator_view, multiscopo_data, seo_policy, sources
from app.atlas_catalog import _downsample
from app.bes_data import all_bes_indicators
from app.cache_util import synchronized_cache
from app.data import get_catalog


def all_indicator_refs():
    """`(famiglia, raw_id)` per ogni indicatore che ha una pagina pubblica.

    Si parte dai registri di famiglia e non dal catalogo dell'atlante, che e' la
    ragione per cui le 40 serie BES solo provinciali restano dentro.
    """
    refs = [("territorial", str(item["id"])) for item in get_catalog()["indicators"]]
    refs.extend(("bes", str(item["id"])) for item in all_bes_indicators())
    if multiscopo_data.has_multiscopo_data():
        refs.extend(("multiscopo", str(item["id"]))
                    for item in multiscopo_data.all_multiscopo_indicators())
    if external_atlas.has_external_data():
        refs.extend(sources.split_internal_id(item["id"])
                    for item in external_atlas.all_external_indicators())
    return refs


@synchronized_cache(maxsize=1)
def projection():
    """Un record compatto per ognuno dei 634, indicizzabili e non.

    `synchronized_cache` e non `lru_cache`: `lru_cache` non coalizza i miss
    concorrenti, e il worker gunicorn di produzione ha otto thread. Due crawler
    simultanei a freddo entravano entrambi nel corpo e rifacevano la traversata
    per intero, con la memoria che passava da 221 a 463 MB.

    Cache per la **vita del processo**, non a tempo: il risultato e' funzione
    pura del contenuto dell'immagine, e i loader delle fonti sono gia' congelati
    allo stesso modo. Un deploy ricrea il processo, che e' l'unico momento in cui
    questo puo' cambiare.
    """
    records = []
    for family, raw_id in all_indicator_refs():
        view = indicator_view.build_indicator_view(family, raw_id)
        if view is None:
            continue
        records.append({
            "family": family,
            "raw_id": raw_id,
            "meta": view["meta"],
            "default_level": view["default_level"],
            "levels": [
                {"key": level["key"], "label": level["label"],
                 "year_min": level["year_min"], "year_max": level["year_max"],
                 "territory_count": len(level["observations"]),
                 "panel": _compact_panel(level)}
                for level in view["levels"]
            ],
        })
    return records


def _compact_panel(level):
    """La serie della sparkline sul pannello fisso (`indicator_view.fixed_panel`),
    al massimo 24 punti: e' la sola parte della serie che la proiezione tiene,
    e la leggono l'atlante e chi disegnera' la fascia in home. None quando il
    pannello non arriva a tre anni."""
    panel = indicator_view.fixed_panel(level)
    if panel is None:
        return None
    return {**panel, "points": _downsample(panel["points"], indicator_view.PANEL_MAX_POINTS)}


@synchronized_cache(maxsize=1)
def indexable_catalog():
    """Le sole pagine indicizzabili, deduplicate per path canonico e ordinate.

    E' quello che leggono `sitemap.xml` e `llms-full.txt`, con la stessa forma di
    prima (`meta` piu' il riassunto per livello). Il dedup su `canonical_path`
    resta **dentro il sottoinsieme indicizzabile**: allargando la passata a tutti
    e 634 sarebbe stato naturale deduplicare prima di filtrare, e un non
    indicizzabile che occupa il path avrebbe buttato fuori dalla sitemap il suo
    gemello indicizzabile. Oggi non ci sono collisioni, ma `TERRITORIAL_NAME_TWINS` e
    `PROVINCE_ONLY_TITLE_COLLISIONS` esistono perche' sono reali.
    """
    catalog = []
    seen_paths = set()
    for record in projection():
        if not record["meta"]["indexable"]:
            continue
        path = record["meta"]["canonical_path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        catalog.append({"meta": record["meta"], "levels": record["levels"]})
    return sorted(catalog, key=lambda record: record["meta"]["canonical_path"])


def level_pages(listed=False):
    """Una voce per ogni pagina di livello indicizzabile, in ordine di path.

    Una scheda indicizzabile e' una pagina per la sua base, e una seconda per
    la sua `/province` quando ha tutti e due i livelli e il livello provinciale
    passa la regola (`indicator_view.level_passes_rule`, e l'interruttore
    `seo_policy.LEVEL_PAGES_INDEXABLE`). La leggono sitemap, llms-full e
    `scripts/duplicazione.py`: le viste provinciali sono URL a se', e cio' che
    le elenca o le misura le deve vedere. `indexable_catalog()` resta una voce
    per scheda, con la sua forma. Manca la base che ha il canonical su un'altra
    scheda (`indicator_view.canonical_elsewhere`, la vista regionale di
    bes-01SAL001): indicizzabile, ma elencata dalla sua canonica.

    Ogni voce: `meta` e `levels` della scheda (come in `indexable_catalog`),
    `level` (il riassunto del livello), `path` (il canonico del livello) e
    `base` (vero sulla pagina base della scheda).

    Con `listed=True` ci sono anche le `/province` che la regola ammette ma
    l'interruttore `seo_policy.LEVEL_PAGES_INDEXABLE` spento tiene fuori
    dall'indice: la ricerca le deve trovare lo stesso, perche' l'interruttore
    toglie l'indice e non i link. Senza, le sole indicizzabili. L'interruttore
    si legge a ogni chiamata, quindi spegnerlo non chiede di svuotare cache.
    """
    pages = _rule_level_pages()
    if listed or seo_policy.LEVEL_PAGES_INDEXABLE:
        return pages
    return [page for page in pages if page["base"]]


@synchronized_cache(maxsize=1)
def _rule_level_pages():
    """Le pagine di livello che passano la regola (`level_passes_rule`)."""
    pages = []
    for record in indexable_catalog():
        meta, levels = record["meta"], record["levels"]
        base_key = levels[0]["key"]
        for level in levels:
            if not indicator_view.level_passes_rule(meta, level["key"], base_key):
                continue
            # Una vista col canonical su un'altra scheda (bes-01SAL001 regionale,
            # verso ter-910) resta indicizzabile, cioe' senza `noindex`, ma la
            # sitemap e llms-full elencano solo la scheda canonica.
            if indicator_view.canonical_elsewhere(meta, level["key"]):
                continue
            pages.append({
                "meta": meta,
                "levels": levels,
                "level": level,
                "path": sources.level_path(meta["canonical_path"], level["key"], base_key),
                "base": level["key"] == base_key,
            })
    return sorted(pages, key=lambda page: page["path"])


def cache_clear():
    """Svuota la passata e la sua proiezione: serve ai test, che altrimenti
    leggono il catalogo del test precedente. `cache.clear()` di Flask-Caching non
    tocca queste, che non sono memoize."""
    projection.cache_clear()
    indexable_catalog.cache_clear()
    _rule_level_pages.cache_clear()
    # Le righe dell'atlante nascono dalla proiezione: vanno via con lei.
    # L'import sta qui perche' la pagina importa questo modulo.
    from app.design.pages import atlante

    atlante.rows.cache_clear()
