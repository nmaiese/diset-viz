"""Il cancello unico: ogni regola su prosa costruita apposta.

Su prosa sintetica e non sul catalogo, per la ragione che ha lasciato passare
67 indicatori provinciali: una guardia che non incontra niente da controllare
resta verde e non lo dice. Qui ogni regola vede il caso che deve prendere e il
caso che deve lasciar passare.
"""
import unittest
import unittest.mock

from officina import lint


def entry(**overrides):
    base = {
        "level": "regione",
        "lead": "Una prima frase che sta dentro i limiti.",
        "vintage": 2023,
        "sections": [
            {"role": "quadro", "h": "Un vertice", "body": "Corpo del quadro."},
            {"role": "dinamica", "h": "Sei anni", "body": "Corpo della dinamica."},
            {"role": "limiti", "h": "Che cosa non dice", "body": "Corpo dei limiti."},
        ],
    }
    base.update(overrides)
    return base


def rules_fired(found):
    return {finding["rule"] for finding in found}


class BannedCharacters(unittest.TestCase):
    def test_an_em_dash_blocks(self):
        found = lint.check_banned_characters(entry(lead="Un lead — con il trattino."))
        self.assertEqual(rules_fired(found), {"caratteri-vietati"})
        self.assertEqual(found[0]["severity"], lint.BLOCKS)

    def test_it_looks_inside_authored_titles_too(self):
        found = lint.check_banned_characters(entry(h1="Un titolo; con punto e virgola"))
        self.assertEqual(found[0]["field"], "h1")

    def test_clean_prose_passes(self):
        self.assertEqual(lint.check_banned_characters(entry()), [])


class TheLead(unittest.TestCase):
    def test_a_missing_lead_blocks(self):
        self.assertEqual(rules_fired(lint.check_lead(entry(lead=""))), {"lead"})

    def test_a_first_sentence_too_long_to_be_a_meta_description_blocks(self):
        found = lint.check_lead(entry(lead="parola " * 60 + "."))
        self.assertEqual(rules_fired(found), {"lead"})

    def test_a_long_lead_with_a_short_first_sentence_passes(self):
        """Conta la prima frase, non il lead: e' quella che finisce in SERP."""
        self.assertEqual(lint.check_lead(entry(lead="Corta. " + "parola " * 60)), [])


class Figures(unittest.TestCase):
    ALTERNATION = "Emilia-Romagna|Campania|Gorizia|Molise"

    def setUp(self):
        self.compiled = lint.patterns(self.ALTERNATION)
        self.compiled["alternation"] = self.ALTERNATION
        self.values = {"Campania": 40.1, "Gorizia": 18.0, "Molise": 5.0}
        # Un anno passato con valori diversi: serve a provare che una cifra con
        # l'anno scritto accanto e' giudicata contro **quell'anno**.
        self.storici = {2020: {"Campania": 21.8}}

    def _run(self, text):
        item = entry(sections=[{"role": "quadro", "h": "h", "body": text}])
        saved = lint.values_of
        lint.values_of = (lambda key, e, year=None:
                          self.storici.get(year, self.values) if year else self.values)
        try:
            return lint.check_figures(item, key="ter:1", compiled=self.compiled)
        finally:
            lint.values_of = saved

    def test_a_wrong_figure_before_the_territory_blocks(self):
        self.assertEqual(rules_fired(self._run("Il 21,8% della Campania.")),
                         {"cifra-falsa"})

    def test_a_right_figure_before_the_territory_passes(self):
        self.assertEqual(self._run("Il 40,1% della Campania."), [])

    def test_a_wrong_figure_after_the_territory_blocks(self):
        """Il verso che la prosa provinciale usa davvero."""
        self.assertEqual(rules_fired(self._run("Gorizia si ferma a 44.")),
                         {"cifra-falsa"})

    def test_an_integer_close_enough_passes(self):
        self.assertEqual(self._run("Gorizia si ferma a 18."), [])

    def test_a_gap_is_not_a_level(self):
        self.assertEqual(self._run("Il Molise sta 39,4 punti sopra le Marche."), [])

    def test_an_explicit_other_year_is_judged_against_that_year(self):
        """Non piu' saltata: controllata contro l'anno che nomina.

        Prima veniva esclusa, per non giudicarla contro l'anno corrente. Ma
        saltarla lasciava scoperte proprio le cifre storiche, che la macchina
        nuova produce in quantita': gli angoli del pacchetto sono quasi tutti
        nel tempo.
        """
        self.assertEqual(self._run("La Campania si ferma a 21,8 nel 2020."), [])

    def test_a_wrong_figure_for_that_other_year_blocks(self):
        found = self._run("La Campania si ferma a 40,1 nel 2020.")
        self.assertEqual(rules_fired(found), {"cifra-falsa"})
        self.assertIn("nel 2020", found[0]["detail"])

    def test_figures_of_a_linked_series_are_not_ours(self):
        self.assertEqual(
            self._run("Il [tasso](/indicatore/x/ter-407), dove la Campania "
                      "si ferma a 21,80."), [])

    def test_a_false_threshold_blocks(self):
        self.assertEqual(rules_fired(self._run("Supera il 50% in Campania.")),
                         {"soglia-falsa"})

    def test_a_true_threshold_passes(self):
        self.assertEqual(self._run("Supera il 30% in Campania."), [])


