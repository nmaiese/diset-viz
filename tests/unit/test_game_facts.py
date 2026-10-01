"""Le regole del fatto di fine partita (`app/game_facts.py`), sulle funzioni pure.

Ogni regola ha il suo caso borderline: se la regola salta, il test cade. Qui non
si leggono dati veri (il piazzamento si sostituisce): il ciclo su tutti gli
indicatori giocabili sta in `tests/integration/test_game_facts_payload.py`."""

import unittest
from unittest import mock

from app import game_facts as g
from app.data import REGION_ORDER
from app.design import numfmt

THIN = numfmt.THIN


def _ind(unit="euro", name="Reddito per abitante", year=2024, id_="901"):
    return {"id": id_, "name": name, "unit": unit, "year": year}


def _t(name, value, key=None):
    return {"name": name, "key": key or name.lower(), "value": value}


class SenzaDati(unittest.TestCase):
    """Il piazzamento legge i dati veri: nei test sulla frase si spegne."""

    def setUp(self):
        patcher = mock.patch.object(g, "piazzamento", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)


class ValidaTest(unittest.TestCase):
    def test_a_good_sentence_passes(self):
        self.assertEqual(g.valida("Hai messo Roma sopra Milano."), "Hai messo Roma sopra Milano.")

    def test_thousands_dots_are_not_extra_final_points(self):
        frase = f"Roma ha 1.234{THIN}euro, Milano ha 12.000{THIN}euro, ogni 1.000 abitanti."
        self.assertEqual(g.valida(frase), frase)

    def test_a_second_sentence_is_refused(self):
        self.assertIsNone(g.valida("Una frase. Un'altra."))

    def test_missing_final_point_is_refused(self):
        self.assertIsNone(g.valida("Hai messo Roma sopra Milano"))

    def test_each_forbidden_character_is_refused(self):
        for vietato in ("—", "–", ";", "…", "n.d."):
            with self.subTest(vietato=vietato):
                self.assertIsNone(g.valida(f"Roma ha {vietato} Milano."))

    def test_nan_is_refused(self):
        self.assertIsNone(g.valida("Roma ha nan euro."))

    def test_length_limit_is_260_and_never_truncates(self):
        giusta = "a" * 259 + "."
        lunga = "a" * 260 + "."
        self.assertEqual(len(giusta), 260)
        self.assertEqual(g.valida(giusta), giusta)
        self.assertIsNone(g.valida(lunga))

    def test_non_strings_are_refused(self):
        for valore in (None, "", 12):
            self.assertIsNone(g.valida(valore))


class ArticoliTest(unittest.TestCase):
    def test_all_twenty_regions_have_the_right_article(self):
        atteso = {
            "Piemonte": "il Piemonte", "Valle d'Aosta": "la Valle d'Aosta", "Lombardia": "la Lombardia",
            "Trentino Alto Adige": "il Trentino Alto Adige", "Veneto": "il Veneto",
            "Friuli-Venezia Giulia": "il Friuli-Venezia Giulia", "Liguria": "la Liguria",
            "Emilia-Romagna": "l'Emilia-Romagna", "Toscana": "la Toscana", "Umbria": "l'Umbria",
            "Marche": "le Marche", "Lazio": "il Lazio", "Abruzzo": "l'Abruzzo", "Molise": "il Molise",
            "Campania": "la Campania", "Puglia": "la Puglia", "Basilicata": "la Basilicata",
            "Calabria": "la Calabria", "Sicilia": "la Sicilia", "Sardegna": "la Sardegna",
        }
        self.assertEqual(set(atteso), set(REGION_ORDER))
        for regione, forma in atteso.items():
            with self.subTest(regione=regione):
                self.assertEqual(g.nome_con_articolo(regione, "regioni"), forma)

    def test_an_unknown_region_name_stays_bare(self):
        self.assertEqual(g.nome_con_articolo("Atlantide", "regioni"), "Atlantide")

    def test_provinces_are_bare_except_the_two_that_take_the_article(self):
        self.assertEqual(g.nome_con_articolo("Trieste", "province"), "Trieste")
        self.assertEqual(g.nome_con_articolo("La Spezia", "stessa_regione"), "La Spezia")
        self.assertEqual(g.nome_con_articolo("Sud Sardegna", "province"), "il Sud Sardegna")
        self.assertEqual(g.nome_con_articolo("Verbano-Cusio-Ossola", "province"), "il Verbano-Cusio-Ossola")


