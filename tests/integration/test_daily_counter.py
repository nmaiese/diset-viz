"""La misura lato server delle sfide finite (`app/daily_counter.py`, tabella `daily_counter`).

Un contatore aggregato: una riga per `(gioco, data, punteggio)`, niente che identifichi
chi ha giocato. Si scrive una volta per sfida finita, alla risposta finale di un round
legato a un token, e mai solleva: una misura non rompe la partita."""

import importlib.util
import io
import shutil
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app import app, config, daily_counter, game, game_daily, game_provincia, quiz_tokens
from app.cache import cache
from app.db import get_engine, session_scope
from app.models import DailyCounter
from scripts import partite_giocate
from tests.integration.test_game_compare_daily import T0, Base as CompareBase, _vincitore


class ConDatabase(unittest.TestCase):
    def setUp(self):
        self._saved = config.LEADERBOARD_DB
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "c.sqlite3")
        for chiave in ("rl:prov:ip:127.0.0.1", "rl:ans:ip:127.0.0.1"):
            cache.delete(chiave)

    def tearDown(self):
        config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def righe(self):
        with session_scope() as s:
            return {(r.gioco, r.data, r.punteggio): r.conteggio for r in s.query(DailyCounter).all()}


class RecordTest(ConDatabase):
    def test_una_riga_per_gioco_data_punteggio(self):
        self.assertTrue(daily_counter.record("compare", "2026-10-01", 8))
        self.assertEqual(self.righe(), {("compare", "2026-10-01", 8): 1})

    def test_la_stessa_chiave_e_un_upsert_che_somma(self):
        for _ in range(3):
            daily_counter.record("compare", "2026-10-01", 8)
        self.assertEqual(self.righe(), {("compare", "2026-10-01", 8): 3})

    def test_chiavi_diverse_sono_righe_diverse(self):
        daily_counter.record("compare", "2026-10-01", 8)
        daily_counter.record("compare", "2026-10-01", 9)
        daily_counter.record("compare", "2026-10-02", 8)
        daily_counter.record("order", "2026-10-01", 8)
        self.assertEqual(len(self.righe()), 4)
        self.assertTrue(all(n == 1 for n in self.righe().values()))

    def test_il_punteggio_zero_si_conta(self):
        self.assertTrue(daily_counter.record("provincia", "2026-10-01", 0))
        self.assertEqual(self.righe(), {("provincia", "2026-10-01", 0): 1})

    def test_un_input_non_valido_non_scrive_e_non_solleva(self):
        for gioco, data, punteggio in (
            ("", "2026-10-01", 1), (None, "2026-10-01", 1), ("Compare", "2026-10-01", 1),
            ("compare; drop", "2026-10-01", 1), ("compare", "ieri", 1), ("compare", "2026-13-40", 1),
            ("compare", None, 1), ("compare", "2026-10-01", -1), ("compare", "2026-10-01", None),
            ("compare", "2026-10-01", "8"), ("compare", "2026-10-01", 7.5), ("compare", "2026-10-01", True),
            ("compare", "2026-10-01", 10**6),
        ):
            with self.subTest(gioco=gioco, data=data, punteggio=punteggio):
                self.assertFalse(daily_counter.record(gioco, data, punteggio))
        self.assertEqual(self.righe(), {})

    def test_un_errore_del_database_finisce_nel_log_e_non_solleva(self):
        with mock.patch.object(daily_counter, "session_scope", side_effect=RuntimeError("db giu'")):
            with self.assertLogs("app.daily_counter", level="ERROR"):
                self.assertFalse(daily_counter.record("compare", "2026-10-01", 8))

    def test_l_incremento_e_atomico_fra_thread(self):
        daily_counter.record("compare", "2026-10-01", 5)  # la tabella esiste gia' per tutti

        def gira():
            for _ in range(10):
                daily_counter.record("compare", "2026-10-01", 5)

        fili = [threading.Thread(target=gira) for _ in range(8)]
        for f in fili:
            f.start()
        for f in fili:
            f.join()
        self.assertEqual(self.righe(), {("compare", "2026-10-01", 5): 81})

    def test_la_tabella_non_ha_nessun_identificativo(self):
        daily_counter.record("compare", "2026-10-01", 5)
        colonne = {c["name"] for c in inspect(get_engine()).get_columns("daily_counter")}
        self.assertEqual(colonne, {"gioco", "data", "punteggio", "conteggio"})


