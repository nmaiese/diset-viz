"""Hub del Quiz, classifica del giorno e traguardi nuovi (W7).

La classifica di oggi ordina per tentativi e poi per ora di arrivo, mostra solo
nickname moderati e niente id, e un anonimo non ci compare. I tre traguardi nuovi
si provano su righe vere di `daily_results` e `daily_scores`, un caso che li
sblocca e uno che no."""

import html
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import accounts, achievements, app, config, game, game_daily, game_provincia, player_stats, profiles, province_profile
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
        self.oggi = game_daily.today_rome()

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


class ClassificaDelGiornoRitirataTest(Base):
    """Con la guess anonima aperta una classifica per tentativi non si puo' rendere
    onesta (chi gioca sceglie il numero del tentativo): la rotta e il modulo non ci sono."""

    def test_la_rotta_non_esiste_piu(self):
        self.risultato("uuid-x", "Presente", 2, "2026-09-30T08:00:00Z")
        risposta = app.test_client().get("/api/game/daily/leaderboard")
        self.assertEqual(risposta.status_code, 404)

    def test_il_modulo_non_esiste_piu(self):
        with self.assertRaises(ImportError):
            __import__("app.classifica_giorno")

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

    def test_la_guess_anonima_non_scrive_niente(self):
        puzzle_id = f"daily:{self.oggi.isoformat()}"
        vincente = game.build_puzzle(puzzle_id)["region_key"]
        app.test_client().post("/api/game/guess", json={"puzzle_id": puzzle_id, "region_key": vincente, "attempt": 1})
        with session_scope() as s:
            self.assertEqual(s.query(DailyScore).count(), 0)


class GuessProvinciaTest(Base):
    def _gioca(self, sub, corretta, livello="province"):
        client = app.test_client()
        payload = client.get(f"/api/game/provincia/daily?level={livello}").get_json()
        mistero = game_provincia.provincia_del_giorno(self.oggi)["key"]
        if corretta:
            chiave = mistero
        else:
            chiave = next(o["key"] for o in game_provincia.opzioni(livello, self.oggi) if o["key"] != mistero)
        cache.delete("rl:prov:ip:127.0.0.1")
        return client.post("/api/game/provincia/guess", json={"token": payload["token"], "province_key": chiave},
                           headers={"Authorization": f"Bearer {_jwt(sub)}"} if sub else {})

    def _riga(self, sub, gioco="provincia"):
        with session_scope() as s:
            return s.get(DailyScore, {"auth_id": sub, "gioco": gioco, "data": self.oggi.isoformat()})

    def test_il_livello_della_regione_scrive_un_punteggio_a_parte_e_non_sblocca_geografo(self):
        # R1 punto 13: la regione svelata dal livello facile e' quella del livello difficile.
        r = self._gioca("uuid-prov-reg", True, "stessa_regione").get_json()
        self.assertTrue(r["correct"])
        self.assertIsNone(self._riga("uuid-prov-reg", "provincia"))
        self.assertEqual(self._riga("uuid-prov-reg", "provincia_regione").punteggio, 1)
        self.assertNotIn("geografo", [a["id"] for a in r["achievements"]])
        self.assertNotIn("geografo", achievements.unlocked_map("uuid-prov-reg"))

    def test_il_livello_della_regione_non_conta_per_il_giro_d_italia(self):
        oggi = self.oggi.isoformat()
        player_stats.record_daily("uuid-giro-liv", oggi, 2, True)
        player_stats.record_daily_score("uuid-giro-liv", "compare", oggi, 7)
        player_stats.record_daily_score("uuid-giro-liv", "order", oggi, 5)
        self._gioca("uuid-giro-liv", True, "stessa_regione")
        self.assertNotIn("giro_ditalia", achievements.unlocked_map("uuid-giro-liv"))

    def test_il_livello_tutta_italia_scrive_provincia(self):
        self._gioca("uuid-prov-ita", True, "province")
        self.assertEqual(self._riga("uuid-prov-ita", "provincia").punteggio, 1)
        self.assertIsNone(self._riga("uuid-prov-ita", "provincia_regione"))

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
                               ("/quiz/ordina", "ordina"),
                               ("/quiz/province-italiane", "province-italiane")):
            html = client.get(percorso).get_data(as_text=True)
            self.assertIn(f"/static/img/og/gioco-{nome}.png", html, percorso)
            self.assertTrue((_ROOT / "app" / "static" / "img" / "og" / f"gioco-{nome}.png").is_file())


class HubPaginaTest(unittest.TestCase):
    def test_le_cinque_card_sono_nel_markup_del_server(self):
        html = app.test_client().get("/quiz").get_data(as_text=True)
        for gioco in ("indovina", "provincia", "compare", "order", "mappa"):
            self.assertIn(f'data-gioco="{gioco}"', html)
        self.assertIn("data-oggi-countdown", html)
        self.assertNotIn("Come funziona il quiz", html)


class NotaDellHubTest(unittest.TestCase):
    def test_la_nota_non_dice_che_le_classifiche_vogliono_un_account(self):
        """Le classifiche accettano un nickname anche senza account (SubmitScoreModal): la frase
        "solo chi ha un account compare nelle classifiche" era un residuo della scheda Oggi."""
        html = app.test_client().get("/quiz").get_data(as_text=True)
        self.assertNotIn("solo chi ha un account compare", html)
        self.assertIn("anche senza account, con un nickname", html)


