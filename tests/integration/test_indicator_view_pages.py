"""One template now serves 621 indicators across four families.

That is the whole point of the app/indicator_view.py refactor and also its main
risk: a field that is None for one family only (a province-only BES series has
no catalog metadata, so no source label) breaks a page no targeted test
happens to open. Exactly that shipped a 500 during this rebuild, caught only
because an unrelated assertion loaded the page.

This is the HTTP half of tests/unit/test_indicator_view.py's golden fixture:
it needs a real Flask request/response cycle for every indicator, so it lives
in tests/integration rather than next to the pure-arithmetic assertions.
Rendering all of them costs several seconds, which is worth paying, just not
on every edit-save cycle.
"""

import json
import re
import unittest
from pathlib import Path

from app import app, sources
from app.indicator_texts import ROLE_ORDER
from app.indicator_view import build_indicator_view

from tests.support import family_and_raw

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "indicator_stats_golden.json"


class EveryIndicatorPageRenders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(FIXTURE.read_text(encoding="utf-8"))
        app.config["PROPAGATE_EXCEPTIONS"] = True
        cls.client = app.test_client()

    def _get(self, indicator_id, query=""):
        family, raw_id = family_and_raw(indicator_id)
        url = sources.indicator_url(family, raw_id, "x") + query
        return self.client.get(url, follow_redirects=True)

    def test_every_indicator_page_returns_200(self):
        broken = []
        for indicator_id in self.golden:
            try:
                response = self._get(indicator_id)
                if response.status_code != 200:
                    broken.append((indicator_id, response.status_code))
            except Exception as error:  # noqa: BLE001 - the point is to report, not to raise
                broken.append((indicator_id, f"{type(error).__name__}: {error}"))
        self.assertEqual(broken, [], f"indicator pages that do not render: {broken[:10]}")

    def test_every_indicator_page_has_a_markdown_representation(self):
        broken = []
        for indicator_id in self.golden:
            try:
                response = self._get(indicator_id)
                canonical = response.request.path
                markdown = self.client.get(canonical, headers={"Accept": "text/markdown"})
                if markdown.status_code != 200 or not markdown.content_type.startswith("text/markdown"):
                    broken.append((indicator_id, markdown.status_code, markdown.content_type))
            except Exception as error:  # noqa: BLE001 - report every family failure together
                broken.append((indicator_id, f"{type(error).__name__}: {error}"))
        self.assertEqual(broken, [], f"indicator Markdown pages that do not render: {broken[:10]}")

    def test_every_page_carries_the_full_article_skeleton(self):
        missing = []
        for indicator_id in self.golden:
            html = self._get(indicator_id).get_data(as_text=True)
            for role in ROLE_ORDER:
                if f'id="sezione-{role}"' not in html:
                    missing.append((indicator_id, role))
        self.assertEqual(missing, [], f"pages missing an article section: {missing[:10]}")

    def test_the_historical_series_is_server_rendered_as_a_table(self):
        """Il grafico di trend e' uno <svg> riempito da JS: senza JavaScript il
        lettore e il crawler perderebbero la serie. La tabella-serie la porta a
        tutti, un anno per riga, e per una serie a un solo anno non compare."""
        multi = self._get("920").get_data(as_text=True)  # eta media, serie lunga
        self.assertIn('class="trend-table"', multi)
        rows = re.findall(r'<tr><th scope="row">(\d{4})</th><td>[^<]+</td>', multi)
        self.assertGreater(len(rows), 5)
        self.assertEqual(rows, sorted(rows))  # in ordine di anno

    def test_question_navigation_points_to_visible_answers(self):
        response = self._get("920")
        html = response.get_data(as_text=True)
        for intent in ("definizione", "dato", "classifica", "confronto", "andamento", "metodologia", "download"):
            self.assertIn(f'data-query-intent="{intent}"', html)
        for target in ("esplora", "classifica-dati", "serie-storica", "fonti-verifica", "download-dati"):
            self.assertIn(f'id="{target}"', html)

    def test_the_sitemap_and_the_pages_agree_on_what_is_indexable(self):
        """A listed URL must not serve noindex, and vice versa.

        The families use genuinely different indexability rules (the atlas wants
        complete regional coverage, the quality-of-life ones 80% coverage in the
        latest year) and the sitemap branches on the family catalog's own flag.
        Unifying the page put 47 BES and Multiscopo pages out of step with the
        sitemap listing them, and rebuilding the canonical slug moved six more to
        a URL the sitemap does not contain at all. Neither was caught by anything.
        """
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("/indicatore/", sitemap)
        wrong = []
        for indicator_id in self.golden:
            family, raw_id = family_and_raw(indicator_id)
            view = build_indicator_view(family, raw_id)
            if view is None:
                continue
            path = view["meta"]["canonical_path"]
            response = self.client.get(path)
            if response.status_code != 200:
                wrong.append((indicator_id, path, f"status {response.status_code}"))
                continue
            listed = path in sitemap
            noindex = (response.headers.get("X-Robots-Tag") or "").startswith("noindex")
            if listed == noindex:
                wrong.append((
                    indicator_id, path,
                    "in sitemap ma noindex" if listed else "indicizzabile ma assente dalla sitemap",
                ))
        self.assertEqual(wrong, [], f"sitemap and pages disagree: {wrong[:10]}")

    def test_the_provincial_level_renders_and_stays_out_of_the_index(self):
        two_level = [
            indicator_id for indicator_id, entry in self.golden.items()
            if len(entry["levels"]) > 1
        ]
        self.assertGreater(len(two_level), 20)
        for indicator_id in two_level:
            with self.subTest(indicator=indicator_id):
                response = self._get(indicator_id, "?livello=provincia")
                self.assertEqual(response.status_code, 200)
                # A level is a state of the same page, never a second document.
                self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex, follow")


if __name__ == "__main__":
    unittest.main()
