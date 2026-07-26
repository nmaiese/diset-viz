"""The writer's worklist: which integrated indicators still need an article.

Logic-only, on synthetic manifest/notes and an injected year_max lookup, so it
never depends on the live indicator_texts.json (which the writer edits) and needs
no running app.
"""

import unittest

from scripts import pending_notes


def _article(*roles, lead="Un lead.", vintage=2025):
    return {
        "lead": lead,
        "vintage": vintage,
        "sections": [{"role": role, "h": None, "body": "Corpo."} for role in roles],
    }


FULL = pending_notes.ARTICLE_ROLES


class PendingNotesWorklist(unittest.TestCase):
    YEARS = {
        "eur:rd_e_gerdreg": 2023,   # integrated, will have no article -> missing
        "12": 2025,                 # integrated, complete and current -> neither
        "13": 2025,                 # integrated, complete but stale   -> stale
        "14": 2025,                 # integrated, two sections of four -> missing
        "57": 2024,                 # not integrated (proposed)        -> ignored
    }

    def _year_max(self, key):
        return self.YEARS.get(key)

    def _manifest(self):
        return [
            {"target_indicator_id": "eur:rd_e_gerdreg", "status": "integrated"},
            {"target_indicator_id": "12", "status": "integrated"},
            {"target_indicator_id": "13", "status": "integrated"},
            {"target_indicator_id": "14", "status": "integrated"},
            {"target_indicator_id": "57", "status": "proposed"},
        ]

    def _notes(self):
        return {
            "12": _article(*FULL, vintage=2025),
            "13": _article(*FULL, vintage=2024),          # behind year_max 2025
            "14": _article("quadro", "limiti", vintage=2025),
        }

    def test_missing_flags_integrated_indicator_without_an_article(self):
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        entry = next(m for m in missing if m["id"] == "eur:rd_e_gerdreg")
        self.assertEqual(entry["year_max"], 2023)
        self.assertEqual(entry["unwritten"], list(FULL))

    def test_missing_flags_a_half_written_article(self):
        """An entry can exist and still be half a page.

        The four-role rewrite split "has an entry" from "is written", and this
        script only knew the first, so both externally sourced indicators sat at
        two sections of four while it printed "la catena e completa" and the
        writer stage never fired.
        """
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        entry = next(m for m in missing if m["id"] == "14")
        self.assertEqual(entry["unwritten"], ["definizione", "dinamica"])
        self.assertTrue(entry["lead"])

    def test_a_complete_article_is_not_on_the_worklist(self):
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        self.assertNotIn("12", [m["id"] for m in missing])

    def test_an_article_with_every_section_but_no_lead_is_missing(self):
        notes = {"12": _article(*FULL, lead="")}
        missing, _ = pending_notes.pending(self._manifest(), notes, self._year_max)
        entry = next(m for m in missing if m["id"] == "12")
        self.assertEqual(entry["unwritten"], [])
        self.assertFalse(entry["lead"])

    def test_roles_mirror_the_app_schema(self):
        """Stdlib copy of app.indicator_texts.ROLES: pin it or it drifts."""
        from app.indicator_texts import ROLE_ORDER

        self.assertEqual(list(pending_notes.ARTICLE_ROLES), list(ROLE_ORDER))

    def test_proposed_indicator_is_not_on_the_worklist(self):
        missing, _ = pending_notes.pending(self._manifest(), self._notes(), self._year_max)
        self.assertNotIn("57", [m["id"] for m in missing])

    def test_current_article_is_neither_missing_nor_stale(self):
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
