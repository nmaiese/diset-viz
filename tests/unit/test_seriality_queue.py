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

    def test_a_body_match_over_threshold_beats_a_higher_lead_match_under_it(self):
        """Le due soglie sono diverse, quindi i due numeri grezzi non si
        confrontano fra loro: un attacco a 0,44 e' sotto la sua soglia, un corpo
        a 0,42 e' sopra la sua. Tenendo il vicino col numero piu' alto la coppia
        seriale vera veniva sostituita da una non seriale, e poi `serial()` la
        scartava: la coppia spariva dalla coda invece di finirci.
        """
        lead_sim, body_sim = 0.44, 0.42
        self.assertLess(lead_sim, sq.LEAD_SIM)      # sotto soglia
        self.assertGreater(body_sim, sq.BODY_SIM)   # sopra soglia
        self.assertGreater(lead_sim, body_sim)      # eppure il numero e' piu' grande
        self.assertGreater(sq._pressure(0.0, body_sim), sq._pressure(lead_sim, 0.0))
        self.assertGreaterEqual(sq._pressure(0.0, body_sim), 1.0)
        self.assertLess(sq._pressure(lead_sim, 0.0), 1.0)

    def test_the_serial_pair_survives_a_higher_scoring_peer_under_threshold(self):
        """La stessa cosa dalla coda, non dall'aritmetica: `1` e `2` condividono
        il corpo sopra soglia, `3` ha con `1` un attacco piu' simile in valore ma
        sotto la sua soglia. La riga di `1` deve restare la coppia seriale."""
        shared_body = ("Le regioni meridionali restano distanti dalla media nazionale "
                       "mentre il divario territoriale non si chiude affatto.")
        texts = {
            "1": _entry("Attacco primo sulle nascite regionali.", [shared_body]),
            "2": _entry("Attacco secondo sulla mortalita regionale.", [shared_body]),
            "3": _entry("Attacco primo sulle nascite provinciali.",
                        ["Corpo terzo, sui laboratori e i brevetti depositati."]),
        }
        rows = {r["code"]: r for r in self._queue(texts)}
        self.assertEqual(rows["ter-1"]["peer"], "ter-2")
        self.assertTrue(rows["ter-1"]["serial"])
        self.assertEqual([r["code"] for r in sq.serial(self._queue(texts))][:2],
                         ["ter-1", "ter-2"])

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
