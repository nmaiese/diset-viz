"""Il pool esteso delle sfide del giorno: i giorni gia' serviti non cambiano.

`game_daily._candidates` mescola l'elenco curato con il seed del giorno, quindi
aggiungere una riga a `config/game_indicators.csv` cambierebbe l'indicatore di OGNI
giorno, anche di uno gia' servito e condiviso. Le righe aggiunte dopo il lancio
portano `dal` (`POOL_CUTOVER`): prima di quel giorno il pool e' quello di prima.

Le costanti qui sotto sono state calcolate sul commit `b7dd6d98` (prima delle righe
nuove e del merge dei dati nuovi), con la chiave di prova `CHIAVE`, giorno per
giorno dal lancio al 3 ottobre 2026. Non si rigenerano: se un giorno non torna, e'
il codice a essere sbagliato, non la costante.
"""

import hashlib
import json
import unittest
from datetime import date, timedelta
from unittest import mock

from app import app, game_compare, game_daily, game_facts, provincial_families, quiz, quiz_tokens, sources
from app.design import numfmt

CHIAVE = "chiave-di-prova-del-passaggio"

# (id, livello_regione, livello_provincia) delle righe che c'erano al lancio.
RIGHE_DI_PRIMA = (
    ("901", 1, 0),
    ("902", 1, 0),
    ("multiscopo:MULTI_REDD_MEDIANO", 1, 0),
    ("multiscopo:MULTI_ABIT_SPESA_EURO", 1, 0),
    ("631", 1, 0),
    ("multiscopo:MULTI_DISAGIO_IMPREVISTI", 1, 0),
    ("multiscopo:MULTI_DISAGIO_RISPARMIO", 1, 0),
    ("12", 1, 0),
    ("15", 1, 0),
    ("57", 1, 0),
    ("402", 1, 0),
    ("bes:03LAV001-N22", 1, 1),
    ("bes:03LAV002-N22", 1, 1),
    ("339", 1, 0),
    ("bes:02IST002-N22", 1, 1),
    ("bes:02IST005-N22", 1, 0),
    ("bes:02IST006-N22", 1, 1),
    ("bes:02IST007-N22", 1, 1),
    ("bes:02IST023", 1, 0),
    ("bes:SDG-310", 1, 0),
    ("910", 1, 0),
    ("bes:01SAL002", 1, 0),
    ("bes:01SAL009", 1, 0),
    ("bes:01SAL010", 1, 0),
    ("bes:01SAL012", 1, 0),
    ("multiscopo:MULTI_BMI_OBESI", 1, 0),
    ("590", 1, 0),
    ("920", 1, 0),
    ("921", 1, 0),
    ("922", 1, 0),
    ("dem:POP65OVER", 1, 0),
    ("dem:POP014", 1, 0),
    ("923", 1, 0),
    ("dem:MEANAGECH", 1, 0),
    ("dem:BIRTHRATE", 1, 0),
    ("dem:MARRATE", 1, 0),
    ("52", 1, 0),
    ("232", 1, 0),
    ("84", 1, 0),
    ("60", 1, 0),
    ("105", 1, 0),
    ("165", 1, 0),
    ("611", 1, 0),
    ("27", 1, 0),
    ("426", 1, 0),
    ("72", 1, 0),
    ("multiscopo:MULTI_ICT_BANDA_LARGA", 1, 0),
    ("279", 1, 0),
    ("280", 1, 0),
    ("542", 1, 0),
    ("multiscopo:MULTI_ABIT_PROPRIETA", 1, 0),
    ("multiscopo:MULTI_ABIT_AFFITTO", 1, 0),
    ("multiscopo:MULTI_ABIT_UMIDITA", 1, 0),
    ("multiscopo:MULTI_ZONA_RUMORI", 1, 0),
    ("multiscopo:MULTI_ZONA_INQUINAMENTO", 1, 0),
    ("bes:08BSO001", 1, 0),
    ("bes:05REL006", 1, 0),
    ("bes:06POL007", 1, 0),
    ("54", 1, 0),
    ("123", 1, 0),
    ("01SAL001", 0, 1),
    ("01SAL004", 0, 1),
    ("01SAL006", 0, 1),
    ("01SAL020", 0, 1),
    ("02IST001", 0, 1),
    ("02IST003P-N22", 0, 1),
    ("02IST010P", 0, 1),
    ("02IST011P", 0, 1),
    ("03LAV003P-N22", 0, 1),
    ("03LAV006P-N22", 0, 1),
    ("03LAV007", 0, 1),
    ("04BEC001P", 0, 1),
    ("04BEC002P", 0, 1),
    ("04BEC005P", 0, 1),
    ("04BEC006P", 0, 1),
    ("04BEC009P", 0, 1),
    ("05REL008", 0, 1),
    ("06POL001", 0, 1),
    ("06POL002P", 0, 1),
    ("06POL003P", 0, 1),
    ("09PAE002", 0, 1),
    ("09PAE008", 0, 1),
    ("10AMB003", 0, 1),
    ("10AMB008", 0, 1),
    ("10AMB014", 0, 1),
    ("10AMB016", 0, 1),
    ("10AMB017", 0, 1),
    ("10AMB018P", 0, 1),
    ("10AMB024P", 0, 1),
    ("11RIC002", 0, 1),
    ("11RIC004P", 0, 1),
    ("12SER002P", 0, 1),
    ("12SER003P-N25", 0, 1),
    ("12SER007", 0, 1),
    ("12SER025", 0, 1),
)