class RelazioneTest(unittest.TestCase):
    def test_ratio_1_49_is_not_said_but_1_5_is(self):
        self.assertEqual(g.relazione("euro", "Reddito", [10.0, 14.9], 10.0, 14.9), "")
        self.assertEqual(g.relazione("euro", "Reddito", [10.0, 15.0], 10.0, 15.0), ", un rapporto di 1,5 volte")

    def test_the_ratio_is_decided_on_the_raw_value_not_the_rounded_one(self):
        # 1,4996 si scriverebbe "1,5 volte", ma e' sotto la soglia.
        self.assertEqual(g.relazione("euro", "Reddito", [10000.0, 14996.0], 10000.0, 14996.0), "")

    def test_ratio_is_written_with_one_decimal_and_italian_comma(self):
        self.assertEqual(g.relazione("euro", "Reddito", [10.0, 23.0], 10.0, 23.0), ", un rapporto di 2,3 volte")

    def test_a_small_value_near_zero_blocks_the_ratio(self):
        # mediana 10, il piu' piccolo 0,4 e' sotto il 5% (0,5)
        valori = [0.4, 9.0, 10.0, 11.0, 12.0]
        self.assertEqual(g.relazione("euro", "Reddito", valori, 0.4, 12.0), "")
        # 0,5 e' esattamente il 5%: regge
        valori = [0.5, 9.0, 10.0, 11.0, 12.0]
        self.assertEqual(g.relazione("euro", "Reddito", valori, 0.5, 12.0), ", un rapporto di 24,0 volte")

    def test_for_a_pair_the_median_is_the_mean(self):
        # mediana (0,2 + 10) / 2 = 5,1: lo 0,2 e' sotto il 5% di 5,1 (0,255)
        self.assertEqual(g.relazione("euro", "Reddito", [0.2, 10.0], 0.2, 10.0), "")

    def test_negative_or_zero_values_block_the_ratio(self):
        self.assertEqual(g.relazione("euro", "Reddito", [-2.0, 10.0], -2.0, 10.0), "")
        self.assertEqual(g.relazione("euro", "Reddito", [0.0, 10.0], 0.0, 10.0), "")
        # un valore negativo fra quelli in gioco, anche se la coppia e' positiva
        self.assertEqual(g.relazione("euro", "Reddito", [-1.0, 4.0, 10.0], 4.0, 10.0), "")

    def test_a_balance_never_gets_a_ratio(self):
        nome = "Saldo migratorio: chi arriva meno chi parte, ogni 1.000 abitanti"
        self.assertEqual(g.relazione("per 1.000 abitanti", nome, [2.0, 8.0], 2.0, 8.0), "")

    def test_percent_units_say_points_never_times(self):
        for unita in ("percentuale", "%", "Valori percentuali"):
            with self.subTest(unita=unita):
                rel = g.relazione(unita, "Disoccupazione", [5.0, 20.0], 5.0, 20.0)
                self.assertEqual(rel, ", uno scarto di 15,0 punti percentuali")
                self.assertNotIn("volte", rel)

    def test_percentage_points_unit_says_points_too(self):
        rel = g.relazione("punti percentuali", "Distanza", [10.0, 30.0], 10.0, 30.0)
        self.assertEqual(rel, ", uno scarto di 20,0 punti percentuali")

    def test_an_invisible_point_gap_says_nothing(self):
        self.assertEqual(g.relazione("percentuale", "X", [12.0, 12.00001], 12.0, 12.00001), "")

    def test_a_close_pair_of_non_percent_values_has_no_relation(self):
        self.assertEqual(g.relazione("anni", "Speranza di vita", [80.0, 83.0], 80.0, 83.0), "")


