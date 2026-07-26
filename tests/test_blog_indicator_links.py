"""The two halves of the site have to point at each other.

A post has always declared its indicator in the frontmatter, and /blog/<slug>
has always rendered the link forward. Nothing rendered it back: an indicator
page was a dead end for a reader who wanted the story behind the number, and a
mistyped id in the frontmatter broke the one existing direction in silence.

These tests pin both directions and the guard that keeps the mapping honest.
"""

import unittest

from markupsafe import escape

from app import app, sources
from app.atlas_catalog import get_atlas_indicator
from app.blog import POSTS_PER_INDICATOR, get_posts, posts_for_indicator


def _linked_posts():
    return [post for post in get_posts() if post["indicator"]]


def _unwritten_indicator():
    """A catalog entry no article points at, for the negative cases."""
    from app.atlas_catalog import get_atlas_catalog

    declared = {post["indicator"] for post in _linked_posts()}
    return next(
        entry for entry in get_atlas_catalog()["indicators"]
        if str(entry["id"]) not in declared
    )


class FrontmatterIndicatorTest(unittest.TestCase):
    """Every article is anchored to a real indicator."""

    def test_every_post_declares_an_indicator(self):
        orphans = [post["slug"] for post in get_posts() if not post["indicator"]]
        self.assertEqual(orphans, [], "articoli senza campo indicator nel frontmatter")

    def test_every_declared_indicator_exists_in_the_catalog(self):
        """A typo here used to fail open: the post rendered without its link
        block and nobody noticed."""
        broken = [
            (post["slug"], post["indicator"])
            for post in _linked_posts()
            if get_atlas_indicator(post["indicator"]) is None
        ]
        self.assertEqual(broken, [], "id indicatore non risolvibili nel catalogo")

    def test_the_unified_url_code_is_accepted_as_well_as_the_bare_id(self):
        """An author can paste the code out of the address bar. Both spellings
        have to land on the same catalog id, otherwise the same indicator would
        collect articles under two keys."""
        from app.blog import _normalize_indicator

        self.assertEqual(_normalize_indicator(408), "408")
        self.assertEqual(_normalize_indicator("ter-408"), "408")
        self.assertEqual(_normalize_indicator("bes-01SAL001"), "bes:01SAL001")
        self.assertEqual(_normalize_indicator("eur-rd_e_gerdreg"), "eur:rd_e_gerdreg")
        self.assertIsNone(_normalize_indicator(None))
        self.assertIsNone(_normalize_indicator("  "))


class PostsForIndicatorTest(unittest.TestCase):
    def test_a_post_is_found_from_the_indicator_it_declares(self):
        for post in _linked_posts():
            matched = posts_for_indicator(post["indicator"], limit=None)
            self.assertIn(
                post["slug"],
                [item["slug"] for item in matched],
                f"{post['slug']} non risulta collegato a {post['indicator']}",
            )

    def test_an_indicator_nobody_wrote_about_has_no_posts(self):
        self.assertEqual(posts_for_indicator(_unwritten_indicator()["id"]), [])

    def test_no_indicator_means_no_posts(self):
        self.assertEqual(posts_for_indicator(None), [])
        self.assertEqual(posts_for_indicator(""), [])

    def test_the_widget_never_grows_past_its_limit(self):
        for post in _linked_posts():
            self.assertLessEqual(len(posts_for_indicator(post["indicator"])), POSTS_PER_INDICATOR)

    def test_posts_come_back_newest_first(self):
        """The list is a reading path: the most recent take goes on top."""
        for post in _linked_posts():
            dates = [item["date"] for item in posts_for_indicator(post["indicator"], limit=None)]
            self.assertEqual(dates, sorted(dates, reverse=True))


class IndicatorPageRendersItsArticlesTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_the_round_trip_closes_for_every_post(self):
        """Post -> indicator page -> back to the post, on the real HTML."""
        for post in _linked_posts():
            family, raw_id = sources.split_internal_id(post["indicator"])
            path = get_atlas_indicator(post["indicator"])["metadata"]["path"]
            with self.subTest(post=post["slug"]):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn(f'href="/blog/{post["slug"]}"', body)
                # Titles carry apostrophes ("L'Italia dei giovani"), so compare
                # against the escaped form the template actually emits.
                self.assertIn(str(escape(post["title"])), body)
                # The code the URL resolves through, so a family change here
                # would surface as a failing round trip rather than a dead link.
                self.assertIn(sources.indicator_code(family, raw_id), path)

    def test_an_indicator_without_articles_renders_no_widget(self):
        """An empty section with a heading would read as a broken promise."""
        payload = get_atlas_indicator(_unwritten_indicator()["id"])
        response = self.client.get(payload["metadata"]["path"])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("indicator-articles", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
