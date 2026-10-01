import importlib.util
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app import game_daily
from app.game_daily import (
    GAME_EPOCH,
    distance_km_direction,
    today_rome,
    next_challenge_rome,
    province_pool,
    daily_region,
    eligible_regions,
    day_seed,
)

ROOT = Path(__file__).resolve().parents[2]

ORDINE = (
    "Piemonte", "Valle d'Aosta", "Lombardia", "Trentino Alto Adige", "Veneto",
    "Friuli-Venezia Giulia", "Liguria", "Emilia-Romagna", "Toscana", "Umbria",
    "Marche", "Lazio", "Abruzzo", "Molise", "Campania", "Puglia", "Basilicata",
    "Calabria", "Sicilia", "Sardegna",
)
# Le soluzioni servite dal codice di prima del cutover (seed
# `random.Random("divario-regioni-cycle-N")`), dal giorno di lancio in poi, una
# per giorno. Sono fissate a mano: e' quello che l'archivio deve continuare a dire.
SOLUZIONI_VECCHIE = (
    "Lazio", "Calabria", "Puglia", "Valle d'Aosta", "Marche", "Sicilia", "Emilia-Romagna",
    "Basilicata", "Molise", "Lombardia", "Veneto", "Abruzzo", "Friuli-Venezia Giulia",
    "Piemonte", "Campania", "Toscana", "Sardegna", "Umbria", "Trentino Alto Adige", "Liguria",
    "Liguria", "Valle d'Aosta", "Lombardia", "Molise", "Emilia-Romagna", "Basilicata", "Toscana",
    "Abruzzo", "Umbria", "Sicilia", "Puglia", "Trentino Alto Adige", "Sardegna", "Campania",
    "Lazio", "Piemonte", "Marche", "Calabria", "Veneto", "Friuli-Venezia Giulia",
    "Valle d'Aosta", "Sardegna", "Trentino Alto Adige", "Molise", "Friuli-Venezia Giulia",
    "Piemonte", "Umbria", "Liguria", "Calabria", "Veneto", "Puglia", "Sicilia", "Basilicata",
    "Lazio", "Campania", "Lombardia", "Toscana", "Marche", "Abruzzo", "Emilia-Romagna",
)


class TestOggiRoma(unittest.TestCase):
    def test_dopo_le_23_utc_a_roma_e_gia_il_giorno_dopo(self):
        # 23:30 UTC del 30 settembre: a Roma (CEST, UTC+2) sono le 01:30 del 1 ottobre.
        now = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(today_rome(now), date(2026, 10, 1))

    def test_prima_delle_22_utc_il_giorno_e_lo_stesso(self):
        now = datetime(2026, 9, 30, 21, 59, tzinfo=timezone.utc)
        self.assertEqual(today_rome(now), date(2026, 9, 30))

    def test_ora_solare_cambia_la_soglia(self):
        # In inverno (CET, UTC+1) il giorno cambia alle 23:00 UTC, non alle 22:00.
        self.assertEqual(today_rome(datetime(2026, 12, 15, 22, 30, tzinfo=timezone.utc)), date(2026, 12, 15))
        self.assertEqual(today_rome(datetime(2026, 12, 15, 23, 30, tzinfo=timezone.utc)), date(2026, 12, 16))

    def test_prossima_sfida_e_la_mezzanotte_di_roma(self):
        # Mezzanotte del 1 ottobre a Roma (CEST) = 22:00 UTC del 30 settembre.
        self.assertEqual(next_challenge_rome(date(2026, 9, 30)), "2026-09-30T22:00:00+00:00")
        # In inverno (CET) = 23:00 UTC.
        self.assertEqual(next_challenge_rome(date(2026, 12, 15)), "2026-12-15T23:00:00+00:00")