class TerritorioMioRealeTest(unittest.TestCase):
    """`parseTerritorioMio` su ogni chiave e ogni nome veri: i bottoni "E' la mia" delle 20
    regioni e delle 107 province, resi dal server, scritti come li scrive `v1.js` e riletti dal
    parser. Un valore vero rifiutato vorrebbe dire una funzione che non parte mai per quel
    territorio, senza che niente fallisca."""

    _ATTRIBUTO = re.compile(r'data-([\w-]+)="([^"]*)"')

    def _payload(self, client, livello, chiave):
        html_pagina = client.get(f"/{livello}/{chiave}").get_data(as_text=True)
        bottone = re.search(r"<button[^>]*data-mine-set[^>]*>", html_pagina)
        self.assertIsNotNone(bottone, f"{livello}/{chiave}: nessun bottone \"E' la mia\"")
        a = {k: html.unescape(v) for k, v in self._ATTRIBUTO.findall(bottone.group(0))}
        v = {"level": a["level"], "key": a["key"], "name": a["name"]}
        if "region" in a:
            v["region"], v["regionName"] = a["region"], a["region-name"]
        return v

    @unittest.skipUnless(shutil.which("node"), "serve node per eseguire puri.js")
    def test_tutti_i_territori_veri_passano_il_parser(self):
        client = app.test_client()
        payload = [self._payload(client, "regione", r["region_key"]) for r in profiles.all_regions_index()]
        payload += [self._payload(client, "provincia", p["key"])
                    for lista in province_profile.by_region().values() for p in lista]
        script = (
            "import { parseTerritorioMio } from %s;"
            "const letti = JSON.parse(await new Promise((ok) => { let s = ''; process.stdin.on('data', (d) => s += d);"
            " process.stdin.on('end', () => ok(s)); }));"
            "console.log(JSON.stringify(letti.filter((v) => JSON.stringify(parseTerritorioMio(JSON.stringify(v))) !== JSON.stringify(v))));"
        ) % json.dumps((_ROOT / "frontend" / "src" / "game" / "puri.js").as_uri())
        r = subprocess.run(["node", "--input-type=module", "-e", script], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [], "territori veri che il parser rifiuta o altera")
        self.assertEqual(len([v for v in payload if v["level"] == "regione"]), len(profiles.all_regions_index()))
        self.assertEqual(len([v for v in payload if v["level"] == "provincia"]), len(game_daily.province_pool()))


class ClassificaSenzaSchedaOggiTest(unittest.TestCase):
    """La scheda "Oggi" della classifica se n'e' andata con la sua rotta: niente testo che la
    promette, niente codice che la chiama."""

    def test_la_pagina_non_promette_piu_la_scheda_oggi(self):
        html = app.test_client().get("/quiz/classifica").get_data(as_text=True)
        self.assertNotIn('La scheda "Oggi"', html)
        self.assertNotIn("La scheda &#34;Oggi&#34;", html)
        self.assertNotIn("ora di arrivo", html)
        self.assertIn("Come funziona", html)

    def test_il_frontend_non_chiama_la_rotta_che_non_c_e(self):
        sorgente = (_ROOT / "frontend" / "src" / "game" / "leaderboard.jsx").read_text(encoding="utf-8")
        for traccia in ("daily/leaderboard", "ClassificaOggi", "statoOggi", '"oggi"', "oraArrivo"):
            self.assertNotIn(traccia, sorgente)

    def test_le_due_classifiche_che_restano_rispondono(self):
        client = app.test_client()
        for modo in ("compare", "order"):
            r = client.get(f"/api/game/leaderboard?mode={modo}&period=week&limit=4")
            self.assertEqual(r.status_code, 200, modo)


class SerieDellHubTest(Base):
    """L'hub mostra la serie del profilo (`stats.play_streak`) con il login e quella locale senza."""

    def test_il_profilo_porta_play_streak_con_il_riposo(self):
        oggi = self.oggi
        for giorni_fa in (4, 3, 1, 0):  # un giorno vuoto in mezzo, perdonato
            player_stats.record_daily("uuid-serie", (oggi - timedelta(days=giorni_fa)).isoformat(), 2, True)
        r = app.test_client().get("/api/player/me", headers={"Authorization": f"Bearer {_jwt('uuid-serie')}"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["stats"]["play_streak"], {"current": 4, "max": 4})

    def test_l_hub_legge_play_streak_e_non_la_serie_di_indovina(self):
        sorgente = (_ROOT / "frontend" / "src" / "game" / "hub.jsx").read_text(encoding="utf-8")
        self.assertIn("play_streak", sorgente)
        self.assertNotIn("current_daily_streak", sorgente)

    def test_il_testo_del_traguardo_della_serie_dice_il_vero(self):
        descrizioni = {v["id"]: v["description"] for v in achievements.list_for("nessuno")}
        self.assertIn("7 giorni di fila con la Regione del giorno risolta", descrizioni["daily_streak_7"])
        self.assertIn("almeno una sfida del giorno", descrizioni["fedele"])


if __name__ == "__main__":
    unittest.main()
