"""La sfida del giorno di "Chi è maggiore?": stessa per tutti, senza soluzioni
nel payload, valutata sui valori veri, con round monouso, tempo misurato dal
server e allenamento fuori classifica.

Ogni test qui sotto fallisce sul ramo di prima (il modulo `app/game_compare.py` e
le due rotte `/api/game/compare/daily/*` non ci sono ancora)."""

import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from app import app, config, game_compare, game_daily, quiz, quiz_tokens, sources
from app.cache import cache

T0 = 1_800_000_000.0
# La mezzanotte di Roma del 30 settembre 2026 cade alle 22:00 UTC (estate):
# un secondo prima è ancora il 30 settembre a Roma, dopo è l'1 ottobre. Le
# 23:30 UTC dello stesso giorno, l'ora che la sfida fissa come orologio, sono
# già l'1 ottobre a Roma.
MEZZANOTTE_ROMA = datetime(2026, 9, 30, 22, 0, tzinfo=timezone.utc)
OROLOGIO_2330 = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
GIORNO_PRIMA = datetime(2026, 9, 30, 20, 30, tzinfo=timezone.utc)
GIORNO_30 = date(2026, 9, 30)


def _orologio(now):
    """Fissa l'orologio del server su un istante, per le rotte."""
    giorno = game_daily.today_rome(now)
    return mock.patch.object(game_compare, "today_rome", return_value=giorno)


def _valori_veri(livello, coppia):
    """(valore di a, valore di b) della coppia, letti dai dati."""
    indicatore = coppia["indicator"]
    if livello == "regioni":
        valori = {
            riga["region_key"]: riga["value"]
            for riga in quiz._quiz_indicator_payload(indicatore["id"], indicatore["year"])["values"]
        }
    else:
        _, righe = game_daily._indicator_rows({"id": indicatore["id"]}, "province")
        valori = {riga["key"]: riga["value"] for riga in righe}
    return valori[coppia["a"]["key"]], valori[coppia["b"]["key"]]


def _vincitore(livello, coppia):
    valore_a, valore_b = _valori_veri(livello, coppia)
    return "region_a" if valore_a > valore_b else "region_b"


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = "test-jwt-secret"
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "s.sqlite3")
        self._svuota_cache()
        self.client = app.test_client()

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)
        self._svuota_cache()

    @staticmethod
    def _svuota_cache():
        for chiave in ("rl:lb:127.0.0.1", "rl:ans:ip:127.0.0.1"):
            cache.delete(chiave)

    def _sessione(self, livello="regioni", timer=1, now=T0):
        richiesta = f"/api/game/compare/daily/session?level={livello}"
        if timer == 0:
            richiesta += "&timer=0"
        with mock.patch.object(quiz_tokens, "_now", return_value=now):
            return self.client.get(richiesta).get_json()

    def _risponde(self, sessione, indice, choice, token=None, now=None):
        with mock.patch.object(quiz_tokens, "_now", return_value=T0 if now is None else now):
            return self.client.post("/api/game/compare/daily/answer", json={
                "puzzle_id": sessione["puzzle_id"], "q": indice, "choice": choice,
                "token": token if token is not None else sessione["token"],
            })

    def _avanti(self, sessione, indice, token, now=None):
        """Il giocatore preme "Avanti" dopo aver risposto alla domanda `indice`."""
        with mock.patch.object(quiz_tokens, "_now", return_value=T0 if now is None else now):
            return self.client.post("/api/game/compare/daily/next", json={
                "puzzle_id": sessione["puzzle_id"], "q": indice, "token": token})

    def _gioca(self, sessione, livello, giuste=10):
        """Risponde a tutte e dieci le domande: le prime `giuste` con la risposta
        vera, le altre col tempo scaduto. L'orologio scorre di un secondo a ogni
        risposta e di undici quando la risposta è il tempo scaduto, che il server
        non accetta prima dei dieci secondi. Ritorna le risposte nell'ordine."""
        token = sessione["token"]
        orario = T0
        risposte = []
        for indice, coppia in enumerate(sessione["questions"]):
            if indice < giuste:
                choice = _vincitore(livello, coppia)
                orario += 1
            else:
                choice = "timeout"
                orario += 11
            risposta = self._risponde(sessione, indice, choice, token=token, now=orario)
            risposte.append(risposta)
            self.assertEqual(risposta.status_code, 200, indice)
            token = risposta.get_json()["token"]
            if indice < len(sessione["questions"]) - 1:
                avanti = self._avanti(sessione, indice, token, now=orario)
                self.assertEqual(avanti.status_code, 200, indice)
                token = avanti.get_json()["token"]
        return risposte