class TestSeedOnesto(unittest.TestCase):
    CHIAVE = "chiave-di-prova"

    def test_il_seed_e_deterministico_e_dipende_da_gioco_data_e_chiave(self):
        giorno = date(2026, 10, 1)
        base = day_seed("regioni", giorno, self.CHIAVE)
        self.assertEqual(base, day_seed("regioni", giorno, self.CHIAVE))
        self.assertNotEqual(base, day_seed("compare", giorno, self.CHIAVE))
        self.assertNotEqual(base, day_seed("regioni", giorno + timedelta(days=1), self.CHIAVE))
        self.assertNotEqual(base, day_seed("regioni", giorno, "altra-chiave"))

    def test_senza_variabile_si_usa_la_chiave_di_sviluppo(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GAME_SEED_KEY", None)
            self.assertEqual(game_daily.seed_key(), game_daily.DEV_SEED_KEY)
        with mock.patch.dict(os.environ, {"GAME_SEED_KEY": "da-ambiente"}):
            self.assertEqual(game_daily.seed_key(), "da-ambiente")

    def test_il_cutover_e_dopo_il_lancio(self):
        # Il valore cambia: il segnaposto (2099) lo sostituisce il coordinatore.
        self.assertGreater(game_daily.SEED_CUTOVER, GAME_EPOCH)

    def test_prima_del_cutover_le_soluzioni_sono_quelle_di_oggi(self):
        cutover = GAME_EPOCH + timedelta(days=len(SOLUZIONI_VECCHIE))
        for offset, attesa in enumerate(SOLUZIONI_VECCHIE):
            giorno = GAME_EPOCH + timedelta(days=offset)
            self.assertEqual(daily_region(giorno, ORDINE, cutover, self.CHIAVE), attesa, giorno)
            # Con il segnaposto di default: stesso risultato.
            self.assertEqual(daily_region(giorno, ORDINE), attesa, giorno)

    def test_dal_cutover_cambiano_e_non_ripetono_nel_ciclo(self):
        cutover = GAME_EPOCH + timedelta(days=30)
        dopo = [daily_region(cutover + timedelta(days=i), ORDINE, cutover, self.CHIAVE) for i in range(40)]
        self.assertEqual(len(set(dopo[:20])), 20)
        self.assertEqual(len(set(dopo[20:40])), 20)
        vecchie = [daily_region(cutover + timedelta(days=i), ORDINE, cutover + timedelta(days=99)) for i in range(20)]
        self.assertNotEqual(dopo[:20], vecchie)

    def test_ruotare_la_chiave_cambia_le_soluzioni_dal_cutover_in_poi(self):
        cutover = GAME_EPOCH + timedelta(days=30)
        giorni = [cutover + timedelta(days=i) for i in range(20)]
        a = [daily_region(g, ORDINE, cutover, "chiave-a") for g in giorni]
        b = [daily_region(g, ORDINE, cutover, "chiave-b") for g in giorni]
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(sum(x != y for x, y in zip(a, b)), 10)
        # Prima del cutover la chiave non conta.
        prima = [GAME_EPOCH + timedelta(days=i) for i in range(30)]
        self.assertEqual(
            [daily_region(g, ORDINE, cutover, "chiave-a") for g in prima],
            [daily_region(g, ORDINE, cutover, "chiave-b") for g in prima],
        )


class TestTerritori(unittest.TestCase):
    def test_le_107_province_hanno_regione_e_centroide_dentro_il_viewbox(self):
        dati = json.loads((ROOT / "app/static/data/province_centroidi.json").read_text(encoding="utf-8"))
        larghezza, altezza = dati["viewBox"]
        self.assertEqual(len(dati["province"]), 107)
        for chiave, p in dati["province"].items():
            self.assertTrue(0 <= p["x"] <= larghezza and 0 <= p["y"] <= altezza, chiave)
        pool = province_pool()
        self.assertEqual(len(pool), 107)
        self.assertEqual(len({p["key"] for p in pool}), 107)
        self.assertEqual({p["key"] for p in pool}, set(dati["province"]))
        for p in pool:
            self.assertTrue(p["region_key"], p["key"])

    def test_province_giocabili_escludono_le_sagome_illeggibili(self):
        self.assertEqual(game_daily.excluded_provinces(), ["lecco", "monza-e-della-brianza", "prato", "trieste"])
        giocabili = province_pool(solo_giocabili=True)
        self.assertEqual(len(giocabili), 103)
        for p in giocabili:
            self.assertGreaterEqual(min(p["w"], p["h"]), game_daily.PLAYABLE_THRESHOLD, p["key"])

    def test_regioni_idonee(self):
        conteggi = {}
        for p in province_pool():
            conteggi[p["region"]] = conteggi.get(p["region"], 0) + 1
        self.assertEqual(conteggi["Valle d'Aosta"], 1)
        for regione in ("Molise", "Basilicata", "Umbria", "Trentino Alto Adige"):
            self.assertEqual(conteggi[regione], 2, regione)
        tre = eligible_regions(3)
        cinque = eligible_regions(5)
        self.assertEqual(len(tre), 15)
        for fuori in ("Valle d'Aosta", "Molise", "Basilicata", "Umbria", "Trentino Alto Adige"):
            self.assertNotIn(fuori, tre)
        self.assertEqual(
            cinque,
            ["Piemonte", "Lombardia", "Veneto", "Emilia-Romagna", "Toscana", "Marche", "Lazio",
             "Campania", "Puglia", "Calabria", "Sicilia", "Sardegna"],
        )
        for fuori in ("Friuli-Venezia Giulia", "Liguria", "Abruzzo"):
            self.assertIn(fuori, tre)
            self.assertNotIn(fuori, cinque)

    def test_distanze_di_riferimento_entro_il_cinque_per_cento(self):
        # Distanze in linea d'aria fra i capoluoghi (haversine): i centroidi
        # delle province non coincidono con le citta', da qui la tolleranza.
        riferimenti = (("milano", "roma", 477), ("torino", "trieste", 480), ("palermo", "bolzano", 947))
        for a, b, vero in riferimenti:
            km, _ = distance_km_direction(a, b)
            self.assertAlmostEqual(km / vero, 1.0, delta=0.05, msg=f"{a}-{b}: {km} km contro {vero}")
            self.assertEqual(distance_km_direction(a, b)[0], distance_km_direction(b, a)[0])

    def test_direzione_in_otto_punti(self):
        self.assertEqual(distance_km_direction("palermo", "bolzano")[1], "N")
        self.assertEqual(distance_km_direction("bolzano", "palermo")[1], "S")
        self.assertEqual(distance_km_direction("torino", "trieste")[1], "E")
        self.assertEqual(distance_km_direction("trieste", "torino")[1], "O")
        self.assertEqual(distance_km_direction("milano", "roma")[1], "SE")
        self.assertEqual(distance_km_direction("roma", "milano")[1], "NO")
        self.assertEqual(distance_km_direction("roma", "roma"), (0, None))


class TestScriptCentroidi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("centroidi_province", ROOT / "design/v1/tools/centroidi_province.py")
        cls.modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.modulo)

    def test_centroide_di_un_quadrato_con_comandi_relativi(self):
        c = self.modulo.centroide_provincia("M10 20l10 0 0 10-10 0z")
        self.assertEqual((c["x"], c["y"], c["w"], c["h"]), (15.0, 25.0, 10.0, 10.0))

    def test_conta_solo_il_poligono_piu_grande(self):
        # Un quadrato 10x10 e un'isola 2x2 lontana: il centroide e' del quadrato.
        c = self.modulo.centroide_provincia("M0 0h10v10h-10zM100 100h2v2h-2z")
        self.assertEqual((c["x"], c["y"]), (5.0, 5.0))

    def test_un_comando_non_gestito_ferma_il_calcolo(self):
        with self.assertRaises(ValueError):
            self.modulo.poligoni("M0 0C1 1 2 2 3 3z")


if __name__ == "__main__":
    unittest.main()
