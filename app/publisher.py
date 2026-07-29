"""The single public identity of Divario Italia.

Keep this object deliberately small.  In particular, ``sameAs`` is omitted
until the project has an externally verified, owned profile to point to.
"""

import json
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.config import SITE_NAME, SITE_URL


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
    """Return the upstream snapshot date recorded by the refresh pipeline."""
    key = _STATE_KEYS.get(family)
    if not key:
        return None
    with _SOURCE_STATE.open(encoding="utf-8") as handle:
        value = json.load(handle).get("sources", {}).get(key, {}).get("last_modified")
    return parsedate_to_datetime(value).date().isoformat() if value else None
