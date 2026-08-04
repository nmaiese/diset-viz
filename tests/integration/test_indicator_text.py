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

from app import app, indicator_notes, indicator_texts
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

    def test_composed_lead_never_says_one_regioni(self):
        meta = {"explain": {"plain": "Misura qualcosa."}, "institution": "Istat"}
        level = {
            "observations": [{"key": "a", "name": "A", "value": 1.0}],
            "singular": "regione", "plural": "regioni",
            "year_min": 2024, "year_max": 2024, "has_map": True,
        }
        one = indicator_texts.composed_lead(meta, level)
        self.assertIn("1 regione", one)
        self.assertNotIn("1 regioni", one)

    def test_composed_lead_does_not_repeat_the_cockpit_figures(self):
        """The lead used to open with best, worst and the mean, which the KPI row
        prints right below it. That duplication is the whole reason this text was
        rewritten, so it must not creep back."""
        meta = {"explain": {"plain": "Misura qualcosa."}, "institution": "Istat"}
        level = {
            "observations": [
                {"key": "a", "name": "Alpha", "value": 91.5},
                {"key": "b", "name": "Beta", "value": 12.25},
            ],
            "singular": "regione", "plural": "regioni",
            "year_min": 2019, "year_max": 2024, "has_map": True,
        }
        lead = indicator_texts.composed_lead(meta, level)
        for forbidden in ("Alpha", "Beta", "91,5", "12,25", "51,8"):
            self.assertNotIn(forbidden, lead)
        self.assertIn("2 regioni", lead)
        self.assertIn("dal 2019 al 2024", lead)


class AnalystSourcesRendered(unittest.TestCase):
    def test_fonti_are_shown_on_the_page(self):
        # id 178 (tasso di occupazione femminile) carries a note with a source.
        meta = get_atlas_indicator("178")["metadata"]
        html = app.test_client().get(meta["path"]).data.decode("utf-8")
        self.assertIn("Fonti dell", html)  # "Fonti dell'analisi" (apostrophe escaped)
        self.assertIn("ec.europa.eu/eurostat", html)


class NoGeneratedFaq(unittest.TestCase):
    """The auto-generated FAQ is gone, and must not come back.

    It restated the highest region, the lowest region and the mean, which the
    cockpit already shows above it, and emitted FAQPage structured data for
    those same three facts. INDICATOR_PAGES.md forbids generic FAQ filler and
    CLAUDE.md allows JSON-LD only where the visible page supports it, so the
    block and its schema were removed together rather than one without the other.
    """

    def test_page_has_no_faq_block_and_no_faqpage_schema(self):
        meta = get_atlas_indicator("178")["metadata"]
        html = app.test_client().get(meta["path"]).data.decode("utf-8")
        self.assertNotIn("Domande frequenti", html)
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        self.assertEqual([b for b in blocks if '"FAQPage"' in b], [])
        # The two schemas the visible page does support stay.
        self.assertTrue(any('"Dataset"' in b for b in blocks))
        self.assertTrue(any('"BreadcrumbList"' in b for b in blocks))

if __name__ == "__main__":
    unittest.main()
