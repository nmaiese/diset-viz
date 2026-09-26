"""The 107 province pages: description, headings and captions from the shared
template, checked across every province rather than on one sample.

At the 26 September 2026 audit, 4 province pages had one impression each.
Milano and Roma are indexed, so the problem is not indexing. The pages
never said "provincia" or "dati" to someone searching "dati provincia di
Lecce", even though they carry the actual values of every BES indicator.
The Molise caption also read "con le altre 1 province".
"""

import html as html_lib
import re
import unittest

from app import app, province_profile


class TestProvinceSeo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.pages = {key: client.get(f"/provincia/{key}").get_data(as_text=True)
                     for key in province_profile.chiavi()}

    def test_there_are_107_and_they_answer(self):
        self.assertEqual(len(self.pages), 107)
        for key, page in self.pages.items():
            self.assertIn('data-v1="provincia"', page, key)

    def test_the_description_names_the_province_and_stays_within_160(self):
        descriptions = []
        for key, page in self.pages.items():
            with self.subTest(provincia=key):
                profile = province_profile.profilo(key)
                description = html_lib.unescape(re.search(r'name="description" content="(.*?)"', page).group(1))
                descriptions.append(description)
                self.assertLessEqual(len(description), 160)
                kind = "città metropolitana" if profile.get("metro_city") else "provincia"
                self.assertTrue(description.startswith(f"Qualità della vita e dati della {kind} "), description)
                self.assertIn(f"{profile['rank']}ª su {profile['total']} province", description)
        # The pages differ from one another in more than the numbers.
        without_numbers = {re.sub(r"\d+(?:,\d+)?", "#", d) for d in descriptions}
        self.assertGreater(len(without_numbers), 100)

    def test_the_indicators_section_says_whose_data_it_is(self):
        for key, page in self.pages.items():
            with self.subTest(provincia=key):
                h2 = html_lib.unescape(re.search(r'<h2 id="h-indicatori">(.*?)</h2>', page).group(1))
                self.assertRegex(h2, r"^I dati della (provincia|città metropolitana) ")

    def test_no_caption_says_altre_1_province(self):
        for key, page in self.pages.items():
            with self.subTest(provincia=key):
                self.assertNotIn("altre 1 province", page)

    def test_title_still_carries_name_and_position(self):
        for key, page in self.pages.items():
            with self.subTest(provincia=key):
                profile = province_profile.profilo(key)
                title = html_lib.unescape(re.search(r"<title>(.*?)</title>", page).group(1))
                self.assertTrue(title.startswith(f"{profile['name']}: {profile['rank']}ª su"), title)
                self.assertLessEqual(len(title), 60)


if __name__ == "__main__":
    unittest.main()
