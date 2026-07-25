"""The writer's worklist: which integrated indicators still need an analyst note.

Logic-only, on synthetic manifest/notes and an injected year_max lookup, so it
never depends on the live analyst_notes.json (which the writer edits) and needs
no running app.
"""

import unittest

from scripts import pending_notes


class PendingNotesWorklist(unittest.TestCase):
    YEARS = {
        "eur:rd_e_gerdreg": 2023,   # integrated, will have no note -> missing
        "12": 2025,                 # integrated, has a current note -> neither
        "13": 2025,                 # integrated, has a stale note   -> stale
        "57": 2024,                 # not integrated (proposed)      -> ignored
    }

    def _year_max(self, key):
        return self.YEARS.get(key)

    def _manifest(self):
        return [
            {"target_indicator_id": "eur:rd_e_gerdreg", "status": "integrated"},
            {"target_indicator_id": "12", "status": "integrated"},
            {"target_indicator_id": "13", "status": "integrated"},
            {"target_indicator_id": "57", "status": "proposed"},
        ]

    def _notes(self):
        return {
            "12": {"vintage": 2025, "attacco": "..."},   # current
            "13": {"vintage": 2024, "attacco": "..."},   # behind year_max 2025
        }

    def test_missing_flags_integrated_indicator_without_a_note(self):
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        ids = [m["id"] for m in missing]
        self.assertEqual(ids, ["eur:rd_e_gerdreg"])
        self.assertEqual(missing[0]["year_max"], 2023)

    def test_proposed_indicator_is_not_on_the_worklist(self):
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        self.assertNotIn("57", [m["id"] for m in missing])

    def test_current_note_is_neither_missing_nor_stale(self):
        missing, stale = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        self.assertNotIn("12", [m["id"] for m in missing])
        self.assertNotIn("12", [s["id"] for s in stale])

    def test_stale_flags_a_note_behind_the_data(self):
        _, stale = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        ids = [s["id"] for s in stale]
        self.assertEqual(ids, ["13"])
        self.assertEqual(stale[0]["vintage"], 2024)
        self.assertEqual(stale[0]["year_max"], 2025)

    def test_manifest_year_max_reads_new_year_stdlib(self):
        rows = [
            {"target_indicator_id": "eur:a", "new_year": "2023", "status": "integrated"},
            {"target_indicator_id": "eur:b", "new_year": "", "current_year": "", "status": "integrated"},
            {"target_indicator_id": "eur:c", "new_year": "n/d", "status": "integrated"},
        ]
        year_of = pending_notes.manifest_year_max(rows)
        self.assertEqual(year_of, {"eur:a": 2023})  # blank / non-numeric -> no year
        self.assertIsInstance(year_of["eur:a"], int)

    def test_manifest_year_max_falls_back_to_current_year(self):
        # Integrated entries like 617/618/623/624 carry the year only in
        # current_year; the max of both columns keeps them eligible for staleness.
        rows = [
            {"target_indicator_id": "617", "new_year": "", "current_year": "2025"},
            {"target_indicator_id": "eur:a", "new_year": "2023", "current_year": "2024"},
        ]
        year_of = pending_notes.manifest_year_max(rows)
        self.assertEqual(year_of["617"], 2025)          # current_year fallback
        self.assertEqual(year_of["eur:a"], 2024)        # max of the two

    def test_integrated_targets_dedup_and_order(self):
        rows = [
            {"target_indicator_id": "eur:a", "status": "integrated"},
            {"target_indicator_id": "eur:a", "status": "integrated"},
            {"target_indicator_id": "eur:b", "status": "proposed"},
            {"target_indicator_id": "eur:c", "status": "integrated"},
        ]
        self.assertEqual(pending_notes.integrated_targets(rows), ["eur:a", "eur:c"])


if __name__ == "__main__":
    unittest.main()
