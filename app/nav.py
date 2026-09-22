"""La navigazione del sito, in un posto solo.

Le voci erano scritte due volte: in `_ds_header.html` per le pagine Flask e a
mano in `frontend/src/main.jsx` per la testata React dell'atlante. Due elenchi
non si tengono allineati da soli, e infatti non lo erano: dall'atlante non si
raggiungevano `/confronto` ne' `/divari-regionali`, la qualita' della vita
portava all'indice invece che alla classifica, e le stesse sezioni si
chiamavano "Quiz Italia" e "Blog" da una parte, "Quiz" e "Storie" dall'altra.

La SPA continua a non conoscere nessuna rotta Flask: le voci le arrivano da
`window.__diNav`, lo stesso meccanismo con cui `.claude/rules/frontend.md`
consente gia' di passarle `__diInitialView`. Qui si decide, li' si disegna.

`active` e' la chiave che una pagina dichiara con `active_nav` per marcare la
voce corrente, e serve solo alla testata Flask: nella SPA la voce attiva la sa
il bundle.
"""
from __future__ import annotations

# Le voci di primo livello, nell'ordine in cui si leggono.
# `group` raccoglie le voci di una tendina, `path` quelle singole.
PRIMARY = (
    {
        "label": "Esplora",
        "key": "esplora",
        "group": (
            {"label": "Atlante", "path": "/atlante", "active": "atlas"},
            {"label": "Regioni", "path": "/regioni", "active": "regioni"},
            {"label": "Temi", "path": "/temi", "active": "temi"},
            {"label": "Confronta", "path": "/confronto", "active": "confronto"},
            {"label": "Divari regionali", "path": "/divari-regionali", "active": "divari"},
        ),
    },
    {
        "label": "Classifiche",
        "key": "classifiche",
        "group": (
            {"label": "Qualità della vita, regioni",
             "path": "/qualita-della-vita/classifica/regioni", "active": "qualita-della-vita"},
            {"label": "Qualità della vita, province",
             "path": "/qualita-della-vita/classifica/province", "active": "qualita-della-vita"},
            {"label": "Metodologia dell'indice", "path": "/metodologia", "active": "metodologia"},
        ),
    },
    {"label": "Storie", "path": "/blog", "active": "blog"},
    {"label": "Quiz", "path": "/quiz", "active": "gioco"},
    {"label": "Metodologia", "path": "/metodologia", "active": "metodologia"},
)

# Il pie' di pagina: piatto, e con le voci di servizio che nella testata non
# stanno.
FOOTER = (
    {"label": "Atlante", "path": "/atlante"},
    {"label": "Regioni", "path": "/regioni"},
    {"label": "Temi", "path": "/temi"},
    {"label": "Confronta", "path": "/confronto"},
    {"label": "Divari regionali", "path": "/divari-regionali"},
    {"label": "Qualità della vita", "path": "/qualita-della-vita/classifica/regioni"},
    {"label": "Quiz", "path": "/quiz"},
    {"label": "Storie", "path": "/blog"},
    {"label": "Metodologia", "path": "/metodologia"},
    {"label": "Catalogo dati", "path": "/catalogo-dati"},
    {"label": "Chi siamo", "path": "/chi-siamo"},
    {"label": "Privacy e cookie", "path": "/privacy"},
)


# La barra compatta della testata React non puo' portare le undici voci della
# navigazione Flask, che li' vivono in due tendine. Qui si dichiara **quali**
# destinazioni porta, non le sue etichette: quelle restano quelle di sopra, e
# una prova verifica che ogni percorso di questa lista esista davvero in
# `PRIMARY`. Cosi' le due superfici mostrano quantita' diverse dello stesso
# vocabolario, invece di essere due elenchi che divergono.
SPA_MASTHEAD = (
    "/atlante",
    "/regioni",
    "/temi",
    "/confronto",
    "/divari-regionali",
    "/qualita-della-vita/classifica/regioni",
    "/quiz",
    "/blog",
)

# Dove il nome per esteso non entra in una barra. Non e' un'etichetta diversa:
# e' la stessa voce, abbreviata dove lo spazio lo impone.
SHORT = {
    "/qualita-della-vita/classifica/regioni": "Qualità della vita",
}


def drawer_other():
    """Il gruppo "Altro" del cassetto: le voci fuori dalle due tendine.

    Si ricava invece di essere un quarto elenco, cosi' aggiungere una sezione al
    sito la fa comparire dove deve senza toccare il template. Le voci di primo
    livello vengono prima, con la loro etichetta piena, e poi le voci di
    servizio che stanno solo nel pie' di pagina.

    Escludere per percorso **le tendine intere** cancellava "Metodologia" dal
    cassetto, perche' quel percorso sta anche fra le classifiche col nome
    "Metodologia dell'indice": sul telefono la voce generale spariva e restava
    solo quella qualificata, cioe' la pagina si trovava solo cercandola sotto
    una parola che non la descrive tutta. Qui si esclude il gruppo "Esplora" e
    le classifiche vere, non ogni percorso che compaia li' dentro."""
    tendine = {v["path"] for gruppo in PRIMARY[:2] for v in gruppo["group"]}
    primo_livello = [v for v in PRIMARY if not v.get("group")]
    coperti = {v["path"] for v in primo_livello}
    return primo_livello + [
        v for v in FOOTER
        if v["path"] not in coperti and v["path"] not in tendine
    ]


def flat(items=PRIMARY):
    """Le voci con una destinazione, tendine sciolte, nell'ordine di lettura."""
    uscita = []
    for voce in items:
        if voce.get("group"):
            uscita.extend(voce["group"])
        else:
            uscita.append(voce)
    return uscita


def paths():
    """Ogni rotta che la navigazione promette, senza ripetizioni.

    La usa la prova che controlla che nessuna voce porti a un 404: una voce di
    menu rotta non fa fallire niente e la trova solo chi ci clicca."""
    viste, uscita = set(), []
    for voce in flat() + list(FOOTER):
        if voce["path"] not in viste:
            viste.add(voce["path"])
            uscita.append(voce["path"])
    return uscita


def for_spa():
    """La forma che il bundle legge da `window.__diNav`.

    Solo etichette, percorsi e la chiave `key` con cui la SPA riconosce le due
    voci che gestisce internamente (atlante e regioni) senza ricaricare la
    pagina. La chiave `active` della testata Flask non serve: nella SPA la voce
    corrente la sa il bundle."""
    per_percorso = {v["path"]: v for v in flat()}
    return {
        "masthead": [
            {"label": SHORT.get(percorso) or per_percorso[percorso]["label"],
             "path": percorso,
             "key": per_percorso[percorso].get("active", "")}
            for percorso in SPA_MASTHEAD if percorso in per_percorso
        ],
        "footer": [{"label": v["label"], "path": v["path"]} for v in FOOTER],
    }
