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

import statistics
from collections import defaultdict

from app import bes_data, profiles
from app import quality_life_bes as qb
from app.cache import cache
from app.external_data import freshness_status

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


# ---------------------------------------------------------------------------
# I valori veri, che la pagina non mostrava.
#
# Fino al 22 settembre 2026 una pagina provincia diceva soltanto punteggi da 0 a
# 100, standardizzati sulle 103 province. Chi cercava "speranza di vita
# provincia di Lecce" arrivava su una pagina che non conteneva il numero di
# anni: il punteggio dice dove sta rispetto alle altre, non quanto vale.
#
# Il dato c'era gia' tutto e non lo leggeva nessuno: `bes_data.get_bes_rows`
# porta 48.603 righe, 67 indicatori dal 2015 al 2024, 479 righe per ogni
# provincia. Qui si legge quello, una volta per tutte e centotre le pagine.
# ---------------------------------------------------------------------------


def _graduatoria(valori, direzione):
    """Posizione di ogni territorio in un anno, 1 = migliore.

    A pari valore pari posizione, e la successiva salta (1, 2, 2, 4): due
    province con lo stesso numero non sono una davanti all'altra, e fingere
    che lo siano e' il modo in cui una graduatoria comincia a mentire sui
    decimali.
    """
    inverso = direzione != "lower_better"
    ordinati = sorted(valori.items(), key=lambda voce: voce[1], reverse=inverso)
    posizioni, precedente, posto = {}, None, 0
    for indice, (chiave, valore) in enumerate(ordinati, start=1):
        if valore != precedente:
            posto, precedente = indice, valore
        posizioni[chiave] = posto
    return posizioni


@cache.memoize(timeout=3600)
def _serie():
    """Valori e graduatorie per indicatore e per anno, in una passata sola.

    Calcolarlo dentro `profilo()` vorrebbe dire rileggere quarantottomila
    righe centotre volte, una per pagina. Il risultato e' lo stesso per tutte,
    quindi si calcola una volta e si indicizza per provincia.
    """
    manifesto = bes_data.get_bes_manifest(LIVELLO)
    valori = defaultdict(lambda: defaultdict(dict))
    for riga in bes_data.get_bes_rows(LIVELLO):
        if riga["id"] in manifesto and riga["value"] is not None:
            valori[riga["id"]][riga["year"]][riga["territory_key"]] = riga["value"]

    serie = {}
    for id_indicatore, per_anno in valori.items():
        direzione = manifesto[id_indicatore].get("direction")
        serie[id_indicatore] = {
            anno: {
                "valori": per_anno[anno],
                "posizioni": _graduatoria(per_anno[anno], direzione),
            }
            for anno in per_anno
        }
    return serie


def _regione_di():
    return {chiave: info.get("region") or ""
            for chiave, info in bes_data.get_bes_territories(LIVELLO).items()}


def indicatori(chiave):
    """Tutti gli indicatori BES misurati per una provincia, con il valore vero.

    **Non memoizzata, e non e' una svista.** Il lavoro pesante sta tutto in
    `_serie()`, che e' una voce di cache sola, e da li' questa funzione costa
    otto millesimi di secondo. Memoizzarla aggiungeva centotre voci alla cache,
    che e' una `SimpleCache` e pota quando supera le cinquecento: le voci nuove
    sfrattavano il caricatore dei post del blog, che ricaricava e riconvertiva
    undici Markdown a ogni pagina indicatore. La suite passava da cinquantadue
    secondi a centosessantotto, e il profilo dava la colpa al blog.

    Una riga per indicatore: quanto vale, in che unita', in che anno, in che
    posizione fra le province che quell'anno hanno un dato, come si e' mossa
    quella posizione dall'anno prima, e come sta rispetto alle altre province
    della sua stessa regione.

    Il confronto con la regione e' fra province, non con il valore regionale:
    il livello provinciale e quello regionale sono due letture diverse della
    stessa misura, e mescolarle produrrebbe un confronto che non esiste. E'
    lo stesso motivo per cui questo modulo non riusa `region_profile`.
    """
    manifesto = bes_data.get_bes_manifest(LIVELLO)
    serie = _serie()
    regione_di = _regione_di()
    mia_regione = regione_di.get(chiave) or ""
    sorelle = {k for k, r in regione_di.items() if r and r == mia_regione}

    righe = []
    for id_indicatore, per_anno in serie.items():
        anni = sorted(a for a, dati in per_anno.items() if chiave in dati["valori"])
        if not anni:
            continue
        info = manifesto[id_indicatore]
        ultimo = anni[-1]
        dati = per_anno[ultimo]
        valore = dati["valori"][chiave]
        posizione = dati["posizioni"][chiave]

        # Il movimento e' di posizione, non di valore: e' la stessa lettura
        # dell'esploratore regionale, e un valore che sale mentre salgono tutti
        # non e' un miglioramento. Positivo vuol dire salita in graduatoria.
        movimento = None
        if len(anni) > 1:
            prima = per_anno[anni[-2]]["posizioni"].get(chiave)
            if prima is not None:
                movimento = prima - posizione

        # Dentro la propria regione. Una provincia sola nella sua regione non
        # ha un dentro, e la riga resta senza confronto invece di dire che e'
        # prima su una.
        in_regione = None
        if len(sorelle) > 1:
            vicini = {k: v for k, v in dati["valori"].items() if k in sorelle}
            if len(vicini) > 1 and chiave in vicini:
                altri = [v for k, v in vicini.items() if k != chiave]
                in_regione = {
                    "posizione": _graduatoria(vicini, info.get("direction"))[chiave],
                    "quante": len(vicini),
                    "media": round(statistics.fmean(altri), 2),
                    "sopra": valore > statistics.fmean(altri),
                }

        variazione = None
        if len(anni) > 1:
            variazione = round(valore - per_anno[anni[0]]["valori"][chiave], 2)

        righe.append({
            "id": id_indicatore,
            "name": info["name"],
            "theme": info.get("category_name") or info.get("domain_name") or "",
            "macro_area": info.get("domain_name") or "",
            "path": bes_data.bes_indicator_path(id_indicatore, info["name"]),
            "unit": info.get("unit") or "",
            "direction": info.get("direction"),
            "value": valore,
            "year": ultimo,
            "year_from": anni[0],
            "freshness_status": freshness_status(ultimo),
            "rank": posizione,
            "province_count": len(dati["valori"]),
            "movement": movimento,
            "variazione": variazione,
            "in_regione": in_regione,
        })

    righe.sort(key=lambda r: (r["rank"], r["name"]))
    return righe


def movimenti(righe, quanti=4):
    """Dove la provincia ha guadagnato e perso piu' posizioni nell'ultimo anno."""
    mossi = [r for r in righe if r["movement"]]
    su = sorted([r for r in mossi if r["movement"] > 0],
                key=lambda r: -r["movement"])[:quanti]
    giu = sorted([r for r in mossi if r["movement"] < 0],
                 key=lambda r: r["movement"])[:quanti]
    return su, giu


def dentro_la_regione(righe, quanti=4):
    """Dove stacca e dove resta indietro rispetto alle province della sua regione.

    E' la domanda che la classifica nazionale non risponde: una provincia
    novantesima su 103 puo' essere la prima della sua regione, e per chi ci
    vive quella e' l'informazione utile.
    """
    confrontabili = [r for r in righe if r["in_regione"]]
    prime = [r for r in confrontabili if r["in_regione"]["posizione"] == 1]
    ultime = [r for r in confrontabili
              if r["in_regione"]["posizione"] == r["in_regione"]["quante"]]
    return prime[:quanti], ultime[:quanti]
