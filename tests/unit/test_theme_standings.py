"""La classifica delle regioni su un tema, e il suo accordo col profilo regione.

`region_profile` legge la matrice dei percentili per regione e ne ricava un
punteggio per tema; `theme_standings` legge la stessa matrice per tema e ne
ricava un punteggio per regione. Sono lo stesso calcolo letto nei due versi,
quindi la prova che conta e' che diano **lo stesso numero**: due percorsi che
misurano la stessa cosa e rispondono diverso sono un difetto, anche quando la
differenza non si vede in pagina (ne sono usciti diciassette scarti da 0,0001,
perche' uno arrotondava prima della media e l'altro dopo).
"""
import unittest

from app import atlas_catalog, profiles


class LaClassificaPerTema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temi = [t["theme"] for t in atlas_catalog.all_atlas_themes_index()]
        cls.classifiche = {t: profiles.theme_standings(t) for t in cls.temi}

    def test_un_tema_classifica_tutte_le_regioni_o_nessuna(self):
        """Mai una classifica parziale: o ci sono tutte e venti, o non c'e'.

        Due temi oggi non ne hanno nessuna, per due motivi diversi e legittimi.
        "Benessere soggettivo" non ha indicatori nel catalogo territoriale da
        cui la matrice dei percentili e' costruita. "Istituzioni e
        partecipazione" ne ha tre direzionali ma nessuno completo su tutte e
        venti le regioni, e un percentile su una copertura parziale non e'
        confrontabile. In quei casi la pagina mostra i suoi indicatori senza
        fingere una graduatoria.
        """
        for tema, s in self.classifiche.items():
            with self.subTest(tema=tema):
                self.assertIn(len(s["rows"]), (0, len(profiles.REGION_ORDER)))
                if not s["rows"]:
                    self.assertFalse(s["rated"])

    def test_la_maggioranza_dei_temi_si_classifica(self):
        """Se un giorno la matrice si svuota, le pagine tema tornano elenchi."""
        con_classifica = sum(1 for s in self.classifiche.values() if s["rated"])
        self.assertGreaterEqual(con_classifica, len(self.classifiche) - 3)

    def test_le_posizioni_sono_progressive_e_ordinate_per_punteggio(self):
        for tema, s in self.classifiche.items():
            with self.subTest(tema=tema):
                posizioni = [r["rank"] for r in s["rows"]]
                self.assertEqual(posizioni, list(range(1, len(posizioni) + 1)))
                punteggi = [r["score"] for r in s["rows"]]
                self.assertEqual(punteggi, sorted(punteggi, reverse=True))

    def test_i_punteggi_stanno_fra_zero_e_uno(self):
        for tema, s in self.classifiche.items():
            for r in s["rows"]:
                with self.subTest(tema=tema, regione=r["region_key"]):
                    self.assertGreaterEqual(r["score"], 0.0)
                    self.assertLessEqual(r["score"], 1.0)

    def test_il_pareggio_si_rompe_sempre_allo_stesso_modo(self):
        """Senza un secondo criterio, due regioni a pari punteggio si
        scambiano di posto a ogni processo e la pagina cambia da sola."""
        for tema in self.temi:
            with self.subTest(tema=tema):
                uno = [r["region_key"] for r in profiles.theme_standings(tema)["rows"]]
                due = [r["region_key"] for r in profiles.theme_standings(tema)["rows"]]
                self.assertEqual(uno, due)

    def test_un_tema_senza_abbastanza_indicatori_non_si_classifica(self):
        """Due indicatori non ordinano venti regioni: `rated` lo dice, e la
        pagina non deve presentare quelle righe come una graduatoria."""
        for tema, s in self.classifiche.items():
            with self.subTest(tema=tema):
                self.assertEqual(s["rated"], s["indicator_count"] >= profiles.MIN_THEME_INDICATORS)

    def test_ogni_regione_porta_il_suo_indicatore_migliore_e_peggiore(self):
        for tema, s in self.classifiche.items():
            for r in s["rows"]:
                with self.subTest(tema=tema, regione=r["region_key"]):
                    self.assertTrue(r["best_indicator"]["name"])
                    self.assertTrue(r["worst_indicator"]["path"].startswith("/indicatore/"))

    def test_l_inversione_concorda_col_profilo_regione(self):
        """Il vincolo vero: stesso punteggio e stesso conteggio nei due versi."""
        confronti = 0
        for tema, s in self.classifiche.items():
            for r in s["rows"]:
                profilo = profiles.region_profile(r["region_key"])
                voce = next((v for v in profilo["theme_table"] if v["theme"] == tema), None)
                if voce is None:
                    continue
                confronti += 1
                with self.subTest(tema=tema, regione=r["region_key"]):
                    self.assertEqual(voce["score"], r["score"])
                    self.assertEqual(voce["count"], r["count"])
        self.assertGreater(confronti, 100, "il test non sta confrontando quasi niente")

    def test_la_posizione_si_legge_anche_da_sola(self):
        tema = next(t for t, s in self.classifiche.items() if s["rated"])
        prima = self.classifiche[tema]["rows"][0]
        self.assertEqual(profiles.theme_rank_of(tema, prima["region_key"]), 1)

    def test_un_tema_non_classificabile_non_restituisce_posizioni(self):
        non_classificabili = [t for t, s in self.classifiche.items() if not s["rated"]]
        if not non_classificabili:
            self.skipTest("tutti i temi hanno abbastanza indicatori")
        tema = non_classificabili[0]
        self.assertIsNone(profiles.theme_rank_of(tema, "lombardia"))

    def test_un_tema_che_non_esiste_non_esplode(self):
        s = profiles.theme_standings("Un tema che non esiste")
        self.assertEqual(s["rows"], [])
        self.assertFalse(s["rated"])


class NessunaRegioneRispondeNiente(unittest.TestCase):
    """Quattro regioni su venti dicevano "Nessun tema emerge nettamente sopra
    la media" proprio alla domanda per cui il lettore era arrivato, e sei sul
    rovescio. I tre migliori e i tre peggiori ci sono sempre; `netto` dice se
    la soglia e' davvero superata."""

    def test_ogni_regione_ha_tre_temi_per_lato(self):
        for voce in profiles.all_regions_index():
            profilo = profiles.region_profile(voce["region_key"])
            with self.subTest(regione=voce["region_key"]):
                self.assertEqual(len(profilo["themes_strong"]), 3)
                self.assertEqual(len(profilo["themes_weak"]), 3)

    def test_netto_dice_la_verita(self):
        for voce in profiles.all_regions_index():
            profilo = profiles.region_profile(voce["region_key"])
            for t in profilo["themes_strong"]:
                with self.subTest(regione=voce["region_key"], tema=t["theme"]):
                    self.assertEqual(t["netto"], t["score"] >= 0.6)
            for t in profilo["themes_weak"]:
                with self.subTest(regione=voce["region_key"], tema=t["theme"]):
                    self.assertEqual(t["netto"], t["score"] <= 0.4)

    def test_i_forti_sono_ordinati_meglio_per_primo_e_i_deboli_al_contrario(self):
        profilo = profiles.region_profile("molise")
        forti = [t["score"] for t in profilo["themes_strong"]]
        deboli = [t["score"] for t in profilo["themes_weak"]]
        self.assertEqual(forti, sorted(forti, reverse=True))
        self.assertEqual(deboli, sorted(deboli))


if __name__ == "__main__":
    unittest.main()