class SessioneTest(Base):
    def test_questions_carry_no_values_and_no_solution(self):
        for livello in game_daily.LEVELS:
            sessione = self._sessione(livello)
            self.assertEqual(len(sessione["questions"]), game_daily.COMPARE_PAIRS)
            testo = json.dumps(sessione)
            for rubrica in ("value", "winner", "correct", "description"):
                self.assertNotIn(rubrica, testo, f"{livello}: {rubrica} nelle domande")
            for domanda in sessione["questions"]:
                self.assertNotIn("value", domanda["a"])
                self.assertNotIn("value", domanda["b"])

    def test_unknown_level_is_refused(self):
        self.assertEqual(
            self.client.get("/api/game/compare/daily/session?level=mars").status_code, 400
        )

    def test_region_level_links_the_region_pages(self):
        sessione = self._sessione("regioni")
        for domanda in sessione["questions"]:
            self.assertEqual(domanda["a"]["path"], f"/regione/{domanda['a']['key']}")
            self.assertEqual(domanda["b"]["path"], f"/regione/{domanda['b']['key']}")

    def test_province_levels_link_the_province_pages(self):
        for livello in ("province", "stessa_regione"):
            sessione = self._sessione(livello)
            for domanda in sessione["questions"]:
                self.assertEqual(domanda["a"]["path"], f"/provincia/{domanda['a']['key']}")
                self.assertEqual(domanda["b"]["path"], f"/provincia/{domanda['b']['key']}")

    def test_province_level_shows_the_region_of_each_territory(self):
        regioni = {p["key"]: p["region"] for p in game_daily.province_pool()}
        for livello in ("province", "stessa_regione"):
            for domanda in self._sessione(livello)["questions"]:
                for lato in ("a", "b"):
                    self.assertEqual(domanda[lato]["region"], regioni[domanda[lato]["key"]])

    def test_same_region_level_only_uses_eligible_regions(self):
        idonee = set(game_daily.eligible_regions(game_daily.MIN_PROVINCES_COMPARE))
        for giorno in range(10):
            sfida = game_daily.daily_compare(GIORNO_30 + timedelta(days=giorno), "stessa_regione")
            self.assertIn(sfida["region"], idonee)
            for coppia in sfida["pairs"]:
                for lato in ("a", "b"):
                    self.assertEqual(coppia[lato]["region"], sfida["region"])


