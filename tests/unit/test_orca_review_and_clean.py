"""Test unitari per scripts/orca_review.py e scripts/orca_clean.py."""
import unittest

from scripts import orca_clean, orca_review


class OrcaReviewAndCleanTest(unittest.TestCase):
    def test_review_dry_run_executes(self):
        res = orca_review.run_review(slug="105-test-slug", issue_id=105, dry_run=True)
        self.assertEqual(res, 0)

    def test_clean_dry_run_executes(self):
        res = orca_clean.run_clean(slug="105-test-slug", dry_run=True)
        self.assertEqual(res, 0)


if __name__ == "__main__":
    unittest.main()
