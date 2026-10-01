"""La sfida del giorno di "Dov'è la provincia?": dieci province da trovare su una
mappa muta, stesse per tutti, valutate dal server.

Il contratto con il client (pagina `/quiz/province-italiane`) sta qui sotto, e ogni
cambio di forma del JSON si scrive qui prima che nel codice.

**Apertura** `GET /api/game/map/daily/session?level=italia|regione&mode=map|list`
(sessione sempre nuova). 400 `bad_request` su livello o modalita' sconosciuti e su
`mode=list` con `level=regione`, 503 `seed_unavailable` senza `GAME_SEED_KEY` in
produzione, 429 `rate_limited`. Il corpo 200 e' MINIMO:

    {puzzle_id, number, date, next_puzzle_at, level, level_label, mode, total,
     points_max, question, token}           e in modalita' `list` anche `regions`

- `question` = `{index, name, label}`. `name` e' il nome da mostrare (quello di
  `province_codes.csv`, tranne "Aosta (Valle d'Aosta)", vedi `display_name`),
  `label` la frase intera della domanda: "Dov'è Lecce?", al livello `regione`
  "Dov'è Lecce? Si trova in Puglia.", in modalita' `list` "In quale regione si
  trova Lecce?". Al livello `regione` porta anche `region` (nome) e `region_key`.
- `regions` = le 20 regioni `[{key, name}]` nell'ordine di `REGION_ORDER`.
- NIENTE coordinate, nessun'altra provincia del giorno, mai la chiave, il centroide
  o (al livello `italia`) la regione della provincia chiesta. I centri per la
  tastiera si ricavano dal DOM, i riquadri delle regioni stanno nel template.

**Risposta** `POST /api/game/map/daily/answer`, corpo `{token, puzzle_id, q,
province_key}` in modalita' `map` o `{token, puzzle_id, q, region_key}` in `list`.
Dal client arriva solo la chiave: livello e modalita' vengono dal token firmato,
mai dal corpo. Gli errori, nell'ordine in cui si controllano:

1. `puzzle_id` diverso dalla sfida di oggi a Roma: 400 `puzzle_changed`;
2. token scaduto (oltre le 12 ore di `quiz_tokens`): 400 `session_expired`;
3. token assente, di un'altra modalita', di un altro giorno, o che non lega la
   domanda `q` (intero 0..9): 400 `token_invalid`;
4. chiave che non e' una delle 107 province (o, in `list`, delle 20 regioni): 400
   `bad_request`, PRIMA del claim, cosi' un errore non brucia la domanda;
5. la stessa domanda risposta di nuovo: 409 `round_already_answered`.

Nessuna risposta diversa da 200 porta `chosen`, `right`, `distance_km` o
`direction`: si rivelano solo dopo `quiz_tokens.claim_round`. Il corpo 200:

    {index, esito, points, score: {points, max, answered},
     chosen: {key, name, region, path},
     right: {key, name, region, region_key, path},
     distance_km, direction, finished, next_question, token}
    e a partita finita anche
    summary: {puzzle_id, number, date, next_puzzle_at, score, esiti, achievements}

- `esito` e' `exact` (2 punti), `region` (1: provincia sbagliata ma della stessa
  regione) o `miss` (0). In modalita' `list` e' `exact` (1 punto, regione giusta) o
  `miss` (0), e `chosen` e' la regione scelta (`region` uguale a `name`, `path`
  `/regione/<key>`).
- `distance_km` e `direction` vanno dalla provincia scelta a quella giusta, fra i
  centroidi (`game_daily.distanza_km_direzione`): sono una STIMA, e il testo deve
  dirlo. `null` se l'esito e' esatto o in modalita' `list`.
- `next_question` ha la stessa forma di `question` (al livello `regione` quindi
  anche `region` e `region_key`, che servono allo zoom), `null` dopo l'ultima.
- `summary.esiti` sono i 10 esiti in ordine. `summary.achievements` e' la lista dei
  traguardi appena valutati per chi ha un account, vuota per chi non ce l'ha.

**Il giorno e il seed.** Il giorno e' quello di Roma (`game_daily.oggi_roma`), e il
`puzzle_id` del client deve essere quello di oggi: chi apre alle 23:59:50 e risponde
alle 00:00:05 riceve `puzzle_changed`. Le province escono da
`HMAC(GAME_SEED_KEY, "mappa-<livello>|<data>")` (`game_daily.seed_giorno`), quindi i
due livelli hanno due insiemi diversi e quello di domani non si calcola leggendo il
repo. Senza la chiave in produzione si risponde 503 (`game_daily.chiave_seed`).

**La storia.** Una provincia non torna prima di 7 giorni: il giorno N esclude quelle
dei 6 giorni prima, che a loro volta dipendono dai precedenti. Nessuno le ha
salvate, quindi si ricalcolano in avanti da `MAP_EPOCH` con `_history`, una funzione
PURA in cache per `(giorno, livello, chiave)`, con la chiave risolta prima della
cache (cosi' una sfida gia' calcolata non aggira il 503). Mai una lista condivisa
che si allunga: con 8 thread due richieste la allungherebbero due volte.

    QUALSIASI cambio di dati (aree di `province_centroidi.json`, regioni di
    `province_codes.csv`, `MIX`, `WINDOW_DAYS`, la regola delle fasce) cambia la
    storia ricalcolata e quindi la sfida di OGGI, e chi sta giocando prende
    `token_invalid`. Il test d'oro (`tests/unit/test_game_mappa_puro.py`) lo rende
    visibile. Quando i dati cambiano di proposito, `MAP_EPOCH` passa al giorno del
    cambio: la storia riparte, al piu' con una ripetizione al confine.
    Ruotare `GAME_SEED_KEY` cambia anche la storia, quindi la sfida di oggi: mai a
    meta' giornata (stessa avvertenza di `game_daily`).

**Il token.** `quiz_tokens` v2 senza modifiche, modalita' `MODE` (`peek_state` la
rifiuta: niente classifica). L'impronta del round lega `"mappa"`, la data e la chiave
giusta, quindi un token di ieri non vale oggi. Il token e' firmato, NON cifrato: il
campo `SCORE_KEY` (data, livello, modalita', punti, esiti) si legge, e non contiene
mai una chiave del giorno. `fp` non e' un segreto: e' uno SHA-256 troncato di campi
tutti nel token piu' la chiave giusta, e 107 tentativi la trovano. Qui non conta,
perche' la domanda dice gia' il nome e la sagoma ha lo slug nel DOM.
`quiz_tokens.claim_round` fallisce aperto se il DB non risponde: chi ha visto `right`
potrebbe rimandare il token vecchio con la chiave giusta. Il punteggio persistito non
cambia (`daily_scores` sta nello stesso DB), si gonfia solo quello mostrato.

**La Sardegna.** Vedi `QUESTION_EXCLUDED_REGIONS`.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta
from functools import lru_cache

from itsdangerous import BadData, SignatureExpired

from app import game_daily, quiz_tokens
from app.game_daily import oggi_roma

MODE = "mappa_daily"
LEVELS = ("italia", "regione")
ANSWER_MODES = ("map", "list")
QUESTIONS = 10
POINTS = {"exact": 2, "region": 1, "miss": 0}
# Senza mappa conta solo la regione: un punto, massimo 10. E' un altro esercizio.
LIST_POINTS = {"exact": 1, "miss": 0}
WINDOW_DAYS = 6
# Ancora del calcolo in avanti della storia, NON la data di lancio. Si sposta solo
# quando i dati cambiano di proposito (vedi il docstring del modulo).
MAP_EPOCH = date(2026, 10, 1)
# Campo del token con data, livello, modalita', punti ed esiti. Firmato, non cifrato.
SCORE_KEY = "mappa"
# Il gioco in `daily_scores` e in `daily_counter`: tre esercizi diversi, tre conte.
SCORE_GAMES = {
    ("italia", "map"): "mappa",
    ("regione", "map"): "mappa_regione",
    ("italia", "list"): "mappa_elenco",
}
# Quante province per fascia (grandi, medie, piccole) per difficolta' del giorno
# della settimana (`game_daily.DIFFICOLTA_SETTIMANA`).
MIX = {0: (6, 4, 0), 1: (4, 4, 2), 2: (3, 4, 3), 3: (2, 4, 4), 4: (1, 3, 6)}
# Province minime nella regione per il livello `regione` (con una sola, la domanda
# si risponde da sola).
REGION_LEVEL_MIN = 3
# Dal 1 gennaio 2026 l'Istat conta 110 unita' e la Sardegna ha un assetto nuovo (due
# citta' metropolitane, Cagliari e Sassari, e sei province). I tracciati e i dati
# del sito sono ancora a 107, con la Sardegna di prima: le sue cinque province
# restano sulla mappa ma non si chiedono, perche' "Dov'è Sud Sardegna?" chiederebbe
# una provincia che non esiste piu'.
QUESTION_EXCLUDED_REGIONS = ("Sardegna",)
# Le forme ufficiali dove differiscono dal nome di `province_codes.csv` (quello che
# il giocatore cerca e scrive), per l'elenco indicizzabile della pagina.
OFFICIAL_NAMES = {
    "aosta": "Valle d'Aosta/Vallée d'Aoste",
    "bolzano": "Bolzano/Bozen",
    "reggio-emilia": "Reggio nell'Emilia",
}
# Aosta coincide con l'intera regione: il nome da solo, su una mappa muta, chiede
# una sagoma che il giocatore conosce come "Valle d'Aosta".
DISPLAY_NAMES = {"aosta": "Aosta (Valle d'Aosta)"}
LEVEL_LABELS = {"italia": "Tutta Italia", "regione": "Regione indicata"}
_PROVINCE_PATH = "/provincia/"
_REGION_PATH = "/regione/"


def puzzle_id(day):
    return f"daily:{day.isoformat()}"


# I nomi

def display_name(province):
    """Il nome da mostrare nella domanda e nell'esito."""
    return DISPLAY_NAMES.get(province["key"], province["name"])