class StessoPerTuttiTest(Base):
    def _impronte(self, sessione):
        return [(d["indicator"]["id"], d["a"]["key"], d["b"]["key"]) for d in sessione["questions"]]

    def test_same_day_same_challenge_for_everyone(self):
        with _orologio(GIORNO_PRIMA):
            uno = self.client.get("/api/game/compare/daily/session").get_json()
        with _orologio(GIORNO_PRIMA + timedelta(hours=1)):
            due = self.client.get("/api/game/compare/daily/session").get_json()
        self.assertEqual(uno["puzzle_id"], "daily:2026-09-30")
        self.assertEqual(due["puzzle_id"], uno["puzzle_id"])
        self.assertEqual(self._impronte(due), self._impronte(uno))

    def test_challenge_changes_at_midnight_in_rome(self):
        # Le 21:59:59 UTC del 30 settembre sono le 23:59:59 a Roma, un secondo
        # dopo è già mezzanotte: sfida e numero cambiano insieme.
        with _orologio(MEZZANOTTE_ROMA - timedelta(seconds=1)):
            prima = self.client.get("/api/game/compare/daily/session").get_json()
        with _orologio(MEZZANOTTE_ROMA):
            dopo = self.client.get("/api/game/compare/daily/session").get_json()
        self.assertEqual(prima["date"], "2026-09-30")
        self.assertEqual(dopo["date"], "2026-10-01")
        self.assertNotEqual(dopo["puzzle_id"], prima["puzzle_id"])
        self.assertEqual(dopo["number"], prima["number"] + 1)
        self.assertNotEqual(self._impronte(dopo), self._impronte(prima))

    def test_with_the_clock_at_2330_utc_rome_is_already_tomorrow(self):
        # L'orologio fermo alle 23:30 UTC del 30 settembre: a Roma è già l'1
        # ottobre, quindi la sfida di oggi è quella dell'1 ottobre.
        with _orologio(OROLOGIO_2330):
            sessione = self.client.get("/api/game/compare/daily/session").get_json()
        self.assertEqual(sessione["date"], "2026-10-01")
        self.assertEqual(sessione["puzzle_id"], "daily:2026-10-01")

    def test_answer_to_yesterdays_challenge_is_refused(self):
        # La sessione si apre con l'orologio fissato sul 30 settembre: con la data vera
        # del computer, da mezzanotte di quel giorno in poi la sfida "di ieri" sarebbe
        # quella di oggi e il test non potrebbe piu' fallire come deve.
        with _orologio(GIORNO_PRIMA):
            sessione = self._sessione()
        with _orologio(MEZZANOTTE_ROMA):
            risposta = self.client.post("/api/game/compare/daily/answer", json={
                "puzzle_id": sessione["puzzle_id"], "q": 0, "choice": "region_a",
                "token": sessione["token"],
            })
        self.assertEqual(risposta.status_code, 400)
        self.assertEqual(risposta.get_json()["error"], "puzzle_changed")