# Impronta della sfida di ogni giorno servito: coppie e round dei tre livelli.
IMPRONTE_DI_PRIMA = {
    "2026-07-15": "568930eeb8d9c28d",
    "2026-07-16": "475a17c4ddb6072b",
    "2026-07-17": "bef9714511f3cbbf",
    "2026-07-18": "74d7e280643bef58",
    "2026-07-19": "d6b48f5f737aaac8",
    "2026-07-20": "997edc91166cc79d",
    "2026-07-21": "9296e30f995c8eb5",
    "2026-07-22": "cf98c0fe017c8b86",
    "2026-07-23": "bcb829fec52af775",
    "2026-07-24": "efbfa2222be7a8ea",
    "2026-07-25": "4953355a59314fed",
    "2026-07-26": "7aacd1315d585d10",
    "2026-07-27": "0a2baac985a89715",
    "2026-07-28": "f58c057f9a5a08f7",
    "2026-07-29": "296c04a1d5f17bad",
    "2026-07-30": "8140e5bbdd287cb8",
    "2026-07-31": "80c4e1a3f9935149",
    "2026-08-01": "e3fe8f40f0f59c53",
    "2026-08-02": "d90b7298d9fc7e03",
    "2026-08-03": "75c0f34c6e2dab8e",
    "2026-08-04": "0ae1fd2a84bf6216",
    "2026-08-05": "fea5a795a90909d6",
    "2026-08-06": "ace1771b67185421",
    "2026-08-07": "600f1f26eef9f082",
    "2026-08-08": "38bd3ad722b9120a",
    "2026-08-09": "f062334bc5b742f0",
    "2026-08-10": "1d8d108bad4f0147",
    "2026-08-11": "9725f45487881446",
    "2026-08-12": "ba8e4056f8ca3aa4",
    "2026-08-13": "1cc1b6b12d977730",
    "2026-08-14": "661be9ef69e11107",
    "2026-08-15": "2b7416484f9851a8",
    "2026-08-16": "523e1f5d55c767f6",
    "2026-08-17": "28caa42501b98de7",
    "2026-08-18": "0e0ac357f06f77f2",
    "2026-08-19": "8995e9e9b44168c1",
    "2026-08-20": "6dfd693efb9c81d7",
    "2026-08-21": "5608bec58e491e67",
    "2026-08-22": "845cfe292adf8ae7",
    "2026-08-23": "3e17850edd553774",
    "2026-08-24": "f0e8e9aad86bd124",
    "2026-08-25": "849a591779229c37",
    "2026-08-26": "86dc63080709c2d4",
    "2026-08-27": "54757a000368570e",
    "2026-08-28": "1b4356d55ad09173",
    "2026-08-29": "999b44212270c741",
    "2026-08-30": "8b4e96b0d28a91ff",
    "2026-08-31": "02c3412e13bea539",
    "2026-09-01": "43428c27caf19012",
    "2026-09-02": "604104b790f7e79b",
    "2026-09-03": "bcf003edff72484b",
    "2026-09-04": "99e8a96e82bae7f5",
    "2026-09-05": "f15df271f58746c0",
    "2026-09-06": "c1b20f5fe4e49981",
    "2026-09-07": "984720954aa2f372",
    "2026-09-08": "5186df8107046ba6",
    "2026-09-09": "9a7551584f124425",
    "2026-09-10": "92dd324173ac82fb",
    "2026-09-11": "d0b5ab3c41195a7f",
    "2026-09-12": "a097f913973de4b6",
    "2026-09-13": "fdfb147e8ff15240",
    "2026-09-14": "f927221646ed308c",
    "2026-09-15": "97645ec368290ae4",
    "2026-09-16": "a9aa47a4a5b16ca5",
    "2026-09-17": "663c0374dde86d42",
    "2026-09-18": "ef6fd9911b4b6b03",
    "2026-09-19": "f24273f3a55a7e93",
    "2026-09-20": "78eb7c799ddee744",
    "2026-09-21": "d0359a55e00c72aa",
    "2026-09-22": "15c91ba5e61c1055",
    "2026-09-23": "4a3761aefea7a099",
    "2026-09-24": "875dd3111a42886e",
    "2026-09-25": "b98f4d6c91e17a07",
    "2026-09-26": "b8bc389755d87ac1",
    "2026-09-27": "c523e153d5deb166",
    "2026-09-28": "06d62494f0724b84",
    "2026-09-29": "da581c7cd58549cd",
    "2026-09-30": "6fe6d309c6388188",
    "2026-10-01": "caf2d0bfa5a4145a",
    "2026-10-02": "2739b1e07c69dda5",
    "2026-10-03": "6fd6d1ce93ad6a6c",
}

