"""Hub del Quiz, classifica del giorno e traguardi nuovi (W7).

La classifica di oggi ordina per tentativi e poi per ora di arrivo, mostra solo
nickname moderati e niente id, e un anonimo non ci compare. I tre traguardi nuovi
si provano su righe vere di `daily_results` e `daily_scores`, un caso che li
sblocca e uno che no."""

import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import accounts, achievements, app, classifica_giorno, config, game, game_daily, game_provincia, player_stats
from app.cache import cache
from app.db import session_scope
from app.models import DailyResult, DailyScore

_SECRET = "test-jwt-secret"
_ROOT = Path(__file__).resolve().parents[2]


def _jwt(sub):
    payload = {"sub": sub, "email": f"{sub}@example.com", "aud": "authenticated",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = _SECRET
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "h.sqlite3")
        for chiave in ("rl:prov:ip:127.0.0.1", "rl:ans:ip:127.0.0.1"):
            cache.delete(chiave)
        self.oggi = game_daily.oggi_roma()

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def risultato(self, auth_id, nickname, tentativi, arrivo, risolto=True, giorno=None):
        """Un risultato giornaliero di Indovina, con l'ora di arrivo in `daily_scores`."""
        giorno = (giorno or self.oggi).isoformat()
        if nickname is not None:
            accounts.upsert_profile(auth_id, f"{auth_id}@example.com", nickname)
        with session_scope() as s:
            s.add(DailyResult(auth_id=auth_id, puzzle_date=giorno, attempts=tentativi, solved=1 if risolto else 0))
            if arrivo:
                s.add(DailyScore(auth_id=auth_id, gioco="indovina", data=giorno,
                                 punteggio=1 if risolto else 0, created_at=arrivo))


class ClassificaDelGiornoTest(Base):
    def test_ordina_per_tentativi_poi_per_ora_di_arrivo(self):
        self.risultato("u-lento", "Lento", 3, "2026-09-30T09:00:00Z")
        self.risultato("u-veloce", "Veloce", 3, "2026-09-30T07:00:00Z")
        self.risultato("u-bravo", "Bravo", 1, "2026-09-30T20:00:00Z")
        self.risultato("u-ultimo", "Ultimo", 6, "2026-09-30T06:00:00Z")
        voci = classifica_giorno.classifica_oggi()
        self.assertEqual([v["nickname"] for v in voci], ["Bravo", "Veloce", "Lento", "Ultimo"])
        self.assertEqual([v["rank"] for v in voci], [1, 2, 3, 4])

    def test_chi_non_ha_l_ora_di_arrivo_viene_dopo_a_parita_di_tentativi(self):
        self.risultato("u-senza", "Senzaora", 2, None)
        self.risultato("u-con", "Conora", 2, "2026-09-30T12:00:00Z")
        voci = classifica_giorno.classifica_oggi()
        self.assertEqual([v["nickname"] for v in voci], ["Conora", "Senzaora"])

    def test_solo_chi_ha_risolto_oggi(self):
        self.risultato("u-ok", "Risolto", 4, "2026-09-30T08:00:00Z")
        self.risultato("u-no", "Perso", 6, "2026-09-30T08:00:00Z", risolto=False)
        self.risultato("u-ieri", "Ieri", 1, "2026-09-29T08:00:00Z", giorno=self.oggi - timedelta(days=1))
        self.assertEqual([v["nickname"] for v in classifica_giorno.classifica_oggi()], ["Risolto"])

    def test_un_anonimo_o_senza_nickname_non_compare(self):
        self.risultato("u-senza-profilo", None, 1, "2026-09-30T08:00:00Z")
        self.risultato("u-vuoto", "", 1, "2026-09-30T08:00:00Z")
        self.risultato("u-ok", "Presente", 2, "2026-09-30T08:00:00Z")
        self.assertEqual([v["nickname"] for v in classifica_giorno.classifica_oggi()], ["Presente"])

    def test_un_nickname_non_moderato_non_esce(self):
        self.risultato("u-male", "a", 1, "2026-09-30T08:00:00Z")
        self.risultato("u-ok", "Presente", 2, "2026-09-30T08:00:00Z")
        self.assertEqual([v["nickname"] for v in classifica_giorno.classifica_oggi()], ["Presente"])

    def test_primi_venti(self):
        for i in range(25):
            self.risultato(f"u{i:02d}", f"Giocatore{i:02d}", 1 + i % 6, f"2026-09-30T08:{i:02d}:00Z")
        self.assertEqual(len(classifica_giorno.classifica_oggi()), 20)

    def test_la_rotta_e_pubblica_e_non_espone_ne_id_ne_email(self):
        self.risultato("uuid-segreto-123", "Presente", 2, "2026-09-30T08:00:00Z")
        risposta = app.test_client().get("/api/game/daily/leaderboard")
        self.assertEqual(risposta.status_code, 200)
        corpo = risposta.get_json()
        self.assertEqual(corpo["date"], self.oggi.isoformat())
        self.assertEqual([v["nickname"] for v in corpo["entries"]], ["Presente"])
        testo = json.dumps(corpo)
        self.assertNotIn("uuid-segreto-123", testo)
        self.assertNotIn("example.com", testo)
        self.assertNotIn("auth_id", testo)

    def test_la_guess_di_indovina_scrive_la_riga_con_l_ora_e_la_classifica_la_vede(self):
        puzzle_id = f"daily:{self.oggi.isoformat()}"
        vincente = game.build_puzzle(puzzle_id)["region_key"]
        accounts.upsert_profile("uuid-guess", "g@example.com", "Indovino")
        r = app.test_client().post("/api/game/guess", json={"puzzle_id": puzzle_id, "region_key": vincente, "attempt": 1},
                                   headers={"Authorization": f"Bearer {_jwt('uuid-guess')}"})
        self.assertTrue(r.get_json()["correct"])
        with session_scope() as s:
            riga = s.get(DailyScore, {"auth_id": "uuid-guess", "gioco": "indovina", "data": self.oggi.isoformat()})
        self.assertIsNotNone(riga)
        self.assertEqual(riga.punteggio, 1)
        self.assertEqual([v["nickname"] for v in classifica_giorno.classifica_oggi()], ["Indovino"])

    def test_la_guess_anonima_non_scrive_niente(self):
        puzzle_id = f"daily:{self.oggi.isoformat()}"
        vincente = game.build_puzzle(puzzle_id)["region_key"]
        app.test_client().post("/api/game/guess", json={"puzzle_id": puzzle_id, "region_key": vincente, "attempt": 1})
        with session_scope() as s:
            self.assertEqual(s.query(DailyScore).count(), 0)
        self.assertEqual(classifica_giorno.classifica_oggi(), [])


