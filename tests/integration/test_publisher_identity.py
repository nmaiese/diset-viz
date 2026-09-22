import json
import re
import unittest
from pathlib import Path

from app import app, publisher


def jsonld(response):
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        response.get_data(as_text=True),
        re.S,
    )
    return [json.loads(block) for block in blocks]


class PublisherIdentityTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_about_page_is_visible_linked_and_listed(self):
        page = self.client.get("/chi-siamo")
        self.assertEqual(page.status_code, 200)
        text = page.get_data(as_text=True)
        for claim in ("Responsabilità editoriale", "Come verifichiamo", "Correzioni e contatto", "Come citare"):
            self.assertIn(claim, text)
        self.assertIn(publisher.CORRECTIONS_URL, text)
        self.assertIn('/chi-siamo', self.client.get('/').get_data(as_text=True))
        self.assertIn('<loc>https://divarioitalia.it/chi-siamo</loc>', self.client.get('/sitemap.xml').get_data(as_text=True))

    def test_one_reusable_organization_matches_visible_identity(self):
        about = jsonld(self.client.get("/chi-siamo"))[0]["@graph"]
        organization = next(node for node in about if node.get("@type") == "Organization")
        self.assertEqual(organization, publisher.ORGANIZATION)
        self.assertNotIn("sameAs", organization)
        self.assertIn(organization["name"], self.client.get("/chi-siamo").get_data(as_text=True))

        home_graph = jsonld(self.client.get("/"))[0]["@graph"]
        self.assertEqual(home_graph[1], organization)
        self.assertEqual(home_graph[0]["publisher"]["@id"], organization["@id"])

    def test_article_and_dataset_dates_and_corrections_match_visible_copy(self):
        article = self.client.get("/blog").get_data(as_text=True)
        match = re.search(r'href="/blog/([^"?]+)"', article)
        self.assertIsNotNone(match)
        response = self.client.get(f"/blog/{match.group(1)}")
        document = next(item for item in jsonld(response) if item.get("@type") == "Article")
        visible = response.get_data(as_text=True)
        self.assertIn(document["dateModified"].split("-")[0], visible)
        self.assertEqual(document["publisher"], publisher.ORGANIZATION)
        self.assertIn(publisher.CORRECTIONS_URL, visible)

        from app.data import get_catalog
        from app.profiles import indicator_path
        sample = get_catalog()["indicators"][0]
        response = self.client.get(indicator_path(sample["id"], sample["name"]))
        dataset = next(item for item in jsonld(response) if item.get("@type") == "Dataset")
        visible = response.get_data(as_text=True)
        self.assertIn(dataset["dateModified"], visible)
        self.assertEqual(dataset["publisher"], publisher.ORGANIZATION)
        self.assertIn(publisher.CORRECTIONS_URL, visible)