# Escluse di proposito dalle sfide: campione piccolo o differenze fra territori troppo
# piccole per una domanda giusta (vedi docs/GIOCO.md).
ESCLUSE = {
    "multiscopo:MULTI_PRONTO_SOCCORSO", "multiscopo:MULTI_GUARDIA_MEDICA",
    "multiscopo:MULTI_RICOVERO_ASSISTENZA_MEDICA", "multiscopo:MULTI_INCIDENTI_DOMESTICI",
    "multiscopo:MULTI_CINQUE_PORZIONI", "multiscopo:MULTI_LAVORO_BICICLETTA",
    "multiscopo:MULTI_LAVORO_A_PIEDI", "multiscopo:MULTI_AMICI_OGNI_GIORNO",
    "multiscopo:MULTI_COLAZIONE_ADEGUATA", "eur:lfst_r_lfe2ehour",
    "ipr:speranza-di-vita-65", "ipr:eta-media-madre-al-parto",
}

# Per una riga nuova: scarto fra il valore piu' alto e il piu' basso, come frazione
# della media. Sotto, la domanda "chi e' maggiore?" si decide sul rumore.
SCARTO_MINIMO = 0.15
TERRITORI_MINIMI = {"regioni": 15, "province": 100}
VALORI_DISTINTI_MINIMI = 8


def _impronta(giorno):
    parti = []
    for livello in game_daily.LEVELS:
        confronto = game_daily.daily_compare(giorno, livello, CHIAVE)
        ordina = game_daily.daily_order(giorno, livello, CHIAVE)
        parti.append([
            livello, confronto["region"],
            [(p["indicator"]["id"], p["indicator"]["year"], p["a"]["key"], p["b"]["key"]) for p in confronto["pairs"]],
            ordina["region"], ordina["indicator"]["id"], ordina["indicator"]["year"],
            [t["key"] for t in ordina["territories"]],
        ])
    return hashlib.sha256(json.dumps(parti, sort_keys=True).encode()).hexdigest()[:16]


