"""Il workflow di scrittura: le proprieta' che non devono sparire in un edit.

Uno script di orchestrazione non ha una suite propria, ed e' esattamente il
tipo di file che si degrada in silenzio: qualcuno toglie la seconda bozza per
risparmiare, e la regressione alla media torna senza che niente fallisca. Qui
si controllano le poche decisioni su cui poggia il disegno, e ognuna viene da
una misura della prima run, non da un'opinione.

Non prova che il workflow *funzioni*: quello lo dice solo una run vera. Prova
che continui a essere il workflow che e' stato deciso.
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, ".claude", "workflows", "produci-indicatori.js")
AGENTI = os.path.join(ROOT, ".claude", "agents")
# I quattro tipi che il workflow lancia. `preparatore-pacchetti` c'e' perche'
# lo stadio dei pacchetti girava come `pubblicatore`, cioe' con il permesso di
# scrivere in content/indicators/ che non gli serve.
AGENTI_DELL_OFFICINA = ("preparatore-pacchetti.md", "scrittore-indicatore.md",
                        "giudice-cieco.md", "pubblicatore.md")


def _senza_commenti(text):
    return "\n".join(line for line in text.splitlines()
                     if not line.strip().startswith("//"))


class TheScriptExists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as handle:
            cls.text = handle.read()

    def test_it_declares_a_meta_block_with_the_phases(self):
        self.assertRegex(self.text, r"export const meta = \{")
        for phase in ("Pacchetti", "Scrittura", "Giudizio", "Lint"):
            self.assertIn(f"title: '{phase}'", self.text)

    def test_every_phase_declared_in_meta_is_used_by_an_agent(self):
        declared = set(re.findall(r"title: '([^']+)'", self.text))
        used = set(re.findall(r"phase: '([^']+)'", self.text))
        self.assertEqual(declared - used, set(),
                         "una fase dichiarata e mai usata non compare nel progresso")


class AnAgentReceivesItDoesNotSearch(unittest.TestCase):
    """La regola da cui discende tutto, e la misura che la impone.

    Prima run: scrittori 162 turni e $2,90-3,66 ciascuno, giudici 4 turni e
    $0,14 ciascuno, con lo stesso modello e un prompt di partenza piu' piccolo
    per gli scrittori (26.676 contro 30.434). La differenza erano i turni, e i
    turni erano ricerca. E il costo dei turni e' quadratico: la lettura di
    cache cresce di ~1.950 token a turno.
    """

    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as handle:
            cls.text = handle.read()

    def test_the_packs_are_built_once_for_the_whole_run(self):
        self.assertIn("officina.pacchetti", self.text)
        self.assertEqual(len(re.findall(r"phase: 'Pacchetti'", self.text)), 1,
                         "un pacchettaio per run, non uno per indicatore")

    def test_what_travels_is_the_path_not_the_pack(self):
        """Cio' che un agente restituisce e' output, a 25 $/MTok.

        Un pacchetto pesa 6-12 mila token: cinquanta indicatori sarebbero mezzo
        milione di token di puro transito da un agente solo.
        """
        self.assertIn("percorsi ASSOLUTI", self.text)
        self.assertIn("Non leggere i pacchetti", self.text)

    def test_the_writer_is_given_the_path_not_told_to_find_it(self):
        self.assertIn("${pack.path}", self.text)
        self.assertNotIn("officina.brief", self.text,
                         "il brief eseguito dall'agente e' la riga che e' costata la run")

    def test_no_agent_is_told_to_run_bare_python3(self):
        """`python3` qui e' una funzione di shell senza le dipendenze.

        Tutti e quattro gli scrittori della prima run ci hanno sbattuto contro,
        e un pubblicatore ha finito per usare l'interprete di un altro
        worktree: due codici possibili per lo stesso verdetto.
        """
        code = _senza_commenti(self.text)
        self.assertNotIn("python3 -m", code)
        self.assertIn("bin/py", code)

    def test_every_agent_declares_a_type_with_narrowed_tools(self):
        """Un `agent()` senza `agentType` eredita l'insieme intero di strumenti.

        Si contano le chiamate invece di analizzare gli oggetti di opzioni: un
        template literal contiene graffe, e una regex che le bilanci sarebbe
        piu' fragile del controllo che deve fare.
        """
        code = _senza_commenti(self.text)
        # Ogni spawn passa da `conTipo`, che aggiunge `agentType` e ripiega una
        # volta sola se il registro della sessione non conosce il tipo.
        spawns = len(re.findall(r"\bconTipo\(", code)) - 1  # meno la definizione
        types = re.findall(r"^\s+'([a-z-]+)',$", code, re.M)
        self.assertGreater(spawns, 0)
        self.assertEqual(spawns, len(types),
                         f"{spawns - len(types)} agenti senza tipo ereditano tutti gli strumenti")
        self.assertNotIn("await agent(", code.replace("await agent(prompt", ""),
                         "uno spawn diretto salta la restrizione di strumenti")

    def test_a_missing_agent_type_stops_the_run_instead_of_degrading_it(self):
        """Il perimetro non si degrada: se manca, non si gira.

        Una prima versione ripiegava su un agente senza tipo, e la prova ha
        mostrato perche' e' sbagliato: senza restrizione, due scrittori con
        prompt identico hanno fatto 2 e 26 turni, e l'advisor e' rientrato per
        il 29% del costo. Il ripiego toglieva esattamente cio' che il tipo
        esiste per imporre, e la run continuava sembrando riuscita.
        """
        code = _senza_commenti(self.text)
        self.assertIn("throw new Error", code)
        self.assertNotIn("tipiDisponibili", code,
                         "il ripiego silenzioso e' tornato")
        # Nessuno spawn senza tipo: `conTipo` e' l'unica porta.
        self.assertEqual(len(re.findall(r"\bagent\(", code)),
                         len(re.findall(r"agentType: tipo", code)))


class TheDesignDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as handle:
            cls.text = handle.read()

    def test_two_drafts_not_one(self):
        """Scegliere fra due e' la sostituzione meccanica del gusto."""
        self.assertIn("scrivi(pack, 1)", self.text)
        self.assertIn("scrivi(pack, 2)", self.text)

    def test_the_second_draft_is_told_to_tell_another_story(self):
        self.assertIn("non una variante della stessa", self.text)

    def test_two_judges_with_different_lenses(self):
        lenses = re.findall(r"giudica\(pack\.code, bozze, '([^']+)'", self.text)
        self.assertEqual(len(lenses), 2)
        self.assertNotEqual(lenses[0], lenses[1],
                            "due giudici identici scoprono lo stesso errore due volte")

    def test_the_two_judges_see_the_drafts_in_opposite_order(self):
        """Lo slot A vince 10-15 punti piu' spesso a parita' di contenuto.

        Prima l'angolo 1 stava sempre in A. Invertire fra i due giudici
        cancella il bias invece di randomizzarlo, e resta deterministico,
        quindi la run si puo' riprendere.
        """
        flags = re.findall(r"giudica\(pack\.code, bozze, '[^']+', (true|false)\)", self.text)
        self.assertEqual(sorted(flags), ["false", "true"])

    def test_a_tie_can_be_declared_as_a_tie(self):
        """66,5% di pareggi nel best-of-N: il pareggio e' il caso normale."""
        self.assertIn("'pari'", self.text)

    def test_the_measure_selects_and_the_judge_only_breaks_ties(self):
        """Il giudice e' debole sulla scelta e forte sulla diagnosi, misurato."""
        body = self.text[self.text.index("function scegli("):
                         self.text.index("const preparati")]
        self.assertIn("soglia", body)
        self.assertIn("la misura non discrimina", body)

    def test_both_decisions_are_recorded_not_just_the_winner(self):
        """Senza registrarle, l'accordo fra giudice e misura si assume."""
        self.assertIn("scelte:", self.text)
        self.assertIn("voti", self.text)

    def test_the_judge_carries_no_rubric(self):
        body = self.text[self.text.index("function giudica("):
                         self.text.index("const PARAGRAFO_MIN_PAROLE")]
        prompt = _senza_commenti(body)
        self.assertIn("quale leggerebbe fino in fondo", prompt)
        for banned in ("rubrica", "punteggio", "criteri", "su 20", "0-2"):
            self.assertNotIn(banned, prompt,
                             f"il giudizio e' tornato a essere una griglia ({banned})")

    def test_the_judge_asks_for_the_coldest_paragraph(self):
        """E' il difetto che ha fatto ripensare la pipeline: non falso, freddo."""
        self.assertIn("paragrafo_piu_freddo", self.text)

    def test_the_section_roles_are_an_enum(self):
        """Senza, la prima run ha inventato `scala` e `distribuzione`.

        Quelle bozze hanno perso il giudizio, ma per fortuna, non per disegno.
        """
        self.assertIn("enum: RUOLI", self.text)
        roles = re.search(r"const RUOLI = \[([^\]]+)\]", self.text)
        self.assertIsNotNone(roles)
        self.assertEqual(
            sorted(re.findall(r"'([a-z]+)'", roles.group(1))),
            ["definizione", "dinamica", "limiti", "quadro"])

    def test_the_gate_is_the_deterministic_lint(self):
        self.assertIn("officina.lint", self.text)
        self.assertIn("blocca", self.text)

    def test_a_block_goes_back_to_whoever_writes_and_only_once(self):
        """Il pubblicatore non ripara piu' niente, nemmeno un `blocca`.

        Non ha Edit ne' Write, quindi ripararlo in casa vorrebbe dire ribattere
        l'articolo intero come una riga JSON, oppure aprire `sed` sul file
        appena scritto: cioe' l'editoria che gli abbiamo tolto, per la porta di
        servizio. Un giro solo, perche' se una riscrittura mirata non basta il
        problema non e' una frase.
        """
        self.assertIn("Non ripari niente, nemmeno un", self.text)
        self.assertIn("ilBlocco", _senza_commenti(self.text))
        # Tre chiamate: la prima, piu' un solo giro di ritorno per ciascuno dei
        # due modi di non essere pubblicabile (bozza rifiutata dal comando di
        # scrittura, articolo bocciato dal lint).
        self.assertEqual(_senza_commenti(self.text).count("await pubblica(corrente"), 3)

    def test_it_forbids_inventing_a_source_to_silence_the_lint(self):
        self.assertIn("non inventare una fonte", self.text)

    def test_an_unresolved_code_is_treated_as_an_error(self):
        """`lint ter-176` selezionava zero articoli e stampava zero rilievi.

        Il pubblicatore della prima run ha letto proprio quel verde.
        """
        self.assertIn("Uscita 2", self.text)

    def test_it_does_not_isolate_what_does_not_collide(self):
        """Due ragioni, non una: niente git da serializzare, e la cache di
        prompt e' legata alla directory, quindi un worktree e' un miss pieno."""
        self.assertNotIn("isolation:", _senza_commenti(self.text))
        with open(os.path.join(AGENTI, "pubblicatore.md"), encoding="utf-8") as handle:
            self.assertIn("solo il file dell'articolo", handle.read())

    def test_no_agent_file_is_resurrected(self):
        """I due critici della catena e i due agenti demoliti. `verificatore`
        ha preso il posto di `indicator-verifier` quando il file e' stato
        rinominato sullo stadio: e' lo stesso agente, e il workflow non deve
        chiamarlo con nessuno dei due nomi."""
        for role in ("reader-editor", "verificatore", "launcher", "producer.md"):
            self.assertNotIn(role, self.text)


