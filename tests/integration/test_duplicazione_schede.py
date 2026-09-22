"""L'apparato sta nell'apparato, e il racconto resta il racconto.

Il 22 settembre 2026 il 42,5% delle parole dell'articolo medio di una scheda
indicatore viveva dentro una sequenza di otto parole che si leggeva identica su
altre pagine. Non era prosa: era metodo messo dentro la narrazione. La frase
"Il confronto usa le 20 regioni presenti in entrambi gli anni" stava su 269
pagine su 372, dentro la sezione "Come e' cambiato nel tempo", e diceva su che
perimetro e' calcolato il numero, non che cosa era successo.

Adesso quelle frasi stanno in due posti dichiarati, il riquadro "Come leggere
il dato" e l'apparato "Fonti e verifica", e il racconto e' sceso al 26,8%.

Queste prove tengono il confine. Sono due, e la prima conta piu' della seconda:

1. le frasi di metodo **non tornano** dentro il blocco articolo. E' il tipo di
   regressione che nessuno nota, perche' ogni singolo ritorno sembra una frase
   in piu' in un paragrafo;
2. la quota ripetuta non risale oltre un tetto, su un campione.

Il campione e' di sessanta pagine e il tetto e' largo. La misura vera e'
`bin/py scripts/duplicazione.py`, che legge tutte e 372 le schede e stampa due
numeri: quella qui e' una rete, non la misura.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import app  # noqa: E402
from app import indicator_universe  # noqa: E402
from scripts import duplicazione  # noqa: E402


# Le frasi che dicono **come si calcola** o **come si legge**, non che cosa
# dicono questi numeri. Ognuna stava dentro il racconto, e ognuna ha una casa.
METODO = (
    "Il confronto usa le",
    "presenti in entrambi gli anni",
    "non ha una direzione univoca",
    "statisticamente significativa",
    "La graduatoria è quindi ordinata",
    "Il confronto applica la stessa definizione",
)

CAMPIONE = 60
TETTO_RACCONTO = 25.0
TETTO_CON_METODO = 35.0


def _blocco(html, espressione):
    trovato = espressione.search(html)
    return trovato.group(0) if trovato else ""


class IlMetodoNonTornaNelRacconto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.pagine = []
        for vista in indicator_universe.indexable_catalog():
            risposta = cls.client.get(vista["meta"]["canonical_path"], follow_redirects=True)
            if risposta.status_code == 200:
                cls.pagine.append((vista["meta"]["canonical_path"], risposta.get_data(as_text=True)))
            if len(cls.pagine) >= 25:
                break

    def test_nessuna_frase_di_metodo_sta_dentro_il_blocco_articolo(self):
        self.assertGreater(len(self.pagine), 10, "campione troppo piccolo per dire qualcosa")
        for percorso, html in self.pagine:
            articolo = _blocco(html, duplicazione._ARTICOLO)
            self.assertTrue(articolo, percorso)
            for frase in METODO:
                with self.subTest(pagina=percorso, frase=frase):
                    self.assertNotIn(frase, articolo,
                                     "una frase di metodo è tornata dentro il racconto")

    def test_il_riquadro_del_metodo_c_e_su_ogni_scheda(self):
        """Da quando il metodo e' uscito dall'articolo, questo riquadro e'
        l'unico posto in cui vive: una scheda senza non direbbe piu' in che
        verso si legge la sua graduatoria."""
        for percorso, html in self.pagine:
            with self.subTest(pagina=percorso):
                self.assertIn('id="come-leggere"', html)
                self.assertTrue(_blocco(html, duplicazione._COME_LEGGERE), percorso)


class LaQuotaRipetutaNonRisale(unittest.TestCase):
    def test_sul_campione_resta_sotto_il_tetto(self):
        esito = duplicazione.misura(limite=CAMPIONE)
        self.assertGreaterEqual(esito["pagine"], CAMPIONE // 2)
        racconto = esito["racconto"]["quota"]
        intero = esito["con_metodo"]["quota"]
        self.assertLess(racconto, TETTO_RACCONTO,
                        f"il racconto è tornato ripetitivo: {racconto}%")
        self.assertLess(intero, TETTO_CON_METODO,
                        f"scheda e metodo insieme sono tornati ripetitivi: {intero}%")


if __name__ == "__main__":
    unittest.main()