class ValutazioneTest(Base):
    def test_the_real_values_decide_the_answer(self):
        coppia = self._sessione()["questions"][0]
        giusta = _vincitore("regioni", coppia)
        sbagliata = "region_b" if giusta == "region_a" else "region_a"
        # Due sessioni, perché la stessa coppia si risponde una volta sola.
        prima = self._risponde(self._sessione(), 0, giusta).get_json()
        seconda = self._risponde(self._sessione(), 0, sbagliata).get_json()
        self.assertTrue(prima["correct"])
        self.assertFalse(seconda["correct"])
        self.assertEqual(prima["score"], {"correct": 1, "total": 10})
        self.assertEqual(seconda["score"], {"correct": 0, "total": 10})
        self.assertEqual(prima["esito"], "exact")
        self.assertEqual(seconda["esito"], "miss")

    def test_timeout_counts_as_a_miss(self):
        corpo = self._risponde(self._sessione(), 0, "timeout", now=T0 + 10).get_json()
        self.assertFalse(corpo["correct"])
        self.assertEqual(corpo["esito"], "miss")
        self.assertEqual(corpo["choice"], "timeout")

    def test_the_answer_carries_the_real_values_with_unit_year_and_path(self):
        sessione = self._sessione()
        coppia = sessione["questions"][0]
        corpo = self._risponde(sessione, 0, _vincitore("regioni", coppia)).get_json()
        valore_a, valore_b = _valori_veri("regioni", coppia)
        self.assertEqual(corpo["a"]["value"], valore_a)
        self.assertEqual(corpo["b"]["value"], valore_b)
        self.assertEqual(corpo["winner"], "a" if valore_a > valore_b else "b")
        self.assertEqual(corpo["indicator"]["unit"], coppia["indicator"]["unit"])
        self.assertEqual(corpo["indicator"]["year"], coppia["indicator"]["year"])
        self.assertTrue(corpo["indicator"]["path"].startswith("/indicatore/"))
        self.assertTrue(corpo["indicator"]["description"])
        self.assertEqual(corpo["a"]["path"], coppia["a"]["path"])
        self.assertEqual(corpo["b"]["path"], coppia["b"]["path"])

    def test_province_level_is_judged_on_the_province_data(self):
        for livello in ("province", "stessa_regione"):
            sessione = self._sessione(livello)
            coppia = sessione["questions"][0]
            corpo = self._risponde(sessione, 0, _vincitore("province", coppia)).get_json()
            valore_a, valore_b = _valori_veri("province", coppia)
            self.assertEqual(corpo["a"]["value"], valore_a, livello)
            self.assertEqual(corpo["b"]["value"], valore_b, livello)
            self.assertTrue(corpo["correct"], livello)
            self.assertEqual(corpo["level"], livello)
            self.assertTrue(corpo["indicator"]["path"].startswith("/indicatore/"))
            self.assertTrue(corpo["indicator"]["description"])

    def test_a_livello_province_la_fonte_viene_da_sources(self):
        # L'etichetta di una fonte sta in un posto solo (app/sources.py).
        sessione = self._sessione("province")
        coppia = sessione["questions"][0]
        corpo = self._risponde(sessione, 0, _vincitore("province", coppia)).get_json()
        # L'indicatore della coppia puo' essere BES o di una famiglia esterna: si
        # confronta con l'etichetta della sua famiglia, non con quella BES.
        family, _ = game_daily.province_source(corpo["indicator"]["id"])
        self.assertEqual(corpo["indicator"]["source_label"], sources.family_label(family))

    def test_token_of_another_question_does_not_judge_this_one(self):
        sessione = self._sessione()
        prima = self._risponde(sessione, 0, "region_a").get_json()
        token = self._avanti(sessione, 0, prima["token"]).get_json()["token"]
        # Il token ora lega la seconda domanda: la nona non è un round aperto.
        risposta = self._risponde(sessione, 8, "region_a", token=token)
        self.assertEqual(risposta.status_code, 400)
        self.assertEqual(risposta.get_json()["error"], "token_invalid")

    def test_level_in_the_body_does_not_change_the_pair(self):
        sessione = self._sessione("regioni")
        coppia = sessione["questions"][0]
        with mock.patch.object(quiz_tokens, "_now", return_value=T0):
            risposta = self.client.post("/api/game/compare/daily/answer", json={
                "puzzle_id": sessione["puzzle_id"], "q": 0,
                "choice": _vincitore("regioni", coppia),
                "level": "province", "token": sessione["token"],
            })
        corpo = risposta.get_json()
        self.assertEqual(corpo["level"], "regioni")
        self.assertEqual(corpo["a"]["key"], coppia["a"]["key"])
        self.assertEqual(corpo["b"]["key"], coppia["b"]["key"])

    def test_unknown_answer_or_index_is_refused(self):
        sessione = self._sessione()
        self.assertEqual(self._risponde(sessione, 0, "entrambe").status_code, 400)
        self.assertEqual(self._risponde(sessione, 99, "region_a").status_code, 400)
        self.assertEqual(self._risponde(sessione, -1, "region_a").status_code, 400)


