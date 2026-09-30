"""La sfida del giorno di "Chi è maggiore?": dieci coppie, stesse per tutti.

Qui c'è la logica del giornale, tutto il resto è in `app/game_daily.py` (che
sceglie le coppie di oggi) e in `app/quiz.py` (che sa giudicare un confronto fra
regioni). Il modulo non tocca nessuno dei due e non li duplica.

**Il giorno lo sceglie il server.** Ogni richiesta ricostruisce la sfida di
oggi a Roma con `game_daily.compare_del_giorno`: il client manda solo
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
vale) o troppo tardi (oltre i 10 s più 2 di tolleranza è un errore, e la
risposta viene rifiutata senza rivelare nulla).

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
i dati sono quelli provinciali (`game_daily._righe_indicatore`, la stessa
funzione privata da cui la sfida è stata composta: rileggere i dati con un
secondo percorso li farebbe divergere) e il vincitore si calcola qui, perché
`quiz.evaluate_compare` confronta regioni. Lo stesso indicatore può esistere a
entrambi i livelli: al livello provincia la risposta deve usare il dato
provinciale, non quello regionale.
"""

from __future__ import annotations

from functools import lru_cache

from app import bes_data, game_daily, quiz, quiz_tokens, sources
from app.game_daily import LIVELLI, oggi_roma

MODO = "compare"
COPPIE = game_daily.COMPARE_COPPIE
# Etichetta della fonte per i livelli con le province, che non passano da
# quiz.evaluate_compare: viene da app/sources.py, l'unica fonte di verita' dei
# nomi (un'etichetta scritta qui ha gia' pubblicato una serie sotto un altro nome).
FONTE_PROVINCE = sources.SOURCES["bes"]["label"]
# La scheda del territorio: la stessa forma degli altri giochi (`/regione/<key>`
# e `/provincia/<key>`).
PERCORSI = {"regioni": "/regione/", "stessa_regione": "/provincia/", "province": "/provincia/"}
# Campo del token con la data della sfida e le risposte giuste. Firmato come
# tutto il resto del token.
CHIAVE_PUNTEGGIO = "sfida"

ETICHETTE_LIVELLO = {
    "regioni": "Regioni",
    "stessa_regione": "Province della stessa regione",
    "province": "Province",
}


def sfida_di_oggi_id(giorno):
    return f"daily:{giorno.isoformat()}"


def etichetta_livello(livello):
    return ETICHETTE_LIVELLO.get(livello, ETICHETTE_LIVELLO["regioni"])


@lru_cache(maxsize=6)
def _sfida(giorno, livello):
    """La sfida del giorno a un livello, in cache per po' giorni e livelli: le
    coppie sono deterministiche sul seed, quindi ricalcolarle non cambia nulla e
    ogni richiesta rileggerebbe gli elenchi degli indicatori."""
    return game_daily.compare_del_giorno(giorno, livello)


def _percorso_territorio(livello, chiave):
    return PERCORSI.get(livello, PERCORSI["regioni"]) + chiave


def _domanda(coppia, indice, livello):
    """La domanda `indice` senza valori e senza soluzione: quello che il client
    vede prima di rispondere."""
    return {
        "index": indice,
        "indicator": dict(coppia["indicator"]),
        "a": {**coppia["a"], "path": _percorso_territorio(livello, coppia["a"]["key"])},
        "b": {**coppia["b"], "path": _percorso_territorio(livello, coppia["b"]["key"])},
    }


def _indicatore_provinciale(ind_id, anno, nome, unita):
    """I campi dell'indicatore per una risposta ai livelli con le province: nome
    leggibile e unità sono quelli scelti per il gioco in
    `config/game_indicators.csv`, la spiegazione e il link canonico vengono dal
    catalogo BES, l'unica fonte che li ha per gli indicatori solo provinciali."""
    raw = game_daily.id_provinciale(ind_id)
    info = bes_data.get_bes_manifest("provincia").get(raw)
    if info is None:
        return None
    try:
        percorso = bes_data.bes_path(raw)
    except LookupError:
        percorso = None
    return {
        "id": ind_id,
        "name": nome,
        "unit": unita,
        "year": anno,
        "description": info["explain"]["plain"],
        "value_explanation": info["explain"]["example"],
        "path": percorso,
        "source_label": FONTE_PROVINCE,
        "source_url": bes_data.BES_SOURCE_URLS["provincia"],
    }


