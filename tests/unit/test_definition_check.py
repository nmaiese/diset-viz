"""The guard that reads an article against the source's own definition.

Three layers, tested separately because they fail in different ways:

1. `scripts/xls_reader` walks an OLE2 container and a BIFF8 stream by hand. A
   parser that gets a byte offset wrong does not raise, it returns plausible
   nonsense, so the container is built here from scratch and read back.
2. `scripts/fetch_definitions` turns Istat's sheet into the committed CSV. What
   matters is the joins: the zero padding, the provincial suffixes, and the
   header lookup that must not silently slide by one column.
3. `scripts/definition_check` compares prose to that CSV. Every case is
   synthetic except the two anchored on the real catalogue, because a check
   calibrated on today's articles would pass forever by construction.
"""

from __future__ import annotations

import csv
import io
import struct
import tempfile
import unittest
from pathlib import Path

from scripts import definition_check, fetch_definitions, xls_reader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# a minimal .xls, built here so the reader has something real to walk
# ---------------------------------------------------------------------------

SECTOR = 512
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD
FREESECT = 0xFFFFFFFF


def _biff_record(record_id: int, payload: bytes) -> bytes:
    return struct.pack("<HH", record_id, len(payload)) + payload


def _sst(strings: list[str]) -> bytes:
    payload = struct.pack("<II", len(strings), len(strings))
    for text in strings:
        payload += struct.pack("<H", len(text)) + b"\x01" + text.encode("utf-16-le")
    return _biff_record(xls_reader.SST, payload)


def _workbook_stream(sheet_name: str, rows: list[list[str]]) -> bytes:
    """A one-sheet BIFF8 stream: globals, then the sheet substream."""
    strings: list[str] = []
    index_of: dict[str, int] = {}
    for row in rows:
        for cell in row:
            if isinstance(cell, str) and cell not in index_of:
                index_of[cell] = len(strings)
                strings.append(cell)

    globals_head = _biff_record(xls_reader.BOF, struct.pack("<HH", 0x0600, 0x0005) + b"\x00" * 12)
    sst = _sst(strings)
    # BOUNDSHEET carries the byte offset of the sheet's BOF, which is only known
    # once the globals substream has its final length: build it, measure, patch.
    name = sheet_name.encode("utf-16-le")
    boundsheet_body = struct.pack("<IH", 0, 0x0000) + bytes([len(sheet_name), 0x01]) + name
    boundsheet = _biff_record(xls_reader.BOUNDSHEET, boundsheet_body)
    eof = _biff_record(0x000A, b"")
    globals_length = len(globals_head) + len(sst) + len(boundsheet) + len(eof)
    boundsheet = _biff_record(
        xls_reader.BOUNDSHEET,
        struct.pack("<IH", globals_length, 0x0000) + bytes([len(sheet_name), 0x01]) + name,
    )

    sheet = _biff_record(xls_reader.BOF, struct.pack("<HH", 0x0600, 0x0010) + b"\x00" * 12)
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            if isinstance(cell, str):
                sheet += _biff_record(
                    xls_reader.LABELSST,
                    struct.pack("<HHHI", row_index, column_index, 0, index_of[cell]),
                )
            elif isinstance(cell, (int, float)):
                sheet += _biff_record(
                    xls_reader.NUMBER,
                    struct.pack("<HHH", row_index, column_index, 0) + struct.pack("<d", float(cell)),
                )
    sheet += eof
    return globals_head + sst + boundsheet + eof + sheet


