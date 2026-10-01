"""Il fatto "Da portarti via" dentro le due sfide del giorno, e su tutto il pool.

Due cose. Il **payload**: client Flask, sfida di una data fissa, il campo `fact`
c'e' a fine partita e non prima (Ordina: `fact` in cima alla risposta, che e' la
fine; Chi e' maggiore: `summary.fact`, e il `summary` esiste solo all'ultima
risposta). Il **ciclo**: ogni indicatore giocabile del pool vero, a ogni livello,
per Ordina e per Chi e' maggiore, e la frase che esce non ha mai un carattere
vietato, un "n.d." o piu' di 260 caratteri."""

import re
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from app import app, config, game_compare, game_daily, game_facts, quiz_tokens
from app.design import numfmt
from tests.integration.test_game_compare_daily import Base, T0, _vincitore

GIORNO = date(2026, 9, 30)
LIVELLI = ("regioni", "stessa_regione", "province")
# Il testo che il client scarta: lo dice `fattoPresentabile` in frontend/src/game/puri.js.
VIETATI = ("n.d.", "NaN", "—", "–", ";", "…")


def _controlla_frase(test, testo, contesto=""):
    test.assertIsInstance(testo, str, contesto)
    test.assertLessEqual(len(testo), 260, f"{contesto}: {testo}")
    for vietato in VIETATI:
        test.assertNotIn(vietato, testo, f"{contesto}: {testo}")
    test.assertTrue(testo.endswith("."), f"{contesto}: {testo}")
    # un solo punto finale: gli altri sono separatori delle migliaia ("1.234")
    test.assertEqual(len(re.findall(r"\.(?!\d)", testo)), 1, f"{contesto}: {testo}")


def _cifre(testo):
    """Le due cifre della frase ("... A ha 74,3%, B ha 1.234 euro"), come
    (valore, decimali scritti)."""
    cifre = []
    for scritta in re.findall(r" ha (-?[\d.]+(?:,\d+)?)", testo):
        intera, _, decimali = scritta.partition(",")
        cifre.append((float(intera.replace(".", "") + ("." + decimali if decimali else "")), len(decimali)))
    return cifre


def _controlla_cifre(test, testo, valori, contesto=""):
    """Le due cifre della frase sono due dei valori veri, arrotondati come scritti."""
    cifre = _cifre(testo)
    test.assertEqual(len(cifre), 2, f"{contesto}: {testo}")
    usati = []
    for cifra, decimali in cifre:
        tolleranza = 0.5 * 10 ** -decimali + 1e-9
        vicini = [v for v in valori if abs(v - cifra) <= tolleranza and v not in usati]
        test.assertTrue(vicini, f"{contesto}: {cifra} non e' fra {valori}: {testo}")
        usati.append(vicini[0])


def _coppia_del_fatto(coppie, testo):
    """La coppia di cui parla la frase: quella con il nome dell'indicatore fra le
    virgolette basse e il suo anno."""
    trovate = [c for c in coppie if f"«{numfmt.lower_first(c['indicator']['name'])}» ({c['indicator']['year']})" in testo]
    return trovate[0] if len(trovate) == 1 else None


def _scarto(coppia, valuta):
    esito = valuta(coppia, "region_a")
    a, b = esito["a"]["value"], esito["b"]["value"]
    return abs(a - b) / max(abs(a), abs(b)), (a, b)


