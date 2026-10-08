import unittest

from app import nav, page_types


class CorrectionsNavigation(unittest.TestCase):
    def test_footer_has_unique_corrections_destination(self):
        entries = [item for item in nav.FOOTER if item["path"] == "/correzioni"]
        self.assertEqual(entries, [{"label": "Errori e correzioni", "path": "/correzioni"}])

    def test_page_type_is_info(self):
        self.assertEqual(page_types.page_type("/correzioni"), "info")
