import unittest

from app import sources


class ExternalSourceRegistry(unittest.TestCase):
    EXPECTED = {
        "mef", "ispra", "mim", "salute", "aci", "unioncamere",
    }

    def test_required_external_families_have_distinct_public_identity(self):
        self.assertTrue(self.EXPECTED <= set(sources.SOURCES))
        acronyms = [sources.SOURCES[family]["acronym"] for family in sources.SOURCES]
        prefixes = [sources.SOURCES[family]["internal_prefix"] for family in sources.SOURCES]
        self.assertEqual(len(acronyms), len(set(acronyms)))
        self.assertEqual(len(prefixes), len(set(prefixes)))
        for family in self.EXPECTED:
            meta = sources.SOURCES[family]
            self.assertTrue(meta["internal_prefix"])
            self.assertTrue(meta["feeds"])
            self.assertTrue(meta["license"])
            self.assertTrue(meta["license_url"].startswith("https://"))
            self.assertEqual(sources.parse_indicator_code(f"{meta['acronym']}-reddito-irpef-medio"),
                             (family, "reddito-irpef-medio"))

    def test_mef_ispra_and_aci_keep_declared_non_istat_deeds(self):
        self.assertIn("3.0", sources.SOURCES["mef"]["license"])
        self.assertIn("4.0", sources.SOURCES["ispra"]["license"])
        self.assertIn("4.0", sources.SOURCES["aci"]["license"])
        self.assertNotEqual(sources.SOURCES["aci"]["license_url"], sources.LICENSE_URL)
        self.assertNotEqual(sources.SOURCES["mef"]["license_url"], sources.LICENSE_URL)


if __name__ == "__main__":
    unittest.main()