class MonousoTest(Base):
    def test_same_answer_twice_gives_409(self):
        sessione = self._sessione()
        self.assertEqual(self._risponde(sessione, 0, "region_a").status_code, 200)
        secondo = self._risponde(sessione, 0, "region_a")
        self.assertEqual(secondo.status_code, 409)
        self.assertEqual(secondo.get_json()["error"], "round_already_answered")

    def test_a_replay_does_not_move_the_score(self):
        sessione = self._sessione()
        coppia = sessione["questions"][0]
        prima = self._risponde(sessione, 0, _vincitore("regioni", coppia)).get_json()
        self.assertEqual(prima["score"], {"correct": 1, "total": 10})
        # Un doppio invio (un click e la scadenza insieme) è un 409 e non tocca
        # né il punteggio né il token.
        replay = self._risponde(sessione, 0, "region_b")
        self.assertEqual(replay.status_code, 409)
        # Il token di "Avanti" lega la domanda dopo, e il punteggio prosegue da
        # dove era: la seconda risposta è sbagliata, quindi resta a uno.
        token = self._avanti(sessione, 0, prima["token"]).get_json()["token"]
        seconda = self._risponde(sessione, 1, "timeout", token=token, now=T0 + 12)
        self.assertEqual(seconda.status_code, 200)
        self.assertEqual(seconda.get_json()["score"]["correct"], 1)

    def test_the_last_answer_does_not_bind_another_question(self):
        sessione = self._sessione()
        risposte = self._gioca(sessione, "regioni", giuste=10)
        ultima = risposte[-1].get_json()
        stato = quiz_tokens.load_state(ultima["token"], game_compare.MODE)
        self.assertIsNone(stato["fp"])
        # La decima coppia non si può rispondere una seconda volta.
        self.assertEqual(self._risponde(sessione, 9, "region_a", token=ultima["token"]).status_code, 400)

    def test_the_score_travels_in_the_signed_token(self):
        sessione = self._sessione()
        coppia = sessione["questions"][0]
        risposta = self._risponde(sessione, 0, _vincitore("regioni", coppia)).get_json()
        stato = quiz_tokens.load_state(risposta["token"], game_compare.MODE)
        # "l" e' il livello: dopo la risposta `x` si svuota e "Avanti" lo legge da qui.
        self.assertEqual(stato["sfida"], {"d": sessione["date"], "c": 1, "l": "regioni"})


class TempoTest(Base):
    def test_a_late_answer_is_a_miss_and_the_game_goes_on(self):
        """A1: oltre i 12 s la risposta conta come sbagliata (come un tempo scaduto) e
        il round si chiude, cosi' "Avanti" funziona. Prima era un 400 `late` senza
        claim: ogni nuovo invio era di nuovo `late` e la partita non finiva piu'."""
        sessione = self._sessione()
        giusta = _vincitore("regioni", sessione["questions"][0])
        risposta = self._risponde(sessione, 0, giusta, now=T0 + 13)
        self.assertEqual(risposta.status_code, 200)
        corpo = risposta.get_json()
        self.assertTrue(corpo["late"])
        self.assertFalse(corpo["correct"])
        self.assertEqual(corpo["choice"], "timeout")
        self.assertEqual(corpo["score"], {"correct": 0, "total": 10})
        self.assertEqual(corpo["session"]["streak"], 0)
        # un secondo invio della stessa domanda e' il doppio invio di sempre
        self.assertEqual(self._risponde(sessione, 0, giusta, now=T0 + 14).status_code, 409)
        # e la partita prosegue: "Avanti" lega la domanda dopo, che si risponde
        avanti = self._avanti(sessione, 0, corpo["token"], now=T0 + 14)
        self.assertEqual(avanti.status_code, 200)
        seconda = self._risponde(sessione, 1, _vincitore("regioni", sessione["questions"][1]),
                                 token=avanti.get_json()["token"], now=T0 + 16)
        self.assertEqual(seconda.status_code, 200)
        self.assertEqual(seconda.get_json()["score"], {"correct": 1, "total": 10})

    def test_a_late_answer_says_no_more_than_a_timeout(self):
        sessione = self._sessione()
        tardi = self._risponde(sessione, 0, "region_a", now=T0 + 13).get_json()
        altra = self._sessione()
        scaduta = self._risponde(altra, 0, "timeout", now=T0 + 11).get_json()
        self.assertEqual(set(tardi) - set(scaduta), {"late"})
        for campo in ("correct", "choice", "winner", "a", "b", "indicator", "esito", "score"):
            self.assertEqual(tardi[campo], scaduta[campo], campo)
        # una risposta giusta arrivata tardi non diventa l'errore del fatto di fine partita
        stato = quiz_tokens.load_state(tardi["token"], game_compare.MODE)
        self.assertNotIn("e", stato[game_compare.SCORE_KEY])

    def test_timeout_before_the_ten_seconds_does_not_count(self):
        sessione = self._sessione()
        risposta = self._risponde(sessione, 0, "timeout", now=T0 + 2)
        self.assertEqual(risposta.status_code, 400)
        self.assertEqual(risposta.get_json()["error"], "timeout_too_early")

    def test_answer_in_time_with_timer_is_accepted(self):
        sessione = self._sessione()
        corpo = self._risponde(sessione, 0, "region_a", now=T0 + 9).get_json()
        self.assertNotIn("error", corpo)
        self.assertTrue(corpo["leaderboard"])

    def test_without_timer_nothing_is_checked_and_the_run_is_training(self):
        sessione = self._sessione(timer=0)
        self.assertFalse(sessione["timer"])
        self.assertFalse(sessione["leaderboard"])
        coppia = sessione["questions"][0]
        corpo = self._risponde(
            sessione, 0, _vincitore("regioni", coppia), now=T0 + 600
        ).get_json()
        self.assertTrue(corpo["correct"])
        self.assertFalse(corpo["leaderboard"])
        self.assertEqual(corpo["notice"], "training_session")

    def test_untimed_daily_session_is_not_submittable_to_the_leaderboard(self):
        sessione = self._sessione(timer=0)
        coppia = sessione["questions"][0]
        risposta = self._risponde(
            sessione, 0, _vincitore("regioni", coppia), now=T0 + 20
        ).get_json()
        self.assertTrue(risposta["correct"])
        with mock.patch.object(quiz_tokens, "_now", return_value=T0 + 3600):
            invio = self.client.post(
                "/api/game/leaderboard",
                json={"token": risposta["token"], "nickname": "Allenamento"},
            )
        self.assertEqual(invio.status_code, 400)