def _nuove():
    return [r for r in game_daily.game_indicators() if r["since"] is not None]


class PassaggioDelPoolTest(unittest.TestCase):
    def test_le_righe_senza_data_sono_quelle_di_prima(self):
        """Nessuno puo' aggiungere una riga senza `dal`: entrerebbe anche nei giorni
        passati. Le righe di prima restano le stesse, con gli stessi flag."""
        di_prima = tuple(
            (r["id"], int(r["regione"]), int(r["provincia"]))
            for r in game_daily.game_indicators() if r["since"] is None
        )
        self.assertEqual(di_prima, RIGHE_DI_PRIMA)

    def test_ogni_riga_nuova_ha_il_passaggio_e_mai_prima(self):
        nuove = _nuove()
        self.assertGreaterEqual(len(nuove), 20)
        for r in nuove:
            self.assertGreaterEqual(r["since"], game_daily.POOL_CUTOVER, r["id"])
        self.assertEqual(min(r["since"] for r in nuove), game_daily.POOL_CUTOVER)
        # Il passaggio e' dopo l'ultimo giorno gia' servito (3 ottobre 2026).
        self.assertGreaterEqual(game_daily.POOL_CUTOVER, date(2026, 10, 4))

    def test_i_giorni_fino_al_3_ottobre_sono_identici_a_prima(self):
        giorno, visti = game_daily.GAME_EPOCH, 0
        while giorno <= date(2026, 10, 3):
            with self.subTest(giorno=giorno.isoformat()):
                self.assertEqual(_impronta(giorno), IMPRONTE_DI_PRIMA[giorno.isoformat()])
            giorno += timedelta(days=1)
            visti += 1
        self.assertEqual(visti, len(IMPRONTE_DI_PRIMA))

    def test_prima_del_passaggio_le_righe_nuove_non_sono_nel_pool(self):
        ultimo = game_daily.POOL_CUTOVER - timedelta(days=1)
        nuove = {r["id"] for r in _nuove()}
        for livello, ambito in (("regioni", "regioni"), ("province", "province")):
            prima = {i["id"] for i, _, _ in self._pool(livello, ambito, ultimo)}
            dopo = {i["id"] for i, _, _ in self._pool(livello, ambito, game_daily.POOL_CUTOVER)}
            self.assertFalse(prima & nuove, livello)
            self.assertTrue(dopo & nuove, livello)

    @staticmethod
    def _pool(livello, ambito, giorno):
        import random

        return game_daily._candidates(livello, ambito, lambda r: True, 2, random.Random(1), giorno)

    def test_dal_passaggio_le_sfide_usano_anche_le_righe_nuove(self):
        nuove = {r["id"] for r in _nuove()}
        usate = set()
        giorno = game_daily.POOL_CUTOVER
        for _ in range(8):
            for livello in game_daily.LEVELS:
                usate.update(p["indicator"]["id"] for p in game_daily.daily_compare(giorno, livello, CHIAVE)["pairs"])
                usate.add(game_daily.daily_order(giorno, livello, CHIAVE)["indicator"]["id"])
            giorno += timedelta(days=1)
        self.assertTrue(usate & nuove)


