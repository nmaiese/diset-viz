"""Le definizioni a portata di mano (`app/design/terms.py`, `ui.term`)."""

import unittest

from app import app
from app.design import terms


class TestTerms(unittest.TestCase):
    def test_i_testi_rispettano_la_punteggiatura_del_sito(self):
        for key, entry in terms.TERMS.items():
            with self.subTest(term=key):
                for bad in ("—", "–", ";", "…"):
                    self.assertNotIn(bad, entry["text"])
                self.assertTrue(entry["href"].startswith("/metodologia"))

    def test_ogni_richiamo_ha_un_popover_suo(self):
        a, b = terms.term("verso"), terms.term("verso")
        self.assertNotEqual(a["id"], b["id"])
        self.assertIsNone(terms.term("inesistente"))

    def test_la_macro_apre_il_popover_giusto(self):
        with app.app_context():
            tpl = app.jinja_env.from_string('{% import "v1/_ui.html" as ui %}{{ ui.term("nd") }}')
            html = tpl.render()
        self.assertIn('class="term" popovertarget="def-nd-', html)
        self.assertIn('popover style="position-anchor: --def-nd-', html)
        self.assertIn("n.d.", html)


if __name__ == "__main__":
    unittest.main()
