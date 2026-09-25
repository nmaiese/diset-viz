"""Il profilo di una provincia, come `app/profiles.py` fa per una regione.

Il buco che ha chiuso. Il sito misurava le province nella classifica della
qualita' della vita, e nessuna aveva una pagina: chi cercava "qualita' della
vita provincia di Lecce" arrivava, nel migliore dei casi, su una tabella di 103
righe, e da li' poteva solo salire alla Puglia.

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
from app.cache_util import synchronized_cache
from app.design.charts import spark_floor
from app.external_data import freshness_label, freshness_status
from app.taxonomy import CANONICAL_CATEGORIES

LIVELLO = "provincia"

# Quanti indicatori si mostrano per lato. Gli elenchi della fonte ne portano di
# piu', ma una pagina che ne elenca dieci per lato torna a essere la tabella da
# cui questa pagina esiste per uscire.
QUANTI_INDICATORI = 5


def _province_view_path(voce):
    try:
        return bes_data.bes_level_path(voce["id"], "provincia")
    except LookupError:
        return voce["path"]


def _indicatori(voci):
    return [
        {
            "id": voce.get("id"),
            "name": voce.get("name"),
            "theme": voce.get("theme"),
            "score": voce.get("score"),
            "year_max": voce.get("year_max"),
            # Il canonico lo calcola `quality_life_bes` (`bes_path`), qui lo si
            # apre sulle province come le altre righe della pagina.
            "path": _province_view_path(voce),
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


_CODELIST = bes_data.PROVINCE_CODES.parents[3] / "data" / "provincia" / "codelist_CL_ITTER107.csv"


@synchronized_cache(maxsize=1)
def unmeasured_provinces():
    """Le province della codifica Istat per cui il BES non ha dati, per nome.

    La nota pubblica di copertura si calcola da qui, confrontando la codifica
    con le province misurate. Scritta a mano diceva "Sud Sardegna non e'
    presente in questa edizione del BES", e non era vero: la scartava una
    regex della pipeline. Le province sarde soppresse prima del 2016 non sono
    un'assenza ma un'esclusione, e la nota le dice a parte.
    """
    import csv

    # Qui dentro e non in testa: `scripts.province_sources` importa
    # `app.taxonomy`, che carica il pacchetto `app` e con lui questo modulo, e
    # l'import in testa rompeva `build_province_dataset.py` lanciato da solo.
    from scripts.province_sources import DEFUNCT_PROVINCES, NUTS3_PATTERN

    measured = set()
    with bes_data.PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            measured.add(row["code"])
    names = []
    with _CODELIST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if (NUTS3_PATTERN.match(row["code"]) and row["code"] not in measured
                    and row["name"] not in DEFUNCT_PROVINCES):
                names.append(row["name"])
    return sorted(names)


def by_region():
    """`{region_key: [provincia, ...]}`: le province di ogni regione.

    Le regioni nell'ordine geografico del sito, quello di
    `profiles.regions_overview`, le province in ordine alfabetico: e' l'indice
    che risponde a "dov'e' la mia provincia", non a "chi e' prima", che e'
    la classifica. Ogni provincia porta posizione e punteggio del profilo
    predefinito, per chi vuole il numero senza aprire la pagina.

    Una provincia la cui regione non ha una pagina e' un errore, non una riga
    saltata: e' cosi' che Bolzano e Trento sono rimaste per mesi nella
    "regione" Provincia Autonoma, senza che niente lo dicesse.
    """
    ranking = qb.build_bes_ranking(LIVELLO, qb.DEFAULT_PROFILE)
    if not ranking:
        return {}
    grouped = {key: [] for key in profiles.regions_overview()}
    for row in ranking["ranking"]:
        region_key = profiles.region_key_for(row.get("region") or "")
        if region_key not in grouped:
            raise LookupError(
                f"provincia {row.get('key')!r}: la regione {row.get('region')!r} non ha una pagina")
        grouped[region_key].append({
            "key": row["key"],
            "name": row["name"],
            "path": f"/provincia/{row['key']}",
            "rank": row.get("rank"),
            "score": row.get("score"),
            "metro_city": bool(row.get("metro_city")),
        })
    for provinces in grouped.values():
        provinces.sort(key=lambda entry: entry["name"])
    return grouped


def total():
    """Quante province sono misurate: il numero che le pagine scrivono."""
    return len(chiavi())


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
    # Sempre `quante` vicine, anche in cima e in fondo alla classifica: la
    # finestra centrata sull'ultima ne dava tre, la meta' di tutte le altre.
    start = max(0, min(centro - max(1, quante // 2), len(righe) - quante - 1))
    finestra = righe[start: start + quante + 1]
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


def _macro_area(category):
    if category not in CANONICAL_CATEGORIES:
        raise LookupError(f"categoria {category!r} senza macro-area in taxonomy.CANONICAL_CATEGORIES")
    return CANONICAL_CATEGORIES[category]["macro_area"]


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
                # Niente flag "sopra la media": la pagina mostra il valore e
                # la media una accanto all'altra, e un booleano che ripete un
                # confronto gia' visibile e' solo un campo in piu' da tenere
                # allineato.
                in_regione = {
                    "posizione": _graduatoria(vicini, info.get("direction"))[chiave],
                    "quante": len(vicini),
                    "media": round(statistics.fmean(altri), 2),
                }

        variazione = None
        if len(anni) > 1:
            variazione = round(valore - per_anno[anni[0]]["valori"][chiave], 2)

        # La sparkline della riga e' la serie di questa provincia, anno per
        # anno, mai una media: sulla pagina di un territorio la linea dice
        # come si e' mosso lui. Il pavimento e' lo scarto interquartile delle
        # province con un dato nell'ultimo anno della riga, la stessa regola
        # delle minicard (`charts.spark_floor`): una provincia che si muove
        # poco rispetto alla distanza fra le province si disegna quasi piatta,
        # invece di riempire l'altezza come se fosse salita di molto. Tutto
        # sta gia' in `_serie()`: qui non si legge niente di nuovo.
        spark = [{"year": year, "value": per_anno[year]["valori"][chiave]} for year in anni]

        # Aperta sulle province: da qui il lettore cerca la sua, e il canonico
        # di una scheda a due livelli mostra le regioni. E aperta sulla sua
        # riga (`#p-<chiave>`, che `:target` accende anche senza JavaScript),
        # ma solo se la provincia ha il dato dell'ultimo anno della serie:
        # la classifica della scheda e' quella, e un'ancora senza riga non
        # porta da nessuna parte.
        path = bes_data.bes_level_path(id_indicatore, "provincia")
        if ultimo == max(per_anno):
            path += f"#p-{chiave}"

        righe.append({
            "id": id_indicatore,
            "name": info["name"],
            "theme": info.get("category_name") or info.get("domain_name") or "",
            # Le quattro macro-aree del sito, come sulla pagina regione. Il
            # dominio BES ne dava undici, che si sovrapponevano quasi voce per
            # voce al filtro Tema e alzavano la barra dei filtri a 564 px.
            "macro_area": _macro_area(info.get("category")),
            "path": path,
            "unit": info.get("unit") or "",
            "direction": info.get("direction"),
            "value": valore,
            "year": ultimo,
            "year_from": anni[0],
            "freshness_status": freshness_status(ultimo),
            "freshness_label": freshness_label(freshness_status(ultimo)),
            "rank": posizione,
            "province_count": len(dati["valori"]),
            "movement": movimento,
            "variazione": variazione,
            "spark": spark,
            "spark_floor": spark_floor(dati["valori"].values()) if len(spark) > 1 else None,
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
