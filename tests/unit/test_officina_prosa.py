"""La misura del freddo, e il cancello che non deve passare quando non capisce.

Due cose distinte finite nello stesso file perché vengono dallo stesso giro:

1. **La quota di paragrafi scoperti.** L'ipotesi di partenza era la densità
   numerica, mediatore misurato da Thäsler-Kordonouri et al. (Journalism 26(9)
   2025, n=3135). Provata su questo corpus e caduta: i nostri articoli hanno
   mediana 2,91 numeri ogni cento parole contro i 3,54 degli esempi, cioè sono
   **meno** densi. Regge invece la quota di paragrafi sostanziali senza nemmeno
   una cifra: esempi 0,25 di mediana e 0,33 di massimo, pubblicati 0,67, con
   313 articoli su 376 sopra il massimo degli esempi.

2. **Un codice che non risolve.** `officina.lint ter-176` selezionava zero
   articoli e stampava "articoli con rilievi: 0". Nella prima run il
   pubblicatore ha eseguito proprio quella forma e ha letto un verde che
   nessuno aveva guadagnato.
"""
import json
import os
import unittest

from officina import lint
from scripts import calibra_prosa


def _paragrafi(*blocchi):
    """Blocchi separati da riga vuota, ognuno lungo abbastanza per contare."""
    riempimento = " ".join(["parola"] * 30)
    return "\n\n".join(f"{blocco} {riempimento}" for blocco in blocchi)


