"""La scelta dell'esempio: deterministica, esistente, e non sempre la stessa.

Il difetto che questa mappa corregge e' lo stesso di tutta la rifondazione: se
la scelta la fa il modello, il modello sceglie quasi sempre uguale, e
l'uniformita' rientra da una porta che nessuno guardava.

Sintetico soltanto: la misura su sessanta pacchetti veri sta in
`tests/integration/test_officina_esempi_live.py`.
"""
import unittest

from officina import esempi


class TheMapPointsAtRealFiles(unittest.TestCase):
    def test_every_mapped_extract_exists(self):
        missing = sorted({name for name in esempi.BY_ANGLE.values()
                          if name not in esempi.available()})
        self.assertEqual(missing, [], f"estratti mappati e assenti: {missing}")

    def test_a_fixed_strength_angle_cannot_be_missing_from_the_map(self):
        """Un tipo a forza fissa e alta apre quasi sempre, quindi non mapparlo
        non e' una lacuna qualunque: `pick()` scenderebbe a un angolo piu'
        debole o all'estratto del "nessuna storia" proprio sull'articolo in cui
        la storia era la piu' forte."""
        for tipo in ("gruppi-che-si-sorpassano", "sorpasso"):
            self.assertIn(tipo, esempi.BY_ANGLE, tipo)

    def test_the_fallback_exists_too(self):
        self.assertIn(esempi.WHEN_THERE_IS_NO_STORY, esempi.available())

    def test_the_library_is_not_mostly_unused(self):
        """Una biblioteca di dieci testi con due usati e' una biblioteca finta."""
        used = set(esempi.BY_ANGLE.values()) | {esempi.WHEN_THERE_IS_NO_STORY}
        self.assertGreaterEqual(len(used), 5,
                                f"solo {len(used)} estratti raggiungibili")


class Picking(unittest.TestCase):
    def test_the_strongest_angle_decides(self):
        angles = [{"type": "graduatoria-spezzata"}, {"type": "sorpasso"}]
        self.assertEqual(esempi.pick(angles), "infodata-mortalita-comuni.md")

    def test_a_different_story_gets_a_different_model(self):
        """Il punto di tutta la mappa, in un test."""
        ranking = esempi.pick([{"type": "graduatoria-spezzata"}])
        over_time = esempi.pick([{"type": "rottura-di-pendenza"}])
        outlier = esempi.pick([{"type": "valore-fuori-scala"}])
        self.assertEqual(len({ranking, over_time, outlier}), 3)

    def test_an_unmapped_type_falls_to_the_next_angle_not_to_the_fallback(self):
        angles = [{"type": "tipo-nuovo-mai-visto"}, {"type": "sorpasso"}]
        self.assertEqual(esempi.pick(angles), "pagellapolitica-record-occupati.md")

    def test_no_angles_means_no_article(self):
        """Un indicatore senza storia si scrive come un comunicato asciutto."""
        self.assertEqual(esempi.pick([]), esempi.WHEN_THERE_IS_NO_STORY)
        self.assertEqual(esempi.pick(None), esempi.WHEN_THERE_IS_NO_STORY)

    def test_it_is_deterministic(self):
        angles = [{"type": "controcorrente"}]
        self.assertEqual(esempi.pick(angles), esempi.pick(angles))

if __name__ == "__main__":
    unittest.main()
