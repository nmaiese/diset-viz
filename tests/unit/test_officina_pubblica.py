"""Lo stadio `pubblica`: la mappa bozza -> entry è codice, non un turno di agente.

Il pubblicatore componeva da solo l'entry dello store, e per farlo apriva
`indicator_store.py`, i template e le viste: otto turni nella prova, ventuno e
ventiquattro nella prima run, per far uscire zero a un linter. Chiave interna,
livello, vintage e forma del file non sono decisioni editoriali, quindi non
possono costare un turno a ogni articolo.

L'altra metà è che questo comando **rifiuta** invece di scrivere male: un
cancello che accetta ciò che non capisce non è un cancello.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
import unittest.mock

from officina import lint, pubblica
from scripts import indicator_store

BOZZA = {
    "lead": "Un lead con l'apostrofo.",
    "sections": [
        {"role": "quadro", "h": "Che cosa dice", "body": "Corpo del quadro.", "claims": []},
        {"role": "dinamica", "h": "Come cambia", "body": "Corpo della dinamica."},
        {"role": "limiti", "h": "Che cosa non dice", "body": "Corpo dei limiti."},
    ],
    "corpus": [],
    "angolo": "graduatoria-spezzata",
}


class ItMapsADraftOntoAnEntry(unittest.TestCase):
    def test_the_key_comes_from_the_url_form(self):
        self.assertEqual(pubblica.chiave("ter-30"), "30")
        self.assertEqual(pubblica.chiave("bes-10AMB004"), "bes:10AMB004")

    def test_level_and_vintage_are_filled_by_the_code(self):
        entry = pubblica.entry(BOZZA, "ter-30")
        self.assertEqual(entry["level"], "regione")
        self.assertIsInstance(entry["vintage"], int)
        self.assertEqual([s["role"] for s in entry["sections"]],
                         ["quadro", "dinamica", "limiti"])

    def test_the_draft_does_not_carry_its_own_passport(self):
        """`origine` non si mette montando il dizionario, si guadagna.

        Non è una firma: è la porta da cui l'articolo entra nella coda di
        verifica e in quella di lettura, che senza di lui non lo vedono. Scriverlo
        qui vuol dire scriverlo **prima** che il cancello abbia parlato, e un
        articolo bocciato lo portava lo stesso. Adesso lo mette `main` dopo aver
        letto `bloccanti`, e questa prova esiste perché rimettercelo per comodità
        è una riga sola.
        """
        self.assertNotIn("origine", pubblica.entry(BOZZA, "ter-30"))

    def test_it_does_not_declare_roles_covered(self):
        # Lo deriva `app.indicator_texts.emitted_roles` dalle sezioni scritte.
        # Dichiararlo qui sarebbe la seconda copia della stessa lista.
        self.assertNotIn("roles_covered", pubblica.entry(BOZZA, "ter-30"))

    def test_unknown_fields_do_not_reach_the_file(self):
        sporca = dict(BOZZA, feedback={"stato": "applicato"}, note_di_lavorazione="x")
        entry = pubblica.entry(sporca, "ter-30")
        self.assertNotIn("feedback", entry)
        self.assertNotIn("note_di_lavorazione", entry)


class ItRefusesInsteadOfGuessing(unittest.TestCase):
    def rifiuto(self, bozza, code="ter-30"):
        with self.assertRaises(pubblica.Rifiutata) as caso:
            pubblica.entry(bozza, code)
        return str(caso.exception)

    def test_an_invented_role_is_named(self):
        bozza = dict(BOZZA, sections=[{"role": "scala", "body": "x"}])
        self.assertIn("scala", self.rifiuto(bozza))

    def test_an_empty_body_stops_it(self):
        bozza = dict(BOZZA, sections=[dict(BOZZA["sections"][0], body="  ")])
        self.assertIn("corpo", self.rifiuto(bozza))

    def test_a_missing_lead_stops_it(self):
        self.assertIn("lead", self.rifiuto(dict(BOZZA, lead="")))

    def test_two_sections_with_the_same_role_stop_it(self):
        """Uscito al primo giro della macchina nuova: due `dinamica` con due
        titoli diversi. Il renderer indicizzava per ruolo, quindi la pagina
        rendeva un corpo due volte e perdeva l'altro, senza che nessuna guardia
        lo vedesse."""
        doppia = dict(BOZZA, sections=[
            {"role": "dinamica", "h": "A", "body": "Primo corpo."},
            {"role": "dinamica", "h": "B", "body": "Secondo corpo."},
        ])
        self.assertIn("due sezioni con ruolo", self.rifiuto(doppia))

    def test_an_indicator_outside_the_catalogue_stops_it(self):
        self.assertIn("catalogo", self.rifiuto(BOZZA, "ter-99999"))

    def test_a_level_the_indicator_does_not_have_stops_it(self):
        with self.assertRaises(pubblica.Rifiutata) as caso:
            pubblica.entry(BOZZA, "ter-30", level="comune")
        self.assertIn("comune", str(caso.exception))


class ItWritesWhereTheStoreExpects(unittest.TestCase):
    def test_the_file_lands_and_reads_back(self):
        with tempfile.TemporaryDirectory(prefix="pubblica-") as root:
            entry = pubblica.entry(BOZZA, "ter-30")
            path = indicator_store.write(pubblica.chiave("ter-30"), entry, root=root)
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                letta = json.load(handle)
            self.assertEqual(letta["key"], "30")
            self.assertEqual(letta["lead"], BOZZA["lead"])


class OnlyAnArticleThatPassedTheGateGetsItsOrigin(unittest.TestCase):
    """`origine: officina` è l'unica porta verso le due code a valle.

    L'officina non ha un revisore che firmi, quindi
    `verification_queue.build_queue()` e `reading_queue._eligible()` guardano
    quel campo e nient'altro. Scritto mentre si montava il dizionario, cioè
    prima del lint, un articolo **bocciato** lo portava lo stesso: sovrascriveva
    il precedente, veniva reso dall'app, ed entrava in tutte e due le code, dove
    i due critici indipendenti sprecavano un giro su una prosa già respinta.

    E riguardava anche la regola `angolo-non-rilevato` aggiunta due commit fa:
    bloccava, e l'articolo bloccato passava lo stesso.
    """

    def _main(self, bozza, code="ter-30", root=None, precedenti=None):
        """Esegue `main` con la bozza su stdin, dentro uno store temporaneo.

        `precedenti` sostituisce lo store che `main` legge per sapere se sotto
        la bozza c'è già un articolo: `{}` è una prima pubblicazione, un
        dizionario con la chiave dentro è una riscrittura. `None` lascia lo
        store vivo, dove `30` esiste.
        """
        scritte = {}

        def finta_write(key, entry, root=None):
            scritte["key"], scritte["entry"] = key, entry
            return f"/finto/{key}.json"

        contesti = [
            unittest.mock.patch.object(pubblica.indicator_store, "write", finta_write),
            unittest.mock.patch.object(pubblica.sys, "stdin",
                                       io.StringIO(json.dumps(bozza))),
        ]
        if precedenti is not None:
            contesti.append(unittest.mock.patch.object(
                pubblica.indicator_store, "load_all", lambda *a, **k: dict(precedenti)))

        rumore = io.StringIO()
        with contextlib.ExitStack() as stack:
            for contesto in contesti:
                stack.enter_context(contesto)
            stack.enter_context(contextlib.redirect_stdout(rumore))
            stack.enter_context(contextlib.redirect_stderr(rumore))
            codice = pubblica.main([code])
        return codice, scritte.get("entry", {}), rumore.getvalue()

    def test_a_clean_draft_earns_it(self):
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi", lambda key, fatta: []):
            codice, entry, _ = self._main(BOZZA)
        self.assertEqual(codice, 0)
        self.assertEqual(entry["origine"], "officina")

    def test_a_blocked_draft_is_written_without_it(self):
        """Scritta lo stesso, e senza il campo.

        Rifiutare la scrittura romperebbe il giro di riparazione: il workflow
        legge l'uscita 2 come "non è scritta", tornerebbe a chi scrive con un
        messaggio di forma invece che con i rilievi, e il lint successivo
        girerebbe sull'articolo **vecchio**.
        """
        fermo = [{"rule": "cifra-falsa", "severity": "blocca", "detail": "x", "field": None}]
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi", lambda key, fatta: fermo):
            codice, entry, _ = self._main(BOZZA, precedenti={})
        self.assertEqual(codice, 0, "l'articolo è scritto: l'uscita non cambia")
        self.assertNotIn("origine", entry)

    def test_the_gate_it_runs_is_the_same_one(self):
        """Non una seconda regola: lo stesso `lint_entry` di `officina.lint`.

        Due cancelli che giudicano lo stesso articolo sono due cancelli che
        prima o poi divergono, ed è la classe di difetto che questa PR chiude.
        """
        visto = {}

        def finto_lint_entry(key, entry, texts=None, compiled=None):
            visto["key"], visto["entry"], visto["texts"] = key, entry, texts
            return [{"rule": "gemello", "severity": lint.BLOCKS, "detail": "", "field": None},
                    {"rule": "troppo-corto", "severity": lint.FLAGS, "detail": "", "field": None}]

        with unittest.mock.patch.object(lint, "lint_entry", finto_lint_entry):
            fermi = pubblica.bloccanti("30", {"lead": "x", "sections": []})
        self.assertEqual([f["rule"] for f in fermi], ["gemello"],
                         "solo i `blocca`: un `segnala` non chiude nessuna porta")
        self.assertEqual(visto["key"], "30")
        self.assertIs(visto["texts"]["30"], visto["entry"],
                      "lo store che il lint vede porta la bozza al proprio posto, "
                      "non la versione vecchia")


    def test_a_gate_that_cannot_run_is_not_a_green_gate(self):
        """Il verso della guardia è scelto, e va nel senso prudente.

        Se il lint stesso esplode (dati storti, vista che non si costruisce),
        `origine` **non** si scrive: un guasto qui non deve promuovere niente.
        La scrittura invece prosegue, perché prima di questa funzione avveniva
        sempre, e far sparire l'articolo per un errore del cancello sarebbe una
        regressione peggiore del difetto che stiamo chiudendo.
        """
        with unittest.mock.patch.object(lint, "lint_entry",
                                        side_effect=RuntimeError("vista rotta")):
            fermi = pubblica.bloccanti("30", {"lead": "x", "sections": []})
        self.assertEqual([f["rule"] for f in fermi], ["cancello-non-eseguibile"])
        self.assertIn("vista rotta", fermi[0]["detail"])

    def test_and_a_first_publication_is_still_written(self):
        """Su una prima pubblicazione la bozza si scrive lo stesso, senza
        `origine`: non c'è niente sotto da proteggere, e rifiutare perderebbe
        l'unica copia per un errore che non riguarda la prosa.

        Su una **riscrittura** il verso si rovescia, ed è l'altra metà della
        stessa regola: vedi
        `ARejectedRewriteDoesNotEatTheGoodArticle.test_a_gate_that_cannot_run_does_not_replace_the_article_either`.
        """
        with unittest.mock.patch.object(lint, "lint_entry",
                                        side_effect=RuntimeError("vista rotta")):
            codice, entry, _ = self._main(BOZZA, precedenti={})
        self.assertEqual(codice, 0)
        self.assertNotIn("origine", entry)
        self.assertEqual(entry["lead"], BOZZA["lead"])


class ARejectedRewriteDoesNotEatTheGoodArticle(
        OnlyAnArticleThatPassedTheGateGetsItsOrigin):
    """Una bozza che il cancello blocca non sostituisce l'articolo che c'era.

    Il difetto: l'officina scriveva `content/indicators/<chiave>.json` senza
    condizionare la scrittura al verdetto. Su una prima pubblicazione non si
    perde niente; su una **riscrittura** di un articolo già buono, quello buono
    spariva dal working tree e si recuperava solo da git.

    **Vale a ogni tentativo, e questa è la parte che si sbaglia.** Una prima
    versione rifiutava solo la seconda scrittura, con un flag acceso dal
    workflow sul giro di ritorno: inutile, perché il danno lo fa il **primo**
    tentativo, e dopo di lui l'articolo protetto è già una bozza bocciata.

    Si può rifiutare a ogni tentativo perché il comando **stampa i rilievi**
    (`RILIEVI <json>`). Erano loro il motivo per cui la scrittura doveva
    avvenire comunque: il passo successivo del pubblicatore li rileggeva da
    disco con `officina.lint`, e su un articolo non sovrascritto avrebbe
    descritto il testo vecchio attribuendone i rilievi alla bozza nuova.

    Eredita la classe sopra per riusarne `_main`.
    """

    FERMO = [{"rule": "cifra-falsa", "severity": "blocca", "detail": "x", "field": None},
             {"rule": "troppo-corto", "severity": "segnala", "detail": "y", "field": None}]
    PRECEDENTE = {"30": {"lead": "Il buono di prima.", "sections": []}}

    def test_the_previous_article_survives_a_blocked_rewrite(self):
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi",
                                        lambda key, fatta: self.FERMO):
            codice, entry, detto = self._main(BOZZA, precedenti=self.PRECEDENTE)
        self.assertEqual(codice, 2, "non è scritta, e l'uscita lo dice")
        self.assertEqual(entry, {}, "nessuna scrittura: il file precedente è intatto")
        self.assertIn("rimasto al suo posto", detto)

    def test_it_prints_the_findings_of_the_draft_not_of_the_disk(self):
        """Senza questi, chi riscrive riceverebbe i rilievi del testo vecchio.

        Sono tutti, `segnala` compresi, perché è lo stesso contratto del passo
        di lint che questa uscita sostituisce.
        """
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi",
                                        lambda key, fatta: self.FERMO):
            _, _, detto = self._main(BOZZA, precedenti=self.PRECEDENTE)
        riga = next(r for r in detto.splitlines() if r.startswith("RILIEVI "))
        self.assertEqual(json.loads(riga[len("RILIEVI "):]), self.FERMO)

    def test_a_first_publication_is_still_written(self):
        """Senza un precedente non c'è niente da proteggere, e rifiutare qui
        perderebbe l'unica copia della bozza."""
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi",
                                        lambda key, fatta: self.FERMO):
            codice, entry, _ = self._main(BOZZA, precedenti={})
        self.assertEqual(codice, 0)
        self.assertNotIn("origine", entry)
        self.assertEqual(entry["lead"], BOZZA["lead"])

    def test_a_clean_rewrite_is_written(self):
        with unittest.mock.patch.object(pubblica, "tutti_i_rilievi",
                                        lambda key, fatta: []):
            codice, entry, _ = self._main(BOZZA, precedenti=self.PRECEDENTE)
        self.assertEqual(codice, 0)
        self.assertEqual(entry["origine"], "officina")

    def test_a_gate_that_cannot_run_does_not_replace_the_article_either(self):
        """Nemmeno un guasto del cancello sostituisce un articolo che esiste.

        La regola "un guasto del lint non deve costare una scrittura" nasce
        sulla **prima** pubblicazione, dove rifiutare perderebbe l'unica copia
        della bozza. Su una riscrittura si rovescia: lì scrivere costa
        l'articolo precedente, sostituito da un testo che nessuno ha potuto
        controllare, e la bozza non è persa in nessuno dei due casi (il
        workflow la riporta, la run può ripartire) mentre l'articolo buono sì.

        Resta quindi una regola sola: un articolo che esiste non viene mai
        sostituito da qualcosa che il cancello non ha passato.
        """
        with unittest.mock.patch.object(lint, "lint_entry",
                                        side_effect=RuntimeError("vista rotta")):
            codice, entry, detto = self._main(BOZZA, precedenti=self.PRECEDENTE)
        self.assertEqual(codice, 2)
        self.assertEqual(entry, {})
        self.assertIn("cancello-non-eseguibile", detto)

    def test_a_gate_that_cannot_run_still_writes_a_first_publication(self):
        """Qui invece la regola originale vale intera: senza un precedente,
        rifiutare perderebbe l'unica copia della bozza per un errore che non
        riguarda la prosa."""
        with unittest.mock.patch.object(lint, "lint_entry",
                                        side_effect=RuntimeError("vista rotta")):
            codice, entry, _ = self._main(BOZZA, precedenti={})
        self.assertEqual(codice, 0)
        self.assertNotIn("origine", entry)
        self.assertEqual(entry["lead"], BOZZA["lead"])


if __name__ == "__main__":
    unittest.main()
