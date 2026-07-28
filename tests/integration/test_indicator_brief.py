"""The editorial brief, and in particular the block that makes a cross-reference possible.

The rest of the brief reformats numbers the page already computes, so it cannot
disagree with the page and does not need a guard. The related-indicators block is
different: it is arithmetic this file does itself, on series from every family,
and a rank correlation that is quietly wrong would not look wrong. It would look
like an insight, get written into an article as "va di pari passo con", and pass
every other guard in the suite.
"""

import unittest

from scripts import indicator_brief


class KnownErrorsRegister(unittest.TestCase):
    """Il registro errori (learning loop): le smentite confermate, a cerchi
    concentrici. Vista pura su una lista di verifiche sintetiche."""

    VERIFICHE = [
        {"code": "eur-rd_e_gerdreg", "esito": "smentito", "smentite": "1",
         "at": "2026-07-27", "rilievi": "fonti/grave: il Lazio non e' al Nord"},
        {"code": "eur-rd_p_persreg", "esito": "smentito", "smentite": "2",
         "at": "2026-07-20", "rilievi": "causale/media: una causa inventata; universale/lieve: 'tutte' e' falso"},
        {"code": "ter-651", "esito": "smentito", "smentite": "1",
         "at": "2026-07-18", "rilievi": "provincia/grave: una cifra provinciale sbagliata"},
        {"code": "ter-12", "esito": "confermato", "smentite": "0", "rilievi": ""},
    ]

    def test_classes_are_read_from_the_rilievi_prefix(self):
        classes = indicator_brief._classes_in(
            "causale/media: x; universale/lieve: y")
        self.assertEqual(classes, ["causale", "universale"])

    def test_a_smentita_on_this_indicator_is_the_strongest_signal(self):
        ke = indicator_brief._known_errors("eur-rd_e_gerdreg", self.VERIFICHE)
        self.assertEqual(len(ke["on_this"]), 1)
        self.assertIn("fonti", ke["on_this"][0]["classes"])

    def test_the_family_ring_gathers_classes_from_siblings(self):
        # eur-rd_e_gerdreg: nella stessa famiglia (eur-) c'e' rd_p_persreg,
        # con causale e universale.
        ke = indicator_brief._known_errors("eur-rd_e_gerdreg", self.VERIFICHE)
        fam = dict(ke["family_classes"])
        self.assertIn("causale", fam)
        self.assertIn("universale", fam)
        self.assertNotIn("fonti", fam)   # fonti e' su questo indicatore, non nel giro famiglia

    def test_only_confirmed_smentite_count(self):
        # la riga 'confermato' (ter-12) non entra da nessuna parte
        ke = indicator_brief._known_errors("ter-12", self.VERIFICHE)
        self.assertEqual(ke["count"], 3)   # tre smentite, non quattro righe
        self.assertEqual(ke["on_this"], [])

    def test_recurring_counts_across_the_whole_chain(self):
        ke = indicator_brief._known_errors("ter-651", self.VERIFICHE)
        rec = dict(ke["recurring"])
        self.assertEqual(rec.get("fonti"), 1)
        self.assertEqual(rec.get("causale"), 1)
        self.assertEqual(rec.get("provincia"), 1)


class SpearmanArithmetic(unittest.TestCase):
    def test_a_perfectly_monotonic_pair_is_one(self):
        first = {f"r{i}": i for i in range(20)}
        second = {f"r{i}": i * 3 + 7 for i in range(20)}
        rho, count = indicator_brief._spearman(first, second)
        self.assertEqual(count, 20)
        self.assertAlmostEqual(rho, 1.0, places=6)

    def test_a_reversed_pair_is_minus_one(self):
        first = {f"r{i}": i for i in range(20)}
        second = {f"r{i}": -i for i in range(20)}
        rho, _ = indicator_brief._spearman(first, second)
        self.assertAlmostEqual(rho, -1.0, places=6)

    def test_ties_share_an_average_rank(self):
        """Two regions on the same rounded value is routine, not a corner case.

        Breaking the tie by dictionary order would make rho depend on the region
        names, so the same pair of series would score differently depending on
        which one was briefed.
        """
        self.assertEqual(indicator_brief._average_ranks([5, 5, 9]), [1.5, 1.5, 3.0])
        self.assertEqual(indicator_brief._average_ranks([1, 2, 3]), [1.0, 2.0, 3.0])
        forward = indicator_brief._spearman(
            {"a": 1, "b": 1, "c": 2, **{f"r{i}": i + 10 for i in range(12)}},
            {"a": 5, "b": 5, "c": 6, **{f"r{i}": i + 20 for i in range(12)}},
        )
        self.assertAlmostEqual(forward[0], 1.0, places=6)

    def test_too_few_shared_regions_is_no_answer_rather_than_a_weak_one(self):
        """Five regions in common produce a rho that means nothing, and printing
        it next to one computed on twenty would invite the same sentence."""
        rho, count = indicator_brief._spearman(
            {f"r{i}": i for i in range(5)}, {f"r{i}": i for i in range(5)}
        )
        self.assertIsNone(rho)
        self.assertEqual(count, 5)

    def test_a_flat_series_has_no_order_to_correlate(self):
        rho, _ = indicator_brief._spearman(
            {f"r{i}": i for i in range(20)}, {f"r{i}": 4 for i in range(20)}
        )
        self.assertIsNone(rho)


