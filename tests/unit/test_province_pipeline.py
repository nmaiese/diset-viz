"""Offline tests for the provincial SDMX acquisition pipeline.

None of these touch the network: the SDMX client is exercised through an injected
opener and a fake clock, and the parsers run on small inline fixtures. The
provincial dataset schema test runs only if the CSV has already been produced, so
the suite stays green before the first real download campaign.
"""

import csv
import io
import unittest
from pathlib import Path

from scripts import build_province_dataset, istat_sdmx, province_sources
from scripts.province_names import normalize_province_name, province_key


SAMPLE_SDMX_CSV = (
    "DATAFLOW,FREQ,REF_AREA,DATA_TYPE,TIME_PERIOD,OBS_VALUE\r\n"
    "IT1:DCCV_X(1.0),A,ITC11,V1,2022,81.4\r\n"
    "IT1:DCCV_X(1.0),A,ITF33,V1,2022,79.2\r\n"
)

SAMPLE_DATAFLOWS_JSON = (
    '{"data":{"dataflows":[{"id":"DCIS_POPRES1","agencyID":"IT1","version":"1.0",'
    '"name":"Popolazione residente","names":{"it":"Popolazione residente",'
    '"en":"Resident population"},"structure":'
    '"urn:...DataStructure=IT1:DCIS_POPRES1(1.0)"}]}}'
)

SAMPLE_DSD_JSON = (
    '{"data":{"dataStructures":[{"id":"DCIS_POPRES1",'
    '"dataStructureComponents":{"dimensionList":{'
    '"dimensions":['
    '{"id":"REF_AREA","position":2,"localRepresentation":{"enumeration":'
    '"urn:...Codelist=IT1:CL_ITTER107(1.0)"}},'
    '{"id":"FREQ","position":1,"localRepresentation":{"enumeration":'
    '"urn:...Codelist=IT1:CL_FREQ(1.0)"}}],'
    '"timeDimensions":[{"id":"TIME_PERIOD"}]}}}]}}'
)

SAMPLE_CODELIST_JSON = (
    '{"data":{"codelists":[{"id":"CL_ITTER107","codes":['
    '{"id":"ITC11","name":"Torino","names":{"it":"Torino"}},'
    '{"id":"ITH10","name":"Bolzano/Bozen","names":{"it":"Bolzano/Bozen"}}]}]}}'
)


class SdmxParserTest(unittest.TestCase):
    def test_parse_sdmx_csv(self):
        rows = istat_sdmx.parse_sdmx_csv(SAMPLE_SDMX_CSV)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["REF_AREA"], "ITC11")
        self.assertEqual(rows[0]["TIME_PERIOD"], "2022")
        self.assertEqual(rows[0]["OBS_VALUE"], "81.4")

    def test_parse_dataflows(self):
        flows = istat_sdmx.parse_dataflows(SAMPLE_DATAFLOWS_JSON)
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0]["id"], "DCIS_POPRES1")
        self.assertEqual(flows[0]["name"], "Popolazione residente")

    def test_parse_datastructure_orders_dimensions_by_position(self):
        dsd = istat_sdmx.parse_datastructure(SAMPLE_DSD_JSON)
        self.assertEqual([d["id"] for d in dsd["dimensions"]], ["FREQ", "REF_AREA"])
        self.assertEqual(dsd["time_dimension"], "TIME_PERIOD")
        self.assertIn("CL_ITTER107", dsd["dimensions"][1]["codelist"])

    def test_parse_codelist(self):
        codelist = istat_sdmx.parse_codelist(SAMPLE_CODELIST_JSON)
        self.assertEqual(codelist["codes"]["ITC11"]["name"], "Torino")
        self.assertIn("ITH10", codelist["codes"])


