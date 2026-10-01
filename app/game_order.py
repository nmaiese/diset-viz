"""Backend della sfida del giorno per "Ordina le regioni": sessioni e
valutazione delle risposte server-side senza spoiler.

**Il round lo lega il token.** La sessione apre con un token di modalita'
`order_daily` (mai quella dei round a serie, vedi `quiz_tokens.peek_state`) che
porta il livello nel campo `x`, firmato e coperto dall'impronta del round: il
livello non si legge dal corpo della risposta. Senza un round legato (token
assente, di un'altra modalita', scaduto, gia' risposto) la risposta e' un 400
`token_invalid` senza valori ne' ordine giusto.

**Niente timer.** Il client di Ordina non ha un tempo per round, quindi la sessione
apre sempre con `t` falso: nessun controllo del tempo e nessuna risposta `late`.

**Il punteggio.** `record_daily_score` gira solo con il round legato, PRIMA che la
vista valuti i traguardi: "Giro d'Italia" e "Fedele" devono vedere il punteggio di
oggi. Senza il DB (migrazione 0010 mancante) la risposta resta valida e l'errore
va nel log.
"""

import logging

from app import bes_data, game_daily, player_stats, quiz, quiz_tokens, sources

log = logging.getLogger(__name__)

MODO = "order_daily"


class ErroreOrdina(Exception):
    """Un errore del dominio con il nome che il client conosce e lo status HTTP:
    la vista lo traduce in una risposta JSON."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


def daily_order_session(level="regioni"):
    """Payload per l'apertura di una sessione della sfida del giorno. La sessione e'
    sempre nuova: riprendere un token precedente rilegherebbe lo stesso puzzle e farebbe
    crescere una serie che non esiste."""
    if level not in game_daily.LIVELLI:
        raise ErroreOrdina("bad_request")
    payload = game_daily.sfida_payload("order", level)
    state = quiz_tokens.load_state(None, MODO, timer=False)
    payload["timer"] = False
    keys = [t["key"] for t in payload["territories"]]
    payload["token"] = quiz_tokens.bind_round(
        state, payload["indicator"]["id"], payload["indicator"]["year"], keys, level, count=len(keys)
    )
    return payload


def evaluate_daily_order_answer(payload, auth_user=None):
    """Valuta la risposta proposta per la sfida del giorno di OGGI. Ritorna il
    risultato, o solleva `ErroreOrdina`."""
    if not isinstance(payload, dict):
        raise ErroreOrdina("bad_request")

    state = quiz_tokens.load_state(payload.get("token"), MODO)
    level = state.get("x")
    if state.get("fp") is None or level not in game_daily.LIVELLI:
        raise ErroreOrdina("token_invalid")

    region_keys = payload.get("region_keys")
    if not isinstance(region_keys, list) or len(region_keys) != game_daily.ORDER_TERRITORI:
        raise ErroreOrdina("bad_request")

    today = game_daily.oggi_roma()
    daily_puzzle = game_daily.order_del_giorno(today, level)
    ind = daily_puzzle["indicator"]
    ind_id = ind["id"]
    year = ind["year"]

    # Si ordina proprio la sfida di oggi: i cinque territori, ciascuno una volta.
    session_keys = [t["key"] for t in daily_puzzle["territories"]]
    if sorted(region_keys) != sorted(session_keys):
        raise ErroreOrdina("bad_request")

    # Il round deve essere legato proprio a questa sfida: prima di ogni valore.
    if quiz_tokens.apply_answer(state, ind_id, year, session_keys, False)[0] is None:
        raise ErroreOrdina("token_invalid")

    result = None
    if level == "regioni":
        result = quiz.evaluate_order(ind_id, year, region_keys)
        if result is None:
            raise ErroreOrdina("bad_request")

    if result is None:
        ambito = "province"
        righe_data = game_daily._righe_indicatore(ind, ambito)
        if not righe_data:
            raise ErroreOrdina("bad_request")
        _, all_rows = righe_data
        val_map = {r["key"]: r["value"] for r in all_rows}
        name_map = {r["key"]: r["name"] for r in all_rows}

        if not all(k in val_map for k in region_keys):
            raise ErroreOrdina("bad_request")

        correct_keys = sorted(region_keys, key=lambda k: val_map[k], reverse=True)
        correct_position = {k: idx + 1 for idx, k in enumerate(correct_keys)}

        positions = []
        score = 0
        for idx, key in enumerate(region_keys):
            guessed = idx + 1
            right = correct_position[key]
            hit = (guessed == right)
            if hit:
                score += 1
            positions.append({
                "region": name_map[key],
                "region_key": key,
                "value": val_map[key],
                "guessed_position": guessed,
                "correct_position": right,
                "correct": hit,
            })

        correct_order = [
            {"region": name_map[k], "region_key": k, "value": val_map[k]}
            for k in correct_keys
        ]

        raw_id = game_daily.id_provinciale(ind_id)
        manifest = bes_data.get_bes_manifest("provincia").get(raw_id) or {}
        explain = manifest.get("explain") or {}
        desc = explain.get("plain") or ind["name"]
        canonical_path = province_path(ind_id)
        val_expl = explain.get("example") or ""
        source_lbl = sources.SOURCES["bes"]["label"]
        source_u = bes_data.BES_SOURCE_URLS["provincia"]

        result = {
            "score": score,
            "total": len(region_keys),
            "positions": positions,
            "correct_order": correct_order,
            "indicator": {
                "id": ind_id,
                "name": ind["name"],
                "unit": ind["unit"],
                "year": year,
                "source_label": source_lbl,
                "source_url": source_u,
                "description": desc,
                "value_explanation": val_expl,
                "path": canonical_path,
            },
        }

    result = _righe_con_unita(result)

    is_perfect = result["score"] == result["total"]
    session, token_out = quiz_tokens.apply_answer(state, ind_id, year, session_keys, is_perfect)
    if not quiz_tokens.claim_round(state["sid"], state["q"]):
        raise ErroreOrdina("round_conflict", 409)

    result["session"] = quiz_tokens.session_summary(session)
    result["token"] = token_out
    if auth_user:
        try:
            player_stats.record_daily_score(auth_user["id"], "order", today.isoformat(), result["score"])
        except Exception:  # noqa: BLE001
            log.exception("ordina: punteggio del giorno non registrato")
    return result


def _righe_con_unita(result):
    """L'unita' accanto a ogni valore, dentro `positions` e `correct_order`.

    Il client scrive "74,3%" e non "74,3 Valori percentuali": senza l'unita' per
    riga doveva indovinarla, e per un indicatore senza valore (o con l'etichetta
    della fonte al posto dell'unita') finiva per stampare un numero nudo o un
    "n.d.". Si aggiunge un campo, non se ne toglie nessuno. Vale per entrambe le
    diramazioni (regioni e province), perche' la prova guarda il payload."""
    unit = (result.get("indicator") or {}).get("unit") or ""
    if not unit:
        return result
    for chiave in ("positions", "correct_order"):
        righe = result.get(chiave)
        if isinstance(righe, list):
            result[chiave] = [{**riga, "unit": unit} for riga in righe]
    return result


def province_path(ind_id):
    """Il link canonico della scheda a livello province, quello di `game_provincia`:
    uno slug composto dal nome leggibile del gioco porta a un 301."""
    return bes_data.bes_level_path(game_daily.id_provinciale(ind_id), "provincia")


def sid_del_token(token):
    """Il `sid` della sessione, per il limite di frequenza: un token assente o rotto
    apre una sessione nuova, come fa `load_state` nelle altre rotte."""
    return quiz_tokens.load_state(token, MODO)["sid"]
