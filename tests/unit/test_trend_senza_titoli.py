"""Test che i titoli delle notizie non vengano salvati (privacy)."""

import json
import unittest
from pathlib import Path

from scripts.trend_articles.collect import senza_titoli_di_cronaca
from scripts.trend_articles.rank import interest_score


class TestSenzaTitoliDiCronaca(unittest.TestCase):
    def test_toglie_title_da_news_principali(self):
        signals = [{
            "type": "google_news_principali",
            "title": "Titolo privato",
            "url": "http://example.com",
            "published": "2026-09-23",
        }]
        out = senza_titoli_di_cronaca(signals)
        self.assertNotIn("title", out[0])
        self.assertEqual(out[0]["url"], "http://example.com")

    def test_toglie_title_da_news_tema(self):
        signals = [{
            "type": "google_news_tema",
            "title": "Titolo privato",
            "topic": "sanita",
            "url": "http://example.com",
            "published": "2026-09-23",
        }]
        out = senza_titoli_di_cronaca(signals)
        self.assertNotIn("title", out[0])

    def test_toglie_title_dagli_elementi_news_dei_trend(self):
        signals = [{
            "type": "google_trends_tendenza",
            "term": "ricerca",
            "news": [
                {"title": "Titolo privato", "url": "http://example.com", "source": "Test"},
            ],
        }]
        out = senza_titoli_di_cronaca(signals)
        self.assertNotIn("title", out[0]["news"][0])
        self.assertEqual(out[0]["news"][0]["url"], "http://example.com")

    def test_lascia_title_a_istat_comunicato(self):
        signals = [{
            "type": "istat_comunicato",
            "title": "Comunicato Istat pubblico",
            "url": "http://istat.it",
            "published": "2026-09-23",
        }]
        out = senza_titoli_di_cronaca(signals)
        self.assertIn("title", out[0])
        self.assertEqual(out[0]["title"], "Comunicato Istat pubblico")

    def test_non_muta_input(self):
        signals = [{
            "type": "google_news_principali",
            "title": "Titolo privato",
            "url": "http://example.com",
        }]
        original = json.dumps(signals)
        senza_titoli_di_cronaca(signals)
        self.assertEqual(json.dumps(signals), original)


class TestRankSenzaTitoli(unittest.TestCase):
    def setUp(self):
        self.topic = {
            "id": "sanita",
            "name": "Sanita",
            "indicators": ["bes:TEST001"],
        }
        self.signals = [
            {
                "type": "google_news_tema",
                "topic": "sanita",
                "topics": ["sanita"],
                "url": "http://example.com/1",
                "published": "2026-09-23",
            },
            {
                "type": "google_news_principali",
                "topics": ["sanita"],
                "url": "http://example.com/2",
                "published": "2026-09-23",
            },
            {
                "type": "istat_comunicato",
                "topics": ["sanita"],
                "title": "Comunicato Istat",
                "url": "http://istat.it",
                "published": "2026-09-23",
            },
            {
                "type": "google_trends_tendenza",
                "term": "sanita",
                "topics": ["sanita"],
                "news": [
                    {"url": "http://example.com/3", "source": "Test", "published": "2026-09-23"},
                ],
            },
        ]
        self.interest = {}
        self.most_news = 1

    def test_interest_score_senza_keyerror(self):
        result = interest_score(self.topic, self.signals, self.interest, self.most_news)
        self.assertIn("score", result)

    def test_output_non_contiene_top_news(self):
        result = interest_score(self.topic, self.signals, self.interest, self.most_news)
        self.assertNotIn("top_news", result)

    def test_news_examples_senza_title(self):
        result = interest_score(self.topic, self.signals, self.interest, self.most_news)
        for ex in result.get("news_examples", []):
            self.assertNotIn("title", ex)
            self.assertIn("url", ex)
            self.assertIn("published", ex)

    def test_istat_usa_get(self):
        result = interest_score(self.topic, self.signals, self.interest, self.most_news)
        self.assertIn("istat", result)
        self.assertEqual(result["istat"], ["Comunicato Istat"])


class TestCancelloDati(unittest.TestCase):
    def test_signals_json_senza_title_eccetto_istat(self):
        root = Path("data/trend")
        if not root.exists():
            self.skipTest("data/trend non esiste")
        for signals_file in root.glob("*/signals.json"):
            with signals_file.open() as f:
                data = json.load(f)
            for s in data.get("signals", []):
                if s.get("type") == "istat_comunicato":
                    continue
                self.assertNotIn("title", s, f"{signals_file}: segnale {s.get('type')} ha title")
                for n in s.get("news", []):
                    self.assertNotIn("title", n, f"{signals_file}: news in {s.get('type')} ha title")

    def test_ranking_json_senza_top_news_e_title(self):
        root = Path("data/trend")
        if not root.exists():
            self.skipTest("data/trend non esiste")
        for ranking_file in root.glob("*/ranking.json"):
            with ranking_file.open() as f:
                data = json.load(f)
            for pair in data.get("pairs", []):
                inter = pair.get("interest", {})
                self.assertNotIn("top_news", inter, f"{ranking_file}: interest ha top_news")
                for ex in inter.get("news_examples", []):
                    self.assertNotIn("title", ex, f"{ranking_file}: news_examples ha title")
                istat_list = inter.get("istat", [])
                for item in istat_list:
                    self.assertIsInstance(item, str, f"{ranking_file}: istat deve essere lista di stringhe")


if __name__ == "__main__":
    unittest.main()