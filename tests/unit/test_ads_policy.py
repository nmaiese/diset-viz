"""La regola degli annunci: dove un'unita' potra' comparire, e dove mai.

`ads_allowed` e' la funzione unica che decide. Oggi il sito carica solo il
loader AdSense e nessuna unita': questa prova fissa la regola per quando le
unita' arriveranno, cosi' nessuno le metta su schermate di interfaccia o sotto
la soglia di testo editoriale.
"""

import unittest

from app.ads_policy import MIN_WORDS, ads_allowed


class LaRegolaDegliAnnunci(unittest.TestCase):
    def test_un_articolo_e_sempre_ammesso(self):
        self.assertTrue(ads_allowed("blog"))

    def test_le_interfacce_non_sono_mai_ammesse(self):
        for page in ("atlas", "search", "game", "account", "legacy", "error"):
            with self.subTest(page=page):
                self.assertFalse(ads_allowed(page))

    def test_quiz_e_atlante_sono_falsi(self):
        self.assertFalse(ads_allowed("game"))
        self.assertFalse(ads_allowed("atlas"))

    def test_una_pagina_editoriale_sopra_soglia_e_ammessa(self):
        self.assertTrue(ads_allowed("indicator", 800))

    def test_una_pagina_editoriale_sotto_soglia_non_e_ammessa(self):
        self.assertFalse(ads_allowed("indicator", 300))

    def test_la_soglia_esatta_e_ammessa(self):
        self.assertTrue(ads_allowed("region", MIN_WORDS))

    def test_senza_il_numero_di_parole_e_falsa(self):
        """Non si rischia: se il conteggio manca, gli annunci restano spenti."""
        self.assertFalse(ads_allowed("indicator"))


if __name__ == "__main__":
    unittest.main()
