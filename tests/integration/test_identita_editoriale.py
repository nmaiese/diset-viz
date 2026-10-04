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
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit
from unittest import mock

from flask import Response

from app import agent_discovery, app, publisher

ROOT = Path(__file__).resolve().parents[2]
# Il gestore GitHub personale: non deve comparire in nessuna pagina servita.
GESTORE_GITHUB = "nm" + "aiese"
COGNOME_TITOLARE = "mai" + "ese"
EMAIL_PERSONALE = COGNOME_TITOLARE + ".next" + "@" + "gmail" + ".com"
# TODO titolare: aggiungere il dominio personale se esiste
DOMINI_PERSONALI = ()
GESTORI_GITHUB_AMMESSI = {
    # Organizzazione che pubblica dati, citata come fonte in app/sources.py.
    "openpolis",
}
# Rotte GET senza parametri che richiedono una sessione oppure rifiutano una
# richiesta priva dei parametri obbligatori. Il test verifica sotto che restino
# 4xx: quando una diventa pubblicamente servibile va rimossa da questa mappa.
GET_ENDPOINTS_4XX = {
    "account_export_api": "richiede autenticazione",
    "atlante_modulo": "richiede il parametro tema",
    "comparisons_list_api": "richiede autenticazione",
    "favorites_list_api": "richiede autenticazione",
    "leaderboard_get_api": "richiede il parametro game",
    "game_order_round_api": "richiede una sessione di gioco",
    "player_me_api": "richiede autenticazione",
}
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


def find_personal_identifiers(response, path):
    """Restituisce gli identificativi personali trovati in una risposta testuale."""
    if not (response.mimetype.startswith("text/") or response.mimetype.endswith(("json", "xml"))
            or response.mimetype == "application/linkset+json"):
        return set()

    text = unquote(unescape(response.get_data(as_text=True))).casefold()
    found = set()
    legal_holder = unescape(publisher.identity()["intestatario_legale"]).casefold()
    surname_text = text.replace(legal_holder, "") if path == "/privacy" else text

    if COGNOME_TITOLARE in surname_text:
        found.add("cognome")
    if GESTORE_GITHUB in text:
        found.add("gestore_github")
    if EMAIL_PERSONALE in text:
        found.add("email_personale")
    if "linkedin" + ".com/in/" in text:
        found.add("linkedin")
    for handle in re.findall(r"github\.com/([a-z0-9-]+)", text):
        if handle not in GESTORI_GITHUB_AMMESSI:
            found.add("github_personale")
    for domain in DOMINI_PERSONALI:
        if domain.casefold() in text:
            found.add("dominio_personale")
    return found


def served_paths(client):
    """Costruisce le URL pubbliche da sitemap e regole GET, senza liste a mano.

    Le regole con parametri entrano tramite la prima URL della sitemap che le
    istanzia. Quelle senza rappresentante in sitemap restano fuori: senza un
    valore canonico non esiste una richiesta pubblica deterministica da fare.
    """
    response = client.get("/sitemap.xml")
    if response.status_code != 200:
        raise AssertionError(f"/sitemap.xml risponde {response.status_code}")
    root = ET.fromstring(response.data)
    response.close()
    sitemap_paths = [urlsplit(node.text).path for node in root.findall("{*}url/{*}loc")]
    paths = set(sitemap_paths)

    adapter = app.url_map.bind("divarioitalia.it")
    first_sitemap_path = {}
    for path in sitemap_paths:
        rule, _ = adapter.match(path, method="GET", return_rule=True)
        first_sitemap_path.setdefault((rule.rule, rule.endpoint), path)

    for rule in app.url_map.iter_rules():
        if "GET" not in rule.methods or rule.endpoint == "static":
            continue
        if rule.arguments:
            representative = first_sitemap_path.get((rule.rule, rule.endpoint))
            if representative:
                paths.add(representative)
        elif rule.endpoint not in GET_ENDPOINTS_4XX:
            paths.add(rule.rule)
    return sorted(paths)