class MigrazioneTest(unittest.TestCase):
    """La 0011 crea la stessa tabella del modello: su Postgres la possiede Alembic, su
    SQLite il modello, e i due non devono divergere."""

    def test_la_migrazione_crea_la_tabella_del_modello(self):
        percorso = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0011_daily_counter.py"
        spec = importlib.util.spec_from_file_location("migrazione_0011", percorso)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        self.assertEqual(modulo.down_revision, "0010_quiz_monouso_punteggi")

        engine = create_engine("sqlite://")
        with engine.begin() as conn:
            with mock.patch.object(modulo, "op", Operations(MigrationContext.configure(conn))):
                modulo.upgrade()
            ispettore = inspect(conn)
            colonne = {c["name"]: c for c in ispettore.get_columns("daily_counter")}
            chiave = ispettore.get_pk_constraint("daily_counter")["constrained_columns"]
        self.assertEqual(set(colonne), {c.name for c in DailyCounter.__table__.columns})
        self.assertEqual(sorted(chiave), sorted(c.name for c in DailyCounter.__table__.primary_key.columns))
        self.assertFalse(colonne["conteggio"]["nullable"])


class TotalsTest(ConDatabase):
    def setUp(self):
        super().setUp()
        for gioco, data, punteggio, volte in (
            ("compare", "2026-10-01", 8, 2), ("compare", "2026-10-01", 6, 1),
            ("order", "2026-10-01", 5, 4), ("compare", "2026-10-03", 10, 1),
        ):
            for _ in range(volte):
                daily_counter.record(gioco, data, punteggio)

    def test_somma_le_partite_per_giorno_e_gioco(self):
        voci = daily_counter.totals()
        self.assertEqual([(v["data"], v["gioco"], v["partite"]) for v in voci], [
            ("2026-10-01", "compare", 3), ("2026-10-01", "order", 4), ("2026-10-03", "compare", 1)])
        self.assertEqual(voci[0]["punteggi"], {8: 2, 6: 1})

    def test_filtra_per_gioco_e_per_finestra_inclusa(self):
        self.assertEqual([v["partite"] for v in daily_counter.totals("order")], [4])
        self.assertEqual([v["data"] for v in daily_counter.totals(since="2026-10-02")], ["2026-10-03"])
        self.assertEqual([v["data"] for v in daily_counter.totals(until="2026-10-01")], ["2026-10-01"] * 2)
        self.assertEqual(daily_counter.totals(since="2026-10-03", until="2026-10-03")[0]["partite"], 1)

    def test_senza_partite_e_vuoto(self):
        self.assertEqual(daily_counter.totals("provincia"), [])


class ScriptTest(ConDatabase):
    def test_stampa_per_gioco_e_giorno(self):
        daily_counter.record("compare", "2026-10-01", 8)
        daily_counter.record("compare", "2026-10-01", 8)
        daily_counter.record("order", "2026-10-01", 5)
        fuori = io.StringIO()
        with redirect_stdout(fuori):
            self.assertEqual(partite_giocate.main(["--da", "2026-10-01", "--a", "2026-10-01", "--punteggi"]), 0)
        testo = fuori.getvalue()
        self.assertRegex(testo, r"2026-10-01\s+compare\s+2\s+8:2")
        self.assertRegex(testo, r"2026-10-01\s+order\s+1\s+5:1")
        self.assertRegex(testo, r"compare\s+2\n")

    def test_senza_partite_lo_dice(self):
        fuori = io.StringIO()
        with redirect_stdout(fuori):
            partite_giocate.main(["--da", "2026-10-01", "--a", "2026-10-02"])
        self.assertIn("Nessuna partita finita", fuori.getvalue())


