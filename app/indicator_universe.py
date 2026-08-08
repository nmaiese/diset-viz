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

from app import external_atlas, indicator_view, multiscopo_data, sources
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
                 "territory_count": len(level["observations"])}
                for level in view["levels"]
            ],
        })
    return records


@synchronized_cache(maxsize=1)
def indexable_catalog():
    """Le sole pagine indicizzabili, deduplicate per path canonico e ordinate.

    E' quello che leggono `sitemap.xml` e `llms-full.txt`, con la stessa forma di
    prima (`meta` piu' il riassunto per livello). Il dedup su `canonical_path`
    resta **dentro il sottoinsieme indicizzabile**: allargando la passata a tutti
    e 634 sarebbe stato naturale deduplicare prima di filtrare, e un non
    indicizzabile che occupa il path avrebbe buttato fuori dalla sitemap il suo
    gemello indicizzabile. Oggi non ci sono collisioni, ma `DUPLICATE_BES_IDS` e
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


def cache_clear():
    """Svuota la passata e la sua proiezione: serve ai test, che altrimenti
    leggono il catalogo del test precedente. `cache.clear()` di Flask-Caching non
    tocca queste, che non sono memoize."""
    projection.cache_clear()
    indexable_catalog.cache_clear()
