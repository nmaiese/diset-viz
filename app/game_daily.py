"""Sfida del giorno: il giorno di Roma, il seed e i payload dei giochi a livelli.

Tre cose stanno qui, perche' devono restare d'accordo fra loro.

**Il giorno e' quello di Roma.** Un'unica funzione, `oggi_roma()`, dice che
giorno e' per il gioco. Il server gira in UTC (Cloud Run): senza questa funzione
la sfida nuova uscirebbe all'una o alle due di notte in Italia, e un punto che
usa `date.today()` darebbe un giorno diverso da quello che il giocatore vede. I
timestamp restano in UTC.

**Il seed e' onesto.** Il repo e' pubblico: il vecchio seed di Indovina la
Regione (`random.Random("divario-regioni-cycle-N")`) si calcola leggendo il
codice, e chiunque puo' sapere la soluzione di domani. Dal giorno `SEED_CUTOVER`
in avanti le soluzioni escono da `HMAC(GAME_SEED_KEY, "<gioco>|<data>")`, con una
chiave che non sta nel repo. Le date PRECEDENTI al passaggio tengono il seed
vecchio, cosi' l'archivio e il `localStorage` per `puzzleId` restano coerenti.

    RUOTARE `GAME_SEED_KEY` CAMBIA LE SFIDE FUTURE (dal cutover in poi) e mai le
    passate. Va fatto solo di proposito, e mai a meta' giornata: chi ha gia'
    giocato oggi vedrebbe un'altra soluzione ricaricando la pagina.

Senza la variabile d'ambiente si usa `CHIAVE_SVILUPPO`, che e' scritta qui e
quindi NON E' SEGRETA: va bene in locale e nei test, non in produzione.
`SEED_CUTOVER` e' un segnaposto (2099): la data vera si fissa nell'ultimo commit
prima del merge, al giorno del deploy piu' uno.

**I giochi con le province.** Il pool dei territori (107 province, centroidi,
province "giocabili"), l'elenco curato degli indicatori da gioco
(`config/game_indicators.csv`) e i payload della sfida del giorno di "Chi e'
maggiore?" e "Ordina": funzioni pure e deterministiche sul seed, che non
rivelano mai un valore. Come si valutano le risposte non e' qui.

`config/game_indicators.csv`: una riga per indicatore. L'`id` e' quello del pool
regionale del quiz (`105`, `bes:10AMB009`, `multiscopo:...`) quando
`livello_regione` e' 1, oppure l'id BES delle province (`04BEC001P`) quando
l'indicatore esiste solo a livello provinciale. Con `livello_provincia` 1 i dati
provinciali si leggono sotto l'id senza il prefisso `bes:`.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import logging
import math
import os
import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
GAME_EPOCH = date(2026, 7, 15)  # giorno di lancio, puzzle numero 1

# Segnaposto: la data vera si fissa prima del merge (vedi sopra).
SEED_CUTOVER = date(2099, 1, 1)
# NON SEGRETA: vale solo finche' `GAME_SEED_KEY` non e' impostata.
CHIAVE_SVILUPPO = "divario-chiave-di-sviluppo-non-segreta"

LIVELLI = ("regioni", "stessa_regione", "province")
COMPARE_COPPIE = 10
ORDER_TERRITORI = 5
# Province minime in una regione perche' "stessa regione" abbia senso.
MINIMO_COMPARE = 3
MINIMO_ORDER = 5

ROOT = Path(__file__).resolve().parents[1]
GIOCHI_CSV = ROOT / "config" / "game_indicators.csv"
CENTROIDI_JSON = ROOT / "app" / "static" / "data" / "province_centroidi.json"

# Lato minore (unita' del viewBox 560x660) del poligono principale di una
# provincia, sotto il quale la sagoma e' illeggibile sulla mappa a 390 px. Fra
# Trieste (12,7) e Gorizia (16,3) non cade nessuna provincia: la soglia sta nel
# vuoto, non taglia a caso.
SOGLIA_GIOCABILE = 14.0
# Chilometri per unita' del viewBox: media di tre distanze note (Milano-Roma,
# Torino-Trieste, Palermo-Bolzano) fra centroidi. Il viewBox e' un Mercatore,
# quindi la scala varia con la latitudine: i km sono approssimati.
KM_PER_UNITA = 1.90

# Livello di difficolta' (0 facile, 4 duro) per giorno della settimana, lunedi' = 0.
DIFFICOLTA_SETTIMANA = (0, 1, 1, 2, 3, 3, 4)
# Finestra (min, max) della distanza fra i due valori in gara, come frazione
# degli indici distinti disponibili: a livello 0 la coppia e' lontana in
# classifica, ai livelli alti quasi adiacente.
_FINESTRA_COMPARE = {0: (0.63, 1.0), 1: (0.42, 0.58), 2: (0.26, 0.37), 3: (0.16, 0.21), 4: (0.05, 0.11)}
# Per Ordina: quanta parte della classifica puo' coprire l'insieme dei cinque.
_FINESTRA_ORDER = {0: 1.0, 1: 0.7, 2: 0.5, 3: 0.35, 4: 0.22}
_MIN_DISTINTI_REGIONI = 6

_log = logging.getLogger(__name__)


# Il giorno di Roma

def oggi_roma(now=None):
    """Il giorno corrente a Roma. `now` (datetime con fuso) serve ai test."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ROMA).date()


