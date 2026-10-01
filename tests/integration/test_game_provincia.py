"""Indovina la Provincia: la sfida del giorno, il feedback, l'anti-spoiler.

Il server decide tutto: la provincia esce dal seed, il numero del tentativo dal
token firmato, la soluzione solo a partita finita. Le prove guardano i fatti che
il giocatore non deve poter cambiare.
"""
import json
import re
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from app import app, game_daily, game_provincia
from app.cache import cache
from app.game_daily import today_rome

CHIAVE = "chiave-di-prova"


class _OrologioFisso(datetime):
    """`datetime` con `now()` fissato alle 23:30 UTC del 30 settembre 2026,
    quando a Roma (CEST) e' gia' l'1 ottobre."""

    @classmethod
    def now(cls, tz=None):
        fisso = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
        return fisso.astimezone(tz) if tz else fisso.replace(tzinfo=None)


def _sbagliata(mistero, livello="province", giorno=None, escluse=()):
    """Una provincia tentabile a quel livello che non e' la misteriosa."""
    giorno = giorno or today_rome()
    for voce in game_provincia.options(livello, giorno):
        if voce["key"] != mistero["key"] and voce["key"] not in escluse:
            return voce["key"]
    raise AssertionError("nessuna provincia sbagliata disponibile")


class ProvinciaDelGiornoTest(unittest.TestCase):
    def test_e_la_stessa_per_tutti(self):
        giorno = date(2026, 10, 1)
        a = game_provincia.daily_province(giorno, CHIAVE)
        b = game_provincia.daily_province(giorno, CHIAVE)
        self.assertEqual(a, b)
        primo, secondo = (game_provincia.payload("province", key=CHIAVE) for _ in range(2))
        for payload in (primo, secondo):
            payload.pop("token")
        self.assertEqual(primo, secondo)

    def test_dipende_dalla_chiave_non_dal_solo_calendario(self):
        giorno = date(2026, 10, 1)
        scelte = {game_provincia.daily_province(giorno, f"k{i}")["key"] for i in range(12)}
        self.assertGreater(len(scelte), 1)

    def test_e_sempre_giocabile_e_di_una_regione_idonea(self):
        idonee = set(game_daily.eligible_regions(3))
        escluse = set(game_daily.excluded_provinces())
        inizio = date(2026, 7, 15)
        for offset in range(400):
            provincia = game_provincia.daily_province(inizio + timedelta(days=offset), CHIAVE)
            self.assertNotIn(provincia["key"], escluse)
            self.assertIn(provincia["region"], idonee)

    def test_cambia_a_mezzanotte_di_roma_e_non_a_quella_utc(self):
        prima = game_provincia.payload("province", now=datetime(2026, 9, 30, 21, 30, tzinfo=timezone.utc), key=CHIAVE)
        dopo = game_provincia.payload("province", now=datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc), key=CHIAVE)
        self.assertEqual(prima["date"], "2026-09-30")
        self.assertEqual(dopo["date"], "2026-10-01")
        self.assertEqual(dopo["puzzle_id"], "daily:2026-10-01")
        self.assertEqual(dopo["next_puzzle_at"], "2026-10-01T22:00:00+00:00")
        self.assertEqual(dopo["number"], prima["number"] + 1)
        # Le due giornate hanno il loro seed: nell'arco di un mese non sono tutte uguali.
        chiavi = {
            game_provincia.daily_province(date(2026, 9, 1) + timedelta(days=i), CHIAVE)["key"]
            for i in range(30)
        }
        self.assertGreater(len(chiavi), 20)

    def test_le_rotte_seguono_il_giorno_di_roma(self):
        with mock.patch("app.game_daily.datetime", _OrologioFisso):
            cache.delete("rl:prov:ip:127.0.0.1")
            payload = app.test_client().get("/api/game/provincia/daily?level=province").get_json()
        self.assertEqual(payload["date"], "2026-10-01")
        self.assertEqual(payload["puzzle_id"], "daily:2026-10-01")


