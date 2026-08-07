"""Lo stadio `pubblica`: la mappa bozza -> entry e' codice, non un turno di agente.

Il pubblicatore componeva da solo l'entry dello store, e per farlo apriva
`indicator_store.py`, i template e le viste: otto turni nella prova, ventuno e
ventiquattro nella prima run, per far uscire zero a un linter. Chiave interna,
livello, vintage e forma del file non sono decisioni editoriali, quindi non
possono costare un turno a ogni articolo.

L'altra meta' e' che questo comando **rifiuta** invece di scrivere male: un
cancello che accetta cio' che non capisce non e' un cancello.
"""
import json
import os
import tempfile
import unittest

from officina import pubblica
from scripts import indicator_store

BOZZA = {
    "lead": "Un lead con l'apostrofo.",
    "sections": [
        {"role": "quadro", "h": "Che cosa dice", "body": "Corpo del quadro.", "claims": []},
        {"role": "dinamica", "h": "Come cambia", "body": "Corpo della dinamica."},
        {"role": "limiti", "h": "Che cosa non dice", "body": "Corpo dei limiti."},
    ],
    "corpus": [],
    "angolo": "graduatoria-spezzata",
}


class ItMapsADraftOntoAnEntry(unittest.TestCase):
    def test_the_key_comes_from_the_url_form(self):
        self.assertEqual(pubblica.chiave("ter-30"), "30")
        self.assertEqual(pubblica.chiave("bes-10AMB004"), "bes:10AMB004")

    def test_level_and_vintage_are_filled_by_the_code(self):
        entry = pubblica.entry(BOZZA, "ter-30")
        self.assertEqual(entry["level"], "regione")
        self.assertIsInstance(entry["vintage"], int)
        self.assertEqual([s["role"] for s in entry["sections"]],
                         ["quadro", "dinamica", "limiti"])

    def test_the_entry_says_where_it_comes_from(self):
        """Non e' una firma: e' la porta da cui l'articolo entra nella coda di
        verifica, che prima prendeva solo i firmati dal revisore."""
        self.assertEqual(pubblica.entry(BOZZA, "ter-30")["origine"], "officina")

    def test_it_does_not_declare_roles_covered(self):
        # Lo deriva `app.indicator_texts.emitted_roles` dalle sezioni scritte.
        # Dichiararlo qui sarebbe la seconda copia della stessa lista.
        self.assertNotIn("roles_covered", pubblica.entry(BOZZA, "ter-30"))

    def test_unknown_fields_do_not_reach_the_file(self):
        sporca = dict(BOZZA, feedback={"stato": "applicato"}, note_di_lavorazione="x")
        entry = pubblica.entry(sporca, "ter-30")
        self.assertNotIn("feedback", entry)
        self.assertNotIn("note_di_lavorazione", entry)


class ItRefusesInsteadOfGuessing(unittest.TestCase):
    def rifiuto(self, bozza, code="ter-30"):
        with self.assertRaises(pubblica.Rifiutata) as caso:
            pubblica.entry(bozza, code)
        return str(caso.exception)

    def test_an_invented_role_is_named(self):
        bozza = dict(BOZZA, sections=[{"role": "scala", "body": "x"}])
        self.assertIn("scala", self.rifiuto(bozza))

    def test_an_empty_body_stops_it(self):
        bozza = dict(BOZZA, sections=[dict(BOZZA["sections"][0], body="  ")])
        self.assertIn("corpo", self.rifiuto(bozza))

    def test_a_missing_lead_stops_it(self):
        self.assertIn("lead", self.rifiuto(dict(BOZZA, lead="")))

    def test_two_sections_with_the_same_role_stop_it(self):
        """Uscito al primo giro della macchina nuova: due `dinamica` con due
        titoli diversi. Il renderer indicizzava per ruolo, quindi la pagina
        rendeva un corpo due volte e perdeva l'altro, senza che nessuna guardia
        lo vedesse."""
        doppia = dict(BOZZA, sections=[
            {"role": "dinamica", "h": "A", "body": "Primo corpo."},
            {"role": "dinamica", "h": "B", "body": "Secondo corpo."},
        ])
        self.assertIn("due sezioni con ruolo", self.rifiuto(doppia))

    def test_an_indicator_outside_the_catalogue_stops_it(self):
        self.assertIn("catalogo", self.rifiuto(BOZZA, "ter-99999"))

    def test_a_level_the_indicator_does_not_have_stops_it(self):
        with self.assertRaises(pubblica.Rifiutata) as caso:
            pubblica.entry(BOZZA, "ter-30", level="comune")
        self.assertIn("comune", str(caso.exception))


class ItWritesWhereTheStoreExpects(unittest.TestCase):
    def test_the_file_lands_and_reads_back(self):
        with tempfile.TemporaryDirectory(prefix="pubblica-") as root:
            entry = pubblica.entry(BOZZA, "ter-30")
            path = indicator_store.write(pubblica.chiave("ter-30"), entry, root=root)
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                letta = json.load(handle)
            self.assertEqual(letta["key"], "30")
            self.assertEqual(letta["lead"], BOZZA["lead"])


if __name__ == "__main__":
    unittest.main()
