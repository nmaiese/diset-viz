import unittest
from unittest.mock import patch

from scripts.editoriale import prova_dal_vivo as prova


class ProvaDalVivoTests(unittest.TestCase):
    def test_estrazione_diff_esclude_frontmatter_e_pulisce_markdown(self):
        diff = """--- a/content/posts/2026-01-01-prova.md
+++ b/content/posts/2026-01-01-prova.md
@@ -1,3 +1,4 @@
 ---
 title: Vecchio titolo
+slug: prova
 ---
 Testo vecchio, breve.
+Una frase nuova con [link utile](https://example.com) e **grassetto** contiene molte parole valide.
+Questa riga e' troppo corta.
"""
        frasi = prova.estrai_frasi_nuove(diff)
        self.assertEqual([f.testo for f in frasi], [
            "Una frase nuova con link utile e grassetto contiene molte parole valide."
        ])

    def test_i_punti_elenco_non_entrano_nella_frase_cercata(self):
        diff = """--- a/content/posts/2026-01-01-prova.md
+++ b/content/posts/2026-01-01-prova.md
@@ -1,2 +1,4 @@
 ---
 title: Vecchio titolo
+- Una frase in un elenco puntato che contiene molte parole valide.
+1. Una frase in un elenco numerato che contiene molte parole valide.
"""
        frasi = prova.estrai_frasi_nuove(diff, body_start=1)
        self.assertEqual([f.testo for f in frasi], [
            "Una frase in un elenco puntato che contiene molte parole valide.",
            "Una frase in un elenco numerato che contiene molte parole valide.",
        ])

    def test_campione_deterministico_ordina_per_lunghezza_e_riga(self):
        frasi = [prova.Frase("breve ma abbastanza lunga per entrare nel campione", 8),
                 prova.Frase("questa frase contiene molte piu parole e deve essere scelta", 3),
                 prova.Frase("altra frase sufficientemente lunga per questo test", 9)]
        self.assertEqual(prova.campiona(frasi, 2), [frasi[1], frasi[0]])

    def test_url_post_con_slug_e_fallback_data(self):
        self.assertEqual(prova.url_post("content/posts/2026-01-01-file.md", {"slug": "mio-slug"}), "/blog/mio-slug")
        self.assertEqual(prova.url_post("content/posts/2026-01-01-file.md", {}), "/blog/file")

    def test_frase_trovata_normalizza_apostrofo_ed_entita(self):
        self.assertTrue(prova.frase_trovata("L&#39;Italia è cambiata", "L’Italia è cambiata"))

    def test_frase_mancante_e_pagina_404_danno_esito_uno(self):
        result = prova.verifica_file("content/posts/2026-01-01-file.md", "/blog/file", {},
                                     [prova.Frase("Frase completamente assente dal testo della pagina", 8)],
                                     scarica=lambda url: (404, ""), tentativi=1, pausa=0)
        self.assertEqual(result["esito"], 1)
        self.assertEqual(result["pagina_status"], 404)

    def test_nessun_contenuto_cambiato_esito_zero(self):
        with patch.object(prova, "_contenuti_cambiati", return_value=[]):
            self.assertEqual(prova.esegui("old", "new", scarica=lambda url: None)["esito"], 0)

    def test_secondo_tentativo_trova_frase(self):
        risposte = iter([(200, "ancora vecchio"), (200, "la frase arriva nel secondo tentativo")])
        result = prova.verifica_file("content/posts/file.md", "/blog/file", {},
                                     [prova.Frase("la frase arriva nel secondo tentativo", 10)],
                                     scarica=lambda url: next(risposte), tentativi=2, pausa=0)
        self.assertEqual(result["frasi"][0]["trovata"], True)

    def test_un_paragrafo_si_divide_in_frasi(self):
        diff = (
            "--- a/content/posts/x.md\n+++ b/content/posts/x.md\n@@ -1,0 +10,1 @@\n"
            "+Il peso della redistribuzione è misurato dall'Istat nell'[audizione del maggio 2025](https://x.it/a.pdf). "
            "Nel 2023 la redistribuzione pesa per il 22,0% del reddito disponibile in Calabria e per lo 0,2% in Lombardia. "
            "Breve frase.\n"
        )
        frasi = prova.estrai_frasi_nuove(diff, body_start=1)
        self.assertEqual(len(frasi), 2)
        self.assertTrue(frasi[0].testo.startswith("Il peso della redistribuzione"))
        self.assertIn("audizione del maggio 2025", frasi[0].testo)
        self.assertNotIn("https", frasi[0].testo)
        self.assertTrue(frasi[1].testo.startswith("Nel 2023"))

    def test_un_link_nella_pagina_non_fa_mancare_la_frase(self):
        pagina = ("<p>Il peso della redistribuzione è misurato dall&#39;Istat nell&#39;"
                  "<a href='x'>audizione del maggio 2025</a>. Nel 2023 la redistribuzione pesa.</p>")
        frase = "Il peso della redistribuzione è misurato dall'Istat nell'audizione del maggio 2025."
        self.assertTrue(prova.frase_trovata(pagina, frase))
        self.assertFalse(prova.frase_trovata(pagina, "Questa frase non è nella pagina e ha otto parole."))


if __name__ == "__main__":
    unittest.main()