class OrdinaPayloadTest(unittest.TestCase):
    def setUp(self):
        self._saved = (config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB)
        config.SUPABASE_JWT_SECRET = "test-jwt-secret"
        config.SUPABASE_URL = ""
        self._tmp = tempfile.mkdtemp()
        config.LEADERBOARD_DB = str(Path(self._tmp) / "s.sqlite3")
        self.client = app.test_client()
        self._giorno = mock.patch.object(game_daily, "today_rome", return_value=GIORNO)
        self._giorno.start()
        self.addCleanup(self._giorno.stop)

    def tearDown(self):
        config.SUPABASE_JWT_SECRET, config.SUPABASE_URL, config.LEADERBOARD_DB = self._saved
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _gioca(self, livello, ordine=None):
        """(sessione, risposta): `ordine` e' una funzione dalle chiavi del giocatore
        alle chiavi nell'ordine scelto."""
        sessione = self.client.get(f"/api/game/order/daily/session?level={livello}").get_json()
        chiavi = [t["key"] for t in sessione["territories"]]
        if ordine is not None:
            chiavi = ordine(chiavi, sessione)
        risposta = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "level": livello, "region_keys": chiavi})
        return sessione, risposta

    def test_the_session_has_no_fact_before_the_end(self):
        for livello in LIVELLI:
            with self.subTest(livello=livello):
                sessione = self.client.get(f"/api/game/order/daily/session?level={livello}").get_json()
                self.assertNotIn("fact", sessione)
                self.assertNotIn("fatto", sessione)

    def test_the_final_answer_has_the_fact(self):
        sessione, risposta = self._gioca("regioni")
        self.assertEqual(risposta.status_code, 200)
        corpo = risposta.get_json()
        self.assertIn("fact", corpo)
        _controlla_frase(self, corpo["fact"], "regioni")
        # il fatto parla dell'indicatore e dell'anno della sfida
        self.assertIn(str(sessione["indicator"]["year"]), corpo["fact"])
        self.assertIn(numfmt.lower_first(sessione["indicator"]["name"]), corpo["fact"])
        # le cifre della frase sono i `value` dello stesso payload
        _controlla_cifre(self, corpo["fact"], [p["value"] for p in corpo["positions"]], "regioni")

    def test_the_fact_on_a_mistake_starts_from_the_players_error(self):
        _, risposta = self._gioca("regioni", ordine=lambda chiavi, s: chiavi)
        corpo = risposta.get_json()
        if corpo["score"] == corpo["total"]:
            self.skipTest("l'ordine di partenza e' gia' quello giusto")
        self.assertTrue(corpo["fact"].startswith("Hai messo "), corpo["fact"])

    def test_the_fact_for_a_perfect_order_starts_from_the_widest_case(self):
        sessione = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        chiavi = [t["key"] for t in sessione["territories"]]
        # una risposta a un token buono brucia il round: ne serve uno nuovo per quella giusta
        corretto = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "level": "regioni", "region_keys": chiavi}).get_json()
        ordine_giusto = [r["region_key"] for r in corretto["correct_order"]]
        sessione = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        corpo = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "level": "regioni", "region_keys": ordine_giusto}).get_json()
        self.assertEqual(corpo["score"], corpo["total"])
        self.assertTrue(corpo["fact"].startswith("Tutto al posto giusto"), corpo["fact"])
        _controlla_frase(self, corpo["fact"])

    def test_a_refused_answer_has_no_fact(self):
        sessione = self.client.get("/api/game/order/daily/session?level=regioni").get_json()
        chiavi = [t["key"] for t in sessione["territories"]]
        rotta = self.client.post("/api/game/order/daily/answer", json={
            "token": "rotto", "level": "regioni", "region_keys": chiavi})
        self.assertEqual(rotta.status_code, 400)
        self.assertNotIn("fact", rotta.get_json())
        troppo_corta = self.client.post("/api/game/order/daily/answer", json={
            "token": sessione["token"], "level": "regioni", "region_keys": chiavi[:2]})
        self.assertEqual(troppo_corta.status_code, 400)
        self.assertNotIn("fact", troppo_corta.get_json())

    def test_every_level_gives_a_valid_fact_or_none(self):
        trovati = 0
        for livello in LIVELLI:
            with self.subTest(livello=livello):
                _, risposta = self._gioca(livello)
                self.assertEqual(risposta.status_code, 200)
                fatto = risposta.get_json().get("fact")
                if fatto is not None:
                    _controlla_frase(self, fatto, livello)
                    trovati += 1
        self.assertGreaterEqual(trovati, 2)


