"""The single public identity of Divario Italia.

Keep this object deliberately small.  In particular, ``sameAs`` is omitted
until the project has an externally verified, owned profile to point to.

``contactPoint`` is the one exception to "small", and it earns its place: it
carries an address that /contatti shows in plain text, so the structured data
never claims a way to reach us that the visible page does not offer.
"""

import json
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import SITE_NAME, SITE_URL

# L'identita' con cui il sito firma sta in `config/identita.yaml`, un file solo:
# passare da un marchio a una persona e' cambiare quello, non cercare nomi nel
# codice. Un test sostituisce questo percorso con un file di prova.
IDENTITY_PATH = Path(__file__).resolve().parents[1] / "config" / "identita.yaml"
IDENTITY_TYPES = ("organizzazione", "persona")


@lru_cache(maxsize=8)
def _load_identity(path):
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    kind = str(raw.get("tipo") or "").strip()
    name = str(raw.get("nome") or "").strip()
    if kind not in IDENTITY_TYPES:
        raise ValueError(f"{path}: `tipo` deve essere uno fra {IDENTITY_TYPES}, trovato {kind!r}")
    if not name:
        raise ValueError(f"{path}: `nome` e' obbligatorio")
    same_as = raw.get("same_as") or []
    if not isinstance(same_as, list):
        raise ValueError(f"{path}: `same_as` deve essere una lista")
    author_path = str(raw.get("url_autore") or "/chi-siamo").strip()
    return {
        "tipo": kind,
        "nome": name,
        "descrizione": str(raw.get("descrizione") or "").strip(),
        "email": str(raw.get("email") or "").strip(),
        "url_autore": author_path,
        "url_autore_abs": author_path if author_path.startswith("http") else f"{SITE_URL}{author_path}",
        "same_as": [str(url).strip() for url in same_as if str(url).strip()],
        "intestatario_legale": str(raw.get("intestatario_legale") or "").strip(),
    }


def identity():
    """L'identita' editoriale corrente, letta da `IDENTITY_PATH`.

    Si rilegge il percorso a ogni chiamata (la lettura e' in cache per
    percorso), cosi' un test che lo sostituisce vede subito l'altro file."""
    return _load_identity(str(IDENTITY_PATH))


# L'indirizzo a cui si risponde. Qui e non in una variabile d'ambiente: e'
# pubblico, stabile, e la sua verita' sta accanto all'identita' che dichiara.
# In pagina va in chiaro, mai offuscato da JavaScript: un indirizzo che solo un
# browser con JS attivo sa comporre non e' un contatto per chi legge il sito
# senza, ne' per chi lo controlla dall'esterno.
#
# E non basta scriverlo in chiaro. Cloudflare ha Email Address Obfuscation
# acceso, e riscrive **ogni** `mailto:` in `/cdn-cgi/l/email-protection#<hex>`
# piu' un testo da decifrare con JavaScript: in produzione la pagina prometteva
# un contatto e consegnava un blob, mentre in locale era perfetta. Per questo
# ogni indirizzo in pagina sta fra `<!--email_off-->` e `<!--email_on-->`, la
# direttiva con cui Cloudflare spegne l'offuscamento su un blocco solo, invece
# di spegnere Scrape Shield su tutto il sito.
CONTACT_EMAIL = identity()["email"]

# La piattaforma che raccoglie il consenso. Il nome sta qui perche' compare
# nell'informativa, e un'informativa che nomina la piattaforma sbagliata e'
# un'informativa falsa: fino al 22 settembre 2026 /privacy diceva "pannello
# privacy gestito da Google" mentre il pannello era di Iubenda. Cambiare
# piattaforma e' cambiare queste due righe.
CONSENT_CMP_NAME = "Iubenda"
CONSENT_CMP_URL = "https://www.iubenda.com/privacy-policy/"

ORGANIZATION_ID = f"{SITE_URL}/chi-siamo#organizzazione"
EDITOR_ID = f"{SITE_URL}/chi-siamo#chi-lo-cura"


def editor_name():
    """Il nome che firma: quello dell'identita', di marchio o di persona."""
    return identity()["nome"]


def titolare():
    """Chi e' il titolare del trattamento in /privacy: l'intestatario legale se
    c'e', altrimenti il nome della firma (il ripiego serve al file di prova,
    dove l'intestatario e' vuoto)."""
    ident = identity()
    return ident["intestatario_legale"] or ident["nome"]


def author_node():
    """Il nodo JSON-LD che firma un articolo.

    `Person` solo quando l'identita' e' di tipo `persona`; altrimenti
    un'`Organization` con il nome della redazione."""
    ident = identity()
    node = {
        "@type": "Person" if ident["tipo"] == "persona" else "Organization",
        "name": ident["nome"],
        "url": ident["url_autore_abs"],
    }
    if ident["tipo"] == "persona":
        node["@id"] = EDITOR_ID
    if ident["descrizione"]:
        node["description"] = ident["descrizione"]
    if ident["same_as"]:
        node["sameAs"] = ident["same_as"]
    return node


def author_jsonld():
    return json.dumps(author_node(), ensure_ascii=False)


def about_entity():
    """L'entita' principale di /chi-siamo: la persona se c'e', altrimenti
    l'organizzazione gia' nel grafo."""
    if identity()["tipo"] == "persona":
        return author_node()
    return {"@id": ORGANIZATION_ID}


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

if identity()["tipo"] == "organizzazione" and identity()["same_as"]:
    ORGANIZATION["sameAs"] = identity()["same_as"]

# "Segnala un errore" porta alla pagina contatti, dove si scrive per email. Fino
# al 25/9/2026 portava a una issue GitHub, che chiede un account e il login a
# chi vuole solo dire che una cifra e' sbagliata. GitHub resta come canale
# pubblico, dichiarato in /contatti.
CORRECTIONS_URL = "/contatti#segnala-un-errore"
PUBLIC_ISSUES_URL = "https://github.com/nmaiese/diset-viz/issues/new"

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
