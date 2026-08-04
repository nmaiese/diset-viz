"""Le metriche della revisione (mandato sezione 5), su dossier sintetici.

Puro: si costruiscono i dossier a mano e si controlla che i numeri escano.
"""

import unittest

from scripts import practice_metrics as m


def _d(ind, state, published=None, flags=None, entered="2026-01-01", runs=None, timeline=None, motivo=""):
    return {
        "id": ind, "state": state, "published": published,
        "flags": flags or {}, "entered_at": entered, "motivo": motivo,
        "runs": runs or [], "timeline": timeline if timeline is not None else [{"at": entered}],
    }


class Compute(unittest.TestCase):
    def _metrics(self, dossier, runs=None, **kw):
        return m.compute(dossier, runs or [], today="2026-02-01", **kw)

    def test_counts_indicators_and_open_practices(self):
        dossier = {"a": _d("a", "fusa"), "b": _d("b", "chiusa"), "c": _d("c", "pubblicata")}
        out = self._metrics(dossier)
        self.assertEqual(out["osservabilita"]["indicatori_totali"], 3)
        self.assertEqual(out["velocita"]["pratiche_aperte"], 1)  # solo 'fusa' e' aperta

    def test_public_error_is_counted(self):
        dossier = {"a": _d("a", "invalidata", flags={"open_smentita": True})}
        out = self._metrics(dossier)
        self.assertEqual(out["affidabilita"]["errori_pubblici_dopo_pubblicazione"], 1)
        self.assertEqual(out["qualita"]["smentite_aperte"], 1)

    def test_invalidated_but_published_is_reliability_hit(self):
        dossier = {"a": _d("a", "invalidata", published=True)}
        out = self._metrics(dossier)
        self.assertEqual(out["affidabilita"]["risultati_invalidati_pubblicati"], 1)

    def test_run_association_share(self):
        runs = [{"summary": "dem:NMIGRATEIN curato", "detail": []},
                {"summary": "niente di identificabile", "detail": []}]
        out = self._metrics({"a": _d("a", "fusa")}, runs=runs)
        self.assertEqual(out["osservabilita"]["quota_run_associati_a_un_indicatore_pct"], 50.0)

    def test_stuck_over_threshold(self):
        old = _d("a", "in-lavorazione", entered="2025-01-01")
        out = self._metrics({"a": old}, soglia_giorni=30)
        self.assertEqual(out["velocita"]["ferme_oltre_soglia"], 1)

    def test_bloccate_excludes_normal_upstream_wait(self):
        # Stesso predicato di is_stuck: monte-mancante non e' bloccata, un blocco
        # esterno si'. La metrica non deve dire "bloccato" cio' che il cruscotto non chiama tale.
        dossier = {
            "a": _d("a", "in-attesa", motivo="monte-mancante"),
            "b": _d("b", "in-attesa", motivo="dipendenza-esterna"),
            "c": _d("c", "in-quarantena"),
        }
        out = self._metrics(dossier)
        self.assertEqual(out["velocita"]["bloccate"], 2)  # b + c, non a

    def test_longitudinal_metrics_are_none_not_zero(self):
        out = self._metrics({"a": _d("a", "fusa")})
        self.assertIsNone(out["affidabilita"]["tentativi_duplicati"])

    def test_resolve_today_defaults_to_a_real_date(self):
        # senza --today la fotografia non deve datare ogni pratica a zero giorni
        self.assertEqual(m._resolve_today("2026-01-01"), "2026-01-01")
        default = m._resolve_today("")
        self.assertRegex(default, r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