def official_name(province):
    """La forma ufficiale, o il nome di `province_codes.csv` se coincidono."""
    return OFFICIAL_NAMES.get(province["key"], province["name"])


def static_list():
    """Le 107 province in ordine alfabetico, per l'elenco indicizzabile della pagina:
    `{key, name, official_name, path}`. Non dipende dal seed."""
    entries = [
        {"key": p["key"], "name": p["name"], "official_name": official_name(p),
         "path": _PROVINCE_PATH + p["key"]}
        for p in game_daily.province_pool()
    ]
    return sorted(entries, key=lambda entry: entry["name"].casefold())


# I territori

def _provinces():
    """{chiave: provincia} delle 107, con regione e centroide (vedi `game_daily`)."""
    return {p["key"]: p for p in game_daily.province_pool()}


@lru_cache(maxsize=1)
def _regions():
    """Le 20 regioni `(key, name)` nell'ordine di `REGION_ORDER`."""
    from app import profiles
    from app.data import REGION_ORDER

    return tuple((profiles.region_key_for(r), r) for r in REGION_ORDER)


@lru_cache(maxsize=2)
def pool(level):
    """Le chiavi che possono essere chieste a un livello, in ordine: le 107 senza la
    Sardegna, e al livello `regione` solo le regioni con almeno 3 province."""
    _check_level(level)
    eligible = set(game_daily.regioni_idonee(REGION_LEVEL_MIN)) if level == "regione" else None
    return tuple(sorted(
        p["key"] for p in game_daily.province_pool()
        if p["region"] not in QUESTION_EXCLUDED_REGIONS and (eligible is None or p["region"] in eligible)
    ))


