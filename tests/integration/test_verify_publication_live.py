"""Fase D, end-to-end: la verifica della pubblicazione contro la pagina servita.

Usa il test client dell'app come sito, cosi' e' deterministico e senza rete. Un
articolo committato, la sua pagina reale, la firma di contenuto che deve
combaciare, e la prova che promuove la pratica a `pubblicata`. E' la prova che il
pezzo nuovo del modello (la transizione `fusa -> pubblicata`) regge contro un
sito vero, non solo contro un HTML finto.
"""

import pathlib
import tempfile
import unittest
from urllib.parse import urlsplit

from app import app
from scripts import indicator_store, practice_timeline
from scripts import verify_publication as v

# Un indicatore territoriale committato, riletto e verificato: la sua pagina
# porta il lead e il vintage. Se un giorno sparisce, il test lo dice invece di
# fingere di aver provato.
PINNED = "651"


def _client_fetcher(client):
    def fetch(url):
        resp = client.get(urlsplit(url).path, follow_redirects=True)
        if resp.status_code != 200:
            raise OSError(f"HTTP {resp.status_code}")
        return resp.get_data(as_text=True)
    return fetch


class PublicationCheckAgainstServedPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.fetch = _client_fetcher(self.client)
        self.entry = indicator_store.read(PINNED)
        if self.entry is None:
            self.skipTest(f"l'articolo {PINNED} non e' piu' nel repo")
        self.code = practice_timeline.code_of(PINNED)
        self.url = v.build_url(self.code, base="http://test")

    def test_code_only_url_301s_and_the_signature_matches(self):
        # /indicatore/ter-651 deve reindirizzare alla forma canonica con lo slug
        resp = self.client.get(f"/indicatore/{self.code}")
        self.assertIn(resp.status_code, (301, 308))
        result = v.verify(self.url, self.entry, fetcher=self.fetch)
        self.assertTrue(result["ok"], result)

    def test_wrong_vintage_does_not_match_the_page(self):
        tampered = dict(self.entry)
        tampered["vintage"] = 1873  # un anno che la pagina non porta di sicuro
        result = v.verify(self.url, tampered, fetcher=self.fetch)
        self.assertFalse(result["vintage_ok"])
        self.assertFalse(result["ok"])

    def test_a_written_proof_makes_the_reconstruction_pubblicata(self):
        result = v.verify(self.url, self.entry, fetcher=self.fetch)
        result["code"] = self.code
        self.assertTrue(result["ok"])
        root = pathlib.Path(tempfile.mkdtemp())
        v.write_proof(v.build_proof(self.entry, result), root=root)
        d = practice_timeline.load_real(proofs_root=root).get(PINNED)
        self.assertIsNotNone(d)
        self.assertTrue(d["published"])
        # 651 ha il ciclo editoriale completo (scritto, firmato, verificato),
        # quindi la prova lo porta fino a pubblicata.
        self.assertEqual(d["state"], "pubblicata")


if __name__ == "__main__":
    unittest.main()