class PiazzamentoTest(unittest.TestCase):
    @staticmethod
    def _venti(**cambi):
        valori = {f"r{i:02d}": float(i) for i in range(1, 21)}
        valori.update(cambi)
        return valori

    def test_exact_place_with_direction_higher_better(self):
        # r03 vale 3: e' la 18ª su 20 se piu' alto e' meglio.
        self.assertEqual(
            g.piazzamento_da_valori(self._venti(), "r03", "higher_better", False, "regioni", 20), "18ª su 20")

    def test_lower_better_reverses_the_order(self):
        self.assertEqual(
            g.piazzamento_da_valori(self._venti(), "r03", "lower_better", False, "regioni", 20), "3ª su 20")

    def test_unknown_direction_gives_no_place(self):
        self.assertIsNone(g.piazzamento_da_valori(self._venti(), "r03", None, False, "regioni", 20))

    def test_incomplete_coverage_gives_no_place(self):
        valori = self._venti()
        del valori["r20"]
        self.assertIsNone(g.piazzamento_da_valori(valori, "r03", "higher_better", False, "regioni", 20))
        self.assertIsNone(g.piazzamento_da_valori(self._venti(r05=None), "r03", "higher_better", False, "regioni", 20))

    def test_a_missing_territory_gives_no_place(self):
        self.assertIsNone(g.piazzamento_da_valori(self._venti(), "zz", "higher_better", False, "regioni", 20))

    def test_ties_share_the_place_and_skip_the_next(self):
        valori = self._venti(r19=20.0)  # r19 e r20 a pari merito in cima
        self.assertEqual(g.piazzamento_da_valori(valori, "r19", "higher_better", False, "regioni", 20), "1ª su 20")
        self.assertEqual(g.piazzamento_da_valori(valori, "r20", "higher_better", False, "regioni", 20), "1ª su 20")
        # la successiva salta un posto: r18 e' terza
        self.assertEqual(g.piazzamento_da_valori(valori, "r18", "higher_better", False, "regioni", 20), "3ª su 20")

    def test_ties_on_provinces_too(self):
        valori = {f"p{i:03d}": float(i) for i in range(1, 108)}
        valori["p106"] = 107.0
        self.assertEqual(g.piazzamento_da_valori(valori, "p106", "higher_better", False, "province", 107), "1ª su 107")
        self.assertEqual(g.piazzamento_da_valori(valori, "p105", "higher_better", False, "province", 107), "3ª su 107")

    def test_sampled_indicators_never_give_the_exact_number(self):
        # r03 e' la 18ª su 20: campionario, non e' fra le ultime cinque (16-20 = 16ª o piu')
        testo = g.piazzamento_da_valori(self._venti(), "r03", "higher_better", True, "regioni", 20)
        self.assertEqual(testo, "fra le ultime cinque")
        self.assertNotIn("ª", testo)
        # r10 e' la 11ª: ne' il numero ne' la fascia
        self.assertIsNone(g.piazzamento_da_valori(self._venti(), "r10", "higher_better", True, "regioni", 20))

    def test_last_five_boundary_is_the_sixteenth_place(self):
        # 16ª su 20 e' ancora fra le ultime cinque, la 15ª no.
        valori = self._venti()
        self.assertEqual(g.piazzamento_da_valori(valori, "r05", "higher_better", True, "regioni", 20),
                         "fra le ultime cinque")
        self.assertIsNone(g.piazzamento_da_valori(valori, "r06", "higher_better", True, "regioni", 20))

    def test_a_tie_that_starts_before_the_last_five_is_not_in_them(self):
        # r05 e r06 a pari merito: 15ª tutte e due, e la 15ª non e' fra le ultime cinque
        valori = self._venti(r06=5.0)
        self.assertIsNone(g.piazzamento_da_valori(valori, "r06", "higher_better", True, "regioni", 20))

    def test_direction_resolution_never_guesses(self):
        # un id senza direzione curata non si giudica, e `higher_worse` ordina come `lower_better`
        self.assertIsNone(g.direzione("dem:POP65OVER", "regioni"))
        self.assertEqual(g.direzione("910", "regioni"), "higher_better")
        self.assertEqual(g.direzione("930", "regioni"), "lower_better")
        self.assertEqual(g.direzione("multiscopo:MULTI_ABIT_UMIDITA", "regioni"), "lower_better")

    def test_sampling_flags(self):
        self.assertTrue(g.campionario("bes:03LAV001-N22", "regioni"))
        self.assertTrue(g.campionario("multiscopo:MULTI_BMI_OBESI", "regioni"))
        self.assertTrue(g.campionario("04BEC001P", "province"))
        self.assertFalse(g.campionario("910", "regioni"))
        self.assertFalse(g.campionario("dem:BIRTHRATE", "regioni"))


