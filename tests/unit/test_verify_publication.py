"""La verifica della pubblicazione sul sito (§8), senza rete.

Il nucleo (`page_signature`, `match_signature`) e' puro; il recupero HTTP e'
provato con un fetcher iniettato, cosi' il test non tocca la rete e verifica la
regola di prudenza: un controllo che non ha potuto girare non passa.
"""

import unittest

from scripts import verify_publication as v


ENTRY = {
    "lead": "Nella spesa in ricerca e sviluppo il divario fra Nord e Sud resta ampio",
    "vintage": 2023,
    "sections": [],
}


class Signature(unittest.TestCase):
    def test_signature_is_lead_snippet_plus_vintage(self):
        sig = v.page_signature(ENTRY)
        self.assertTrue(sig["snippet"].startswith("nella spesa in ricerca"))
        self.assertEqual(sig["vintage"], "2023")

    def test_match_needs_both_snippet_and_year(self):
        sig = v.page_signature(ENTRY)
        page = ("<html><body><h1>R&S</h1><p>Nella spesa in ricerca e sviluppo il "
                "divario fra Nord e Sud resta ampio nel 2023.</p></body></html>")
        self.assertTrue(v.match_signature(page, sig)["ok"])

    def test_year_present_but_text_absent_does_not_match(self):
        sig = v.page_signature(ENTRY)
        self.assertFalse(v.match_signature("<p>Un altro testo del 2023</p>", sig)["ok"])

    def test_text_present_but_wrong_year_does_not_match(self):
        sig = v.page_signature(ENTRY)
        page = "<p>Nella spesa in ricerca e sviluppo il divario fra Nord e Sud resta ampio nel 2019</p>"
        result = v.match_signature(page, sig)
        self.assertTrue(result["snippet_ok"])
        self.assertFalse(result["vintage_ok"])
        self.assertFalse(result["ok"])


class Verify(unittest.TestCase):
    def test_matching_page_is_ok_true(self):
        page = ("<p>Nella spesa in ricerca e sviluppo il divario fra Nord e Sud "
                "resta ampio, dato 2023.</p>")
        self.assertTrue(v.verify("http://x", ENTRY, fetcher=lambda u: page)["ok"])

    def test_wrong_version_is_ok_false(self):
        self.assertFalse(v.verify("http://x", ENTRY, fetcher=lambda u: "<p>vuoto</p>")["ok"])

    def test_unreachable_is_ok_none_not_a_pass(self):
        def boom(url):
            raise OSError("nessuna rete")
        result = v.verify("http://x", ENTRY, fetcher=boom)
        self.assertIsNone(result["ok"])
        self.assertEqual(result["reason"], "irraggiungibile")


class Url(unittest.TestCase):
    def test_build_url_puts_code_last(self):
        url = v.build_url("eur-rd_e_gerdreg", slug="spesa-ricerca", base="https://x.it")
        self.assertEqual(url, "https://x.it/indicatore/spesa-ricerca/eur-rd_e_gerdreg")


if __name__ == "__main__":
    unittest.main()
