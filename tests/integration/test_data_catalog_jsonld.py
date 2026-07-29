import json
import re
import unittest

from app import app
from app import profiles
from app.data import get_catalog


def jsonld_blocks(html):
    return [
        json.loads(block)
        for block in re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S
        )
    ]


class DataCatalogJsonLdTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_catalog_links_only_canonical_indexable_datasets(self):
        response = self.client.get("/catalogo-dati")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        catalog = next(block for block in jsonld_blocks(html) if block.get("@type") == "DataCatalog")
        self.assertEqual(catalog["url"], "https://divarioitalia.it/catalogo-dati")
        self.assertIn(catalog["description"], html)
        self.assertTrue(catalog["dataset"])
        for dataset in catalog["dataset"]:
            self.assertTrue(dataset["url"].startswith("https://divarioitalia.it/indicatore/"))
            path = dataset["url"].removeprefix("https://divarioitalia.it")
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, path)
            self.assertNotIn(b'<meta name="robots" content="noindex', page.data, path)
            self.assertIn(f'href="{path}"'.encode(), response.data, path)

    def test_dataset_downloads_exist_and_match_visible_provenance(self):
        sample = next(item for item in get_catalog()["indicators"] if profiles.is_search_indexable_indicator(item))
        response = self.client.get(profiles.indicator_path(sample["id"], sample["name"]))
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        dataset = next(block for block in jsonld_blocks(html) if block.get("@type") == "Dataset")

        self.assertEqual(dataset["url"], response.request.url.replace("http://localhost", "https://divarioitalia.it"))
        self.assertIn(dataset["creator"]["name"], html)
        self.assertIn(f'href="{dataset["creator"]["url"]}"', html)
        self.assertEqual(dataset["publisher"]["name"], "Divario Italia")
        self.assertNotEqual(dataset["publisher"]["name"], dataset["creator"]["name"])
        self.assertIn(dataset["measurementTechnique"].lower(), html.lower())

        self.assertEqual({item["encodingFormat"] for item in dataset["distribution"]}, {"text/csv", "application/json"})
        for distribution in dataset["distribution"]:
            path = distribution["contentUrl"].removeprefix("https://divarioitalia.it")
            download = self.client.get(path)
            self.assertEqual(download.status_code, 200, path)
            self.assertIn(distribution["description"], html)


if __name__ == "__main__":
    unittest.main()