class FinePartitaTest(Base):
    def test_last_answer_carries_the_score_and_the_next_challenge(self):
        sessione = self._sessione()
        risposte = self._gioca(sessione, "regioni", giuste=7)
        self.assertEqual([r.status_code for r in risposte], [200] * 10)
        self.assertEqual(
            [r.get_json()["score"]["correct"] for r in risposte],
            [1, 2, 3, 4, 5, 6, 7, 7, 7, 7],
        )
        self.assertEqual([r.get_json()["esito"] for r in risposte[:7]], ["exact"] * 7)
        self.assertEqual([r.get_json()["esito"] for r in risposte[7:]], ["miss"] * 3)
        ultima = risposte[-1].get_json()
        self.assertTrue(ultima["finished"])
        self.assertEqual(ultima["summary"]["score"], {"correct": 7, "total": 10})
        self.assertEqual(ultima["summary"]["puzzle_id"], sessione["puzzle_id"])
        self.assertEqual(ultima["summary"]["number"], sessione["number"])
        self.assertEqual(ultima["summary"]["next_puzzle_at"], sessione["next_puzzle_at"])
        self.assertFalse(risposte[0].get_json()["finished"])

    def test_an_answer_carries_only_the_pair_it_answers(self):
        sessione = self._sessione()
        ultima = self._gioca(sessione, "regioni", giuste=10)[-1].get_json()
        # Nell'ultima risposta ci sono i valori di una sola coppia, mai delle altre.
        self.assertEqual(json.dumps(ultima).count('"value"'), 2)
        self.assertEqual(ultima["a"]["key"], sessione["questions"][9]["a"]["key"])
        self.assertEqual(ultima["b"]["key"], sessione["questions"][9]["b"]["key"])

    def test_every_answer_names_its_own_indicator(self):
        sessione = self._sessione()
        for domanda, risposta in zip(sessione["questions"], self._gioca(sessione, "regioni")):
            corpo = risposta.get_json()
            self.assertEqual(corpo["index"], domanda["index"])
            self.assertEqual(corpo["indicator"]["id"], domanda["indicator"]["id"])
            self.assertEqual(corpo["a"]["name"], domanda["a"]["name"])
            self.assertEqual(corpo["b"]["name"], domanda["b"]["name"])


