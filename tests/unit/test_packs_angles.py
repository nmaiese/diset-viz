"""Lo story finder, su serie inventate dove la risposta si sa gia'.

Ogni rilevatore ha due prove: una serie che contiene la sua storia, e una che
non la contiene. La seconda conta quanto la prima. Un rilevatore che spara su
tutto e' peggio di uno che non spara: riempie l'inventario di angoli deboli e
sposta l'articolo verso il rumore, e nessuna guardia numerica se ne accorge
perche' ogni singola cifra resta giusta.
"""
import unittest

from packs import angles


def matrix(per_year, names=None):
    """{anno: {territorio: valore}} da {anno: [valori]}."""
    names = names or [f"t{index:02d}" for index in range(len(next(iter(per_year.values()))))]
    return {year: dict(zip(names, values)) for year, values in per_year.items()}


def flat(years=range(2000, 2016), width=20):
    """Venti territori equispaziati, fermi. Nessuna storia dentro."""
    return {year: {f"t{i:02d}": float(i) for i in range(width)} for year in years}


def kinds(found):
    return [angle["type"] for angle in found]


class SlopeBreak(unittest.TestCase):
    def test_finds_the_year_the_series_changes_direction(self):
        series = {}
        for year in range(2000, 2008):
            series[year] = {f"t{i:02d}": 10.0 + i for i in range(20)}
        for step, year in enumerate(range(2008, 2016), start=1):
            series[year] = {f"t{i:02d}": 10.0 + i + 5 * step for i in range(20)}
        found = angles.slope_break(series)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["years"], [2007])
        self.assertGreater(found[0]["strength"], 0.5)

    def test_a_straight_line_has_no_break(self):
        series = {year: {f"t{i:02d}": float(i + year - 2000) for i in range(20)}
                  for year in range(2000, 2016)}
        self.assertEqual(angles.slope_break(series), [])

    def test_too_few_years_says_nothing(self):
        self.assertEqual(angles.slope_break(flat(range(2000, 2004))), [])


class Acceleration(unittest.TestCase):
    def test_same_direction_at_another_speed(self):
        values, series = 10.0, {}
        for year in range(2000, 2008):
            series[year] = {f"t{i:02d}": values + i for i in range(20)}
            values += 1
        for year in range(2008, 2016):
            series[year] = {f"t{i:02d}": values + i for i in range(20)}
            values += 4
        found = angles.acceleration(series)
        self.assertEqual(kinds(found), ["accelerazione"])
        # Le pendenze stanno in `diagnostica`, non in `figures`: ordinano
        # l'angolo e non si scrivono. Vedi `angles.DIAGNOSTIC_FIGURES`.
        self.assertGreater(found[0]["diagnostica"]["pendenza_seconda_meta"],
                           found[0]["diagnostica"]["pendenza_prima_meta"])

    def test_a_change_of_direction_is_not_a_change_of_speed(self):
        """Su e poi giu' e' materia di slope_break: qui deve tacere."""
        values, series = 10.0, {}
        for year in range(2000, 2008):
            series[year] = {f"t{i:02d}": values + i for i in range(20)}
            values += 3
        for year in range(2008, 2016):
            series[year] = {f"t{i:02d}": values + i for i in range(20)}
            values -= 3
        self.assertEqual(angles.acceleration(series), [])


class ReturnToLevel(unittest.TestCase):
    def test_a_v_shape_comes_back(self):
        shape = [0, -4, -8, -12, -14, -12, -8, -4, -1, 0]
        series = {2000 + step: {f"t{i:02d}": 50.0 + offset + i for i in range(20)}
                  for step, offset in enumerate(shape)}
        found = angles.return_to_level(series)
        self.assertEqual(kinds(found), ["ritorno-al-livello"])
        self.assertEqual(found[0]["figures"]["anno_di_oggi"], 2009)
        self.assertIsNotNone(found[0]["caution"])

    def test_a_flat_series_does_not_keep_returning(self):
        self.assertEqual(angles.return_to_level(flat()), [])


