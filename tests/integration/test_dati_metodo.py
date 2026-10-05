"""Il riquadro "Dati e metodo" sulle pagine indicizzabili.

La stessa macro (`v1/_dati_metodo.html`) appare sui sei tipi di pagina elencati
dalla spec: indicatore, provincia, regione, tema, qualita' della vita (le basi)
e articolo. Qui si controlla che ne esca davvero, senza JavaScript, con la
fonte e la firma della redazione.
"""

import re
import unittest

from app import app
from app.blog import get_posts
from app import publisher

MARKER = 'class="dati-metodo" data-dati-metodo'
# Il titolo che sul sito vivo non si vedeva: dentro il riquadro, non solo
# nell'`aria-label`, e una volta sola per pagina.
TITOLO = re.compile(r'<h[1-6] class="dati-metodo__titolo">\s*Dati e metodo\s*</h[1-6]>')

# Una pagina per tipo, abbastanza stabile da non sparire alla prossima ondata.
PAGINE = {
    "indicatore": "/indicatore/pil-pro-capite/ter-901",
    "provincia": "/provincia/lecce",
    "regione": "/regione/puglia",
    "tema": "/tema/lavoro-e-conciliazione",
    "qualita-della-vita": "/qualita-della-vita",
    "classifica": "/qualita-della-vita/classifica/regioni",
}


def _box(html):
    """Il blocco del riquadro, dall'apertura dell'`<aside>` alla chiusura."""
    inizio = html.index(MARKER)
    return html[inizio:html.index("</aside>", inizio)]


class IlRiquadroCompareNeiTipi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _pagina(self, percorso):
        risposta = self.client.get(percorso, follow_redirects=True)
        self.assertEqual(risposta.status_code, 200, percorso)
        return risposta.get_data(as_text=True)

    def _verifica(self, html, percorso):
        self.assertIn(MARKER, html, f"{percorso}: riquadro assente")
        riquadro = _box(html)
        self.assertRegex(riquadro, TITOLO,
                         f"{percorso}: dentro il riquadro non c'e' il titolo visibile "
                         "'Dati e metodo'")
        self.assertIn("dati-metodo__fonte", riquadro, f"{percorso}: fonte assente")
        self.assertIn("dati-metodo__firma", riquadro, f"{percorso}: firma assente")
        self.assertIn(publisher.editor_name(), riquadro, f"{percorso}: nome della redazione assente")
        self.assertIn('href="/metodologia"', riquadro, f"{percorso}: link alla metodologia assente")
        self.assertNotIn("<script", riquadro, f"{percorso}: JavaScript dentro il riquadro")
        # La sezione che contiene il riquadro non ne ripete il titolo: due volte
        # di fila si leggono come un refuso. Il titolo resta dentro l'`<aside>`,
        # e l'unico titolo della pagina che porta quelle parole e' quello.
        titoli = re.findall(r"<h[1-6][^>]*>\s*Dati e metodo\s*</h[1-6]>", html)
        self.assertEqual(len(titoli), 1,
                         f"{percorso}: {len(titoli)} titoli 'Dati e metodo' nella pagina, "
                         "uno solo: quello dentro il riquadro")

    def test_indicatore_provincia_regione_tema_qualita_e_classifica(self):
        for tipo, percorso in PAGINE.items():
            with self.subTest(tipo=tipo):
                self._verifica(self._pagina(percorso), percorso)

    def test_articolo(self):
        post = get_posts()
        self.assertTrue(post, "nessun articolo nel blog: la prova non guarda niente")
        percorso = f"/blog/{post[0]['slug']}"
        self._verifica(self._pagina(percorso), percorso)

    def test_non_compare_sul_ripiego_della_scheda(self):
        """Il riquadro sta nella regia della 1.0, non nel guscio di prima."""
        risposta = self.client.get("/indicatore/pil-pro-capite/ter-901", follow_redirects=True)
        self.assertIn(MARKER, risposta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
