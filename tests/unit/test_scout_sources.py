"""The scout: proposing NEW sources (dataflows), not new indicators.

Pure-function tests over an inline dataflow list, so every filter branch is
exercised deterministically without the SDMX catalogue or the network.
"""

import unittest

from scripts import scout_sources


# Covered: one exact curated flow, plus an AVQ flow that stands in for the whole
# already-integrated Multiscopo survey family (DCCV_AVQ).
COVERED = {"covered_exact", "1_DF_DCCV_AVQ_PERSONE_1"}
# Domain tokens already on the allowlist (here: Forze di Lavoro).
TERMS = {"lavoro", "forze"}

FLOWS = [
    {"id": "1_DF_DCCV_AVQ_PERSONE_1", "name": "Fumo - regioni e tipo di comune"},
    {"id": "10_DF_DCCV_AVQ_FAMIGLIE_9", "name": "Alcolici - regioni e tipo di comune"},
    {"id": "2_DF_DCIS_RSERVSAN_4", "name": "Accertamenti diagnostici - regioni"},
    {"id": "3_DF_DCSS_HUDW_2", "name": "Abitazioni per epoca di costruzione - regioni e province"},
    {"id": "4_DF_DCCV_TAXDISOCCU1_5", "name": "Dati regionali - durata della disoccupazione"},
    {"id": "5_DF_X_LAVORO_1", "name": "Occupati per forze di lavoro - regioni"},
    {"id": "6_DF_BULK_CORRIS", "name": "Corrispondenza tra codice e nome della regione"},
    {"id": "7_DF_Y_GEN_1", "name": "Dati regionali"},
    {"id": "8_DF_Z_NAT_1", "name": "Occupazione nazionale"},
    {"id": "11_DF_DCSC_FIDIMPR_1", "name": "Clima di fiducia - livello nazionale e ripartizionale"},
    {"id": "covered_exact", "name": "Servizi sanitari - regioni"},
    {"id": "9_DF_DCIS_RSERVSAN_4b", "name": "Accertamenti diagnostici - regioni"},
]


class ProposeSources(unittest.TestCase):
    def setUp(self):
        self.props = scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS, limit=40)
        self.ids = [p["dataflow_id"] for p in self.props]

    def test_only_genuinely_new_regional_domains_survive(self):
        # Health (RSERVSAN) and housing census (HUDW) are new domains, kept once
        # each; the duplicate-named health flow is de-duplicated.
        self.assertEqual(len(self.props), 2)
        self.assertIn("2_DF_DCIS_RSERVSAN_4", self.ids)
        self.assertIn("3_DF_DCSS_HUDW_2", self.ids)

    def test_excludes_covered_and_allowlisted(self):
        for excluded in [
            "covered_exact",              # exact curated flow
            "10_DF_DCCV_AVQ_FAMIGLIE_9",  # covered survey family (Multiscopo AVQ)
            "5_DF_X_LAVORO_1",            # allowlist domain by name token
            "4_DF_DCCV_TAXDISOCCU1_5",    # allowlist survey family (Forze di Lavoro)
            "6_DF_BULK_CORRIS",           # metadata/lookup table
            "7_DF_Y_GEN_1",               # generic name, no domain signal
            "8_DF_Z_NAT_1",               # not a regional breakdown
            "11_DF_DCSC_FIDIMPR_1",       # macro-area only (ripartizionale), not 20 regions
        ]:
            self.assertNotIn(excluded, self.ids, excluded)

    def test_proposals_are_ranked_and_shaped(self):
        scores = [p["priority_score"] for p in self.props]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for p in self.props:
            self.assertEqual(p["territory_hint"], "regione")
            self.assertGreater(p["priority_score"], 0.0)
            self.assertTrue(p["reason"])


class Uncapped(unittest.TestCase):
    """Every uncovered regional domain must survive, not just the first N.

    The cap used to default to 40 and the score is uniform, so the ranking fell
    back to alphabetical: past the cap a genuinely new domain was invisible, and
    the scout looked exhausted while the catalogue still held dozens. These
    flows are five distinct new domains; the default must return all five.
    """

    FLOWS = [
        {"id": f"{i}_DF_DCCV_{tok.upper()}_1", "name": f"{name} - regioni"}
        for i, (tok, name) in enumerate([
            ("turismo", "Notti trascorse per turismo"),
            ("reddito", "Reddito disponibile delle famiglie"),
            ("istruzione", "Popolazione per titolo di studio"),
            ("giustizia", "Procedimenti definiti dai tribunali"),
            ("cultura", "Spesa delle amministrazioni per cultura"),
        ])
    ]

    def test_default_proposes_every_new_domain(self):
        props = scout_sources.propose_sources(self.FLOWS, covered=set(), terms=set())
        self.assertEqual(len(props), 5)

    def test_limit_still_caps_when_asked(self):
        props = scout_sources.propose_sources(
            self.FLOWS, covered=set(), terms=set(), limit=2)
        self.assertEqual(len(props), 2)


