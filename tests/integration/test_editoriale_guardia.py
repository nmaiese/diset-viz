"""La guardia deterministica sulla prosa: verde sul catalogo, rossa su una bozza costruita apposta.

`tests/integration/test_indicator_texts.py` verificava i testi scritti a mano
finche' non e' stato tolto nel commit `eb2c2f72`. Questo file lo rimpiazza per
`scripts/editoriale/guardia.py`: prima la prova che il vincolo decisivo tenga
("verde su tutti gli articoli committati"), poi i cinque controlli uno per uno
su bozze minime, dove ogni difetto e' costruito e non trovato per caso.

Nessun articolo del catalogo porta un dossier (`lavoro/` non e' nel repo), e
`AllCommittedArticles` lo rispecchia: gira senza `--dossier`, come nella pratica
di oggi, quindi esercita solo i controlli 2-5. Il controllo 1 (le cifre contro
il dossier) lo esercita `Figures`, con un dossier minimo scritto qui.
"""

import subprocess
import sys
import unittest
from pathlib import Path

from scripts import indicator_store
from scripts.editoriale import brief, guardia

ROOT = Path(__file__).resolve().parent.parent.parent


def entry(sections, lead="", level="regione"):
    return {"level": level, "lead": lead, "sections": sections}


class AllCommittedArticles(unittest.TestCase):
    """Il catalogo non contiene rilievi bloccanti; gli avvisi restano visibili."""

    def test_nessun_difetto_senza_dossier(self):
        articles = indicator_store.load_all()
        self.assertGreater(len(articles), 0, "il catalogo committato non dovrebbe essere vuoto")
        for key, article in articles.items():
            with self.subTest(key=key):
                defects = guardia.check_article(key, article)
                blocking = guardia.blocking_defects(defects)
                self.assertEqual(blocking, [], "\n".join(d.line() for d in blocking))

    def test_avvisi_catalogo_restano_nel_rapporto(self):
        articles = indicator_store.load_all()
        findings = [(key, defect) for key, article in articles.items()
                    for defect in guardia.check_article(key, article)
                    if not defect.blocking]
        self.assertGreater(len(findings), 0)
        self.assertTrue(all(defect.check.endswith("-avviso") or
                            defect.check.endswith("-non verificabile")
                            for _, defect in findings))

    def test_ter_901_e_ter_12_come_sono_oggi(self):
        for code in ("ter-901", "ter-12"):
            with self.subTest(code=code):
                family, raw_id = brief.resolve(code)
                key = key_for(family, raw_id)
                article = indicator_store.read(key)
                self.assertIsNotNone(article, f"{code} non ha un articolo scritto")
                self.assertEqual(guardia.blocking_defects(guardia.check_article(key, article)), [])


def key_for(family, raw_id):
    from app import sources
    return sources.internal_id(family, raw_id)


class Typography(unittest.TestCase):
    def test_gli_assoluti_tipografici_sono_bloccanti(self):
        for char in ("—", "–", ";", "…"):
            with self.subTest(char=char):
                article = entry([{"role": "quadro", "h": "Titolo", "body": f"Una frase con {char} dentro."}])
                defects = guardia.check_article("9999999", article)
                self.assertTrue(any(d.check == "tipografia" for d in defects))

    def test_prosa_pulita_non_solleva_niente(self):
        article = entry([{"role": "quadro", "h": "Titolo", "body": "Una frase pulita, senza niente di vietato."}])
        self.assertEqual(guardia.check_article("9999999", article), [])


class FindingSeverity(unittest.TestCase):
    def test_g4_titolo_figura_o_tabella_resta_bloccante(self):
        for title in ("Figura 3 regioni", "Tabella 4 province"):
            with self.subTest(title=title):
                self.assertTrue(guardia.Defect("G4", "figure", title, "numero nudo").blocking)

    def test_g4_avviso_non_blocca_ma_resta_rilievo(self):
        warning = guardia.Defect("G4-avviso", "lead", "17", "numero nudo")
        self.assertFalse(warning.blocking)
        self.assertEqual(guardia.blocking_defects([warning]), [])


