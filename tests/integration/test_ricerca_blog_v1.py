"""La ricerca e l'indice delle storie nella 1.0.

Che cosa si rompe senza che niente fallisca:
- la ricerca torna a dare 1 a tutto cio' che contiene la query solo nel tema,
  e per "lavoro" il tasso di disoccupazione finisce al 50° posto;
- il filtro `?tipo=` smette di filtrare, o i suoi link perdono la query;
- l'evidenziazione del termine inietta markup (la query arriva dall'URL);
- le due pagine escono dal ripiego invece che dal template della 1.0.
"""
import re
import unittest

from app import app
from app.design.pages.blog import tag_slug
from app.design.pages.ricerca import highlight, pager

RESULT_LINK = re.compile(r'<a class="search-result__title" href="([^"]+)">(.*?)</a>', re.S)


class LaRicerca(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _html(self, **query):
        response = self.client.get("/ricerca", query_string=query)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_e_la_pagina_della_v1(self):
        for query in ({}, {"q": "lavoro"}, {"q": "zzzznessunrisultato"}, {"q": "tasso", "tipo": "indicatori", "pagina": "2"}):
            with self.subTest(query=query):
                html = self._html(**query)
                self.assertIn('data-v1="ricerca"', html)
                self.assertEqual(html.count("<h1"), 1)
                self.assertIn('<meta name="robots" content="noindex, follow">', html)

    def test_per_lavoro_i_tassi_del_lavoro_stanno_nella_prima_pagina(self):
        html = self._html(q="lavoro")
        titles = [re.sub(r"<[^>]+>", "", t) for _, t in RESULT_LINK.findall(html)]
        self.assertIn("Tasso di disoccupazione", titles)
        self.assertIn("Tasso di occupazione (totale)", titles)
        # E il tema "Lavoro e conciliazione" e' un risultato, sopra le schede.
        self.assertIn('href="/tema/lavoro-e-conciliazione"', html)

    def test_i_sinonimi_allargano_la_raccolta(self):
        html = self._html(q="reddito", tipo="indicatori")
        titles = [re.sub(r"<[^>]+>", "", t) for _, t in RESULT_LINK.findall(html)]
        self.assertIn("PIL pro capite", titles)

    def test_il_filtro_per_tipo(self):
        html = self._html(q="lavoro", tipo="articoli")
        links = [href for href, _ in RESULT_LINK.findall(html)]
        self.assertTrue(links)
        self.assertTrue(all(href.startswith("/blog/") for href in links), links)
        self.assertNotIn('data-kind="indicatore"', html)
        # Il controllo segmentato: link veri che tengono la query, la voce
        # corrente marcata.
        self.assertIn('<a href="/ricerca?q=lavoro&amp;tipo=articoli" aria-current="page">', html)
        self.assertIn('href="/ricerca?q=lavoro&amp;tipo=indicatori"', html)
        self.assertIn('href="/ricerca?q=lavoro"', html)
        # Un tipo che non esiste vale tutti.
        every = self._html(q="lavoro", tipo="nonesiste")
        self.assertIn('<a href="/ricerca?q=lavoro" aria-current="page">', every)

    def test_la_paginazione_numerata_tiene_il_tipo(self):
        html = self._html(q="tasso", tipo="indicatori")
        self.assertIn('href="/ricerca?q=tasso&amp;tipo=indicatori&amp;pagina=2"', html)
        self.assertIn('aria-current="page"><span class="sr-only">Pagina </span>1</a>', html)
        second = self._html(q="tasso", tipo="indicatori", pagina="2")
        self.assertIn('rel="prev"', second)
        self.assertIn("Pagina 2 di", second)

    def test_il_termine_e_evidenziato_senza_iniettare_markup(self):
        html = self._html(q="lavoro")
        self.assertIn("<mark>Lavoro</mark> e conciliazione", html)
        hostile = self._html(q='<script>alert(1)</script>')
        self.assertNotIn("<script>alert(1)</script>", hostile)

    def test_highlight_escapa_prima_di_marcare(self):
        self.assertEqual(str(highlight("<b>Città</b>", ["citta"])), "&lt;b&gt;<mark>Città</mark>&lt;/b&gt;")
        self.assertEqual(str(highlight("a & b", ["amp"])), "a &amp; b")
        # I sinonimi valgono solo come inizio di parola.
        self.assertEqual(str(highlight("Tasso di disoccupazione", ["lavoro", "occupazione"])),
                         "Tasso di disoccupazione")
        self.assertEqual(str(highlight("Tasso di occupazione", ["lavoro", "occupazione"])),
                         "Tasso di <mark>occupazione</mark>")

    def test_pager_salta_le_pagine_lontane(self):
        numbers = [it.get("n") for it in pager("x", "", 5, 12)["items"]]
        self.assertEqual(numbers, [1, None, 3, 4, 5, 6, 7, None, 12])
        self.assertIsNone(pager("x", "", 1, 1))


class LeStorie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.html = cls.client.get("/blog").get_data(as_text=True)

    def test_e_la_pagina_della_v1(self):
        self.assertIn('data-v1="blog"', self.html)
        self.assertEqual(self.html.count("<h1"), 1)
        self.assertIn('"@type": "Blog"', self.html)

    def test_ogni_storia_ha_il_suo_link_una_volta_come_scheda(self):
        from app.blog import get_posts

        posts = get_posts()
        main = self.html[self.html.index("<main"):self.html.index("</main>")]
        self.assertIn(f'class="story__title"><a href="/blog/{posts[0]["slug"]}"', main)
        cards = re.findall(r'<h3 class="card__title"><a href="(/blog/[^"]+)"', main)
        self.assertEqual(cards, [f"/blog/{p['slug']}" for p in posts[1:]])

    def test_i_filtri_per_tema_portano_a_una_sezione_che_esiste(self):
        anchors = re.findall(r'<nav class="blog-tags".*?</nav>', self.html, re.S)[0]
        for target in re.findall(r'href="#([^"]+)"', anchors):
            self.assertIn(f'id="{target}"', self.html)
        self.assertEqual(tag_slug("Divario Nord-Sud"), "tema-divario-nord-sud")

    def test_le_copertine_disegnate_sono_della_1_0(self):
        from pathlib import Path

        for svg in (Path(app.root_path) / "static" / "img" / "blog").glob("*.svg"):
            with self.subTest(svg=svg.name):
                text = svg.read_text(encoding="utf-8")
                self.assertIn('viewBox="0 0 1200 630"', text)
                self.assertNotIn("#e4572e", text)
                self.assertNotIn("Space Mono", text)
                self.assertIsNone(re.search(r">[^<]*[A-Z]{5,}[^<]*<", text.replace("NEET", "")), "testo tutto maiuscolo")


if __name__ == "__main__":
    unittest.main()