class TheMeasureThatSeparatesTheTwoCorpora(unittest.TestCase):
    def test_a_paragraph_with_a_figure_is_supported(self):
        self.assertEqual(calibra_prosa.unsupported_share(
            _paragrafi("La Campania segna 15,75.", "Il Nord segna 4,5.",
                       "La distanza vale 11,2.")), 0.0)

    def test_a_paragraph_with_nothing_is_not(self):
        self.assertEqual(calibra_prosa.unsupported_share(
            _paragrafi("Il divario resta ampio.", "La situazione è complessa.",
                       "Il quadro non cambia.")), 1.0)

    def test_short_blocks_do_not_count(self):
        """Sotto le venticinque parole è una didascalia, non un paragrafo."""
        testo = "Breve.\n\n" + _paragrafi("Vale 12,5.", "Vale 3,1.", "Vale 8,0.")
        self.assertEqual(calibra_prosa.unsupported_share(testo), 0.0)

    def test_under_three_paragraphs_it_refuses_to_measure(self):
        """Con due blocchi la quota vale 0, 1/2 o 1: non è una misura."""
        self.assertIsNone(calibra_prosa.unsupported_share(
            _paragrafi("Il divario resta.", "Vale 12,5.")))

    def test_the_exemplars_are_read_without_their_index_card(self):
        """La scheda sopra l'estratto ha date e URL: numeri che non sono prosa.

        Contarli gonfierebbe verso l'alto proprio il campione che fa da metro.
        """
        percorso = os.path.join(calibra_prosa.ROOT, "content", "esempi",
                                "ilpost-borgo-albergo.md")
        testo = calibra_prosa.read_exemplar(percorso)
        self.assertNotIn("**Testata**", testo)
        self.assertNotIn("https://", testo)
        self.assertIn("Ferriere", testo)

    def test_the_calibration_file_carries_the_threshold_and_its_reason(self):
        with open(lint.CALIBRAZIONE_PROSA, encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertGreater(payload["soglia_paragrafi_scoperti"], 0)
        self.assertLess(payload["soglia_paragrafi_scoperti"], 1)
        self.assertIn("content/esempi", payload["fonte"])
        self.assertIn("caduta", payload["perche"],
                      "l'ipotesi provata e caduta va detta, o qualcuno la riprova")

    def test_the_threshold_is_measured_on_the_exemplars_not_on_the_cold_ones(self):
        """I 52 riscritti sono i freddi: calibrarci sopra consacra il difetto.

        Stesso principio di packs/calibration.py, e la ragione per cui questa
        soglia non si scrive a mano.
        """
        misurata = calibra_prosa.build()["soglia_paragrafi_scoperti"]
        with open(lint.CALIBRAZIONE_PROSA, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["soglia_paragrafi_scoperti"], misurata)


class TheLintRule(unittest.TestCase):
    def _entry(self, *blocchi):
        return {"lead": "Un lead qualunque, abbastanza lungo da esistere.",
                "sections": [{"role": "quadro", "h": "H", "body": _paragrafi(*blocchi)}]}

    def test_an_article_that_carries_its_figures_passes(self):
        entry = self._entry("La Campania segna 15,75.", "Il Nord si ferma a 4,5.",
                            "Nel 2021 la curva si spezza.")
        self.assertEqual(lint.check_unsupported_paragraphs(entry), [])

    def test_an_article_that_asserts_without_carrying_anything_is_flagged(self):
        entry = self._entry("Il divario resta ampio.", "La situazione è complessa.",
                            "Il quadro non cambia.")
        found = lint.check_unsupported_paragraphs(entry)
        self.assertEqual([f["rule"] for f in found], ["paragrafi-scoperti"])
        self.assertEqual(found[0]["severity"], lint.FLAGS,
                         "è una misura nuova: segnala finché non è tarata sul nuovo")

    def test_an_inline_identifier_is_not_a_free_pass(self):
        """La regola conta le cifre, e basta, com'è calibrata.

        Una prima versione lasciava passare i paragrafi con un identificatore
        fra parentesi quadre. Cercato sui 376 articoli, quel caso ricorre
        **zero volte**: gli identificatori stanno nel campo `corpus`, non nel
        testo. Una scappatoia che non scatta mai si legge come una garanzia e
        non lo è, e faceva divergere la regola dalla misura su cui poggia.
        """
        entry = self._entry("Il calo dipende dal ciclo [eurostat-lunga-durata-ciclo].",
                            "Anche qui [istat-ricambio-naturale-2026].",
                            "E qui [snpa-bacino-padano-2025].")
        found = lint.check_unsupported_paragraphs(entry)
        self.assertEqual([f["rule"] for f in found], ["paragrafi-scoperti"])

    def test_the_rule_counts_what_the_calibration_counted(self):
        """Se le due divergono, la soglia misura una cosa e il cancello un'altra."""
        testo = _paragrafi("Il divario resta ampio.", "Vale 12,5.",
                           "La situazione è complessa.")
        entry = {"lead": "", "sections": [{"role": "quadro", "h": "H", "body": testo}]}
        from scripts import calibra_prosa
        misurata = calibra_prosa.unsupported_share(testo)
        found = lint.check_unsupported_paragraphs(entry)
        self.assertIn(f"({misurata:.0%})", found[0]["detail"])

    def test_a_short_article_is_not_measured(self):
        entry = self._entry("Il divario resta ampio.")
        self.assertEqual(lint.check_unsupported_paragraphs(entry), [])

    def test_the_rule_is_in_the_registry(self):
        self.assertIn(lint.check_unsupported_paragraphs, lint.RULES)

    def test_a_missing_calibration_switches_the_rule_off_not_the_lint(self):
        """Un cancello che muore perché manca un file di misura ferma la
        produzione per la ragione sbagliata."""
        lint.calibrazione_prosa.cache_clear()
        vero, lint.CALIBRAZIONE_PROSA = lint.CALIBRAZIONE_PROSA, "/non/esiste.json"
        try:
            entry = self._entry("Il divario resta ampio.", "La situazione è complessa.",
                                "Il quadro non cambia.")
            self.assertEqual(lint.check_unsupported_paragraphs(entry), [])
        finally:
            lint.CALIBRAZIONE_PROSA = vero
            lint.calibrazione_prosa.cache_clear()


class AnUnresolvedCodeIsAnError(unittest.TestCase):
    """Un cancello che passa quando non capisce l'argomento non è un cancello."""

    TEXTS = {"176": {}, "203": {}, "eur:LFSA": {}}

    def test_the_bare_key_resolves(self):
        selected, missing = lint.resolve_codes(["176"], self.TEXTS)
        self.assertEqual((selected, missing), ({"176"}, []))

    def test_the_family_prefixed_form_resolves_to_the_bare_key(self):
        """È la forma che chi scrive e chi lancia usa sempre."""
        selected, missing = lint.resolve_codes(["ter-176"], self.TEXTS)
        self.assertEqual((selected, missing), ({"176"}, []))

    def test_the_external_colon_form_resolves(self):
        selected, missing = lint.resolve_codes(["eur-LFSA"], self.TEXTS)
        self.assertEqual((selected, missing), ({"eur:LFSA"}, []))

    def test_a_code_that_matches_nothing_is_named(self):
        selected, missing = lint.resolve_codes(["ter-99999"], self.TEXTS)
        self.assertEqual((selected, missing), (set(), ["ter-99999"]))

    def test_a_missing_code_does_not_silently_select_everything(self):
        """Il difetto vero era più sottile: selezionava ZERO e stampava zero
        rilievi, che si legge come promosso."""
        selected, missing = lint.resolve_codes(["ter-99999", "176"], self.TEXTS)
        self.assertEqual(selected, {"176"})
        self.assertEqual(missing, ["ter-99999"])


if __name__ == "__main__":
    unittest.main()
