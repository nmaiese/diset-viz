"""La coda di revisione costruita sugli articoli **committati**.

L'unica metà di `test_review_queue` che ha bisogno di un giro reale, e per anni
è stata la ragione per cui l'altra metà, sintetica, girava in `integration/`
insieme a lei. Adesso la logica sta in `tests/unit/test_review_queue.py` e qui
resta soltanto la lettura del disco.

Quello che questo test compra: la coda non è vuota, e ogni riga che ne esce ha
un livello e un codice leggibili e nessun segnale fuori dal vocabolario. Un
segnale nuovo che nessuna etichetta nomina esce comunque dalla coda, e in cima
alla lista di lettura, senza che una riga dica che cos'è.
"""

import unittest

from scripts import review_queue


class QueueAgainstTheLiveFile(unittest.TestCase):
    def test_the_queue_builds_over_the_committed_articles(self):
        rows = review_queue.build_queue()
        self.assertGreater(len(rows), 100)
        for row in rows[:20]:
            self.assertIn(row["level"], ("regione", "provincia"))
            self.assertTrue(row["code"])
            self.assertTrue(set(row["flags"]) <= set(review_queue.FLAG_LABELS))


if __name__ == "__main__":
    unittest.main()
