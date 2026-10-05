"""Test di scripts/misure/url_inspection.py: solo funzioni pure, senza rete né credenziali."""
import unittest

from scripts.misure import url_inspection as ui

BASE = "https://divarioitalia.it"


def _urls():
    out = [f"{BASE}/", f"{BASE}/atlante"]
    out += [f"{BASE}/indicatore/s{i}/ter-{i}" for i in range(30)]
    out += [f"{BASE}/indicatore/s{i}/ter-{i}/province" for i in range(30)]
    out += [f"{BASE}/regione/r{i}" for i in range(20)]
    out += [f"{BASE}/provincia/p{i}" for i in range(40)]
    out += [f"{BASE}/tema/t{i}" for i in range(10)]
    out += [f"{BASE}/blog/post-{i}" for i in range(25)]
    return out


class ClassifyTest(unittest.TestCase):
    def test_tipi(self):
        casi = {
            f"{BASE}/": "home",
            f"{BASE}/indicatore/lavoro/ter-105": "indicatore",
            f"{BASE}/indicatore/lavoro/ter-105/province": "indicatore_province",
            f"{BASE}/regione/lazio": "regione",
            f"{BASE}/provincia/roma": "provincia",
            f"{BASE}/tema/lavoro": "tema",
            f"{BASE}/blog/un-articolo": "blog",
            f"{BASE}/blog": "blog",
            f"{BASE}/atlante": "altro",
            f"{BASE}/temi": "altro",
        }
        for url, atteso in casi.items():
            with self.subTest(url=url):
                self.assertEqual(ui.classify(url), atteso)


class SampleTest(unittest.TestCase):
    def test_deterministico_col_seme(self):
        a = ui.sample_urls(_urls(), 5, 1, 100)
        b = ui.sample_urls(list(reversed(_urls())), 5, 1, 100)
        self.assertEqual(a, b)
        self.assertNotEqual(a, ui.sample_urls(_urls(), 5, 2, 100))

    def test_per_tipo(self):
        sample = ui.sample_urls(_urls(), 5, 1, 100)
        for t in ("indicatore", "regione", "provincia", "blog"):
            self.assertEqual(sum(1 for k, _ in sample if k == t), 5)
        self.assertEqual(sum(1 for k, _ in sample if k == "home"), 1)

    def test_rispetta_max(self):
        sample = ui.sample_urls(_urls(), 20, 1, 12)
        self.assertEqual(len(sample), 12)
        self.assertGreater(len({k for k, _ in sample}), 4)

    def test_mai_oltre_la_quota(self):
        self.assertLessEqual(len(ui.sample_urls(_urls(), 1000, 1, 10**6)), ui.DAILY_QUOTA)


class SummarizeTest(unittest.TestCase):
    def test_aggregazione(self):
        def resp(verdict, state, google=None, user=None):
            return {"inspectionResult": {"indexStatusResult": {
                "verdict": verdict, "coverageState": state,
                "googleCanonical": google, "userCanonical": user}}}
        k = "regione"
        rows = [
            ui.row_from_response("u1", k, resp("PASS", "Submitted and indexed", "u1", "u1")),
            ui.row_from_response("u2", k, resp("NEUTRAL", "Crawled - currently not indexed", "u2", "u2")),
            ui.row_from_response("u3", k, resp("NEUTRAL", "Crawled - currently not indexed", "x", "u3")),
            ui.row_from_response("u4", k, resp("NEUTRAL", "Discovered - currently not indexed")),
            ui.error_row("u5", k, "HTTP 500"),
        ]
        s = ui.summarize(rows)["regione"]
        self.assertEqual(s["ispezionate"], 4)
        self.assertEqual(s["errori"], 1)
        self.assertEqual(s["indicizzate"], 1)
        self.assertEqual(s["non_indicizzate"], 3)
        self.assertEqual(s["stati_non_indicizzate"][0], ("Crawled - currently not indexed", 2))
        self.assertEqual(s["canonical_diverso"], 1)
        self.assertIn("| regione | 4 | 1 | 3 |", ui.to_markdown({"regione": s}, "2026-10-05"))


if __name__ == "__main__":
    unittest.main()
