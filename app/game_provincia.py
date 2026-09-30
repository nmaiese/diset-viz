"""Indovina la Provincia: una provincia al giorno, sei indizi di dato, sei tentativi.

La provincia del giorno e' una sola, uguale per tutti e per i due livelli:

- **"della regione indicata"** (`stessa_regione`): al giocatore si dice la
  regione e si indovina fra le sue province;
- **"di tutta Italia"** (`province`): si indovina fra le 107.

Il livello e' la sola cosa che cambia: la provincia, gli indizi e la soluzione
sono gli stessi. Per questo la provincia si sceglie fra le giocabili
(`game_daily.province_pool(solo_giocabili=True)`) **di una regione idonea**
(`regioni_idonee(3)`): altrimenti il livello facile non avrebbe fra chi scegliere.

Il giorno e' quello di Roma (`game_daily.oggi_roma`) e il seed esce da
`game_daily.seed_giorno("provincia", giorno)`, cioe' da un HMAC con una chiave
che non sta nel repo: la soluzione di domani non si calcola leggendo il codice.

**Anti-spoiler.** Lo stato dei tentativi sta nel server, non nel solo client: il
client non dice mai a che tentativo e'. Porta un token firmato (`itsdangerous`,
sale propria) con il `puzzle_id`, il livello e le chiavi gia' tentate; il server
deriva il numero del tentativo da quel token, rifiuta chiavi ripetute o fuori
dalle opzioni del livello, e mette la soluzione nella risposta solo a partita
finita. Il `puzzle_id` vale solo se e' la giornaliera di oggi. Un token piu'
vecchio di uno gia' usato dalla stessa sessione si rifiuta (`token_superato`,
per processo: un solo worker con piu' thread).
Limite noto: chi chiede un payload nuovo apre una sessione nuova, quindi puo'
riprovare dall'inizio. Non svela la soluzione (i tentativi di una sessione sono
sei) ma consente di sondare. Le rotte sono a frequenza limitata.

**Gli indizi** sono sei dati dell'Istat (BES dei Territori) presi da
`Assoluti_Provincia.csv` tramite `province_profile._serie()`: solo gli
indicatori di `config/game_indicators.csv` con il flag provincia, con un valore
per tutte e 107 le province nell'ultimo anno (`n_province_latest == 107`) e un
ultimo anno dal 2022 in poi. Uno per famiglia quando si puo', scelti dal seed e
ordinati dal meno al piu' distintivo per quella provincia (la distanza della sua
posizione dalla meta' della classifica).

Il risultato non entra in `player_stats.record_daily`: quello resta alla
giornaliera di Indovina la Regione. Serie e classifica sono dell'ondata 3.
"""

from __future__ import annotations

import csv
import random
from functools import lru_cache
from statistics import fmean

from itsdangerous import BadData, URLSafeTimedSerializer

from app import app, bes_data, game_daily, province_profile, sources
from app.cache import cache
from app.design import maps

TENTATIVI = 6
LIVELLI = ("province", "stessa_regione")
ANNO_MINIMO = 2022
PROVINCE_ATTESE = 107

_SALT = "game-provincia"
_TOKEN_MAX_AGE_S = 2 * 24 * 3600
_MANIFEST_CSV = game_daily.ROOT / "app" / "static" / "data" / "province_manifest.csv"


