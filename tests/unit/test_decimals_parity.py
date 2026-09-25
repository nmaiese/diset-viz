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

from app import it_numbers, seo_titles
from app.design import numfmt

V1_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "js" / "v1.js"

# Le sole forme di riga che la traduzione accetta.
_ASSIGN = re.compile(r"var m = Math\.abs\(v\);")
_IF = re.compile(r"if \(m (===|>=|<) ([\d.]+)\) return (\d+);")
_TERNARY = re.compile(r"return m (<|>=) ([\d.]+) \? (\d+) : (\d+);")
_OPS = {"===": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b}

VALUES = (0, 0.0, -0.0, 0.00044, 0.001, 0.004, 0.0095, 0.01, 0.0107, 0.137, 0.999, 1, 1.5, 9.99, 10, 10.5,
          99.9, 100, 116, 34343, -0.004, -2.6, -64.7, -150)


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
        """Zero, un millesimo, un centesimo, uno, dieci, cento: la tabella che
        la regola promette. Sotto un centesimo i decimali arrivano alla prima
        cifra significativa, fino a quattro."""
        attesi = {0: 0, 0.00044: 4, 0.001: 3, 0.0045: 3, 0.01: 2, 0.137: 2, 1: 1, 9.99: 1, 10: 1, 99.9: 1,
                  100: 0}
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

    def test_le_cifre_delle_pagine_territorio(self):
        """Le cifre che la pagina provincia scriveva coi decimali della fonte, e
        la scheda con quelli della grandezza: il reddito di Milano era
        "34.885,3" da una parte e "34.885" dall'altra. Gli euro sopra cento
        senza decimali, le percentuali sotto l'uno con due, gli indici piccoli
        con due e mai a zero."""
        attese = {34885.3: "34.885", 26348.5: "26.349", 128.8: "129", 31.88: "31,9",
                  6: "6,0", 0.3: "0,30", 0.137: "0,14", 0.0107: "0,01", -5367.2: "-5.367",
                  0.0044917107519759: "0,004", 0.000439952532688906: "0,0004"}
        for valore, scritta in attese.items():
            with self.subTest(valore=valore):
                self.assertEqual(numfmt.text(valore), scritta)

    def test_la_variazione_ha_una_forma_sola(self):
        """`change_text` e' il testo del filtro `delta`: la pagina, il suo
        gemello Markdown e il template di ripiego scrivono la stessa
        variazione, col segno e con "invariato" quando arrotondata fa zero."""
        for valore in (5024.4, -1, 1.1, -0.7, 0.1, 0.004, -0.004, 0, 0.0005):
            with self.subTest(valore=valore):
                html = str(numfmt.delta(valore))
                testo = re.sub(r"<[^>]+>", "", html)
                self.assertEqual(numfmt.change_text(valore), testo)
        self.assertEqual(numfmt.change_text(5024.4), "+5.024")
        self.assertEqual(numfmt.change_text(-0.7), "-0,70")
        # Coi decimali della sua grandezza una variazione diversa da zero non
        # e' mai "invariato": lo e' solo coi decimali di un'altra cifra.
        self.assertEqual(numfmt.change_text(0.004), "+0,004")
        self.assertEqual(numfmt.change_text(0.004, 2), "invariato")
        self.assertEqual(numfmt.change_text(0.0004, 3), "invariato")
        self.assertEqual(numfmt.change_text(0.004, 3), "+0,004")

    def test_il_pareggio_va_per_eccesso_come_nel_browser(self):
        """Il formato di Python arrotonda il cinque al pari e sul binario,
        `Intl.NumberFormat` di v1.js lo porta in su partendo dalla cifra come si
        scrive. La retribuzione di Milano, 26348,5, era "26.348" sulla pagina e
        "26.349" sulla mappa appena la si ridisegnava. Le cifre attese sono
        quelle di `Intl.NumberFormat("it-IT")` con gli stessi decimali: pagina,
        title e numeri all'italiana arrotondano allo stesso modo."""
        attese = {26348.5: "26.349", 754.5: "755", 13.25: "13,3", 1.45: "1,5", 0.285: "0,29",
                  0.125: "0,13", -2.5: "-2,5", -754.5: "-755"}
        for valore, scritta in attese.items():
            with self.subTest(valore=valore):
                self.assertEqual(numfmt.text(valore), scritta)
                self.assertEqual(seo_titles.format_number(valore), scritta)
                self.assertEqual(it_numbers.number(valore, numfmt.magnitude_decimals(valore)), scritta)
        self.assertEqual(numfmt.change_text(2778.5), "+2.779")
        # Coi decimali dati: 1,005 e 2,675 in binario stanno appena sotto il
        # cinque, e il formato di Python dava "1,00" e "2,67".
        self.assertEqual(it_numbers.number(1.005, 2), "1,01")
        self.assertEqual(it_numbers.number(2.675, 2), "2,68")
        self.assertEqual(numfmt.text(2.675, 2), "2,68")
        self.assertEqual(it_numbers.number(2.5, 0), "3")
        self.assertEqual(it_numbers.change(0.05), "+0,1")

    def test_nessuna_seconda_regola_dei_decimali(self):
        """I decimali della fonte (`bes_data.source_decimals`) erano la seconda
        regola: la provincia li leggeva dalla riga, il Markdown ci ricadeva a un
        decimale fisso se il campo mancava. Tolta la regola, nessuno deve
        rileggerla, ne' le pagine territorio ne' i loro gemelli."""
        from app import bes_data

        self.assertFalse(hasattr(bes_data, "source_decimals"))
        radice = Path(__file__).resolve().parents[2] / "app"
        for relativo in ("province_profile.py", "agent_discovery.py", "design/pages/provincia.py",
                         "design/pages/regione.py", "templates/v1/provincia.html",
                         "templates/v1/regione.html", "templates/province_page.html",
                         "templates/region_page.html"):
            sorgente = (radice / relativo).read_text(encoding="utf-8")
            with self.subTest(file=relativo):
                self.assertNotIn("source_decimals", sorgente)
                self.assertNotRegex(sorgente, r"""\bi\.decimals\b|\[["']decimals["']\]|get\(["']decimals["']""")
                # Il ripiego della regione scriveva il valore con `it_num`, un
                # decimale fisso: "28.154,3 euro" e "0,0". Il punteggio
                # (`p.score | it_num`) ha un decimale per regola, e resta.
                self.assertNotRegex(sorgente, r"\b(i|voce|row|r)\.value\s*\|\s*it_num\b")


if __name__ == "__main__":
    unittest.main()
