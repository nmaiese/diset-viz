"""Le famiglie mappate in config/indicator_families.csv (docs/FAMIGLIE_INDICATORI.md,
passo a) devono comparire come navigazione fra dimensioni sulla pagina
indicatore, senza cambiare url: la famiglia collega pagine che esistono già,
non ne crea una nuova (Nello, 4/9: "non modifichiamo la struttura delle
pagine, url pubblicate").
"""

import unittest

from app.atlas_catalog import get_atlas_catalog
from app.indicator_view import build_indicator_view


class DimensionSiblingsTest(unittest.TestCase):
    """id 345/346/347: Tasso di occupazione 20-64 anni, totale/maschi/femmine
    (config/indicator_families.csv, family_key tasso_di_occupazione_20_64_anni),
    la stessa tripletta verificata in nmaiese/diset-viz#216."""

    @classmethod
    def setUpClass(cls):
        cls.totale = build_indicator_view("territorial", "345")
        cls.maschi = build_indicator_view("territorial", "346")
        cls.femmine = build_indicator_view("territorial", "347")

    def test_each_member_links_to_the_other_two_by_value(self):
        totale_values = {s["value"]: s["id"] for s in self.totale["dimension_siblings"]}
        self.assertEqual(totale_values, {"maschi": "346", "femmine": "347"})

        maschi_values = {s["value"]: s["id"] for s in self.maschi["dimension_siblings"]}
        self.assertEqual(maschi_values, {"totale": "345", "femmine": "347"})

        femmine_values = {s["value"]: s["id"] for s in self.femmine["dimension_siblings"]}
        self.assertEqual(femmine_values, {"totale": "345", "maschi": "346"})

    def test_no_member_links_itself(self):
        for view, own_id in ((self.totale, "345"), (self.maschi, "346"), (self.femmine, "347")):
            with self.subTest(id=own_id):
                self.assertNotIn(own_id, {s["id"] for s in view["dimension_siblings"]})

    def test_sibling_path_matches_the_atlas_catalogue_unchanged(self):
        """La navigazione linka la pagina già pubblicata di ciascun membro,
        non ne calcola una nuova: stesso `path` che il catalogo atlante
        già usa per quell'id, quindi nessun url nuovo o diverso."""
        path_by_id = {str(item["id"]): item["path"] for item in get_atlas_catalog()["indicators"]}
        for view in (self.totale, self.maschi, self.femmine):
            for sibling in view["dimension_siblings"]:
                with self.subTest(sibling=sibling["id"]):
                    self.assertEqual(sibling["path"], path_by_id[sibling["id"]])
            # La pagina stessa non ha cambiato canonical_path.
            self.assertEqual(view["meta"]["canonical_path"], path_by_id[view["meta"]["id"]])

    def test_values_are_ordered_totale_maschi_femmine(self):
        order = [s["value"] for s in self.maschi["dimension_siblings"]]
        self.assertEqual(order, sorted(order, key=lambda v: ("totale", "maschi", "femmine").index(v)))

    def test_an_indicator_outside_any_family_has_no_dimension_siblings(self):
        # id 1: Produttività del lavoro in agricoltura, nessuna famiglia di genere.
        view = build_indicator_view("territorial", "1")
        self.assertIsNotNone(view)
        self.assertEqual(view["dimension_siblings"], [])


if __name__ == "__main__":
    unittest.main()