def _directory_entry(name: str, entry_type: int, start: int, size: int) -> bytes:
    raw = name.encode("utf-16-le") + b"\x00\x00"
    entry = raw.ljust(64, b"\x00")
    entry += struct.pack("<H", len(raw))
    entry += bytes([entry_type, 0x01])
    entry += struct.pack("<III", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    entry += b"\x00" * 16          # CLSID
    entry += b"\x00" * 4           # state bits
    entry += b"\x00" * 16          # timestamps
    entry += struct.pack("<II", start, size)
    return entry.ljust(128, b"\x00")


def build_xls(sheet_name: str, rows: list[list[str]]) -> bytes:
    """An OLE2 compound file whose only stream is a BIFF8 workbook."""
    stream = _workbook_stream(sheet_name, rows)
    # Keep the workbook above the mini-stream cutoff so it lives in ordinary
    # sectors, which is where a real Istat workbook lives too.
    stream = stream.ljust(5000, b"\x00")
    data_sectors = (len(stream) + SECTOR - 1) // SECTOR
    payload = stream.ljust(data_sectors * SECTOR, b"\x00")

    directory_sector = data_sectors
    fat_sector = data_sectors + 1
    total_sectors = data_sectors + 2

    directory = (
        _directory_entry("Root Entry", 5, ENDOFCHAIN, 0)
        + _directory_entry("Workbook", 2, 0, len(stream))
    ).ljust(SECTOR, b"\x00")

    fat = [FREESECT] * (SECTOR // 4)
    for index in range(data_sectors):
        fat[index] = index + 1 if index + 1 < data_sectors else ENDOFCHAIN
    fat[directory_sector] = ENDOFCHAIN
    fat[fat_sector] = FATSECT
    fat_bytes = b"".join(struct.pack("<I", value) for value in fat)

    header = bytearray(b"\x00" * SECTOR)
    header[0:8] = xls_reader.OLE_MAGIC
    struct.pack_into("<HH", header, 24, 0x003E, 0x0003)
    struct.pack_into("<H", header, 28, 0xFFFE)
    struct.pack_into("<HH", header, 30, 9, 6)
    struct.pack_into("<I", header, 44, 1)                    # FAT sectors
    struct.pack_into("<I", header, 48, directory_sector)
    struct.pack_into("<I", header, 56, 4096)                 # mini stream cutoff
    struct.pack_into("<I", header, 60, ENDOFCHAIN)           # first mini FAT
    struct.pack_into("<I", header, 64, 0)
    struct.pack_into("<I", header, 68, ENDOFCHAIN)           # first DIFAT
    struct.pack_into("<I", header, 72, 0)
    for slot in range(109):
        struct.pack_into("<I", header, 76 + slot * 4, FREESECT)
    struct.pack_into("<I", header, 76, fat_sector)

    body = bytearray(payload)
    body += directory
    body += fat_bytes
    assert len(body) == total_sectors * SECTOR
    return bytes(header) + bytes(body)


class XlsReader(unittest.TestCase):
    def test_reads_back_a_workbook_it_did_not_write(self):
        rows = [["CODICE", "INDICATORE"], ["060", "Interruzioni"], ["", 42.5]]
        sheets = xls_reader.read_sheets(build_xls("Metadati", rows))
        self.assertEqual(list(sheets), ["Metadati"])
        grid = xls_reader.sheet_rows(sheets["Metadati"])
        self.assertEqual(grid[0], ["CODICE", "INDICATORE"])
        self.assertEqual(grid[1], ["060", "Interruzioni"])
        self.assertEqual(grid[2][1], 42.5)

    def test_a_string_split_across_a_continue_comes_back_whole(self):
        """The one place this parser can be wrong without looking wrong.

        A CONTINUE restarts with its own compression flag, so the byte that
        says "the rest is 8-bit" is not text. Reading it as text costs one
        garbled character per continuation and nothing else, which is exactly
        the kind of defect that ships.
        """
        text = "definizione lunghissima " * 3
        head = struct.pack("<II", 1, 1) + struct.pack("<H", len(text)) + b"\x01"
        cut = 20
        head += text[:cut].encode("utf-16-le")
        continuation = b"\x01" + text[cut:].encode("utf-16-le")
        self.assertEqual(xls_reader._parse_sst([head, continuation]), [text])

    def test_a_continuation_may_switch_to_one_byte_characters(self):
        text = "abcdefghijklmnop"
        head = struct.pack("<II", 1, 1) + struct.pack("<H", len(text)) + b"\x01"
        head += text[:4].encode("utf-16-le")
        continuation = b"\x00" + text[4:].encode("cp1252")
        self.assertEqual(xls_reader._parse_sst([head, continuation]), [text])

    def test_rk_numbers_in_all_four_shapes(self):
        """Two low bits select the encoding, and both of them can be wrong quietly."""
        self.assertAlmostEqual(xls_reader._rk_value(0x3FF00000), 1.0)              # float
        self.assertAlmostEqual(xls_reader._rk_value(0x3FF00001), 0.01)             # float / 100
        self.assertAlmostEqual(xls_reader._rk_value((100 << 2) | 0x02), 100.0)     # int
        self.assertAlmostEqual(xls_reader._rk_value((100 << 2) | 0x03), 1.0)       # int / 100
        self.assertAlmostEqual(xls_reader._rk_value(0xFFFFFFFE), -1.0)             # negative int

    def test_a_file_that_is_not_a_workbook_raises_instead_of_returning_nothing(self):
        with self.assertRaises(xls_reader.XlsError):
            xls_reader.read_sheets(b"PK\x03\x04 this is an xlsx")


class ParseSheet(unittest.TestCase):
    HEADER = [
        "CODICE", "INDICATORE", "DEFINIZIONE TECNICA INDICATORE",
        "DATI DI BASE ASSOCIATI", "AMBITO TERRITORIALE",
        "ANNO INIZIALE", "ANNO FINALE", "PERIODICITA'", "FONTI", "NOTE",
    ]

    def _parse(self, *rows):
        return fetch_definitions.parse_sheet([["Titolo"], [], self.HEADER, *rows])

    def test_the_zero_padding_is_stripped_so_the_join_with_the_archive_works(self):
        rows = self._parse(["060", "Interruzioni", "Frequenza", "", "REGIONI",
                            "1997", "2023", "Annuale", "Fonte: Istat", ""])
        self.assertEqual(rows[0]["id"], "60")

    def test_provincial_and_municipal_cuts_are_dropped_not_renamed(self):
        rows = self._parse(
            ["060", "Interruzioni", "Frequenza", "", "REGIONI", "", "", "", "", ""],
            ["060_P", "Interruzioni", "Frequenza provinciale", "", "PROVINCE", "", "", "", "", ""],
            ["472_C", "PM10", "Concentrazione", "", "COMUNI", "", "", "", "", ""],
        )
        self.assertEqual([row["id"] for row in rows], ["60"])

    def test_a_numeric_code_arrives_as_a_float_and_still_joins(self):
        rows = self._parse(["552.0", "PIL", "Prodotto interno lordo", "", "REGIONI",
                            "1995.0", "2024.0", "Annuale", "", ""])
        self.assertEqual(rows[0]["id"], "552")
        self.assertEqual(rows[0]["anno_iniziale"], "1995")
        self.assertEqual(rows[0]["anno_finale"], "2024")

    def test_columns_are_found_by_label_so_a_reordered_sheet_stays_correct(self):
        shuffled = ["INDICATORE", "CODICE", "NOTE", "DEFINIZIONE TECNICA INDICATORE"]
        rows = fetch_definitions.parse_sheet(
            [shuffled, ["Interruzioni", "060", "una nota", "Frequenza"]]
        )
        self.assertEqual(rows[0]["id"], "60")
        self.assertEqual(rows[0]["indicatore"], "Interruzioni")
        self.assertEqual(rows[0]["definizione"], "Frequenza")
        self.assertEqual(rows[0]["note"], "una nota")

    def test_a_sheet_without_the_expected_header_raises(self):
        with self.assertRaises(xls_reader.XlsError):
            fetch_definitions.parse_sheet([["A", "B"], ["1", "2"]])

    def test_the_lost_apostrophes_are_restored(self):
        rows = self._parse(["060", "X", "riguardanti l¿attività e ¿il resto¿", "",
                            "REGIONI", "", "", "", "", ""])
        self.assertEqual(rows[0]["definizione"], 'riguardanti l\'attività e "il resto"')


class Stemming(unittest.TestCase):
    def test_singular_and_plural_are_the_same_token(self):
        for singular, plural in (
            ("impresa", "imprese"), ("addetto", "addetti"),
            ("titolare", "titolari"), ("persona", "persone"),
            ("classe", "classi"), ("occupate", "occupazione"),
        ):
            self.assertEqual(
                definition_check.stem(singular), definition_check.stem(plural),
                f"{singular} / {plural}",
            )

    def test_accents_do_not_split_a_word_in_two(self):
        self.assertEqual(definition_check.stem("attività"), definition_check.stem("attivita"))

    def test_scaffolding_words_are_not_content(self):
        terms = definition_check.content_terms(
            "Percentuale di titolari donne sul totale dei titolari"
        )
        self.assertIn("titolari", terms)
        self.assertNotIn("Percentuale", terms)
        self.assertNotIn("totale", terms)


class BaseAndQualifiers(unittest.TestCase):
    def test_the_denominator_is_pulled_out_of_the_definition(self):
        self.assertEqual(
            definition_check.base_phrases(
                "Titolari di imprese individuali donne in percentuale sul totale "
                "dei titolari di imprese individuali iscritti nei registri"
            ),
            ["titolari di imprese individuali iscritti nei registri"],
        )

    def test_a_rate_per_hundred_counts_as_a_base(self):
        self.assertTrue(definition_check.base_phrases("Ingressi per 100 abitanti"))

    def test_a_definition_with_no_denominator_yields_none(self):
        self.assertEqual(definition_check.base_phrases("Numero di posti letto"), [])

    def test_age_bands_and_size_thresholds_are_qualifiers(self):
        found = definition_check.qualifiers(
            "Persone occupate in età 15-64 anni delle imprese con più di dieci addetti"
        )
        self.assertIn("15-64 anni", found)
        self.assertIn("con più di dieci addetti", found)


class Contradictions(unittest.TestCase):
    def test_almeno_and_piu_di_over_the_same_number_are_different_populations(self):
        found = definition_check.contradictions(
            "Percentuale di addetti delle imprese (con più di dieci addetti)",
            "Le imprese italiane con almeno dieci addetti usano internet.",
        )
        self.assertEqual(len(found), 1)
        self.assertIn("almeno", found[0])

    def test_it_is_reported_even_when_the_article_also_says_it_right(self):
        """The defect found on ter-72 was one wrong sentence among three right ones.

        An article that draws the perimeter both ways still has a false
        sentence, and it is the one in the lead that the reader meets first.
        """
        found = definition_check.contradictions(
            "Percentuale di addetti delle imprese (con più di dieci addetti)",
            "Le imprese con almeno dieci addetti. Le imprese con più di dieci addetti.",
        )
        self.assertEqual(len(found), 1)

    def test_the_same_edge_is_not_a_contradiction(self):
        self.assertEqual(
            definition_check.contradictions(
                "imprese con più di dieci addetti",
                "le imprese con più di dieci addetti",
            ),
            [],
        )

    def test_a_different_number_is_not_a_contradiction(self):
        self.assertEqual(
            definition_check.contradictions(
                "imprese con più di dieci addetti",
                "le imprese con almeno cinquanta addetti",
            ),
            [],
        )

    def test_the_wrong_age_band_is_flagged(self):
        found = definition_check.contradictions(
            "Persone occupate in età 15-64 anni",
            "Il tasso di occupazione fra i 20 e i 64 anni: la quota 20-64 anni sale.",
        )
        self.assertEqual(len(found), 1)
        self.assertIn("15-64", found[0])

    def test_naming_another_indicator_band_alongside_the_right_one_is_not(self):
        self.assertEqual(
            definition_check.contradictions(
                "Persone occupate in età 15-64 anni",
                "La quota 15-64 anni, contro il tasso 20-64 anni dell'altro indicatore.",
            ),
            [],
        )


def _entry(definizione, lead="Un lead.", limiti="Dei limiti."):
    return {
        "lead": lead,
        "level": "regione",
        "vintage": 2023,
        "fonti": [],
        "sections": [
            {"role": "definizione", "h": None, "body": definizione},
            {"role": "quadro", "h": None, "body": "Il quadro."},
            {"role": "dinamica", "h": None, "body": "La dinamica."},
            {"role": "limiti", "h": None, "body": limiti},
        ],
    }


class CheckEntry(unittest.TestCase):
    SOURCE = {
        "indicatore": "Imprenditorialità femminile",
        "definizione": (
            "Titolari di imprese individuali donne in percentuale sul totale dei "
            "titolari di imprese individuali iscritti nei registri delle Camere "
            "di Commercio italiane"
        ),
    }

    def test_the_real_ter_402_defect_is_caught(self):
        """The article calls them firms; the source counts sole proprietors."""
        row = definition_check.check_entry(
            "ter-402",
            _entry("Questo indicatore misura la quota di imprese a guida femminile."),
            self.SOURCE,
        )
        self.assertIn("base", row["hits"])
        self.assertIn("titolari", row["hits"]["base"][0])

    def test_an_article_that_names_the_denominator_passes(self):
        row = definition_check.check_entry(
            "ter-402",
            _entry(
                "Conta le titolari donne di imprese individuali sul totale dei "
                "titolari di imprese individuali iscritti ai registri delle "
                "Camere di Commercio."
            ),
            self.SOURCE,
        )
        self.assertNotIn("base", row["hits"])
        self.assertNotIn("termini", row["hits"])

    def test_a_family_without_a_metadata_sheet_says_so_instead_of_passing(self):
        row = definition_check.check_entry("bes-12SER003", _entry("Qualunque cosa."), None)
        self.assertEqual(list(row["hits"]), ["scoperto"])

    def test_scoperto_is_not_counted_as_clean(self):
        summary = definition_check.summarize(
            [definition_check.check_entry("bes-1", _entry("X"), None)]
        )
        self.assertEqual(summary["covered"], 0)
        self.assertEqual(summary["clean"], 0)

    def test_a_missing_threshold_is_a_signal_but_a_present_one_is_not(self):
        source = {"indicatore": "X", "definizione": "Disoccupati da oltre 12 mesi"}
        silent = definition_check.check_entry("ter-179", _entry("Chi cerca lavoro."), source)
        self.assertIn("soglia", silent["hits"])
        explicit = definition_check.check_entry(
            "ter-179", _entry("Chi cerca lavoro da oltre 12 mesi."), source
        )
        self.assertNotIn("soglia", explicit["hits"])

    def test_the_whole_article_counts_for_terms_not_only_the_definition(self):
        """`ter-402` repeated its error in `limiti`, so `limiti` is read too."""
        source = {"indicatore": "X", "definizione": "Ingressi a eventi di spettacolo cinematografico"}
        row = definition_check.check_entry(
            "ter-611",
            _entry("Una definizione vaga.", limiti="Conta gli ingressi al cinema, non gli spettatori."),
            source,
        )
        self.assertNotIn("termini", row["hits"])


class AgainstTheRealCatalogue(unittest.TestCase):
    """Two anchors on committed data. Everything else here is synthetic."""

    @classmethod
    def setUpClass(cls):
        cls.definitions = fetch_definitions.load_definitions()

    def test_the_committed_csv_exists_and_carries_the_declared_columns(self):
        self.assertTrue(fetch_definitions.OUTPUT_PATH.exists(),
                        "run python3 scripts/fetch_definitions.py")
        with fetch_definitions.OUTPUT_PATH.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            self.assertEqual(reader.fieldnames, fetch_definitions.COLUMNS)

    def test_it_covers_most_of_the_territorial_archive(self):
        """A join that silently stops matching is the failure mode here.

        The uncovered ids are real: locally curated series (the 9xx block) and
        rows Istat has dropped from the sheet. What must not happen is the
        coverage falling off a cliff because the padding, the float suffix or
        the header lookup changed under us.
        """
        archive = PROJECT_ROOT / "app" / "static" / "data" / "Assoluti_Regione.csv"
        with archive.open(encoding="utf-8", newline="") as handle:
            ids = {row["idIndicatore"] for row in csv.DictReader(handle, delimiter=";")}
        covered = ids & set(self.definitions)
        self.assertGreater(len(covered) / len(ids), 0.85, "the join has come apart")

    def test_the_source_still_defines_imprenditorialita_femminile_the_narrow_way(self):
        """The one definition this whole guard was built around.

        If Istat ever broadens it to all female-led firms, the article that says
        so stops being wrong and this test is the place that finds out.
        """
        row = self.definitions.get("402")
        self.assertIsNotNone(row, "id 402 is not in the definitions CSV")
        self.assertIn("titolari di imprese individuali", row["definizione"].lower())


class CommandLine(unittest.TestCase):
    def test_show_accepts_the_url_form_the_prompts_are_written_in(self):
        with tempfile.TemporaryDirectory() as folder:
            texts = Path(folder) / "texts.json"
            texts.write_text(
                '{"402": %s}' % __import__("json").dumps(_entry("Le imprese femminili."),
                                                         ensure_ascii=False),
                encoding="utf-8",
            )
            buffer = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(buffer):
                code = definition_check.main(["--show", "ter-402", "--texts", str(texts)])
            self.assertEqual(code, 0)
            self.assertIn("ter-402", buffer.getvalue())

    def test_an_unknown_code_fails_loudly(self):
        with tempfile.TemporaryDirectory() as folder:
            texts = Path(folder) / "texts.json"
            texts.write_text("{}", encoding="utf-8")
            buffer = io.StringIO()
            import contextlib
            with contextlib.redirect_stderr(buffer):
                code = definition_check.main(["--show", "ter-999999", "--texts", str(texts)])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