def _areas():
    """{chiave: area della sagoma} da `province_centroidi.json`."""
    shapes = json.loads(game_daily.CENTROIDI_JSON.read_text(encoding="utf-8"))["province"]
    return {k: v["area"] for k, v in shapes.items()}


@lru_cache(maxsize=2)
def size_bands(level):
    """Le tre fasce (grandi, medie, piccole) del pool di un livello, per area della
    sagoma dalla piu' grande, divise in terzi (102 domande possibili a `italia`,
    34/34/34, e 93 a `regione`, 31/31/31). La dimensione misura quanto e' difficile
    trovare la sagoma, non quanto e' nota la provincia. Ogni fascia e' in ordine di
    chiave."""
    areas = _areas()
    ordered = sorted(pool(level), key=lambda k: (-areas[k], k))
    n = len(ordered)
    cuts = (0, round(n / 3), round(2 * n / 3), n)
    return tuple(tuple(sorted(ordered[cuts[i]:cuts[i + 1]])) for i in range(3))


def bands_fingerprint(level):
    """Impronta corta delle fasce di un livello, per il test d'oro."""
    text = "|".join(",".join(band) for band in size_bands(level))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# La sfida del giorno

def _check_level(level):
    if level not in LEVELS:
        raise ValueError(f"livello sconosciuto: {level!r}")


def _pick_day(day, level, key, recent):
    """Le 10 chiavi di un giorno, dalle fasce grandi alle piccole, escluse quelle in
    `recent`. Solleva se una fascia non ne ha abbastanza (con le fasce e il `MIX` di
    oggi non succede: lo prova un test su cinque anni)."""
    rng = random.Random(game_daily.seed_giorno(f"mappa-{level}", day, key))
    counts = MIX[game_daily.DIFFICOLTA_SETTIMANA[day.weekday()]]
    picks = []
    for band, n in zip(size_bands(level), counts):
        free = [k for k in band if k not in recent]
        if len(free) < n:
            raise RuntimeError(f"mappa: la fascia non basta il {day} ({level})")
        picks.extend(rng.sample(free, n))
    return tuple(picks)