class ErroreProvincia(Exception):
    """Un tentativo che non si valuta. `code` e' una parola per il client,
    `status` il codice HTTP."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


# Gli indizi ammessi


@lru_cache(maxsize=1)
def _manifesto():
    with _MANIFEST_CSV.open(encoding="utf-8", newline="") as handle:
        return {riga["id"]: riga for riga in csv.DictReader(handle, delimiter=";")}


@lru_cache(maxsize=1)
def indizi_ammessi():
    """Gli indicatori che possono fare da indizio, nell'ordine del file di
    configurazione: (id BES, nome leggibile, unita', famiglia, tema, anno)."""
    manifesto = _manifesto()
    ammessi = []
    for voce in game_daily.indicatori_gioco():
        if not voce["provincia"]:
            continue
        raw = game_daily.id_provinciale(voce["id"])
        riga = manifesto.get(raw)
        if riga is None:
            continue
        anno = int(riga["year_max"])
        if int(riga["n_province_latest"]) != PROVINCE_ATTESE or anno < ANNO_MINIMO:
            continue
        valori = (province_profile._serie().get(raw) or {}).get(anno)
        if not valori or len(valori["valori"]) != PROVINCE_ATTESE:
            continue
        ammessi.append({
            "id": raw,
            "name": voce["name"],
            "unit": voce["unit"],
            "family": voce["family"],
            "theme": riga["domain_name"],
            "year": anno,
        })
    return tuple(ammessi)


# La sfida del giorno


def puzzle_id(giorno):
    return f"daily:{giorno.isoformat()}"


def provincia_del_giorno(giorno, chiave=None):
    """La provincia misteriosa di un giorno: una giocabile di una regione
    idonea, dal seed. `chiave` serve ai test."""
    idonee = set(game_daily.regioni_idonee(game_daily.MINIMO_COMPARE))
    candidate = sorted(
        (p for p in game_daily.province_pool(solo_giocabili=True) if p["region"] in idonee),
        key=lambda p: p["key"],
    )
    rng = random.Random(game_daily.seed_giorno("provincia", giorno, chiave))
    return rng.choice(candidate)


def _campi_indizio(ind, chiave_provincia):
    """L'indizio di un indicatore per una provincia: valore, posizione fra le
    107, anno e fonte. Le spiegazioni e il link alla scheda seguono il recap."""
    anno = ind["year"]
    dati = province_profile._serie()[ind["id"]][anno]
    spiegazione = bes_data.get_bes_manifest("provincia")[ind["id"]]["explain"]
    return {
        "id": ind["id"],
        "name": ind["name"],
        "theme": ind["theme"],
        "unit": ind["unit"],
        "year": anno,
        "value": dati["valori"][chiave_provincia],
        "rank": dati["posizioni"][chiave_provincia],
        "province_count": PROVINCE_ATTESE,
        "source_label": sources.SOURCES["bes"]["label"],
        "source_url": bes_data.BES_SOURCE_URLS["provincia"],
        "path": bes_data.bes_level_path(ind["id"], "provincia"),
        "description": spiegazione["plain"],
        "value_explanation": spiegazione["example"],
        "reading": spiegazione["reading"],
    }


def indizi_del_giorno(giorno, chiave=None):
    """I sei indizi della provincia del giorno, dal meno al piu' distintivo."""
    mistero = provincia_del_giorno(giorno, chiave)["key"]
    rng = random.Random(game_daily.seed_giorno("provincia-indizi", giorno, chiave))
    candidati = sorted(indizi_ammessi(), key=lambda i: i["id"])
    rng.shuffle(candidati)
    scelti, famiglie = [], set()
    for ind in candidati:  # un indizio per famiglia finche' ce ne sono
        if ind["family"] not in famiglie and len(scelti) < TENTATIVI:
            scelti.append(ind)
            famiglie.add(ind["family"])
    for ind in candidati:
        if ind not in scelti and len(scelti) < TENTATIVI:
            scelti.append(ind)
    indizi = [_campi_indizio(ind, mistero) for ind in scelti]
    meta = (PROVINCE_ATTESE + 1) / 2
    indizi.sort(key=lambda c: (abs(c["rank"] - meta), c["id"]))
    return indizi


def opzioni(livello, giorno, chiave=None):
    """Le province fra cui si indovina a un livello, con il centroide per la
    mappa. Non dicono quali sono giocabili e non dicono qual e' la misteriosa."""
    mistero = provincia_del_giorno(giorno, chiave)
    pool = game_daily.province_pool()
    if livello == "stessa_regione":
        pool = [p for p in pool if p["region"] == mistero["region"]]
    return [
        {"key": p["key"], "name": p["name"], "region": p["region"], "x": p["x"], "y": p["y"]}
        for p in sorted(pool, key=lambda p: p["name"])
    ]


# Il token


def _serializzatore():
    return URLSafeTimedSerializer(app.secret_key, salt=_SALT)


def _firma(stato):
    return _serializzatore().dumps(stato)


def _leggi(token):
    if not token or not isinstance(token, str):
        raise ErroreProvincia("token_non_valido")
    try:
        stato = _serializzatore().loads(token, max_age=_TOKEN_MAX_AGE_S)
    except BadData:
        raise ErroreProvincia("token_non_valido") from None
    if (
        not isinstance(stato, dict)
        or stato.get("l") not in LIVELLI
        or not isinstance(stato.get("p"), str)
        or not isinstance(stato.get("g"), list)
        or not isinstance(stato.get("sid"), str)
    ):
        raise ErroreProvincia("token_non_valido")
    return stato


def _controlla_livello(livello):
    if livello not in LIVELLI:
        raise ErroreProvincia("livello_sconosciuto")


# Le risposte


def payload(livello, now=None, chiave=None):
    """La sfida di OGGI (a Roma) a un livello: mai una data a scelta del client.
    Porta il primo indizio e le opzioni, mai la provincia ne' gli altri indizi."""
    _controlla_livello(livello)
    giorno = game_daily.oggi_roma(now)
    mistero = provincia_del_giorno(giorno, chiave)
    indizi = indizi_del_giorno(giorno, chiave)
    regione = None
    if livello == "stessa_regione":
        chiave_regione = mistero["region_key"]
        regione = {"name": mistero["region"], "key": chiave_regione, "viewbox": maps.zoom(chiave_regione)["viewbox"]}
    token = _firma({"p": puzzle_id(giorno), "l": livello, "g": [], "sid": _nuova_sessione()})
    risposta = {
        "puzzle_id": puzzle_id(giorno),
        "number": game_daily.numero_sfida(giorno),
        "date": giorno.isoformat(),
        "next_puzzle_at": game_daily.prossima_sfida_roma(giorno),
        "level": livello,
        "attempts_total": TENTATIVI,
        "clues_total": len(indizi),
        "region": regione,
        "provinces": opzioni(livello, giorno, chiave),
        "clue": dict(indizi[0]),
        "token": token,
    }
    if livello == "stessa_regione":
        # Le province delle altre regioni, solo nome e regione: il client le usa per dire
        # "Milano non e' in Puglia" a chi scrive una provincia che non e' fra le opzioni. La regione
        # e' gia' nel payload e la misteriosa e' fra le opzioni, quindi niente si svela.
        risposta["other_provinces"] = [
            {"name": p["name"], "region": p["region"]}
            for p in sorted(game_daily.province_pool(), key=lambda p: p["name"])
            if p["region"] != mistero["region"]
        ]
    return risposta


@lru_cache(maxsize=1)
def _anagrafe():
    return {p["key"]: p for p in game_daily.province_pool()}


def _nuova_sessione():
    return random.SystemRandom().randbytes(8).hex()


def _confronto(valore_misterioso, valore_tentativo):
    """Come in `game._compare`: descrive il valore TENTATO rispetto al mistero."""
    if valore_tentativo is None or valore_misterioso is None:
        return "unknown"
    if abs(valore_tentativo - valore_misterioso) < 1e-9:
        return "equal"
    return "higher" if valore_tentativo > valore_misterioso else "lower"


def _riepilogo(indizi):
    righe = []
    for indizio in indizi:
        valori = province_profile._serie()[indizio["id"]][indizio["year"]]["valori"]
        righe.append({**indizio, "province_avg": round(fmean(valori.values()), 3)})
    return righe


def valuta_tentativo(token, chiave_provincia, now=None, chiave=None):
    """Valuta un tentativo e ritorna il risultato, o solleva `ErroreProvincia`.
    Il numero del tentativo lo decide il token, mai il client."""
    stato = _leggi(token)
    giorno = game_daily.oggi_roma(now)
    if stato["p"] != puzzle_id(giorno):
        raise ErroreProvincia("sfida_scaduta", 410)
    livello, tentate = stato["l"], stato["g"]
    attempt = len(tentate) + 1
    if attempt > TENTATIVI:
        raise ErroreProvincia("partita_conclusa", 409)
    mistero = provincia_del_giorno(giorno, chiave)
    if tentate and tentate[-1] == mistero["key"]:
        raise ErroreProvincia("partita_conclusa", 409)
    if not isinstance(chiave_provincia, str) or chiave_provincia not in {
        o["key"] for o in opzioni(livello, giorno, chiave)
    }:
        raise ErroreProvincia("provincia_non_valida")
    if chiave_provincia in tentate:
        raise ErroreProvincia("provincia_gia_tentata")
    visti = cache.get(f"provincia:{stato['sid']}") or 0
    if len(tentate) < visti:
        raise ErroreProvincia("token_superato", 409)
    cache.set(f"provincia:{stato['sid']}", attempt, timeout=_TOKEN_MAX_AGE_S)

    indizi = indizi_del_giorno(giorno, chiave)
    corretta = chiave_provincia == mistero["key"]
    finita = corretta or attempt >= TENTATIVI
    tentata = _anagrafe()[chiave_provincia]
    km, direzione = game_daily.distanza_km_direzione(chiave_provincia, mistero["key"])

    confronti = []
    for indizio in indizi[:attempt]:
        dati = province_profile._serie()[indizio["id"]][indizio["year"]]
        valore = dati["valori"].get(chiave_provincia)
        confronti.append({
            "id": indizio["id"],
            "name": indizio["name"],
            "unit": indizio["unit"],
            "comparison": "equal" if corretta else _confronto(indizio["value"], valore),
            "guess_value": valore,
            "guess_rank": dati["posizioni"].get(chiave_provincia),
            "mystery_rank": indizio["rank"],
            "province_count": PROVINCE_ATTESE,
        })

    soluzione = riepilogo = None
    if finita:
        soluzione = {
            "province": mistero["name"],
            "province_key": mistero["key"],
            "path": f"/provincia/{mistero['key']}",
            "region": mistero["region"],
            "region_key": mistero["region_key"],
            "region_path": f"/regione/{mistero['region_key']}",
        }
        riepilogo = _riepilogo(indizi)

    nuovo = _firma({**stato, "g": [*tentate, chiave_provincia]})
    return {
        "correct": corretta,
        "level": livello,
        "attempt": attempt,
        "province": tentata["name"],
        "province_key": chiave_provincia,
        "distance_km": km,
        "direction": direzione,
        "same_region": tentata["region"] == mistero["region"],
        "feedback": confronti,
        "next_clue": None if finita else dict(indizi[attempt]),
        "finished": finita,
        "solution": soluzione,
        "recap": riepilogo,
        "token": nuovo,
    }
