"""La sfida del giorno di "Chi è maggiore?": dieci coppie, stesse per tutti.

Qui c'è la logica del giornale, tutto il resto è in `app/game_daily.py` (che
sceglie le coppie di oggi) e in `app/quiz.py` (che sa giudicare un confronto fra
regioni). Il modulo non tocca nessuno dei due e non li duplica.

**Il giorno lo sceglie il server.** Ogni richiesta ricostruisce la sfida di
oggi a Roma con `game_daily.daily_compare`: il client manda solo
`puzzle_id`, indice di domanda e scelta, e il `puzzle_id` deve essere quello di
oggi. Nessuna data scelta dal client, quindi nessuna soluzione di un giorno
futuro può uscire. Se la mezzanotte di Roma passa fra l'apertura e la risposta,
la risposta arriva a una sfida diversa e viene rifiutata (`puzzle_changed`).

**Il livello lo sceglie il server.** Lo dichiaro il client all'apertura
(`?level=`) e da lì viaggia dentro il token firmato, non in un campo del corpo
della risposta: un client non può farsi valutare la coppia di un livello che non
ha chiesto. Stessa regola del tempo (`timer`) e della difficoltà.

**Il tempo lo misura il server.** Il token v2 porta `t` (timer sì o no) e `iat`
(quando è uscito il round): `quiz_tokens.round_timing` dice se la risposta è
arrivata in tempo, prima del tempo (un `timeout` che scatta troppo presto non
vale) o troppo tardi. Oltre i 10 s più 2 di tolleranza la risposta conta come un
tempo scaduto: il round si chiude, la risposta è sbagliata e il corpo è quello di
un `timeout` più `late: true`, così "Avanti" funziona. Rifiutarla con un 400 senza
chiudere il round rendeva la partita impossibile da finire (ogni nuovo invio era
di nuovo tardi).

**La domanda dopo la lega "Avanti".** La risposta a una domanda non lega la
successiva: lo fa `next_question` (`POST /api/game/compare/daily/next`) quando il
giocatore preme il pulsante, cosi' il tempo di lettura della rivelazione non
consuma i 12 secondi della domanda dopo.

**Un round, una risposta.** `quiz_tokens.claim_round` mette (sessione, domanda)
nel DB: la seconda risposta alla stessa coppia è un 409, così un doppio invio
(un click e la scadenza del timer insieme) non conta due volte. Il secondo
invio è ignorato dal client senza messaggio di errore.

**Il punteggio vive nel token.** Il token v2 non ha un contatore delle risposte
giuste (e `app/quiz_tokens.py` non si tocca), ma firma tutto quello che gli
diamo: `apply_answer` copia lo stato ricevuto nel token nuovo, quindi il
punteggio che calcolo qui dentro resta firmato dal server e torna con la
risposta. Non è un campo che il client può scrivere: riaprire un token vecchio
non cambia la conta, e il round singolo tiene gli invii duplicati fuori.

**I valori veri, e da dove vengono.** Al livello "regioni" la valutazione è
`quiz.evaluate_compare`, la stessa del round a serie. Ai livelli con le province
i dati sono quelli provinciali (`game_daily._indicator_rows`, la stessa
funzione privata da cui la sfida è stata composta: rileggere i dati con un
secondo percorso li farebbe divergere) e il vincitore si calcola qui, perché
`quiz.evaluate_compare` confronta regioni. Lo stesso indicatore può esistere a
entrambi i livelli: al livello provincia la risposta deve usare il dato
provinciale, non quello regionale.
"""

from __future__ import annotations

from app import bes_data, game_daily, game_facts, quiz, quiz_tokens, sources
from app.game_daily import LEVELS, today_rome

# Modalita' di token propria: il token della sfida del giorno non entra nelle serie
# (`/api/game/compare/round|answer`) ne' nella classifica (`peek_state` la rifiuta), e
# il token di una serie apre una sessione nuova qui.
MODE = "compare_daily"
PAIRS = game_daily.COMPARE_PAIRS
# Etichetta della fonte per i livelli con le province, che non passano da
# quiz.evaluate_compare: viene da app/sources.py, l'unica fonte di verita' dei
# nomi (un'etichetta scritta qui ha gia' pubblicato una serie sotto un altro nome).
PROVINCE_SOURCE = sources.SOURCES["bes"]["label"]
# La scheda del territorio: la stessa forma degli altri giochi (`/regione/<key>`
# e `/provincia/<key>`).
TERRITORY_PATHS = {"regioni": "/regione/", "stessa_regione": "/provincia/", "province": "/provincia/"}
# Campo del token con la data della sfida e le risposte giuste. Firmato come
# tutto il resto del token.
SCORE_KEY = "sfida"