class PunteggioDelGiornoTest(Base):
    """La sfida finita con il timer conta per l'account (`daily_scores`)."""

    def _punteggi(self):
        from sqlalchemy import select
        from app.db import session_scope
        from app.models import DailyScore
        with session_scope() as s:
            return [(r.auth_id, r.gioco, r.data, r.punteggio)
                    for r in s.execute(select(DailyScore)).scalars().all()]

    def _accedi(self, sub):
        import jwt
        credenziale = jwt.encode(
            {"sub": sub, "email": "c@example.com", "aud": "authenticated",
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "test-jwt-secret", algorithm="HS256")
        self.client.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + credenziale

    def test_da_loggato_la_sfida_con_timer_registra_il_punteggio_una_volta(self):
        self._accedi("uuid-compare-1")
        sessione = self._sessione("regioni")
        self._gioca(sessione, "regioni", giuste=7)
        giorno = sessione["date"]
        self.assertEqual(self._punteggi(), [("uuid-compare-1", "compare", giorno, 7)])

    def test_l_allenamento_senza_timer_non_registra_niente(self):
        self._accedi("uuid-compare-2")
        sessione = self._sessione("regioni", timer=0)
        self._gioca(sessione, "regioni")
        self.assertEqual(self._punteggi(), [])
        # neanche i round per le serie dell'account (basso c della revisione finale)
        from app import player_stats
        self.assertEqual(player_stats.stats_map("uuid-compare-2")["compare"]["rounds_played"], 0)

    def test_con_il_timer_i_round_contano_per_l_account(self):
        from app import player_stats
        self._accedi("uuid-compare-4")
        self._gioca(self._sessione("regioni"), "regioni")
        self.assertEqual(player_stats.stats_map("uuid-compare-4")["compare"]["rounds_played"], 10)

    def test_da_anonimo_non_si_registra_niente(self):
        sessione = self._sessione("regioni")
        self._gioca(sessione, "regioni")
        self.assertEqual(self._punteggi(), [])


class LimiteFrequenzaTest(Base):
    def test_ip_limit_on_daily_answers(self):
        codici = [
            self.client.post("/api/game/compare/daily/answer", json={}).status_code
            for _ in range(121)
        ]
        self.assertEqual(codici[:120], [400] * 120)
        self.assertEqual(codici[120], 429)


class AvantiTest(Base):
    """R1 punto 9: la domanda successiva si lega quando il giocatore preme "Avanti",
    non quando risponde: il tempo di lettura della rivelazione non consuma i 12 s.
    `q` e' l'indice della domanda appena risposta."""

    def test_la_risposta_non_lega_piu_la_domanda_successiva(self):
        sessione = self._sessione()
        prima = self._risponde(sessione, 0, _vincitore("regioni", sessione["questions"][0])).get_json()
        self.assertIsNone(quiz_tokens.load_state(prima["token"], game_compare.MODE)["fp"])
        seconda = self._risponde(sessione, 1, "region_a", token=prima["token"], now=T0 + 2)
        self.assertEqual((seconda.status_code, seconda.get_json()["error"]), (400, "token_invalid"))

    def test_cinque_secondi_di_lettura_e_otto_di_risposta_non_sono_late(self):
        sessione = self._sessione()
        prima = self._risponde(sessione, 0, _vincitore("regioni", sessione["questions"][0]), now=T0 + 1).get_json()
        avanti = self._avanti(sessione, 0, prima["token"], now=T0 + 6)
        self.assertEqual(avanti.status_code, 200)
        self.assertEqual(list(avanti.get_json()), ["token"])
        seconda = self._risponde(sessione, 1, "region_a", token=avanti.get_json()["token"], now=T0 + 14)
        self.assertEqual(seconda.status_code, 200)

    def test_il_tempo_della_domanda_parte_da_avanti_e_non_si_ripete(self):
        sessione = self._sessione()
        prima = self._risponde(sessione, 0, "region_a", now=T0 + 1).get_json()
        avanti = self._avanti(sessione, 0, prima["token"], now=T0 + 6)
        tardi = self._risponde(sessione, 1, "region_a", token=avanti.get_json()["token"], now=T0 + 6 + 13)
        self.assertEqual(tardi.status_code, 200)
        self.assertTrue(tardi.get_json()["late"])
        # Chiedere di nuovo "Avanti" con lo stesso token per azzerare l'orologio non si puo'.
        di_nuovo = self._avanti(sessione, 0, prima["token"], now=T0 + 20)
        self.assertEqual(di_nuovo.status_code, 409)

    def test_non_si_salta_una_domanda_senza_averle_risposto(self):
        sessione = self._sessione()
        r = self._avanti(sessione, 0, sessione["token"])
        self.assertEqual((r.status_code, r.get_json()["error"]), (400, "token_invalid"))

    def test_dopo_l_ultima_domanda_non_c_e_altro_da_legare(self):
        sessione = self._sessione()
        risposte = self._gioca(sessione, "regioni")
        ultima = risposte[-1].get_json()
        r = self._avanti(sessione, 9, ultima["token"])
        self.assertEqual((r.status_code, r.get_json()["error"]), (400, "bad_request"))

    def test_un_altro_giorno_e_un_altro_token_non_valgono(self):
        sessione = self._sessione()
        prima = self._risponde(sessione, 0, "region_a").get_json()
        with mock.patch.object(quiz_tokens, "_now", return_value=T0):
            r = self.client.post("/api/game/compare/daily/next", json={
                "puzzle_id": "daily:2020-01-01", "q": 0, "token": prima["token"]})
            self.assertEqual(r.get_json()["error"], "puzzle_changed")
            serie = self.client.get("/api/game/compare/round").get_json()
            r = self.client.post("/api/game/compare/daily/next", json={
                "puzzle_id": sessione["puzzle_id"], "q": 0, "token": serie["token"]})
            self.assertEqual((r.status_code, r.get_json()["error"]), (400, "token_invalid"))

    def test_ha_il_limite_di_frequenza(self):
        codici = [self.client.post("/api/game/compare/daily/next", json={}).status_code for _ in range(121)]
        self.assertEqual(codici[120], 429)


class SerieTest(Base):
    def _corpo_serie(self, round_):
        valori = {
            riga["region_key"]: riga["value"]
            for riga in quiz._quiz_indicator_payload(
                round_["indicator"]["id"], round_["indicator"]["year"])["values"]
        }
        a = valori[round_["region_a"]["region_key"]]
        b = valori[round_["region_b"]["region_key"]]
        return {
            "indicator_id": round_["indicator"]["id"], "year": round_["indicator"]["year"],
            "region_a_key": round_["region_a"]["region_key"],
            "region_b_key": round_["region_b"]["region_key"],
            "choice": "region_a" if a > b else "region_b", "token": round_["token"],
        }

    def test_the_endless_round_still_works_next_to_the_daily(self):
        # La sfida del giorno aggiunge rotte, non toglie quelle del round a serie.
        round_ = self.client.get("/api/game/compare/round").get_json()
        corpo = self._corpo_serie(round_)
        self.assertEqual(self.client.post("/api/game/compare/answer", json=corpo).status_code, 200)
        # E una seconda volta la stessa coppia è un 409, come prima.
        self.assertEqual(
            self.client.post("/api/game/compare/answer", json=corpo).status_code, 409
        )

    def test_the_two_routes_keep_their_own_sessions(self):
        sessione = self._sessione()
        stato = quiz_tokens.load_state(sessione["token"], game_compare.MODE)
        self.assertEqual(stato["q"], 1)
        self.assertEqual(stato["x"], "regioni")
        # Il round a serie resta un round: due regioni e la sua difficolta'.
        round_ = self.client.get("/api/game/compare/round").get_json()
        self.assertIn("region_a", round_)
        self.assertIn("difficulty", round_)


if __name__ == "__main__":
    unittest.main()