"""Test per la sfida del giorno di "Ordina le regioni" (app/game_order.py e rotte /api/game/order/daily/*)."""

import shutil
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import jwt

from app import app, config, game_daily, game_order, quiz_tokens, sources
from app.db import session_scope
from app.models import DailyScore


class TestGameOrderDaily(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_daily_challenge_is_same_for_everyone_and_changes_at_rome_midnight(self):
        with mock.patch.object(game_daily, "oggi_roma", return_value=date(2026, 9, 30)):
            res1 = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
            res2 = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
            self.assertEqual(res1["date"], "2026-09-30")
            self.assertEqual(res1["puzzle_id"], "daily:2026-09-30")
            self.assertEqual(res1["indicator"]["id"], res2["indicator"]["id"])
            self.assertEqual(
                [t["key"] for t in res1["territories"]],
                [t["key"] for t in res2["territories"]],
            )

        with mock.patch.object(game_daily, "oggi_roma", return_value=date(2026, 10, 1)):
            res3 = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
            self.assertEqual(res3["date"], "2026-10-01")
            self.assertEqual(res3["puzzle_id"], "daily:2026-10-01")

    def test_payload_does_not_contain_correct_order_or_values(self):
        res = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        self.assertNotIn("values", res)
        self.assertNotIn("correct_order", res)
        self.assertIn("territories", res)
        for t in res["territories"]:
            self.assertNotIn("value", t)
            self.assertNotIn("correct_position", t)

    def test_evaluation_uses_real_values_and_returns_correct_fields(self):
        session = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        token = session["token"]
        keys = [t["key"] for t in session["territories"]]

        response = self.client.post("/api/game/order/daily/answer", json={
            "token": token,
            "level": "regioni",
            "region_keys": keys,
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("score", data)
        self.assertEqual(data["total"], 5)
        self.assertIn("positions", data)
        self.assertIn("correct_order", data)
        self.assertIn("indicator", data)
        self.assertIn("path", data["indicator"])
        self.assertIn("description", data["indicator"])
        self.assertIn("unit", data["indicator"])
        self.assertIn("year", data["indicator"])

        vals = [r["value"] for r in data["correct_order"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

        # Ogni riga porta il valore e la sua unita': e' quello che il client
        # scrive accanto al nome, e senza unita' non puo' farlo.
        for riga in data["positions"]:
            self.assertIsInstance(riga["value"], (int, float))
            self.assertEqual(riga["unit"], data["indicator"]["unit"])
        for riga in data["correct_order"]:
            self.assertIsInstance(riga["value"], (int, float))
            self.assertEqual(riga["unit"], data["indicator"]["unit"])

    def test_same_session_submitted_twice_returns_409(self):
        session = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        token = session["token"]
        keys = [t["key"] for t in session["territories"]]

        body = {"token": token, "level": "regioni", "region_keys": keys}
        res1 = self.client.post("/api/game/order/daily/answer", json=body)
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/game/order/daily/answer", json=body)
        self.assertEqual(res2.status_code, 409)

    def test_stessa_regione_uses_only_regions_with_at_least_5_provinces(self):
        idonee = game_daily.regioni_idonee(5)
        self.assertNotIn("Molise", idonee)
        self.assertNotIn("Valle d'Aosta", idonee)
        self.assertNotIn("Umbria", idonee)
        self.assertIn("Lombardia", idonee)
        self.assertIn("Piemonte", idonee)

        session = self.client.get("/api/game/order/daily/session?level=stessa_regione").get_json()
        self.assertIn(session["region"], idonee)
        self.assertEqual(len(session["territories"]), 5)
        for t in session["territories"]:
            self.assertEqual(t["region"], session["region"])

    def test_si_ordina_solo_la_sfida_di_oggi(self):
        session = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        token = session["token"]
        del_giorno = [t["key"] for t in session["territories"]]
        altri = [k for k in game_daily_regioni() if k not in del_giorno][:5]
        for chiavi in (altri, del_giorno[:4] + [del_giorno[0]], del_giorno[:4]):
            with self.subTest(chiavi=chiavi):
                r = self.client.post("/api/game/order/daily/answer", json={
                    "token": token, "level": "regioni", "region_keys": chiavi})
                self.assertEqual(r.status_code, 400)

    def test_a_livello_province_la_fonte_viene_da_sources(self):
        session = self.client.get("/api/game/order/daily/session?level=province").get_json()
        keys = [t["key"] for t in session["territories"]]
        r = self.client.post("/api/game/order/daily/answer", json={
            "token": session["token"], "level": "province", "region_keys": keys})
        self.assertEqual(r.status_code, 200)
        ind = r.get_json()["indicator"]
        self.assertEqual(ind["source_label"], sources.SOURCES["bes"]["label"])
        self.assertTrue(ind["path"].startswith("/indicatore/") and ind["path"].endswith("/province"))
        self.assertNotEqual(ind["source_url"], "https://www.istat.it")


def _jwt(sub):
    return jwt.encode({"sub": sub, "email": f"{sub}@example.com", "aud": "authenticated",
                       "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                      "test-jwt-secret", algorithm="HS256")


def _punteggi(auth_id):
    with session_scope() as s:
        return [(r.gioco, r.punteggio) for r in s.query(DailyScore).filter_by(auth_id=auth_id)]


class BaseOrdina(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = "test-jwt-secret"
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "o.sqlite3")
        from app.cache import cache
        for k in ("rl:ans:ip:127.0.0.1",):
            cache.delete(k)
        self.client = app.test_client()

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _sessione(self, level="regioni"):
        return self.client.get(f"/api/game/order/daily/session?level={level}").get_json()

    def _chiavi(self, sessione):
        return [t["key"] for t in sessione["territories"]]


class OrdinaDelGiornoSicuroTest(BaseOrdina):
    """R1 punti 2 e 10: il livello viene dal token, senza round legato niente valori
    ne' punteggio, e Ordina non ha un timer nel client."""

    def test_senza_token_si_risponde_400_senza_valori_ne_ordine_giusto(self):
        sessione = self._sessione()
        r = self.client.post("/api/game/order/daily/answer", json={"region_keys": self._chiavi(sessione)})
        self.assertEqual((r.status_code, r.get_json()), (400, {"error": "token_invalid"}))

    def test_senza_token_ma_loggato_non_registra_il_punteggio(self):
        sessione = self._sessione()
        r = self.client.post("/api/game/order/daily/answer", headers={"Authorization": "Bearer " + _jwt("o-1")},
                             json={"region_keys": self._chiavi(sessione)})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(_punteggi("o-1"), [])

    def test_un_token_di_un_altro_round_non_lega(self):
        sessione = self._sessione()
        serie = self.client.get("/api/game/order/round?count=5").get_json()
        for token in (serie["token"], "rotto"):
            with self.subTest(token=token[:6]):
                r = self.client.post("/api/game/order/daily/answer", json={
                    "token": token, "region_keys": self._chiavi(sessione)})
                self.assertEqual((r.status_code, r.get_json()), (400, {"error": "token_invalid"}))

    def test_il_livello_viene_dal_token_e_non_dal_corpo(self):
        sessione = self._sessione("province")
        r = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "level": "regioni", "region_keys": self._chiavi(sessione)})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["indicator"]["source_label"], sources.SOURCES["bes"]["label"])

    def test_la_sessione_del_giorno_non_ha_timer_e_una_risposta_tarda_conta(self):
        sessione = self._sessione()
        self.assertIs(sessione["timer"], False)
        with mock.patch.object(quiz_tokens, "_now", return_value=time.time() + 600):
            r = self.client.post("/api/game/order/daily/answer", headers={"Authorization": "Bearer " + _jwt("o-2")},
                                 json={"token": sessione["token"], "region_keys": self._chiavi(sessione)})
        corpo = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("late", corpo)
        ordine = [x["region_key"] for x in corpo["correct_order"]]
        self.assertEqual(len(ordine), 5)
        self.assertEqual(_punteggi("o-2"), [("order", corpo["score"])])

    def test_da_loggato_con_il_round_legato_registra_il_punteggio_una_volta(self):
        sessione = self._sessione()
        corpo = {"token": sessione["token"], "region_keys": self._chiavi(sessione)}
        intest = {"Authorization": "Bearer " + _jwt("o-3")}
        r = self.client.post("/api/game/order/daily/answer", headers=intest, json=corpo)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(_punteggi("o-3")), 1)
        self.assertEqual(self.client.post("/api/game/order/daily/answer", headers=intest, json=corpo).status_code, 409)

    def test_le_chiavi_alternative_non_si_accettano(self):
        sessione = self._sessione()
        for nome in ("territory_keys", "keys"):
            with self.subTest(nome=nome):
                r = self.client.post("/api/game/order/daily/answer", json={
                    "token": sessione["token"], nome: self._chiavi(sessione)})
                self.assertEqual(r.status_code, 400)

    def test_un_livello_sconosciuto_e_400(self):
        self.assertEqual(self.client.get("/api/game/order/daily/session?level=boh").status_code, 400)

    def test_il_modulo_di_dominio_non_dipende_da_flask_ne_dalle_viste(self):
        self.assertFalse(hasattr(game_order, "abort"))
        self.assertNotIn("app.views", open(game_order.__file__, encoding="utf-8").read())


class LimiteFrequenzaOrdinaTest(BaseOrdina):
    """R1 punto 15: sessione e risposta del giorno hanno il limite delle altre rotte."""

    def test_la_sessione_ha_il_limite_per_ip(self):
        codici = [self.client.get("/api/game/order/daily/session?level=regioni").status_code for _ in range(121)]
        self.assertEqual(codici[:120], [200] * 120)
        self.assertEqual(codici[120], 429)

    def test_la_risposta_ha_il_limite_per_ip(self):
        codici = [self.client.post("/api/game/order/daily/answer", json={}).status_code for _ in range(121)]
        self.assertEqual(codici[:120], [400] * 120)
        self.assertEqual(codici[120], 429)


class PercorsoCanonicoOrdinaTest(BaseOrdina):
    """R1 punto 17: il link dell'indicatore a livello province e' quello canonico
    (`bes_data.bes_level_path`), non uno slug composto dal nome leggibile."""

    def test_nessun_301_sui_quaranta_indicatori_provinciali(self):
        provinciali = [i for i in game_daily.indicatori_gioco() if i["provincia"]]
        self.assertGreaterEqual(len(provinciali), 40)
        for ind in provinciali:
            with self.subTest(indicatore=ind["id"]):
                percorso = game_order.province_path(ind["id"])
                self.assertEqual(self.client.get(percorso).status_code, 200, percorso)

    def test_la_risposta_del_giorno_porta_il_percorso_canonico(self):
        sessione = self._sessione("province")
        r = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "region_keys": self._chiavi(sessione)})
        percorso = r.get_json()["indicator"]["path"]
        self.assertEqual(percorso, game_order.province_path(sessione["indicator"]["id"]))
        self.assertEqual(self.client.get(percorso).status_code, 200)


class GiroDItaliaTest(unittest.TestCase):
    """Aggiunta A: il punteggio di oggi si registra PRIMA di valutare i traguardi,
    quindi la sfida giocata per ultima, qualunque sia, sblocca "Giro d'Italia" sulla
    sua risposta. Le altre tre si scrivono nel DB, l'ultima passa dalla rotta vera."""

    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = "test-jwt-secret"
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "g.sqlite3")
        self.client = app.test_client()

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _auth(self, sub):
        return {"Authorization": "Bearer " + _jwt(sub)}

    def _prepara(self, sub, tranne):
        from app import player_stats
        oggi = game_daily.oggi_roma().isoformat()
        if tranne != "indovina":
            player_stats.record_daily(sub, oggi, 2, True)
        for gioco, punteggio in (("provincia", 1), ("compare", 7), ("order", 5)):
            if gioco != tranne:
                player_stats.record_daily_score(sub, gioco, oggi, punteggio)

    def test_indovina_per_ultima_sblocca_il_giro_d_italia(self):
        from app import game
        self._prepara("giro-indovina", "indovina")
        puzzle_id = f"daily:{game_daily.oggi_roma().isoformat()}"
        r = self.client.post("/api/game/guess", headers=self._auth("giro-indovina"), json={
            "puzzle_id": puzzle_id, "region_key": game.build_puzzle(puzzle_id)["region_key"], "attempt": 1})
        self.assertIn("giro_ditalia", [a["id"] for a in r.get_json()["achievements"]])

    def test_provincia_per_ultima_sblocca_il_giro_d_italia(self):
        from app import game_provincia
        from app.cache import cache
        self._prepara("giro-provincia", "provincia")
        cache.delete("rl:prov:ip:127.0.0.1")
        payload = self.client.get("/api/game/provincia/daily?level=province").get_json()
        mistero = game_provincia.provincia_del_giorno(game_daily.oggi_roma())["key"]
        r = self.client.post("/api/game/provincia/guess", headers=self._auth("giro-provincia"), json={
            "token": payload["token"], "province_key": mistero})
        self.assertIn("giro_ditalia", [a["id"] for a in r.get_json()["achievements"]])

    def test_chi_e_maggiore_per_ultima_sblocca_il_giro_d_italia(self):
        from app.cache import cache
        self._prepara("giro-compare", "compare")
        cache.delete("rl:ans:ip:127.0.0.1")
        sessione = self.client.get("/api/game/compare/daily/session?level=regioni").get_json()
        token = sessione["token"]
        ultima = None
        for indice in range(len(sessione["questions"])):
            ultima = self.client.post("/api/game/compare/daily/answer", headers=self._auth("giro-compare"), json={
                "token": token, "puzzle_id": sessione["puzzle_id"], "q": indice, "choice": "region_a"}).get_json()
            token = ultima["token"]
            if indice < len(sessione["questions"]) - 1:
                token = self.client.post("/api/game/compare/daily/next", json={
                    "token": token, "puzzle_id": sessione["puzzle_id"], "q": indice}).get_json()["token"]
        self.assertTrue(ultima["finished"])
        self.assertIn("giro_ditalia", [a["id"] for a in ultima["achievements"]])

    def test_ordina_per_ultima_sblocca_il_giro_d_italia_sull_ultima_risposta(self):
        from app import player_stats
        oggi = game_daily.oggi_roma().isoformat()
        for gioco, punteggio in (("provincia", 1), ("compare", 7)):
            player_stats.record_daily_score("giro-1", gioco, oggi, punteggio)
        player_stats.record_daily("giro-1", oggi, 2, True)
        sessione = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        r = self.client.post("/api/game/order/daily/answer", headers={"Authorization": "Bearer " + _jwt("giro-1")},
                             json={"token": sessione["token"], "region_keys": [t["key"] for t in sessione["territories"]]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("giro_ditalia", [a["id"] for a in r.get_json()["achievements"]])



def game_daily_regioni():
    from app.data import REGION_ORDER
    return list(REGION_ORDER)


if __name__ == "__main__":
    unittest.main()
