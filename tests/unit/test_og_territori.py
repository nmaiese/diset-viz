"""Ogni regione e ogni provincia ha la sua immagine da condividere.

Le disegna `scripts/og_territori.py` e si committano: se una provincia entra
nella classifica, o si rinomina una chiave, e nessuno rilancia lo script, la
sua pagina tornerebbe in silenzio alla figura del sito. Le dimensioni si
leggono dall'intestazione del PNG, senza dipendenze: 1200x630 e' la misura
che ogni lettore di anteprime si aspetta.
"""
import struct
import unittest

from app import province_profile
from app.data import REGION_GEO_AREA
from app.design import og

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path) -> tuple[int, int]:
    with open(path, "rb") as handle:
        head = handle.read(24)
    if head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise AssertionError(f"{path} non e' un PNG")
    return struct.unpack(">II", head[16:24])


class LeImmaginiDeiTerritori(unittest.TestCase):
    def assert_has_image(self, level_key, key):
        path = og.DIRECTORY / og.filename(level_key, key)
        self.assertTrue(path.is_file(), f"manca {path.name}: rilanciare scripts/og_territori.py")
        self.assertEqual(png_size(path), (og.WIDTH, og.HEIGHT), path.name)
        self.assertEqual(og.og_image(level_key, key), f"/static/img/og/territori/{path.name}")

    def test_ogni_regione_ha_la_sua_immagine(self):
        self.assertEqual(len(REGION_GEO_AREA), 20)
        for key in REGION_GEO_AREA:
            with self.subTest(regione=key):
                self.assert_has_image("regione", key)

    def test_ogni_provincia_ha_la_sua_immagine(self):
        keys = province_profile.chiavi()
        self.assertEqual(len(keys), 107)
        for key in keys:
            with self.subTest(provincia=key):
                self.assert_has_image("provincia", key)

    def test_una_chiave_che_non_esiste_non_ha_immagine(self):
        self.assertIsNone(og.og_image("provincia", "atlantide"))
        self.assertIsNone(og.og_image("regione", "atlantide"))
        self.assertIsNone(og.og_image("provincia", "../../etc/passwd"))

    def test_un_livello_sconosciuto_e_un_errore(self):
        with self.assertRaises(ValueError):
            og.og_image("comune", "milano")


if __name__ == "__main__":
    unittest.main()
