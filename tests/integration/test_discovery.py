"""Discovery pipeline tests (pure stdlib: no Flask, runs in the hunter's env).

Covers the staging queue schema, the priority policy (fresh + regional first),
the conservative dedup classifier, the Eurostat adapter's NUTS2->region collapse
and freshest-honest-year logic, and the hunter/integrator round trip through a
temporary queue so production data is never touched.
"""

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import (
    discovery, eurostat_source, istat_regional_source,
    discover_candidates, promote_candidates,
)


class FreshnessAndScoring(unittest.TestCase):
    def test_freshness_bands_match_external_layer(self):
        self.assertEqual(discovery.freshness_status(2025), "current")
        self.assertEqual(discovery.freshness_status(2023), "recent")
        self.assertEqual(discovery.freshness_status(2020), "dated")
        self.assertEqual(discovery.freshness_status(2019), "stale")
        self.assertEqual(discovery.freshness_status(None), "unknown")

    def test_priority_prefers_fresh_regional_new(self):
        fresh_regional_new = discovery.priority_score({
            "freshness_status": "current", "territory_level": "regione",
            "coverage": 1.0, "definition_match": "new",
        })
        stale_provincial_dup = discovery.priority_score({
            "freshness_status": "stale", "territory_level": "provincia",
            "coverage": 0.5, "definition_match": "exact",
        })
        self.assertGreater(fresh_regional_new, stale_provincial_dup)

    def test_regional_outranks_identical_provincial(self):
        base = {"freshness_status": "recent", "coverage": 1.0, "definition_match": "new"}
        self.assertGreater(
            discovery.priority_score({**base, "territory_level": "regione"}),
            discovery.priority_score({**base, "territory_level": "provincia"}),
        )


class DedupClassifier(unittest.TestCase):
    def test_new_when_no_overlap(self):
        index = [("1", "Numero di biblioteche pubbliche", discovery.normalize_name("Numero di biblioteche pubbliche"))]
        match, dup = discovery.classify_definition_match("Spesa in ricerca e sviluppo sul PIL", index)
        self.assertEqual(match, "new")
        self.assertEqual(dup, "")

    def test_overlap_flags_compatible_with_id(self):
        index = [("901", "PIL pro capite ai prezzi di mercato", discovery.normalize_name("PIL pro capite ai prezzi di mercato"))]
        match, dup = discovery.classify_definition_match("PIL pro capite ai prezzi di mercato (Eurostat)", index)
        self.assertIn(match, {"compatible", "proxy"})
        self.assertEqual(dup, "901")

    def test_never_claims_exact(self):
        index = [("901", "PIL pro capite", discovery.normalize_name("PIL pro capite"))]
        match, _ = discovery.classify_definition_match("PIL pro capite", index)
        self.assertNotEqual(match, "exact")

    def test_existing_index_ids_carry_their_family(self):
        """A raw id is only unique inside a family, so a match on a BES or
        Multiscopo series has to name the family or the promotion step cannot
        tell which indicator it means."""
        index = discovery.build_existing_index()
        by_prefix = {
            "bes:": sum(1 for i, _, _ in index if i.startswith("bes:")),
            "multiscopo:": sum(1 for i, _, _ in index if i.startswith("multiscopo:")),
        }
        for prefix, count in by_prefix.items():
            self.assertGreater(count, 0, f"no {prefix} entries in the index")
        # The territorial family owns the unprefixed namespace.
        self.assertTrue(any(i.isdigit() for i, _, _ in index))

    def test_promotion_refuses_a_candidate_id_that_lies_about_its_source(self):
        """Found end-to-end: the dataset merge is keyed on the source series, so
        a queue row whose candidate_id no longer matches its own source fields
        overwrites and retargets another candidate's series, silently removing a
        live atlas entry. The queue is hand-edited in the review PR, so the
        mismatch has to fail before anything is written."""
        from scripts import promote_candidates

        good = {"candidate_id": "eurostat_regional:rd_e_gerdreg",
                "source": "eurostat_regional", "source_indicator_id": "rd_e_gerdreg"}
        promote_candidates._check_candidate_id(good)  # non solleva

        lying = dict(good, candidate_id="eurostat_regional:qualcos_altro")
        with self.assertRaises(SystemExit):
            promote_candidates._check_candidate_id(lying)

    def test_promotion_refuses_an_unqualified_duplicate_target(self):
        from scripts import promote_candidates

        candidate = {
            "candidate_id": "eurostat_regional:x",
            "definition_match": "compatible",
            "duplicate_of": "10AMB014",  # a BES id without its family
            "source_indicator_id": "x",
        }
        with self.assertRaises(SystemExit):
            promote_candidates._target_id(candidate)

        candidate["duplicate_of"] = "bes:10AMB014"
        self.assertEqual(promote_candidates._target_id(candidate), "bes:10AMB014")


