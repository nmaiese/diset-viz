import json
import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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

    def test_toglie_lo_script_reale_e_tiene_il_resto_byte_per_byte(self):
        pagina = (
            '<html><head><meta charset="utf-8"></head><body><p>Testo &amp; entità</p>'
            '<!-- commento intatto --><script src="/static/js/v1.js"></script><p>Dopo</p></body></html>'
        )
        atteso = (
            '<html><head><meta charset="utf-8"></head><body><p>Testo &amp; entità</p>'
            '<!-- commento intatto --><p>Dopo</p></body></html>'
        )
        self.assertEqual(b.togli_script(pagina), atteso)

    def test_il_commento_css_con_script_non_mangia_lo_stile(self):
        pagina = (
            "<html><head><style>\n/* ci sono gli <script> qui */\n.x{color:red}\n</style></head>"
            "<body><p>Testo</p><script>alert(1)</script></body></html>"
        )
        out = b.togli_script(pagina)
        self.assertIn("</style>", out)
        self.assertIn("/* ci sono gli <script> qui */", out)
        self.assertIn(".x{color:red}", out)
        self.assertNotIn("alert(1)", out)
        self.assertEqual(out.count("<style"), out.count("</style>"))

    def test_il_css_incorporato_con_script_commentato_resta_intero(self):
        css = {"/static/css/rotta.css": b"/* ci sono gli <script> qui */\nbody{color:#000}"}
        pagina = (
            '<html><head><link rel="stylesheet" href="/static/css/rotta.css"></head>'
            "<body><p>Testo</p></body></html>"
        )
        out = b.incorpora(pagina, css.get)
        self.assertEqual(out.count("<style"), out.count("</style>"))
        self.assertIn("/* ci sono gli <script> qui */", out)
        self.assertIn("body{color:#000}", out)
        self.assertIn("</style></head>", out)

    def test_controlla_rifiuta_lo_style_non_chiuso(self):
        pagina = "<html><head><style>body{color:red}</head><body>" + "parola " * 200 + "</body></html>"
        with self.assertRaises(ValueError) as c:
            b.controlla(pagina)
        self.assertIn("style", str(c.exception))

    def test_controlla_rifiuta_uno_script_residuo(self):
        pagina = (
            "<html><head><style>body{color:red}</style></head><body>"
            + "<p>Una frase abbastanza lunga da superare la soglia del controllo. </p>" * 12
            + "<script>alert(1)</script></body></html>"
        )
        with self.assertRaises(ValueError) as c:
            b.controlla(pagina)
        self.assertIn("script", str(c.exception))

    def test_controlla_rifiuta_uno_script_aperto_e_non_chiuso(self):
        pagina = (
            "<html><head><style>body{color:red}</style></head><body>"
            + "<p>Una frase abbastanza lunga da superare la soglia del controllo. </p>" * 12
            + "<script>alert(1)</body></html>"
        )
        with self.assertRaises(ValueError) as c:
            b.controlla(pagina)
        self.assertIn("script", str(c.exception))

    def test_controlla_non_confonde_script_in_commento_o_attributo(self):
        pagina = (
            "<html><head><style>/* <script> finto */ body{color:red}</style></head><body>"
            + "<p>Una frase abbastanza lunga da superare la soglia del controllo. </p>" * 12
            + '<p title="<script>">testo</p></body></html>'
        )
        self.assertIsNone(b.controlla(pagina))

    def test_controlla_non_conta_lo_style_in_commento_come_apertura(self):
        pagina = (
            "<html><head><style>/* <style> finto */ body{color:red}</style></head><body>"
            + "<p>Una frase abbastanza lunga da superare la soglia del controllo. </p>" * 12
            + "</body></html>"
        )
        self.assertIsNone(b.controlla(pagina))

    def test_controlla_rifiuta_un_body_senza_testo_visibile(self):
        pagina = "<html><head><style>body{color:red}</style></head><body><p>Ciao</p></body></html>"
        with self.assertRaises(ValueError) as c:
            b.controlla(pagina)
        self.assertIn("testo visibile", str(c.exception))

    def test_controlla_accetta_una_pagina_normale(self):
        pagina = (
            "<html><head><style>body{color:red}</style></head><body>"
            + "<p>Una frase abbastanza lunga da superare la soglia del controllo. </p>" * 12
            + "</body></html>"
        )
        self.assertIsNone(b.controlla(pagina))

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


def pagina_valida() -> str:
    return (
        "<html><head><style>body{color:#111}</style></head><body>"
        "<h1>Titolo bozza</h1>"
        + "<p>Frase di testo visibile abbastanza lunga per il controllo. </p>" * 40
        + "</body></html>"
    )