def prossima_sfida_roma(oggi=None):
    """ISO 8601 UTC della mezzanotte di Roma che apre il giorno dopo `oggi`."""
    oggi = oggi or oggi_roma()
    mezzanotte = datetime.combine(oggi + timedelta(days=1), datetime.min.time(), tzinfo=ROMA)
    return mezzanotte.astimezone(timezone.utc).isoformat()


def numero_sfida(giorno):
    return max((giorno - GAME_EPOCH).days, 0) + 1


# Il seed

@lru_cache(maxsize=1)
def _avvisa_chiave_di_sviluppo():
    _log.warning("GAME_SEED_KEY non impostata: le sfide usano la chiave di sviluppo, che non e' segreta")


def chiave_seed():
    chiave = os.environ.get("GAME_SEED_KEY")
    if chiave:
        return chiave
    _avvisa_chiave_di_sviluppo()
    return CHIAVE_SVILUPPO


def seed_giorno(gioco, giorno, chiave=None):
    """Il seed intero di `gioco` nel `giorno`: HMAC-SHA256 di "<gioco>|<data>"."""
    chiave = chiave_seed() if chiave is None else chiave
    messaggio = f"{gioco}|{giorno.isoformat()}".encode()
    digest = hmac.new(chiave.encode(), messaggio, hashlib.sha256).digest()
    return int.from_bytes(digest, "big")


def _rng(gioco, giorno, chiave=None):
    return random.Random(seed_giorno(gioco, giorno, chiave))


def _ciclo_vecchio(indice_ciclo, ordine):
    """Il seed di prima del cutover: calcolabile da chiunque, conservato
    perche' le sfide gia' servite restano le stesse."""
    rng = random.Random(f"divario-regioni-cycle-{indice_ciclo}")
    regioni = list(ordine)
    rng.shuffle(regioni)
    return regioni


def regione_del_giorno(giorno, ordine, cutover=None, chiave=None):
    """La regione di Indovina per un giorno. Prima del cutover il ciclo vecchio
    di 20 giorni, dopo lo stesso schema (nessuna ripetizione nel ciclo) con un
    mescolamento che esce dall'HMAC. `ordine` e' l'elenco delle regioni."""
    cutover = SEED_CUTOVER if cutover is None else cutover
    if giorno < cutover:
        indice = max((giorno - GAME_EPOCH).days, 0)
        ciclo, pos = divmod(indice, len(ordine))
        return _ciclo_vecchio(ciclo, ordine)[pos]
    ciclo, pos = divmod((giorno - cutover).days, len(ordine))
    inizio = cutover + timedelta(days=ciclo * len(ordine))
    regioni = list(ordine)
    _rng("regioni", inizio, chiave).shuffle(regioni)
    return regioni[pos]


# I territori

@lru_cache(maxsize=1)
def _province():
    from app import bes_data, profiles

    with bes_data.PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        codici = list(csv.DictReader(handle, delimiter=";"))
    centroidi = json.loads(CENTROIDI_JSON.read_text(encoding="utf-8"))["province"]
    pool = []
    for riga in codici:
        chiave = riga["province_key"]
        c = centroidi[chiave]
        pool.append({
            "key": chiave,
            "name": riga["name"],
            "region": riga["region"],
            "region_key": profiles.region_key_for(riga["region"]),
            "x": c["x"],
            "y": c["y"],
            "w": c["w"],
            "h": c["h"],
            "giocabile": min(c["w"], c["h"]) >= SOGLIA_GIOCABILE,
        })
    return tuple(pool)


def province_pool(solo_giocabili=False):
    """Le 107 province con chiave, nome, regione e centroide (`x`, `y` nel
    viewBox 560x660). `giocabile` dice se la sagoma e' leggibile sulla mappa;
    `solo_giocabili` restituisce solo quelle. Non modificare le voci."""
    return [p for p in _province() if p["giocabile"] or not solo_giocabili]


