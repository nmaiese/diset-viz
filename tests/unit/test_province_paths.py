"""I contorni delle province per le mappe della 1.0 (design/v1/tools/province_map.py)."""
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class IContorniDelleProvince(unittest.TestCase):
    def test_ogni_provincia_del_bes_ha_il_suo_tracciato(self):
        """Con le coordinate arrotondate un anello minuscolo sparisce: Trieste,
        Prato e Monza stanno in pochi pixel, e una provincia senza tracciato e'
        un buco nella mappa che nessun errore segnala."""
        paths = json.loads((ROOT / "app/design/province_paths.json").read_text(encoding="utf-8"))
        with (ROOT / "app/static/data/province_codes.csv").open(encoding="utf-8", newline="") as handle:
            keys = {row["province_key"] for row in csv.DictReader(handle, delimiter=";")}
        self.assertEqual(len(keys), 107)
        self.assertEqual(set(paths), keys)
        for key, d in paths.items():
            with self.subTest(provincia=key):
                self.assertRegex(d, r"^M[\d.]+[ -][\d.]+l")
                self.assertGreaterEqual(len(re.findall(r"-?\d+(?:\.\d+)?", d)), 6)


class IlParserDeiTracciati(unittest.TestCase):
    def test_legge_assoluti_e_relativi_e_torna_all_inizio_dopo_z(self):
        """Le regioni sono scritte con M/L assoluti, le province con m/l
        relativi. Dopo z il punto corrente torna all'inizio del sottotracciato:
        una m relativa che segue parte da li', non dall'ultimo vertice."""
        from app.design import charts

        self.assertEqual(charts.path_rings("M1,2L3,4L5,6Z"), [[(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]])
        rings = charts.path_rings("M0 0l10 0 0 10zm5 5l1 0 0 1z")
        self.assertEqual(rings[0], [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
        self.assertEqual(rings[1][0], (5.0, 5.0))


if __name__ == "__main__":
    unittest.main()