class FraseTest(SenzaDati):
    def test_error_sentence_has_names_values_unit_and_year(self):
        testo = g.frase("regioni", _ind(), "errore", _t("Lazio", 21000.0), _t("Lombardia", 34000.0), [21000.0, 34000.0])
        self.assertEqual(
            testo,
            f"Hai messo il Lazio sopra la Lombardia: per «reddito per abitante» (2024) "
            f"il Lazio ha 21.000{THIN}euro, la Lombardia ha 34.000{THIN}euro, un rapporto di 1,6 volte.")

    def test_figures_are_written_like_the_site_writes_them(self):
        testo = g.frase("province", _ind(unit="anni", name="Speranza di vita"), "errore",
                        _t("Napoli", 80.4), _t("Bolzano", 83.9), [80.4, 83.9])
        # numfmt: virgola decimale, un decimale a questa grandezza, unita' dopo lo spazio fine
        self.assertIn(f"Napoli ha {numfmt.text(80.4)}{THIN}anni", testo)
        self.assertIn("80,4", testo)
        self.assertIn("83,9", testo)
        big = g.frase("province", _ind(), "errore", _t("A", 1234567.0), _t("B", 2345678.0), [1234567.0, 2345678.0])
        self.assertIn(f"1.234.567{THIN}euro", big)

    def test_percent_attaches_and_says_points(self):
        testo = g.frase("province", _ind(unit="percentuale", name="Disoccupazione"), "errore",
                        _t("Roma", 9.5), _t("Milano", 14.25), [9.5, 14.25])
        self.assertIn("Roma ha 9,5%", testo)
        self.assertIn("uno scarto di 4,8 punti percentuali", testo)
        self.assertNotIn("volte", testo)

    def test_a_unit_that_cannot_be_written_gives_no_sentence(self):
        for unita in ("numero medio", "numero", "", None, "classi", "una misura lunga con una virgola, e una coda"):
            with self.subTest(unita=unita):
                self.assertIsNone(g.frase("province", _ind(unit=unita), "errore", _t("A", 1.0), _t("B", 9.0), [1.0, 9.0]))

    def test_a_long_unit_label_is_written_in_full(self):
        testo = g.frase("province", _ind(unit="metri quadrati per abitante", name="Verde urbano"), "errore",
                        _t("Rimini", 21.5), _t("Brescia", 25.3), [21.5, 25.3])
        self.assertIn(f"21,5{THIN}metri quadrati per abitante", testo)

    def test_the_tail_after_a_comma_is_dropped_from_a_rate(self):
        self.assertEqual(g.unita_scritta("ogni 10.000 abitanti, tasso standardizzato"), "ogni 10.000 abitanti")

    def test_equal_values_give_no_sentence(self):
        self.assertIsNone(g.frase("province", _ind(), "errore", _t("A", 5.0), _t("B", 5.0), [5.0, 5.0]))

    def test_values_that_round_alike_get_more_decimals(self):
        testo = g.frase("province", _ind(unit="percentuale"), "errore", _t("A", 12.31), _t("B", 12.34), [12.31, 12.34])
        self.assertIn("A ha 12,31%", testo)
        self.assertIn("B ha 12,34%", testo)

    def test_values_that_stay_alike_give_no_sentence(self):
        self.assertIsNone(g.frase("province", _ind(unit="percentuale"), "errore",
                                  _t("A", 12.0), _t("B", 12.0000001), [12.0, 12.0000001]))

    def test_a_balance_has_no_ratio_in_the_sentence(self):
        testo = g.frase("regioni", _ind(unit="per 1.000 abitanti", name="Saldo migratorio"), "errore",
                        _t("Lazio", 2.0), _t("Veneto", 9.0), [2.0, 9.0])
        self.assertNotIn("volte", testo)
        self.assertNotIn("rapporto", testo)

    def test_negative_values_are_written_with_the_ascii_minus_and_no_ratio(self):
        testo = g.frase("regioni", _ind(unit="per 1.000 abitanti", name="Saldo"), "errore",
                        _t("Lazio", -2.5), _t("Veneto", 4.0), [-2.5, 4.0])
        self.assertIn("-2,5", testo)
        self.assertNotIn("volte", testo)

    def test_the_relation_goes_first_when_the_sentence_is_too_long(self):
        coppia = (_t("Verbano-Cusio-Ossola", 1000.0), _t("Reggio nell'Emilia", 3000.0), [1000.0, 3000.0])
        corta = g.frase("province", _ind(name="x" * 40, unit="euro"), "errore", *coppia)
        self.assertIn("un rapporto di 3,0 volte", corta)
        # con 110 caratteri di nome la frase sta in 260 solo senza la relazione
        lunga = g.frase("province", _ind(name="x" * 110, unit="euro"), "errore", *coppia)
        self.assertIsNotNone(lunga)
        self.assertNotIn("rapporto", lunga)
        self.assertLessEqual(len(lunga), 260)

    def test_a_sentence_that_cannot_fit_is_none_not_truncated(self):
        self.assertIsNone(g.frase("province", _ind(name="x" * 300), "errore", _t("A", 1.0), _t("B", 3.0), [1.0, 3.0]))

    def test_the_sentence_is_one_sentence_without_forbidden_characters(self):
        testo = g.frase("regioni", _ind(), "errore", _t("Lazio", 21000.0), _t("Lombardia", 34000.0), [21000.0, 34000.0])
        self.assertIsNotNone(g.valida(testo))
        self.assertLessEqual(len(testo), 260)

    def test_no_causal_or_value_judging_words(self):
        for caso in ("errore", "distante", "perfetto"):
            testo = g.frase("regioni", _ind(), caso, _t("Lazio", 21000.0), _t("Lombardia", 34000.0), [21000.0, 34000.0])
            for parola in ("colpa", "causa", "perché", "perche", "migliore", "peggiore", "meglio", "peggio"):
                self.assertNotIn(parola, testo.lower())

    def test_the_place_is_added_in_brackets_when_known(self):
        with mock.patch.object(g, "piazzamento", return_value="18ª su 20"):
            testo = g.frase("regioni", _ind(), "errore", _t("Lazio", 21000.0), _t("Lombardia", 34000.0), [21000.0, 34000.0])
        self.assertIn(f"il Lazio ha 21.000{THIN}euro (18ª su 20),", testo)


