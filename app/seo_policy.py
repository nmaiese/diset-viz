"""SEO policy overrides for public indicator landing pages."""

import csv
import functools
import logging
from pathlib import Path

from app.data import get_catalog


MIN_INDEXABLE_YEAR = 2020
MIN_COMPLETENESS = 0.98
REQUIRED_REGION_COUNT = 20
# Sta in `config/` e non in `reports/` perche' il Dockerfile non copia
# `reports/` nell'immagine: li' il file mancherebbe in produzione e la regola
# fallirebbe aperta in silenzio. Un file letto a runtime vuole la sua COPY.
INDICATOR_CLASSIFICATION = (
    Path(__file__).resolve().parents[1] / "config" / "indicator_search_metrics.csv"
)

_log = logging.getLogger(__name__)
_warned_missing_classification = False

# Exploration query parameters that put an indicator or region page into an
# in-page state (a chosen year, a focused region, a territorial level). They
# never create a new document: the canonical stays the URL of the page (for an
# indicator, the URL of the level it renders, `level["canonical_path"]`) and the
# variant is kept out of the index and the sitemap. Keeping the list here makes it the
# single source of truth shared by the views and any future sitemap check.
#
# `livello` switched an indicator page between regions and provinces. Oggi la
# vista provinciale di una scheda a due livelli ha il suo URL,
# `/indicatore/<slug>/<codice>/province`, e ogni `?livello=` risponde con un 301
# in un salto solo (alla `/province` o alla base, tenendo `anno` e `regione`).
# Resta qui lo stesso: dopo i 301 non rende piu' una pagina, e se il ripiego
# dovesse tornare a renderla deve restare fuori dall'indice.
EXPLORE_PARAMS = ("anno", "regione", "livello")

# L'interruttore delle viste di livello. A True la `/province` di una scheda a
# due livelli e' indicizzabile, e sta nella sitemap, quando il suo livello
# provinciale passa la regola di `bes_data.all_bes_indicators` (copertura almeno
# 0,8 e anno almeno 2023): 17 su 34. A False tutte le `/province` diventano
# `noindex, follow` ed escono dalla sitemap, mentre link e 301 restano: e' il
# modo di tornare indietro se Google le fonde con la base, senza togliere URL.
# Non tocca la base delle schede ne' le schede solo provinciali.
LEVEL_PAGES_INDEXABLE = True


@functools.lru_cache(maxsize=1)
def indicator_search_metrics():
    """Metriche GSC versionate per indicatore, raccolte nei 28 giorni al 3/10."""
    try:
        with INDICATOR_CLASSIFICATION.open(encoding="utf-8", newline="") as stream:
            rows = csv.DictReader(stream)
            return {
                row["indicatore"]: {
                    "impressions": int(row["impressioni"]),
                    "clicks": int(row["clic"]),
                    "class": row["classe"],
                }
                for row in rows
            }
    except (OSError, KeyError, TypeError, ValueError):
        # Un file assente o illeggibile non deve togliere per errore tutto
        # l'atlante dall'indice. I test verificano presenza, forma e conteggi.
        # Il fallimento aperto resta, ma non piu' in silenzio: una volta sola,
        # col percorso, cosi' in produzione si vede il buco e non una regola muta.
        global _warned_missing_classification
        if not _warned_missing_classification:
            _warned_missing_classification = True
            _log.warning(
                "metriche GSC non leggibili da %s: la regola del contenuto risponde "
                "True per tutto",
                INDICATOR_CLASSIFICATION,
            )
        return {}


def _has_authored_prose(indicator_id):
    """True con un lead o almeno un corpo di sezione scritto."""
    from app import indicator_texts

    entry = indicator_texts.get_text(indicator_id) or {}
    if (entry.get("lead") or "").strip():
        return True
    return any(
        (section.get("body") or "").strip()
        for section in entry.get("sections") or []
        if isinstance(section, dict)
    )


def indicator_passes_content_rule(item):
    """Tiene una scheda con impressioni GSC o prosa scritta.

    Indicatori non presenti nella fotografia GSC restano invariati. Una scheda
    senza impressioni rientra da sola al deploy successivo quando riceve prosa.
    """
    indicator_id = str(item.get("id") or "")
    metrics = indicator_search_metrics().get(indicator_id)
    if metrics is None or metrics["impressions"] > 0:
        return True
    return _has_authored_prose(indicator_id)


def has_explore_params(args):
    """True when the request carries an in-page exploration state.

    ``args`` is a Werkzeug ``MultiDict`` (``request.args``). A page in this
    state renders the same content as its canonical base URL, so it must be
    served ``noindex, follow`` while pointing its canonical back to the base.
    """
    return any(args.get(name) for name in EXPLORE_PARAMS)


def is_search_indexable_indicator(original_policy, item):
    """Return True only for complete, fresh, canonical indicator pages.

    The baseline policy in ``app.profiles`` excludes gender variants, incomplete
    regional coverage and old series. This wrapper keeps that threshold instead
    of exposing every indicator, so sitemap contents match the public
    methodology note about not pushing stale, incomplete or duplicative pages.
    """
    if not original_policy(item):
        return False
    if item.get("region_count") is None or item.get("completeness") is None:
        catalog_item = next(
            (entry for entry in get_catalog()["indicators"] if str(entry["id"]) == str(item.get("id"))),
            None,
        )
        if catalog_item:
            item = {**item, **catalog_item}
    if item.get("region_count", len(item.get("regions", []))) < REQUIRED_REGION_COUNT:
        return False
    if item.get("completeness", 0) < MIN_COMPLETENESS:
        return False
    if int(item.get("year_max") or 0) < MIN_INDEXABLE_YEAR:
        return False
    return indicator_passes_content_rule(item)