@lru_cache(maxsize=4)
def _history(day, level, key):
    """Le sfide di tutti i giorni da `MAP_EPOCH` a `day` compreso, una tupla di tuple
    di 10 chiavi. Pura: stessi argomenti, stesso risultato, in ogni processo. Un
    giorno prima dell'epoca non ha storia e si calcola da solo."""
    _check_level(level)
    days = []
    current = min(day, MAP_EPOCH)
    while current <= day:
        recent = {k for picks in days[-WINDOW_DAYS:] for k in picks}
        days.append(_pick_day(current, level, key, recent))
        current += timedelta(days=1)
    return tuple(days)


def daily_provinces(day, level, key=None):
    """Le 10 chiavi della sfida di `day` a un livello, dalle facili alle difficili.
    La chiave del seed si risolve qui, PRIMA della cache di `_history`."""
    _check_level(level)
    return _history(day, level, game_daily.chiave_seed() if key is None else key)[-1]


# Le domande

def question(day, level, mode, index):
    """La domanda `index` senza la risposta: il nome, la frase e, al livello
    `regione`, la regione (che e' parte della domanda)."""
    province = _provinces()[daily_provinces(day, level)[index]]
    name = display_name(province)
    if mode == "list":
        label = f"In quale regione si trova {name}?"
    elif level == "regione":
        label = f"Dov'è {name}? Si trova in {province['region']}."
    else:
        label = f"Dov'è {name}?"
    body = {"index": index, "name": name, "label": label}
    if level == "regione":
        body["region"] = province["region"]
        body["region_key"] = province["region_key"]
    return body


def outcome(chosen_key, right_key):
    """`exact`, `region` (stessa regione, provincia sbagliata) o `miss`. La regione
    viene da `province_codes.csv`: un dato, non una geometria."""
    if chosen_key == right_key:
        return "exact"
    provinces = _provinces()
    return "region" if provinces[chosen_key]["region"] == provinces[right_key]["region"] else "miss"


def list_outcome(region_key, right_key):
    """In modalita' `list`: `exact` se la regione e' quella della provincia, o `miss`."""
    return "exact" if _provinces()[right_key]["region_key"] == region_key else "miss"


def points_max(mode):
    return QUESTIONS * (LIST_POINTS if mode == "list" else POINTS)["exact"]


def _bind(state, day, level, right_key):
    return quiz_tokens.bind_round(state, "mappa", day.isoformat(), [right_key], level)


def _check_round(state, day, right_key):
    """True se il token lega proprio questa domanda di questo giorno."""
    session, _ = quiz_tokens.apply_answer(state, "mappa", day.isoformat(), [right_key], False)
    return session is not None


# L'apertura

def open_session(level, mode, now=None):
    """Il corpo dell'apertura, o None se livello o modalita' non valgono (400).
    Sessione nuova a ogni apertura, senza timer: livello e modalita' viaggiano da qui
    nel token firmato."""
    if level not in LEVELS or mode not in ANSWER_MODES or (mode == "list" and level != "italia"):
        return None
    day = oggi_roma(now)
    keys = daily_provinces(day, level)
    state = quiz_tokens.load_state(None, MODE, timer=False)
    state = {**state, SCORE_KEY: {"d": day.isoformat(), "l": level, "m": mode, "p": 0, "e": []}}
    body = {
        "puzzle_id": puzzle_id(day),
        "number": game_daily.numero_sfida(day),
        "date": day.isoformat(),
        "next_puzzle_at": game_daily.prossima_sfida_roma(day),
        "level": level,
        "level_label": LEVEL_LABELS[level],
        "mode": mode,
        "total": QUESTIONS,
        "points_max": points_max(mode),
        "question": question(day, level, mode, 0),
        "token": _bind(state, day, level, keys[0]),
    }
    if mode == "list":
        body["regions"] = [{"key": k, "name": n} for k, n in _regions()]
    return body


def sid_of_token(token):
    """Il `sid` della sessione, per il limite di frequenza."""
    return quiz_tokens.load_state(token, MODE)["sid"]


