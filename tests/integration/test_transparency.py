"""La dichiarazione di generazione automatica, e la pagina che la sostiene.

Articolo 50(4) del regolamento europeo sull'intelligenza artificiale, in vigore
dal **2 agosto 2026**. Chi pubblica un testo "with the purpose of informing the
public on matters of public interest" deve dichiarare che e' generato, e
l'esenzione e' **cumulativa**: revisione o controllo editoriale umano **e** una
persona fisica o giuridica che detenga la responsabilita' editoriale. Una
catena a zero tempo umano per articolo non puo' invocarla.

Il comma 5 chiede la dichiarazione "in a clear and distinguishable manner at
the latest at the time of the first ... exposure": in pagina, quindi, non in
una policy che nessuno apre.

Sta nel template, quindi copre anche i cinquantadue articoli congelati senza
toccarne una riga di prosa. Il congelamento riguardava il testo, non il guscio.
"""
import glob
import json
import os
import unittest

from app import app

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TheDisclosureIsOnThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _page(self, code):
        response = self.client.get(f"/indicatore/x/{code}", follow_redirects=True)
        self.assertEqual(response.status_code, 200, code)
        return response.get_data(as_text=True)

    def test_an_article_written_by_the_chain_declares_it(self):
        page = self._page("ter-176")
        self.assertIn("scritto automaticamente", page)
        self.assertIn("senza riscrittura umana", page)

    def test_the_declaration_links_to_the_page_that_explains_it(self):
        self.assertIn("/metodologia#come-nasce-il-testo", self._page("ter-176"))

    def test_a_page_whose_text_is_composed_by_code_does_not_claim_to_be_generated(self):
        """Le sezioni composte sono template deterministici sui dati della fonte.

        Dichiararle generate sarebbe impreciso in eccesso, e su una pagina di
        dati pubblici l'imprecisione in eccesso costa fiducia quanto quella in
        difetto.

        L'indicatore si sceglie a run-time fra quelli senza articolo firmato:
        fissarne uno a mano vorrebbe dire che il test fallisce il giorno in cui
        la catena lo scrive, cioe' per il motivo giusto ma col messaggio
        sbagliato.
        """
        from scripts import indicator_store
        scritti = set(indicator_store.load_all())
        for raw in ("120", "30", "45", "60", "72", "88", "140"):
            if raw in scritti:
                continue
            response = self.client.get(f"/indicatore/x/ter-{raw}", follow_redirects=True)
            if response.status_code != 200:
                continue
            self.assertNotIn("scritto automaticamente", response.get_data(as_text=True))
            return
        self.skipTest("nessun indicatore senza articolo firmato fra quelli provati")

    def test_it_says_the_figures_are_recomputed_not_frozen(self):
        self.assertIn("ricalcolati dalla fonte", self._page("ter-176"))


class TheMethodPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = app.test_client().get("/metodologia").get_data(as_text=True)

    def test_the_anchor_the_articles_point_at_exists(self):
        self.assertIn('id="come-nasce-il-testo"', self.page)

    def test_it_separates_what_is_generated_from_what_is_not(self):
        self.assertIn("I dati non sono generati", self.page)

    def test_it_says_what_is_verified(self):
        self.assertIn("riverificata contro il valore vero", self.page)

    def test_it_says_what_the_verification_does_not_catch(self):
        """Una pagina di metodo che elenca solo le garanzie e' marketing."""
        self.assertIn("non garantisce", self.page)
        self.assertIn("Non c'è una rilettura umana", self.page)

    def test_it_names_a_responsibility_and_refuses_invented_bylines(self):
        """Un nome finto non e' una persona che detiene responsabilita'
        editoriale: la simula. E le linee guida di Google danno il rating
        minimo a una pagina che attribuisce il contenuto a una fonte fittizia
        "even if the page assigns credit for the content to another source".
        """
        self.assertIn("responsabilità editoriale", self.page)
        self.assertIn("non firmiamo le schede con nomi di redattori che non esistono",
                      self.page.lower())


class TheFrozenFiftyTwoAreCoveredWithoutBeingTouched(unittest.TestCase):
    def test_the_declaration_comes_from_the_template_not_from_the_json(self):
        """Se fosse nel JSON, coprirla vorrebbe dire riscrivere 52 articoli."""
        with open(os.path.join(ROOT, "app", "templates", "_indicator_article.html"),
                  encoding="utf-8") as handle:
            template = handle.read()
        self.assertIn("scritto automaticamente", template)
        self.assertIn("macro dichiarazione", template)

    def test_no_committed_article_carries_the_sentence_in_its_prose(self):
        for path in glob.glob(os.path.join(ROOT, "content", "indicators", "*.json")):
            with open(path, encoding="utf-8") as handle:
                blob = json.dumps(json.load(handle), ensure_ascii=False)
            self.assertNotIn("scritto automaticamente", blob,
                             f"{path} ha la dichiarazione nella prosa invece che nel guscio")


if __name__ == "__main__":
    unittest.main()
