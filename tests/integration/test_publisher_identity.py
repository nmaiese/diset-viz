import json
import re
import unittest

from app import app, publisher


def jsonld(response):
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        response.get_data(as_text=True),
        re.S,
    )
    return [json.loads(block) for block in blocks]


class PublisherIdentityTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_about_page_is_visible_linked_and_listed(self):
        page = self.client.get("/chi-siamo")
        self.assertEqual(page.status_code, 200)
        text = page.get_data(as_text=True)
        for claim in ("Responsabilità editoriale", "Come verifichiamo", "Correzioni e contatto", "Come citare"):
            self.assertIn(claim, text)
        self.assertIn(publisher.CORRECTIONS_URL, text)
        self.assertIn('/chi-siamo', self.client.get('/').get_data(as_text=True))
        self.assertIn('<loc>https://divarioitalia.it/chi-siamo</loc>', self.client.get('/sitemap.xml').get_data(as_text=True))

    def test_one_reusable_organization_matches_visible_identity(self):
        about = jsonld(self.client.get("/chi-siamo"))[0]["@graph"]
        organization = next(node for node in about if node.get("@type") == "Organization")
        self.assertEqual(organization, publisher.ORGANIZATION)
        self.assertNotIn("sameAs", organization)
        self.assertIn(organization["name"], self.client.get("/chi-siamo").get_data(as_text=True))

        home_graph = jsonld(self.client.get("/"))[0]["@graph"]
        self.assertEqual(home_graph[1], organization)
        self.assertEqual(home_graph[0]["publisher"]["@id"], organization["@id"])

    def test_article_and_dataset_dates_and_corrections_match_visible_copy(self):
        article = self.client.get("/blog").get_data(as_text=True)
        match = re.search(r'href="/blog/([^"?]+)"', article)
        self.assertIsNotNone(match)
        response = self.client.get(f"/blog/{match.group(1)}")
        document = next(item for item in jsonld(response) if item.get("@type") == "Article")
        visible = response.get_data(as_text=True)
        self.assertIn(document["dateModified"].split("-")[0], visible)
        self.assertEqual(document["publisher"], publisher.ORGANIZATION)
        self.assertIn(publisher.CORRECTIONS_URL, visible)

        from app.data import get_catalog
        from app.profiles import indicator_path
        sample = get_catalog()["indicators"][0]
        response = self.client.get(indicator_path(sample["id"], sample["name"]))
        dataset = next(item for item in jsonld(response) if item.get("@type") == "Dataset")
        visible = response.get_data(as_text=True)
        self.assertIn(dataset["dateModified"], visible)
        self.assertEqual(dataset["publisher"], publisher.ORGANIZATION)
        self.assertIn(publisher.CORRECTIONS_URL, visible)


if __name__ == "__main__":
    unittest.main()