class TheMechanicalStagesTakeNoEditorialDecision(unittest.TestCase):
    """Il difetto che questa classe presidia era due istruzioni opposte.

    `pubblicatore.md` diceva "se il lint non blocca niente, hai finito: non
    rileggere, non migliorare, non riordinare", e il prompt del workflow diceva
    allo stesso agente, nello stesso momento, di riscrivere il paragrafo piu'
    freddo. Un compito editoriale affidato al ruolo definito come meccanico, e
    nessun modo di sapere quale delle due avesse vinto.
    """

    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as handle:
            cls.text = handle.read()
        cls.codice = _senza_commenti(cls.text)
        cls.pubblica = cls.text.split("Pubblica l'articolo", 1)[1]

    def test_the_publisher_is_not_asked_to_rewrite(self):
        self.assertNotIn("riscrivilo", self.pubblica)
        self.assertIn("non riscriverlo", self.pubblica)

    def test_the_diagnosis_is_applied_where_the_pack_still_is(self):
        self.assertIn("function rivedi", self.codice)
        self.assertIn("'scrittore-indicatore'",
                      self.text.split("function rivedi", 1)[1].split("function", 1)[0])

    def test_every_diagnosis_gets_an_explicit_outcome(self):
        """Una diagnosi che il passo dopo puo' ignorare in silenzio non e' un
        input del processo, e' un commento."""
        for esito in ("applicato", "rifiutato", "non_applicabile"):
            self.assertIn(f"'{esito}'", self.codice)
        self.assertIn("feedback:", self.codice.split("return {")[-1],
                      "il feedback non risale nell'esito della run")

    def test_the_publisher_gets_the_exact_write_command(self):
        """La forma dell'entry non e' una decisione editoriale, quindi non puo'
        costare un turno: la scriveva a mano leggendo `indicator_store.py`."""
        self.assertIn("officina.pubblica", self.pubblica)
        self.assertNotIn("scripts.indicator_store", self.text)

    def test_a_refused_write_carries_the_findings_of_the_draft(self):
        """Quando `officina.pubblica` rifiuta di sovrascrivere, il passo 2 va
        saltato, e il prompt deve dirlo.

        Il comando rifiuta quando il cancello blocca e sotto c'e' gia' un
        articolo: li' non si scrive, quindi `officina.lint` descriverebbe il
        **testo precedente** e ne attribuirebbe i rilievi alla bozza nuova. Per
        questo il comando li stampa da se' su una riga `RILIEVI`, e il
        pubblicatore copia quelli. Senza questa istruzione il giro di
        riparazione riceve i rilievi di un altro testo, che e' un verdetto
        falso, peggio della sovrascrittura che il rifiuto evita.
        """
        self.assertIn("RILIEVI", self.pubblica)
        self.assertIn("salta il passo 2", self.pubblica)
        self.assertNotIn("--ultimo-tentativo", self.text,
                         "il rifiuto non ha piu' un flag: vale a ogni tentativo, "
                         "perche' il danno lo fa il primo")

    def test_a_gate_block_is_not_reported_as_a_form_error(self):
        """`ilRifiuto` dice "e' una regola di forma, correggi cio' che il
        messaggio nomina": su un rilievo editoriale e' un'istruzione sbagliata.

        Quindi `rifiutato` esclude il caso in cui la scrittura e' stata
        rifiutata **con** dei rilievi bloccanti: quello e' un blocco, e va a
        `ilBlocco`."""
        codice = _senza_commenti(self.text)
        self.assertIn("esito.scritto === false && !primi.length", codice)
        self.assertEqual(codice.count("await pubblica(corrente, ':2')"), 2)

    def test_the_pack_stage_does_not_run_as_the_publisher(self):
        prepara = self.text.split("async function prepara", 1)[1].split("\n}", 1)[0]
        self.assertIn("'preparatore-pacchetti'", prepara)
        self.assertNotIn("'pubblicatore'", prepara)

    def test_work_notes_do_not_reach_the_published_file(self):
        self.assertIn("function bozzaDaScrivere", self.codice)
        self.assertIn("bozzaDaScrivere(scelto.bozza)", self.codice)

    def test_a_silent_reviser_is_a_fault_not_a_verdict(self):
        """Ripiegare su `non_applicabile` scriveva "il rilievo non si
        applicava" al posto di "la revisione non e' avvenuta": indistinguibili
        a valle, e proprio sul campo che serve a decidere se lo stadio vale il
        suo prezzo."""
        rivedi = self.codice.split("function rivedi", 1)[1].split("\n}", 1)[0]
        self.assertIn("throw new Error", rivedi)
        self.assertNotIn("non ha risposto'", rivedi)

    def test_a_red_gate_does_not_count_as_written(self):
        """"Il lint e' l'unico cancello" e' vero solo se un cancello rosso
        arriva fino all'esito della run. `scritti` valeva `fatti.length`, quindi
        una run col lint rosso su ogni articolo si chiudeva dicendo di aver
        scritto tutto."""
        self.assertIn("const bloccati = fatti.filter", self.codice)
        self.assertIn("scritti: scritti.length", self.codice)
        self.assertNotIn("scritti: fatti.length", self.codice)

    def test_a_refused_draft_is_not_a_written_article(self):
        """`scritto: false` non lo guardava nessuno: un articolo mai scritto
        contava fra gli scritti, ed e' la stessa falla del cancello rosso su un
        altro campo."""
        self.assertIn("esito.scritto === false", self.codice)
        self.assertIn("ilRifiuto", self.codice)
        self.assertIn("errore_scrittura", self.codice)

    def test_the_script_is_text(self):
        """Un NUL dentro un template literal: Node lo accetta, `file` e `grep`
        classificano il sorgente come binario e smettono di cercarci dentro."""
        with open(SCRIPT, "rb") as handle:
            self.assertNotIn(b"\x00", handle.read())


