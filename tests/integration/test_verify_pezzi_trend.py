"""I pezzi gia' committati che dichiarano `trend:` passano la guardia, in CI.

`verify.py` e' la guardia che ferma un pezzo prima della PR: cifra nel dossier,
caratteri vietati, frontmatter, foto con la sua scheda, link interni, figure,
sezione delle fonti. Fino al 29 settembre 2026 non l'eseguiva nessuno su un
file committato, quindi un pezzo con una cifra fuori dal dossier poteva stare in
`master` indisturbato e lo scoprivano i lettori.

Il test gira `verify.py --offline`: salta l'unico controllo che apre una URL
esterna, la richiesta al server delle fonti citate, e tiene tutto il resto.
Offline perche' in CI non si puo' chiedere a quattro domini se rispondono, e perche'
una fonte che non si raggiunge da una rete filtrata non e' un difetto del pezzo.
Il controllo dei link interni resta, e passa dall'app di Flask con il suo
`test_client`: e' locale, non una chiamata di rete.

`content/` e' di Nello e questo test non lo tocca. Un pezzo gia' committato che
falla non si corregge qui: si mette in `ESCLUSI` con il motivo e il nome
dell'errore, cosi' il rosso resta visibile e qualcuno lo guarda.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

import frontmatter

from scripts.trend_articles import common, verify

# slug del pezzo: (motivo, nome dell'errore che la guardia ha restituito).
# Vuota al 29 settembre 2026: i quattro pezzi del 23 settembre passano tutti.
ESCLUSI: dict[str, tuple[str, str]] = {}


def _pezzi() -> list[tuple[Path, str]]:
    """I pezzi che dichiarano `trend:`, con lo slug col calcolo di verify.py."""
    found = []
    for path in sorted(common.POSTS_DIR.glob("*.md")):
        m = frontmatter.load(path).metadata
        if m.get("trend"):
            found.append((path, m.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)))
    return found


class VerifyPezziTrend(unittest.TestCase):
    def test_i_pezzi_con_trend_ci_sono_e_ogni_escluso_esiste(self):
        """Il test non puo' passare perche' la glob non trova pezzi, e ogni
        esclusione deve corrispondere a un pezzo che c'e' davvero."""
        slug = {s for _, s in _pezzi()}
        self.assertGreaterEqual(len(slug), 1, "nessun content/posts/*.md dichiara trend: nel frontmatter")
        self.assertLessEqual(set(ESCLUSI), slug, "ESCLUSI nomina un pezzo che non c'e' fra quelli con trend:")

    def test_ogni_pezzo_committato_passa_la_guardia(self):
        for path, slug in _pezzi():
            with self.subTest(pezzo=slug):
                if slug in ESCLUSI:
                    continue
                errori, _ = verify.verify(path, offline=True)
                # Gli avvisi non entrano nel verdetto: sono cose da leggere, non
                # cose che fermano il pezzo.
                self.assertEqual(errori, [])

    def test_nessun_escluso_passa_ancora(self):
        """Un pezzo in ESCLUSI che ormai passa e' un pezzo da togliere dalla
        lista: la lista deve restare corta, non comoda."""
        for slug, (motivo, nome_errore) in ESCLUSI.items():
            with self.subTest(pezzo=slug):
                path = next(p for p, s in _pezzi() if s == slug)
                errori, _ = verify.verify(path, offline=True)
                self.assertTrue(errori, f"{slug} e' in ESCLUSI ({motivo}) ma non da piu' errori: toglilo")
                self.assertTrue(any(nome_errore in e for e in errori),
                                f"{slug} non da piu' l'errore {nome_errore!r}: aggiorna ESCLUSI ({errori})")

    def test_la_riga_di_comando_ha_l_opzione_offline(self):
        """La guardia gira dalla riga di comando: un test che chiamasse solo la
        funzione passerebbe anche senza `--offline`."""
        post = _pezzi()[0][0]
        esito = subprocess.run(
            [sys.executable, "-m", "scripts.trend_articles.verify", "--offline", str(post)],
            cwd=common.ROOT, capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(esito.returncode, 0, f"{esito.stdout}\n{esito.stderr}")


if __name__ == "__main__":
    unittest.main()
