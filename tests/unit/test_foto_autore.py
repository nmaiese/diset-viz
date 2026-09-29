"""Il campo `Artist` di Commons, ridotto al nome che va nell'attribuzione.

Il campo porta il nome e poi tutto il resto che l'autore ha scritto: una
richiesta di cortesia, un indirizzo email, la formula con cui vuole essere
citato. Copiato cosi' com'e' finiva dentro `cover_credit` e quindi dentro la
pagina, e ogni volta si correggeva a mano. Due valori reali, presi dalla
scheda delle foto del 23 settembre 2026:

    Ivan Ruggiero
    I'd appreciate if you could mail me (ivanrugg+credit@gmail.com) if you want
    to use this picture out of the Wikimedia project scope. Please attribute as:
    Ivan Ruggiero (Wikimedia)

    https://www.flickr.com/photos/geographyalltheway_photos/
"""

import unittest

from scripts.trend_articles import photo


class CleanAuthor(unittest.TestCase):
    def test_il_caso_reale_del_nome_seguito_dalla_nota(self):
        valore = ("Ivan Ruggiero\n"
                  "I'd appreciate if you could mail me (ivanrugg+credit@gmail.com) if you want to use "
                  "this picture out of the Wikimedia project scope. Please attribute as: "
                  "Ivan Ruggiero (Wikimedia)")
        self.assertEqual(photo.clean_author(valore), "Ivan Ruggiero")

    def test_il_caso_reale_del_profilo_flickr(self):
        self.assertEqual(
            photo.clean_author("https://www.flickr.com/photos/geographyalltheway_photos/"),
            "geographyalltheway_photos (Flickr)",
        )

    def test_nota_e_indirizzo_sulla_stessa_riga(self):
        self.assertEqual(
            photo.clean_author("Maria Verdi (maria.verdi@esempio.it). Please attribute as: Maria Verdi"),
            "Maria Verdi",
        )

    def test_html_residuo_tolto_e_nome_preservato(self):
        self.assertEqual(
            photo.clean_author('<a href="https://commons.wikimedia.org/wiki/User:GinevraBianchi" '
                               'title="User:GinevraBianchi">GinevraBianchi</a>'),
            "GinevraBianchi",
        )

    def test_profilo_flickr_senza_barra_finale_e_url_di_una_istituzione(self):
        self.assertEqual(photo.clean_author("https://www.flickr.com/photos/paolo_bianchi_photos"),
                         "paolo_bianchi_photos (Flickr)")
        self.assertEqual(photo.clean_author("https://www.si.edu/"), "si.edu")

    def test_un_nome_gia_pulito_non_si_tocca(self):
        # I due valori delle schede del 23 settembre, e un nome normale.
        for valore, atteso in (("Herzi Pinki", "Herzi Pinki"), ("m/m", "m/m"),
                               ("rawpixel.com", "rawpixel.com"), ("GinevraBianchi", "GinevraBianchi")):
            with self.subTest(valore=valore):
                self.assertEqual(photo.clean_author(valore), atteso)

    def test_un_valore_vuoto_non_diventa_inventato(self):
        for valore in ("", "   \n  ", None):
            with self.subTest(valore=valore):
                self.assertEqual(photo.clean_author(valore), "")


class AuthorNellaScheda(unittest.TestCase):
    """Non basta che la funzione esista: `author` deve passargli dentro."""

    def test_la_scheda_registra_il_nome_pulito(self):
        page = {
            "title": "File:SS131DCN-7602.jpg",
            "imageinfo": [{
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:SS131DCN-7602.jpg",
                "url": "https://upload.wikimedia.org/x.jpg",
                "mime": "image/jpeg", "width": 2000, "height": 1500,
                "extmetadata": {
                    "Artist": {"value": "<a href='https://www.flickr.com/photos/il_fotografo/'>"
                                         "Marco\nI'd appreciate if you could mail me (m@esempio.it)</a>"},
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                },
            }],
        }
        record = photo._record(page)
        self.assertEqual(record["author"], "Marco")
        self.assertEqual(record["license"], "CC BY-SA 4.0")

    def test_senza_autore_resta_la_dicitura_di_promemoria(self):
        page = {"title": "File:X.jpg", "imageinfo": [{"extmetadata": {}}]}
        self.assertEqual(photo._record(page)["author"], "autore non indicato")


if __name__ == "__main__":
    unittest.main()
