"""La coda anti-serialita': quali articoli si somigliano troppo.

Nessun articolo e' seriale da solo, lo e' rispetto a un altro, quindi le prove
sono su coppie sintetiche: due testi che condividono l'attacco o il corpo devono
salire in coda, due che parlano di cose diverse no.
"""

from __future__ import annotations

import unittest

from scripts import seriality_queue as sq


def _entry(lead, bodies, headings=None):
    headings = headings or [None] * len(bodies)
    roles = ("definizione", "quadro", "dinamica", "limiti")
    return {
        "lead": lead,
        "sections": [{"role": roles[i], "h": headings[i], "body": bodies[i]}
                     for i in range(len(bodies))],
    }


class TheProfileIsStyleNotContent(unittest.TestCase):
    def test_a_fully_composed_article_has_no_profile(self):
        # Nessuna prosa d'autore: lo scheletro composto e' uguale per tutti apposta.
        self.assertIsNone(sq._profile({"lead": "", "sections": []}))

    def test_short_function_words_do_not_count(self):
        # "di", "che", "la" non discriminano: sotto la soglia di lunghezza.
        self.assertEqual(sq._tokens("di che la per un"), set())
        self.assertIn("regione", sq._tokens("nella regione"))


class SerialPairsRiseToTheTop(unittest.TestCase):
    def _queue(self, texts):
        return sq.build_queue(texts)

    def test_two_articles_with_the_same_lead_are_serial(self):
        lead = "In cima alla classifica il divario tra le regioni resta immobile da anni."
        texts = {
            "1": _entry(lead, ["Corpo uno distinto sulla natalita."]),
            "2": _entry(lead, ["Corpo due distinto sulla mortalita."]),
            "3": _entry("Un attacco completamente diverso sulla ricerca.",
                        ["Corpo tre sulla spesa in laboratori."]),
        }
        rows = {r["code"]: r for r in self._queue(texts)}
        self.assertTrue(rows["ter-1"]["serial"])
        self.assertEqual(rows["ter-1"]["peer"], "ter-2")
        self.assertGreaterEqual(rows["ter-1"]["lead_sim"], sq.LEAD_SIM)

    def test_an_article_with_no_close_peer_is_not_serial(self):
        texts = {
            "1": _entry("Attacco sulla natalita regionale nel Mezzogiorno.",
                        ["Corpo sulla fecondita e le nascite."]),
            "2": _entry("Attacco sulla ricerca e sviluppo nelle imprese del Nord.",
                        ["Corpo sui laboratori e i brevetti."]),
        }
        rows = {r["code"]: r for r in self._queue(texts)}
        self.assertFalse(rows["ter-1"]["serial"])
        self.assertFalse(rows["ter-2"]["serial"])

    def test_identical_heading_sequences_are_measured(self):
        headings = ["Che cosa misura", "Il quadro", "La dinamica", "I limiti"]
        texts = {
            "1": _entry("Attacco alfa sulle nascite.",
                        ["a", "b", "c", "d"], headings),
            "2": _entry("Attacco beta sulle morti.",
                        ["e", "f", "g", "h"], headings),
        }
        rows = {r["code"]: r for r in self._queue(texts)}
        self.assertEqual(rows["ter-1"]["headings_sim"], 1.0)

    def test_the_queue_is_ordered_by_similarity(self):
        lead = "Lo stesso identico attacco ripetuto su due articoli diversi qui."
        texts = {
            "1": _entry(lead, ["corpo distinto uno"]),
            "2": _entry(lead, ["corpo distinto due"]),
            "3": _entry("Attacco unico sulla mobilita urbana e i trasporti.",
                        ["corpo unico sui pendolari"]),
        }
        rows = self._queue(texts)
        self.assertGreaterEqual(rows[0]["score"], rows[-1]["score"])


if __name__ == "__main__":
    unittest.main()
