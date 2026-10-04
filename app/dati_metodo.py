"""La firma, la fonte e la freschezza: il riquadro "Dati e metodo".

Ogni pagina indicizzabile mostra chi la firma, da dove vengono i dati e quanto
sono freschi. Un solo posto compone cio' che il riquadro dice, cosi' le pagine
non copiano HTML e non si inventano una data: la data di aggiornamento della
fonte esiste solo dove la registra la pipeline (`publisher.dataset_updated`),
e se non c'e' il riquadro non la scrive.

La firma della redazione e il link alla metodologia stanno nella macro
(`v1/_dati_metodo.html`), che prende la firma da `REDAZIONE` (qui sotto) e il
link da `/metodologia`.
"""

from __future__ import annotations

from app import publisher, sources
from app import bes_data

# La firma del riquadro: il nome della testata, non il nome del titolare. Il
# nome del titolare compare solo in config/identita.yaml e in /privacy (lo
# sorveglia tests/unit/test_privacy_nome.py), mai in una firma pubblica come
# questa.
REDAZIONE = "Redazione Divario Italia"


def page_source(page: str, level: str | None = None) -> dict:
    """`{"label", "url", "updated"}` della fonte primaria di una pagina.

    `page` e' il tipo (`app/page_types.page_type`); `level` sceglie la fonte
    provinciale del BES quando le due differiscono (la pagina provincia). La
    voce `updated` e' `None` quando la fonte non registra una data, e il
    riquadro allora non la mostra. Mai un valore inventato.
    """
    if page == "province" or level == "provincia":
        return {
            "label": sources.family_label("bes"),
            "url": bes_data.BES_SOURCE_URLS["provincia"],
            "updated": publisher.dataset_updated("bes"),
        }
    if page == "region" or page == "theme":
        return {
            "label": sources.family_label("territorial"),
            "url": sources.TERRITORIAL_SOURCE_DEFAULT["url"],
            "updated": publisher.dataset_updated("territorial"),
        }
    if page == "quality_of_life":
        return {
            "label": sources.family_label("bes"),
            "url": bes_data.BES_SOURCE_URLS["regione"],
            "updated": publisher.dataset_updated("bes"),
        }
    return {"label": None, "url": None, "updated": None}