class IlContattoEsisteDavvero(unittest.TestCase):
    """Fino al 22 settembre 2026 il sito non aveva un indirizzo.

    L'unico contatto era un issue tracker, e /chi-siamo lo presentava come "il
    contatto operativo del progetto". Per chi legge non e' un contatto, e per
    chi verifica un sito dall'esterno non lo e' affatto: apre /contatti, non
    trova la pagina, e si ferma li'.
    """

    def setUp(self):
        self.client = app.test_client()

    def test_la_pagina_esiste_e_mostra_l_indirizzo_in_chiaro(self):
        risposta = self.client.get("/contatti")
        self.assertEqual(risposta.status_code, 200)
        testo = risposta.get_data(as_text=True)
        self.assertIn(publisher.CONTACT_EMAIL, testo)
        self.assertIn(f"mailto:{publisher.CONTACT_EMAIL}", testo,
                      "l'indirizzo va in un mailto in chiaro, non composto da JavaScript")

    def test_ogni_indirizzo_e_al_riparo_dall_offuscamento_di_cloudflare(self):
        """In locale era perfetto, in produzione era un blob.

        Cloudflare ha Email Address Obfuscation acceso e riscrive ogni
        `mailto:` in `/cdn-cgi/l/email-protection#<hex>`, con il testo da
        decifrare in JavaScript. La pagina prometteva un contatto e non ne
        dava uno a chi legge senza JavaScript, che e' anche chi verifica il
        sito dall'esterno. `<!--email_off-->` e' la direttiva con cui
        Cloudflare spegne l'offuscamento su un blocco solo.

        La prova guarda i template e non una pagina resa, perche' qui non si
        puo' riprodurre: l'offuscamento lo fa Cloudflare, non l'applicazione.
        Quello che si puo' tenere e' che nessun `mailto:` esca da quel riparo.
        """
        radice = Path(__file__).resolve().parents[2] / "app" / "templates"
        trovati = 0
        for template in sorted(radice.rglob("*.html")):
            sorgente = template.read_text(encoding="utf-8")
            for riga in sorgente.splitlines():
                if "mailto:" not in riga:
                    continue
                trovati += 1
                with self.subTest(template=template.name, riga=riga.strip()[:60]):
                    self.assertIn("<!--email_off-->", riga)
                    self.assertIn("<!--email_on-->", riga)
        self.assertGreater(trovati, 0, "nessun mailto nei template: la prova non guarda piu' niente")

    def test_il_dato_strutturato_non_promette_un_recapito_che_la_pagina_non_da(self):
        """Un `contactPoint` che nomina un indirizzo assente dalla pagina
        visibile e' la stessa incoerenza fra JSON-LD e testo che il percorso
        aveva gia' pagato una volta."""
        contatto = publisher.ORGANIZATION["contactPoint"]
        self.assertEqual(contatto["email"], publisher.CONTACT_EMAIL)
        self.assertEqual(contatto["url"], "https://divarioitalia.it/contatti")
        self.assertIn(contatto["email"], self.client.get("/contatti").get_data(as_text=True))

    def test_sta_in_sitemap_e_nel_piede_di_ogni_guscio(self):
        self.assertIn("<loc>https://divarioitalia.it/contatti</loc>",
                      self.client.get("/sitemap.xml").get_data(as_text=True))
        for percorso in ("/", "/atlante", "/confronto"):
            with self.subTest(percorso=percorso):
                html = self.client.get(percorso).get_data(as_text=True)
                piede = re.search(r"<footer[^>]*>.*</footer>", html, re.S)
                self.assertIsNotNone(piede, percorso)
                for atteso in ("/contatti", "/chi-siamo", "/privacy"):
                    self.assertIn(f'href="{atteso}"', piede.group(0),
                                  f"{percorso}: il piede visibile non porta a {atteso}")


class NessunLinkInternoPortaAUn404(unittest.TestCase):
    """Il paragrafo "Chi ne risponde" della metodologia linkava `/about`.

    Rotta che non esiste: chi andava a cercare chi risponde del sito trovava
    una pagina non trovata, e nessuna prova lo vedeva. `nav.paths()` copre solo
    le voci di menu, e quel link non era una voce di menu.
    """

    def test_ogni_href_interno_scritto_a_mano_nei_template_risponde(self):
        client = app.test_client()
        radice = Path(__file__).resolve().parents[2] / "app" / "templates"
        visti = {}
        for template in sorted(radice.rglob("*.html")):
            for href in re.findall(r'href="(/[^"\s]*)"', template.read_text(encoding="utf-8")):
                # Solo i percorsi letterali: quelli con Jinja dentro li decide
                # il render, e li coprono le prove delle pagine che li usano.
                if "{" in href or href.startswith("//"):
                    continue
                visti.setdefault(href.split("#")[0].split("?")[0], template.name)
        for percorso, dove in sorted(visti.items()):
            with self.subTest(percorso=percorso, template=dove):
                self.assertNotEqual(client.get(percorso).status_code, 404,
                                    f"{dove} manda a {percorso}, che non esiste")


if __name__ == "__main__":
    unittest.main()
