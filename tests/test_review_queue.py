"""The reviewer's worklist: which written articles are most likely to be wrong.

Logic-only, on synthetic entries, so it never depends on what the live
indicator_texts.json happens to contain today.

The patterns here are not style preferences. Each one is a class of claim the
mechanical guards in tests/test_indicator_texts.py cannot check and that
docs/INDICATOR_PAGES.md lists as needing eyes: a universal statement one
counter-example would break, a causal mechanism the indicator does not measure,
a comparison outside the dataset with no source, a provincial figure the region
regex cannot read, and a figure the cockpit already prints.
"""

import unittest

from scripts import review_queue


def _view(level_key="regione", indexable=True, avg=40.73, best=48.30, worst=32.70):
    return {
        "meta": {
            "family": "territorial", "raw_id": "178", "name": "Un indicatore",
            "indexable": indexable, "quality_life_scored": False,
        },
        "levels": [{
            "key": level_key,
            "stats": {"year_avg": avg, "gap_abs": 15.60},
            "best": {"value": best}, "worst": {"value": worst},
            "annual_change": {"average_delta": 0.74},
        }],
    }


def _entry(body, **extra):
    return {"lead": "Un lead.", "sections": [{"role": "quadro", "h": None, "body": body}], **extra}


class RiskFlags(unittest.TestCase):
    def flags(self, body, view=None, **extra):
        row = review_queue.assess("178", _entry(body, **extra), view or _view())
        return row["flags"]

    def test_a_universal_claim_is_flagged(self):
        self.assertIn("universale", self.flags("Il valore è cresciuto ovunque."))
        self.assertIn("universale", self.flags("Da anni la Lombardia guida."))

    def test_a_causal_mechanism_is_flagged(self):
        self.assertIn("causale", self.flags("Il divario dipende dalle imprese del Nord."))
        self.assertIn("causale", self.flags("Cresce grazie agli investimenti pubblici."))

    def test_a_comparison_outside_the_dataset_needs_a_source(self):
        body = "È il valore più alto d'Europa."
        self.assertIn("esterno", self.flags(body))
        with_source = review_queue.assess(
            "178", _entry(body, fonti=[{"testo": "Eurostat", "url": "https://ec.europa.eu"}]), _view(),
        )
        self.assertNotIn("esterno", with_source["flags"],
                         "a verified source is exactly what clears this claim")

    def test_provincial_figures_are_flagged_because_no_guard_reads_them(self):
        body = "Il valore arriva a 15,50 nel capoluogo."
        self.assertNotIn("provincia", self.flags(body))
        provincial = review_queue.assess(
            "bes:10AMB008", _entry(body, level="provincia"), _view("provincia"),
        )
        self.assertIn("provincia", provincial["flags"])

    def test_a_figure_the_cockpit_prints_is_flagged_as_an_echo(self):
        """Correct but redundant: the layout was rebuilt to show a figure once."""
        self.assertIn("eco", self.flags("La media è 40,73."))
        self.assertNotIn("eco", self.flags("La mediana è 41,10."))

    def test_a_clean_article_carries_no_flags(self):
        self.assertEqual(self.flags("La Sardegna ha guadagnato 11,00 punti in dieci anni."), {})


class ReadingOrder(unittest.TestCase):
    def test_a_causal_claim_outranks_an_echo(self):
        causal = review_queue.assess("178", _entry("Cresce grazie agli incentivi."), _view())
        echo = review_queue.assess("178", _entry("La media è 40,73."), _view())
        self.assertGreater(causal["score"], echo["score"])

    def test_an_indexable_page_outranks_a_noindex_one_with_the_same_flags(self):
        body = "Il valore è cresciuto ovunque."
        yes = review_queue.assess("178", _entry(body), _view(indexable=True))
        no = review_queue.assess("178", _entry(body), _view(indexable=False))
        self.assertGreater(yes["score"], no["score"])

    def test_a_reviewed_article_leaves_the_reading_order(self):
        entry = _entry("Cresce grazie agli incentivi.", reviewed_at="2026-07-26")
        row = review_queue.assess("178", entry, _view())
        self.assertEqual(row["score"], 0)
        self.assertEqual(row["reviewed_at"], "2026-07-26")
        self.assertIn("causale", row["flags"], "the flag stays visible, only the priority drops")


class TheSignatureExpiresWithTheData(unittest.TestCase):
    """Re-entry: the half of the chain that makes it work on published pages.

    A reviewer signs a text *and* the numbers under it. When the source
    publishes a new year the writer refreshes the article, every figure in it
    changes, and the signature now covers sentences nobody has read. Without
    this the reading order drains once and never refills: the chain reports
    itself finished while the catalogue ages underneath it.
    """

    def test_an_article_refreshed_after_its_review_comes_back(self):
        entry = _entry(
            "Un testo pulito.", reviewed_at="2026-07-26", reviewed_vintage=2023, vintage=2024
        )
        row = review_queue.assess("178", entry, _view())
        self.assertIn("rilettura", row["flags"])
        self.assertGreater(row["score"], 0)
        self.assertEqual(row["reviewed_at"], "", "torna in coda come non firmato")

    def test_an_article_whose_data_has_not_moved_stays_out(self):
        """The churn this rule must not reintroduce. A series that published
        nothing new has nothing new to read, and re-reading it on a timer is
        the failure `curate.uncurated_targets` was already fixed for once."""
        entry = _entry(
            "Un testo pulito.", reviewed_at="2026-07-26", reviewed_vintage=2023, vintage=2023
        )
        row = review_queue.assess("178", entry, _view())
        self.assertNotIn("rilettura", row["flags"])
        self.assertEqual(row["score"], 0)
        self.assertEqual(row["reviewed_at"], "2026-07-26")

    def test_a_signature_that_never_recorded_a_vintage_is_not_trusted(self):
        """Unknown means "written before anyone recorded what was read", and the
        safe reading of unknown is re-read once, not trust forever."""
        entry = _entry("Un testo pulito.", reviewed_at="2026-07-26", vintage=2023)
        row = review_queue.assess("178", entry, _view())
        self.assertIn("rilettura", row["flags"])

    def test_a_re_read_outranks_every_risk_flag(self):
        stale = review_queue.assess(
            "178",
            _entry("Un testo pulito.", reviewed_at="2026-07-26", reviewed_vintage=2023, vintage=2024),
            _view(),
        )
        causal = review_queue.assess("178", _entry("Cresce grazie agli incentivi."), _view())
        self.assertGreater(stale["score"], causal["score"])


class QueueAgainstTheLiveFile(unittest.TestCase):
    def test_the_queue_builds_over_the_committed_articles(self):
        rows = review_queue.build_queue()
        self.assertGreater(len(rows), 100)
        for row in rows[:20]:
            self.assertIn(row["level"], ("regione", "provincia"))
            self.assertTrue(row["code"])
            self.assertTrue(set(row["flags"]) <= set(review_queue.FLAG_LABELS))


if __name__ == "__main__":
    unittest.main()