class DispersionTrend(unittest.TestCase):
    def test_a_gap_that_widens_and_from_which_side(self):
        series = {}
        for step, year in enumerate(range(2000, 2016)):
            series[year] = {f"t{i:02d}": float(i) * (1 + 0.1 * step) for i in range(20)}
        found = angles.dispersion_trend(series)
        self.assertEqual(kinds(found), ["divario-che-si-allarga"])
        self.assertEqual(found[0]["figures"]["si_muove"], "dall'alto")

    def test_a_gap_that_closes_from_the_bottom(self):
        series = {}
        for step, year in enumerate(range(2000, 2016)):
            series[year] = {f"t{i:02d}": 100.0 - (20 - i) * (1 - 0.04 * step)
                            for i in range(20)}
        found = angles.dispersion_trend(series)
        self.assertEqual(kinds(found), ["divario-che-si-chiude"])
        self.assertEqual(found[0]["figures"]["si_muove"], "dal basso")

    def test_a_frozen_distribution_has_no_trend(self):
        self.assertEqual(angles.dispersion_trend(flat()), [])

    def test_five_territories_are_not_a_distribution(self):
        self.assertEqual(angles.dispersion_trend(flat(width=5)), [])


class RankReversals(unittest.TestCase):
    def _swapping(self):
        series = {}
        for year in range(2000, 2016):
            row = {f"t{i:02d}": float(i) for i in range(20)}
            if year >= 2010:
                row["t00"], row["t19"] = 19.0, 0.0
            series[year] = row
        return series

    def test_a_swap_that_holds_is_reported(self):
        found = angles.rank_reversals(self._swapping())
        self.assertTrue(found)
        self.assertEqual(found[0]["type"], "sorpasso")
        self.assertEqual(sorted(found[0]["territories"]), ["t00", "t19"])
        self.assertGreaterEqual(found[0]["figures"]["anni_di_tenuta"], 3)

    def test_a_one_year_swap_is_noise(self):
        series = {}
        for year in range(2000, 2016):
            row = {f"t{i:02d}": float(i) for i in range(20)}
            if year == 2008:
                row["t00"], row["t19"] = 19.0, 0.0
            series[year] = row
        self.assertEqual(angles.rank_reversals(series), [])

    def test_a_frozen_ranking_has_no_reversals(self):
        self.assertEqual(angles.rank_reversals(flat()), [])


class Outliers(unittest.TestCase):
    def test_one_value_far_outside_the_pack(self):
        series = flat()
        series[2015] = dict(series[2015], t00=500.0)
        found = angles.outliers(series)
        self.assertEqual(kinds(found)[:1], ["valore-fuori-scala"])
        self.assertEqual(found[0]["territories"], ["t00"])

    def test_an_even_spread_has_no_outlier(self):
        self.assertEqual(angles.outliers(flat()), [])


class DistributionBreaks(unittest.TestCase):
    def test_a_ranking_that_splits_in_two_clusters(self):
        row = {f"t{i:02d}": float(i) for i in range(10)}
        row.update({f"t{i:02d}": 100.0 + i for i in range(10, 20)})
        found = angles.distribution_breaks({2015: row})
        self.assertEqual(kinds(found)[:1], ["graduatoria-spezzata"])
        self.assertEqual(found[0]["figures"]["dopo_la_posizione"], 10)

    def test_a_regular_staircase_has_no_step(self):
        self.assertEqual(angles.distribution_breaks(flat()), [])


class AgainstTheGrain(unittest.TestCase):
    def test_the_one_that_went_the_other_way(self):
        series = {2000: {f"t{i:02d}": 10.0 for i in range(20)},
                  2015: {f"t{i:02d}": 20.0 for i in range(20)}}
        series[2015]["t07"] = 5.0
        found = angles.against_the_grain(series)
        self.assertEqual(kinds(found), ["controcorrente"])
        self.assertEqual(found[0]["territories"], ["t07"])

    def test_when_everyone_moves_together_nobody_is_counter(self):
        series = {2000: {f"t{i:02d}": 10.0 for i in range(20)},
                  2015: {f"t{i:02d}": 20.0 for i in range(20)}}
        self.assertEqual(angles.against_the_grain(series), [])