class CompareFattoTest(Base):
    def setUp(self):
        super().setUp()
        self._giorno = mock.patch.object(game_compare, "today_rome", return_value=GIORNO)
        self._giorno.start()
        self.addCleanup(self._giorno.stop)

    def _partita(self, livello, sbagliate=(), scadute=()):
        """Le dieci risposte: giuste, tranne le `sbagliate` (la scelta vera ma sbagliata)
        e le `scadute` (il tempo scaduto). Ritorna (sessione, risposte)."""
        sessione = self._sessione(livello)
        token, orario, risposte = sessione["token"], T0, []
        for indice, coppia in enumerate(sessione["questions"]):
            vincitore = _vincitore(livello, coppia)
            if indice in scadute:
                scelta, orario = "timeout", orario + 11
            elif indice in sbagliate:
                scelta, orario = ("region_b" if vincitore == "region_a" else "region_a"), orario + 1
            else:
                scelta, orario = vincitore, orario + 1
            risposta = self._risponde(sessione, indice, scelta, token=token, now=orario)
            self.assertEqual(risposta.status_code, 200, indice)
            risposte.append(risposta.get_json())
            token = risposte[-1]["token"]
            if indice < len(sessione["questions"]) - 1:
                token = self._avanti(sessione, indice, token, now=orario).get_json()["token"]
        return sessione, risposte

    def test_no_fact_before_the_last_answer(self):
        for livello in LIVELLI:
            with self.subTest(livello=livello):
                sessione, risposte = self._partita(livello, sbagliate=(2,))
                self.assertNotIn("fact", sessione)
                for corpo in risposte[:-1]:
                    self.assertNotIn("summary", corpo)
                    self.assertNotIn("fact", corpo)
                    self.assertNotIn("fatto", corpo)

    def _vera(self, sessione, risposte, testo, livello="regioni"):
        """La frase di una partita senza errori dice il vero: le cifre sono i valori
        della coppia di cui parla (letti dalle risposte della stessa partita), e "la
        coppia piu' distante" e' davvero quella con lo scarto relativo piu' ampio."""
        coppia = _coppia_del_fatto(sessione["questions"], testo)
        self.assertIsNotNone(coppia, testo)
        risposta = risposte[coppia["index"]]
        _controlla_cifre(self, testo, [risposta["a"]["value"], risposta["b"]["value"]], livello)
        if testo.startswith("La coppia più distante:"):
            scarti = [abs(r["a"]["value"] - r["b"]["value"]) / max(abs(r["a"]["value"]), abs(r["b"]["value"]))
                      for r in risposte]
            a, b = risposta["a"]["value"], risposta["b"]["value"]
            self.assertEqual(abs(a - b) / max(abs(a), abs(b)), max(scarti), testo)
            self.assertFalse(any(r["a"]["value"] * r["b"]["value"] < 0 for r in risposte), testo)
        else:
            self.assertTrue(testo.startswith("Una coppia lontana:"), testo)

    def test_the_last_answer_has_the_fact_in_the_summary(self):
        sessione, risposte = self._partita("regioni")
        riassunto = risposte[-1]["summary"]
        self.assertIn("fact", riassunto)
        _controlla_frase(self, riassunto["fact"], "regioni")
        self._vera(sessione, risposte, riassunto["fact"])
        self.assertTrue(riassunto["fact_path"].startswith("/"), riassunto["fact_path"])

    def test_the_first_mistake_is_the_one_the_fact_talks_about(self):
        sessione, risposte = self._partita("regioni", sbagliate=(5, 3))
        fatto = risposte[-1]["summary"]["fact"]
        coppia = sessione["questions"][3]
        _controlla_frase(self, fatto, "regioni")
        self.assertTrue(fatto.startswith("Hai messo "), fatto)
        self.assertIn(numfmt.lower_first(coppia["indicator"]["name"]), fatto)
        self.assertIn(str(coppia["indicator"]["year"]), fatto)
        _controlla_cifre(self, fatto, [risposte[3]["a"]["value"], risposte[3]["b"]["value"]], "regioni")

    def test_the_mistake_lives_in_the_signed_token_not_in_the_body(self):
        _, risposte = self._partita("regioni", sbagliate=(3,))
        self.assertNotIn("fact", risposte[3])
        stato = quiz_tokens.load_state(risposte[3]["token"], game_compare.MODE)
        self.assertEqual(stato[game_compare.SCORE_KEY]["e"], 3)
        # le risposte dopo, anche giuste, tengono la prima
        stato = quiz_tokens.load_state(risposte[8]["token"], game_compare.MODE)
        self.assertEqual(stato[game_compare.SCORE_KEY]["e"], 3)

    def test_a_perfect_game_never_writes_a_mistake_into_the_token(self):
        _, risposte = self._partita("regioni")
        stato = quiz_tokens.load_state(risposte[5]["token"], game_compare.MODE)
        self.assertNotIn("e", stato[game_compare.SCORE_KEY])

    def test_only_timeouts_fall_back_to_the_widest_pair(self):
        sessione, risposte = self._partita("regioni", scadute=(1, 4))
        fatto = risposte[-1]["summary"]["fact"]
        self.assertFalse(fatto.startswith("Hai messo "), fatto)
        self._vera(sessione, risposte, fatto)
        stato = quiz_tokens.load_state(risposte[4]["token"], game_compare.MODE)
        self.assertNotIn("e", stato[game_compare.SCORE_KEY])

    def test_the_score_travels_as_before(self):
        _, risposte = self._partita("regioni", sbagliate=(3,))
        self.assertEqual(risposte[-1]["score"], {"correct": 9, "total": 10})
        self.assertEqual(risposte[-1]["summary"]["score"], {"correct": 9, "total": 10})

    def test_province_levels_give_a_valid_fact(self):
        for livello in ("stessa_regione", "province"):
            with self.subTest(livello=livello):
                _, risposte = self._partita(livello, sbagliate=(0,))
                fatto = risposte[-1]["summary"].get("fact")
                self.assertIsNotNone(fatto, livello)
                _controlla_frase(self, fatto, livello)