class ThePermanentPromptsAgreeWithTheWorkflow(unittest.TestCase):
    """Il prompt permanente e il messaggio della run sono due voci sullo stesso
    agente, e possono contraddirsi in silenzio.

    E' successo: il workflow ha smesso di chiedere riparazioni al pubblicatore,
    e `pubblicatore.md` ha continuato a prometterle per un giro intero. I test
    guardavano solo il prompt costruito dal workflow, quindi non l'hanno visto.
    """

    @classmethod
    def setUpClass(cls):
        cls.prompt = {}
        for name in AGENTI_DELL_OFFICINA:
            with open(os.path.join(AGENTI, name), encoding="utf-8") as handle:
                cls.prompt[name] = handle.read()

    def test_the_publisher_never_promises_a_repair(self):
        testo = self.prompt["pubblicatore.md"]
        self.assertIn("non ripari niente", testo.lower())
        self.assertNotIn("Ripari **solo**", testo)
        self.assertNotIn("al massimo due giri", testo)

    def test_the_publisher_still_reports_every_finding(self):
        self.assertIn("severity", self.prompt["pubblicatore.md"])

    def test_the_writer_declares_both_of_its_invocations(self):
        """Lo stesso tipo scrive una bozza e ne rivede una: un contratto che
        nomina solo la prima e' la stessa divergenza di `corpus` contro
        `claims`."""
        testo = self.prompt["scrittore-indicatore.md"]
        self.assertIn("rivedi", testo)
        self.assertIn("angolo", testo)


