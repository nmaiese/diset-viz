"""La verifica della pubblicazione sul sito (§8), senza rete.

Il nucleo (`page_signature`, `match_signature`) e' puro, il recupero HTTP e'
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

    def test_without_slug_it_is_the_code_only_form(self):
        # la forma che l'app serve e 301 reindirizza alla canonica
        url = v.build_url("ter-651", base="https://x.it")
        self.assertEqual(url, "https://x.it/indicatore/ter-651")


class ProofRegister(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.root = Path(tempfile.mkdtemp())

    def test_proof_carries_the_prose_fingerprint(self):
        from scripts import verification_queue
        result = {"code": "ter-651", "ok": True, "snippet_ok": True,
                  "vintage_ok": True, "url": "http://x", "reason": "combacia"}
        proof = v.build_proof(ENTRY, result, level="regione", at="2026-07-28")
        self.assertEqual(proof["prosa"], verification_queue.prose_fingerprint(ENTRY))
        self.assertEqual(proof["vintage"], "2023")
        self.assertTrue(proof["ok"])

    def test_write_and_load_round_trip(self):
        result = {"code": "ter-651", "ok": True, "url": "http://x", "reason": "combacia"}
        v.write_proof(v.build_proof(ENTRY, result, at="2026-07-28"), root=self.root)
        loaded = v.load_proofs(root=self.root)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["code"], "ter-651")

    def test_missing_register_reads_empty(self):
        self.assertEqual(v.load_proofs(root=self.root / "nope"), [])


if __name__ == "__main__":
    unittest.main()
