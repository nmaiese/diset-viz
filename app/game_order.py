"""Backend della sfida del giorno per "Ordina le regioni": sessioni e
valutazione delle risposte server-side senza spoiler."""

from flask import abort

from app import bes_data, game_daily, player_stats, profiles, quiz, quiz_tokens, sources


def daily_order_session(level="regioni", token=None, timer=True):
    """Payload per l'avvio o il ripristino di una sessione della sfida del giorno."""
    if level not in game_daily.LIVELLI:
        abort(400)
    payload = game_daily.sfida_payload("order", level)
    state = quiz_tokens.load_state(token, "order", timer)
    payload["timer"] = bool(state["t"])
    keys = [t["key"] for t in payload["territories"]]
    payload["token"] = quiz_tokens.bind_round(
        state, payload["indicator"]["id"], payload["indicator"]["year"], keys, len(keys), count=len(keys)
    )
    return payload


def evaluate_daily_order_answer(payload, auth_user=None, request_obj=None):
    """Valuta la risposta proposta per la sfida del giorno di OGGI."""
    if not isinstance(payload, dict):
        return {"error": "bad_request"}, 400

    token = payload.get("token")
    state = quiz_tokens.load_state(token, "order")

    level = payload.get("level") or "regioni"
    if level not in game_daily.LIVELLI:
        return {"error": "bad_request"}, 400

    region_keys = payload.get("region_keys") or payload.get("territory_keys") or payload.get("keys")
    if not isinstance(region_keys, list) or len(region_keys) != game_daily.ORDER_TERRITORI:
        return {"error": "bad_request"}, 400

    today = game_daily.oggi_roma()
    daily_puzzle = game_daily.order_del_giorno(today, level)
    ind = daily_puzzle["indicator"]
    ind_id = ind["id"]
    year = ind["year"]

    # Si ordina proprio la sfida di oggi: i cinque territori, ciascuno una volta.
    if sorted(region_keys) != sorted(t["key"] for t in daily_puzzle["territories"]):
        return {"error": "bad_request"}, 400

    result = None
    if level == "regioni":
        result = quiz.evaluate_order(ind_id, year, region_keys)
        if result is None:
            return {"error": "bad_request"}, 400

    if result is None:
        ambito = "province"
        righe_data = game_daily._righe_indicatore(ind, ambito)
        if not righe_data:
            return {"error": "bad_request"}, 400
        _, all_rows = righe_data
        val_map = {r["key"]: r["value"] for r in all_rows}
        name_map = {r["key"]: r["name"] for r in all_rows}

        if not all(k in val_map for k in region_keys):
            return {"error": "bad_request"}, 400

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
        slug = profiles.indicator_slug(ind["name"])
        canonical_path = sources.indicator_url("bes", raw_id, slug) + "/province"
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

    late = False
    if state.get("t"):
        timing = quiz_tokens.round_timing(state, None)
        if timing == "early_timeout":
            return {"error": "timeout_too_early"}, 400
        late = (timing == "late")

    is_perfect = (result["score"] == result["total"]) and not late

    session_keys = [t["key"] for t in daily_puzzle["territories"]]
    session, token_out = quiz_tokens.apply_answer(state, ind_id, year, session_keys, is_perfect)

    if session is not None and not quiz_tokens.claim_round(state["sid"], state["q"]):
        return {"error": "round_conflict"}, 409

    if late:
        result["correct"] = False
        result["late"] = True

    from app.views import _session_summary, _record_quiz
    result["session"] = _session_summary(session)
    result["token"] = token_out
    if request_obj:
        result["achievements"] = _record_quiz(request_obj, "order", is_perfect, result["session"])

    if auth_user:
        date_str = today.isoformat()
        player_stats.record_daily_score(auth_user["id"], "order", date_str, result["score"])

    return result, 200