class TheAgentTypesAreNarrow(unittest.TestCase):
    """Un agente non deve poter fare cio' per cui pagheremmo turni.

    E' l'altra meta' della regola: il prompt dice cosa fare, il tipo dice cosa
    e' possibile. Un divieto scritto nel prompt e' un suggerimento; un tool
    assente e' un fatto.
    """

    def _frontmatter(self, name):
        with open(os.path.join(AGENTI, name), encoding="utf-8") as handle:
            text = handle.read()
        block = text.split("---")[1]
        out = {}
        for line in block.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                out[key.strip()] = value.strip()
        return out

    def test_the_writer_can_only_read(self):
        tools = self._frontmatter("scrittore-indicatore.md")["tools"]
        self.assertEqual(tools, "Read",
                         "uno scrittore con Bash torna a cercare l'interprete")

    def test_the_judge_cannot_run_commands(self):
        self.assertNotIn("Bash", self._frontmatter("giudice-cieco.md")["tools"])

    def test_the_publisher_keeps_bash_because_it_must_run_the_lint(self):
        self.assertIn("Bash", self._frontmatter("pubblicatore.md")["tools"])

    def test_no_workflow_agent_can_call_the_advisor(self):
        """Nove chiamate advisor, 740 mila token di input non in cache, $5,58.

        Il 26% del costo della prima run, e non compare in `usage`, non compare
        nel campo `tokens` del progresso, non compare da nessuna parte se non
        dentro `usage.iterations`.

        Il divieto e' un **hook**, non `disallowedTools`. Quel campo elenca i
        tool, e l'advisor non e' un tool: con il divieto gia' scritto nel
        frontmatter, la prova su `ter-30` ha comunque letto nel trascritto
        *"let me check my plan with the advisor"*. Questo test asseriva quel
        campo, cioe' asseriva una restrizione che non restringeva niente.
        """
        for name in AGENTI_DELL_OFFICINA:
            with open(os.path.join(AGENTI, name), encoding="utf-8") as handle:
                testo = handle.read()
            self.assertIn("no_advisor.py", testo,
                          f"{name} non ha l'hook che nega l'advisor")
            self.assertNotIn("disallowedTools: advisor", testo,
                             f"{name} dichiara una restrizione che non funziona")

    def test_every_type_used_by_the_workflow_exists(self):
        with open(SCRIPT, encoding="utf-8") as handle:
            code = _senza_commenti(handle.read())
        used = set(re.findall(r"^\s+'([a-z-]+)',$", code, re.M))
        self.assertTrue(used)
        for name in used:
            self.assertTrue(os.path.exists(os.path.join(AGENTI, f"{name}.md")),
                            f"agentType {name} non ha un file: l'agente non parte")


class ItDoesNotDependOnTheOldChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as handle:
            cls.text = handle.read()

    def test_it_never_calls_the_launcher_or_the_stage_queues(self):
        for old in ("pipeline_launch", "pipeline_status", "practice_timeline",
                    "verification_queue", "reading_queue"):
            self.assertNotIn(old, self.text)

    def test_it_does_not_open_a_pull_request_per_article(self):
        """La cerimonia esce dal per-articolo: e' il 92% del tempo del cancello."""
        for ceremony in ("gh pr create", "pipeline_merge", "pipeline-close-run"):
            self.assertNotIn(ceremony, self.text)


if __name__ == "__main__":
    unittest.main()
