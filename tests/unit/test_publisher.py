import unittest
from pathlib import Path

from app import publisher


class PublisherDatasetUpdatedTest(unittest.TestCase):
    def test_missing_state_file_yields_no_date_instead_of_raising(self):
        # The deployed image does not ship data/, so source_state.json is absent.
        # dataset_updated must degrade to None, never raise (which would 500 the
        # otherwise healthy indicator page).
        original = publisher._SOURCE_STATE
        try:
            publisher._SOURCE_STATE = Path("/nonexistent/source_state.json")
            self.assertIsNone(publisher.dataset_updated("territorial"))
            self.assertIsNone(publisher.dataset_updated("bes"))
        finally:
            publisher._SOURCE_STATE = original

    def test_unknown_family_yields_no_date(self):
        self.assertIsNone(publisher.dataset_updated("eurostat"))
        self.assertIsNone(publisher.dataset_updated(None))


if __name__ == "__main__":
    unittest.main()
