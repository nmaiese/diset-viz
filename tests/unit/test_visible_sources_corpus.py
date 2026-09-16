"""La citazione del corpus arriva al lettore anche quando l'url e' gia' in elenco.

Il 16 settembre 2026 ter-901 e' andato in pagina con due affermazioni Istat
citate nella prosa e **nessuna citazione visibile**. `visible_sources`
deduplicava per url, e la quarta guardia di `motore verifica` impone che ogni
url linkato nella prosa stia anche nell'elenco `fonti`: quindi l'url di
un'affermazione citata ci sta sempre, e la deduplica per url la scartava
sempre. In pagina restavano i titoli dei documenti, che dicono *quale documento
e'*, e spariva la frase, che e' la sola cosa che il lettore non puo' ricavare
dalla pagina.

Nessuna guardia lo vedeva: `motore verifica` diceva `spiegazione.zero: false`
perche' i claim stavano nell'entry, e `fonti_inline_rotte` era vuoto perche'
l'url rispondeva. Il difetto stava nello spazio fra i due controlli.

Un test per lato, come chiede il Quadro: l'url che coincide, e l'url nuovo.
"""

import unittest
from unittest import mock

from app import indicator_texts

URL = "https://www.istat.it/comunicato-stampa/una-cosa/"
ALTRO = "https://www.bancaditalia.it/pubblicazioni/una-altra/"

CLAIM = {
    "id": "istat-coesione-1",
    "source_id": "istat-rapporto-annuale",
    "url": URL,
    "quote": "il divario non si e' chiuso in vent'anni",
}
REGISTRO = {"istat-rapporto-annuale": {"institution": "Istat, Rapporto annuale"}}


def _entry(fonti, claims=("istat-coesione-1",)):
    return {"fonti": list(fonti),
            "sections": [{"role": "libera", "h": "Una sezione",
                          "body": "testo", "claims": list(claims)}]}


class CitazioneSullUrlCheCoincide(unittest.TestCase):
    """L'url e' gia' in `fonti`: l'etichetta resta e la citazione si aggiunge."""

    def test_la_citazione_arriva_in_pagina(self):
        entry = _entry([{"testo": 'Istat, "Una cosa", comunicato del 13 giugno 2023',
                         "url": URL}])
        with mock.patch.object(indicator_texts.context, "claims", return_value=[CLAIM]), \
             mock.patch.object(indicator_texts.context, "sources", return_value=REGISTRO):
            fonti = indicator_texts.visible_sources(entry)

        self.assertEqual(len(fonti), 1, "una sola voce per un solo url")
        testo = fonti[0]["testo"]
        self.assertIn("il divario non si e' chiuso in vent'anni", testo,
                      "la citazione e' la sola cosa che il lettore non ricava dalla pagina")
        self.assertIn('Istat, "Una cosa", comunicato del 13 giugno 2023', testo,
                      "l'etichetta autorata dice quale documento e', e non si butta")
        self.assertEqual(fonti[0]["url"], URL)

    def test_l_entry_di_partenza_non_viene_modificata(self):
        """`visible_sources` e' una vista, e l'entry sta in una cache di processo."""
        fonte = {"testo": "Istat, un titolo", "url": URL}
        entry = _entry([fonte])
        with mock.patch.object(indicator_texts.context, "claims", return_value=[CLAIM]), \
             mock.patch.object(indicator_texts.context, "sources", return_value=REGISTRO):
            indicator_texts.visible_sources(entry)
        self.assertEqual(fonte["testo"], "Istat, un titolo")


class CitazioneSuUnUrlNuovo(unittest.TestCase):
    """L'url non e' in `fonti`: si aggiunge una voce, come faceva gia' prima."""

    def test_si_aggiunge_in_coda(self):
        entry = _entry([{"testo": "Banca d'Italia, un altro documento", "url": ALTRO}])
        with mock.patch.object(indicator_texts.context, "claims", return_value=[CLAIM]), \
             mock.patch.object(indicator_texts.context, "sources", return_value=REGISTRO):
            fonti = indicator_texts.visible_sources(entry)

        self.assertEqual([f["url"] for f in fonti], [ALTRO, URL],
                         "le autorate prima, le derivate in coda")
        self.assertIn("il divario non si e' chiuso in vent'anni", fonti[1]["testo"])
        self.assertIn("Istat, Rapporto annuale", fonti[1]["testo"])

    def test_una_citazione_non_mostrabile_non_duplica_la_fonte(self):
        """Con un carattere vietato resta l'istituzione, e se l'url c'e' gia' non si ripete."""
        claim = dict(CLAIM, quote="una frase con il punto e virgola; dentro")
        entry = _entry([{"testo": "Istat, un titolo", "url": URL}])
        with mock.patch.object(indicator_texts.context, "claims", return_value=[claim]), \
             mock.patch.object(indicator_texts.context, "sources", return_value=REGISTRO):
            fonti = indicator_texts.visible_sources(entry)
        self.assertEqual(len(fonti), 1)
        self.assertEqual(fonti[0]["testo"], "Istat, un titolo")


if __name__ == "__main__":
    unittest.main()