class RotteTest(CompareBase):
    """Si conta alla risposta finale e solo li': mai prima, mai due volte."""

    def righe(self):
        with session_scope() as s:
            return {(r.gioco, r.data, r.punteggio): r.conteggio for r in s.query(DailyCounter).all()}

    def _gioca_con_calma(self, sessione, livello, giuste=10, passo=2):
        """Come `_gioca`, ma con `passo` secondi per risposta: dieci risposte in venti
        secondi sono una partita plausibile (`quiz_tokens.is_plausible`, 1,5 s a round),
        dieci in dieci no."""
        token, orario, risposte = sessione["token"], T0, []
        for indice, coppia in enumerate(sessione["questions"]):
            if indice < giuste:
                scelta, orario = _vincitore(livello, coppia), orario + passo
            else:
                scelta, orario = "timeout", orario + 11
            risposta = self._risponde(sessione, indice, scelta, token=token, now=orario)
            self.assertEqual(risposta.status_code, 200, indice)
            risposte.append(risposta)
            token = risposta.get_json()["token"]
            if indice < len(sessione["questions"]) - 1:
                token = self._avanti(sessione, indice, token, now=orario).get_json()["token"]
        return risposte

    def test_chi_e_maggiore_conta_una_volta_all_ultima_risposta(self):
        sessione = self._sessione("regioni")
        risposte = self._gioca_con_calma(sessione, "regioni", giuste=10)
        ultimo = risposte[-1].get_json()
        self.assertTrue(ultimo["finished"])
        data = ultimo["summary"]["date"]
        self.assertEqual(self.righe(), {("compare", data, 10): 1})

    def test_chi_e_maggiore_non_conta_prima_della_fine(self):
        sessione = self._sessione("regioni")
        self._gioca_con_calma(sessione, "regioni", giuste=10)
        with session_scope() as s:
            s.query(DailyCounter).delete()
        sessione = self._sessione("regioni")
        self._risponde(sessione, 0, "region_a", now=T0 + 2)
        self.assertEqual(self.righe(), {})

    def test_il_punteggio_e_quello_della_risposta_finale(self):
        sessione = self._sessione("regioni")
        risposte = self._gioca_con_calma(sessione, "regioni", giuste=7)
        summary = risposte[-1].get_json()["summary"]
        self.assertEqual(summary["score"]["correct"], 7)
        self.assertEqual(self.righe(), {("compare", summary["date"], 7): 1})

    def test_chi_e_maggiore_senza_timer_non_conta(self):
        """Basso (d): l'allenamento non e' una sfida finita."""
        sessione = self._sessione("regioni", timer=0)
        risposte = self._gioca_con_calma(sessione, "regioni", giuste=10)
        self.assertTrue(risposte[-1].get_json()["finished"])
        self.assertEqual(self.righe(), {})

    def test_chi_e_maggiore_non_plausibile_non_conta(self):
        """Dieci risposte in dieci secondi non sono di una persona."""
        sessione = self._sessione("regioni")
        risposte = self._gioca_con_calma(sessione, "regioni", giuste=10, passo=1)
        self.assertTrue(risposte[-1].get_json()["finished"])
        self.assertEqual(self.righe(), {})

    def test_un_guasto_del_contatore_non_rompe_la_risposta(self):
        sessione = self._sessione("regioni")
        with mock.patch.object(daily_counter, "record", side_effect=RuntimeError("giu'")):
            with self.assertLogs(app.logger, level="ERROR"):
                risposte = self._gioca_con_calma(sessione, "regioni", giuste=10)
        self.assertEqual(risposte[-1].status_code, 200)
        self.assertTrue(risposte[-1].get_json()["finished"])

    def test_ordina_conta_la_risposta_finale_e_non_il_rifiuto_di_un_doppione(self):
        client = app.test_client()
        with mock.patch.object(quiz_tokens, "_now", return_value=T0):
            sessione = client.get("/api/game/order/daily/session?level=regioni").get_json()
        corpo = {"token": sessione["token"], "level": "regioni", "region_keys": [t["key"] for t in sessione["territories"]]}
        with mock.patch.object(quiz_tokens, "_now", return_value=T0 + 10):
            prima = client.post("/api/game/order/daily/answer", json=corpo)
            self.assertEqual(prima.status_code, 200)
            oggi = game_daily.today_rome().isoformat()
            self.assertEqual(self.righe(), {("order", oggi, prima.get_json()["score"]): 1})
            self.assertEqual(client.post("/api/game/order/daily/answer", json=corpo).status_code, 409)
        self.assertEqual(sum(self.righe().values()), 1)

    def test_ordina_non_plausibile_non_conta(self):
        """Cinque territori ordinati nello stesso istante dell'apertura: uno script."""
        client = app.test_client()
        with mock.patch.object(quiz_tokens, "_now", return_value=T0):
            sessione = client.get("/api/game/order/daily/session?level=regioni").get_json()
            r = client.post("/api/game/order/daily/answer", json={
                "token": sessione["token"], "level": "regioni",
                "region_keys": [t["key"] for t in sessione["territories"]]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.righe(), {})

    def test_ordina_non_conta_una_risposta_rifiutata(self):
        client = app.test_client()
        sessione = client.get("/api/game/order/daily/session?level=regioni").get_json()
        chiavi = [t["key"] for t in sessione["territories"]][:4]
        r = client.post("/api/game/order/daily/answer", json={"token": sessione["token"], "level": "regioni", "region_keys": chiavi})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.righe(), {})

    def _guess_provincia(self, livello, corretta):
        client = app.test_client()
        oggi = game_daily.today_rome()
        payload = client.get(f"/api/game/provincia/daily?level={livello}").get_json()
        mistero = game_provincia.daily_province(oggi)["key"]
        chiave = mistero if corretta else next(
            o["key"] for o in game_provincia.options(livello, oggi) if o["key"] != mistero)
        cache.delete("rl:prov:ip:127.0.0.1")
        return client.post("/api/game/provincia/guess", json={"token": payload["token"], "province_key": chiave})

    def test_provincia_conta_alla_fine_col_suo_livello(self):
        self.assertTrue(self._guess_provincia("province", True).get_json()["finished"])
        self.assertTrue(self._guess_provincia("stessa_regione", True).get_json()["finished"])
        oggi = game_daily.today_rome().isoformat()
        self.assertEqual(self.righe(), {("provincia", oggi, 1): 1, ("provincia_regione", oggi, 1): 1})

    def test_provincia_non_si_conta_due_volte_se_si_rimanda_la_richiesta_finale(self):
        client = app.test_client()
        oggi = game_daily.today_rome()
        payload = client.get("/api/game/provincia/daily?level=province").get_json()
        corpo = {"token": payload["token"], "province_key": game_provincia.daily_province(oggi)["key"]}
        cache.delete("rl:prov:ip:127.0.0.1")
        prima = client.post("/api/game/provincia/guess", json=corpo)
        self.assertTrue(prima.get_json()["finished"])
        for _ in range(3):
            cache.delete("rl:prov:ip:127.0.0.1")
            client.post("/api/game/provincia/guess", json=corpo)
        self.assertEqual(self.righe(), {("provincia", oggi.isoformat(), 1): 1})

    def test_provincia_non_si_conta_due_volte_con_il_token_dopo_la_fine(self):
        client = app.test_client()
        oggi = game_daily.today_rome()
        payload = client.get("/api/game/provincia/daily?level=province").get_json()
        chiave = game_provincia.daily_province(oggi)["key"]
        cache.delete("rl:prov:ip:127.0.0.1")
        prima = client.post("/api/game/provincia/guess", json={"token": payload["token"], "province_key": chiave}).get_json()
        self.assertTrue(prima["finished"])
        for _ in range(3):
            cache.delete("rl:prov:ip:127.0.0.1")
            client.post("/api/game/provincia/guess", json={"token": prima["token"], "province_key": chiave})
        self.assertEqual(self.righe(), {("provincia", oggi.isoformat(), 1): 1})

    def test_provincia_non_conta_un_tentativo_sbagliato_che_non_chiude(self):
        r = self._guess_provincia("province", False).get_json()
        self.assertFalse(r["finished"])
        self.assertEqual(self.righe(), {})

    def test_indovina_la_regione_non_entra(self):
        puzzle_id = f"daily:{game_daily.today_rome().isoformat()}"
        vincente = game.build_puzzle(puzzle_id)["region_key"]
        app.test_client().post("/api/game/guess", json={"puzzle_id": puzzle_id, "region_key": vincente, "attempt": 1})
        self.assertEqual(self.righe(), {})


if __name__ == "__main__":
    unittest.main()