def province_escluse():
    return [p["key"] for p in _province() if not p["giocabile"]]


def regioni_idonee(minimo):
    """Le regioni con almeno `minimo` province (5 per Ordina, 3 per gli altri
    giochi), nell'ordine di `REGION_ORDER`."""
    from app.data import REGION_ORDER

    conteggi = {}
    for p in _province():
        conteggi[p["region"]] = conteggi.get(p["region"], 0) + 1
    return [r for r in REGION_ORDER if conteggi.get(r, 0) >= minimo]


def _provincia(chiave):
    for p in _province():
        if p["key"] == chiave:
            return p
    raise KeyError(chiave)


_PUNTI = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


def distanza_km_direzione(a, b):
    """(km approssimati, direzione in otto punti) per andare dalla provincia `a`
    alla `b`, fra i centroidi. I km sono una stima: vanno dichiarati tali."""
    pa, pb = _provincia(a), _provincia(b)
    dx, dy = pb["x"] - pa["x"], pb["y"] - pa["y"]
    km = round(math.hypot(dx, dy) * KM_PER_UNITA)
    if km == 0:
        return 0, None
    gradi = math.degrees(math.atan2(dx, -dy)) % 360  # l'asse y dell'SVG scende
    return km, _PUNTI[int((gradi + 22.5) // 45) % 8]


# L'elenco curato

@lru_cache(maxsize=1)
def indicatori_gioco():
    """Le righe di `config/game_indicators.csv`, con i due flag come bool."""
    with GIOCHI_CSV.open(encoding="utf-8", newline="") as handle:
        righe = list(csv.DictReader(handle, delimiter=";"))
    return tuple(
        {
            "id": r["id"],
            "family": r["famiglia"],
            "name": r["nome_leggibile"],
            "unit": r["unita"],
            "regione": r["livello_regione"] == "1",
            "provincia": r["livello_provincia"] == "1",
            "note": r["note"],
        }
        for r in righe
    )


def id_provinciale(id_):
    return id_[len("bes:"):] if id_.startswith("bes:") else id_


def _righe_indicatore(ind, ambito):
    """(anno, [{key, name, region, value}]) di un indicatore a un livello
    territoriale, o None se il dato non c'e'. `ambito` e' "regioni" o "province"."""
    if ambito == "regioni":
        from app import quiz

        voce = {p["id"]: p for p in quiz._quiz_indicators()}.get(ind["id"])
        if voce is None:
            return None
        righe = [
            {"key": r["region_key"], "name": r["region"], "region": r["region"], "value": r["value"]}
            for r in voce["ranking"]
        ]
        return voce["year"], righe
    from app import bes_data, province_profile

    raw = id_provinciale(ind["id"])
    info = bes_data.get_bes_manifest("provincia").get(raw)
    if info is None:
        return None
    valori = (province_profile._serie().get(raw) or {}).get(info["year_max"])
    if not valori:
        return None
    anagrafe = {p["key"]: p for p in _province()}
    righe = [
        {"key": k, "name": anagrafe[k]["name"], "region": anagrafe[k]["region"], "value": v}
        for k, v in sorted(valori["valori"].items()) if k in anagrafe
    ]
    return info["year_max"], righe


def _campi_indicatore(ind, anno):
    return {"id": ind["id"], "name": ind["name"], "unit": ind["unit"], "year": anno, "family": ind["family"]}


def _campi_territorio(riga):
    return {"key": riga["key"], "name": riga["name"], "region": riga["region"]}


def _distinti(righe):
    """Valori distinti dal piu' alto al piu' basso, e le righe di ciascuno."""
    per_valore = {}
    for r in righe:
        per_valore.setdefault(r["value"], []).append(r)
    ordine = sorted(per_valore, reverse=True)
    return ordine, per_valore


def _ambito(livello, gioco, giorno, chiave):
    """(ambito dei dati, filtro sulle righe, regione) per un livello. Per
    "stessa regione" la regione del giorno esce dal seed."""
    if livello == "regioni":
        return "regioni", (lambda r: True), None
    if livello == "province":
        return "province", (lambda r: True), None
    minimo = MINIMO_ORDER if gioco == "order" else MINIMO_COMPARE
    idonee = regioni_idonee(minimo)
    regione = _rng(f"{gioco}-regione", giorno, chiave).choice(idonee)
    return "province", (lambda r: r["region"] == regione), regione


def _candidati(livello, ambito, filtro, minimo_distinti, rng):
    """Gli indicatori utilizzabili in quell'ambito, in ordine mescolato dal
    seed: una lista di (indicatore, anno, righe filtrate)."""
    flag = "regione" if ambito == "regioni" else "provincia"
    elenco = sorted((i for i in indicatori_gioco() if i[flag]), key=lambda i: i["id"])
    rng.shuffle(elenco)
    minimo = minimo_distinti if livello == "stessa_regione" else max(minimo_distinti, _MIN_DISTINTI_REGIONI)
    utili = []
    for ind in elenco:
        dato = _righe_indicatore(ind, ambito)
        if dato is None:
            continue
        anno, righe = dato
        righe = [r for r in righe if r["value"] is not None and filtro(r)]
        if len({r["value"] for r in righe}) >= minimo:
            utili.append((ind, anno, righe))
    return utili


def _controlla(livello):
    if livello not in LIVELLI:
        raise ValueError(f"livello sconosciuto: {livello!r}")


def compare_del_giorno(giorno, livello, chiave=None):
    """Le 10 coppie di "Chi e' maggiore?" per un giorno e un livello: per
    ciascuna un indicatore e due territori, MAI i valori. La difficolta' cresce
    da lunedi' (coppie lontane in classifica) a domenica (quasi adiacenti)."""
    _controlla(livello)
    difficolta = DIFFICOLTA_SETTIMANA[giorno.weekday()]
    rng = _rng(f"compare-{livello}", giorno, chiave)
    ambito, filtro, regione = _ambito(livello, "compare", giorno, chiave)
    utili = _candidati(livello, ambito, filtro, 2, rng)
    lo, hi = _FINESTRA_COMPARE[difficolta]
    coppie = []
    for i in range(COMPARE_COPPIE):
        ind, anno, righe = utili[i % len(utili)]
        distinti, per_valore = _distinti(righe)
        massimo = len(distinti) - 1
        gap_min = max(1, math.ceil(lo * massimo))
        gap_max = min(max(gap_min, math.floor(hi * massimo)), massimo)
        gap = rng.randint(gap_min, gap_max)
        j = rng.randint(0, massimo - gap)
        coppia = [rng.choice(per_valore[distinti[j]]), rng.choice(per_valore[distinti[j + gap]])]
        rng.shuffle(coppia)
        coppie.append({
            "indicator": _campi_indicatore(ind, anno),
            "a": _campi_territorio(coppia[0]),
            "b": _campi_territorio(coppia[1]),
        })
    return {"level": livello, "difficulty": difficolta, "region": regione, "pairs": coppie}


def order_del_giorno(giorno, livello, chiave=None):
    """Il round di "Ordina" per un giorno e un livello: cinque territori e un
    indicatore, senza valori ne' ordine (i territori sono mescolati). Le
    finestre di difficolta' stringono l'intervallo che i cinque coprono."""
    _controlla(livello)
    difficolta = DIFFICOLTA_SETTIMANA[giorno.weekday()]
    rng = _rng(f"order-{livello}", giorno, chiave)
    ambito, filtro, regione = _ambito(livello, "order", giorno, chiave)
    utili = _candidati(livello, ambito, filtro, ORDER_TERRITORI, rng)
    ind, anno, righe = utili[0]
    distinti, per_valore = _distinti(righe)
    n = len(distinti)
    finestra = min(n, max(ORDER_TERRITORI, math.ceil(_FINESTRA_ORDER[difficolta] * n)))
    inizio = rng.randint(0, n - finestra)
    indici = sorted(rng.sample(range(inizio, inizio + finestra), ORDER_TERRITORI))
    scelti = [rng.choice(per_valore[distinti[i]]) for i in indici]
    rng.shuffle(scelti)
    return {
        "level": livello,
        "difficulty": difficolta,
        "region": regione,
        "indicator": _campi_indicatore(ind, anno),
        "territories": [_campi_territorio(r) for r in scelti],
    }


# I payload delle rotte

def sfida_payload(gioco, livello, now=None):
    """Il payload della sfida di OGGI (a Roma): mai una data a scelta del
    client, cosi' una soluzione futura non puo' uscire."""
    giorno = oggi_roma(now)
    corpo = (compare_del_giorno if gioco == "compare" else order_del_giorno)(giorno, livello)
    return {
        "puzzle_id": f"daily:{giorno.isoformat()}",
        "number": numero_sfida(giorno),
        "date": giorno.isoformat(),
        "next_puzzle_at": prossima_sfida_roma(giorno),
        **corpo,
    }
