import unittest

from scripts.ci.controlla_pr_contenuti import controlla_pr


class ControllaPRContenutiTest(unittest.TestCase):
    def test_post_senza_riferimento_issue_fallisce(self):
        self.assertIn("manca", controlla_pr("testo", ["run:blog"], ["A\tcontent/posts/x.md"])[0])

    def test_post_senza_label_run_fallisce(self):
        self.assertIn("label", controlla_pr("Closes #4", [], ["A\tcontent/posts/x.md"])[0])

    def test_post_con_issue_e_label_passa(self):
        self.assertEqual([], controlla_pr("Closes #4", ["run:blog"], ["A\tcontent/posts/x.md"]))

    def test_refs_e_label_passano(self):
        self.assertEqual([], controlla_pr("Refs #12", ["run:team"], ["A\tcontent/indicators/x.md"]))

    def test_solo_app_non_richiede_metadati(self):
        self.assertEqual([], controlla_pr(None, [], ["M\tapp/x.py"]))

    def test_cancellazione_sola_contenuto_non_richiede_metadati(self):
        self.assertEqual([], controlla_pr(None, [], ["D\tcontent/posts/x.md"]))

    def test_riferimento_case_insensitive(self):
        self.assertEqual([], controlla_pr("closes #5", ["run:lite"], ["M\tcontent/posts/x.md"]))

    def test_closes_senza_numero_non_basta(self):
        self.assertIn("manca", controlla_pr("Closes", ["run:routine"], ["M\tcontent/posts/x.md"])[0])

    def test_corpo_vuoto_o_none_non_basta(self):
        for body in ("", None):
            with self.subTest(body=body):
                self.assertIn("manca", controlla_pr(body, ["run:blog"], ["M\tcontent/posts/x.md"])[0])

    def test_label_run_case_insensitive(self):
        self.assertEqual([], controlla_pr("Fixes #3", ["RUN:Blog"], ["M\tcontent/posts/x.md"]))

    def test_rinomina_nel_contenuto_conta_destinazione(self):
        self.assertIn("manca", controlla_pr("body", ["run:blog"], ["R100\tapp/x.py\tcontent/posts/x.md"])[0])


if __name__ == "__main__":
    unittest.main()