class CicloSulPoolTest(unittest.TestCase):
    """Ogni indicatore giocabile, a ogni livello, con righe vere e il piazzamento vero."""

    @staticmethod
    def _cinque(righe):
        ordinate = sorted((r for r in righe if r["value"] is not None), key=lambda r: -r["value"])
        n = len(ordinate)
        return [ordinate[int(i * (n - 1) / 4)] for i in range(5)]

    def test_order_sentences_over_the_whole_pool(self):
        prodotte = totali = 0
        for ind in game_daily.game_indicators():
            for flag, ambito, livello in (("regione", "regioni", "regioni"), ("provincia", "province", "province")):
                if not ind[flag]:
                    continue
                dato = game_daily._indicator_rows(ind, ambito)
                if dato is None:
                    continue
                anno, righe = dato
                scelti = self._cinque(righe)
                indicatore = game_daily._indicator_fields(ind, anno)
                giusto = [{"region": r["name"], "region_key": r["key"], "value": r["value"]} for r in scelti]
                rovesciato = [{**r, "guessed_position": i + 1} for i, r in enumerate(reversed(giusto))]
                esatto = [{**r, "guessed_position": i + 1} for i, r in enumerate(giusto)]
                for caso, mosse in (("errore", rovesciato), ("perfetto", esatto)):
                    totali += 1
                    fatto = game_facts.order_fact(livello, indicatore, mosse, giusto)
                    if fatto is not None:
                        prodotte += 1
                        _controlla_frase(self, fatto, f"ordina {ind['id']} {livello} {caso}")
        self.assertGreater(totali, 150)
        self.assertGreaterEqual(prodotte / totali, 0.9)

    def test_compare_sentences_over_the_whole_pool(self):
        prodotte = totali = 0
        for ind in game_daily.game_indicators():
            for flag, ambito, livello in (("regione", "regioni", "regioni"), ("provincia", "province", "province")):
                if not ind[flag]:
                    continue
                dato = game_daily._indicator_rows(ind, ambito)
                if dato is None:
                    continue
                anno, righe = dato
                scelti = self._cinque(righe)
                indicatore = game_daily._indicator_fields(ind, anno)
                coppie = [{"indicator": indicatore,
                           "a": {"key": a["key"], "name": a["name"], "region": a["region"]},
                           "b": {"key": b["key"], "name": b["name"], "region": b["region"]}}
                          for a, b in zip(scelti, scelti[1:])]
                valori = {r["key"]: r["value"] for r in scelti}

                def valuta(coppia, scelta, valori=valori):
                    return {"indicator": {"path": "/x"},
                            "a": {**coppia["a"], "value": valori[coppia["a"]["key"]]},
                            "b": {**coppia["b"], "value": valori[coppia["b"]["key"]]}}

                for errore in (None, 0, 2):
                    totali += 1
                    fatto = game_facts.compare_fact(livello, coppie, errore, valuta)
                    if fatto is not None:
                        prodotte += 1
                        _controlla_frase(self, fatto["fact"], f"compare {ind['id']} {livello} {errore}")
        self.assertGreater(totali, 200)
        self.assertGreaterEqual(prodotte / totali, 0.9)

    def test_the_real_daily_puzzles_of_two_weeks(self):
        """Le sfide vere dei prossimi quattordici giorni, con i valori che la risposta
        porterebbe: Ordina come la vista, Chi e' maggiore con `_evaluate` vero. La
        frase c'e' per la maggioranza delle partite e le sue cifre sono i valori veri
        della coppia (o della cinquina) di cui parla."""
        partite = {"compare_errore": 0, "compare_perfetta": 0, "ordina": 0}
        trovate = dict.fromkeys(partite, 0)
        for giorno_n in range(14):
            giorno = date.fromordinal(GIORNO.toordinal() + giorno_n)
            for livello in LIVELLI:
                contesto = f"{giorno} {livello}"
                coppie = game_daily.daily_compare(giorno, livello)["pairs"]

                def valuta(c, s, livello=livello):
                    return game_compare._evaluate(c, livello, s)

                for caso, errore in (("compare_errore", 0), ("compare_perfetta", None)):
                    partite[caso] += 1
                    fatto = game_facts.compare_fact(livello, coppie, errore, valuta)
                    if fatto is None:
                        continue
                    trovate[caso] += 1
                    testo = fatto["fact"]
                    _controlla_frase(self, testo, f"compare {contesto}")
                    coppia = _coppia_del_fatto(coppie, testo)
                    self.assertIsNotNone(coppia, testo)
                    scarto, valori = _scarto(coppia, valuta)
                    _controlla_cifre(self, testo, list(valori), f"compare {contesto}")
                    if testo.startswith("Hai messo "):
                        self.assertIs(coppia, coppie[0], testo)
                    if testo.startswith("La coppia più distante:"):
                        scarti = [_scarto(c, valuta) for c in coppie]
                        self.assertFalse(any(a * b < 0 for _, (a, b) in scarti), testo)
                        self.assertEqual(scarto, max(s for s, _ in scarti), testo)
                partite["ordina"] += 1
                puzzle = game_daily.daily_order(giorno, livello)
                ambito = "regioni" if livello == "regioni" else "province"
                anno, righe = game_daily._indicator_rows(puzzle["indicator"], ambito)
                valori = {r["key"]: r["value"] for r in righe}
                mosse = [{"region": t["name"], "region_key": t["key"], "value": valori[t["key"]],
                          "guessed_position": i + 1} for i, t in enumerate(puzzle["territories"])]
                giusto = sorted(mosse, key=lambda r: -r["value"])
                fatto = game_facts.order_fact(livello, puzzle["indicator"], mosse, giusto)
                if fatto is not None:
                    trovate["ordina"] += 1
                    _controlla_frase(self, fatto, f"ordina {contesto}")
                    _controlla_cifre(self, fatto, [m["value"] for m in mosse], f"ordina {contesto}")
        for caso in partite:
            with self.subTest(caso=caso):
                self.assertGreater(trovate[caso], partite[caso] / 2, trovate)


