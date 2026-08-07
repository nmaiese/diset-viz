"""Il pacchetto sui dati veri: l'interno della matrice, e la forma variabile.

Due promesse da tenere, e sono le due per cui `packs/` esiste.

La prima e' il buco nel perimetro. `scripts/indicator_brief.py` porta il primo
e l'ultimo valore di ogni territorio e la serie delle medie: gli articoli
pubblicati citano cifre di meta' serie che da li' non si potevano prendere, e
`docs/CANARY.md` lo dice apertamente. Se il pacchetto non porta la matrice
intera, quel buco resta.

La seconda e' che la forma cambi da un indicatore all'altro. Un inventario che
mette lo stesso tipo di angolo in cima a tutti gli articoli e' uno scheletro
fisso con un altro nome.
"""
import unittest

from app import sources
from app.atlas_catalog import get_atlas_catalog
from packs import build


def pack_of(code, level=None):
    family, raw = build._resolve(code)
    return build.build_pack(family, raw, level)


class TheMatrixIsWhole(unittest.TestCase):
    """Ogni anno, ogni territorio. E' la cifra che il brief non sapeva dare."""

    @classmethod
    def setUpClass(cls):
        cls.pack = pack_of("ter-1")

    def test_the_middle_years_are_there_not_just_the_ends(self):
        years = self.pack["years"]
        self.assertGreater(len(years), 10)
        for year in years:
            self.assertIn(year, self.pack["matrix"])
            self.assertTrue(self.pack["matrix"][year])

    def test_a_figure_a_published_article_quotes_is_in_the_pack(self):
        """`content/indicators/1.json` cita l'Emilia-Romagna del 2014.

        Quella cifra sta a meta' serie: e' esattamente il tipo di numero che il
        produttore doveva andare a prendere fuori dal brief.
        """
        self.assertIn(2014, self.pack["matrix"])
        value = self.pack["matrix"][2014].get("Emilia-Romagna")
        self.assertIsNotNone(value, "il 2014 dell'Emilia-Romagna non e' nel pacchetto")
        self.assertAlmostEqual(value, 52.13, delta=0.05)

    def test_territories_are_named_not_slugged(self):
        self.assertIn("Emilia-Romagna", self.pack["territories"])
        self.assertNotIn("emilia-romagna", self.pack["territories"])


class TheShapeVaries(unittest.TestCase):
    def test_two_indicators_do_not_open_on_the_same_angle_by_construction(self):
        """Non che sia impossibile: che non sia il caso su tutto il catalogo.

        Il tetto e' quello del piano: nessun tipo apre piu' del 40% degli
        articoli. Prima della calibrazione `graduatoria-spezzata` ne apriva il
        57,7%, e la prosa avrebbe ereditato quell'uniformita'.
        """
        from collections import Counter

        openers = Counter()
        for item in get_atlas_catalog()["indicators"][:120]:
            family, raw = sources.split_internal_id(item["id"])
            try:
                pack = build.build_pack(family, raw)
            except Exception:
                continue
            if pack and pack["angles"]:
                openers[pack["angles"][0]["type"]] += 1

        total = sum(openers.values())
        self.assertGreater(total, 80, "campione troppo piccolo per dire qualcosa")
        top, count = openers.most_common(1)[0]
        self.assertLess(count / total, 0.4,
                        f"{top} apre il {count / total:.0%} degli articoli")
        self.assertGreaterEqual(len(openers), 5,
                                f"solo {len(openers)} tipi di apertura: {openers}")

    def test_length_follows_the_story_instead_of_a_band(self):
        lengths = []
        for item in get_atlas_catalog()["indicators"][:120]:
            family, raw = sources.split_internal_id(item["id"])
            try:
                pack = build.build_pack(family, raw)
            except Exception:
                continue
            if pack:
                lengths.append(pack["words"]["atteso"])

        self.assertGreater(len(lengths), 80)
        lengths.sort()
        median = lengths[len(lengths) // 2]
        spread = (lengths[-1] - lengths[0]) / median
        self.assertGreater(spread, 0.5,
                           f"lunghezze da {lengths[0]} a {lengths[-1]}: piatte, "
                           "quindi lo story finder non sta guidando niente")
        self.assertGreaterEqual(lengths[0], build.MIN_WORDS)

    def test_no_ceiling_on_length(self):
        self.assertIsNone(build.suggested_words(9.0)["massimo"])
        self.assertGreater(build.suggested_words(9.0)["atteso"],
                           build.suggested_words(1.0)["atteso"])


class LevelScoping(unittest.TestCase):
    def test_a_provincial_pack_talks_about_provinces(self):
        pack = pack_of("bes-10AMB001P", "provincia")
        self.assertEqual(pack["level"], "provincia")
        self.assertGreater(len(pack["territories"]), 50)
        self.assertIn("Gorizia", pack["territories"])
        self.assertNotIn("Lombardia", pack["territories"])

    def test_provinces_have_no_partition_so_the_group_angle_stays_quiet(self):
        """Meglio nessun gruppo che un gruppo inventato."""
        pack = pack_of("bes-10AMB001P", "provincia")
        kinds = {angle["type"] for angle in pack["angles"]}
        self.assertNotIn("gruppi-che-divergono", kinds)
        self.assertNotIn("gruppi-che-convergono", kinds)


class MethodBreaksAreConstraintsNotStories(unittest.TestCase):
    """Le note della fonte entrano nel pacchetto, e non competono per l'apertura.

    Duecentotre righe di `data/definitions/istat_territoriali.csv` portano una
    nota metodologica e centoquarantasei nominano un anno. Finora le leggeva a
    mano il verificatore, e `ter-60` aveva costruito la propria tesi sulla
    finestra prima di un cambio di metodo senza dirlo.
    """

    def test_the_note_reaches_the_pack_without_being_passed_by_hand(self):
        pack = pack_of("ter-5")
        self.assertTrue(pack["constraints"], "la nota di ter-5 non arriva")
        constraint = pack["constraints"][0]
        self.assertEqual(constraint["type"], "rottura-di-metodo")
        self.assertIn(1997, constraint["figures"]["anni_citati_nella_nota"])
        self.assertIsNotNone(constraint["caution"])

    def test_a_constraint_never_opens_the_article(self):
        for code in ("ter-5", "ter-1", "ter-13"):
            with self.subTest(code=code):
                pack = pack_of(code)
                kinds = {angle["type"] for angle in pack["angles"]}
                self.assertNotIn("rottura-di-metodo", kinds)

    def test_a_family_without_metadata_gets_no_invented_break(self):
        self.assertIsNone(build.source_note("bes", "10AMB001P"))


class ItIsDeterministic(unittest.TestCase):
    def test_the_same_indicator_gives_the_same_pack_twice(self):
        """Due esecuzioni non devono produrre due articoli diversi."""
        first, second = pack_of("ter-920"), pack_of("ter-920")
        self.assertEqual(first["angles"], second["angles"])
        self.assertEqual(first["total_strength"], second["total_strength"])


if __name__ == "__main__":
    unittest.main()
