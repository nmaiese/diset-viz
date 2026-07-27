"""Read a legacy Excel `.xls` workbook with nothing but the standard library.

Istat publishes the metadata of the Banca dati territoriale as
`Metainformazione.xls`, a real BIFF8 workbook inside an OLE2 compound file, and
that is the only place where the official definition of a territorial indicator
lives in machine-readable form. `openpyxl`, the one spreadsheet dependency this
project has, reads `.xlsx` and refuses `.xls`.

Adding `xlrd` would have been three lines, and it is the wrong three lines: the
scripts of the chain run on a fresh checkout before any venv exists
(`CLAUDE.md`), so a fetch step that needs a wheel is a fetch step a cloud agent
cannot run. What the job actually needs is small, because the sheet is a plain
grid of strings and numbers: the compound-file container, the shared string
table, and five cell records. Charts, formulas, formatting, dates and encrypted
workbooks are all out of scope and stay out.

    python3 scripts/xls_reader.py file.xls              # i fogli e le dimensioni
    python3 scripts/xls_reader.py file.xls --sheet Metadati --rows 5

What is deliberately NOT supported, so a caller is never quietly wrong:

- **encrypted workbooks** raise, they do not come back empty;
- **formula results** come back as the cached string when the file stores one
  (`STRING` follows `FORMULA`) and as `None` otherwise, never as a formula;
- **dates** come back as the raw Excel serial number, because deciding between
  the 1900 and 1904 epochs needs the format records this reader skips. The
  Istat sheet carries dates in one column nobody reads, so paying for that here
  would be paying for nothing.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF

# BIFF8 record ids. The set is small on purpose: everything not listed here is
# skipped, which is what makes the reader short enough to trust.
BOF = 0x0809
BOUNDSHEET = 0x0085
SST = 0x00FC
CONTINUE = 0x003C
LABELSST = 0x00FD
LABEL = 0x0204
RSTRING = 0x00D6
NUMBER = 0x0203
RK = 0x027E
MULRK = 0x00BD
FORMULA = 0x0006
STRING = 0x0207
FILEPASS = 0x002F


class XlsError(RuntimeError):
    """The file is not a workbook this reader can serve."""


# --------------------------------------------------------------------------
# OLE2 compound file
# --------------------------------------------------------------------------

def _read_stream(data: bytes, name: str) -> bytes:
    """The named stream out of an OLE2 compound file.

    A compound file is a FAT filesystem in a byte string: a header, a sector
    allocation table, a directory of streams, and a second smaller allocation
    table for streams under 4096 bytes. All three are walked here because a
    workbook can land on either side of that cutoff depending on how much prose
    it carries.
    """
    if data[:8] != OLE_MAGIC:
        raise XlsError("not an OLE2 compound file (no magic header)")

    sector_shift, mini_shift = struct.unpack_from("<HH", data, 30)
    sector_size = 1 << sector_shift
    mini_size = 1 << mini_shift
    (
        fat_count,
        dir_start,
        _transaction,
        mini_cutoff,
        mini_fat_start,
        _mini_fat_count,
        difat_start,
        difat_count,
    ) = struct.unpack_from("<IIIIIIII", data, 44)

    def offset(sector: int) -> int:
        return 512 + sector * sector_size

    def sector_uints(sector: int) -> tuple[int, ...]:
        start = offset(sector)
        if start + sector_size > len(data):
            raise XlsError("truncated compound file")
        return struct.unpack_from("<%dI" % (sector_size // 4), data, start)

    # The DIFAT lists the sectors of the FAT: 109 entries inline in the header,
    # the rest chained through sectors of their own.
    difat = list(struct.unpack_from("<109I", data, 76))
    sector = difat_start
    for _ in range(difat_count):
        if sector >= END_OF_CHAIN:
            break
        entries = sector_uints(sector)
        difat.extend(entries[:-1])
        sector = entries[-1]

    fat: list[int] = []
    for fat_sector in difat[:fat_count]:
        if fat_sector >= END_OF_CHAIN:
            continue
        fat.extend(sector_uints(fat_sector))

    def chain(start: int, table: list[int]) -> list[int]:
        out: list[int] = []
        seen: set[int] = set()
        sector = start
        while sector < END_OF_CHAIN:
            if sector in seen or sector >= len(table):
                # A loop means a corrupt file. Stopping beats spinning.
                break
            seen.add(sector)
            out.append(sector)
            sector = table[sector]
        return out

    def read_sectors(start: int, size: int | None = None) -> bytes:
        blob = b"".join(
            data[offset(s):offset(s) + sector_size] for s in chain(start, fat)
        )
        return blob[:size] if size is not None else blob

    directory = read_sectors(dir_start)
    entries = []
    for base in range(0, len(directory) - 127, 128):
        raw = directory[base:base + 128]
        name_len = struct.unpack_from("<H", raw, 64)[0]
        entry_name = raw[:max(0, name_len - 2)].decode("utf-16-le", "replace")
        entry_type = raw[66]
        entry_start, entry_size = struct.unpack_from("<II", raw, 116)
        entries.append((entry_name, entry_type, entry_start, entry_size))

    if not entries:
        raise XlsError("compound file has no directory")

    _root_name, _root_type, root_start, _root_size = entries[0]
    mini_stream = read_sectors(root_start) if root_start < END_OF_CHAIN else b""
    mini_fat: list[int] = []
    if mini_fat_start < END_OF_CHAIN:
        for s in chain(mini_fat_start, fat):
            mini_fat.extend(sector_uints(s))

    def read_mini(start: int, size: int) -> bytes:
        blob = b"".join(
            mini_stream[s * mini_size:(s + 1) * mini_size]
            for s in chain(start, mini_fat)
        )
        return blob[:size]

    for entry_name, entry_type, entry_start, entry_size in entries:
        if entry_type == 2 and entry_name == name:
            if entry_size < mini_cutoff:
                return read_mini(entry_start, entry_size)
            return read_sectors(entry_start, entry_size)

    raise XlsError(
        "no stream %r in the compound file (found %s)"
        % (name, ", ".join(sorted(e[0] for e in entries if e[1] == 2)))
    )


def workbook_stream(data: bytes) -> bytes:
    """The BIFF stream, under either of the two names Excel has used."""
    for name in ("Workbook", "Book"):
        try:
            return _read_stream(data, name)
        except XlsError as error:
            if "no stream" not in str(error):
                raise
    raise XlsError("no Workbook or Book stream: not an Excel file")


# --------------------------------------------------------------------------
# BIFF records
# --------------------------------------------------------------------------

def _records(stream: bytes):
    """(record id, payload, stream offset) for every BIFF record, in order."""
    position = 0
    total = len(stream)
    while position + 4 <= total:
        record_id, length = struct.unpack_from("<HH", stream, position)
        payload = stream[position + 4:position + 4 + length]
        yield record_id, payload, position
        position += 4 + length


def _unicode_string(buffer: bytes, position: int, char_count: int, wide: bool) -> tuple[str, int]:
    if wide:
        end = position + char_count * 2
        return buffer[position:end].decode("utf-16-le", "replace"), end
    end = position + char_count
    return buffer[position:end].decode("cp1252", "replace"), end


def _parse_sst(blocks: list[bytes]) -> list[str]:
    """The shared string table, which is where nearly every cell's text lives.

    The one subtlety worth the comment: a string may be cut in half by the
    record boundary, and the second half restarts with its own compression flag,
    so a 16-bit string can continue as an 8-bit one. Reading that flag as text
    is the classic way this parser goes wrong, and it goes wrong silently, one
    garbled character per continuation.
    """
    if not blocks:
        return []
    _total, unique = struct.unpack_from("<II", blocks[0], 0)
    buffer = blocks[0]
    position = 8
    next_block = 1

    def advance() -> bool:
        nonlocal buffer, position, next_block
        if next_block >= len(blocks):
            return False
        buffer = blocks[next_block]
        next_block += 1
        position = 0
        return True

    strings: list[str] = []
    for _ in range(unique):
        while position >= len(buffer):
            if not advance():
                return strings
        char_count = struct.unpack_from("<H", buffer, position)[0]
        position += 2
        while position >= len(buffer):
            if not advance():
                return strings
        flags = buffer[position]
        position += 1
        wide = bool(flags & 0x01)
        rich_runs = 0
        far_east_bytes = 0
        if flags & 0x08:
            rich_runs = struct.unpack_from("<H", buffer, position)[0]
            position += 2
        if flags & 0x04:
            far_east_bytes = struct.unpack_from("<I", buffer, position)[0]
            position += 4

        pieces: list[str] = []
        remaining = char_count
        while remaining > 0:
            if position >= len(buffer):
                if not advance():
                    break
                wide = bool(buffer[position] & 0x01)
                position += 1
                continue
            available = (len(buffer) - position) // (2 if wide else 1)
            take = min(available, remaining)
            if take <= 0:
                if not advance():
                    break
                wide = bool(buffer[position] & 0x01)
                position += 1
                continue
            piece, position = _unicode_string(buffer, position, take, wide)
            pieces.append(piece)
            remaining -= take

        skip = rich_runs * 4 + far_east_bytes
        while skip > 0:
            if position >= len(buffer):
                if not advance():
                    break
                continue
            step = min(skip, len(buffer) - position)
            position += step
            skip -= step

        strings.append("".join(pieces))
    return strings


def _rk_value(encoded: int) -> float:
    """An RK number: a float squeezed into 32 bits, two ways, times two."""
    divide_by_100 = encoded & 0x01
    if encoded & 0x02:
        value = float(encoded >> 2 if encoded < 0x80000000 else (encoded >> 2) - 0x40000000)
    else:
        value = struct.unpack("<d", struct.pack("<Q", (encoded & 0xFFFFFFFC) << 32))[0]
    return value / 100 if divide_by_100 else value


def read_sheets(data: bytes) -> dict[str, dict[tuple[int, int], object]]:
    """Every sheet of the workbook as {name: {(row, column): value}}.

    Sparse on purpose: the Istat sheet is 476 rows by 18 columns with holes, and
    a dense grid would invent empty strings where the file says nothing at all.
    """
    stream = workbook_stream(data)
    records = list(_records(stream))

    for record_id, _payload, _offset in records:
        if record_id == FILEPASS:
            raise XlsError("the workbook is encrypted, this reader does not decrypt")

    shared: list[str] = []
    for index, (record_id, payload, _offset) in enumerate(records):
        if record_id != SST:
            continue
        blocks = [payload]
        follower = index + 1
        while follower < len(records) and records[follower][0] == CONTINUE:
            blocks.append(records[follower][1])
            follower += 1
        shared = _parse_sst(blocks)
        break

    sheets: list[tuple[str, int]] = []
    for record_id, payload, _offset in records:
        if record_id != BOUNDSHEET:
            continue
        bof_offset = struct.unpack_from("<I", payload, 0)[0]
        name_len = payload[6]
        flags = payload[7]
        name, _ = _unicode_string(payload, 8, name_len, bool(flags & 0x01))
        sheets.append((name, bof_offset))

    by_offset = {offset: index for index, (_id, _payload, offset) in enumerate(records)}

    result: dict[str, dict[tuple[int, int], object]] = {}
    for name, bof_offset in sheets:
        start = by_offset.get(bof_offset)
        if start is None:
            continue
        cells: dict[tuple[int, int], object] = {}
        pending_formula: tuple[int, int] | None = None
        for index in range(start + 1, len(records)):
            record_id, payload, _offset = records[index]
            if record_id == BOF:
                break
            if record_id == LABELSST:
                row, column, _xf, sst_index = struct.unpack_from("<HHHI", payload, 0)
                cells[(row, column)] = shared[sst_index] if sst_index < len(shared) else ""
            elif record_id in (LABEL, RSTRING):
                row, column, _xf, char_count = struct.unpack_from("<HHHH", payload, 0)
                text, _ = _unicode_string(payload, 9, char_count, bool(payload[8] & 0x01))
                cells[(row, column)] = text
            elif record_id == NUMBER:
                row, column, _xf = struct.unpack_from("<HHH", payload, 0)
                cells[(row, column)] = struct.unpack_from("<d", payload, 6)[0]
            elif record_id == RK:
                row, column, _xf, encoded = struct.unpack_from("<HHHI", payload, 0)
                cells[(row, column)] = _rk_value(encoded)
            elif record_id == MULRK:
                row, first_column = struct.unpack_from("<HH", payload, 0)
                count = (len(payload) - 6) // 6
                for step in range(count):
                    _xf, encoded = struct.unpack_from("<HI", payload, 4 + step * 6)
                    cells[(row, first_column + step)] = _rk_value(encoded)
            elif record_id == FORMULA:
                row, column, _xf = struct.unpack_from("<HHH", payload, 0)
                # A formula whose cached result is a string is followed by a
                # STRING record; a numeric one carries its value inline.
                if payload[12:14] == b"\xff\xff" and payload[6] == 0x00:
                    pending_formula = (row, column)
                else:
                    cells[(row, column)] = struct.unpack_from("<d", payload, 6)[0]
                continue
            elif record_id == STRING and pending_formula is not None:
                char_count = struct.unpack_from("<H", payload, 0)[0]
                text, _ = _unicode_string(payload, 3, char_count, bool(payload[2] & 0x01))
                cells[pending_formula] = text
            pending_formula = None
        result[name] = cells
    return result


def sheet_rows(cells: dict[tuple[int, int], object]) -> list[list[object]]:
    """A sparse sheet as a rectangular list of lists, empty cells as ""."""
    if not cells:
        return []
    last_row = max(row for row, _column in cells)
    last_column = max(column for _row, column in cells)
    return [
        [cells.get((row, column), "") for column in range(last_column + 1)]
        for row in range(last_row + 1)
    ]


def read_file(path) -> dict[str, dict[tuple[int, int], object]]:
    return read_sheets(Path(path).read_bytes())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path", type=Path)
    parser.add_argument("--sheet", help="stampa le prime righe di un foglio")
    parser.add_argument("--rows", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        sheets = read_file(args.path)
    except XlsError as error:
        print(f"errore: {error}", file=sys.stderr)
        return 1

    if not args.sheet:
        for name, cells in sheets.items():
            rows = sheet_rows(cells)
            columns = len(rows[0]) if rows else 0
            print(f"{name}\t{len(rows)} righe\t{columns} colonne")
        return 0

    if args.sheet not in sheets:
        print(f"nessun foglio {args.sheet!r}", file=sys.stderr)
        return 1
    for index, row in enumerate(sheet_rows(sheets[args.sheet])[:args.rows]):
        print(index, [str(value)[:60] for value in row])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