LEVEL_LABELS = {
    "regioni": "Regioni",
    "stessa_regione": "Province della stessa regione",
    "province": "Province",
}


def today_challenge_id(day):
    return f"daily:{day.isoformat()}"


def level_label(level):
    return LEVEL_LABELS.get(level, LEVEL_LABELS["regioni"])


def _challenge(day, level):
    """La sfida del giorno a un livello. La cache sta in `game_daily` (per giorno,
    livello e chiave del seed), cosi' il controllo della chiave si fa a ogni richiesta."""
    return game_daily.daily_compare(day, level)


def _territory_path(level, key):
    return TERRITORY_PATHS.get(level, TERRITORY_PATHS["regioni"]) + key


def _question(pair, index, level):
    """La domanda `indice` senza valori e senza soluzione: quello che il client
    vede prima di rispondere."""
    return {
        "index": index,
        "indicator": dict(pair["indicator"]),
        "a": {**pair["a"], "path": _territory_path(level, pair["a"]["key"])},
        "b": {**pair["b"], "path": _territory_path(level, pair["b"]["key"])},
    }


def _province_indicator(ind_id, year, name, unit):
    """I campi dell'indicatore per una risposta ai livelli con le province: nome
    leggibile e unità sono quelli scelti per il gioco in
    `config/game_indicators.csv`, la spiegazione e il link canonico vengono dal
    catalogo BES, l'unica fonte che li ha per gli indicatori solo provinciali."""
    raw = game_daily.provincial_id(ind_id)
    info = bes_data.get_bes_manifest("provincia").get(raw)
    if info is None:
        return None
    try:
        path = bes_data.bes_path(raw)
    except LookupError:
        path = None
    return {
        "id": ind_id,
        "name": name,
        "unit": unit,
        "year": year,
        "description": info["explain"]["plain"],
        "value_explanation": info["explain"]["example"],
        "path": path,
        "source_label": PROVINCE_SOURCE,
        "source_url": bes_data.BES_SOURCE_URLS["provincia"],
    }


def _province_values(ind_id, keys):
    """(anno, {chiave: valore}) per un indicatore provinciale, letti dalla stessa
    funzione che ha composto la sfida."""
    found = game_daily._indicator_rows({"id": ind_id}, "province")
    if found is None:
        return None, None
    year, rows = found
    values = {row["key"]: row["value"] for row in rows}
    if any(values.get(key) is None for key in keys):
        return None, None
    return year, values


def _side(choice):
    """Il lato della coppia da una scelta del client ("region_a", "region_b" o
    "timeout"), None per il tempo scaduto. I nomi sono quelli del round a serie,
    così il client non deve imparare due vocabulari."""
    if choice == "region_a":
        return "a"
    if choice == "region_b":
        return "b"
    return None


def _evaluate(pair, level, choice):
    """Il risultato di una risposta, o None se l'input non è valido (chi chiama
    risponde 400). I valori sono quelli veri, la risposta porta l'indicatore con
    `path` e `description` e i due territori con la loro scheda: è tutto quello
    che la fine partita deve mostrare. `winner` è "a" o "b"."""
    if choice not in quiz.COMPARE_CHOICES:
        return None
    side = _side(choice)
    ind = pair["indicator"]
    a, b = pair["a"], pair["b"]
    if level == "regioni":
        base = quiz.evaluate_compare(ind["id"], ind["year"], a["key"], b["key"], choice)
        if base is None:
            return None
        # `winner` torna sempre come "a" o "b": `quiz` lo chiama region_a e
        # region_b, qui la coppia è una coppia e basta.
        return {
            "correct": base["correct"],
            "choice": base["choice"],
            "winner": "a" if base["winner"] == "region_a" else "b",
            # L'unita' e' quella scelta per il gioco in config/game_indicators.csv,
            # non quella abbreviata della scheda: la stessa che sta accanto al
            # valore nella stessa partita.
            "indicator": {**base["indicator"], "unit": ind["unit"], "year": ind["year"]},
            "a": {**a, "value": base["region_a"]["value"], "path": _territory_path(level, a["key"])},
            "b": {**b, "value": base["region_b"]["value"], "path": _territory_path(level, b["key"])},
        }
    year, values = _province_values(ind["id"], [a["key"], b["key"]])
    if year is None or year != ind["year"]:
        return None
    value_a, value_b = values[a["key"]], values[b["key"]]
    if value_a == value_b:
        return None
    indicator = _province_indicator(ind["id"], year, ind["name"], ind["unit"])
    if indicator is None:
        return None
    winner = "a" if value_a > value_b else "b"
    return {
        "correct": side == winner,
        "choice": choice,
        "winner": winner,
        "indicator": indicator,
        "a": {**a, "value": value_a, "path": _territory_path(level, a["key"])},
        "b": {**b, "value": value_b, "path": _territory_path(level, b["key"])},
    }