class GuessProvinciaTest(Base):
    def _gioca(self, sub, corretta):
        client = app.test_client()
        payload = client.get("/api/game/provincia/daily?level=province").get_json()
        mistero = game_provincia.provincia_del_giorno(self.oggi)["key"]
        if corretta:
            chiave = mistero
        else:
            chiave = next(o["key"] for o in game_provincia.opzioni("province", self.oggi) if o["key"] != mistero)
        cache.delete("rl:prov:ip:127.0.0.1")
        return client.post("/api/game/provincia/guess", json={"token": payload["token"], "province_key": chiave},
                           headers={"Authorization": f"Bearer {_jwt(sub)}"} if sub else {})

    def _riga(self, sub):
        with session_scope() as s:
            return s.get(DailyScore, {"auth_id": sub, "gioco": "provincia", "data": self.oggi.isoformat()})

    def test_indovinare_scrive_la_riga_e_sblocca_geografo(self):
        r = self._gioca("uuid-prov", True).get_json()
        self.assertTrue(r["correct"])
        self.assertEqual(self._riga("uuid-prov").punteggio, 1)
        self.assertIn("geografo", [a["id"] for a in r["achievements"]])

    def test_un_tentativo_sbagliato_non_chiude_e_non_scrive(self):
        self._gioca("uuid-prov2", False)
        self.assertIsNone(self._riga("uuid-prov2"))

    def test_da_anonimo_non_scrive(self):
        self._gioca(None, True)
        with session_scope() as s:
            self.assertEqual(s.query(DailyScore).count(), 0)