class EurostatAdapter(unittest.TestCase):
    def test_parse_weights_bolzano_trento(self):
        doc = eurostat_source.fetch_dataset("rd_e_gerdreg", offline=True)
        weights = eurostat_source.fetch_weights(offline=True)
        regional = eurostat_source.parse_regional(doc, "weighted", weights)
        # Trentino present once (Bolzano+Trento combined by population weight),
        # 20 regions, and the value sits between the two provincial figures.
        self.assertIn("trentino-alto-adige", regional)
        self.assertEqual(len(regional), 20)
        for region_key in regional:
            self.assertIn(region_key, eurostat_source.REGION_NAMES)
        tv = regional["trentino-alto-adige"]["2023"]
        self.assertGreater(tv, 1.0)
        self.assertLess(tv, 1.3)

    def test_weighted_needs_weights_else_drops_split(self):
        # Without weights the split region cannot be combined honestly: dropped,
        # never silently averaged.
        doc = eurostat_source.fetch_dataset("rd_e_gerdreg", offline=True)
        regional = eurostat_source.parse_regional(doc, "weighted", weights=None)
        self.assertNotIn("trentino-alto-adige", regional)

    def test_best_recent_year_respects_coverage(self):
        doc = eurostat_source.fetch_dataset("nama_10r_2gdp", offline=True)
        regional = eurostat_source.parse_regional(doc)
        year, coverage, present = eurostat_source.best_recent_year(regional)
        self.assertIsNotNone(year)
        self.assertGreaterEqual(coverage, eurostat_source.MIN_COVERAGE)
        self.assertLessEqual(len(present), 20)

    def test_discover_produces_regional_candidate(self):
        raw = eurostat_source.discover("rd_e_gerdreg", offline=True)
        self.assertEqual(raw["territory_level"], "regione")
        self.assertEqual(raw["source"], "eurostat_regional")
        self.assertTrue(raw["year_max"])
        self.assertGreater(float(raw["coverage"]), 0.0)

    def test_normalized_rows_use_decimal_comma(self):
        rows = eurostat_source.normalized_rows("rd_e_gerdreg", offline=True)
        self.assertTrue(rows)
        self.assertTrue(all(row["region_key"] in eurostat_source.REGION_NAMES for row in rows))
        self.assertTrue(any("," in row["value"] for row in rows))