class OrdinaTest(SenzaDati):
    @staticmethod
    def _righe(valori, ordine):
        """positions nell'ordine del giocatore: `ordine` e' l'elenco dei nomi."""
        return [{"region": n, "region_key": n.lower(), "value": valori[n], "guessed_position": i + 1}
                for i, n in enumerate(ordine)]

    def test_it_starts_from_the_first_adjacent_mistake(self):
        valori = {"Lazio": 5.0, "Veneto": 9.0, "Puglia": 3.0, "Sicilia": 2.0, "Molise": 1.0}
        mosse = self._righe(valori, ["Lazio", "Veneto", "Puglia", "Sicilia", "Molise"])
        giusto = sorted(mosse, key=lambda r: -r["value"])
        testo = g.fatto_ordina("regioni", _ind(unit="anni"), mosse, giusto)
        self.assertTrue(testo.startswith("Hai messo il Lazio sopra il Veneto:"), testo)

    def test_a_perfect_order_starts_from_the_widest_case(self):
        valori = {"Lazio": 5.0, "Veneto": 9.0, "Puglia": 3.0, "Sicilia": 2.0, "Molise": 1.0}
        giusto = [{"region": n, "region_key": n.lower(), "value": v} for n, v in
                  sorted(valori.items(), key=lambda kv: -kv[1])]
        mosse = self._righe(valori, [r["region"] for r in giusto])
        testo = g.fatto_ordina("regioni", _ind(unit="anni"), mosse, giusto)
        self.assertTrue(testo.startswith("Tutto al posto giusto"), testo)
        self.assertIn("il Veneto ha 9,0", testo)
        self.assertIn("il Molise ha 1,0", testo)

    def test_positions_are_read_in_the_players_order_not_the_list_order(self):
        valori = {"Lazio": 5.0, "Veneto": 9.0, "Puglia": 3.0, "Sicilia": 2.0, "Molise": 1.0}
        mosse = self._righe(valori, ["Lazio", "Veneto", "Puglia", "Sicilia", "Molise"])
        rimescolate = [mosse[3], mosse[0], mosse[4], mosse[1], mosse[2]]
        testo = g.fatto_ordina("regioni", _ind(unit="anni"), rimescolate, sorted(mosse, key=lambda r: -r["value"]))
        self.assertTrue(testo.startswith("Hai messo il Lazio sopra il Veneto:"), testo)

    def test_a_missing_value_gives_no_sentence(self):
        mosse = [{"region": "Lazio", "region_key": "lazio", "value": None, "guessed_position": 1},
                 {"region": "Veneto", "region_key": "veneto", "value": 3.0, "guessed_position": 2}]
        self.assertIsNone(g.fatto_ordina("regioni", _ind(), mosse, mosse))

    def test_bad_input_gives_none(self):
        self.assertIsNone(g.fatto_ordina("regioni", _ind(), None, None))
        self.assertIsNone(g.fatto_ordina("regioni", _ind(), [], []))