class HistoricalFiguresAreCheckedNotSkipped(unittest.TestCase):
    """Una cifra con l'anno accanto si controlla contro quell'anno.

    L'esclusione nasceva da un falso allarme vero ("la Sardegna segna 81,67 nel
    2020" giudicato contro l'anno corrente), ma nascondeva un buco che la
    macchina nuova allarga: gli angoli del pacchetto sono quasi tutti storici
    (rotture di pendenza, ritorni a un livello, sorpassi), quindi la prosa cita
    molte piu' cifre di anni passati di quante ne citasse quella vecchia, e
    nessuna era controllata.
    """

    MATRICE = {"2020": {"cam": 10.0}, "2025": {"cam": 20.0}}

    def setUp(self):
        self.saved = lint.view_level
        # `territories` e non `observations`: la mappa dei nomi si legge da li',
        # perche' `observations` copre solo l'ultimo anno e un territorio con
        # dati solo negli anni vecchi resterebbe senza nome, quindi fuori da
        # ogni controllo. Uno stub che usasse `observations` proverebbe una
        # versione del codice che non esiste piu'.
        lint.view_level = lambda key, entry: {
            "year_max": 2025, "matrix": self.MATRICE,
            "territories": [{"key": "cam", "name": "Campania"}],
            "observations": [{"key": "cam", "name": "Campania"}]}
        self.addCleanup(lambda: setattr(lint, "view_level", self.saved))
        self.compiled = lint.patterns("Campania")
        self.compiled["alternation"] = "Campania"

    def _run(self, text):
        item = entry(vintage=2025,
                     sections=[{"role": "quadro", "h": "h", "body": text}])
        return lint.check_figures(item, key="ter:1", compiled=self.compiled)

    def test_a_true_historical_figure_passes(self):
        self.assertEqual(self._run("La Campania segna 10,00 nel 2020."), [])

    def test_a_false_historical_figure_blocks(self):
        found = self._run("La Campania segna 17,40 nel 2020.")
        self.assertEqual(rules_fired(found), {"cifra-falsa"})
        self.assertIn("nel 2020", found[0]["detail"])

    def test_the_current_year_figure_is_not_judged_against_the_old_one(self):
        """Il falso allarme che aveva prodotto l'esclusione, al contrario."""
        self.assertEqual(self._run("La Campania segna 20,00."), [])

    def test_a_year_the_source_does_not_publish_is_not_invented(self):
        self.assertEqual(self._run("La Campania segna 99,00 nel 1999."), [])

    def test_the_value_first_syntax_honours_the_year_too(self):
        """La regola era scritta in un verso solo.

        La prosa scrive una cifra in due modi, e questo file li copre tutti e
        due da sempre ("il 24,3% del Molise" e "Gorizia si ferma a 18"). L'anno
        accanto pero' lo leggeva **solo** il secondo: la stessa affermazione
        vera passava girata in un modo e prendeva un `cifra-falsa` girata
        nell'altro, cioe' un blocco che rimanda chi scrive a correggere un
        numero corretto. E' il verso che l'officina usa piu' spesso, perche' un
        angolo si apre nominando la cifra.
        """
        self.assertEqual(self._run("Il 10,00% della Campania nel 2020 era un altro paese."), [])

    def test_and_it_still_catches_a_false_one(self):
        found = self._run("Il 17,40% della Campania nel 2020 non torna.")
        self.assertEqual(rules_fired(found), {"cifra-falsa"})
        self.assertIn("nel 2020", found[0]["detail"])

    def test_a_threshold_honours_the_year_as_well(self):
        """Il terzo ramo. La regola era scritta per uno su tre.

        `check_figures` legge la prosa con tre pattern (valore-prima,
        verbo-prima, soglia) e l'anno accanto lo leggeva solo il secondo. Una
        soglia vera per l'anno che nomina veniva giudicata contro l'anno
        dell'articolo, cioe' `soglia-falsa` su una frase corretta.
        """
        self.assertEqual(self._run("Restava sotto il 12,00 in Campania nel 2020."), [])

    def test_and_a_false_threshold_in_that_year_still_blocks(self):
        found = self._run("Supera il 18,00 in Campania nel 2020.")
        self.assertEqual(rules_fired(found), {"soglia-falsa"})
        self.assertIn("nel 2020", found[0]["detail"])

    def test_a_threshold_without_a_year_is_judged_on_the_article_year(self):
        self.assertEqual(rules_fired(self._run("Restava sotto il 12,00 in Campania.")),
                         {"soglia-falsa"})
        self.assertEqual(self._run("Supera il 18,00 in Campania."), [])

    def test_a_threshold_is_not_also_read_as_a_value(self):
        """Due regole sullo stesso pezzo di testo, e una delle due sbagliata.

        "restava sotto il 12,00 in Campania" non dice che la Campania valga 12:
        dice che sta sotto 12. Il ramo valore-prima la leggeva come un valore e
        aggiungeva un `cifra-falsa` alla frase, anche quando la soglia era vera
        e il ramo giusto taceva. E' la stessa soppressione che
        `states_a_value` fa gia' per "circa" e "quasi", dall'altro lato.
        """
        for testo in ("Restava sotto il 12,00 in Campania nel 2020.",
                      "Restava sotto il 12,00 in Campania.",
                      "Supera il 18,00 in Campania nel 2020."):
            with self.subTest(testo=testo):
                self.assertNotIn("cifra-falsa", rules_fired(self._run(testo)))

    def test_the_two_syntaxes_agree_on_every_case(self):
        """La proprieta', non i due esempi: girare la frase non cambia il verdetto."""
        for cifra, atteso in (("10,00", set()), ("17,40", {"cifra-falsa"}), ("20,00", {"cifra-falsa"})):
            with self.subTest(cifra=cifra):
                valore_prima = self._run(f"Il {cifra}% della Campania nel 2020 pesa.")
                verbo_prima = self._run(f"La Campania segna {cifra} nel 2020.")
                self.assertEqual(rules_fired(valore_prima), atteso)
                self.assertEqual(rules_fired(verbo_prima), atteso)


