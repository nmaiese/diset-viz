"""Ogni SVG informativo ha un nome, quelli decorativi sono nascosti."""

import re
import unittest

from app import app
from app.blog import get_posts


SVG = re.compile(r"<svg\b([^>]*)>(.*?)</svg\s*>", re.IGNORECASE | re.DOTALL)


def svg_state(html):
    return [
        {
            "attrs": attrs,
            "named": bool(re.search(r"\baria-label\s*=|\baria-labelledby\s*=|<title\b", attrs + body, re.I)),
            "hidden": bool(re.search(r'\baria-hidden\s*=\s*[\"\']true[\"\']', attrs, re.I)),
        }
        for attrs, body in SVG.findall(html)
    ]


class SvgAccessibilita(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        blog_path = "/blog/" + get_posts()[0]["slug"]
        cls.pages = {
            path: svg_state(client.get(path).get_data(as_text=True))
            for path in ("/atlante", "/regione/lombardia", "/provincia/napoli", "/confronto", blog_path)
        }

    def test_ogni_svg_informativo_e_nominato_o_dichiarato_decorativo(self):
        for path, svgs in self.pages.items():
            with self.subTest(path=path):
                self.assertTrue(svgs)
                self.assertTrue(all(svg["named"] or svg["hidden"] for svg in svgs))

    def test_le_mappe_di_qualita_della_vita_hanno_un_nome_accessibile(self):
        for path in ("/regione/lombardia", "/provincia/napoli"):
            with self.subTest(path=path):
                html = app.test_client().get(path).get_data(as_text=True)
                match = re.search(r'<div class="navmap navmap--data navmap--zoom"[^>]*>(.*?)</div>', html, re.S)
                self.assertIsNotNone(match)
                maps = svg_state(match.group(1))
                self.assertEqual(len(maps), 1)
                self.assertTrue(maps[0]["named"] and not maps[0]["hidden"])
