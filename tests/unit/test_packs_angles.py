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

    def _serie(self, nord_primo, sud_primo, nord_ultimo, sud_ultimo):
        return {
            2000: {f"t{i:02d}": (nord_primo if i < 10 else sud_primo) for i in range(20)},
            2015: {f"t{i:02d}": (nord_ultimo if i < 10 else sud_ultimo) for i in range(20)},
        }

    def test_a_rank_reversal_at_an_unchanged_gap_is_not_a_divergence(self):
        """Il difetto: una distanza ferma raccontata come +200%.

        I due gruppi si scelgono sull'ordine dell'**ultimo** anno, e nel primo
        quell'ordine puo' essere rovesciato: li' `first[high] - first[low]` e'
        negativo, e non e' una distanza, e' una distanza col segno di un
        ordinamento che non vale piu'. Da -10 a 10 la sottrazione firmata dava
        +200% di divergenza su un divario che non si e' mosso di un punto, cioe'
        l'angolo piu' forte del pacchetto costruito sul nulla. Un articolo lo
        avrebbe aperto: la forza decide la struttura."""
        found = angles.group_divergence(self._serie(0.0, 10.0, 10.0, 0.0), self.GROUPS)
        self.assertEqual(found, [])

    def test_a_reversal_that_also_widens_says_that_it_reversed(self):
        """L'altra meta': quando il divario si allarga **e** l'ordine si rovescia
        l'angolo esce, e porta il sorpasso fra i fatti. "Il divario si e'
        allargato" li' e' vero e insieme fuorviante, perche' chi sta sopra oggi
        stava sotto allora, e chi scrive non deve dedurlo da due medie."""
        found = angles.group_divergence(self._serie(0.0, 2.0, 20.0, 0.0), self.GROUPS)
        self.assertEqual(kinds(found), ["gruppi-che-divergono"])
        figure = found[0]["figures"]
        self.assertTrue(figure["ordine_invertito"])
        self.assertEqual(figure["distanza_primo_anno"], 2.0)
        self.assertEqual(figure["distanza_ultimo_anno"], 20.0)

    def test_the_ordinary_case_says_the_order_held(self):
        found = angles.group_divergence(self._serie(10.0, 8.0, 20.0, 8.0), self.GROUPS)
        self.assertFalse(found[0]["figures"]["ordine_invertito"])

    def test_the_distances_it_reports_are_never_negative(self):
        """Una distanza col segno e' il sintomo leggibile del difetto: se
        ricompare, e' tornata la sottrazione firmata."""
        for serie in (self._serie(0.0, 2.0, 20.0, 0.0),
                      self._serie(10.0, 8.0, 20.0, 8.0),
                      self._serie(20.0, 2.0, 11.0, 10.0)):
            for found in angles.group_divergence(serie, self.GROUPS):
                self.assertGreaterEqual(found["figures"]["distanza_primo_anno"], 0)
                self.assertGreaterEqual(found["figures"]["distanza_ultimo_anno"], 0)

    def test_without_a_grouping_it_says_nothing(self):
        self.assertEqual(angles.group_divergence(flat(), {}), [])


