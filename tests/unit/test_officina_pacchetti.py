"""Lo stadio `prepara`: i pacchetti su disco, e cio' che viaggia e' il percorso.

Il vincolo che decide se il workflow smaltisce l'arretrato o solo due
indicatori: cio' che un agente **restituisce** e' output, a venticinque dollari
per milione di token. Un pacchetto pesa 6-12 mila token, quindi cinquanta
indicatori restituiti da un agente solo sarebbero mezzo milione di token di
puro transito, oltre i limiti pratici di una risposta. Un percorso ne pesa
venti.
"""
import json
import os
import tempfile
import unittest

from officina import pacchetti
from packs import build as build_module


class ItWritesToDiskAndHandsBackPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="pacchetti-")

    def test_a_real_indicator_lands_as_a_file(self):
        path = pacchetti.write_pack("ter-176", self.dir)
        self.assertIsNotNone(path)
        self.assertTrue(os.path.isabs(path), "l'agente riceve un assoluto, non un relativo")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 5000)

    def test_the_file_carries_what_the_writer_needs_and_nothing_it_must_hunt(self):
        path = pacchetti.write_pack("ter-176", self.dir)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for atteso in ("Come si scrive qui", "La voce", "Il modello di registro",
                       "ANGOLI, DAL PIU' FORTE", "La matrice, anno per territorio"):
            self.assertIn(atteso, text)

    def test_the_legal_roles_are_stated_so_nobody_greps_for_them(self):
        """Tutti e quattro gli scrittori della prima run hanno scoperto i
        `role` con lo stesso `grep`, uno per uno."""
        path = pacchetti.write_pack("ter-176", self.dir)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for role in ("definizione", "quadro", "dinamica", "limiti"):
            self.assertIn(f"`{role}`", text)

    def test_the_diagnostics_are_not_in_the_file(self):
        """Le cifre che ordinano gli angoli non arrivano a chi scrive.

        Tutti e quattro i giudici ciechi della prima run hanno indicato come
        paragrafo piu' freddo quello che le trascriveva.
        """
        path = pacchetti.write_pack("ter-176", self.dir)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for diagnostica in ("pendenza_prima", "pendenza_dopo", "quota_spiegata",
                            "z_modificato", "salto_tipico"):
            self.assertNotIn(f"{diagnostica}:", text,
                             f"{diagnostica} e' arrivata a chi scrive")

    def test_an_unknown_code_is_reported_not_invented(self):
        packs = pacchetti.build(["ter-999999"], self.dir)
        self.assertEqual(packs[0]["path"], None)

    def test_the_json_form_is_one_line_the_workflow_can_parse(self):
        packs = pacchetti.build(["ter-176", "ter-203"], self.dir)
        payload = json.dumps({"packs": packs, "mancanti": []})
        again = json.loads(payload)
        self.assertEqual(len(again["packs"]), 2)
        for pack in again["packs"]:
            self.assertIn("code", pack)
            self.assertIn("path", pack)


class TheLengthIsStructuralNotAWordCount(unittest.TestCase):
    """Chiedere 765 parole non funziona: nella prima run il pacchetto ne
    chiedeva 765 e 540, una forbice del 42%, e le bozze sono uscite a 657 e
    619, una forbice del 13%. **La lunghezza convergeva invece di divergere.**

    Un numero di parole e' una richiesta che un modello media; un numero di
    angoli da sviluppare e' una richiesta che si conta.
    """

    def test_no_angles_means_nothing_to_develop(self):
        self.assertEqual(build_module.angles_to_develop([]), 0)

    def test_one_dominant_angle_asks_for_one(self):
        found = [{"strength": 0.9}, {"strength": 0.2}, {"strength": 0.1}]
        self.assertEqual(build_module.angles_to_develop(found), 1)

    def test_several_comparable_angles_ask_for_several(self):
        found = [{"strength": 0.8}, {"strength": 0.7}, {"strength": 0.6},
                 {"strength": 0.1}]
        self.assertEqual(build_module.angles_to_develop(found), 3)

    def test_a_rich_series_and_a_thin_one_diverge(self):
        """E' il punto: due indicatori devono chiedere lavori diversi."""
        ricca = [{"strength": 0.9}, {"strength": 0.8}, {"strength": 0.7},
                 {"strength": 0.6}, {"strength": 0.5}]
        magra = [{"strength": 0.9}, {"strength": 0.1}]
        self.assertGreaterEqual(build_module.angles_to_develop(ricca),
                                build_module.angles_to_develop(magra) * 3)

    def test_the_pack_states_it_where_the_writer_reads(self):
        family, raw = build_module._resolve("ter-176")
        pack = build_module.build_pack(family, raw)
        self.assertIn("develop", pack)
        rendered = build_module.render(pack)
        self.assertIn("ANGOLI DA SVILUPPARE", rendered)
        self.assertIn("non un bersaglio", rendered,
                      "il numero di parole non deve leggersi come un obiettivo")


if __name__ == "__main__":
    unittest.main()