class FattiVeriTest(unittest.TestCase):
    """M8 della revisione finale, sui dati veri e senza mock del piazzamento."""

    @staticmethod
    def _indicatore(ind_id, ambito="regioni"):
        anno, righe = game_daily._indicator_rows({"id": ind_id}, ambito)
        return {"id": ind_id, "year": anno}, {r["key"]: r["value"] for r in righe}

    def test_the_exact_place_is_the_real_ranking(self):
        """Speranza di vita (910): non campionaria, direzione curata (piu' alto e'
        meglio). Il piazzamento di ogni regione e' quello di un ordinamento dei valori
        fatto qui, a pari merito come la graduatoria del sito."""
        self.assertFalse(game_facts.is_sample_survey("910", "regioni"))
        indicatore, valori = self._indicatore("910")
        self.assertEqual(len(valori), 20)
        for chiave, valore in valori.items():
            posto = 1 + sum(1 for v in valori.values() if v > valore)
            with self.subTest(regione=chiave):
                self.assertEqual(game_facts.placement("regioni", indicatore, chiave), f"{posto}ª su 20")

    def test_sample_surveys_never_give_the_exact_place(self):
        """Multiscopo (426), Forze di lavoro (57) e ICT nelle imprese (72): solo la
        fascia, e solo per chi sta davvero fra le ultime cinque."""
        for ind_id in ("426", "57", "72"):
            indicatore, valori = self._indicatore(ind_id)
            direzione = game_facts.direction(ind_id, "regioni")
            self.assertIsNotNone(direzione, ind_id)
            fascia = 0
            for chiave, valore in valori.items():
                meglio = (lambda v: v > valore) if direzione == "higher_better" else (lambda v: v < valore)
                posto = 1 + sum(1 for v in valori.values() if meglio(v))
                testo = game_facts.placement("regioni", indicatore, chiave)
                with self.subTest(id=ind_id, regione=chiave):
                    self.assertEqual(testo, "fra le ultime cinque" if posto >= 16 else None)
                fascia += testo is not None
            self.assertGreaterEqual(fascia, 5, ind_id)

    def test_same_region_level_writes_no_place(self):
        """Al livello `stessa_regione` il piazzamento si calcolava sulle 107 province
        e si leggeva "della regione": non si scrive."""
        provinciali = [i for i in game_daily.game_indicators()
                       if i["provincia"] and game_facts.direction(i["id"], "province")]
        self.assertTrue(provinciali)
        provato = 0
        for ind in provinciali:
            indicatore, valori = self._indicatore(ind["id"], "province")
            for chiave in valori:
                if game_facts.placement("province", indicatore, chiave) is None:
                    continue
                provato += 1
                with self.subTest(id=ind["id"], provincia=chiave):
                    self.assertIsNone(game_facts.placement("stessa_regione", indicatore, chiave))
        self.assertGreater(provato, 0)

    def test_the_two_names_say_what_the_series_counts(self):
        """`72` conta gli addetti delle imprese, `426` le persone di 6 anni e piu':
        il nome del gioco dice lo stesso soggetto della definizione Istat."""
        nomi = {i["id"]: i["name"] for i in game_daily.game_indicators()}
        definizioni = {}
        with open("app/static/data/Assoluti_Regione.csv", encoding="utf-8") as righe:
            for riga in righe:
                campi = riga.split(";")
                if campi[0] in ("72", "426") and campi[0] not in definizioni:
                    definizioni[campi[0]] = campi[6]
        self.assertIn("Addetti", definizioni["72"])
        self.assertTrue(nomi["72"].startswith("Addetti"), nomi["72"])
        self.assertIn("Persone di 6 anni e più", definizioni["426"])
        self.assertTrue(nomi["426"].startswith("Persone di 6 anni e più"), nomi["426"])

    def test_the_csv_sample_column_is_read(self):
        righe = game_daily.game_indicators()
        self.assertTrue(all(isinstance(r["sample_survey"], bool) for r in righe))
        per_id = {r["id"]: r["sample_survey"] for r in righe}
        for ind_id in ("426", "57", "72"):
            self.assertTrue(per_id[ind_id], ind_id)
        # i prefissi campionari e le righe solo provinciali (BES) sono tutte 1
        for r in righe:
            if r["id"].startswith(("bes:", "multiscopo:")) or not r["regione"]:
                self.assertTrue(r["sample_survey"], r["id"])


if __name__ == "__main__":
    unittest.main()