class QueueShape(unittest.TestCase):
    def test_rows_carry_stable_ids_and_new_status(self):
        props = scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS)
        rows = scout_sources.to_rows(props)
        self.assertTrue(all(r["candidate_id"].startswith("istat_sdmx:") for r in rows))
        self.assertTrue(all(r["triage_status"] == "new" for r in rows))

    def test_written_queue_uses_lf_not_crlf(self):
        # csv.DictWriter defaults to CRLF; a stray CR at end of a changed line
        # reads as trailing whitespace and trips the gate's git diff --check, so
        # the scout could never commit an updated queue. The writer must emit LF.
        import tempfile
        from pathlib import Path

        rows = scout_sources.to_rows(
            scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS)
        )
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source_candidates.csv"
            scout_sources.write_source_candidates(rows, path=path)
            raw = path.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertIn(b"\n", raw)

    def test_upsert_preserves_human_triage(self):
        rows = scout_sources.to_rows(
            scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS)
        )
        reviewed = dict(rows[0])
        reviewed["triage_status"] = "rejected"
        reviewed["triage_notes"] = "gia coperto altrove"
        merged = scout_sources.upsert([reviewed], rows)
        kept = next(r for r in merged if r["candidate_id"] == reviewed["candidate_id"])
        self.assertEqual(kept["triage_status"], "rejected")
        self.assertEqual(kept["triage_notes"], "gia coperto altrove")

    def test_upsert_preserves_first_discovery_date(self):
        # Un refresh ri-vede lo stesso dataflow, non lo ri-scopre: `discovered_at`
        # deve restare quello della prima volta, non la data del refresh, o l'età
        # di ogni candidato si azzererebbe a ogni run.
        rows = scout_sources.to_rows(
            scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS)
        )
        old = dict(rows[0])
        old["discovered_at"] = "2026-07-25T00:00:00+00:00"
        fresh = dict(rows[0])
        fresh["discovered_at"] = "2026-07-28T00:00:00+00:00"
        merged = scout_sources.upsert([old], [fresh])
        kept = next(r for r in merged if r["candidate_id"] == old["candidate_id"])
        self.assertEqual(kept["discovered_at"], "2026-07-25T00:00:00+00:00")

    def test_upsert_dates_a_genuinely_new_candidate(self):
        rows = scout_sources.to_rows(
            scout_sources.propose_sources(FLOWS, covered=COVERED, terms=TERMS)
        )
        fresh = dict(rows[0])
        fresh["discovered_at"] = "2026-07-28T00:00:00+00:00"
        merged = scout_sources.upsert([], [fresh])  # nessun prior
        self.assertEqual(merged[0]["discovered_at"], "2026-07-28T00:00:00+00:00")


class RefreshFallsBackToCache(unittest.TestCase):
    """Con --refresh lo scout forza il refetch del catalogo. Se Istat è giù o
    bloccato, l'errore non deve abortire lo scout prima che triaghi la coda già
    committata: il dispatcher gira uno stadio per tick e lo scout è il primo,
    quindi un guasto Istat persistente lo rilancerebbe e ucciderebbe ogni tick,
    fermando tutta la catena. Si ripiega sulla cache quando c'è."""

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def dataflows(self, force=False):
            if force:
                from scripts import istat_sdmx
                raise istat_sdmx.IstatBlockedError("403 dall'endpoint")
            return [{"id": "cached_1", "name": "Dal catalogo in cache - regioni"}]

    def test_forced_refresh_failure_falls_back_to_cache(self):
        from unittest import mock
        with mock.patch.object(scout_sources.istat_sdmx, "SdmxClient", self._FakeClient):
            flows = scout_sources._load_flows(offline=False, cache_dir="/x", refresh=True)
        self.assertEqual(flows, [{"id": "cached_1", "name": "Dal catalogo in cache - regioni"}])


class RegionalHint(unittest.TestCase):
    """`reg.` abbreviato deve contare come regionale (era il buco per cui la
    spesa sociale dei comuni per regione non arrivava mai in coda), senza pescare
    `registro` o `regime`, che iniziano per `reg` ma non sono territori."""

    def test_the_abbreviation_counts_as_regional(self):
        for name in ("spesa dei comuni per reg.", "Occupati - regioni e province",
                     "Something NUTS2 breakdown"):
            self.assertTrue(scout_sources.REGIONAL_HINT.search(name), name)

    def test_it_does_not_fire_on_reg_words_that_are_not_regions(self):
        for name in ("Registro nazionale imprese", "Regime forfettario per settore",
                     "ripartizionale per area"):
            self.assertFalse(scout_sources.REGIONAL_HINT.search(name), name)


if __name__ == "__main__":
    unittest.main()