class DynamicsMustCiteASource(unittest.TestCase):
    """La regola nuova, quella che toglie il freddo."""

    def setUp(self):
        self.saved_view = lint.view_of
        self.saved_ctx = lint.context_module.for_indicator
        self.saved_claims = lint.context_module.claims
        lint.view_of = lambda key: {"meta": {"theme": "Un tema", "name": "Un nome"}}

    def tearDown(self):
        lint.view_of = self.saved_view
        lint.context_module.for_indicator = self.saved_ctx
        lint.context_module.claims = self.saved_claims

    def _with_corpus(self, ids, esistenti=None):
        """`ids` sono le affermazioni offerte a QUESTO indicatore.

        `esistenti` sono tutte quelle del corpus: le due liste differiscono
        quando un'affermazione esiste ma non riguarda questa serie, che e' il
        caso `fonte-non-pertinente`.
        """
        lint.context_module.for_indicator = (
            lambda k, t, limit=50, indicator_name=None: [{"id": n} for n in ids])
        tutte = ids if esistenti is None else esistenti
        lint.context_module.claims = lambda: [{"id": n} for n in tutte]

    def test_no_source_when_the_corpus_has_some_is_flagged(self):
        self._with_corpus(["a", "b"])
        found = lint.check_dynamics_cite_a_source(entry(), key="ter:1")
        self.assertEqual(rules_fired(found), {"dinamica-senza-fonte"})
        self.assertEqual(found[0]["severity"], lint.FLAGS)

    def _dinamica_che_cita(self, *ids):
        """Un'entry con l'identificatore attaccato **alla dinamica**, che e' la
        forma che il controllo posizionale pretende."""
        voce = entry()
        for sezione in voce["sections"]:
            if sezione["role"] == "dinamica":
                sezione["claims"] = list(ids)
        return voce

    def test_citing_a_real_id_on_the_dynamics_passes(self):
        self._with_corpus(["a", "b"])
        found = lint.check_dynamics_cite_a_source(self._dinamica_che_cita("a"), key="ter:1")
        self.assertEqual(found, [])

    def test_a_corpus_field_alone_does_not_satisfy_a_positional_check(self):
        """Il difetto che questo controllo aveva, scritto come caso.

        Il campo `corpus` a livello di entry e' **obbligatorio** nello schema
        della bozza, i `claims` di sezione no: leggendo l'unione dei due, una
        bozza normale zittiva il controllo senza attaccare niente alla dinamica.
        Il rilievo non usciva mai, e la regola che esiste per togliere il freddo
        era spenta nel caso comune, non in un caso limite. Questo test asseriva
        il contrario, cioe' era il difetto scritto come aspettativa."""
        self._with_corpus(["a", "b"])
        found = lint.check_dynamics_cite_a_source(entry(corpus=["a"]), key="ter:1")
        self.assertEqual(rules_fired(found), {"dinamica-senza-fonte"})
        self.assertIn("altre sezioni", found[0]["detail"])

    def test_a_claim_on_another_section_does_not_cover_the_dynamics(self):
        """Stessa regola, l'altra meta': l'attribuzione ha un posto, e un
        identificatore attaccato al `quadro` non dice niente sulla dinamica."""
        self._with_corpus(["a", "b"])
        voce = entry()
        for sezione in voce["sections"]:
            if sezione["role"] == "quadro":
                sezione["claims"] = ["a"]
        found = lint.check_dynamics_cite_a_source(voce, key="ter:1")
        self.assertEqual(rules_fired(found), {"dinamica-senza-fonte"})

    def test_a_wrong_citation_is_caught_wherever_it_hangs(self):
        """Le altre due domande restano sull'entry intera, e devono restarci: una
        fonte inventata o fuori tema e' un difetto della pagina pubblica
        qualunque sezione la porti. Se anche queste diventassero posizionali,
        spostare la citazione su un'altra sezione la farebbe sparire."""
        self._with_corpus(["a"], esistenti=["a"])
        voce = entry(corpus=["inesistente"])
        found = lint.check_dynamics_cite_a_source(voce, key="ter:1")
        self.assertEqual(rules_fired(found), {"fonte-inesistente"})
        self.assertEqual(found[0]["severity"], lint.BLOCKS)

    def test_citing_an_id_that_does_not_exist_blocks(self):
        """Il modo piu' facile di zittire un lint e' inventare la fonte."""
        self._with_corpus(["a"])
        found = lint.check_dynamics_cite_a_source(entry(corpus=["inventata"]), key="ter:1")
        self.assertEqual(rules_fired(found), {"fonte-inesistente"})
        self.assertEqual(found[0]["severity"], lint.BLOCKS)

    def test_an_empty_corpus_blames_the_corpus_not_the_article(self):
        self._with_corpus([])
        found = lint.check_dynamics_cite_a_source(entry(), key="ter:1")
        self.assertIn("il corpus non ha niente", found[0]["detail"])

    def test_an_article_without_a_dinamica_is_not_asked_for_a_source(self):
        self._with_corpus(["a"])
        item = entry(sections=[{"role": "quadro", "h": "h", "body": "x"}])
        self.assertEqual(lint.check_dynamics_cite_a_source(item, key="ter:1"), [])

    def test_a_real_quote_about_another_indicator_blocks(self):
        """Il caso peggiore da leggere: regge a ogni controllo tranne quello che conta.

        Nella prima run la citazione Eurostat sulla sensibilita' ciclica della
        disoccupazione di lunga durata e' finita a spiegare il **tasso di
        attivita'**, perche' condividono il tema. La frase esiste, l'URL c'e',
        la verifica come stringa passa. E l'attribuzione e' falsa lo stesso.
        """
        self._with_corpus([], esistenti=["eurostat-lunga-durata-ciclo"])
        found = lint.check_dynamics_cite_a_source(
            entry(corpus=["eurostat-lunga-durata-ciclo"]), key="ter:1")
        self.assertEqual(rules_fired(found), {"fonte-non-pertinente"})
        self.assertEqual(found[0]["severity"], lint.BLOCKS,
                         "un'attribuzione falsa su una pagina pubblica non e' un avviso")

    def test_an_invented_id_and_a_misapplied_one_are_different_findings(self):
        """Inventare una fonte e usarne male una vera sono due errori diversi,
        e chi ripara deve sapere quale ha fatto."""
        self._with_corpus(["a"], esistenti=["a", "b"])
        inventata = lint.check_dynamics_cite_a_source(entry(corpus=["zzz"]), key="ter:1")
        fuori = lint.check_dynamics_cite_a_source(entry(corpus=["b"]), key="ter:1")
        self.assertEqual(rules_fired(inventata), {"fonte-inesistente"})
        self.assertEqual(rules_fired(fuori), {"fonte-non-pertinente"})