class TraguardiNuoviTest(Base):
    def _punteggio(self, auth_id, gioco, giorno, punteggio):
        with session_scope() as s:
            s.add(DailyScore(auth_id=auth_id, gioco=gioco, data=giorno.isoformat(), punteggio=punteggio,
                             created_at="2026-09-30T08:00:00Z"))

    def _indovina(self, auth_id, giorno, risolto=True):
        with session_scope() as s:
            s.add(DailyResult(auth_id=auth_id, puzzle_date=giorno.isoformat(), attempts=3, solved=1 if risolto else 0))

    def _sbloccati(self, auth_id):
        return set(achievements.unlocked_map(auth_id))

    def test_geografo_si_sblocca_con_una_provincia_indovinata(self):
        self._punteggio("g1", "provincia", self.oggi, 1)
        achievements.evaluate("g1")
        self.assertIn("geografo", self._sbloccati("g1"))

    def test_geografo_non_si_sblocca_con_una_provincia_sbagliata(self):
        self._punteggio("g2", "provincia", self.oggi, 0)
        achievements.evaluate("g2")
        self.assertNotIn("geografo", self._sbloccati("g2"))

    def test_giro_ditalia_vuole_le_quattro_sfide_nello_stesso_giorno(self):
        self._indovina("g3", self.oggi)
        for gioco, punteggio in (("provincia", 1), ("compare", 7), ("order", 5)):
            self._punteggio("g3", gioco, self.oggi, punteggio)
        achievements.evaluate("g3")
        self.assertIn("giro_ditalia", self._sbloccati("g3"))

    def test_giro_ditalia_non_si_somma_su_giorni_diversi(self):
        ieri = self.oggi - timedelta(days=1)
        self._indovina("g4", self.oggi)
        self._punteggio("g4", "provincia", self.oggi, 1)
        self._punteggio("g4", "compare", ieri, 7)
        self._punteggio("g4", "order", ieri, 5)
        achievements.evaluate("g4")
        self.assertNotIn("giro_ditalia", self._sbloccati("g4"))

    def test_giro_ditalia_non_conta_una_regione_non_risolta(self):
        self._indovina("g5", self.oggi, risolto=False)
        for gioco, punteggio in (("provincia", 1), ("compare", 7), ("order", 5)):
            self._punteggio("g5", gioco, self.oggi, punteggio)
        achievements.evaluate("g5")
        self.assertNotIn("giro_ditalia", self._sbloccati("g5"))

    def test_fedele_vuole_trenta_giorni_di_fila_con_almeno_una_sfida(self):
        for i in range(30):
            giorno = self.oggi - timedelta(days=i)
            if i % 2:
                self._indovina("g6", giorno)
            else:
                self._punteggio("g6", "order", giorno, 3)
        achievements.evaluate("g6")
        self.assertIn("fedele", self._sbloccati("g6"))

    def test_fedele_non_si_sblocca_con_un_giorno_di_buco(self):
        for i in range(30):
            if i == 12:
                continue
            self._punteggio("g7", "order", self.oggi - timedelta(days=i), 3)
        achievements.evaluate("g7")
        self.assertNotIn("fedele", self._sbloccati("g7"))


class IconeDeiTraguardiTest(unittest.TestCase):
    def test_ogni_traguardo_ha_icon_url_e_il_file_c_e(self):
        for voce in achievements.list_for("nessuno"):
            self.assertTrue(voce["icon_url"].startswith("/static/img/gioco/traguardi/"), voce["id"])
            self.assertTrue((_ROOT / "app" / voce["icon_url"].lstrip("/")).is_file(), voce["id"])
            self.assertTrue(voce["icon"], "l'emoji resta per compatibilita'")

    def test_i_testi_dei_traguardi_seguono_le_regole_della_prosa(self):
        for voce in achievements.list_for("nessuno"):
            for campo in (voce["title"], voce["description"]):
                for vietato in ("—", "–", ";", "…"):
                    self.assertNotIn(vietato, campo)


class ImmaginiOgDeiGiochiTest(unittest.TestCase):
    def test_le_pagine_dei_giochi_dichiarano_la_loro_immagine(self):
        client = app.test_client()
        for percorso, nome in (("/quiz/indovina-la-regione", "indovina-regione"),
                               ("/quiz/indovina-la-provincia", "indovina-provincia"),
                               ("/quiz/chi-e-maggiore", "chi-e-maggiore"),
                               ("/quiz/ordina", "ordina")):
            html = client.get(percorso).get_data(as_text=True)
            self.assertIn(f"/static/img/og/gioco-{nome}.png", html, percorso)
            self.assertTrue((_ROOT / "app" / "static" / "img" / "og" / f"gioco-{nome}.png").is_file())


class HubPaginaTest(unittest.TestCase):
    def test_le_quattro_card_sono_nel_markup_del_server(self):
        html = app.test_client().get("/quiz").get_data(as_text=True)
        for gioco in ("indovina", "provincia", "compare", "order"):
            self.assertIn(f'data-gioco="{gioco}"', html)
        self.assertIn("data-oggi-countdown", html)
        self.assertNotIn("Come funziona il quiz", html)


if __name__ == "__main__":
    unittest.main()
