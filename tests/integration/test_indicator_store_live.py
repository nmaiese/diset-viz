"""Lo store degli articoli letto **committato**, cioe' tutto intero.

Sta in `integration/` e non accanto ai suoi fratelli in `tests/unit/` per la
regola di `CLAUDE.md`: un test che legge tutti gli articoli committati ha bisogno
di un giro reale, e la suite veloce deve restare la suite della logica. Finche'
questi due metodi stavano in `tests/unit/test_indicator_store.py`, chi lanciava
`discover -s tests/unit` credeva di aver girato solo logica e aveva girato il
catalogo: un test che non fallisce mai per la ragione che dichiara e' comunque
un test che misura un'altra cosa.

Il resto dello store (codifica delle chiavi, scrittura e rilettura, forma URL)
non tocca il disco vero e resta in `tests/unit/test_indicator_store.py`.
"""

import unittest

from scripts import indicator_store


class TheCommittedStore(unittest.TestCase):
    def test_no_key_in_the_catalogue_breaks_the_assumption(self):
        """La codifica delle chiavi regge perche' nessuna chiave vera contiene
        gia' il separatore. La garanzia sta nel catalogo, non nella funzione:
        e' l'unico dei due test che puo' scoprire una chiave nuova che arriva."""
        for key in indicator_store.load_all():
            self.assertNotIn(indicator_store.FILENAME_SEP, key, key)
            self.assertLessEqual(key.count(":"), 1, key)

    def test_the_committed_store_is_readable_and_not_empty(self):
        entries = indicator_store.load_all()
        self.assertGreater(len(entries), 300)
        for key, entry in entries.items():
            self.assertIsInstance(entry, dict, key)


if __name__ == "__main__":
    unittest.main()