class FreeSections(unittest.TestCase):
    def test_libera_senza_titolo_e_bloccante(self):
        article = entry([{"role": "libera", "h": "", "body": "Testo scritto ma senza titolo."}])
        defects = guardia.check_article("9999999", article)
        self.assertTrue(any(d.check == "sezione" for d in defects))

    def test_libera_con_titolo_passa(self):
        article = entry([{"role": "libera", "h": "Un titolo vero", "body": "Testo scritto con titolo."}])
        self.assertEqual(guardia.check_article("9999999", article), [])

    def test_libera_senza_corpo_non_conta(self):
        article = entry([{"role": "libera", "h": "", "body": ""}])
        self.assertEqual(guardia.check_article("9999999", article), [])


class Links(unittest.TestCase):
    def test_indicator_query_string_e_vietata(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Vedi [qui](/?indicator=12) per il dettaglio."}])
        defects = guardia.check_article("9999999", article)
        self.assertTrue(any(d.check == "link" for d in defects))

    def test_codice_che_non_risolve(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Vedi [qui](/indicatore/fantasia/ter-9999999)."}])
        defects = guardia.check_article("9999999", article)
        self.assertTrue(any(d.check == "link" for d in defects))

    def test_slug_non_canonico_su_un_codice_vero(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Vedi [qui](/indicatore/slug-sbagliato/ter-12)."}])
        defects = guardia.check_article("901", article)
        self.assertTrue(any(d.check == "link" for d in defects))

    def test_link_canonico_vero_passa(self):
        article = entry([{
            "role": "quadro", "h": "T",
            "body": "Vedi [il tasso di disoccupazione](/indicatore/tasso-di-disoccupazione/ter-12).",
        }])
        self.assertEqual(guardia.check_article("901", article), [])


class Markers(unittest.TestCase):
    def test_marcatore_verso_un_codice_inesistente(self):
        article = entry([{
            "role": "quadro", "h": "T",
            "body": "Un grafico.\n\n<!-- grafico: dispersione con=ter-9999999 -->\n\nAltro testo.",
        }])
        defects = guardia.check_article("9999999", article)
        self.assertTrue(any(d.check == "grafico" for d in defects))

    def test_marcatore_vero_produce_svg(self):
        article = entry([{
            "role": "quadro", "h": "T",
            "body": "Un grafico.\n\n<!-- grafico: dispersione con=ter-345 -->\n\nAltro testo.",
        }])
        self.assertEqual(guardia.check_article("901", article), [])


class Figures(unittest.TestCase):
    """Il controllo 1, con un dossier minimo: una sola cifra, `{"valore": -2.1, ...}`."""

    DOSSIER = {"variazione": {"valore": -2.1, "testo": "-2,1 punti percentuali"}}

    def test_decimale_inglese_e_difetto(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Il tasso e' 99.8 per mille."}])
        defects = guardia.check_article("9999999", article, dossier={"a": {"valore": 99.8, "testo": "99,8"}})
        cifre = [d for d in defects if d.check == "cifre"]
        self.assertEqual(len(cifre), 1)
        self.assertIn("'99.8'", cifre[0].message)

        article = entry([{"role": "quadro", "h": "T", "body": "il valore e' 99.5%"}])
        defects = guardia.check_article("9999999", article, dossier={"a": {"valore": 99.5, "testo": "99.5"}})
        cifre = [d for d in defects if d.check == "cifre"]
        self.assertEqual(len(cifre), 1)
        self.assertIn("'99.5'", cifre[0].message)

    def test_decimale_inglese_con_dossier_diverso_e_difetto(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Il tasso e' 9.8 per mille."}])
        defects = guardia.check_article("9999999", article, dossier={"a": {"valore": 9.4, "testo": "9,4"}})
        cifre = [d for d in defects if d.check == "cifre"]
        self.assertEqual(len(cifre), 1)
        self.assertIn("'9.8'", cifre[0].message)

    def test_cifra_col_segno_sbagliato_e_bloccante(self):
        article = entry([{
            "role": "quadro", "h": "T",
            "body": "La variazione e' stata di +2,1 punti percentuali, in salita.",
        }])
        defects = guardia.check_article("9999999", article, dossier=self.DOSSIER)
        cifre = [d for d in defects if d.check == "cifre"]
        self.assertEqual(len(cifre), 1)
        self.assertIn("segno sbagliato", cifre[0].message)

    def test_la_direzione_a_parole_confronta_il_valore_assoluto(self):
        """Lo stesso valore assoluto, ma senza segno esplicito: nessun difetto."""
        article = entry([{"role": "quadro", "h": "T", "body": "Il tasso e' sceso di 2,1 punti."}])
        self.assertEqual(guardia.check_article("9999999", article, dossier=self.DOSSIER), [])

    def test_cifra_assente_dal_dossier(self):
        article = entry([{"role": "quadro", "h": "T", "body": "La variazione e' stata di 7,3 punti."}])
        defects = guardia.check_article("9999999", article, dossier=self.DOSSIER)
        cifre = [d for d in defects if d.check == "cifre"]
        self.assertEqual(len(cifre), 1)
        self.assertIn("non corrisponde", cifre[0].message)

    def test_cifra_esatta_passa(self):
        article = entry([{"role": "quadro", "h": "T", "body": "La variazione e' stata di -2,1 punti."}])
        self.assertEqual(guardia.check_article("9999999", article, dossier=self.DOSSIER), [])

    def test_anni_ranghi_e_piccoli_conteggi_non_si_controllano(self):
        article = entry([{
            "role": "quadro", "h": "T",
            "body": "Nel 2025 il dato e' alla 14ª posizione, su venti territori.",
        }])
        self.assertEqual(guardia.check_article("9999999", article, dossier=self.DOSSIER), [])

    def test_senza_dossier_il_controllo_non_gira(self):
        article = entry([{"role": "quadro", "h": "T", "body": "Una cifra a caso: +99,9 punti."}])
        self.assertEqual(guardia.check_article("9999999", article), [])

    def test_fonti_da_solo_viene_controllato(self):
        import tempfile
        from pathlib import Path
        table = (
            "| claim | citazione letterale |\n"
            "| --- | --- |\n"
            "| test | 12,3 |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fonti.md"
            path.write_text(table, encoding="utf-8")
            values = guardia.source_figures(path)
            article = entry([{"role": "quadro", "h": "T", "body": "Il valore 99,9 non esiste."}])
            defects = guardia.check_article("9999999", article, source_values=values)
            self.assertEqual(len([d for d in defects if d.check == "cifre"]), 1)

    def test_colonna_citazione_letterale_di_fonti_md(self):
        import tempfile
        table = (
            "| claim | citazione letterale |\n"
            "| --- | --- |\n"
            "| previsione 2026 | il tasso salira' di 3,4 punti |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fonti.md"
            path.write_text(table, encoding="utf-8")
            values = guardia.source_figures(path)
            self.assertIn(3.4, values)
            article = entry([{"role": "quadro", "h": "T", "body": "La previsione parla di +3,4 punti."}])
            defects = guardia.check_article("9999999", article, dossier=self.DOSSIER, source_values=values)
            self.assertEqual([d for d in defects if d.check == "cifre"], [])


class BozzaCostruitaApposta(unittest.TestCase):
    """La prova richiesta dall'issue: tre difetti insieme, nella stessa bozza."""

    def test_rossa_su_tre_difetti_insieme(self):
        dossier = {"variazione": {"valore": -2.1, "testo": "-2,1 punti percentuali"}}
        article = entry([
            {
                "role": "quadro",
                "h": "Un titolo",
                "body": (
                    "Il tasso e' sceso di 2,1 punti, ma il dato regge solo in parte.\n\n"
                    "<!-- grafico: dispersione con=ter-9999999 -->\n\n"
                    "La stima corretta parla pero' di +2,1 punti percentuali, in salita."
                ),
            },
            {"role": "libera", "h": "", "body": "Una sezione scritta ma senza titolo."},
        ])
        defects = guardia.check_article("9999999", article, dossier=dossier)
        checks = {d.check for d in defects}
        self.assertIn("grafico", checks, "il marcatore verso un codice inesistente non e' stato visto")
        self.assertIn("cifre", checks, "la cifra col segno sbagliato non e' stata vista")
        self.assertTrue(
            any(d.check == "sezione" for d in defects),
            "la sezione libera senza titolo non e' stata vista",
        )
        # Il "2,1" detto a parole non deve contare come una quarta cifra sbagliata:
        # solo il "+2,1" col segno esplicito e' un difetto.
        self.assertEqual(len([d for d in defects if d.check == "cifre"]), 1)


class RealArticlesWithDossier(unittest.TestCase):
    def test_articoli_veri_con_dossier_vero(self):
        from scripts.editoriale import brief
        from scripts import indicator_store
        from app import sources

        for code in ["ter-12", "ter-17", "ter-167", "ter-901"]:
            with self.subTest(code=code):
                family, raw_id = brief.resolve(code)
                internal_key = sources.internal_id(family, raw_id)
                article = indicator_store.read(internal_key)
                self.assertIsNotNone(article, f"{code} non ha un articolo scritto")

                dossier = brief.build(code)

                fonti = ROOT / "lavoro" / code / "fonti.md"
                source_values = guardia.source_figures(fonti) if fonti.exists() else []

                defects = guardia.check_article(
                    internal_key, article, dossier=dossier, source_values=source_values,
                )
                cifre = [d.quote for d in defects if d.check == "cifre"]

                expected = []
                if code == "ter-12":
                    # riscritto dal pilota del team (#293): le cifre vengono dal dossier e da lavoro/ter-12/fonti.md
                    expected = []
                elif code == "ter-17":
                    # 0,2: la variazione dell'ultimo anno di due territori
                    expected = ["...uli-Venezia Giulia e l'Umbria 0,2, e di un soffio la Valle d'Ao..."]
                elif code == "ter-167":
                    # 5,4 e 8,6: ripartizioni a due livelli non previste nel sito
                    expected = [
                        "...sce in ogni ripartizione, dal 5,4% del Nord-ovest all'8,6% del...",
                        "..., dal 5,4% del Nord-ovest all'8,6% del Centro. Sono variazioni...",
                    ]
                elif code == "ter-901":
                    # 9.603: la variazione della media delle venti regioni fra due anni
                    expected = ["...dia delle regioni è salita di 9.603 euro per abitante. Sono euro..."]

                self.assertEqual(cifre, expected, f"{code} ha difetti imprevisti sulle cifre")

    def test_ter_902_arrotondamento_dossier_vero(self):
        from scripts.editoriale import brief
        from app import sources
        dossier = brief.build("ter-902")
        family, raw_id = brief.resolve("ter-902")
        internal_key = sources.internal_id(family, raw_id)

        # "va dai 16.800 euro della Calabria" è verde
        article_ok = entry([{"role": "quadro", "h": "T", "body": "va dai 16.800 euro della Calabria"}])
        defects_ok = guardia.check_article(internal_key, article_ok, dossier=dossier)
        self.assertEqual(len([d for d in defects_ok if d.check == "cifre"]), 0)

        # "va dai 16.900 euro della Calabria" è un difetto
        article_err = entry([{"role": "quadro", "h": "T", "body": "va dai 16.900 euro della Calabria"}])
        defects_err = guardia.check_article(internal_key, article_err, dossier=dossier)
        self.assertEqual(len([d for d in defects_err if d.check == "cifre"]), 1)

class Cli(unittest.TestCase):
    def test_verde_su_ter_12(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.editoriale.guardia", "ter-12"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"pulito", result.stdout)

    def test_dossier_mancante_esce_con_errore(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.editoriale.guardia", "ter-12", "--dossier", "/tmp/non-esiste-mai.json"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"non esiste", result.stderr)


    def test_fonti_mancante_esce_con_errore(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.editoriale.guardia", "ter-12", "--fonti", "/tmp/non-esiste-mai-fonti.md"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"non esiste", result.stderr)

    def test_fonti_senza_citazioni_stampa_su_stderr(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md") as tmp:
            tmp.write(b"| claim | altra colonna |\n| --- | --- |\n| 1 | 2 |")
            tmp.flush()
            result = subprocess.run(
                [sys.executable, "-m", "scripts.editoriale.guardia", "ter-12", "--fonti", tmp.name],
                cwd=ROOT, capture_output=True, timeout=120,
            )
            self.assertIn(b"nessuna citazione letta da", result.stderr)

    def test_codice_sconosciuto_esce_con_errore(self):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.editoriale.guardia", "ter-99999999"],
            cwd=ROOT, capture_output=True, timeout=120,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"nessuna scheda", result.stderr)


if __name__ == "__main__":
    unittest.main()
