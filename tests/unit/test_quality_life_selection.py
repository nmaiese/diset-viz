"""Gate espliciti della selezione provinciale esterna per la qualità della vita."""

import unittest
from unittest.mock import patch

from app import quality_life_selection as qls


def _item(name, *, family="ipr", direction="lower_better", year_max=2025,
          coverage=1.0, category="lavoro_opportunita"):
    return {
        "metadata": {
            "id": f"{family}:{name}", "family": family, "name": name,
            "direction": direction, "quality_life_category": category,
        },
        "levels": {"provincia": {"year_max": year_max, "coverage_latest": coverage}},
    }


class ProvincialExternalSelection(unittest.TestCase):
    def _select(self, items, bes_names=()):
        with patch.object(qls.provincial_families, "scoreables", return_value=items):
            return [item["metadata"]["id"] for item in qls.provincial_external_selection(set(bes_names))]

    def test_ammette_una_serie_che_passa_ogni_gate(self):
        self.assertEqual(self._select([_item("disoccupazione")]), ["ipr:disoccupazione"])

    def test_ogni_gate_esclude_da_solo(self):
        cases = {
            "verso descrittivo": _item("a", direction="contextual"),
            "anno vecchio": _item("b", year_max=2022),
            "copertura bassa": _item("c", coverage=0.79),
            "categoria ignota": _item("d", category="non_esiste"),
            "categoria vuota": _item("e", category=""),
        }
        for label, item in cases.items():
            with self.subTest(label):
                self.assertEqual(self._select([item]), [])

    def test_soglie_comprese(self):
        self.assertEqual(self._select([_item("x", year_max=2023, coverage=0.80)]), ["ipr:x"])

    def test_un_fenomeno_gia_nel_bes_resta_bes(self):
        item = _item("Tasso di disoccupazione 15-74 anni")
        bes = {qls._normalise_name("Tasso di disoccupazione 15-74 anni")}
        self.assertEqual(self._select([item], bes), [])

    def test_due_famiglie_esterne_non_contano_due_volte_lo_stesso_nome(self):
        items = [_item("Copertura FTTH", family="agcom"), _item("Copertura FTTH", family="mef")]
        self.assertEqual(self._select(items), ["agcom:Copertura FTTH"])



def _level_row(public_id, scoreable, *, direction="lower_better", category="reddito_accessibilita"):
    return {
        "target_indicator_id": public_id, "territory_level": "regione", "name": f"Serie {public_id}",
        "quality_life_category": category, "direction": direction, "scoreable": scoreable,
        "year_max": "2025", "coverage_latest": "1",
    }


class ExternalRegionalScoreGate(unittest.TestCase):
    """Il manifesto dei livelli decide dove ha una riga regionale; senza riga
    vale ancora score_eligible delle righe normalizzate."""

    NORMALIZED = {"eur:da_normalizzato": {"name": "Da normalizzato", "category": "salute_cura",
                                          "direction": "higher_better", "coverage": 1.0,
                                          "year_max": 2024}}

    def _gate(self, levels):
        with patch.object(qls, "external_regional_scoreables", return_value=dict(self.NORMALIZED)), \
             patch.object(qls.external_data, "get_external_levels", return_value=levels):
            return qls.external_regional_score_gate()

    def test_riga_dei_livelli_scoreable_entra(self):
        gate = self._gate([_level_row("eur:acceso", "true")])
        self.assertEqual(gate["eur:acceso"]["direction"], "lower_better")
        self.assertEqual(gate["eur:acceso"]["year_max"], 2025)

    def test_riga_dei_livelli_spenta_vince_sul_normalizzato(self):
        gate = self._gate([_level_row("eur:da_normalizzato", "false")])
        self.assertNotIn("eur:da_normalizzato", gate)

    def test_senza_riga_dei_livelli_vale_il_normalizzato(self):
        gate = self._gate([])
        self.assertIn("eur:da_normalizzato", gate)

    def test_verso_descrittivo_o_categoria_vuota_restano_fuori(self):
        gate = self._gate([_level_row("eur:a", "true", direction="contextual"),
                           _level_row("eur:b", "true", category="")])
        self.assertNotIn("eur:a", gate)
        self.assertNotIn("eur:b", gate)

    def test_le_righe_provinciali_e_le_famiglie_non_esterne_non_contano(self):
        provincial = {**_level_row("ipr:x", "true"), "territory_level": "provincia"}
        gate = self._gate([provincial, _level_row("bes:01SAL001", "true")])
        self.assertNotIn("ipr:x", gate)
        self.assertNotIn("bes:01SAL001", gate)

if __name__ == "__main__":
    unittest.main()
