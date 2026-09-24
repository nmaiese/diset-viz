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
#
# Dalla 1.0 la testata e' ordinata per quello che si cerca, non per il tipo di
# pagina: i territori, i temi, la qualita' della vita, l'atlante coi dati, le
# storie, il quiz. Chi siamo, contatti e informativa sono usciti dalla testata
# (dove li aveva portati una tendina "Progetto") e stanno nel piede, in una
# colonna loro e nella riga legale: su ogni pagina, anche senza JavaScript.
PRIMARY = (
    {
        "label": "Territori",
        "key": "territori",
        "group": (
            {"label": "Le 20 regioni", "path": "/regioni", "active": "regioni"},
            {"label": "Le 107 province", "path": "/province", "active": "province"},
            {"label": "Confronta i territori", "path": "/confronto", "active": "confronto"},
        ),
    },
    {"label": "Temi", "path": "/temi", "active": "temi"},
    {
        "label": "Qualità della vita",
        "key": "qualita",
        "group": (
            {"label": "Dove si vive meglio", "path": "/qualita-della-vita",
             "active": "qualita-della-vita"},
            {"label": "Classifica delle regioni",
             "path": "/qualita-della-vita/classifica/regioni", "active": "qualita-della-vita"},
            {"label": "Classifica delle province",
             "path": "/qualita-della-vita/classifica/province", "active": "qualita-della-vita"},
        ),
    },
    {
        "label": "Atlante e dati",
        "key": "atlante",
        "group": (
            {"label": "Atlante", "path": "/atlante", "active": "atlas"},
            {"label": "Divari regionali", "path": "/divari-regionali", "active": "divari"},
            {"label": "Catalogo dati", "path": "/catalogo-dati", "active": "catalogo"},
            {"label": "Metodologia", "path": "/metodologia", "active": "metodologia"},
        ),
    },
    {"label": "Storie", "path": "/blog", "active": "blog"},
    {"label": "Quiz", "path": "/quiz", "active": "gioco"},
)

# Il pie' di pagina, nelle sue colonne. E' l'elenco che si vede, e da qui si
# ricava anche quello piatto che leggono il cassetto e la SPA.
#
# Era scritto due volte, e questo modulo esiste per non farlo: le colonne
# stavano a mano in `blog_base.html`, la lista piatta qui sotto, e le due
# divergevano in silenzio.
FOOTER_GROUPS = (
    {
        "label": "Territori",
        "items": (
            {"label": "Regioni", "path": "/regioni"},
            {"label": "Province", "path": "/province"},
            {"label": "Confronta", "path": "/confronto"},
            {"label": "Divari regionali", "path": "/divari-regionali"},
        ),
    },
    {
        "label": "Qualità della vita",
        "items": (
            {"label": "Dove si vive meglio", "path": "/qualita-della-vita"},
            {"label": "Classifica delle regioni",
             "path": "/qualita-della-vita/classifica/regioni"},
            {"label": "Classifica delle province",
             "path": "/qualita-della-vita/classifica/province"},
        ),
    },
    {
        "label": "Atlante e dati",
        "items": (
            {"label": "Temi", "path": "/temi"},
            {"label": "Atlante", "path": "/atlante"},
            {"label": "Catalogo dati", "path": "/catalogo-dati"},
            {"label": "Metodologia e fonti", "path": "/metodologia"},
            {"label": "Cerca nel sito", "path": "/ricerca"},
        ),
    },
    {
        "label": "Progetto",
        "items": (
            {"label": "Storie", "path": "/blog"},
            {"label": "Quiz", "path": "/quiz"},
            {"label": "Chi siamo", "path": "/chi-siamo"},
            {"label": "Contatti", "path": "/contatti"},
        ),
    },
)

# La riga legale in fondo al piede. Sta fuori dalle colonne perche' si legge
# come una riga di servizio, ma entra nell'elenco piatto come le altre voci.
LEGAL = (
    {"label": "Privacy e cookie", "path": "/privacy"},
    # Stessa pagina, punto diverso. `anchor` sta separata da `path` perche'
    # `paths()` apre ogni percorso aspettandosi 200, e "/privacy#cookie" come
    # percorso sarebbe una 404: l'ancora la legge il browser, non il router.
    {"label": "Cookie policy", "path": "/privacy", "anchor": "#cookie"},
    {"label": "Termini", "path": "/termini"},
)


def _footer_piatto():
    """Le stesse voci in fila, una sola volta per destinazione.

    La barra della SPA e il cassetto del telefono mostrano una riga, non
    quattro colonne: `/metodologia` sta in due colonne con due nomi diversi e
    in una riga sola diventerebbe una ripetizione. Vince il primo nome, che e'
    quello che la colonna piu' a sinistra ha gia' dato.

    La chiave e' percorso **piu' ancora**: "/privacy" e "/privacy#cookie" sono
    due destinazioni diverse per chi legge, e deduplicarle sul solo percorso
    farebbe sparire la seconda."""
    viste, uscita = set(), []
    for gruppo in (*FOOTER_GROUPS, {"items": LEGAL}):
        for voce in gruppo["items"]:
            chiave = (voce["path"], voce.get("anchor", ""))
            if chiave not in viste:
                viste.add(chiave)
                uscita.append(voce)
    return tuple(uscita)


FOOTER = _footer_piatto()


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
    "/regioni": "Regioni",
    "/confronto": "Confronta",
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
    una parola che non la descrive tutta. Qui si escludono le voci **delle
    tendine**, non ogni percorso che compaia li' dentro.

    Le tendine si ricavano da `PRIMARY`, non si contano: erano due, scritte
    `PRIMARY[:2]`, e quel taglio ha smesso di dire la verita' il giorno in cui
    ne e' arrivata una terza."""
    tendine = {v["path"] for gruppo in PRIMARY if gruppo.get("group")
               for v in gruppo["group"]}
    primo_livello = [v for v in PRIMARY if not v.get("group")]
    coperti = {v["path"] for v in primo_livello}
    return primo_livello + [
        v for v in FOOTER
        if v["path"] not in coperti and v["path"] not in tendine
        and not v.get("anchor")
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


def group_of(active):
    """La tendina che contiene la voce attiva, per accenderla nella testata.

    `_ds_header.html` scriveva a mano quali voci accendono "Esplora", e ogni
    voce nuova andava ricordata in due posti. Si ricava da `PRIMARY`.
    """
    # Una voce che ha anche un posto suo in testata (Metodologia) si accende
    # li', non nella tendina che la ripete.
    if any(entry.get("active") == active for entry in PRIMARY if "group" not in entry):
        return None
    for entry in PRIMARY:
        if any(item.get("active") == active for item in entry.get("group", ())):
            return entry["key"]
    return None


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
        # Il percorso che la SPA usa come href porta l'ancora, quando c'e':
        # li' e' un indirizzo, non una rotta da risolvere.
        "footer": [{"label": v["label"], "path": v["path"] + v.get("anchor", "")}
                   for v in FOOTER],
    }