def _expired(token):
    """True se il token e' buono ma piu' vecchio delle 12 ore di `quiz_tokens`."""
    if not token or not isinstance(token, str):
        return False
    try:
        quiz_tokens._serializer().loads(token, max_age=quiz_tokens._MAX_AGE_S)
    except SignatureExpired:
        return True
    except BadData:
        return False
    return False


# La risposta

def answer(data, now=None):
    """(status, corpo, partita) della risposta a una domanda. `partita` e' None
    tranne all'ultima risposta valida: allora `{game, date, points, plausible}`,
    quello che la rotta registra (contatore, punteggio dell'account). Gli errori e il
    loro ordine sono nel docstring del modulo."""
    token = data.get("token")
    state = quiz_tokens.load_state(token, MODE)
    day = oggi_roma(now)
    if data.get("puzzle_id") != puzzle_id(day):
        return 400, {"error": "puzzle_changed"}, None
    if state.get("fp") is None and _expired(token):
        return 400, {"error": "session_expired"}, None
    saved = state.get(SCORE_KEY) or {}
    level, mode = saved.get("l"), saved.get("m")
    if (level not in LEVELS or (level, mode) not in SCORE_GAMES
            or saved.get("d") != day.isoformat() or state.get("x") != level):
        return 400, {"error": "token_invalid"}, None
    index = data.get("q")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < QUESTIONS:
        return 400, {"error": "token_invalid"}, None
    if state.get("q") != index + 1:
        return 400, {"error": "token_invalid"}, None
    keys = daily_provinces(day, level)
    right_key = keys[index]
    if not _check_round(state, day, right_key):
        return 400, {"error": "token_invalid"}, None

    provinces = _provinces()
    regions = dict(_regions())
    if mode == "list":
        chosen_key = data.get("region_key")
        if not isinstance(chosen_key, str) or chosen_key not in regions:
            return 400, {"error": "bad_request"}, None
        result = list_outcome(chosen_key, right_key)
        points = LIST_POINTS[result]
    else:
        chosen_key = data.get("province_key")
        if not isinstance(chosen_key, str) or chosen_key not in provinces:
            return 400, {"error": "bad_request"}, None
        result = outcome(chosen_key, right_key)
        points = POINTS[result]

    if not quiz_tokens.claim_round(state["sid"], state["q"]):
        return 409, {"error": "round_already_answered"}, None

    # Da qui in poi la domanda e' chiusa e la risposta si puo' rivelare.
    total = int(saved.get("p") or 0) + points
    results = [*(saved.get("e") or []), result]
    state = {**state, SCORE_KEY: {**saved, "p": total, "e": results}}
    _, token = quiz_tokens.apply_answer(state, "mappa", day.isoformat(), [right_key], result == "exact")
    finished = index + 1 == QUESTIONS
    if not finished:
        token = _bind(quiz_tokens.load_state(token, MODE), day, level, keys[index + 1])

    right = provinces[right_key]
    if mode == "list":
        chosen = {"key": chosen_key, "name": regions[chosen_key], "region": regions[chosen_key],
                  "path": _REGION_PATH + chosen_key}
        distance, direction = None, None
    else:
        picked = provinces[chosen_key]
        chosen = {"key": chosen_key, "name": display_name(picked), "region": picked["region"],
                  "path": _PROVINCE_PATH + chosen_key}
        distance, direction = (None, None) if result == "exact" else game_daily.distanza_km_direzione(chosen_key, right_key)
    score = {"points": total, "max": points_max(mode), "answered": index + 1}
    body = {
        "index": index,
        "esito": result,
        "points": points,
        "score": score,
        "chosen": chosen,
        "right": {"key": right_key, "name": display_name(right), "region": right["region"],
                  "region_key": right["region_key"], "path": _PROVINCE_PATH + right_key},
        "distance_km": distance,
        "direction": direction,
        "finished": finished,
        "next_question": None if finished else question(day, level, mode, index + 1),
        "token": token,
    }
    game = None
    if finished:
        body["summary"] = {
            "puzzle_id": puzzle_id(day),
            "number": game_daily.numero_sfida(day),
            "date": day.isoformat(),
            "next_puzzle_at": game_daily.prossima_sfida_roma(day),
            "score": score,
            "esiti": results,
            "achievements": [],
        }
        # Dieci domande in meno di 15 secondi dall'apertura non sono una persona: la
        # partita resta valida per chi la gioca, ma non va nel punteggio dell'account.
        plausible = quiz_tokens.is_plausible({**state, "r": state["r"] + 1})
        game = {"game": SCORE_GAMES[(level, mode)], "date": day.isoformat(),
                "points": total, "plausible": plausible}
    return 200, body, game