class RigheNuoveTest(unittest.TestCase):
    def test_nessuna_esclusa_e_nel_pool(self):
        ids = {r["id"] for r in game_daily.game_indicators()}
        self.assertFalse(ids & ESCLUSE, ids & ESCLUSE)

    def test_fonte_anno_e_valori_di_ogni_riga_nuova(self):
        for r in _nuove():
            with self.subTest(id=r["id"]):
                self.assertTrue(r["regione"] or r["provincia"])
                livelli = [("regioni", "regione")] * r["regione"] + [("province", "provincia")] * r["provincia"]
                for ambito, _ in livelli:
                    anno, righe = game_daily._indicator_rows(r, ambito)
                    self.assertIn(anno, (2025, 2026))
                    valori = [x["value"] for x in righe]
                    self.assertGreaterEqual(len(valori), TERRITORI_MINIMI[ambito], ambito)
                    self.assertGreaterEqual(len(set(valori)), VALORI_DISTINTI_MINIMI, ambito)
                    media = sum(valori) / len(valori)
                    self.assertGreaterEqual((max(valori) - min(valori)) / abs(media), SCARTO_MINIMO, ambito)
                # la fonte viene dal registro, mai a mano
                if r["provincia"]:
                    info = game_daily.province_info(r["id"])
                    self.assertIsNotNone(info)
                    famiglia = game_daily.province_source(r["id"])[0]
                    self.assertEqual(info["source_label"], sources.family_label(famiglia))
                    self.assertTrue(info["source_url"].startswith("https://"))
                    self.assertTrue(info["province_path"].startswith("/indicatore/"))
                    self.assertTrue(info["description"])
                if r["regione"]:
                    voce = {p["id"]: p for p in quiz._quiz_indicators()}[r["id"]]
                    self.assertTrue(voce["source_label"])
                    self.assertTrue(voce["source_url"])
                self.assertIn(game_daily._family_of(r["id"]) if r["regione"] else game_daily.province_source(r["id"])[0],
                              set(sources.SOURCES) | {"territorial"})

    def test_il_livello_dei_flag_segue_la_famiglia(self):
        """ipr solo province, aci e agcom tutti e due, eur e Multiscopo solo regioni."""
        for r in _nuove():
            with self.subTest(id=r["id"]):
                prefisso = r["id"].split(":", 1)[0]
                atteso = {"ipr": (0, 1), "aci": (1, 1), "agcom": (1, 1), "eur": (1, 0), "multiscopo": (1, 0)}[prefisso]
                self.assertEqual((int(r["regione"]), int(r["provincia"])), atteso)

    def test_campionario_per_le_indagini(self):
        per_id = {r["id"]: r["sample_survey"] for r in game_daily.game_indicators()}
        for ind_id, atteso in (
            ("multiscopo:MULTI_TEATRO", True), ("eur:ilc_mdes01_r", True), ("eur:hrst_st_rcat", True),
            ("ipr:tasso-di-disoccupazione", True), ("ipr:tasso-di-attivita", True),
            ("aci:autovetture-ante-2009", False), ("agcom:copertura-ftth", False),
            ("eur:tour_occ_anor2", False), ("ipr:figli-per-donna", False),
        ):
            self.assertEqual(per_id[ind_id], atteso, ind_id)

    def test_ogni_unita_nuova_scrive_una_frase(self):
        """Un'unita' che `game_facts` non sa scrivere fa sparire il fatto senza errori:
        per ogni unita' nuova almeno una riga produce la sua frase."""
        prodotte = {}
        for r in _nuove():
            for flag, ambito in (("regione", "regioni"), ("provincia", "province")):
                if not r[flag]:
                    continue
                anno, righe = game_daily._indicator_rows(r, ambito)
                ordinate = sorted(righe, key=lambda x: -x["value"])
                n = len(ordinate)
                scelti = [ordinate[int(i * (n - 1) / 4)] for i in range(5)]
                giusto = [{"region": x["name"], "region_key": x["key"], "value": x["value"]} for x in scelti]
                rovesciato = [{**x, "guessed_position": i + 1} for i, x in enumerate(reversed(giusto))]
                fatto = game_facts.order_fact(ambito, game_daily._indicator_fields(r, anno), rovesciato, giusto)
                if fatto:
                    prodotte.setdefault(r["unit"], []).append(fatto)
        for unita in {r["unit"] for r in _nuove()}:
            self.assertTrue(prodotte.get(unita), unita)


