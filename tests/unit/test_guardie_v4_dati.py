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

    def test_g7_sottoinsieme_e_perimetro_osservato(self):
        data = self.PROVINCES
        self.assertFalse(any(rule == "G7" for _, rule, _ in self.checks(
            "Nel 2022, 8 province superano la media delle 103 osservate.", data, "province")))
        self.assertFalse(any(rule == "G7" for _, rule, _ in self.checks(
            "Nel 2022, solo 8 province hanno valori sopra la media.", data, "province")))
        self.assertFalse(any(rule == "G7" for _, rule, _ in self.checks(
            "Nel 2022, 8 province su 103 superano la media.", data, "province")))
        self.assertTrue(any(rule == "G7" and severity == "errore" for severity, rule, _ in self.checks(
            "Nel 2022, 8 province superano la media delle 104 osservate.", data, "province")))

    def test_g7_denominatore_su_n_non_e_copertura_csv(self):
        self.assertFalse(any(rule == "G7" for _, rule, _ in self.checks(
            "Nel 2022, 8 province su 107 superano la media.", self.PROVINCES, "province")))

    def test_g7_denominatore_dichiarato_osservato_errato_blocca(self):
        self.assertTrue(any(rule == "G7" and severity == "errore" for severity, rule, _ in self.checks(
            "Nel 2022, 8 province su 107 osservate superano la media.", self.PROVINCES, "province")))

    def test_scheda_usa_livello_e_anno_selezionati(self):
        view = {"meta": {"name": "Quota", "unit": "%", "source": "Istat"},
                "levels": [{"key": "regione", "matrix": {"2023": {"a": 8.8, "b": 9.0}}}]}
        entry = {"level": "regione", "vintage": 2023, "lead": "In Italia la quota è 8,9%.", "sections": []}
        with patch.object(guardia, "build_indicator_view", return_value=view):
            defects = guardia.check_article("901", entry)
        self.assertTrue(any(defect.check == "G1" for defect in defects))

    def test_g3_scheda_segnala_fasce_diverse_come_avviso(self):
        view = {"meta": {"name": "Occupazione", "unit": "%", "source": "Istat"},
                "dimension_siblings": [{"id": "902", "value": "15-34"}],
                "levels": [{"key": "regione", "matrix": {"2024": {"a": 40, "b": 50}}}]}
        entry = {"level": "regione", "vintage": 2024,
                 "lead": "Tasso per 15-34 anni.",
                 "sections": [{"role": "libera", "h": "Adulti", "body": "Tasso per 35-64 anni."}]}
        with patch.object(guardia, "build_indicator_view", return_value=view):
            defects = guardia.check_article("901", entry)
        self.assertTrue(any(defect.check == "G3-avviso" for defect in defects))
        self.assertFalse(any(defect.check == "G3" for defect in defects))

    REGIONI_20 = {"2025": {str(i): Decimal("1.0") for i in range(20)}}
    FRASI_VARIAZIONE = [
        "La quota cala in 17 regioni e cresce in 3.",
        "Nell'ultimo anno la media non cambia: 10 regioni salgono e 10 scendono.",
        "Nell'ultimo anno 15 regioni in salita, 4 in discesa e una invariata.",
        "Con 15 regioni in salita, 4 in discesa e una invariata.",
        "Nell'ultimo anno la quota scende in 12 regioni, sale in 7 e resta uguale in una.",
        "Nell'ultimo anno 8 regioni salgono, 9 scendono e 3 restano invariate.",
        "Con 13 regioni in discesa, 5 in salita e 2 invariate.",
        "Nell'ultimo anno la media sale da 0,40 a 0,75: 7 regioni aumentano, 4 diminuiscono e 9 restano invariate.",
        "Con aumenti in 12 regioni e cali in 8.",
        "Con aumento in 15 regioni e calo in 5.",
        "La quota aumenta in 13 regioni e diminuisce in 7.",
        "La media delle regioni è 26,0% e in un anno è calata in 15 regioni.",
        "La fiducia sale in 9 regioni, scende in 9 e resta invariata in 2.",
        "La media è ferma a 5,3, con 13 regioni in calo e 7 in aumento.",
        "11 regioni calano, 8 salgono e una resta invariata.",
        "3 regioni rimangono invariate.",
        "3 regioni rimangono stabili.",
        "Una regione rimane invariata.",
        "4 regioni sono stabili.",
        "4 regioni sono invariate.",
        "4 regioni sono ferme.",
        "5 regioni stazionarie.",
        "5 regioni restano stazionarie.",
    ]

    def g7(self, sentence, data=None):
        return [r for r in self.checks(sentence, self.REGIONI_20 if data is None else data) if r[1] == "G7"]

    def test_g7_conteggi_di_variazione_sono_sottoinsiemi(self):
        for frase in self.FRASI_VARIAZIONE:
            with self.subTest(frase=frase):
                self.assertEqual(self.g7(frase), [])

    def test_g7_variazione_con_somma_oltre_le_osservate_resta_errore(self):
        for frase in ("13 regioni salgono e 9 scendono.",
                      "La quota sale in 13 regioni, scende in 9 e resta invariata in una.",
                      "Sale in 21 regioni.",
                      "Con 15 regioni in salita, 4 in discesa e due invariate.",
                      "13 regioni salgono e 9 scendono.",
                      "In 25 regioni la quota sale.",
                      "3 regioni sono stabili e 18 salgono."):
            with self.subTest(frase=frase):
                self.assertEqual(self.g7(frase)[0][:2], ("errore", "G7"))

    def test_g7_copertura_sbagliata_resta_errore(self):
        dati19 = {"2025": {str(i): Decimal("1.0") for i in range(19)}}
        self.assertEqual(self.g7("Nel 2025 i dati coprono 13 regioni.")[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Il dato copre 13 regioni.")[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Nel 2025 le 13 regioni del Mezzogiorno hanno dato.")[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Nel 2025 il dato è presente in tutte le 20 regioni.", dati19)[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Nel 2025 il dato è presente in tutte le regioni.", dati19)[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Nel 2025 il dato copre 20 regioni.", dati19)[0][:2], ("errore", "G7"))
        self.assertEqual(self.g7("Nel 2025 le 13 regioni sono state osservate e sale in 3.")[0][:2], ("errore", "G7"))


if __name__ == "__main__":
    unittest.main()