class QueueRoundTrip(unittest.TestCase):
    def setUp(self):
        self._original_path = discovery.CANDIDATES_PATH

    def tearDown(self):
        discovery.CANDIDATES_PATH = self._original_path

    def _patched_queue(self, tmp):
        # scripts share the same discovery module object, so one reassignment
        # redirects the queue everywhere (path is resolved at call time).
        path = Path(tmp) / "candidates.csv"
        discovery.CANDIDATES_PATH = path
        return path

    def test_hunter_writes_ranked_queue(self):
        with TemporaryDirectory() as tmp:
            path = self._patched_queue(tmp)
            discovered, merged = discover_candidates.run("eurostat_regional", offline=True)
            self.assertEqual(len(discovered), len(eurostat_source.EUROSTAT_SERIES))
            rows = discovery.read_candidates(path)
            scores = [float(r["priority_score"]) for r in rows]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertTrue(all(r["triage_status"] == "new" for r in rows))

    def test_upsert_preserves_human_triage(self):
        reviewed = [{
            "candidate_id": "eurostat_regional:rd_e_gerdreg",
            "triage_status": "rejected", "triage_notes": "duplica un BES",
            "priority_score": "0.5",
        }]
        fresh = [{
            "candidate_id": "eurostat_regional:rd_e_gerdreg", "name": "x",
            "year_max": "2024", "coverage": 1.0, "freshness_status": "recent",
            "definition_match": "new", "territory_level": "regione",
            "priority_score": 0.9,
        }]
        merged = discovery.upsert_candidates(reviewed, fresh)
        entry = next(m for m in merged if m["candidate_id"] == "eurostat_regional:rd_e_gerdreg")
        self.assertEqual(entry["triage_status"], "rejected")
        self.assertEqual(entry["triage_notes"], "duplica un BES")
        self.assertEqual(entry["year_max"], "2024")  # data refreshed

    def test_promote_acts_only_on_approved(self):
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            # Nothing approved yet -> no promotion.
            result = promote_candidates.run(offline=True, dry_run=True)
            self.assertEqual(result["approved"], 0)

            # Approve one candidate, then promote to temp outputs.
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:nama_10r_2gdp":
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            result = promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)
            self.assertEqual(result["approved"], 1)
            self.assertGreater(result["dataset_rows"], 0)

            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_rows = list(csv.DictReader(handle, delimiter=";"))
            # GDP is a proxy of id 901 -> enriches that target, never score-eligible.
            self.assertTrue(all(r["target_indicator_id"] == "901" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "false" for r in ds_rows))
            with out_mf.open(encoding="utf-8", newline="") as handle:
                mf_rows = list(csv.DictReader(handle, delimiter=";"))
            self.assertTrue(all(r["status"] == "proposed" for r in mf_rows))

    def test_promote_new_indicator_gets_eur_namespace(self):
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":  # definition_match == new
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)
            with out_ds.open(encoding="utf-8", newline="") as handle:
                ds_rows = list(csv.DictReader(handle, delimiter=";"))
            # A genuinely new series becomes a standalone atlas entry under eur:.
            self.assertTrue(all(r["target_indicator_id"] == "eur:rd_e_gerdreg" for r in ds_rows))
            self.assertTrue(all(r["atlas_eligible"] == "true" for r in ds_rows))
            self.assertTrue(all(r["score_eligible"] == "false" for r in ds_rows))

    def test_retargeting_a_series_moves_its_manifest_entry(self):
        """Found end-to-end. Confirming a match in the review PR (editing
        duplicate_of on an already promoted candidate) is the documented way a
        series changes target. The data rows follow the new target, so the
        manifest entry has to follow too: keying it on the target as well left
        the old entry behind, still claiming status=integrated for an indicator
        with no data. Placeholder entries carry no source and must survive."""
        with TemporaryDirectory() as tmp:
            self._patched_queue(tmp)
            discover_candidates.run("eurostat_regional", offline=True)
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":
                    row["triage_status"] = "approved"
            discovery.write_candidates(rows)

            out_ds = Path(tmp) / "external.csv"
            out_mf = Path(tmp) / "manifest.csv"
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)

            # Un segnaposto senza fonte, come quelli reali (status=unavailable).
            with out_mf.open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle, delimiter=";"))
            placeholder = {c: "" for c in promote_candidates.MANIFEST_COLUMNS}
            placeholder.update({"target_indicator_id": "999", "status": "unavailable"})
            manifest.append(placeholder)
            with out_mf.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=promote_candidates.MANIFEST_COLUMNS,
                                        delimiter=";", lineterminator="\n")
                writer.writeheader()
                writer.writerows(manifest)

            # Un umano conferma il match: la stessa serie ora aggancia un BES.
            rows = discovery.read_candidates()
            for row in rows:
                if row["candidate_id"] == "eurostat_regional:rd_e_gerdreg":
                    row.update({"definition_match": "compatible",
                                "duplicate_of": "bes:01SAL002",
                                "triage_status": "approved"})
            discovery.write_candidates(rows)
            promote_candidates.run(offline=True, out_dataset=out_ds, out_manifest=out_mf)

            with out_mf.open(encoding="utf-8", newline="") as handle:
                manifest = list(csv.DictReader(handle, delimiter=";"))
            for_series = [r for r in manifest if r["source_indicator_id"] == "rd_e_gerdreg"]
            self.assertEqual(len(for_series), 1, "the manifest entry was duplicated, not moved")
            self.assertEqual(for_series[0]["target_indicator_id"], "bes:01SAL002")
            self.assertEqual(
                [r for r in manifest if r["target_indicator_id"] == "eur:rd_e_gerdreg"], [],
                "stale entry left behind for the old target",
            )
            self.assertEqual(
                len([r for r in manifest if not r["source"] and not r["source_indicator_id"]]), 1,
                "the source-less placeholder entry was collapsed",
            )