class GroupDivergence(unittest.TestCase):
    GROUPS = {f"t{i:02d}": ("nord" if i < 10 else "sud") for i in range(20)}

    def test_two_groups_pulling_apart(self):
        series = {
            2000: {f"t{i:02d}": (10.0 if i < 10 else 8.0) for i in range(20)},
            2015: {f"t{i:02d}": (20.0 if i < 10 else 8.0) for i in range(20)},
        }
        found = angles.group_divergence(series, self.GROUPS)
        self.assertEqual(kinds(found), ["gruppi-che-divergono"])
        self.assertEqual(found[0]["figures"]["gruppo_alto"], "nord")
        self.assertIn("ponderati", found[0]["caution"])

    def test_without_a_grouping_it_says_nothing(self):
        self.assertEqual(angles.group_divergence(flat(), {}), [])


class MethodBreaks(unittest.TestCase):
    def test_a_year_in_the_note_inside_the_window(self):
        found = angles.method_breaks(
            "Dal 2013 la rilevazione adotta la nuova classificazione.",
            [2000, 2020])
        self.assertEqual(found[0]["years"], [2013])
        self.assertGreater(found[0]["strength"], 0.8)

    def test_a_year_outside_the_window_is_not_this_article_problem(self):
        self.assertEqual(angles.method_breaks("Rottura nel 1991.", [2000, 2020]), [])

    def test_no_note_no_angle(self):
        self.assertEqual(angles.method_breaks("", [2000, 2020]), [])


class TheInventory(unittest.TestCase):
    def test_a_series_with_nothing_to_say_produces_nothing(self):
        self.assertEqual(angles.find(flat()), [])

    def test_angles_come_out_strongest_first_and_the_same_every_time(self):
        series = {}
        for step, year in enumerate(range(2000, 2016)):
            series[year] = {f"t{i:02d}": float(i) * (1 + 0.1 * step) for i in range(20)}
        first = angles.find(series)
        self.assertTrue(first)
        self.assertEqual(first, angles.find(series))
        strengths = [angle["strength"] for angle in first]
        self.assertEqual(strengths, sorted(strengths, reverse=True))

    def test_string_years_are_accepted(self):
        """Il view model dell'app indicizza la matrice per stringa."""
        series = {str(year): row for year, row in flat().items()}
        series["2015"] = dict(series["2015"], t00=500.0)
        self.assertTrue(angles.find(series))

    def test_one_story_does_not_come_out_three_times(self):
        """Un territorio fuori scala spara tre rilevatori e resta una storia.

        Senza soppressione l'inventario apriva con "salto dopo il primo",
        "salto dopo il secondo" e "valore fuori scala", che sono tre modi di
        dire la stessa cosa sullo stesso territorio. Chi scrive la raccontava
        tre volte.
        """
        series = {str(year): row for year, row in flat().items()}
        series["2015"] = dict(series["2015"], t00=500.0)
        found = angles.find(series)

        distribution = [a for a in found if a["type"] in angles.SAME_STORY]
        self.assertEqual(len(distribution), 1, kinds(found))
        absorbed = distribution[0].get("implied_by") or []
        self.assertTrue(absorbed, "l'angolo assorbito deve restare nominato")
        self.assertIn("valore-fuori-scala", [item["type"] for item in absorbed])

    def test_two_different_facts_about_one_territory_both_survive(self):
        """La soppressione non deve diventare una perdita di materiale."""
        # Tutti fermi, t00 scala la graduatoria, t05 va nell'altro verso.
        # Movimento medio positivo, quindi t05 e' davvero controcorrente.
        series = {}
        for year in range(2000, 2016):
            row = {f"t{i:02d}": float(i) for i in range(20)}
            if year >= 2010:
                row["t00"], row["t05"] = 25.0, 2.0
            series[year] = row
        found = kinds(angles.find(series))
        self.assertIn("sorpasso", found)
        self.assertIn("controcorrente", found)

    def test_total_strength_rewards_depth_not_count(self):
        strong = [{"strength": 0.9, "type": "a"}, {"strength": 0.8, "type": "b"}]
        many = [{"strength": 0.2, "type": str(i)} for i in range(10)]
        self.assertGreater(angles.total_strength(strong), angles.total_strength(many))