class CompareTest(SenzaDati):
    @staticmethod
    def _coppia(n, ind=None, a="Lazio", b="Veneto"):
        return {"indicator": ind or _ind(unit="anni", name=f"Indicatore {n}"),
                "a": {"key": a.lower(), "name": a, "region": a}, "b": {"key": b.lower(), "name": b, "region": b}}

    @staticmethod
    def _valuta(valori):
        """valuta fasulla: i valori di ogni coppia, per l'indirizzo (a, b)."""
        def valuta(coppia, scelta):
            va, vb = valori[coppia["indicator"]["name"]]
            return {"indicator": {"path": "/indicatore/x/ter-1"},
                    "a": {**coppia["a"], "value": va}, "b": {**coppia["b"], "value": vb}}
        return valuta

    def test_with_a_mistake_it_starts_from_that_pair_and_names_the_lower_first(self):
        coppie = [self._coppia(0), self._coppia(1)]
        valori = {"Indicatore 0": (10.0, 90.0), "Indicatore 1": (50.0, 40.0)}
        fatto = g.fatto_compare("regioni", coppie, 1, self._valuta(valori))
        self.assertTrue(fatto["fact"].startswith("Hai messo il Veneto sopra il Lazio:"), fatto)
        self.assertIn("«indicatore 1»", fatto["fact"])
        self.assertEqual(fatto["path"], "/indicatore/x/ter-1")

    def test_without_a_mistake_it_takes_the_widest_relative_gap(self):
        coppie = [self._coppia(0), self._coppia(1), self._coppia(2)]
        valori = {"Indicatore 0": (10.0, 12.0), "Indicatore 1": (1.0, 9.0), "Indicatore 2": (100.0, 101.0)}
        fatto = g.fatto_compare("regioni", coppie, None, self._valuta(valori))
        self.assertTrue(fatto["fact"].startswith("La coppia più distante:"), fatto)
        self.assertIn("«indicatore 1»", fatto["fact"])

    def test_the_gap_is_relative_so_units_do_not_decide(self):
        coppie = [self._coppia(0, _ind(unit="euro", name="Grande")), self._coppia(1, _ind(unit="anni", name="Piccolo"))]
        valori = {"Grande": (20000.0, 30000.0), "Piccolo": (60.0, 90.0)}
        # lo scarto assoluto di "Grande" e' enorme, il relativo e' lo stesso (1/3): vince il primo a parita'
        fatto = g.fatto_compare("regioni", coppie, None, self._valuta(valori))
        self.assertIn("«grande»", fatto["fact"])

    def test_a_bad_error_index_falls_back_to_the_widest_pair(self):
        coppie = [self._coppia(0)]
        fatto = g.fatto_compare("regioni", coppie, 7, self._valuta({"Indicatore 0": (1.0, 9.0)}))
        self.assertTrue(fatto["fact"].startswith("La coppia più distante:"))

    def test_when_the_mistake_pair_has_no_sentence_it_falls_back(self):
        coppie = [self._coppia(0, _ind(unit="numero", name="Senza unita")), self._coppia(1)]
        valori = {"Senza unita": (1.0, 9.0), "Indicatore 1": (1.0, 9.0)}
        fatto = g.fatto_compare("regioni", coppie, 0, self._valuta(valori))
        self.assertIn("«indicatore 1»", fatto["fact"])

    def test_no_pair_with_a_sentence_gives_none(self):
        coppie = [self._coppia(0, _ind(unit="numero", name="Senza unita"))]
        self.assertIsNone(g.fatto_compare("regioni", coppie, None, self._valuta({"Senza unita": (1.0, 9.0)})))

    def test_a_pair_the_evaluator_refuses_is_skipped(self):
        coppie = [self._coppia(0), self._coppia(1)]
        valori = {"Indicatore 1": (1.0, 9.0)}

        def valuta(coppia, scelta):
            return None if coppia["indicator"]["name"] == "Indicatore 0" else self._valuta(valori)(coppia, scelta)

        fatto = g.fatto_compare("regioni", coppie, None, valuta)
        self.assertIn("«indicatore 1»", fatto["fact"])


