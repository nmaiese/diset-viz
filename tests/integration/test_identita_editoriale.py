"""L'identita' con cui il sito firma sta in `config/identita.yaml`, e basta.

Il passaggio da un marchio a una persona deve costare la modifica di quel file.
Il nome finto qui sotto esiste solo in questo test: nessuna persona vera e
nessuna persona inventata entra nel sito.
"""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import app, publisher

ROOT = Path(__file__).resolve().parents[2]
NOME_DI_PROVA = "Zeta Provaldi"
IDENTITA_PERSONA = f"""\
tipo: persona
nome: {NOME_DI_PROVA}
descrizione: Persona di prova, esiste solo nel test.
email: prova@example.invalid
url_autore: /chi-siamo
same_as: []
intestatario_legale: ""
"""


def jsonld(response):
    blocchi = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        response.get_data(as_text=True), re.S,
    )
    return [json.loads(blocco) for blocco in blocchi]


def trova(nodi, tipo):
    for nodo in nodi:
        if isinstance(nodo, dict) and nodo.get("@type") == tipo:
            return nodo
        if isinstance(nodo, dict) and "@graph" in nodo:
            trovato = trova(nodo["@graph"], tipo)
            if trovato:
                return trovato
    return None


class IdentitaEditorialeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.slug = re.search(r'href="/blog/([^"?]+)"', self.client.get("/blog").get_data(as_text=True)).group(1)

    def persona(self):
        cartella = tempfile.TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        percorso = Path(cartella.name) / "identita.yaml"
        percorso.write_text(IDENTITA_PERSONA, encoding="utf-8")
        return mock.patch.object(publisher, "IDENTITY_PATH", percorso)

    def test_il_file_di_produzione_e_un_marchio_senza_persone(self):
        ident = publisher.identity()
        self.assertEqual(ident["tipo"], "organizzazione")
        self.assertEqual(ident["same_as"], [])
        self.assertEqual(ident["intestatario_legale"], "", "TODO titolare: l'intestatario non si inventa")
        articolo = self.client.get(f"/blog/{self.slug}")
        autore = trova(jsonld(articolo), "Article")["author"]
        self.assertEqual(autore["@type"], "Organization")
        self.assertEqual(autore["name"], ident["nome"])
        testo = articolo.get_data(as_text=True)
        self.assertIn(f'<meta name="author" content="{ident["nome"]}">', testo)
        self.assertEqual(trova(jsonld(articolo), "Article")["publisher"], publisher.ORGANIZATION)

    def test_con_tipo_persona_cambiano_tutte_le_superfici(self):
        with self.persona():
            articolo = self.client.get(f"/blog/{self.slug}")
            testo = articolo.get_data(as_text=True)
            autore = trova(jsonld(articolo), "Article")["author"]
            self.assertEqual((autore["@type"], autore["name"]), ("Person", NOME_DI_PROVA))
            self.assertEqual(trova(jsonld(articolo), "Article")["publisher"]["@type"], "Organization")
            self.assertIn(f'<meta name="author" content="{NOME_DI_PROVA}">', testo)
            self.assertIn(NOME_DI_PROVA, testo, "byline e footer")

            lista = self.client.get("/blog").get_data(as_text=True)
            self.assertIn(NOME_DI_PROVA, lista)

            about = self.client.get("/chi-siamo")
            self.assertIn(NOME_DI_PROVA, about.get_data(as_text=True))
            entita = trova(jsonld(about), "AboutPage")["mainEntity"]
            self.assertEqual((entita["@type"], entita["name"]), ("Person", NOME_DI_PROVA))

            feed = self.client.get("/blog/feed.xml").get_data(as_text=True)
            self.assertIn(f"<dc:creator>{NOME_DI_PROVA}</dc:creator>", feed)

            privacy = self.client.get("/privacy").get_data(as_text=True)
            self.assertIn(NOME_DI_PROVA, privacy)

            home = self.client.get("/").get_data(as_text=True)
            self.assertIn(NOME_DI_PROVA, home, "il footer firma con l'identita'")

            from app import agent_discovery, blog
            post = blog.get_post(self.slug)
            self.assertIn(f"Autore: {NOME_DI_PROVA}", agent_discovery.blog_post_markdown(post, "https://x"))
            self.assertIn(NOME_DI_PROVA, agent_discovery.blog_index_markdown([post], "https://x"))

        # Fuori dal `with` il sito torna al marchio: la sostituzione non resta in cache.
        self.assertEqual(publisher.identity()["tipo"], "organizzazione")
        self.assertNotIn(NOME_DI_PROVA, self.client.get("/chi-siamo").get_data(as_text=True))

    def test_tipo_non_ammesso_o_nome_vuoto_falliscono(self):
        with tempfile.TemporaryDirectory() as cartella:
            for contenuto in ("tipo: azienda\nnome: X\n", "tipo: persona\nnome: ''\n"):
                percorso = Path(cartella) / "x.yaml"
                percorso.write_text(contenuto, encoding="utf-8")
                with self.subTest(contenuto=contenuto), mock.patch.object(publisher, "IDENTITY_PATH", percorso):
                    with self.assertRaises(ValueError):
                        publisher.identity()

    def test_nessuna_firma_codificata_fuori_dal_file_di_identita(self):
        """Il grep dell'accettazione: il nome della firma sta solo nel file."""
        nome = publisher.identity()["nome"]
        for vecchio in (nome, "Aniello Maiese", "Maiese"):
            risultato = subprocess.run(
                ["git", "grep", "-n", "-I", vecchio, "--", "app", "scripts", "tests", "config", "Dockerfile",
                 ":(exclude)config/identita.yaml", ":(exclude)tests/integration/test_identita_editoriale.py"],
                cwd=ROOT, capture_output=True, text=True,
            )
            with self.subTest(vecchio=vecchio):
                self.assertEqual(risultato.stdout.strip(), "", f"{vecchio!r} codificato fuori da config/identita.yaml")

    def test_il_file_di_identita_entra_nell_immagine(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY config/identita.yaml config/identita.yaml", dockerfile)


if __name__ == "__main__":
    unittest.main()
