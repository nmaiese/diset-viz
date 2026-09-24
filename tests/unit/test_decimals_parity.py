"""I decimali di una cifra: una regola, tre copie, una prova che le tiene uguali.

La regola vive in `seo_titles._decimals` (i title), in
`numfmt.magnitude_decimals` (la pagina della 1.0) e in `decimals` di
`app/static/js/v1.js` (il valore che la mappa scrive al passaggio). Nessun test
leggeva `v1.js`: lo zero e' uscito "0,00" nei title e sarebbe potuto uscire
diverso fra server e browser senza che niente fallisse.

La copia JavaScript non si esegue, si legge: il corpo di `function decimals` si
traduce riga per riga in soglie, e una riga di forma diversa fa fallire la
prova. E' apposta: chi cambia la funzione deve passare di qui.
"""
import re
import unittest
from pathlib import Path

from app import seo_titles
from app.design import numfmt

V1_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "js" / "v1.js"

# Le sole forme di riga che la traduzione accetta.
_ASSIGN = re.compile(r"var m = Math\.abs\(v\);")
_IF = re.compile(r"if \(m (===|>=|<) ([\d.]+)\) return (\d+);")
_TERNARY = re.compile(r"return m (<|>=) ([\d.]+) \? (\d+) : (\d+);")
_OPS = {"===": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b}

VALUES = (0, 0.0, -0.0, 0.004, 0.137, 0.999, 1, 1.5, 9.99, 10, 10.5, 99.9, 100, 116, 34343, -2.6, -64.7, -150)


def js_decimals():
    """La funzione `decimals` di v1.js tradotta in Python, riga per riga."""
    source = V1_JS.read_text(encoding="utf-8")
    body = re.search(r"function decimals\(v\) \{(.*?)\n  \}", source, re.DOTALL)
    if body is None:
        raise AssertionError("function decimals(v) non trovata in v1.js")
    steps = []
    for line in (raw.strip() for raw in body.group(1).splitlines()):
        if not line or _ASSIGN.fullmatch(line):
            continue
        guard = _IF.fullmatch(line)
        if guard:
            op, bound, result = guard.groups()
            steps.append((_OPS[op], float(bound), int(result), None))
            continue
        ternary = _TERNARY.fullmatch(line)
        if ternary:
            op, bound, yes, no = ternary.groups()
            steps.append((_OPS[op], float(bound), int(yes), int(no)))
            continue
        raise AssertionError(f"riga di v1.js decimals() che la prova non sa leggere: {line!r}")

    def decimals(value):
        magnitude = abs(float(value))
        for op, bound, yes, no in steps:
            if op(magnitude, bound):
                return yes
            if no is not None:
                return no
        raise AssertionError(f"decimals() di v1.js non restituisce niente per {value}")

    return decimals


class ParitaDeiDecimaliTest(unittest.TestCase):
    def test_le_tre_copie_concordano(self):
        js = js_decimals()
        for value in VALUES:
            with self.subTest(valore=value):
                python = seo_titles._decimals(value)
                self.assertEqual(numfmt.magnitude_decimals(value), python)
                self.assertEqual(js(value), python)

    def test_le_soglie_sono_quelle_della_regola(self):
        """Zero, uno, dieci, cento: la tabella che la regola promette."""
        attesi = {0: 0, 0.137: 2, 1: 1, 9.99: 1, 10: 1, 99.9: 1, 100: 0}
        js = js_decimals()
        for value, decimali in attesi.items():
            with self.subTest(valore=value):
                self.assertEqual(seo_titles._decimals(value), decimali)
                self.assertEqual(js(value), decimali)

    def test_lo_zero_si_scrive_zero_ovunque(self):
        self.assertEqual(seo_titles.format_number(0), "0")
        self.assertEqual(seo_titles.format_number(-0.0), "0")
        self.assertEqual(numfmt.text(0), "0")
        self.assertEqual(numfmt.text(-0.0), "0")

    def test_una_colonna_a_mediana_zero_tiene_i_suoi_decimali(self):
        """Lo zero conta per la cifra da sola: una colonna con meta' righe a
        zero non deve arrotondare a intero anche le altre."""
        self.assertEqual(numfmt.column_decimals([0, 0, 0, 0.4, 0.7]), 2)
        self.assertEqual(numfmt.column_decimals([0.2, 0.3, 0.5]), 2)


if __name__ == "__main__":
    unittest.main()
