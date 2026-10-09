"""La home non giudica il verso e non scrive un rapporto fra gli estremi.

Tre indicatori sintetici, uno per verso (`higher_better`, `lower_better`,
`contextual`): nessuna occorrenza di «Meglio se», «migliore», «volte» nel
pannello reso né nel SVG della fascia, e l'ordine della classifica resta
quello legato al verso.
"""

import re
import unittest

from app.data import REGION_GEO_AREA
from app.design import charts
from app.design.pages import home

PROIBITE = re.compile(r"Meglio se|migliore|volte", re.IGNORECASE)


def _meta(direction):
    return {"name": "Tasso di prova", "unit": "%", "value_unit": "%", "direction": direction,
            "canonical_path": "/indicatore/prova/tdp-1", "source_label": "Istat",
            "family": "territorial", "raw_id": "1"}


def _level(direction):
    keys = list(REGION_GEO_AREA)[:12]
    values = [10.0 + 3.1 * i for i in range(len(keys))]
    obs = [{"key": k, "name": k.title(), "value": v} for k, v in zip(keys, values)]
    obs.sort(key=lambda o: o["value"], reverse=direction in ("higher_better", "contextual"))
    return {"key": "regione", "plural": "regioni", "singular": "regione", "year_max": 2024,
            "observations": obs, "stats": {"year_avg": 25.0, "gap_ratio": 4.1},
            "profile_path": "/regione/"}


class VersoNeutro(unittest.TestCase):
    def pannello(self, direction):
        return home.level_panel(_meta(direction), _level(direction), "/?indicatore=tdp-1#dato")

    def test_nessuna_parola_di_giudizio_ne_rapporto(self):
        for direction in ("higher_better", "lower_better", "contextual"):
            with self.subTest(direction=direction):
                panel = self.pannello(direction)
                self.assertIsNotNone(panel)
                self.assertIsNone(PROIBITE.search(panel["strip"]["svg"]), panel["strip"]["svg"])
                for k in ("lead_claim", "table_claim"):
                    self.assertIsNone(PROIBITE.search(panel[k] or ""), panel[k])

    def test_la_fascia_dice_la_differenza_in_unita(self):
        panel = self.pannello("higher_better")
        self.assertIn("differenza 34,1 punti percentuali", panel["strip"]["svg"])

    def test_l_ordine_resta_legato_al_verso(self):
        alto = self.pannello("higher_better")["value_rows"]
        basso = self.pannello("lower_better")["value_rows"]
        self.assertGreater(alto[0]["value"], alto[-1]["value"])
        self.assertLess(basso[0]["value"], basso[-1]["value"])
        self.assertTrue(self.pannello("lower_better")["lower_better"])
        self.assertFalse(self.pannello("contextual")["lower_better"])

    def test_l_etichetta_descrive_solo_l_ordinamento(self):
        for direction, atteso in (("higher_better", "Ordinata dal valore più alto"),
                                  ("lower_better", "Ordinata dal valore più basso"),
                                  ("higher_worse", "Ordinata dal valore più basso"),
                                  ("contextual", "")):
            with self.subTest(direction=direction):
                pick = {"meta": _meta(direction), "level": _level(direction), "other": None}
                f = home.feature(pick)
                self.assertEqual(f["verso"], atteso)
                self.assertIsNone(PROIBITE.search(f["verso"]))


if __name__ == "__main__":
    unittest.main()
