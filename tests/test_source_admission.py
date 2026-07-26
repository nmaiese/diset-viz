"""Ammettere una fonte senza un umano che guardi il diff.

Lo scout fondeva a mano fino a oggi, e il motivo era buono: una fonte decide
quale istituzione e quale licenza compaiono su una pagina pubblica. Adesso fonde
da solo, quindi quel controllo deve esistere da qualche altra parte, ed e' qui.
La CI e' l'unica cosa fra il giudizio dello scout e il sito.

Che cosa puo' andare storto davvero, in ordine di quanto e' silenzioso:

1. **Un tema che nessuno ha mappato.** L'indicatore resta in catalogo e sparisce
   da ogni totale per macro-area. Nessun errore, nessuna pagina rotta, solo un
   buco nei conti che nessuno nota.
2. **Un campo mancante.** `load_series` ha dei default, quindi una riga senza
   `dataflow` non esplode: eredita il dataflow di un'altra serie e pubblica i
   numeri sbagliati sotto il nome giusto.
3. **Una riga che non si scarica.** Prima uccideva l'intera scansione del
   cacciatore, per sempre, con un traceback che nessuno leggeva.

Il primo e il secondo si vedono senza rete e stanno qui. Il terzo e' un problema
di robustezza e sta nella classe in fondo.
"""

import unittest

from app import taxonomy
from scripts import curate, discover_candidates, external_sources, istat_regional_source

REQUIRED = ("id", "dataflow", "dsd_label", "name", "theme", "quality_life_category", "direction")
KNOWN_DIRECTIONS = curate.SCOREABLE_DIRECTIONS | {"contextual"}


def config_rows():
    return external_sources.load_flat_list(istat_regional_source.SERIES_CONFIG, "series")


class EveryAdmittedSeriesIsUsable(unittest.TestCase):
    """Gira su `config/istat_series.yaml` committato, cioe' su quello che lo
    scout ha scritto davvero."""

    def setUp(self):
        self.rows = config_rows()

    def test_there_is_something_to_check(self):
        self.assertTrue(self.rows, "config/istat_series.yaml e' vuoto")

    def test_no_required_field_is_missing(self):
        for row in self.rows:
            for field in REQUIRED:
                value = str(row.get(field, "")).strip()
                self.assertTrue(
                    value,
                    f"la serie {row.get('id', '?')} non dichiara '{field}'. "
                    "load_series ha un default per quasi tutto, quindi una riga "
                    "incompleta non fallisce: pubblica il valore di un'altra serie.",
                )

    def test_no_two_series_share_an_id(self):
        ids = [str(row.get("id", "")).strip() for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)), f"id duplicati in {ids}")

    def test_ids_are_sdmx_codes_not_prose(self):
        for row in self.rows:
            for field in ("id", "dataflow"):
                value = str(row.get(field, ""))
                self.assertNotIn(" ", value, f"{field} '{value}' contiene uno spazio")

    def test_the_direction_is_one_the_curator_can_act_on(self):
        for row in self.rows:
            direction = str(row.get("direction", "")).strip()
            self.assertIn(
                direction, KNOWN_DIRECTIONS,
                f"la serie {row.get('id')} propone un verso sconosciuto '{direction}'",
            )

    def test_the_category_exists(self):
        for row in self.rows:
            slug = str(row.get("quality_life_category", "")).strip()
            self.assertIn(
                slug, taxonomy.CANONICAL_CATEGORIES,
                f"la serie {row.get('id')} propone una categoria che non esiste: '{slug}'. "
                "Inventare una categoria non e' una riga di CSV, e' una sezione del sito.",
            )

    def test_the_theme_resolves_to_a_category(self):
        """Il fallimento piu' silenzioso di tutti: un tema non mappato non rompe
        niente, toglie solo l'indicatore da ogni totale per macro-area."""
        for row in self.rows:
            theme = str(row.get("theme", "")).strip()
            self.assertIn(
                theme, taxonomy.SOURCE_THEME_TO_CATEGORY,
                f"il tema '{theme}' della serie {row.get('id')} non e' mappato. "
                "Si aggiunge una riga a config/theme_categories.csv, non si tocca il codice.",
            )

    def test_the_decimals_are_a_number(self):
        for row in self.rows:
            decimals = row.get("decimals", 1)
            self.assertIsInstance(
                decimals, int,
                f"la serie {row.get('id')} dichiara decimals={decimals!r}, che non e' un intero",
            )


class ABrokenRowCostsOnlyItself(unittest.TestCase):
    """Il difetto trovato provando la catena: una riga sbagliata faceva morire
    tutta la scansione, non solo la sua serie."""

    def setUp(self):
        discover_candidates.FAILURES.clear()

    def tearDown(self):
        discover_candidates.FAILURES.clear()

    def test_one_failure_does_not_lose_the_others(self):
        def fetch(series_id):
            if series_id == "ROTTA":
                raise RuntimeError("HTTP Error 404: Not Found")
            return {"source_indicator_id": series_id}

        rows = discover_candidates._survey(["BUONA", "ROTTA", "ALTRA"], fetch)
        self.assertEqual([r["source_indicator_id"] for r in rows], ["BUONA", "ALTRA"])

    def test_the_failure_is_reported_not_swallowed(self):
        def fetch(series_id):
            raise RuntimeError("HTTP Error 404: Not Found")

        discover_candidates._survey(["ROTTA"], fetch)
        self.assertEqual(len(discover_candidates.FAILURES), 1)
        series_id, message = discover_candidates.FAILURES[0]
        self.assertEqual(series_id, "ROTTA")
        self.assertIn("404", message)

    def test_a_scan_that_reads_nothing_is_not_a_scan_that_found_nothing(self):
        """Le due cose sembrano identiche da fuori e vogliono reazioni opposte."""
        def fetch(series_id):
            raise RuntimeError("boom")

        rows = discover_candidates._survey(["A", "B"], fetch)
        self.assertEqual(rows, [])
        self.assertEqual(len(discover_candidates.FAILURES), 2)


if __name__ == "__main__":
    unittest.main()
