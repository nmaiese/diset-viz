import hashlib
import unittest

from app import app, cache
from app import agent_discovery
from app.blog import get_posts


class AgentDiscoveryTest(unittest.TestCase):
    def setUp(self):
        cache.cache.clear()
        self.client = app.test_client()

    def test_home_advertises_real_machine_resources(self):
        response = self.client.get("/")
        links = response.headers.getlist("Link")
        self.assertTrue(any('rel="api-catalog"' in value for value in links))
        self.assertTrue(any("/.well-known/api-catalog" in value for value in links))
        self.assertTrue(any('rel="service-doc"' in value and "/llms.txt" in value for value in links))
        self.assertTrue(any('rel="service-desc"' in value and "/agent-skills/" in value for value in links))

        for path in (
            "/.well-known/api-catalog",
            "/openapi.json",
            "/.well-known/agent-skills/index.json",
        ):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_api_catalog_is_an_rfc_9727_linkset(self):
        response = self.client.get("/.well-known/api-catalog")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/linkset+json")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")

        linkset = response.get_json()["linkset"]
        self.assertEqual(len(linkset), 1)
        self.assertEqual(linkset[0]["anchor"], "https://divarioitalia.it/api/catalog")
        self.assertEqual(linkset[0]["service-desc"][0]["href"], "https://divarioitalia.it/openapi.json")
        self.assertEqual(linkset[0]["service-doc"][0]["href"], "https://divarioitalia.it/catalogo-dati")

        head = self.client.head("/.well-known/api-catalog")
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.data, b"")
        self.assertTrue(any('rel="service-desc"' in value for value in head.headers.getlist("Link")))

    def test_openapi_exposes_only_the_read_only_data_contract(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")
        document = response.get_json()
        self.assertEqual(document["openapi"], "3.1.0")
        self.assertEqual(document["servers"], [{"url": "https://divarioitalia.it"}])
        self.assertEqual(
            set(document["paths"]),
            {
                "/api/catalog",
                "/api/search",
                "/api/indicator/{indicator_id}",
                "/api/indicator/{indicator_id}/year/{year}",
                "/download/indicator/{indicator_id}.json",
                "/download/indicator/{indicator_id}.csv",
            },
        )
        for operations in document["paths"].values():
            self.assertEqual(set(operations), {"get"})
        serialized = response.get_data(as_text=True)
        for forbidden in ("leaderboard", "/api/game/", "/api/events", "_pipeline"):
            self.assertNotIn(forbidden, serialized)

    def test_canonical_pages_negotiate_markdown_without_poisoning_html_cache(self):
        post_path = f"/blog/{get_posts()[0]['slug']}"
        paths = (
            "/",
            "/atlante",
            "/catalogo-dati",
            "/blog",
            post_path,
            "/metodologia",
            "/indicatore/tasso-di-turisticita/ter-105",
            "/regione/lombardia",
            "/tema/lavoro-e-conciliazione",
        )
        for path in paths:
            with self.subTest(path=path):
                markdown = self.client.get(path, headers={"Accept": "text/markdown"})
                self.assertEqual(markdown.status_code, 200)
                self.assertTrue(markdown.content_type.startswith("text/markdown"))
                self.assertIn("Accept", markdown.headers.get("Vary", ""))
                self.assertTrue(markdown.headers.get("Content-Location", "").startswith("https://divarioitalia.it/"))
                self.assertTrue(markdown.get_data(as_text=True).startswith("# "))
                self.assertNotIn("<!doctype html>", markdown.get_data(as_text=True).lower())

                html = self.client.get(path)
                self.assertTrue(html.content_type.startswith("text/html"))
                self.assertIn("Accept", html.headers.get("Vary", ""))

        wildcard = self.client.get("/", headers={"Accept": "*/*"})
        disabled = self.client.get("/", headers={"Accept": "text/markdown;q=0"})
        self.assertTrue(wildcard.content_type.startswith("text/html"))
        self.assertTrue(disabled.content_type.startswith("text/html"))

    def test_indicator_markdown_preserves_provenance_and_index_policy(self):
        path = "/indicatore/tasso-di-turisticita/ter-105"
        response = self.client.get(path, headers={"Accept": "text/markdown"})
        text = response.get_data(as_text=True)
        for marker in (
            "# Tasso di turisticità",
            "## Che cosa misura",
            "## Ultimo cambiamento disponibile",
            "## Valori per regioni, 2024",
            "Istat",
            "Scarica CSV",
            "Scarica JSON",
        ):
            self.assertIn(marker, text)

        explored = self.client.get(
            path + "?livello=regione", headers={"Accept": "text/markdown"}
        )
        self.assertEqual(explored.headers["X-Robots-Tag"], "noindex, follow")
        self.assertEqual(explored.headers["Content-Location"], "https://divarioitalia.it" + path)

    def test_indicator_markdown_composes_missing_article_sections(self):
        path = "/indicatore/aree-terrestri-protette/ter-264"
        text = self.client.get(path, headers={"Accept": "text/markdown"}).get_data(as_text=True)

        self.assertIn("## Come è cambiato nel tempo", text)
        self.assertIn("la media semplice dei valori regionali è passata", text)

    def test_indicator_markdown_uses_the_selected_levels_explanation(self):
        path = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia"
        response = self.client.get(path, headers={"Accept": "text/markdown"})
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Il confronto tra province", text)
        self.assertNotIn("Il confronto tra regioni", text)

    def test_agent_skill_index_digest_and_artifact_match(self):
        index = self.client.get("/.well-known/agent-skills/index.json")
        self.assertEqual(index.status_code, 200)
        self.assertEqual(index.headers["X-Robots-Tag"], "noindex, nofollow, noarchive")
        document = index.get_json()
        self.assertEqual(document["$schema"], agent_discovery.AGENT_SKILL_SCHEMA)
        self.assertEqual(len(document["skills"]), 1)
        entry = document["skills"][0]
        self.assertEqual(entry["name"], "query-divario-italia")
        self.assertEqual(entry["type"], "skill-md")

        artifact_path = entry["url"].removeprefix("https://divarioitalia.it")
        artifact = self.client.get(artifact_path)
        self.assertEqual(artifact.status_code, 200)
        self.assertTrue(artifact.content_type.startswith("text/markdown"))
        self.assertEqual(
            entry["digest"],
            "sha256:" + hashlib.sha256(artifact.data).hexdigest(),
        )
        text = artifact.get_data(as_text=True)
        self.assertIn("name: query-divario-italia", text)
        self.assertIn("Non chiamare media italiana", text)
        self.assertIn("Non dedurre cause", text)
        self.assertNotIn(artifact_path, self.client.get("/sitemap.xml").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