class PositiveRequirements(unittest.TestCase):
    def test_an_article_that_never_says_what_the_number_cannot_say(self):
        item = entry(sections=[{"role": "quadro", "h": "h", "body": "parola " * 400}])
        self.assertIn("manca-il-limite", rules_fired(
            lint.check_positive_requirements(item, key="ter:1")))

    def test_too_short_is_flagged_not_blocked(self):
        found = lint.check_positive_requirements(entry(), key="ter:1")
        short = [f for f in found if f["rule"] == "troppo-corto"]
        self.assertTrue(short)
        self.assertEqual(short[0]["severity"], lint.FLAGS)


class DistanceFromSiblings(unittest.TestCase):
    def test_two_near_identical_articles_block_each_other(self):
        body = " ".join(f"parola{index}" for index in range(200))
        one = entry(sections=[{"role": "quadro", "h": "a", "body": body}])
        two = entry(sections=[{"role": "quadro", "h": "b", "body": body}])
        found = lint.check_distance_from_siblings(
            one, key="ter:1", texts={"ter:1": one, "ter:2": two})
        self.assertEqual(rules_fired(found), {"gemello"})
        self.assertEqual(found[0]["severity"], lint.BLOCKS)

    def test_two_different_articles_do_not(self):
        one = entry(sections=[{"role": "quadro", "h": "a",
                               "body": " ".join(f"alfa{i}" for i in range(200))}])
        two = entry(sections=[{"role": "quadro", "h": "b",
                               "body": " ".join(f"beta{i}" for i in range(200))}])
        self.assertEqual(lint.check_distance_from_siblings(
            one, key="ter:1", texts={"ter:1": one, "ter:2": two}), [])

    def test_a_stub_is_too_short_to_judge(self):
        one = entry(sections=[{"role": "quadro", "h": "a", "body": "due parole"}])
        self.assertEqual(lint.check_distance_from_siblings(
            one, key="ter:1", texts={"ter:1": one, "ter:2": one}), [])


