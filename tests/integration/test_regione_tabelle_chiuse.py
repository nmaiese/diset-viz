"""Esperimento: le tabelle lunghe della pagina regione, chiuse solo su due regioni.

Il resto del sito non deve accorgersene: la pagina di una regione fuori
dall'elenco e' identica a quella resa con l'elenco vuoto, e su una regione
dell'esperimento il contenuto resta nell'HTML, solo avvolto in un `<details>`.
"""
import re
import unittest
from unittest import mock

from app import app
from app.design.pages import regione as regione_page

APEX = "https://divarioitalia.it"


def _html(key, chiuse):
    with mock.patch.object(regione_page, "REGIONI_TABELLE_CHIUSE", frozenset(chiuse)):
        response = app.test_client().get(f"/regione/{key}", base_url=APEX)
    assert response.status_code == 200
    return response.get_data(as_text=True)


class TestRegioneTabelleChiuse(unittest.TestCase):
    def test_l_esperimento_riguarda_solo_due_regioni(self):
        self.assertEqual(regione_page.REGIONI_TABELLE_CHIUSE, {"molise", "valle-d-aosta"})

    def test_regione_fuori_elenco_identica_con_elenco_vuoto(self):
        con = _html("lombardia", {"molise", "valle-d-aosta"})
        senza = _html("lombardia", set())
        self.assertEqual(con, senza)
        self.assertNotIn("indicatori-tabelle", con)
        self.assertNotIn("regione-tabelle", con)

    def test_regione_dell_esperimento_ha_i_blocchi_chiusi_con_tutte_le_righe(self):
        for key in ("molise", "valle-d-aosta"):
            with self.subTest(key=key):
                esperimento = _html(key, {key})
                base = _html(key, set())
                # Chiusi: nessun attributo `open`, e nessun nascondimento via CSS o JS.
                aperture = re.findall(r'<details class="more regione-tabelle"[^>]*>', esperimento)
                self.assertTrue(aperture)
                self.assertTrue(all(" open" not in tag for tag in aperture))
                self.assertIn('id="indicatori-tabelle"', esperimento)
                self.assertRegex(esperimento, r"<summary>I <data[^>]*>\d+</data> indicatori [^<]*</summary>")
                self.assertNotIn("display:none", esperimento.split('id="indicatori-tabelle"')[1][:2000])
                # Il contenuto resta: stesso numero di righe e di tabelle.
                self.assertEqual(esperimento.count("data-rf-row"), base.count("data-rf-row"))
                self.assertEqual(esperimento.count("<table"), base.count("<table"))
                # Solo wrapper e script in piu': tolti, si torna alla pagina di base.
                pulita = re.sub(r'<details class="more regione-tabelle"[^>]*><summary>.*?</summary>', "", esperimento)
                pulita = pulita.replace("\n    </details>\n  </section>", "\n    \n  </section>")
                pulita = re.sub(r"<script>\n/\* Esperimento:.*?</script>\n", "", pulita, flags=re.S)
                self.assertEqual(pulita, base)


if __name__ == "__main__":
    unittest.main()