def _valori_provinciali(ind_id, chiavi):
    """(anno, {chiave: valore}) per un indicatore provinciale, letti dalla stessa
    funzione che ha composto la sfida."""
    dato = game_daily._righe_indicatore({"id": ind_id}, "province")
    if dato is None:
        return None, None
    anno, righe = dato
    valori = {riga["key"]: riga["value"] for riga in righe}
    if any(valori.get(chiave) is None for chiave in chiavi):
        return None, None
    return anno, valori


def _lato(scelta):
    """Il lato della coppia da una scelta del client ("region_a", "region_b" o
    "timeout"), None per il tempo scaduto. I nomi sono quelli del round a serie,
    così il client non deve imparare due vocabulari."""
    if scelta == "region_a":
        return "a"
    if scelta == "region_b":
        return "b"
    return None


def _valuta(coppia, livello, scelta):
    """Il risultato di una risposta, o None se l'input non è valido (chi chiama
    risponde 400). I valori sono quelli veri, la risposta porta l'indicatore con
    `path` e `description` e i due territori con la loro scheda: è tutto quello
    che la fine partita deve mostrare. `winner` è "a" o "b"."""
    if scelta not in quiz.COMPARE_CHOICES:
        return None
    lato = _lato(scelta)
    ind = coppia["indicator"]
    a, b = coppia["a"], coppia["b"]
    if livello == "regioni":
        base = quiz.evaluate_compare(ind["id"], ind["year"], a["key"], b["key"], scelta)
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
            "a": {**a, "value": base["region_a"]["value"], "path": _percorso_territorio(livello, a["key"])},
            "b": {**b, "value": base["region_b"]["value"], "path": _percorso_territorio(livello, b["key"])},
        }
    anno, valori = _valori_provinciali(ind["id"], [a["key"], b["key"]])
    if anno is None or anno != ind["year"]:
        return None
    valore_a, valore_b = valori[a["key"]], valori[b["key"]]
    if valore_a == valore_b:
        return None
    indicatore = _indicatore_provinciale(ind["id"], anno, ind["name"], ind["unit"])
    if indicatore is None:
        return None
    vincitore = "a" if valore_a > valore_b else "b"
    return {
        "correct": lato == vincitore,
        "choice": scelta,
        "winner": vincitore,
        "indicator": indicatore,
        "a": {**a, "value": valore_a, "path": _percorso_territorio(livello, a["key"])},
        "b": {**b, "value": valore_b, "path": _percorso_territorio(livello, b["key"])},
    }


# L'apertura della sessione

def apri_sessione(livello, timer, now=None):
    """Il token, il livello e le dieci domande SENZA valori. None se il livello
    non esiste (chi chiama risponde 400).

    La sessione è nuova a ogni apertura e non si riprende da un token: la sfida
    del giorno è una partita di dieci domande, e riprenderla a metà richiederebbe
    di sapere quali domande ha già risposto il client, cosa che il token non
    registra. Il livello e il timer viaggiano dentro il token firmato, quindi da
    qui in poi il client non li sceglie più.
    """
    if livello not in LIVELLI:
        return None
    giorno = oggi_roma(now)
    sfida = _sfida(giorno, livello)
    stato = quiz_tokens.load_state(None, MODO, timer)
    coppia = sfida["pairs"][0]
    domande = [_domanda(c, i, livello) for i, c in enumerate(sfida["pairs"])]
    token = quiz_tokens.bind_round(
        stato, coppia["indicator"]["id"], coppia["indicator"]["year"],
        [coppia["a"]["key"], coppia["b"]["key"]], livello,
    )
    return {
        "puzzle_id": sfida_di_oggi_id(giorno),
        "number": game_daily.numero_sfida(giorno),
        "date": giorno.isoformat(),
        "next_puzzle_at": game_daily.prossima_sfida_roma(giorno),
        "level": livello,
        "level_label": etichetta_livello(livello),
        "difficulty": sfida["difficulty"],
        "region": sfida["region"],
        "timer": bool(stato["t"]),
        # Senza timer è allenamento e non va in classifica: il client lo dice e
        # non offre l'invio.
        "leaderboard": bool(stato["t"]),
        "total": COPPIE,
        "questions": domande,
        "token": token,
    }


def sid_del_token(token):
    """Il `sid` della sessione, per il limite di frequenza: un token assente o
    rotto apre una sessione nuova, come fa `load_state` nell'altra rotta."""
    return quiz_tokens.load_state(token, MODO)["sid"]


