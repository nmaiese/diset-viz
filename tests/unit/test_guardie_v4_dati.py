"""Published scale, source selection, and counterexamples for G1/G6/G7."""
import unittest
from decimal import Decimal
from unittest.mock import patch

from scripts.editoriale.guardie_v4 import editorial_checks
from scripts.editoriale import guardia


class GuardieDati(unittest.TestCase):
    REGIONS = {"2023": {"a": Decimal("8.8"), "b": Decimal("9.0")}}
    PROVINCES = {"2022": {str(i): Decimal("1.0") for i in range(103)}}

    def checks(self, sentence, data=None, geo="regioni", **kwargs):
        return editorial_checks(sentence, self.REGIONS if data is None else data, geo, **kwargs)

    def test_g1_blocca_media_chiamata_italia(self):
        self.assertIn(("errore", "G1", "media semplice di 2 regioni nel 2023 chiamata nazionale"),
                      self.checks("In Italia nel 2023 la quota è 8,9%."))
        self.assertFalse(any(rule == "G1" for _, rule, _ in self.checks("La media semplice in Italia nel 2023 è 8,9%.")))
        self.assertFalse(any(rule == "G1" for _, rule, _ in self.checks(
            "Il dato nazionale ufficiale Istat nel 2023 è 8,9%.", official=True)))
        self.assertEqual(self.checks("In Italia la quota è 8,9%.", data={})[0][:2], ("non verificabile", "G1"))

    def test_g1_soglia_decimale(self):
        self.assertTrue(any(rule == "G1" for _, rule, _ in self.checks("Italia 8,95 nel 2023.")))
        self.assertFalse(any(rule == "G1" for _, rule, _ in self.checks("Italia 8,96 nel 2023.")))

    def test_g6_durata_zero_e_rapporto_valido(self):
        self.assertEqual(self.checks("Il divario fra estremi è 1,2 volte.", unit="anni")[0][:2], ("errore", "G6"))
        zero = {"2023": {"a": Decimal("0"), "b": Decimal("3")}}
        self.assertEqual(self.checks("Il rapporto fra estremi è 3 volte.", data=zero)[0][:2], ("errore", "G6"))
        self.assertEqual(self.checks("Il rapporto fra estremi è 3 volte.")[0][:2], ("avviso", "G6"))
        self.assertEqual(self.checks("L'ho detto due volte."), [])

    def test_g7_osservati_e_denominatore(self):
        data = self.PROVINCES
        self.assertEqual(self.checks("Nel 2022 le 107 province hanno dato.", data, "province")[0][:2], ("errore", "G7"))
        self.assertFalse(any(rule == "G7" for _, rule, _ in self.checks("Nel 2022 le 103 province hanno dato.", data, "province")))
        self.assertFalse(any("107" in reason for _, rule, reason in self.checks(
            "Nel 2022, 95 province su 107 province hanno dato.", data, "province") if rule == "G7"))
        self.assertEqual(self.checks("Nel 2022 tutte le province hanno dato.", data, "province")[0][:2], ("errore", "G7"))

    def test_scheda_usa_livello_e_anno_selezionati(self):
        view = {"meta": {"name": "Quota", "unit": "%", "source": "Istat"},
                "levels": [{"key": "regione", "matrix": {"2023": {"a": 8.8, "b": 9.0}}}]}
        entry = {"level": "regione", "vintage": 2023, "lead": "In Italia la quota è 8,9%.", "sections": []}
        with patch.object(guardia, "build_indicator_view", return_value=view):
            defects = guardia.check_article("901", entry)
        self.assertTrue(any(defect.check == "G1" for defect in defects))


if __name__ == "__main__":
    unittest.main()
