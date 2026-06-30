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

from scripts import istat_sdmx, province_sources
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


class ProvinceDatasetSchemaTest(unittest.TestCase):
    DATASET = Path(__file__).resolve().parents[1] / "app" / "static" / "data" / "Assoluti_Provincia.csv"
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