class RelatedIndicators(unittest.TestCase):
    """Against the real catalogue, because the value of the block is that it
    reaches every family: the theme is shared across territorial, BES,
    Multiscopo and the external ones, and a cross-reference that could only see
    its own family would miss the strongest half of the atlas."""

    @classmethod
    def setUpClass(cls):
        cls.brief = indicator_brief.build_brief("territorial", "178")

    def test_the_brief_carries_the_theme_hub_and_the_groups(self):
        related = self.brief["related"]
        self.assertEqual(related["hub"]["path"], "/tema/lavoro-e-conciliazione")
        self.assertEqual(set(related["groups"]), {"stessa", "opposta", "diversa"})
        self.assertGreater(related["theme_size"], 10)

    def test_every_suggested_path_is_the_canonical_one(self):
        """The writer links what the brief prints, so a wrong path here becomes a
        wrong link in published prose. The path is taken from the catalog and
        never rebuilt, which is what this pins."""
        from app.atlas_catalog import get_atlas_catalog

        canonical = {item["path"] for item in get_atlas_catalog()["indicators"]}
        for rows in self.brief["related"]["groups"].values():
            for row in rows:
                with self.subTest(indicator=row["id"]):
                    self.assertIn(row["path"], canonical)
                    self.assertTrue(row["path"].startswith("/indicatore/"))

    def test_an_indicator_is_never_related_to_itself(self):
        suggested = [
            row["id"] for rows in self.brief["related"]["groups"].values() for row in rows
        ]
        self.assertNotIn("178", suggested)
        self.assertEqual(len(suggested), len(set(suggested)))

    def test_the_groups_hold_what_they_claim_to_hold(self):
        groups = self.brief["related"]["groups"]
        for row in groups["stessa"]:
            self.assertGreaterEqual(row["rho"], indicator_brief.SAME_MAP)
        for row in groups["opposta"]:
            self.assertLessEqual(row["rho"], -indicator_brief.SAME_MAP)
        for row in groups["diversa"]:
            self.assertLess(abs(row["rho"]), indicator_brief.DIFFERENT_MAP)

    def test_the_near_twins_do_not_lead_the_group(self):
        """Ranking "same map" by rho alone filled it with the same measurement
        cut a second way, and an article cross-referencing one of those has said
        nothing. Distinct indicators come first."""
        same = self.brief["related"]["groups"]["stessa"]
        self.assertTrue(same, "female employment has same-map siblings")
        twins = [abs(row["rho"]) >= indicator_brief.TWIN_RHO for row in same]
        self.assertEqual(twins, sorted(twins), "twins must sort after the distinct ones")

    def test_an_inverse_twin_carries_the_warning_too(self):
        """A complement is a duplicate: `ter-9` is a hundred minus `ter-385`.

        `_strongest` has always demoted twins on the absolute rho, so the pair
        already sorted to the back of the group. The printed warning tested the
        signed rho, so the one case where the duplication is total, rho exactly
        -1,00, reached the writer looking like independent evidence.
        """
        brief = indicator_brief.build_brief("territorial", "385")
        opposite = brief["related"]["groups"]["opposta"]
        inverse_twin = [row for row in opposite if row["id"] == "9"]
        self.assertTrue(inverse_twin, "ter-9 must be among the correlates of ter-385")
        self.assertLessEqual(inverse_twin[0]["rho"], -indicator_brief.TWIN_RHO)

        lines = indicator_brief._render_related(brief).splitlines()
        marked = [line for line in lines if "misurata due volte" in line]
        self.assertTrue(
            any("-1,00" in line for line in marked),
            f"the inverse twin is not marked: {marked}",
        )

    def test_the_two_extremes_are_placed_on_the_other_scale(self):
        """This is what turns a correlation into a sentence someone can write."""
        rows = [row for rows in self.brief["related"]["groups"].values() for row in rows]
        placed = [
            anchor for row in rows for anchor in row["anchors"] if anchor.get("rank")
        ]
        self.assertTrue(placed)
        for anchor in placed:
            self.assertGreaterEqual(anchor["rank"], 1)
            self.assertLessEqual(anchor["rank"], anchor["of"])

    def test_the_block_renders_without_a_theme(self):
        """A themeless indicator has no siblings, and the brief has to say so
        rather than fail: the writer runs this before every article."""
        empty = {"related": {"hub": None, "groups": {}, "self_year": None},
                 "level": {"key": "regione"}}
        self.assertIn("non ha un tema", indicator_brief._render_related(empty))


if __name__ == "__main__":
    unittest.main()
