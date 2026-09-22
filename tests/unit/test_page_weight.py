"""Il peso che ogni pagina porta, e che nessuno guarda finche' non esplode.

La mappa dell'Italia sta **in linea** in sei template, e in linea ci deve stare:
le regioni si colorano da CSS (`[data-key]`) e la pagina deve renderla senza
JavaScript, che e' cio' che l'audit di discoverability verifica. Quindi non si
puo' spostare in un asset esterno, e l'unica leva e' quanto pesa il disegno.
"""
import re
import unittest
from pathlib import Path

MAPPA = Path(__file__).resolve().parents[2] / "app" / "templates" / "_italy_map.html"


class LaMappaNonRiprendePeso(unittest.TestCase):
    def setUp(self):
        self.testo = MAPPA.read_text(encoding="utf-8")

    def test_i_path_non_tornano_a_tre_decimali(self):
        """Tre decimali su un viewBox 560x660 sono 0,001 unita': meno di un
        millesimo di pixel a qualunque larghezza reale. Ne costavano 31 KB per
        pagina, su sei tipi di pagina."""
        troppo_precisi = []
        for disegno in re.findall(r'd="([^"]*)"', self.testo):
            troppo_precisi += re.findall(r"-?[0-9]+\.[0-9]{2,}", disegno)
        self.assertEqual(troppo_precisi[:5], [], f"{len(troppo_precisi)} numeri oltre il decimo")

    def test_la_mappa_resta_sotto_i_cento_kb(self):
        peso = len(self.testo.encode("utf-8"))
        self.assertLess(peso, 100_000, f"la mappa pesa {peso} byte")

    def test_ci_sono_ancora_venti_regioni_con_la_loro_chiave(self):
        """Una minimizzazione che perde un path toglie una regione dalla mappa
        senza che niente fallisca: la pagina rende, con un buco."""
        chiavi = re.findall(r'data-key="([^"]+)"', self.testo)
        self.assertEqual(len(chiavi), 20)
        self.assertEqual(len(set(chiavi)), 20)

    def test_ogni_path_e_chiuso(self):
        for disegno in re.findall(r'd="([^"]*)"', self.testo):
            self.assertTrue(disegno.rstrip().upper().endswith("Z"), disegno[-40:])


if __name__ == "__main__":
    unittest.main()
