"""Il profilo di una provincia, come `app/profiles.py` fa per una regione.

Il buco che chiude. Il sito misura 103 province nella classifica della qualita'
della vita, e nessuna di loro aveva una pagina. Il commento in `views.py` che
costruisce quella classifica lo dice gia': "Le province non hanno un profilo,
ma la loro regione si', quindi il nome della regione diventa la porta". Cioe'
chi cercava "qualita' della vita provincia di Lecce" arrivava, nel migliore dei
casi, su una tabella di 103 righe, e da li' poteva solo salire alla Puglia.

Non e' un buco di disegno, e' un buco di superficie: il dato c'e' tutto.
`quality_life_bes.build_bes_territory` restituisce gia' punteggio, posizione,
regione, punteggi per categoria, categorie forti e deboli e i due elenchi di
indicatori che tirano su e giu'. Qui non si calcola niente di nuovo: si prende
quel payload e lo si mette in una forma che una pagina puo' rendere, con i link
risolti e le cifre arrotondate una volta sola.

Perche' un modulo e non una funzione in `views.py`: la stessa forma serve alla
pagina HTML, alla sua proiezione Markdown e al JSON-LD, e tenerla in tre posti
e' il modo in cui i tre cominciano a dire cose diverse.

Perche' non riusa `profiles.region_profile`: quello legge la matrice dei
percentili regionali, che a livello provinciale non esiste. Le due fonti sono
diverse, e fingere che siano la stessa produrrebbe una classifica provinciale
calcolata su dati regionali.
"""
from __future__ import annotations

from app import profiles
from app import quality_life_bes as qb

LIVELLO = "provincia"

# Quanti indicatori si mostrano per lato. Gli elenchi della fonte ne portano di
# piu', ma una pagina che ne elenca dieci per lato torna a essere la tabella da
# cui questa pagina esiste per uscire.
QUANTI_INDICATORI = 5


def _indicatore_path(voce):
    """Il link canonico alla scheda di un indicatore dell'elenco.

    `id` arriva namespacizzato (`bes:09PAE002`), e `profiles.indicator_path`
    vuole id e nome: e' la stessa funzione che usano le pagine regione, cosi'
    un link provinciale e uno regionale non possono divergere di forma.
    """
    return profiles.indicator_path(voce.get("id"), voce.get("name") or "")


def _indicatori(voci):
    return [
        {
            "id": voce.get("id"),
            "name": voce.get("name"),
            "theme": voce.get("theme"),
            "score": voce.get("score"),
            "year_max": voce.get("year_max"),
            "path": _indicatore_path(voce),
        }
        for voce in (voci or [])[:QUANTI_INDICATORI]
    ]


def chiavi():
    """Le chiavi di tutte le province misurate, in ordine di classifica.

    Sono la sola sorgente per la sitemap e per la prova che ogni riga della
    classifica porti a una pagina che risponde: un elenco scritto a mano
    resterebbe indietro alla prima provincia che entra o esce dal dato.
    """
    classifica = qb.build_bes_ranking(LIVELLO, qb.DEFAULT_PROFILE)
    if not classifica:
        return []
    return [riga["key"] for riga in classifica["ranking"] if riga.get("key")]


def profilo(chiave):
    """Il profilo di una provincia, o None se la chiave non e' misurata."""
    payload = qb.build_bes_territory(LIVELLO, chiave, qb.DEFAULT_PROFILE)
    if not payload or not payload.get("territory"):
        return None

    territorio = payload["territory"]
    categorie = {voce["slug"]: voce for voce in payload.get("categories") or []}
    punteggi = territorio.get("category_scores") or {}

    # La regione come porta, quando e' una regione vera. Bolzano e Trento
    # dichiarano "Provincia Autonoma Bolzano", che slugificata darebbe un link
    # a una pagina che non esiste: e' lo stesso controllo che fa la classifica,
    # e per la stessa ragione.
    nome_regione = territorio.get("region")
    chiave_regione = profiles.region_key_for(nome_regione) if nome_regione else None
    if not (chiave_regione and profiles.region_name(chiave_regione)):
        chiave_regione = None

    return {
        "key": territorio["key"],
        "name": territorio["name"],
        "path": f"/provincia/{territorio['key']}",
        "region": nome_regione,
        "region_path": f"/regione/{chiave_regione}" if chiave_regione else None,
        "metro_city": bool(territorio.get("metro_city")),
        "score": territorio.get("score"),
        "rank": territorio.get("rank"),
        "total": payload.get("total"),
        "coverage": territorio.get("coverage"),
        "profile": payload.get("profile") or {},
        "methodology": payload.get("methodology") or {},
        "categories": [
            {
                "slug": slug,
                "name": (categorie.get(slug) or {}).get("name") or slug,
                "score": punteggio,
            }
            for slug, punteggio in sorted(punteggi.items(), key=lambda voce: -(voce[1] or 0))
        ],
        "strongest": territorio.get("strongest_categories") or [],
        "weakest": territorio.get("weakest_categories") or [],
        "top_positive": _indicatori(territorio.get("top_positive_indicators")),
        "top_negative": _indicatori(territorio.get("top_negative_indicators")),
    }


def vicine(chiave, quante=6):
    """Le province vicine in classifica, per non chiudere la pagina in fondo.

    Vicine di **punteggio**, non di geografia: la pagina risponde a "come sta
    questa provincia", e il confronto che serve li' e' con chi sta intorno
    nella stessa graduatoria. La geografia ce l'ha gia' il link alla regione.
    """
    classifica = qb.build_bes_ranking(LIVELLO, qb.DEFAULT_PROFILE)
    if not classifica:
        return []
    righe = classifica["ranking"]
    posizioni = {riga["key"]: indice for indice, riga in enumerate(righe)}
    if chiave not in posizioni:
        return []
    centro = posizioni[chiave]
    meta = max(1, quante // 2)
    inizio = max(0, centro - meta)
    finestra = righe[inizio: inizio + quante + 1]
    return [
        {
            "key": riga["key"],
            "name": riga["name"],
            "path": f"/provincia/{riga['key']}",
            "rank": riga.get("rank") or (posizioni[riga["key"]] + 1),
            "score": riga.get("score"),
            "region": riga.get("region"),
        }
        for riga in finestra if riga["key"] != chiave
    ]