# L'apertura della sessione

def open_session(level, timer, now=None):
    """Il token, il livello e le dieci domande SENZA valori. None se il livello
    non esiste (chi chiama risponde 400).

    La sessione è nuova a ogni apertura e non si riprende da un token: la sfida
    del giorno è una partita di dieci domande, e riprenderla a metà richiederebbe
    di sapere quali domande ha già risposto il client, cosa che il token non
    registra. Il livello e il timer viaggiano dentro il token firmato, quindi da
    qui in poi il client non li sceglie più.
    """
    if level not in LEVELS:
        return None
    day = today_rome(now)
    challenge = _challenge(day, level)
    state = quiz_tokens.load_state(None, MODE, timer)
    pair = challenge["pairs"][0]
    questions = [_question(c, i, level) for i, c in enumerate(challenge["pairs"])]
    token = quiz_tokens.bind_round(
        state, pair["indicator"]["id"], pair["indicator"]["year"],
        [pair["a"]["key"], pair["b"]["key"]], level,
    )
    return {
        "puzzle_id": today_challenge_id(day),
        "number": game_daily.challenge_number(day),
        "date": day.isoformat(),
        "next_puzzle_at": game_daily.next_challenge_rome(day),
        "level": level,
        "level_label": level_label(level),
        "difficulty": challenge["difficulty"],
        "region": challenge["region"],
        "timer": bool(state["t"]),
        # Senza timer è allenamento e non va in classifica: il client lo dice e
        # non offre l'invio.
        "leaderboard": bool(state["t"]),
        "total": PAIRS,
        "questions": questions,
        "token": token,
    }


def sid_from_token(token):
    """Il `sid` della sessione, per il limite di frequenza: un token assente o
    rotto apre una sessione nuova, come fa `load_state` nell'altra rotta."""
    return quiz_tokens.load_state(token, MODE)["sid"]


def _score(state):
    """(giorno, risposte giuste) letti dal token firmato. Un token di un altro
    giorno riparte da zero."""
    saved = state.get(SCORE_KEY) or {}
    return saved.get("d"), int(saved.get("c") or 0)


def _bind_question(state, pair, level):
    return quiz_tokens.bind_round(
        state, pair["indicator"]["id"], pair["indicator"]["year"],
        [pair["a"]["key"], pair["b"]["key"]], level,
    )


# La domanda successiva

def next_question(data, now=None):
    """(status, corpo) di "Avanti": lega al token la domanda dopo quella appena
    risposta. `q` e' l'INDICE della domanda appena risposta (0-based): il server lega
    la `q + 1`, e il suo tempo parte da adesso, non da quando il giocatore ha risposto
    alla precedente. Prima la risposta legava la domanda dopo subito, e chi leggeva la
    rivelazione piu' di due secondi perdeva la partita per `late`.

    Il corpo e' `{"token": ...}`. Il token deve essere quello tornato dalla risposta a
    `q` (round non aperto, domanda `q` risposta): un token ancora legato a un round non
    si rilega, cosi' non si salta una domanda, e "Avanti" vale una volta sola per
    domanda (`claim_round` con `q` negativo, distinto dai round risposti), cosi' non
    si azzera l'orologio chiedendolo di nuovo. Errori: `puzzle_changed`,
    `token_invalid`, `bad_request`, e 409 `round_already_bound` per il secondo invio.
    La risposta all'ultima domanda non ha un "dopo".
    """
    state = quiz_tokens.load_state(data.get("token"), MODE)
    day = today_rome(now)
    if data.get("puzzle_id") != today_challenge_id(day):
        return 400, {"error": "puzzle_changed"}
    try:
        index = int(data.get("q"))
    except (TypeError, ValueError):
        return 400, {"error": "bad_request"}
    if not 0 <= index < PAIRS - 1:
        return 400, {"error": "bad_request"}
    saved = state.get(SCORE_KEY) or {}
    level = saved.get("l")
    if (level not in LEVELS or saved.get("d") != day.isoformat()
            or state.get("fp") is not None or state.get("q") != index + 1):
        return 400, {"error": "token_invalid"}
    if not quiz_tokens.claim_round(state["sid"], -(index + 1)):
        return 409, {"error": "round_already_bound"}
    pair = _challenge(day, level)["pairs"][index + 1]
    return 200, {"token": _bind_question(state, pair, level)}