class Severities(unittest.TestCase):
    def test_every_rule_declares_one_of_the_two(self):
        self.assertEqual({lint.BLOCKS, lint.FLAGS}, {"blocca", "segnala"})

    def test_a_rule_that_blocks_is_about_truth_not_taste(self):
        """Il gusto non blocca. E' cio' che la rubrica a venti punti sbagliava."""
        blocking = {"caratteri-vietati", "lead", "cifra-falsa", "soglia-falsa",
                    "fonte-inesistente", "gemello"}
        flagging = {"dinamica-senza-fonte", "manca-il-limite", "troppo-corto"}
        self.assertFalse(blocking & flagging)


if __name__ == "__main__":
    unittest.main()


class TheDefinitionIsCheckedAgainstTheSource(unittest.TestCase):
    """La grandezza, non le cifre intorno.

    Ogni altra regola di `officina/lint.py` confronta la prosa con la serie.
    Questa confronta cio' che l'articolo dice di misurare con le parole della
    fonte, ed e' la classe di errore che sopravvive a ogni lettura perche'
    l'aritmetica intorno e' giusta: `ter-30` spiegava una domanda per circuito
    museale mentre la fonte divide i visitatori per il numero di istituti, e
    `ter-402` chiamava "imprese a guida femminile" quello che Istat definisce
    come donne titolari di ditte individuali.
    """

    DEFINIZIONE = {
        "id": "30",
        "indicatore": "Indice di domanda culturale (circuiti museali)",
        "definizione": ("Numero di visitatori dei circuiti sul totale di musei e "
                        "istituti similari appartenenti ai circuiti"),
    }

    def _rilievi(self, prosa):
        voce = entry(sections=[
            {"role": "definizione", "h": "Che cosa misura", "body": prosa},
            {"role": "quadro", "h": "Un vertice", "body": "Corpo del quadro."},
            {"role": "dinamica", "h": "Sei anni", "body": "Corpo della dinamica."},
            {"role": "limiti", "h": "Che cosa non dice", "body": "Corpo dei limiti."},
        ])
        with unittest.mock.patch.object(lint, "_official_definitions",
                                        lambda: {"30": self.DEFINIZIONE}):
            return lint.check_definition(voce, key="30")

    def test_an_article_that_paraphrases_the_source_passes(self):
        buona = ("Istat divide il numero di visitatori dei circuiti per il totale "
                 "di musei e istituti similari appartenenti ai circuiti: quello "
                 "che esce e' un carico medio per istituto.")
        self.assertEqual(self._rilievi(buona), [])

    def test_a_missing_denominator_is_flagged_not_blocked(self):
        """Trentacinque articoli del catalogo stanno qui, ed e' l'arretrato
        scritto prima che il pacchetto portasse la definizione: bloccare
        vorrebbe dire fermare la produzione per riscriverlo."""
        muta = ("L'indicatore dice quanta domanda culturale arriva a una regione, "
                "in migliaia, e non ha un verso.")
        rilievi = self._rilievi(muta)
        self.assertTrue(rilievi)
        self.assertTrue(all(r["severity"] == lint.FLAGS for r in rilievi))
        self.assertIn("definizione-base", {r["rule"] for r in rilievi})

    def test_an_indicator_without_official_metadata_is_silent(self):
        """`scoperto` descrive la nostra copertura, non l'onesta' dell'articolo:
        un articolo senza definizione ufficiale da confrontare non prende
        rilievi, prende silenzio.

        Provato azzerando le definizioni invece che nominando una famiglia
        scoperta. Il caso diceva `bes:10AMB004`, e nel frattempo
        `data/definitions/federated.csv` ha coperto anche quello: il test
        cadeva non perche' la regola fosse rotta, ma perche' la copertura era
        migliorata. Un test sulla regola non deve dipendere da quanti metadati
        abbiamo scaricato oggi."""
        voce = entry()
        with unittest.mock.patch.object(lint, "_official_definitions", dict):
            self.assertEqual(lint.check_definition(voce, key="bes:10AMB004"), [])

    def test_an_omitted_definition_section_does_not_fire(self):
        """La macchina nuova omette la definizione quando l'angolo piu' forte non
        e' definitorio, ed e' il comportamento voluto: `assente` scatta su 149
        articoli e non entra fra i rilievi."""
        voce = entry()
        with unittest.mock.patch.object(lint, "_official_definitions",
                                        lambda: {"30": self.DEFINIZIONE}):
            rilievi = lint.check_definition(voce, key="30")
        self.assertNotIn("definizione-assente", {r["rule"] for r in rilievi})