class RicercaIdentificativiPersonaliTest(unittest.TestCase):
    def test_la_ricerca_riconosce_ogni_forma_vietata(self):
        casi = (
            ("cognome", "MAI&#101;SE", "cognome"),
            ("gestore GitHub", "GitHub.com/NM" + "AIESE", "gestore_github"),
            ("email personale", EMAIL_PERSONALE.replace("@", "%40"), "email_personale"),
            ("LinkedIn", "LINKEDIN.COM&#47;IN/profilo", "linkedin"),
            ("altro gestore GitHub", "github.com/altro-handle", "github_personale"),
        )
        for nome, corpo, atteso in casi:
            with self.subTest(nome=nome):
                risposta = Response(corpo, content_type="text/plain")
                self.assertIn(atteso, find_personal_identifiers(risposta, "/"))


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
        self.assertTrue(ident["intestatario_legale"], "l'intestatario legale non si lascia vuoto")
        self.assertNotEqual(ident["intestatario_legale"], ident["nome"],
                            "l'intestatario legale e' una persona, non la firma")
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

    def test_intestatario_legale_solo_in_privacy(self):
        """L'intestatario legale firma /privacy e nessun'altra superficie.

        Il titolare del trattamento compare solo nella pagina privacy: non
        firma gli articoli, non sta in /chi-siamo, nei JSON-LD, nel feed,
        nella home/footer, nella sitemap, ne' nel markdown per gli agenti."""
        intestatario = publisher.identity()["intestatario_legale"]
        self.assertTrue(intestatario)

        privacy = self.client.get("/privacy").get_data(as_text=True)
        self.assertIn(intestatario, privacy)
        self.assertIn("che pubblica Divario Italia", privacy)

        for percorso in ("/chi-siamo", "/blog", "/", "/sitemap.xml"):
            with self.subTest(percorso=percorso):
                self.assertNotIn(intestatario, self.client.get(percorso).get_data(as_text=True))

        feed = self.client.get("/blog/feed.xml").get_data(as_text=True)
        self.assertNotIn(intestatario, feed)

        articolo = self.client.get(f"/blog/{self.slug}")
        testo = articolo.get_data(as_text=True)
        self.assertNotIn(intestatario, testo, "l'intestatario non firma l'articolo")
        self.assertNotIn(intestatario, json.dumps(jsonld(articolo), ensure_ascii=False))

        from app import agent_discovery, blog
        post = blog.get_post(self.slug)
        self.assertNotIn(intestatario, agent_discovery.blog_post_markdown(post, "https://x"))
        self.assertNotIn(intestatario, agent_discovery.blog_index_markdown([post], "https://x"))

    def test_gli_identificativi_personali_non_escono_da_nessuna_rotta_pubblica(self):
        paths = served_paths(self.client)
        self.assertGreater(len(paths), 600, f"visitate solo {len(paths)} rotte")

        required = {
            "/legacy", "/legacy-reddito", "/llms.txt", "/llms-full.txt",
            "/robots.txt", "/blog/feed.xml", "/openapi.json",
        }
        required.update(
            rule.rule for rule in app.url_map.iter_rules()
            if rule.rule.startswith("/.well-known/")
        )
        self.assertFalse(required.difference(paths),
                         f"rotte obbligatorie non visitate: {sorted(required.difference(paths))}")

        excluded = {
            rule.endpoint: rule for rule in app.url_map.iter_rules()
            if rule.endpoint in GET_ENDPOINTS_4XX
        }
        self.assertEqual(set(excluded), set(GET_ENDPOINTS_4XX),
                         "una esclusione non corrisponde piu' a una regola GET")
        for endpoint, rule in excluded.items():
            with self.subTest(esclusa=rule.rule, motivo=GET_ENDPOINTS_4XX[endpoint]):
                response = self.client.get(rule.rule)
                try:
                    self.assertGreaterEqual(
                        response.status_code, 400,
                        f"{rule.rule} ora risponde {response.status_code}: rimuovere l'esclusione",
                    )
                finally:
                    response.close()

        leaks = {}
        unreachable = {}
        variants_visited = 0
        for path in paths:
            responses = [(path, self.client.get(path))]
            if agent_discovery.markdown_available(path):
                responses.append((f"{path} [text/markdown]", self.client.get(
                    path, headers={"Accept": "text/markdown"},
                )))
            for label, response in responses:
                variants_visited += 1
                try:
                    if response.status_code >= 400:
                        unreachable[label] = response.status_code
                        continue
                    found = find_personal_identifiers(response, path)
                    if found:
                        leaks[label] = sorted(found)
                finally:
                    response.close()

        summary = f"{len(paths)} rotte e {variants_visited} risposte visitate"
        self.assertEqual(unreachable, {}, f"{summary}; non raggiungibili: {unreachable}")
        self.assertEqual(leaks, {}, f"{summary}; identificativi trovati: {leaks}")

    def test_tipo_non_ammesso_o_nome_vuoto_falliscono(self):
        with tempfile.TemporaryDirectory() as cartella:
            for contenuto in ("tipo: azienda\nnome: X\n", "tipo: persona\nnome: ''\n"):
                percorso = Path(cartella) / "x.yaml"
                percorso.write_text(contenuto, encoding="utf-8")
                with self.subTest(contenuto=contenuto), mock.patch.object(publisher, "IDENTITY_PATH", percorso):
                    with self.assertRaises(ValueError):
                        publisher.identity()

    def test_nessuna_firma_codificata_fuori_dal_file_di_identita(self):
        """Il grep dell'accettazione: firma e intestatario stanno solo nel file."""
        ident = publisher.identity()
        nomi = {ident["nome"], ident["intestatario_legale"]}
        if ident["intestatario_legale"]:
            nomi.add(ident["intestatario_legale"].split()[-1])
        for vecchio in sorted(nomi):
            risultato = subprocess.run(
                ["git", "grep", "-n", "-I", vecchio, "--", "app", "scripts", "tests", "config", "Dockerfile",
                 ":(exclude)config/identita.yaml", ":(exclude)tests/integration/test_identita_editoriale.py",
                 ":(exclude)tests/unit/test_privacy_nome.py"],
                cwd=ROOT, capture_output=True, text=True,
            )
            with self.subTest(vecchio=vecchio):
                self.assertEqual(risultato.stdout.strip(), "", f"{vecchio!r} codificato fuori da config/identita.yaml")

    def test_il_file_di_identita_entra_nell_immagine(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY config/identita.yaml config/identita.yaml", dockerfile)


if __name__ == "__main__":
    unittest.main()