# La risposta

def answer(data, now=None):
    """(status, corpo) della risposta a una domanda della sfida del giorno.

    Gli errori hanno tutti un nome che il client conosce: `puzzle_changed` (fra
    l'apertura e la risposta è cambiato il giorno), `token_invalid` (il token non
    lega questa domanda di questa sfida), `timeout_too_early` (il tempo lo misura
    il server), `round_already_answered` con 409 (un doppio invio, che il client
    ignora in silenzio). Una risposta tardiva non è un errore: vale come un tempo
    scaduto e porta `late: true`. `training_session` non è un errore: è l'avviso
    che senza timer la partita non va in classifica.
    """
    state = quiz_tokens.load_state(data.get("token"), MODE)
    day = today_rome(now)
    if data.get("puzzle_id") != today_challenge_id(day):
        return 400, {"error": "puzzle_changed"}
    level = state.get("x")
    if level not in LEVELS:
        return 400, {"error": "token_invalid"}
    try:
        index = int(data.get("q"))
    except (TypeError, ValueError):
        return 400, {"error": "bad_request"}
    if not 0 <= index < PAIRS:
        return 400, {"error": "bad_request"}
    pair = _challenge(day, level)["pairs"][index]
    choice = data.get("choice")
    outcome = _evaluate(pair, level, choice)
    if outcome is None:
        return 400, {"error": "bad_request"}
    keys = [pair["a"]["key"], pair["b"]["key"]]
    indicator = pair["indicator"]
    # Il token deve legare proprio questa domanda: senza questo controllo un
    # token buono potrebbe essere usato per far valutare una coppia diversa.
    bound, _ = quiz_tokens.apply_answer(
        state, indicator["id"], indicator["year"], keys, outcome["correct"]
    )
    if bound is None or state.get("q") != index + 1:
        return 400, {"error": "token_invalid"}
    timing = quiz_tokens.round_timing(state, choice, now)
    if timing == "early_timeout":
        return 400, {"error": "timeout_too_early"}
    if timing == "late":
        # Oltre i 10 s più la tolleranza la scelta non vale: la risposta è un tempo
        # scaduto, con la stessa rivelazione e niente di più, e il round si chiude.
        choice = "timeout"
        outcome = _evaluate(pair, level, choice)
    if not quiz_tokens.claim_round(state["sid"], state["q"]):
        return 409, {"error": "round_already_answered"}
    token_day, correct_count = _score(state)
    if token_day != day.isoformat():
        correct_count = 0
    if outcome["correct"]:
        correct_count += 1
    # La prima coppia sbagliata resta nel token, per il fatto di fine partita.
    first_error = game_facts.signed_error(
        state.get(SCORE_KEY) or {}, day.isoformat(), index, outcome, choice
    )
    state = {**state, SCORE_KEY: {"d": day.isoformat(), "c": correct_count, "l": level, **first_error}}
    session, token = quiz_tokens.apply_answer(
        state, indicator["id"], indicator["year"], keys, outcome["correct"]
    )
    summary = None if session is None else {
        "streak": session["streak"], "best": session["best"], "rounds": session["rounds"],
    }
    finished = index + 1 == PAIRS
    body = {
        **outcome,
        "index": index,
        "level": level,
        # La forma del risultato per la riga da condividere: mai il nome del
        # territorio né il valore.
        "esito": "exact" if outcome["correct"] else "miss",
        "score": {"correct": correct_count, "total": PAIRS},
        "session": summary,
        "leaderboard": bool(state["t"]),
        "finished": finished,
        "token": token,
    }
    if timing == "late":
        body["late"] = True
    if not state["t"]:
        body["notice"] = "training_session"
    if finished:
        body["summary"] = {
            "puzzle_id": today_challenge_id(day),
            "number": game_daily.challenge_number(day),
            "date": day.isoformat(),
            "next_puzzle_at": game_daily.next_challenge_rome(day),
            "score": {"correct": correct_count, "total": PAIRS},
        }
        fact = game_facts.compare_fact(
            level, _challenge(day, level)["pairs"], state[SCORE_KEY].get("e"),
            lambda pair, choice: _evaluate(pair, level, choice),
        )
        if fact:
            body["summary"]["fact"] = fact["fact"]
            if fact["path"]:
                body["summary"]["fact_path"] = fact["path"]
    return 200, body