class TheAngleHasToBeOneThatWasDetected(unittest.TestCase):
    """L'articolo dichiara su che angolo apre: quel nome dev'essere vero.

    L'officina lancia sempre due scritture, sull'angolo 1 e sull'angolo 2, e su
    11 indicatori su 594 il pacchetto ne ha meno di due. La seconda richiesta
    non ha risposta valida, e lo schema della bozza controlla la **forma** del
    campo `angolo` e non la sua provenienza: un nome inventato attraversava
    giudizio, lint e pubblicazione senza che una riga lo nominasse.

    Il pacchetto ora lo dice a chi scrive, e questa regola lo verifica: senza,
    resterebbe un'istruzione che nessuno controlla, cioe' una speranza.

    Il pacchetto e' finto apposta. Il vero costa una vista completa
    dell'indicatore, e la regola non ha niente da imparare dai dati reali: deve
    solo confrontare due stringhe e scegliere se parlare.
    """

    @staticmethod
    def _pack(*tipi):
        return {"angles": [{"type": t} for t in tipi]}

    def _check(self, voce, tipi=("divario-che-si-chiude", "sorpasso")):
        with unittest.mock.patch.object(lint.pack_build, "_resolve",
                                        lambda code: ("territorial", "30")), \
             unittest.mock.patch.object(lint.pack_build, "build_pack",
                                        lambda *a, **k: self._pack(*tipi)):
            return lint.check_angle_was_detected(voce, key="30")

    def test_an_angle_the_pack_never_detected_blocks(self):
        rilievi = self._check(entry(angolo="rimonta-del-mezzogiorno"))
        self.assertEqual([r["rule"] for r in rilievi], ["angolo-non-rilevato"])
        self.assertEqual(rilievi[0]["severity"], lint.BLOCKS)

    def test_and_the_message_names_the_angles_that_did_exist(self):
        """Chi legge il rilievo deve sapere su che cosa poteva aprire."""
        rilievi = self._check(entry(angolo="rimonta-del-mezzogiorno"))
        self.assertIn("divario-che-si-chiude", rilievi[0]["detail"])
        self.assertIn("sorpasso", rilievi[0]["detail"])

    def test_an_angle_that_was_detected_passes(self):
        self.assertEqual(self._check(entry(angolo="sorpasso")), [])

    def test_an_article_that_declares_nothing_is_left_alone(self):
        """`angolo` e' facoltativo: 2 articoli su 377 lo scrivono. La regola
        tace sugli altri 375 senza costruire un solo pacchetto, che e' anche
        perche' `lint_all` resta a undici secondi."""
        with unittest.mock.patch.object(lint.pack_build, "build_pack") as costruisci:
            self.assertEqual(lint.check_angle_was_detected(entry(), key="30"), [])
            self.assertEqual(lint.check_angle_was_detected(entry(angolo=""), key="30"), [])
            costruisci.assert_not_called()

    def test_an_indicator_with_no_pack_is_silent_not_red(self):
        """Un pacchetto che non si costruisce e' un guasto di dati, non un
        articolo che mente: la regola si spegne come fa quella sulle
        definizioni, invece di rompere il lint su tutto il catalogo."""
        voce = entry(angolo="sorpasso")
        with unittest.mock.patch.object(lint.pack_build, "build_pack",
                                        lambda *a, **k: None):
            self.assertEqual(lint.check_angle_was_detected(voce, key="30"), [])
        with unittest.mock.patch.object(lint.pack_build, "build_pack",
                                        side_effect=KeyError("boom")):
            self.assertEqual(lint.check_angle_was_detected(voce, key="30"), [])