class FakeClock:
    """Monotonic fake time; sleep advances it and records the durations."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class SdmxClientTest(unittest.TestCase):
    def _client(self, tmp, opener, clock):
        return istat_sdmx.SdmxClient(
            cache_dir=tmp,
            min_interval=16.0,
            sleeper=clock.sleep,
            clock=clock.time,
            opener=opener,
        )

    def test_rate_limiter_spaces_network_calls(self):
        import tempfile

        clock = FakeClock()
        calls = []

        def opener(url, headers):
            calls.append(url)
            return 200, b"OK"

        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(tmp, opener, clock)
            client.get("https://example/a", "text/plain")
            client.get("https://example/b", "text/plain")

        # Two distinct network calls, and the second waited the full interval.
        self.assertEqual(len(calls), 2)
        self.assertTrue(any(s >= 16.0 for s in clock.sleeps))

    def test_cache_hit_avoids_network(self):
        import tempfile

        clock = FakeClock()
        calls = []

        def opener(url, headers):
            calls.append(url)
            return 200, b"PAYLOAD"

        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(tmp, opener, clock)
            first = client.get("https://example/x", "text/plain")
            second = client.get("https://example/x", "text/plain")

        self.assertEqual(first, b"PAYLOAD")
        self.assertEqual(second, b"PAYLOAD")
        self.assertEqual(len(calls), 1)        # second served from disk cache
        self.assertEqual(client.request_count, 1)

    def test_expired_data_response_is_refetched_but_structures_are_not(self):
        """The cache split that keeps a scheduled refresh from freezing: a data
        response older than data_max_age is refetched, a structure never is."""
        import tempfile

        import time

        clock = FakeClock()
        # Anchored to real time: cache ages are measured against file mtimes.
        wall = {"now": time.time()}
        calls = []

        def opener(url, headers):
            calls.append(url)
            return 200, b"PAYLOAD"

        with tempfile.TemporaryDirectory() as tmp:
            client = istat_sdmx.SdmxClient(
                cache_dir=tmp,
                min_interval=0.0,
                sleeper=clock.sleep,
                clock=clock.time,
                wall_clock=lambda: wall["now"],
                data_max_age=100.0,
                opener=opener,
            )
            client.get("https://example/data", "text/csv", max_age=100.0)
            client.get("https://example/struct", "text/json")
            self.assertEqual(len(calls), 2)

            # Still inside the window: both served from disk.
            wall["now"] += 50
            client.get("https://example/data", "text/csv", max_age=100.0)
            client.get("https://example/struct", "text/json")
            self.assertEqual(len(calls), 2)

            # Past it: only the data response goes back to the network.
            wall["now"] += 100
            client.get("https://example/data", "text/csv", max_age=100.0)
            client.get("https://example/struct", "text/json")
            self.assertEqual(calls, [
                "https://example/data",
                "https://example/struct",
                "https://example/data",
            ])

    def test_cache_only_serves_expired_entries(self):
        """cache_only means no network at all, so age must not turn a hit into
        a miss (offline reruns of build_province_dataset depend on this)."""
        import tempfile
        import time

        clock = FakeClock()
        wall = {"now": time.time()}

        with tempfile.TemporaryDirectory() as tmp:
            writer = istat_sdmx.SdmxClient(
                cache_dir=tmp, min_interval=0.0, sleeper=clock.sleep, clock=clock.time,
                opener=lambda url, headers: (200, b"PAYLOAD"),
            )
            writer.get("https://example/old", "text/csv", max_age=10.0)

            offline = istat_sdmx.SdmxClient(
                cache_dir=tmp, cache_only=True, wall_clock=lambda: wall["now"] + 10_000,
            )
            self.assertEqual(
                offline.get("https://example/old", "text/csv", max_age=10.0), b"PAYLOAD"
            )
            self.assertEqual(offline.request_count, 0)

    def test_refresh_data_forces_a_refetch(self):
        import tempfile

        clock = FakeClock()
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            client = istat_sdmx.SdmxClient(
                cache_dir=tmp, min_interval=0.0, sleeper=clock.sleep, clock=clock.time,
                refresh_data=True,
                opener=lambda url, headers: (calls.append(url), (200, b"A,B\n1,2\n"))[1],
            )
            client.data("FLOW", key="A")
            client.data("FLOW", key="A")

        self.assertEqual(len(calls), 2)

    def test_block_detection_on_empty_200(self):
        import tempfile

        clock = FakeClock()

        def opener(url, headers):
            return 200, b""

        with tempfile.TemporaryDirectory() as tmp:
            client = self._client(tmp, opener, clock)
            with self.assertRaises(istat_sdmx.IstatBlockedError):
                client.get("https://example/blocked", "text/plain")


class ProvinceNameTest(unittest.TestCase):
    def test_normalization_cases(self):
        self.assertEqual(normalize_province_name("Bolzano/Bozen"), "Bolzano")
        self.assertEqual(normalize_province_name("Bolzano / Bozen"), "Bolzano")
        self.assertEqual(normalize_province_name("Valle d'Aosta/Vallée d'Aoste"), "Aosta")
        self.assertEqual(normalize_province_name("Valle d'Aosta / Vallée d'Aoste"), "Aosta")
        self.assertEqual(normalize_province_name("Reggio nell'Emilia"), "Reggio Emilia")
        self.assertEqual(normalize_province_name("Città metropolitana di Roma"), "Roma")
        self.assertEqual(normalize_province_name("  Forlì-Cesena  "), "Forlì-Cesena")

    def test_province_keys_are_unique_and_clean(self):
        names = ["Torino", "Forlì-Cesena", "Reggio Emilia", "Reggio Calabria",
                 "Massa-Carrara", "Pesaro e Urbino", "Aosta", "Bolzano", "L'Aquila"]
        keys = [province_key(n) for n in names]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(province_key("Forlì-Cesena"), "forli-cesena")
        self.assertEqual(province_key("L'Aquila"), "l-aquila")


class ProposeDirectionTest(unittest.TestCase):
    def test_word_boundary_avoids_false_positives(self):
        # "Laureati" must not match the "reati" token -> higher, not lower.
        self.assertEqual(
            province_sources.propose_direction("Laureati e altri titoli terziari (25-39 anni)"),
            "higher_better",
        )

    def test_clear_polarities(self):
        self.assertEqual(province_sources.propose_direction("Mortalità infantile"), "lower_better")
        self.assertEqual(province_sources.propose_direction("Giovani che non lavorano e non studiano (NEET)"), "lower_better")
        self.assertEqual(province_sources.propose_direction("Speranza di vita alla nascita"), "higher_better")

    def test_nuts_patterns_are_disjoint(self):
        self.assertTrue(province_sources.NUTS3_PATTERN.match("ITC4A"))   # Cremona
        self.assertTrue(province_sources.NUTS3_PATTERN.match("ITC11"))   # Torino
        self.assertFalse(province_sources.NUTS3_PATTERN.match("ITC1"))   # NUTS2 region
        self.assertTrue(province_sources.NUTS2_PATTERN.match("ITC1"))
        # Le province nate dopo il 2004: fino al 23/9/2026 la regex le scartava.
        for code in ("IT108", "IT109", "IT110", "IT111"):
            self.assertTrue(province_sources.NUTS3_PATTERN.match(code), code)
        for code in ("IT", "ITC", "IT1", "IT10", "IT1000"):
            self.assertFalse(province_sources.NUTS3_PATTERN.match(code), code)

    def test_la_pipeline_si_importa_da_sola(self):
        """In un processo nuovo, senza l'app gia' caricata: un import di
        `scripts.province_sources` in testa a `app/province_profile.py` faceva
        un ciclo, e `build_province_dataset.py` lanciato da solo non partiva."""
        import subprocess
        import sys
        from pathlib import Path
        radice = Path(__file__).resolve().parents[2]
        for modulo in ("scripts.build_province_dataset", "scripts.province_sources",
                       "scripts.discover_provinces"):
            with self.subTest(modulo=modulo):
                esito = subprocess.run([sys.executable, "-c", f"import {modulo}"],
                                       cwd=radice, capture_output=True, text=True, check=False)
                self.assertEqual(esito.returncode, 0, esito.stderr[-500:])

    def test_un_indicatore_ha_un_verso_solo_sui_due_livelli(self):
        """Su 18 indicatori il manifest provinciale e quello regionale davano
        versi opposti, e 1.027 posizioni erano speculari fra la pagina
        provincia e la scheda. D1, 23/9/2026: il verso e' uno."""
        import csv
        from pathlib import Path
        dati = Path(__file__).resolve().parents[2] / "app" / "static" / "data"
        def versi(nome):
            with (dati / nome).open(encoding="utf-8", newline="") as handle:
                return {r["id"]: r["proposed_direction"] for r in csv.DictReader(handle, delimiter=";")}
        provincia, regione = versi("province_manifest.csv"), versi("bes_regione_manifest.csv")
        for indicatore in sorted(set(provincia) & set(regione)):
            with self.subTest(indicatore=indicatore):
                self.assertEqual(provincia[indicatore], regione[indicatore])

    def test_le_schede_gemelle_hanno_lo_stesso_verso(self):
        """La prova qui sopra confronta lo stesso id, e l'affollamento delle
        carceri ne ha due: 06POL012 sulle regioni, `contextual`, e 06POL012P
        sulle province, `lower_better`. Stessa misura, due letture, e la prova
        non se ne accorgeva. Qui si confrontano le coppie di
        `taxonomy.PROVINCE_TWINS` fra due schede BES.

        Quattro coppie hanno ancora due versi: restano elencate, e la prova si
        rompe quando una si allinea, cosi' l'elenco non invecchia. 06POL012
        aspetta la prosa riscritta della redazione (`bes__06POL012.md` legge la
        classifica dal valore piu' alto), le altre tre una decisione."""
        import csv
        from pathlib import Path

        from app.taxonomy import PROVINCE_TWINS
        data_dir = Path(__file__).resolve().parents[2] / "app" / "static" / "data"
        def directions(name):
            with (data_dir / name).open(encoding="utf-8", newline="") as handle:
                return {r["id"]: r["proposed_direction"] for r in csv.DictReader(handle, delimiter=";")}
        by_id = {**directions("bes_regione_manifest.csv"), **directions("province_manifest.csv")}
        pending = {"06POL012", "07SIC001", "10AMB018", "10AMB024"}
        pairs = [(r.removeprefix("bes-"), p.removeprefix("bes-"))
                 for r, p in PROVINCE_TWINS.items()
                 if r.startswith("bes-") and p.startswith("bes-")]
        self.assertIn(("06POL012", "06POL012P"), pairs)
        for regional, provincial in pairs:
            with self.subTest(regionale=regional, provinciale=provincial):
                if regional in pending:
                    self.assertNotEqual(by_id[regional], by_id[provincial])
                else:
                    self.assertEqual(by_id[regional], by_id[provincial])

    def test_il_manifest_regionale_e_quello_che_la_pipeline_riscriverebbe(self):
        """I versi del manifest regionale si allineano a mano (D1), e
        `update_bes_regions.py` li riscrive
        da `bes_national_sources.direction_for`. Se i due divergono, la
        prossima rigenerazione rimette il verso di prima senza dirlo."""
        import csv
        from pathlib import Path

        from scripts import bes_national_sources
        manifest = Path(__file__).resolve().parents[2] / "app" / "static" / "data" / "bes_regione_manifest.csv"
        with manifest.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(indicatore=row["id"]):
                self.assertEqual(bes_national_sources.direction_for(row["id"], row["name"]),
                                 row["proposed_direction"])

    def test_discover_provinces_usa_la_stessa_definizione(self):
        from scripts import discover_provinces
        self.assertIs(discover_provinces.NUTS3_PATTERN, province_sources.NUTS3_PATTERN)

    def test_edition_variant_labels_and_units_are_resolved(self):
        indicators = {
            "09PAE009": {"name": "Densità di verde storico"},
            "10AMB018": {"name": "Impermeabilizzazione del suolo da copertura artificiale"},
            "12SER003P": {"name": "Posti letto negli ospedali"},
        }
        self.assertEqual(
            build_province_dataset.resolve_indicator_label(indicators, "09PAE009-N25"),
            "Densità di verde storico",
        )
        self.assertEqual(
            build_province_dataset.resolve_indicator_label(indicators, "10AMB018P"),
            "Impermeabilizzazione del suolo da copertura artificiale",
        )
        self.assertEqual(
            build_province_dataset.resolve_unit_label("10AMB018P", ""), "%",
        )


class ProvinceDatasetSchemaTest(unittest.TestCase):
    DATASET = Path(__file__).resolve().parents[2] / "app" / "static" / "data" / "Assoluti_Provincia.csv"
    EXPECTED_COLUMNS = [
        "idIndicatore", "Territorio", "Tema", "Indicatore", "UDM", "Fonte",
        "Archivio", "Anno", "Livello/Variazione", "Dato", "Benchmark", "Area",
    ]

    def test_schema_when_present(self):
        if not self.DATASET.exists():
            self.skipTest("Assoluti_Provincia.csv not built yet")
        with self.DATASET.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            self.assertEqual(reader.fieldnames, self.EXPECTED_COLUMNS)
            rows = list(reader)
        self.assertTrue(rows)
        # Every row is a provincial Istat observation with an actual value.
        for row in rows:
            self.assertEqual(row["Area"], "Provincia")
            self.assertEqual(row["Fonte"], "Istat")
            self.assertTrue(row["Dato"])
            self.assertTrue(row["Territorio"])
            self.assertNotIn("/", row["Territorio"])


if __name__ == "__main__":
    unittest.main()