class CitableFiguresAndDiagnostics(unittest.TestCase):
    """Le cifre che si scrivono e quelle che ordinano soltanto.

    E' la correzione che i quattro giudici ciechi della prima run hanno trovato
    da soli: tutti e quattro, indipendenti, hanno indicato come paragrafo piu'
    freddo quello che trascriveva pendenze di regressione e varianza spiegata.
    """

    def _every_angle(self):
        """Un campione che accende tutti i rilevatori, non una serie sola."""
        found = []
        rising, falling, broken, jumpy = {}, {}, {}, {}
        value = 10.0
        for year in range(2000, 2016):
            rising[year] = {f"t{i:02d}": value + i * 0.5 for i in range(20)}
            falling[year] = {f"t{i:02d}": 100.0 - value - i * 0.5 for i in range(20)}
            broken[year] = {f"t{i:02d}": (value if year < 2008 else 200.0 - value) + i
                            for i in range(20)}
            row = {f"t{i:02d}": float(i) for i in range(20)}
            row["t19"] = 400.0 if year >= 2010 else 19.0
            jumpy[year] = row
            value += 2
        groups = {f"t{i:02d}": ("Nord" if i < 7 else "Centro" if i < 14 else "Mezzogiorno")
                  for i in range(20)}
        for matrix in (rising, falling, broken, jumpy):
            found.extend(angles.find(matrix, groups=groups))
            found.extend(angles.raw_angles(matrix, groups=groups))
        self.assertGreater(len(found), 10, "il campione non accende abbastanza rilevatori")
        return found

    def test_every_figure_key_is_classified_one_way_or_the_other(self):
        """Una chiave nuova non puo' entrare senza che qualcuno decida dove va.

        Senza questo, il prossimo rilevatore aggiunge una pendenza in `figures`
        e il freddo rientra in silenzio: e' esattamente com'era entrato.
        """
        for angle in self._every_angle():
            for field in angle["diagnostica"]:
                self.assertIn(field, angles.DIAGNOSTIC_FIGURES)
            for field in angle["figures"]:
                self.assertNotIn(
                    field, angles.DIAGNOSTIC_FIGURES,
                    f"{angle['type']}: {field} e' diagnostica e sta fra le citabili")

    def test_no_slope_or_explained_variance_reaches_the_citable_side(self):
        """I tre nomi che i giudici hanno indicato, per nome."""
        for angle in self._every_angle():
            for banned in ("pendenza", "quota_spiegata", "z_modificato"):
                for field in angle["figures"]:
                    self.assertNotIn(banned, field,
                                     f"{angle['type']} espone {field} a chi scrive")

    def test_the_diagnostics_are_kept_not_thrown_away(self):
        """Servono alla calibrazione e ai test: si nascondono, non si perdono."""
        broken = {}
        value = 10.0
        for year in range(2000, 2016):
            broken[year] = {f"t{i:02d}": (value if year < 2008 else 200.0 - value) + i
                            for i in range(20)}
            value += 2
        found = [a for a in angles.find(broken) if a["type"] == "rottura-di-pendenza"]
        self.assertTrue(found, "il campione doveva produrre una rottura di pendenza")
        self.assertIn("quota_spiegata", found[0]["diagnostica"])

    def test_split_figures_moves_nothing_else(self):
        citable, diagnostic = angles.split_figures(
            {"valore": 1.0, "z_modificato": 6.3, "sopra": "Sicilia"})
        self.assertEqual(citable, {"valore": 1.0, "sopra": "Sicilia"})
        self.assertEqual(diagnostic, {"z_modificato": 6.3})


if __name__ == "__main__":
    unittest.main()
