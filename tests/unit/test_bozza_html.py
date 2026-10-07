import unittest
from unittest.mock import patch

from scripts.editoriale import bozza_html as b

FALSA = {
    "/static/css/a.css": b"@font-face{src:url(../fonts/f.woff2)} .x{background:url(/static/img/p.png)}",
    "/static/img/foto.jpg": b"\xff\xd8\xff",
    "/static/img/p.png": b"PNG",
    "/static/fonts/f.woff2": b"WOFF",
    "/static/data/articles/x.csv": b"a;b\n1;2\n",
}


def fetch(p):
    return FALSA.get(p)


class BozzaHtmlTests(unittest.TestCase):
    PAGINA = (
        '<html><head><link rel="preload" href="/static/fonts/f.woff2" as="font">'
        '<link rel="canonical" href="https://divarioitalia.it/x">'
        '<link rel="stylesheet" href="/static/css/a.css?v=1"><script src="/static/js/v1.js"></script></head>'
        '<body class="v1"><h1>Un <em>titolo</em></h1><img src="/static/img/foto.jpg" alt="f">'
        '<a href="/regione/molise">Molise</a><a href="/static/data/articles/x.csv">CSV</a>'
        '<a href="https://esterno.it/x">E</a><script>alert(1)</script></body></html>'
    )

    def test_toglie_gli_script_e_i_preload(self):
        out = b.incorpora(self.PAGINA, fetch)
        self.assertNotIn("<script", out)
        self.assertNotIn("preload", out)
        self.assertNotIn("canonical", out)

    def test_incorpora_foglio_e_immagini(self):
        out = b.incorpora(self.PAGINA, fetch)
        self.assertIn("<style>", out)
        self.assertNotIn('rel="stylesheet"', out)
        self.assertIn("src=\"data:image/jpeg;base64,", out)
        self.assertIn("url(data:image/png;base64,", out.replace("'", "").replace('"', ""))

    def test_i_font_piccoli_si_incorporano(self):
        out = b.incorpora(self.PAGINA, fetch)
        self.assertIn("url(data:font/woff2;base64,", out)

    def test_woff2_senza_catalogo_mime_di_sistema(self):
        with patch.object(b.mimetypes, "guess_type", return_value=(None, None)):
            self.assertTrue(b.data_uri(b"WOFF", "/static/fonts/f.woff2").startswith("data:font/woff2;base64,"))

    def test_link_interni_assoluti_ed_esterni_intatti(self):
        out = b.incorpora(self.PAGINA, fetch)
        self.assertIn('href="https://divarioitalia.it/regione/molise"', out)
        self.assertIn('href="https://esterno.it/x"', out)

    def test_il_csv_del_dataset_si_scarica_dalla_bozza(self):
        out = b.incorpora(self.PAGINA, fetch)
        self.assertIn('href="data:text/csv;base64,', out)
        self.assertIn('download="x.csv"', out)

    def test_immagine_grande_resta_un_link_al_sito(self):
        grande = {"/static/img/g.jpg": b"x" * (b.LIMITE_INCORPORA + 1)}
        out = b.incorpora('<body><img src="/static/img/g.jpg"></body>', grande.get)
        self.assertIn('src="https://divarioitalia.it/static/img/g.jpg"', out)

    def test_banner_dopo_il_body_con_il_numero_della_pr(self):
        out = b.metti_banner("<html><body class='x'><p>t</p></body></html>", b.banner("slug", "353", "2026-10-07"))
        self.assertLess(out.index("BOZZA"), out.index("<p>t</p>"))
        self.assertIn("pull/353", out)

    def test_banner_dopo_l_ultimo_body(self):
        pagina = "<html><head>x<noscript><body></noscript></head><body class='ds'><p>t</p></body></html>"
        out = b.metti_banner(pagina, "<b>BOZZA</b>")
        self.assertLess(out.index("<body class='ds'>"), out.index("BOZZA"))
        self.assertGreater(out.index("BOZZA"), out.index("</head>"))

    def test_titolo_dal_primo_h1(self):
        self.assertEqual(b.titolo_pagina(self.PAGINA), "Un titolo")

    def test_registro_tiene_lo_stato_deciso_a_mano(self):
        reg = [{"slug": "a", "titolo": "A", "data": "2026-10-07", "file": "f.html", "stato": "approvato", "pr": 1}]
        nuovo = {"slug": "a", "titolo": "A2", "data": "2026-10-07", "file": "f.html", "stato": "da leggere", "pr": 1}
        self.assertEqual(b.aggiorna_registro(reg, nuovo)[0]["stato"], "approvato")
        nuovo["stato"], nuovo["stato_esplicito"] = "pubblicato", True
        self.assertEqual(b.aggiorna_registro(reg, nuovo)[0]["stato"], "pubblicato")

    def test_indice_con_titolo_data_stato_e_link(self):
        reg = [{"slug": "a", "titolo": "Titolo <A>", "data": "2026-10-07", "file": "20261007-a.html", "stato": "da leggere", "pr": 353}]
        out = b.render_indice(reg)
        self.assertIn("Titolo &lt;A&gt;", out)
        self.assertIn("20261007-a.html", out)
        self.assertIn("pull/353", out)
        self.assertIn("da leggere", out)


if __name__ == "__main__":
    unittest.main()
