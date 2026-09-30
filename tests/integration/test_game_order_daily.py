"""Test per la sfida del giorno di "Ordina le regioni" (app/game_order.py e rotte /api/game/order/daily/*)."""

import unittest
from datetime import date
from unittest import mock

from app import app, game_daily, sources


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


def game_daily_regioni():
    from app.data import REGION_ORDER
    return list(REGION_ORDER)


if __name__ == "__main__":
    unittest.main()