class IndiziTest(unittest.TestCase):
    def test_indizi_ammessi_sono_quelli_della_spec(self):
        import csv

        with (game_daily.ROOT / "app/static/data/province_manifest.csv").open(encoding="utf-8") as handle:
            manifesto = {r["id"]: r for r in csv.DictReader(handle, delimiter=";")}
        ammessi = game_provincia.allowed_clues()
        self.assertGreaterEqual(len(ammessi), 6)
        in_config = {game_daily.provincial_id(v["id"]) for v in game_daily.game_indicators() if v["provincia"]}
        for ind in ammessi:
            riga = manifesto[ind["id"]]
            self.assertEqual(int(riga["n_province_latest"]), 107, ind["id"])
            self.assertGreaterEqual(int(riga["year_max"]), 2022, ind["id"])
            self.assertIn(ind["id"], in_config)

    def test_sei_indizi_distinti_con_anno_fonte_e_link(self):
        inizio = date(2026, 7, 15)
        for offset in range(60):
            indizi = game_provincia.daily_clues(inizio + timedelta(days=offset), CHIAVE)
            self.assertEqual(len(indizi), 6)
            self.assertEqual(len({i["id"] for i in indizi}), 6)
            for i in indizi:
                self.assertGreaterEqual(i["year"], 2022)
                self.assertTrue(i["path"].startswith("/indicatore/"), i["path"])
                self.assertTrue(i["source_label"] and i["source_url"].startswith("https://"))
                self.assertTrue(i["description"])
                self.assertGreaterEqual(i["rank"], 1)
                self.assertLessEqual(i["rank"], 107)

    def test_gli_indizi_salgono_di_distintivita(self):
        for offset in range(20):
            indizi = game_provincia.daily_clues(date(2026, 8, 1) + timedelta(days=offset), CHIAVE)
            distanze = [abs(i["rank"] - 54) for i in indizi]
            self.assertEqual(distanze, sorted(distanze))