def _punteggio(stato):
    """(giorno, risposte giuste) letti dal token firmato. Un token di un altro
    giorno riparte da zero."""
    salvato = stato.get(CHIAVE_PUNTEGGIO) or {}
    return salvato.get("d"), int(salvato.get("c") or 0)


# La risposta

def risposta(dati, now=None):
    """(status, corpo) della risposta a una domanda della sfida del giorno.

    Gli errori hanno tutti un nome che il client conosce: `puzzle_changed` (fra
    l'apertura e la risposta è cambiato il giorno), `token_invalid` (il token non
    lega questa domanda di questa sfida), `late` e `timeout_too_early` (il tempo
    lo misura il server), `round_already_answered` con 409 (un doppio invio, che
    il client ignora in silenzio). `training_session` non è un errore: è l'avviso
    che senza timer la partita non va in classifica.
    """
    stato = quiz_tokens.load_state(dati.get("token"), MODO)
    giorno = oggi_roma(now)
    if dati.get("puzzle_id") != sfida_di_oggi_id(giorno):
        return 400, {"error": "puzzle_changed"}
    livello = stato.get("x")
    if livello not in LIVELLI:
        return 400, {"error": "token_invalid"}
    try:
        indice = int(dati.get("q"))
    except (TypeError, ValueError):
        return 400, {"error": "bad_request"}
    if not 0 <= indice < COPPIE:
        return 400, {"error": "bad_request"}
    coppia = _sfida(giorno, livello)["pairs"][indice]
    esito = _valuta(coppia, livello, dati.get("choice"))
    if esito is None:
        return 400, {"error": "bad_request"}
    chiavi = [coppia["a"]["key"], coppia["b"]["key"]]
    indicatore = coppia["indicator"]
    # Il token deve legare proprio questa domanda: senza questo controllo un
    # token buono potrebbe essere usato per far valutare una coppia diversa.
    legato, _ = quiz_tokens.apply_answer(
        stato, indicatore["id"], indicatore["year"], chiavi, esito["correct"]
    )
    if legato is None or stato.get("q") != indice + 1:
        return 400, {"error": "token_invalid"}
    tempo = quiz_tokens.round_timing(stato, dati.get("choice"), now)
    if tempo == "early_timeout":
        return 400, {"error": "timeout_too_early"}
    if tempo == "late":
        # oltre i 10 s più la tolleranza non è una risposta: si rifiuta senza
        # rivelare i valori, e il round resta aperto solo per il tempo che manca.
        return 400, {"error": "late"}
    if not quiz_tokens.claim_round(stato["sid"], stato["q"]):
        return 409, {"error": "round_already_answered"}
    giorno_token, giuste = _punteggio(stato)
    if giorno_token != giorno.isoformat():
        giuste = 0
    if esito["correct"]:
        giuste += 1
    stato = {**stato, CHIAVE_PUNTEGGIO: {"d": giorno.isoformat(), "c": giuste}}
    sessione, token = quiz_tokens.apply_answer(
        stato, indicatore["id"], indicatore["year"], chiavi, esito["correct"]
    )
    riassunto = None if sessione is None else {
        "streak": sessione["streak"], "best": sessione["best"], "rounds": sessione["rounds"],
    }
    finita = indice + 1 == COPPIE
    if not finita:
        # La risposta lega al token la domanda dopo, come nel round a serie il
        # token torna legato al round che viene: il client non sceglie la
        # coppia, la riceve già bindsata.
        coppia = _sfida(giorno, livello)["pairs"][indice + 1]
        token = quiz_tokens.bind_round(
            quiz_tokens.load_state(token, MODO), coppia["indicator"]["id"],
            coppia["indicator"]["year"], [coppia["a"]["key"], coppia["b"]["key"]], livello,
        )
    corpo = {
        **esito,
        "index": indice,
        "level": livello,
        # La forma del risultato per la riga da condividere: mai il nome del
        # territorio né il valore.
        "esito": "exact" if esito["correct"] else "miss",
        "score": {"correct": giuste, "total": COPPIE},
        "session": riassunto,
        "leaderboard": bool(stato["t"]),
        "finished": finita,
        "token": token,
    }
    if not stato["t"]:
        corpo["notice"] = "training_session"
    if finita:
        corpo["summary"] = {
            "puzzle_id": sfida_di_oggi_id(giorno),
            "number": game_daily.numero_sfida(giorno),
            "date": giorno.isoformat(),
            "next_puzzle_at": game_daily.prossima_sfida_roma(giorno),
            "score": {"correct": giuste, "total": COPPIE},
        }
    return 200, corpo