class SfidaConUnaFonteEsternaTest(unittest.TestCase):
    """Le risposte a una sfida con un indicatore Istat provinciale, ACI o AGCOM:
    se `province_info` non lo sapesse leggere, ogni risposta sarebbe un 400."""

    def setUp(self):
        self.client = app.test_client()

    @staticmethod
    def _giorno_con(predicato, scorri):
        giorno = game_daily.POOL_CUTOVER
        for _ in range(400):
            if predicato(giorno):
                return giorno
            giorno += timedelta(days=1)
        raise AssertionError("nessun giorno adatto")

    @staticmethod
    def _esterno(ind_id):
        return game_daily.province_source(ind_id)[0] != "bes"

    def test_ordina_a_livello_province_con_una_famiglia_esterna(self):
        visti = set()
        giorno = game_daily.POOL_CUTOVER
        for _ in range(400):
            for livello in ("province", "stessa_regione"):
                ind = game_daily.daily_order(giorno, livello)["indicator"]
                if self._esterno(ind["id"]) and (ind["id"], livello) not in visti:
                    visti.add((ind["id"], livello))
                    self._ordina(giorno, livello)
            giorno += timedelta(days=1)
            if len({i for i, _ in visti}) >= 3:
                break
        self.assertTrue(visti)

    def _ordina(self, giorno, livello):
        with mock.patch.object(game_daily, "today_rome", return_value=giorno):
            sessione = self.client.get(f"/api/game/order/daily/session?level={livello}").get_json()
            risposta = self.client.post("/api/game/order/daily/answer", json={
                "token": sessione["token"], "level": livello,
                "region_keys": [t["key"] for t in sessione["territories"]]})
        self.assertEqual(risposta.status_code, 200, (giorno, livello, sessione["indicator"]["id"]))
        ind = risposta.get_json()["indicator"]
        famiglia = game_daily.province_source(sessione["indicator"]["id"])[0]
        self.assertEqual(ind["source_label"], sources.family_label(famiglia))
        self.assertTrue(ind["source_url"].startswith("https://"))
        entry = provincial_families.indicator_page(*game_daily.province_source(sessione["indicator"]["id"]))
        self.assertEqual(ind["path"], sources.level_path(entry["metadata"]["path"], "provincia", entry["metadata"]["base_level"]))
        self.assertTrue(ind["description"])
        valori = [r["value"] for r in risposta.get_json()["correct_order"]]
        self.assertEqual(valori, sorted(valori, reverse=True))

    def test_chi_e_maggiore_a_livello_province_con_una_famiglia_esterna(self):
        giorno = self._giorno_con(
            lambda g: any(self._esterno(p["indicator"]["id"]) for p in game_daily.daily_compare(g, "province")["pairs"]),
            None,
        )
        with mock.patch.object(game_compare, "today_rome", return_value=giorno),                 mock.patch.object(quiz_tokens, "_now", return_value=1_800_000_000.0):
            sessione = self.client.get("/api/game/compare/daily/session?level=province&timer=0").get_json()
            token, provato = sessione["token"], 0
            for indice, coppia in enumerate(sessione["questions"]):
                risposta = self.client.post("/api/game/compare/daily/answer", json={
                    "puzzle_id": sessione["puzzle_id"], "q": indice, "choice": "region_a", "token": token})
                self.assertEqual(risposta.status_code, 200, (giorno, coppia["indicator"]["id"]))
                dati = risposta.get_json()
                token = dati["token"]
                famiglia = game_daily.province_source(coppia["indicator"]["id"])[0]
                if famiglia != "bes":
                    provato += 1
                    self.assertEqual(dati["indicator"]["source_label"], sources.family_label(famiglia))
                    self.assertTrue(dati["indicator"]["path"].startswith("/indicatore/"))
                if indice < len(sessione["questions"]) - 1:
                    token = self.client.post("/api/game/compare/daily/next", json={
                        "puzzle_id": sessione["puzzle_id"], "q": indice, "token": token}).get_json()["token"]
        self.assertGreater(provato, 0)

    def test_le_fonti_per_il_json_ld_includono_le_famiglie_esterne(self):
        for gioco in ("compare", "order"):
            famiglie = game_daily.game_families(gioco)
            for atteso in ("istat_provinciale", "aci", "agcom", "eurostat", "multiscopo", "bes"):
                self.assertIn(atteso, famiglie, (gioco, atteso))
        self.assertNotIn("aci", game_daily.game_families("provincia"))


if __name__ == "__main__":
    unittest.main()