class PayloadTest(unittest.TestCase):
    def setUp(self):
        cache.delete("rl:prov:ip:127.0.0.1")
        self.client = app.test_client()

    def test_la_soluzione_non_e_nel_payload_della_partita_in_corso(self):
        payload = self.client.get("/api/game/provincia/daily?level=province").get_json()
        for campo in ("solution", "recap", "province", "province_key", "distance_km"):
            self.assertNotIn(campo, payload)
        giorno = today_rome()
        indizi = game_provincia.daily_clues(giorno)
        self.assertEqual(payload["clue"]["id"], indizi[0]["id"])
        testo = json.dumps(payload, ensure_ascii=False)
        # Gli altri cinque indizi non escono prima di un tentativo.
        for indizio in indizi[1:]:
            self.assertNotIn(indizio["name"], testo)
        self.assertEqual(payload["clues_total"], 6)
        self.assertEqual(payload["attempts_total"], 6)

    def test_le_opzioni_non_dicono_quale_e_giocabile_ne_quale_e_la_misteriosa(self):
        payload = self.client.get("/api/game/provincia/daily?level=province").get_json()
        self.assertEqual(len(payload["provinces"]), 107)
        for voce in payload["provinces"]:
            self.assertEqual(set(voce), {"key", "name", "region", "x", "y"})

    def test_livello_sconosciuto_e_400(self):
        for livello in ("regioni", "x", ""):
            with self.subTest(livello=livello):
                risposta = self.client.get(f"/api/game/provincia/daily?level={livello}")
                self.assertEqual(risposta.status_code, 400)

    def test_livello_della_regione_offre_solo_le_province_di_quella_regione(self):
        idonee = set(game_daily.eligible_regions(3))
        inizio = date(2026, 7, 15)
        for offset in range(120):
            giorno = inizio + timedelta(days=offset)
            now = datetime.combine(giorno, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
            payload = game_provincia.payload("stessa_regione", now=now, key=CHIAVE)
            regione = payload["region"]["name"]
            self.assertIn(regione, idonee)
            self.assertGreaterEqual(len(payload["provinces"]), 3)
            self.assertEqual({p["region"] for p in payload["provinces"]}, {regione})
            mistero = game_provincia.daily_province(giorno, CHIAVE)
            self.assertEqual(mistero["region"], regione)
            self.assertIn(mistero["key"], {p["key"] for p in payload["provinces"]})
            self.assertRegex(payload["region"]["viewbox"], r"^[\d.\-]+( [\d.\-]+){3}$")

    def test_al_livello_della_regione_il_payload_porta_le_province_delle_altre(self):
        """Serve al client per dire "Milano non e' in Puglia" invece di tacere: nome e regione,
        niente coordinate, e mai una provincia della regione indicata (ne' la misteriosa)."""
        payload = game_provincia.payload("stessa_regione", key=CHIAVE)
        altre = payload["other_provinces"]
        regione = payload["region"]["name"]
        nomi_regione = {p["name"] for p in payload["provinces"]}
        self.assertEqual(len(altre) + len(payload["provinces"]), 107)
        for voce in altre:
            self.assertEqual(set(voce), {"name", "region"})
            self.assertNotEqual(voce["region"], regione)
            self.assertNotIn(voce["name"], nomi_regione)

    def test_al_livello_di_tutta_italia_non_serve_il_campo(self):
        self.assertNotIn("other_provinces", game_provincia.payload("province", key=CHIAVE))

    def test_livello_di_tutta_italia_offre_tutte_e_107(self):
        payload = game_provincia.payload("province", key=CHIAVE)
        self.assertIsNone(payload["region"])
        self.assertEqual(len(payload["provinces"]), 107)


class TentativiTest(unittest.TestCase):
    def setUp(self):
        cache.delete("rl:prov:ip:127.0.0.1")
        self.client = app.test_client()
        self.giorno = today_rome()
        self.mistero = game_provincia.daily_province(self.giorno)

    def _apri(self, livello="province"):
        return self.client.get(f"/api/game/provincia/daily?level={livello}").get_json()

    def _tenta(self, token, chiave, **extra):
        cache.delete("rl:prov:ip:127.0.0.1")
        return self.client.post("/api/game/provincia/guess", json={"token": token, "province_key": chiave, **extra})

    def test_il_feedback_da_km_e_direzione_come_game_daily(self):
        payload = self._apri()
        chiave = _sbagliata(self.mistero)
        risposta = self._tenta(payload["token"], chiave)
        self.assertEqual(risposta.status_code, 200)
        r = risposta.get_json()
        km, direzione = game_daily.distance_km_direction(chiave, self.mistero["key"])
        self.assertAlmostEqual(r["distance_km"], km, delta=1)
        self.assertEqual(r["direction"], direzione)
        self.assertIn(r["direction"], game_daily._COMPASS_POINTS)
        self.assertGreater(r["distance_km"], 0)
        self.assertEqual(r["same_region"], game_daily._province_by_key(chiave)["region"] == self.mistero["region"])
        self.assertFalse(r["correct"])
        self.assertEqual(r["attempt"], 1)
        self.assertEqual(len(r["feedback"]), 1)
        self.assertIn(r["feedback"][0]["comparison"], {"higher", "lower", "equal", "unknown"})
        self.assertIsNotNone(r["next_clue"])

    def test_la_misura_dei_km_e_plausibile(self):
        # Milano-Roma in linea d'aria sono circa 480 km, Torino-Trieste circa 410:
        # la stima del gioco e' approssimata, non di qualche metro.
        km, direzione = game_daily.distance_km_direction("milano", "roma")
        self.assertTrue(400 <= km <= 560, km)
        self.assertEqual(direzione, "SE")
        self.assertEqual(game_daily.distance_km_direction("roma", "roma"), (0, None))

    def test_il_confronto_dell_indizio_ha_il_verso_del_valore_tentato(self):
        payload = self._apri()
        chiave = _sbagliata(self.mistero)
        r = self._tenta(payload["token"], chiave).get_json()
        indizio = game_provincia.daily_clues(self.giorno)[0]
        f = r["feedback"][0]
        if f["comparison"] == "higher":
            self.assertGreater(f["guess_value"], indizio["value"])
        elif f["comparison"] == "lower":
            self.assertLess(f["guess_value"], indizio["value"])
        self.assertEqual(f["mystery_rank"], indizio["rank"])
        self.assertEqual(f["province_count"], 107)

    def test_il_tentativo_e_deciso_dal_token_non_dal_client(self):
        payload = self._apri()
        chiave = _sbagliata(self.mistero)
        r = self._tenta(payload["token"], chiave, attempt=6, puzzle_id="daily:2026-07-15").get_json()
        self.assertEqual(r["attempt"], 1)
        self.assertFalse(r["finished"])
        self.assertIsNone(r["solution"])
        self.assertIsNone(r["recap"])

    def test_la_soluzione_esce_solo_a_partita_finita(self):
        payload = self._apri()
        token, tentate = payload["token"], []
        for n in range(1, 6):
            chiave = _sbagliata(self.mistero, escluse=tentate)
            r = self._tenta(token, chiave).get_json()
            tentate.append(chiave)
            self.assertEqual(r["attempt"], n)
            self.assertFalse(r["finished"])
            self.assertIsNone(r["solution"])
            self.assertIsNone(r["recap"])
            self.assertEqual(len(r["feedback"]), n)
            self.assertIsNotNone(r["next_clue"])
            token = r["token"]
        ultima = self._tenta(token, _sbagliata(self.mistero, escluse=tentate)).get_json()
        self.assertTrue(ultima["finished"])
        self.assertFalse(ultima["correct"])
        self.assertEqual(ultima["solution"]["province_key"], self.mistero["key"])
        self.assertEqual(ultima["solution"]["path"], f"/provincia/{self.mistero['key']}")
        self.assertEqual(len(ultima["recap"]), 6)
        self.assertIsNone(ultima["next_clue"])
        for riga in ultima["recap"]:
            for campo in ("id", "name", "unit", "year", "value", "province_avg", "path", "description", "source_label"):
                self.assertIn(campo, riga)

    def test_indovinare_chiude_la_partita_con_la_soluzione(self):
        payload = self._apri()
        r = self._tenta(payload["token"], self.mistero["key"]).get_json()
        self.assertTrue(r["correct"])
        self.assertTrue(r["finished"])
        self.assertEqual(r["distance_km"], 0)
        self.assertEqual(r["solution"]["province"], self.mistero["name"])
        self.assertEqual(r["solution"]["region_path"], f"/regione/{self.mistero['region_key']}")
        chiusa = self._tenta(r["token"], _sbagliata(self.mistero))
        self.assertEqual(chiusa.status_code, 409)
        self.assertEqual(chiusa.get_json()["error"], "partita_conclusa")

    def test_un_token_gia_usato_non_si_riusa_per_sondare(self):
        payload = self._apri()
        chiavi = [v["key"] for v in payload["provinces"] if v["key"] != self.mistero["key"]][:2]
        self.assertEqual(self._tenta(payload["token"], chiavi[0]).status_code, 200)
        riuso = self._tenta(payload["token"], chiavi[1])
        self.assertEqual(riuso.status_code, 409)
        self.assertEqual(riuso.get_json()["error"], "token_superato")

    def test_input_non_validi_sono_400(self):
        payload = self._apri()
        chiave = _sbagliata(self.mistero)
        self.assertEqual(self._tenta(payload["token"], "atlantide").status_code, 400)
        self.assertEqual(self._tenta(payload["token"], None).status_code, 400)
        self.assertEqual(self._tenta("non-un-token", chiave).status_code, 400)
        self.assertEqual(self._tenta(payload["token"][:-3] + "abc", chiave).status_code, 400)
        self.assertEqual(self._tenta(None, chiave).status_code, 400)
        primo = self._tenta(payload["token"], chiave).get_json()
        doppia = self._tenta(primo["token"], chiave)
        self.assertEqual(doppia.status_code, 400)
        self.assertEqual(doppia.get_json()["error"], "provincia_gia_tentata")

    def test_a_livello_regione_una_provincia_di_un_altra_regione_e_rifiutata(self):
        payload = self._apri("stessa_regione")
        fuori = next(p["key"] for p in game_daily.province_pool() if p["region"] != payload["region"]["name"])
        risposta = self._tenta(payload["token"], fuori)
        self.assertEqual(risposta.status_code, 400)
        self.assertEqual(risposta.get_json()["error"], "provincia_non_valida")
        dentro = _sbagliata(self.mistero, "stessa_regione")
        r = self._tenta(payload["token"], dentro).get_json()
        self.assertTrue(r["same_region"])

    def test_un_token_di_ieri_non_vale_dopo_mezzanotte_di_roma(self):
        ieri = datetime(2026, 9, 30, 21, 30, tzinfo=timezone.utc)
        oggi = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
        payload = game_provincia.payload("province", now=ieri)
        chiave = next(v["key"] for v in payload["provinces"])
        with self.assertRaises(game_provincia.ProvinceError) as contesto:
            game_provincia.evaluate_attempt(payload["token"], chiave, now=oggi)
        self.assertEqual(contesto.exception.status, 410)

    def test_un_token_di_un_altro_sale_non_si_accetta(self):
        from itsdangerous import URLSafeTimedSerializer

        falso = URLSafeTimedSerializer(app.secret_key, salt="quiz-session").dumps(
            {"p": f"daily:{self.giorno.isoformat()}", "l": "province", "g": [], "sid": "x"}
        )
        self.assertEqual(self._tenta(falso, _sbagliata(self.mistero)).status_code, 400)

    def test_il_risultato_non_entra_nella_serie_regionale(self):
        payload = self._apri()
        with mock.patch("app.auth.current_user", return_value={"id": "utente-di-prova"}), \
                mock.patch("app.player_stats.record_daily") as registra:
            r = self._tenta(payload["token"], self.mistero["key"]).get_json()
        self.assertTrue(r["finished"])
        registra.assert_not_called()
        # I traguardi della provincia (Geografo) possono esserci, quelli della regione del giorno no.
        self.assertNotIn("daily_solver", [a["id"] for a in r.get("achievements", [])])


class PaginaTest(unittest.TestCase):
    def test_la_pagina_porta_la_mappa_delle_107_province(self):
        html = app.test_client().get("/quiz/indovina-la-provincia").get_data(as_text=True)
        self.assertIn('id="game-root"', html)
        self.assertIn('id="game-map-frame"', html)
        self.assertEqual(len(set(re.findall(r'class="prov-tile"[^>]*data-key="([a-z\-]+)"', html))), 107)
        self.assertIn("quiz-provincia.js", html)

    def test_titolo_e_descrizione_non_cannibalizzano_la_pagina_a_mappa_che_arriva_dopo(self):
        """"Quiz sulle province" e' la ricerca della pagina a mappa che verra': qui il titolo e la
        descrizione dicono "Indovina la Provincia" e i dati Istat, dentro il budget dei risultati."""
        from html import unescape
        html = app.test_client().get("/quiz/indovina-la-provincia").get_data(as_text=True)
        titolo = unescape(re.search(r"<title>(.*?)</title>", html, re.S).group(1)).strip()
        descrizione = unescape(re.search(r'<meta name="description" content="([^"]*)"', html).group(1)).strip()
        lead = unescape(re.search(r'<p class="page-lead">(.*?)</p>', html, re.S).group(1))
        self.assertIn("Indovina la Provincia dai dati Istat", titolo)
        self.assertLessEqual(len(titolo), 60, titolo)
        self.assertLessEqual(len(descrizione), 155, descrizione)
        for testo in (titolo, descrizione, lead):
            self.assertNotIn("quiz sulle province", testo.lower())

    def test_la_mappa_dichiara_l_attribuzione_dei_confini(self):
        """La stessa riga che il sito usa alla classifica e in home: l'attribuzione e' un obbligo
        della licenza dei confini, e la mappa del gioco li mostra."""
        html = app.test_client().get("/quiz/indovina-la-provincia").get_data(as_text=True)
        riga = "Confini delle province: Istat, via openpolis, "
        self.assertIn(riga, html)
        self.assertIn("https://creativecommons.org/licenses/by/4.0/deed.it", html)
        self.assertLess(html.index('id="prov-map"'), html.index(riga))

    def test_le_rotte_hanno_x_robots_tag_noindex(self):
        cache.delete("rl:prov:ip:127.0.0.1")
        risposta = app.test_client().get("/api/game/provincia/daily?level=province")
        self.assertIn("noindex", risposta.headers.get("X-Robots-Tag", ""))


if __name__ == "__main__":
    unittest.main()
