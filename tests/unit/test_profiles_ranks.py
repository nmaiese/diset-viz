import unittest

from app import profiles


class RanksTieTest(unittest.TestCase):
    """Un valore uguale e' lo stesso piazzamento: nessun ordine alfabetico nascosto."""

    def test_higher_is_better_gives_ties_the_same_rank(self):
        ranks = profiles._ranks({"a": 10.0, "b": 9.0, "c": 9.0, "d": 7.0}, profiles.HIGHER_IS_BETTER)
        self.assertEqual(ranks, {"a": 1, "b": 2, "c": 2, "d": 4})

    def test_lower_is_better_gives_ties_the_same_rank(self):
        ranks = profiles._ranks({"a": 10.0, "b": 9.0, "c": 9.0, "d": 7.0}, "lower_better")
        self.assertEqual(ranks, {"d": 1, "b": 2, "c": 2, "a": 4})

    def test_no_ties_keeps_the_plain_order(self):
        ranks = profiles._ranks({"a": 3.0, "b": 2.0, "c": 1.0}, profiles.HIGHER_IS_BETTER)
        self.assertEqual(ranks, {"a": 1, "b": 2, "c": 3})


if __name__ == "__main__":
    unittest.main()