class AdmittingASeriesIsConfigNotCode(unittest.TestCase):
    """The change that lets the chain grow without a human writing Python.

    The hunter is exhausted the moment its wired sources stop growing, and
    wiring one used to mean editing `scripts/istat_regional_source.py`. No agent
    may write code, so the chain had a hard ceiling: five series, then nothing
    forever. The curated list now lives in `config/istat_series.yaml`, which the
    scout is allowed to write.
    """

    def test_the_committed_config_loads_every_wired_series_well_formed(self):
        """The committed watchlist may grow, so this does not freeze its
        contents: freezing the list here is what turned admitting a series back
        into a code change and stalled the scout. It guards the two things that
        would break silently instead. The seed series must not be dropped by
        accident, and every row load_series returns must carry the fields the
        hunter needs to fetch and identify the series. The exact shape of each
        admitted row (direction, category, mapped theme) is policed, without
        freezing the list, by tests/test_source_admission.py."""
        series = istat_regional_source.load_series()
        self.assertLessEqual(
            {"OLDAGEDEPR", "DEPENDRATE"}, set(series),
            "a seed series was dropped from config/istat_series.yaml",
        )
        for series_id, spec in series.items():
            self.assertEqual(spec["data_type"], series_id)
            self.assertTrue(spec["name"], f"{series_id}: no name")
            self.assertTrue(spec["dataflow"], f"{series_id}: no dataflow")
            self.assertTrue(spec["dsd_label"], f"{series_id}: no dsd_label")

    def test_a_row_can_bring_its_own_dataflow(self):
        """The point of the file. A second Istat domain is a row, not a module:
        `dataflow` used to be a module constant, so every series had to come
        from the demographic one."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "istat_series.yaml"
            path.write_text(
                "series:\n"
                "  - id: NEWCODE\n"
                "    dataflow: 99_999_DF_OTHER_1\n"
                "    dsd_label: DCIS_OTHER\n"
                "    name: Una serie di un altro dominio (Istat, regioni)\n"
                '    unit: "%"\n'
                "    decimals: 2\n"
                "    theme: Un tema nuovo (Istat)\n"
                "    quality_life_category: salute_cura\n"
                "    direction: lower_better\n",
                encoding="utf-8",
            )
            series = istat_regional_source.load_series(path)
        spec = series["NEWCODE"]
        self.assertEqual(spec["dataflow"], "99_999_DF_OTHER_1")
        self.assertEqual(spec["dsd_label"], "DCIS_OTHER")
        self.assertEqual(spec["decimals"], 2)
        self.assertEqual(spec["proposed_direction"], "lower_better")
        # A quoted YAML scalar must survive the round trip: the mini-parser must
        # not swallow the "%", or a percentage unit would reach the page blank.
        self.assertEqual(spec["unit"], "%")

    def test_a_missing_config_is_an_empty_watchlist_not_a_crash(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(istat_regional_source.load_series(Path(tmp) / "nope.yaml"), {})


class IstatRegionalAdapter(unittest.TestCase):
    def test_parse_regional_combines_bolzano_trento(self):
        rows = istat_regional_source.fetch_rows("OLDAGEDEPR", offline=True)
        regional = istat_regional_source.parse_regional(rows, "OLDAGEDEPR")
        # 20 regions, Trentino present once (Bolzano+Trento combined by weight),
        # its value sitting between the two provincial figures.
        self.assertEqual(len(regional), istat_regional_source.REGION_COUNT)
        self.assertIn(istat_regional_source.TRENTINO_NAME, regional)
        parts = {}
        for row in rows:
            if row["DATA_TYPE"] == "OLDAGEDEPR" and row["REF_AREA"] in istat_regional_source.TRENTINO_PARTS:
                parts.setdefault(row["TIME_PERIOD"], {})[row["REF_AREA"]] = float(row["OBS_VALUE"])
        year = max(istat_regional_source.parse_regional(rows, "OLDAGEDEPR")[istat_regional_source.TRENTINO_NAME])
        combined = regional[istat_regional_source.TRENTINO_NAME][year]
        lo, hi = sorted(parts[year].values())
        self.assertGreaterEqual(combined, lo)
        self.assertLessEqual(combined, hi)

    def test_partial_trentino_is_dropped_not_published(self):
        # A year with only Bolzano (or only Trento) is not Trentino Alto Adige:
        # it must be left missing, never published as one province's value.
        rows = [
            {"DATA_TYPE": "X", "REF_AREA": "ITD1", "TIME_PERIOD": "2020", "OBS_VALUE": "40"},
            {"DATA_TYPE": "X", "REF_AREA": "ITD2", "TIME_PERIOD": "2020", "OBS_VALUE": "42"},
            {"DATA_TYPE": "X", "REF_AREA": "ITD1", "TIME_PERIOD": "2021", "OBS_VALUE": "41"},
        ]
        regional = istat_regional_source.parse_regional(rows, "X")
        trentino = regional.get(istat_regional_source.TRENTINO_NAME, {})
        self.assertIn("2020", trentino)   # both provinces present -> combined
        self.assertNotIn("2021", trentino)  # only Bolzano -> dropped

    def test_best_recent_year_respects_coverage(self):
        rows = istat_regional_source.fetch_rows("DEPENDRATE", offline=True)
        regional = istat_regional_source.parse_regional(rows, "DEPENDRATE")
        year, coverage, present = istat_regional_source.best_recent_year(regional)
        self.assertIsNotNone(year)
        self.assertGreaterEqual(coverage, istat_regional_source.MIN_COVERAGE)
        self.assertLessEqual(len(present), istat_regional_source.REGION_COUNT)

    def test_discover_produces_regional_candidate(self):
        raw = istat_regional_source.discover("OLDAGEDEPR", offline=True)
        self.assertEqual(raw["territory_level"], "regione")
        self.assertEqual(raw["source"], "istat_demografia")
        self.assertEqual(raw["source_dataset"], istat_regional_source.DATAFLOW)
        self.assertTrue(raw["year_max"])
        self.assertGreater(float(raw["coverage"]), 0.0)

    def test_normalized_rows_use_decimal_comma(self):
        rows = istat_regional_source.normalized_rows("OLDAGEDEPR", offline=True)
        self.assertTrue(rows)
        self.assertTrue(any("," in row["value"] for row in rows))

    def test_hunter_discovers_new_istat_candidates(self):
        # Offline, the hunter can only read series that ship a committed fixture.
        # Admitting a live-only series to config/istat_series.yaml (the scout may
        # write a config row but not commit a fixture) must not break this test,
        # so pin the watchlist to the fixture-backed subset instead of the whole
        # config. The live hunter reads every series over the network; that path
        # is not exercised here.
        original_series = istat_regional_source.ISTAT_SERIES
        original_path = discovery.CANDIDATES_PATH
        fixture_backed = {
            sid: spec for sid, spec in original_series.items()
            if istat_regional_source._fixture_path(sid).exists()
        }
        self.assertTrue(fixture_backed, "no committed Istat fixture to discover from")
        istat_regional_source.ISTAT_SERIES = fixture_backed
        try:
            with TemporaryDirectory() as tmp:
                discovery.CANDIDATES_PATH = Path(tmp) / "candidates.csv"
                discovered, _ = discover_candidates.run("istat_demografia", offline=True)
                # A fixture-backed series must not be silently dropped en route.
                self.assertEqual(discover_candidates.FAILURES, [])
                self.assertEqual(len(discovered), len(fixture_backed))
                for cand in discovered:
                    self.assertEqual(cand["source"], "istat_demografia")
                    self.assertEqual(cand["territory_level"], "regione")
                    self.assertEqual(cand["triage_status"], "new")
                    self.assertTrue(cand["discovered_at"], "every candidate carries provenance")
        finally:
            istat_regional_source.ISTAT_SERIES = original_series
            discovery.CANDIDATES_PATH = original_path


class IstatMultiDimensionAdapter(unittest.TestCase):
    """A dataflow with more than the pilot's three dimensions (FREQ, REF_AREA,
    DATA_TYPE) is the common case, not an edge case: povertà, cittadinanza and
    most other Istat regional data also break down by sex, age band, household
    type. `_build_key` and `parse_regional` have to handle any dimension count
    without turning an unfiltered breakdown into a silently wrong regional
    total."""

    def _spec(self, **overrides):
        spec = {
            "data_type": "POVASS",
            "dataflow": "99_1_DF_TESTPOV_1",
            "dsd_label": "DCCV_TESTPOV",
            "indicator_dimension": "DATA_TYPE",
            "dimension_order": ["FREQ", "REF_AREA", "SESSO", "DATA_TYPE"],
            "dimension_values": {"SESSO": "9"},
        }
        spec.update(overrides)
        return spec

    def test_build_key_generalizes_beyond_three_dimensions(self):
        key = istat_regional_source._build_key(self._spec())
        # FREQ=A, REF_AREA=wildcard, SESSO=9 (totale), DATA_TYPE=POVASS, in the
        # dataflow's own position order: a fixed three-slot format could not
        # have produced this even by accident.
        self.assertEqual(key, "A..9.POVASS")

    def test_build_key_still_produces_the_pilot_shape_by_default(self):
        """A row that never sets dimension_order/dimension_values (the four
        seed series) must keep querying exactly as before."""
        spec = {
            "data_type": "OLDAGEDEPR",
            "dataflow": istat_regional_source.DATAFLOW,
            "dsd_label": istat_regional_source.DSD_LABEL,
            "indicator_dimension": "DATA_TYPE",
            "dimension_order": ["FREQ", "REF_AREA", "DATA_TYPE"],
            "dimension_values": {},
        }
        self.assertEqual(istat_regional_source._build_key(spec), "A..OLDAGEDEPR")

    def test_build_key_refuses_a_dimension_with_no_known_value(self):
        """A dimension missing from dimension_values must stop the query, not
        wildcard it: a wildcard here does not mean 'total', it means 'every
        code of this dimension, mixed into the response'."""
        spec = self._spec(dimension_values={})
        with self.assertRaises(ValueError):
            istat_regional_source._build_key(spec)

    def test_load_series_parses_the_new_optional_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "istat_series.yaml"
            path.write_text(
                "series:\n"
                "  - id: POVASS\n"
                "    dataflow: 99_1_DF_TESTPOV_1\n"
                "    dsd_label: DCCV_TESTPOV\n"
                "    name: Poverta assoluta di prova (Istat, regioni)\n"
                '    unit: "%"\n'
                "    decimals: 1\n"
                "    theme: Un tema di prova (Istat)\n"
                "    quality_life_category: salute_cura\n"
                "    direction: lower_better\n"
                "    dimension_order: [FREQ, REF_AREA, SESSO, DATA_TYPE]\n"
                "    dimension_values: SESSO=9\n",
                encoding="utf-8",
            )
            series = istat_regional_source.load_series(path)
        spec = series["POVASS"]
        self.assertEqual(spec["dimension_order"], ["FREQ", "REF_AREA", "SESSO", "DATA_TYPE"])
        self.assertEqual(spec["dimension_values"], {"SESSO": "9"})
        self.assertEqual(spec["indicator_dimension"], "DATA_TYPE")
        self.assertEqual(istat_regional_source._build_key(spec), "A..9.POVASS")

    def _rows(self):
        # Same region/year, three breakdowns of SESSO: 1 (maschi), 2 (femmine),
        # 9 (totale, the only one that should ever reach a published page).
        return [
            {"DATA_TYPE": "POVASS", "REF_AREA": "ITC1", "SESSO": "1", "TIME_PERIOD": "2023", "OBS_VALUE": "10"},
            {"DATA_TYPE": "POVASS", "REF_AREA": "ITC1", "SESSO": "2", "TIME_PERIOD": "2023", "OBS_VALUE": "14"},
            {"DATA_TYPE": "POVASS", "REF_AREA": "ITC1", "SESSO": "9", "TIME_PERIOD": "2023", "OBS_VALUE": "24"},
        ]

    def test_parse_regional_filters_out_other_breakdowns_of_the_same_dataflow(self):
        regional = istat_regional_source.parse_regional(
            self._rows(), "POVASS", indicator_dimension="DATA_TYPE",
            dimension_filters={"SESSO": "9"},
        )
        # Only the 'totale' row (24) may reach the region, never the male-only
        # or female-only figure and never a sum or an average of the three.
        self.assertEqual(regional["Piemonte"]["2023"], 24.0)

    def test_parse_regional_fails_closed_on_a_missing_filter_column(self):
        """A dimension named in dimension_filters that is not even a column of
        the row (a truncated response, or a typo in dimension_values naming a
        column the dataflow does not have) must exclude the row, not pass it
        through unfiltered because there was nothing to compare against."""
        rows = [{"DATA_TYPE": "POVASS", "REF_AREA": "ITC1", "TIME_PERIOD": "2023", "OBS_VALUE": "24"}]
        regional = istat_regional_source.parse_regional(
            rows, "POVASS", dimension_filters={"SESSO": "9"},
        )
        self.assertEqual(regional, {})

    def test_parse_regional_raises_rather_than_guess_a_conflict(self):
        """Without dimension_filters, all three SESSO breakdowns pass the
        DATA_TYPE check and collide on the same region/year with different
        values. Averaging or last-write-wins would publish a number nobody
        asked for; refusing is the only safe response."""
        with self.assertRaises(ValueError):
            istat_regional_source.parse_regional(self._rows(), "POVASS")

    def test_parse_regional_does_not_raise_on_a_genuine_duplicate(self):
        """Two identical rows for the same region/year (a resend, a cache
        artifact) are not a conflict: only *different* values are."""
        rows = self._rows()[-1:] * 2  # the 'totale' row, twice, same value
        regional = istat_regional_source.parse_regional(
            rows, "POVASS", dimension_filters={"SESSO": "9"},
        )
        self.assertEqual(regional["Piemonte"]["2023"], 24.0)