class ErroreFirmatoTest(unittest.TestCase):
    ESITO_SBAGLIATO = {"correct": False}
    ESITO_GIUSTO = {"correct": True}

    def test_the_first_real_mistake_is_remembered(self):
        self.assertEqual(g.errore_firmato({}, "2026-09-30", 3, self.ESITO_SBAGLIATO, "region_a"), {"e": 3})

    def test_a_later_mistake_does_not_replace_the_first(self):
        precedente = {"d": "2026-09-30", "c": 2, "l": "regioni", "e": 3}
        self.assertEqual(g.errore_firmato(precedente, "2026-09-30", 6, self.ESITO_SBAGLIATO, "region_b"), {"e": 3})
        self.assertEqual(g.errore_firmato(precedente, "2026-09-30", 6, self.ESITO_GIUSTO, "region_b"), {"e": 3})

    def test_a_correct_answer_remembers_nothing(self):
        self.assertEqual(g.errore_firmato({}, "2026-09-30", 0, self.ESITO_GIUSTO, "region_a"), {})

    def test_a_timeout_is_not_a_mistake_of_judgement(self):
        self.assertEqual(g.errore_firmato({}, "2026-09-30", 0, self.ESITO_SBAGLIATO, "timeout"), {})

    def test_the_memory_resets_when_the_day_changes(self):
        precedente = {"d": "2026-09-29", "c": 9, "l": "regioni", "e": 3}
        self.assertEqual(g.errore_firmato(precedente, "2026-09-30", 1, self.ESITO_GIUSTO, "region_a"), {})
        self.assertEqual(g.errore_firmato(precedente, "2026-09-30", 1, self.ESITO_SBAGLIATO, "region_a"), {"e": 1})


if __name__ == "__main__":
    unittest.main()
