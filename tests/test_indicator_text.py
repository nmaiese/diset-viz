"""Generated indicator text: article safety, sources rendering, FAQ schema.

Covers the three lower-priority findings from the indicator-text evaluation:
- generated "Misura ..." sentences never come out article-less;
- analyst sources (fonti) are actually rendered on the page;
- the FAQ is data-derived, visible, and its FAQPage JSON-LD matches the visible
  content (per AGENTS.md, no schema-only rich results).
"""

import json
import re
import unittest

from app import app, indicator_notes
from app.atlas_catalog import get_atlas_catalog, get_atlas_indicator

_ARTICLES = {"il", "lo", "la", "l'", "i", "gli", "le", "un", "una", "uno", "un'"}
# Legitimate non-article openers after "Misura" (quantifier clauses).
_QUANTIFIERS = {"quanto", "quanta", "quanti", "quante"}


class GeneratedArticleSafety(unittest.TestCase):
    def test_with_article_never_returns_bare_term(self):
        for term in ("popolazione", "frobnicazione", "xyzabc", "associazione", "reddito", "imprese"):
            out = indicator_notes._with_article(term)
            first = out.split()[0].lower()
            token = "l'" if first.startswith("l'") else first
            self.assertIn(token, _ARTICLES, f"{term!r} -> {out!r}")

    def test_catalog_plain_text_is_articulated(self):
        offenders = []
        for item in get_atlas_catalog()["indicators"]:
            plain = (item.get("explain") or {}).get("plain", "")
            match = re.match(r"^Misura\s+(\S+)", plain)
            if not match:
                continue
            word = match.group(1).lower()
            token = "l'" if word.startswith("l'") else word
            if token not in _ARTICLES and word not in _QUANTIFIERS:
                offenders.append((item["id"], plain[:60]))
        self.assertEqual(offenders, [], f"article-less generated text: {offenders[:10]}")


class AnnualChangeFramingAgreement(unittest.TestCase):
    """A1: the movement noun ('aumento' masculine, 'diminuzione' feminine) must keep
    its article in agreement, in every branch of annual_change_framing."""

    def test_zero_delta_reads_invariata(self):
        self.assertEqual(
            indicator_notes.annual_change_framing("Indicatore X", "contextual", 0.0),
            "La media è rimasta invariata.",
        )

    def test_contextual_uses_indefinite_article_in_agreement(self):
        up = indicator_notes.annual_change_framing("Indicatore X", "contextual", 2.0)
        down = indicator_notes.annual_change_framing("Indicatore X", "contextual", -2.0)
        self.assertIn("un aumento", up)
        self.assertNotIn("un diminuzione", down)
        self.assertIn("una diminuzione", down)

    def test_difference_indicator_uses_definite_article_in_agreement(self):
        up = indicator_notes.annual_change_framing(
            "Differenza tra tasso maschile e femminile", "contextual", 1.5
        )
        down = indicator_notes.annual_change_framing(
            "Differenza tra tasso maschile e femminile", "contextual", -1.5
        )
        self.assertTrue(up.startswith("L'aumento indica"), up)
        self.assertTrue(down.startswith("La diminuzione indica"), down)
        self.assertNotIn("La aumento", up)


class ItPluralAgreement(unittest.TestCase):
    """A2: singular/plural agreement so a count of 1 never reads as '1 regioni'."""

    def test_singular_and_plural_forms(self):
        self.assertEqual(indicator_notes.it_plural(1, "regione", "regioni"), "regione")
        self.assertEqual(indicator_notes.it_plural(2, "regione", "regioni"), "regioni")
        self.assertEqual(indicator_notes.it_plural(0, "regione", "regioni"), "regioni")
        # Verbs agree too.
        self.assertEqual(indicator_notes.it_plural(1, "supera", "superano"), "supera")
        self.assertEqual(indicator_notes.it_plural(3, "supera", "superano"), "superano")

    def test_non_integer_count_falls_back_to_plural(self):
        self.assertEqual(indicator_notes.it_plural(None, "regione", "regioni"), "regioni")
        self.assertEqual(indicator_notes.it_plural("x", "regione", "regioni"), "regioni")

    def test_intro_helper_never_says_one_regioni(self):
        one = indicator_notes.indicator_page_intro("Misura qualcosa.", 2024, 2024, 1)
        self.assertIn("1 regione ", one)
        self.assertNotIn("1 regioni", one)


class AnalystSourcesRendered(unittest.TestCase):
    def test_fonti_are_shown_on_the_page(self):
        # id 178 (tasso di occupazione femminile) carries a note with a source.
        meta = get_atlas_indicator("178")["metadata"]
        html = app.test_client().get(meta["path"]).data.decode("utf-8")
        self.assertIn("Fonti dell", html)  # "Fonti dell'analisi" (apostrophe escaped)
        self.assertIn("ec.europa.eu/eurostat", html)


class IndicatorFaq(unittest.TestCase):
    def test_faq_helper_is_factual_or_empty(self):
        rows = [
            {"region": "Alpha", "value": 10.0},
            {"region": "Beta", "value": 5.0},
            {"region": "Gamma", "value": 1.0},
        ]
        faq = indicator_notes.build_indicator_faq("Indicatore X", "%", 2025, rows, 5.3)
        self.assertEqual(len(faq), 3)
        self.assertIn("Alpha", faq[0]["a"])   # highest
        self.assertIn("Gamma", faq[1]["a"])   # lowest
        self.assertEqual(indicator_notes.build_indicator_faq("X", "%", 2025, rows[:2], None), [])

    def test_faq_number_format_preserves_decimals(self):
        # A value above 100 must keep its decimals (it_num-consistent), not round
        # to a whole number that would disagree with the ranking/table.
        self.assertEqual(indicator_notes._it_number(116.407), "116,41")
        self.assertEqual(indicator_notes._it_number(68.9), "68,9")
        self.assertEqual(indicator_notes._it_number(34500), "34.500")
        self.assertEqual(indicator_notes._it_number(5.0), "5")

    def test_page_faq_jsonld_matches_visible_content(self):
        meta = get_atlas_indicator("178")["metadata"]
        html = app.test_client().get(meta["path"]).data.decode("utf-8")
        self.assertIn("Domande frequenti", html)
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        faq_blocks = [json.loads(b) for b in blocks if '"FAQPage"' in b]
        self.assertEqual(len(faq_blocks), 1)
        for entry in faq_blocks[0]["mainEntity"]:
            question = entry["name"]
            answer = entry["acceptedAnswer"]["text"]
            # Both question and answer must be visible on the page (HTML-escaped).
            self.assertIn(question.replace("'", "&#39;"), html)
            self.assertIn(answer.replace("'", "&#39;"), html)


if __name__ == "__main__":
    unittest.main()