class MultiSourcePromotion(unittest.TestCase):
    """Every hunter adapter must be able to reach the atlas under its own name.

    The hunter grew a second adapter while promotion still hardcoded
    `source != "eurostat_regional"` and a fixed `eur:` namespace. The result was
    two candidates permanently stuck at the top of the queue, and a trap behind
    them: wiring only the parser would have published an Istat series at
    /indicatore/<slug>/eur-... under Eurostat's name and licence.
    """

    def test_every_feed_has_a_promotion_parser_and_a_family(self):
        for feed in discovery.FEED_FAMILY:
            with self.subTest(feed=feed):
                self.assertIn(feed, promote_candidates.PROMOTION_PARSERS)
        for feed in promote_candidates.PROMOTION_PARSERS:
            with self.subTest(feed=feed):
                self.assertIn(feed, discovery.FEED_FAMILY)

    def test_the_stdlib_mirrors_match_the_app_source_registry(self):
        """discovery.FAMILY_PREFIX / FEED_FAMILY are copies of app/sources.py.

        They are copied because the discovery scripts are stdlib-only, and a
        silent drift here does not crash: it mislabels an indicator's
        institution and licence on a public page.
        """
        from app import sources

        self.assertEqual(
            discovery.FAMILY_PREFIX,
            {family: meta["internal_prefix"] for family, meta in sources.SOURCES.items()},
        )
        self.assertEqual(discovery.FEED_FAMILY, dict(sources.FAMILY_BY_FEED))

    def test_a_new_series_takes_its_own_familys_namespace(self):
        istat = {"definition_match": "new", "duplicate_of": "",
                 "source": "istat_demografia", "source_indicator_id": "OLDAGEDEPR",
                 "candidate_id": "istat_demografia:OLDAGEDEPR"}
        euro = {"definition_match": "new", "duplicate_of": "",
                "source": "eurostat_regional", "source_indicator_id": "rd_e_gerdreg",
                "candidate_id": "eurostat_regional:rd_e_gerdreg"}
        self.assertEqual(promote_candidates._target_id(istat), "dem:OLDAGEDEPR")
        self.assertEqual(promote_candidates._target_id(euro), "eur:rd_e_gerdreg")

    def test_an_unknown_source_is_refused_not_guessed(self):
        candidate = {"definition_match": "new", "duplicate_of": "",
                     "source": "invalsi", "source_indicator_id": "x",
                     "candidate_id": "invalsi:x"}
        with self.assertRaises(SystemExit):
            promote_candidates._target_id(candidate)

    def test_repromotion_keeps_the_curators_decision(self):
        """A refresh must not undo a review.

        The promoter fills the manifest from the candidate, so re-promoting an
        integrated series wrote the *proposed* direction, score_eligible=false
        and status=proposed over the curator's work, silently dropping a live
        indicator out of the quality-of-life score.
        """
        existing = [{
            "target_indicator_id": "eur:rd_p_persreg", "source": "eurostat_regional",
            "source_indicator_id": "rd_p_persreg", "new_year": "2023",
            "direction": "higher_better", "score_eligible": "true",
            "status": "integrated", "review_notes": "Verso confermato dai dati.",
        }]
        fresh = [{
            "target_indicator_id": "eur:rd_p_persreg", "source": "eurostat_regional",
            "source_indicator_id": "rd_p_persreg", "new_year": "2024",
            "direction": "contextual", "score_eligible": "false",
            "status": "proposed", "review_notes": "Voce d'atlante autonoma.",
        }]
        merged = promote_candidates._merge_manifest(existing, fresh)
        self.assertEqual(len(merged), 1)
        row = merged[0]
        self.assertEqual(row["new_year"], "2024", "data fields refresh")
        self.assertEqual(row["direction"], "higher_better")
        self.assertEqual(row["score_eligible"], "true")
        self.assertEqual(row["status"], "integrated")
        self.assertEqual(row["review_notes"], "Verso confermato dai dati.")

    def test_a_proposed_entry_is_overwritten_normally(self):
        existing = [{"target_indicator_id": "dem:X", "source": "istat_demografia",
                     "source_indicator_id": "X", "status": "proposed",
                     "direction": "contextual", "score_eligible": "false", "review_notes": ""}]
        fresh = [{"target_indicator_id": "dem:X", "source": "istat_demografia",
                  "source_indicator_id": "X", "status": "proposed",
                  "direction": "higher_better", "score_eligible": "false", "review_notes": "nuova"}]
        merged = promote_candidates._merge_manifest(existing, fresh)
        self.assertEqual(merged[0]["direction"], "higher_better")
        self.assertEqual(merged[0]["review_notes"], "nuova")