class RispostaFinta:
    def __init__(self, testo: str, status: int = 200):
        self.status_code = status
        self._testo = testo

    def get_data(self, as_text: bool = False):
        return self._testo if as_text else self._testo.encode("utf-8")


class ClientFinto:
    def __init__(self, risposte: dict):
        self.risposte = risposte

    def get(self, percorso: str) -> RispostaFinta:
        return self.risposte.get(percorso, RispostaFinta("", 404))


class AppFinta:
    def __init__(self, risposte: dict):
        self._client = ClientFinto(risposte)

    def test_client(self) -> ClientFinto:
        return self._client


def modulo_run(risposte: dict) -> types.ModuleType:
    modulo = types.ModuleType("run")
    modulo.app = AppFinta(risposte)
    return modulo


class MainTests(unittest.TestCase):
    """main() con un'app finta: nessun servizio reale, nessuna rete."""

    def setUp(self):
        self._cwd = os.getcwd()
        self._path = list(sys.path)
        cartella = TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        self.radice = Path(cartella.name) / "worktree"
        (self.radice / "content" / "posts").mkdir(parents=True)
        self.out = Path(cartella.name) / "bozze"
        self.addCleanup(os.chdir, self._cwd)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self._path))

    def _esegui(self, argv: list, risposte: dict) -> int:
        with patch.dict(sys.modules, {"run": modulo_run(risposte)}):
            return b.main([*argv, "--radice", str(self.radice), "--out", str(self.out)])

    def _registro(self) -> list:
        return json.loads((self.out / "indice.json").read_text(encoding="utf-8"))

    def test_main_rifiuta_slug_e_pagina_insieme_o_nessuno(self):
        with self.assertRaises(SystemExit):
            b.main([])
        with self.assertRaises(SystemExit):
            b.main(["x", "--pagina", "/blog/x"])

    def test_main_nome_vuoto_o_traversal_rifiutato(self):
        for brutto in ("", "  ", "a/b", "../x", "a..b"):
            with self.assertRaises(SystemExit):
                b.main(["--pagina", "/indicatore/foo/ter-105", "--nome", brutto])

    def test_main_pagina_e_nome_scrive_il_nome_scelto(self):
        risposte = {"/indicatore/foo/ter-105": RispostaFinta(pagina_valida())}
        esito = self._esegui(["--pagina", "/indicatore/foo/ter-105", "--nome", "mia-scheda"], risposte)
        self.assertEqual(esito, 0)
        reg = self._registro()
        self.assertEqual(reg[0]["slug"], "mia-scheda")
        self.assertTrue((self.out / reg[0]["file"]).exists())

    def test_main_risposta_non_200_non_scrive(self):
        esito = self._esegui(["--pagina", "/indicatore/foo/ter-105", "--nome", "scheda"], {})
        self.assertEqual(esito, 1)
        self.assertFalse((self.out / "indice.json").exists())
        self.assertFalse(list(self.out.glob("*.html")))

    def test_main_bozza_scartata_non_scrive(self):
        breve = "<html><head><style>body{color:red}</style></head><body><p>Ciao</p></body></html>"
        risposte = {"/indicatore/foo/ter-105": RispostaFinta(breve)}
        esito = self._esegui(["--pagina", "/indicatore/foo/ter-105", "--nome", "scheda"], risposte)
        self.assertEqual(esito, 1)
        self.assertFalse((self.out / "indice.json").exists())

    def test_main_pagina_blog_recupera_la_data_del_post(self):
        (self.radice / "content" / "posts" / "2026-10-08-mio-post.md").write_text("---\n---\n", encoding="utf-8")
        risposte = {"/blog/mio-post": RispostaFinta(pagina_valida())}
        esito = self._esegui(["--pagina", "/blog/mio-post"], risposte)
        self.assertEqual(esito, 0)
        reg = self._registro()
        self.assertEqual(reg[0]["data"], "2026-10-08")
        self.assertEqual(reg[0]["slug"], "blog-mio-post")
        self.assertTrue(reg[0]["file"].startswith("20261008-"))


class NomiTests(unittest.TestCase):
    def test_nome_da_percorso_toglie_query_e_fragment(self):
        self.assertEqual(b.nome_da_percorso("/indicatore/foo/ter-105?x=1#f"), "indicatore-foo-ter-105")
        self.assertEqual(b.nome_da_percorso("/"), "")

    def test_data_dal_file_escapa_il_glob(self):
        with TemporaryDirectory() as cartella:
            radice = Path(cartella)
            (radice / "content" / "posts").mkdir(parents=True)
            (radice / "content" / "posts" / "2026-10-08-a[b].md").write_text("x", encoding="utf-8")
            self.assertEqual(b.data_dal_file(radice, "a[b]"), "20261008")


if __name__ == "__main__":
    unittest.main()
