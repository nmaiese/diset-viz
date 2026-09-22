"""The single public identity of Divario Italia.

Keep this object deliberately small.  In particular, ``sameAs`` is omitted
until the project has an externally verified, owned profile to point to.

``contactPoint`` is the one exception to "small", and it earns its place: it
carries an address that /contatti shows in plain text, so the structured data
never claims a way to reach us that the visible page does not offer.
"""

import json
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.config import SITE_NAME, SITE_URL


# L'indirizzo a cui si risponde. Qui e non in una variabile d'ambiente: e'
# pubblico, stabile, e la sua verita' sta accanto all'identita' che dichiara.
# In pagina va in chiaro, mai offuscato da JavaScript: un indirizzo che solo un
# browser con JS attivo sa comporre non e' un contatto per chi legge il sito
# senza, ne' per chi lo controlla dall'esterno.
CONTACT_EMAIL = "divarioitalia@protonmail.com"

# La piattaforma che raccoglie il consenso. Il nome sta qui perche' compare
# nell'informativa, e un'informativa che nomina la piattaforma sbagliata e'
# un'informativa falsa: fino al 22 settembre 2026 /privacy diceva "pannello
# privacy gestito da Google" mentre il pannello era di Iubenda. Cambiare
# piattaforma e' cambiare queste due righe.
CONSENT_CMP_NAME = "Iubenda"
CONSENT_CMP_URL = "https://www.iubenda.com/privacy-policy/"

ORGANIZATION_ID = f"{SITE_URL}/chi-siamo#organizzazione"
ORGANIZATION = {
    "@type": "Organization",
    "@id": ORGANIZATION_ID,
    "name": SITE_NAME,
    "url": f"{SITE_URL}/chi-siamo",
    "logo": {
        "@type": "ImageObject",
        "url": f"{SITE_URL}/static/img/logo-mark.png",
    },
    "contactPoint": {
        "@type": "ContactPoint",
        "contactType": "editorial",
        "email": CONTACT_EMAIL,
        "url": f"{SITE_URL}/contatti",
        "availableLanguage": "it",
    },
}

CORRECTIONS_URL = "https://github.com/nmaiese/diset-viz/issues/new"

_SOURCE_STATE = Path(__file__).resolve().parents[1] / "data" / "source_state.json"
_STATE_KEYS = {
    "territorial": "istat_indicatori_territoriali",
    "bes": "istat_bes_regioni",
}


def organization_json():
    return json.dumps(ORGANIZATION, ensure_ascii=False)


def dataset_updated(family):
    """Return the upstream snapshot date recorded by the refresh pipeline.

    The dataset date is an optional enrichment: the deployed image ships
    app/, content/ and scripts/ but not data/, so ``source_state.json`` is
    absent in production. A missing or unreadable state file must degrade to
    "no date shown", never raise and 500 an otherwise healthy indicator page.
    """
    key = _STATE_KEYS.get(family)
    if not key:
        return None
    try:
        with _SOURCE_STATE.open(encoding="utf-8") as handle:
            value = json.load(handle).get("sources", {}).get(key, {}).get("last_modified")
    except (OSError, ValueError):
        return None
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None
