import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


JS = Path(__file__).resolve().parents[2] / "app/static/js/v1.js"


@unittest.skipUnless(shutil.which("node"), "node non disponibile")
class V1DistributionFase1a(unittest.TestCase):
    def test_year_update_recomputes_gap_median_and_band(self):
        source = JS.read_text(encoding="utf-8")
        block = re.search(r"/\* distribution:start \*/(.*?)/\* distribution:end \*/", source, re.S).group(1)
        script = block + r'''
        function fmt(v) { return Number(v).toFixed(1); }
        function withUnit(v, unit) { return fmt(v) + " " + unit; }
        var els = {"median-value": {}, "central-band": {}, "gap-value": {}, distribution: {}};
        var mod = {querySelector: function (selector) { return els[selector.match(/data-kpi="([^"]+)/)[1]]; }};
        paintDistribution(mod, [1, 2, 3, 4, 100], "%");
        var first = Object.fromEntries(Object.keys(els).map(function (key) { return [key, els[key].textContent]; }));
        paintDistribution(mod, [10, 20, 30, 40, 50], "%");
        var second = Object.fromEntries(Object.keys(els).map(function (key) { return [key, els[key].textContent]; }));
        paintDistribution(mod, [], "%");
        var empty = Object.fromEntries(Object.keys(els).map(function (key) { return [key, els[key].textContent]; }));
        empty.hidden = els.distribution.hidden;
        process.stdout.write(JSON.stringify({first: first, second: second, empty: empty}));
        '''
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(result.stdout)
        self.assertEqual(out["first"]["gap-value"], "99.0 %")
        self.assertEqual(out["first"]["median-value"], "3.0 %")
        self.assertEqual(out["first"]["central-band"], "da 2.0 % a 4.0 %")
        self.assertEqual(out["second"]["gap-value"], "40.0 %")
        self.assertEqual(out["second"]["median-value"], "30.0 %")
        self.assertEqual(out["second"]["central-band"], "da 20.0 % a 40.0 %")
        self.assertEqual(out["empty"]["median-value"], "n.d.")
        self.assertEqual(out["empty"]["gap-value"], "n.d.")
        self.assertTrue(out["empty"]["hidden"])


if __name__ == "__main__":
    unittest.main()
