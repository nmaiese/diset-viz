"""I gradini delle mappe: una regola, due copie, una prova che le tiene uguali.

La regola vive in `indicator_notes.choropleth_scale` (la pagina servita) e in
`choroScale` di `app/static/js/v1.js` (la mappa che cambia anno senza
ricaricare, e il confronto). Se le due copie si separano, la stessa mappa ha
colori diversi prima e dopo aver toccato il cursore dell'anno, e nessun altro
test se ne accorge.

La copia JavaScript si esegue davvero con node, sulle righe fra i segni
`choro:start` e `choro:end`. Dove node non c'e' la prova si salta dicendolo.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from app.design import LEGEND_MODE
from app.indicator_notes import choropleth_scale, choropleth_step

V1_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "js" / "v1.js"

CASES = {
    # il turismo 2024: un valore fuori scala, diciassette regioni nel primo gradino
    "fuori_scala": [52.3, 30.1, 15.1, 12.6, 10.7, 10.0, 9.2, 9.1, 8.5, 7.9,
                    7.1, 5.7, 4.7, 4.6, 4.5, 4.4, 3.8, 3.6, 3.4, 1.6],
    "regolare": [float(v) for v in range(20)],
    "pari_merito": [1, 1, 1, 1, 2, 2, 2, 3, 3, 9, 50, 50],
    "pochi": [3.2, 7.5, 40.0, 1.1],
    "tutti_uguali": [5.0] * 8,
    "negativi": [-12.0, -3.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.2, 0.4, 25.0],
    "province": [round(14.5 + (i * 7.3) % 20.3, 2) for i in range(107)],
}


def _js_block():
    source = V1_JS.read_text(encoding="utf-8")
    block = re.search(r"/\* choro:start \*/(.*?)/\* choro:end \*/", source, re.DOTALL)
    if block is None:
        raise AssertionError("i segni choro:start e choro:end non ci sono piu' in v1.js")
    return block.group(1)


@unittest.skipUnless(shutil.which("node"), "node non c'e': la copia JavaScript non si puo' eseguire")
class TestChoroplethParity(unittest.TestCase):
    def _run_js(self):
        script = _js_block() + """
        var cases = %s, out = {};
        Object.keys(cases).forEach(function (name) {
          var sc = choroScale(cases[name]);
          out[name] = { mode: sc.mode, median: sc.median,
                        steps: cases[name].map(function (v) { return choroStep(v, sc); }) };
        });
        out.__legend = LEGEND_MODE;
        process.stdout.write(JSON.stringify(out));
        """ % json.dumps(CASES)
        done = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def test_le_due_copie_danno_gli_stessi_gradini(self):
        js = self._run_js()
        for name, values in CASES.items():
            with self.subTest(caso=name):
                scale = choropleth_scale(values)
                self.assertEqual(js[name]["mode"], scale["mode"])
                self.assertEqual(js[name]["steps"], [choropleth_step(v, scale) for v in values])
                self.assertAlmostEqual(js[name]["median"], scale["median"], places=9)

    def test_le_frasi_della_legenda_sono_le_stesse(self):
        self.assertEqual(self._run_js()["__legend"], LEGEND_MODE)


class TestChoroplethRule(unittest.TestCase):
    def test_un_valore_fuori_scala_passa_ai_quantili(self):
        scale = choropleth_scale(CASES["fuori_scala"])
        self.assertEqual(scale["mode"], "quantile")
        steps = [choropleth_step(v, scale) for v in CASES["fuori_scala"]]
        # sei gruppi, nessuno oltre un terzo dei territori
        self.assertEqual(sorted(set(steps)), [1, 2, 3, 4, 5, 6])
        self.assertLessEqual(max(steps.count(s) for s in set(steps)), 5)

    def test_una_distribuzione_regolare_tiene_i_gradini_uguali(self):
        scale = choropleth_scale(CASES["regolare"])
        self.assertEqual(scale["mode"], "equal")
        self.assertEqual(choropleth_step(0.0, scale), 1)
        self.assertEqual(choropleth_step(19.0, scale), 6)

    def test_pari_merito_stesso_gradino_e_pochi_valori_restano_uguali(self):
        values = CASES["pari_merito"]
        scale = choropleth_scale(values)
        self.assertEqual(scale["mode"], "quantile")
        # il minimo nel primo gradino, il massimo nell'ultimo, i pari merito insieme
        self.assertEqual(choropleth_step(min(values), scale), 1)
        self.assertEqual(choropleth_step(max(values), scale), 6)
        steps = {v: {choropleth_step(v, scale)} for v in values}
        self.assertTrue(all(len(s) == 1 for s in steps.values()))
        self.assertEqual(choropleth_scale(CASES["pochi"])["mode"], "equal")
        flat = choropleth_scale(CASES["tutti_uguali"])
        self.assertEqual({choropleth_step(v, flat) for v in CASES["tutti_uguali"]}, {1})


if __name__ == "__main__":
    unittest.main()
