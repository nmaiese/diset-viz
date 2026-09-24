"""L'atlante aperto su un tema: il nome del tema, non lo slug, e le parziali.

Il filtro della SPA confronta il nome con `item.theme` del catalogo, e senza
`partial=1` tiene solo le serie complete: la pagina tema conta tutte le serie,
quindi un link senza le parziali mostrerebbe meno di quello che promette. Che
il conto torni pagina per pagina lo guarda
`tests/integration/test_hub_pages.py` (`IRimandiAllAtlanteDiconoIlVero`).
"""
import unittest
from urllib.parse import parse_qs, urlsplit

from app.atlas_catalog import atlas_theme_url


class IlRimandoAlTemaDellAtlante(unittest.TestCase):
    def test_il_nome_del_tema_con_accenti_e_virgole(self):
        link = atlas_theme_url("Reddito, inclusione e accessibilità")
        self.assertTrue(link.startswith("/atlante?"), link)
        self.assertEqual(parse_qs(urlsplit(link).query),
                         {"theme": ["Reddito, inclusione e accessibilità"], "partial": ["1"]})

    def test_senza_tema_resta_l_atlante(self):
        self.assertEqual(atlas_theme_url(None), "/atlante")
        self.assertEqual(atlas_theme_url(""), "/atlante")


if __name__ == "__main__":
    unittest.main()
