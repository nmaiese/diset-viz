"""Lo store delle pratiche: un file per record, id dentro il file.

Su una directory temporanea, cosi' non tocca mai i registri committati.
"""

import tempfile
import unittest
from pathlib import Path

from scripts import practice_store as s


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_save_and_load_one(self):
        rec = {"practice_id": "dem:NMIGRATEIN#nuovo-1", "state": "fusa", "type": "nuovo"}
        s.save(rec, root=self.root)
        got = s.load("dem:NMIGRATEIN#nuovo-1", root=self.root)
        self.assertEqual(got["state"], "fusa")
        self.assertEqual(got["practice_id"], "dem:NMIGRATEIN#nuovo-1")

    def test_load_all_keys_by_practice_id(self):
        s.save({"practice_id": "dem:A#nuovo-1", "state": "fusa"}, root=self.root)
        s.save({"practice_id": "901#aggiornamento-3", "state": "invalidata"}, root=self.root)
        allp = s.load_all(root=self.root)
        self.assertEqual(set(allp), {"dem:A#nuovo-1", "901#aggiornamento-3"})
        self.assertEqual(allp["901#aggiornamento-3"]["state"], "invalidata")

    def test_awkward_ids_survive(self):
        # due punti, cancelletto e trattino insieme
        pid = "bes:09PAE009-N25#smentita-2"
        s.save({"practice_id": pid, "state": "invalidata"}, root=self.root)
        self.assertEqual(s.load(pid, root=self.root)["practice_id"], pid)

    def test_two_ids_that_sanitize_alike_do_not_collide(self):
        # "dem:A" e "dem/A" ripuliscono allo stesso slug, ma l'impronta li separa
        s.save({"practice_id": "dem:A#nuovo-1", "state": "x"}, root=self.root)
        s.save({"practice_id": "dem/A#nuovo-1", "state": "y"}, root=self.root)
        allp = s.load_all(root=self.root)
        self.assertEqual(len(allp), 2)

    def test_save_without_id_is_refused(self):
        with self.assertRaises(s.StoreError):
            s.save({"state": "fusa"}, root=self.root)

    def test_remove(self):
        s.save({"practice_id": "dem:A#nuovo-1", "state": "x"}, root=self.root)
        self.assertTrue(s.remove("dem:A#nuovo-1", root=self.root))
        self.assertFalse(s.remove("dem:A#nuovo-1", root=self.root))
        self.assertIsNone(s.load("dem:A#nuovo-1", root=self.root))

    def test_missing_directory_reads_as_empty(self):
        self.assertEqual(s.load_all(root=self.root / "nope"), {})

    def test_broken_file_stops_strict_reader(self):
        (self.root / "broken.json").write_text("{ not json", encoding="utf-8")
        with self.assertRaises(Exception):
            s.load_all(root=self.root, strict=True)
        # tollerante: salta il file rotto invece di fermarsi
        self.assertEqual(s.load_all(root=self.root, strict=False), {})


if __name__ == "__main__":
    unittest.main()