class ThreeGroupsAreTheNormalCase(unittest.TestCase):
    """Con due gruppi la coppia agli estremi e' sempre la stessa. Con tre no.

    E tre e' il caso normale: le macroaree italiane sono tre o cinque. Scegliere
    la coppia una volta sola sull'ultimo anno e misurarla anche nel primo puo'
    dare il **verso opposto** a quello del divario fra gruppi, che e' la frase
    che questo progetto fa piu' spesso.
    """

    GROUPS = {"a1": "A", "b1": "B", "c1": "C"}

    @staticmethod
    def _serie(primo, ultimo):
        return {2015: dict(zip(("a1", "b1", "c1"), primo)),
                2024: dict(zip(("a1", "b1", "c1"), ultimo))}

    def test_a_narrowing_spread_is_not_called_a_divergence(self):
        """A=0 B=100 C=50 -> A=60 B=50 C=0: il divario passa da 100 a 60.

        Confrontando A con C (gli estremi del solo ultimo anno) usciva
        `gruppi-che-divergono` al +20%. Non era un numero impreciso, era il
        verso sbagliato.
        """
        found = angles.group_divergence(
            self._serie((0.0, 100.0, 50.0), (60.0, 50.0, 0.0)), self.GROUPS)
        self.assertEqual(kinds(found), ["gruppi-che-convergono"])
        figure = found[0]["figures"]
        self.assertEqual(figure["distanza_primo_anno"], 100.0)
        self.assertEqual(figure["distanza_ultimo_anno"], 60.0)
        self.assertLess(figure["variazione_relativa"], 0)

    def test_and_it_names_who_was_at_the_extremes_before(self):
        """"Il divario fra gruppi si e' mosso" senza dire fra chi racconterebbe
        una crescita al posto di un cambio di protagonisti."""
        found = angles.group_divergence(
            self._serie((0.0, 100.0, 50.0), (60.0, 50.0, 0.0)), self.GROUPS)
        figure = found[0]["figures"]
        self.assertEqual((figure["gruppo_alto"], figure["gruppo_basso"]), ("A", "C"))
        self.assertEqual((figure["gruppo_alto_primo_anno"],
                          figure["gruppo_basso_primo_anno"]), ("B", "A"))
        self.assertTrue(figure["estremi_cambiati"])
        self.assertFalse(figure["ordine_invertito"],
                         "non e' un sorpasso fra gli stessi due: sono altri due")

    def test_a_spread_that_really_widens_still_says_so(self):
        """La correzione non spegne il rilevatore: cambia chi confronta."""
        found = angles.group_divergence(
            self._serie((40.0, 50.0, 60.0), (10.0, 50.0, 90.0)), self.GROUPS)
        self.assertEqual(kinds(found), ["gruppi-che-divergono"])
        figure = found[0]["figures"]
        self.assertEqual(figure["distanza_primo_anno"], 20.0)
        self.assertEqual(figure["distanza_ultimo_anno"], 80.0)
        self.assertFalse(figure["estremi_cambiati"])

    def test_the_distances_are_non_negative_by_construction(self):
        """Con gli estremi presi dentro ciascun anno non esiste piu' una
        sottrazione firmata da cui difendersi: e' la correzione precedente che
        diventa superflua invece di restare a fare la guardia."""
        for primo, ultimo in ((( 0.0, 100.0, 50.0), (60.0, 50.0,  0.0)),
                              ((40.0,  50.0, 60.0), (10.0, 50.0, 90.0)),
                              ((10.0,  10.0, 90.0), (90.0, 10.0, 10.0))):
            for found in angles.group_divergence(self._serie(primo, ultimo), self.GROUPS):
                self.assertGreaterEqual(found["figures"]["distanza_primo_anno"], 0)
                self.assertGreaterEqual(found["figures"]["distanza_ultimo_anno"], 0)


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