class NonFinalObservations(unittest.TestCase):
    """Estimates must not win the freshness ranking.

    Istat flags the current year 'e' on the demographic indicators. Nothing read
    OBS_STATUS, so an estimate set year_max, scored `current` and put the
    candidate at the top of the queue ahead of series with published years.
    """

    def test_istat_drops_estimated_observations(self):
        rows = istat_regional_source.fetch_rows("OLDAGEDEPR", offline=True)
        final = istat_regional_source.parse_regional(rows, "OLDAGEDEPR")
        everything = istat_regional_source.parse_regional(rows, "OLDAGEDEPR", include_non_final=True)
        years = lambda data: {int(y) for values in data.values() for y in values}
        self.assertTrue(years(everything) - years(final), "the fixture must carry an estimate")
        for row in rows:
            if (row.get("OBS_STATUS") or "").strip().lower() in istat_regional_source.NON_FINAL_STATUSES:
                self.assertNotIn(int(row["TIME_PERIOD"]), years(final))

    def test_only_estimate_like_codes_are_dropped(self):
        """'b' (break), 'd' (definition differs) and 'u' (low reliability) are
        final values with a caveat. Dropping them would discard real data."""
        for code in ("b", "d", "u", "", "a"):
            self.assertNotIn(code, istat_regional_source.NON_FINAL_STATUSES)
        self.assertEqual(
            istat_regional_source.NON_FINAL_STATUSES,
            eurostat_source.NON_FINAL_STATUSES,
            "both adapters must apply the same rule",
        )


if __name__ == "__main__":
    unittest.main()