class ZeroHasNoDirection(unittest.TestCase):
    """Ogni caso col suo specchio, perche' e' l'unico modo di vedere lo zero.

    `(a < 0) != (b < 0)` tratta lo zero come positivo. Rileggendo la riga non si
    vede: si vede solo dando a un rilevatore un fenomeno e poi lo stesso
    fenomeno capovolto, e scoprendo che risponde in due modi. La stessa riga era
    scritta in tre punti, e in due su tre sbagliava.
    """

    @staticmethod
    def _series(values, width=1):
        return {2015 + i: {f"t{n:02d}": v for n in range(width)}
                for i, v in enumerate(values)}

    @staticmethod
    def _moves(fermi, mossi, delta):
        """`fermi` territori immobili, `mossi` che si spostano di `delta`."""
        names = [f"t{i:02d}" for i in range(fermi + mossi)]
        return {
            2020: {name: 100.0 for name in names},
            2024: {name: (100.0 if index < fermi else 100.0 + delta)
                   for index, name in enumerate(names)},
        }

    def test_a_territory_that_did_not_move_is_not_moving_against_the_trend(self):
        """Il caso che valeva forza 1,00 su una tabella di movimenti tutti a zero."""
        found = angles.against_the_grain(self._moves(fermi=16, mossi=4, delta=-40.0))
        self.assertEqual(found, [], "sedici fermi non sono sedici controcorrente")

    def test_and_its_mirror_answers_the_same_way(self):
        """Stessa forma, media positiva: prima taceva solo questo dei due."""
        self.assertEqual(angles.against_the_grain(self._moves(16, 4, 40.0)), [])

    def test_a_real_countertrend_still_speaks(self):
        """La correzione non spegne il rilevatore: toglie i fermi, non i contrari."""
        names = [f"t{i:02d}" for i in range(20)]
        series = {
            2020: {name: 100.0 for name in names},
            2024: {name: (90.0 if i < 12 else (100.0 if i < 16 else 110.0))
                   for i, name in enumerate(names)},
        }
        found = angles.against_the_grain(series)
        self.assertEqual(kinds(found), ["controcorrente"])
        self.assertEqual(found[0]["figures"]["quanti"], 4)
        self.assertEqual(found[0]["territories"], names[16:],
                         "i quattro fermi non devono comparire fra i controcorrente")

    def test_a_flat_first_half_is_not_an_acceleration(self):
        """Senza un verso di partenza non c'e' una velocita' da confrontare."""
        rising = self._series([100.0] * 7 + [105.0, 110.0, 115.0, 120.0, 125.0])
        self.assertEqual(angles.acceleration(rising), [])

    def test_and_its_mirror_answers_the_same_way_too(self):
        falling = self._series([100.0] * 7 + [95.0, 90.0, 85.0, 80.0, 75.0])
        self.assertEqual(angles.acceleration(falling), [])

    def test_a_real_acceleration_still_speaks(self):
        series = self._series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0,
                               110.0, 120.0, 130.0, 140.0, 150.0, 160.0])
        self.assertEqual(kinds(angles.acceleration(series)), ["accelerazione"])

    def test_a_flat_stretch_that_starts_falling_has_not_turned(self):
        """`cambia_verso` e' una cifra citabile: finisce in una frase."""
        falling = self._series([100.0] * 7 + [95.0, 90.0, 85.0, 80.0, 75.0])
        found = angles.slope_break(falling)
        self.assertTrue(found, "il campione doveva produrre una rottura di pendenza")
        self.assertFalse(found[0]["figures"]["cambia_verso"])

    def test_nor_has_one_that_starts_rising(self):
        rising = self._series([100.0] * 7 + [105.0, 110.0, 115.0, 120.0, 125.0])
        found = angles.slope_break(rising)
        self.assertTrue(found)
        self.assertFalse(found[0]["figures"]["cambia_verso"])

    def test_but_a_series_that_goes_up_then_down_has(self):
        series = self._series([100.0, 105.0, 110.0, 115.0, 120.0, 125.0,
                               120.0, 115.0, 110.0, 105.0, 100.0, 95.0])
        found = angles.slope_break(series)
        self.assertTrue(found)
        self.assertTrue(found[0]["figures"]["cambia_verso"])


class ATiedRankingStillBreaks(unittest.TestCase):
    """Quando meta' delle posizioni sono in pari, il salto tipico e' zero.

    Misurare contro di lui vuol dire dividere per zero, e rinunciare vuol dire
    perdere la spaccatura piu' netta che esista invece della piu' debole. Non e'
    un caso di laboratorio: **13 indicatori su 594** del catalogo lo producono,
    fra cui i quattro `MULTI_SATLIFE` e `bes:06POL002`-`005`, che sono
    percentuali arrotondate su cui molti territori coincidono.
    """

    @staticmethod
    def _split(high=100.0, low=0.0, each=10):
        row = {f"a{i:02d}": high for i in range(each)}
        row.update({f"b{i:02d}": low for i in range(each)})
        return {2024: row}

    def test_the_clearest_split_there_is_produces_an_angle(self):
        found = angles.distribution_breaks(self._split())
        self.assertEqual(kinds(found), ["graduatoria-spezzata"])
        self.assertEqual(found[0]["figures"]["salto"], 100.0)
        self.assertEqual(found[0]["figures"]["dopo_la_posizione"], 10)

    def test_and_it_is_strong_not_a_rounding_error(self):
        """La mediana dei soli salti positivi darebbe rapporto 1,00, forza 0,00."""
        found = angles.distribution_breaks(self._split())
        self.assertGreater(found[0]["strength"], 0.5)

    def test_all_the_same_value_is_still_silent(self):
        """Nessun salto: li' non c'e' nessuna graduatoria da spezzare."""
        same = {2024: {f"t{i:02d}": 50.0 for i in range(20)}}
        self.assertEqual(angles.distribution_breaks(same), [])

    def test_a_regular_ladder_is_still_silent(self):
        """La proprieta' che il rilevatore aveva gia': non spara sulla scaletta."""
        self.assertEqual(angles.distribution_breaks(flat()), [])


if __name__ == "__main__":
    unittest.main()
