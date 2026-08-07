"""I documenti controllati contro il codice, invece che riletti.

Un documento che sbaglia non e' inerte come un commento che sbaglia: qualcuno
lo esegue. Il comando `--stage` di `AGENT_CONTRACT.md` e' l'ultimo gesto di ogni
run, il `description` di una skill decide se la skill viene scelta, e la lista
delle eval nel canary decide che cosa viene misurato prima di cambiare un
modello. Tre cose che si copiano e si incollano, e che nessuna suite guardava.

**Perche' questo file non vieta i nomi morti.** La tentazione ovvia era cercare
`writer`, `producer`, `revisore` nei documenti e bocciare. Misurato: dei 34
percorsi "morti" nella documentazione, 32 sono **citazioni corrette** della
forma "X e' stato ritirato", che sono il contrario di un difetto. Un controllo
cosi' diventa rosso sulla storia scritta bene e insegna a cancellarla.

Quindi qui si controlla solo cio' che e' **dereferenziabile**: un nome che il
codice puo' risolvere, e su cui puo' dire si' o no senza interpretare la prosa
intorno. Un comando copiaincollabile, una chiave di dizionario, un file che c'e'
o non c'e'.

Esente per costruzione: `docs/archive/`, che dichiara di non essere una fonte di
verita', e le righe datate del registro di `CANARY.md`, che sono storia e vanno
lasciate come sono state scritte.
"""

import re
import unittest
from pathlib import Path

from scripts import agent_guard, pipeline_gate, pipeline_log, pipeline_status

RADICE = pipeline_gate.PROJECT_ROOT
AGENTI = RADICE / ".claude" / "agents"

# Dove si guarda. `docs/archive/` no: quei documenti dichiarano nel proprio
# README di non essere fonti di verita', e correggerli sarebbe riscrivere un
# piano gia' eseguito per farlo sembrare eseguito diversamente.
ALBERI = ("docs", ".claude", "scripts", "evals", "content")
ESENTI = (RADICE / "docs" / "archive",)

# Il vocabolario di ogni script, letto dal codice e non ricopiato: e' lo stesso
# insieme che finisce nel `choices` di argparse, quindi un comando che questo
# test approva e' un comando che parte.
VOCABOLARI = {
    "pipeline_gate.py": sorted(pipeline_gate.STAGE_PATHS),
    "pipeline_merge.py": sorted(pipeline_gate.STAGE_PATHS),
    "agent_guard.py": sorted(agent_guard.GUARDED_STAGES),
    "pipeline_log.py": list(pipeline_log.HISTORICAL_STAGES),
    "pipeline_status.py": list(pipeline_status.STAGE_ORDER),
}

# Una riga di comando copiaincollabile: comincia con l'interprete. E' il taglio
# che separa il difetto dalla citazione. `pipeline_gate.py:103` scrive «il primo
# `--stage writer` di passaggio riaprirebbe...», cioe' nomina lo stadio morto
# **per dire che non si puo' piu' usare**; una regex sul solo `--stage` la
# boccerebbe, e la frase che spiega la demolizione andrebbe cancellata per far
# tornare verde un test.
COMANDO = re.compile(
    r"^\s*(?:python3|bin/py|\$\(python3)\s+\S*?(?P<script>[a-z_]+\.py)\b(?P<coda>.*)$")
STADIO = re.compile(r"--stage\s+(?P<nome>[^\s\\]+)")
# Il registro datato di `docs/CANARY.md`: storia, non procedura.
RIGA_DI_REGISTRO = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}")
# Un comando che comincia con l'interprete sbagliato. `.venv/bin/python` non
# esiste in un worktree fresco, dove gli agenti girano: esce 127 dicendo "no such
# file or directory", che non suggerisce niente a chi legge. `bin/py` prova i
# percorsi in ordine e, quando fallisce, dice quali ha provato e come crearne uno.
INTERPRETE_VIETATO = re.compile(r"^\s*(?:[A-Z_]+=\S+\s+)*\.venv/bin/(?:python|gunicorn)\b")


def _file_di_testo():
    for albero in ALBERI:
        for path in sorted((RADICE / albero).rglob("*")):
            if not path.is_file() or path.suffix not in (".md", ".py", ".js", ".sh"):
                continue
            if any(esente in path.parents for esente in ESENTI):
                continue
            yield path
    yield RADICE / "CLAUDE.md"
    yield RADICE / "AGENTS.md"


def _comandi_con_stadio():
    """(percorso, riga, script, stadio) per ogni comando eseguibile scritto."""
    for path in _file_di_testo():
        for numero, riga in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if RIGA_DI_REGISTRO.match(riga):
                continue
            comando = COMANDO.match(riga)
            if not comando or comando.group("script") not in VOCABOLARI:
                continue
            for stadio in STADIO.finditer(comando.group("coda")):
                nome = stadio.group("nome")
                # `<stadio>` e' un segnaposto: chi lo legge lo sostituisce, e
                # non c'e' niente da verificare. `<a|b|c>` **non** lo e': e'
                # un'enumerazione, cioe' la lista da cui si sceglie, e i suoi
                # nomi si copiano uno per uno. E' la forma esatta del difetto in
                # `AGENT_CONTRACT.md`, dove sei alternative su sette erano di
                # stadi cancellati.
                if nome.startswith("<") and "|" not in nome:
                    continue
                for alternativa in nome.strip("<>").split("|"):
                    yield (path.relative_to(RADICE), numero,
                           comando.group("script"), alternativa)


class UnAgentePerPerimetro(unittest.TestCase):
    """L'invariante la cui assenza ha reso necessaria una mappa da tradurre.

    Il cancello conosceva dieci perimetri e sette appartenevano a ruoli
    cancellati; e l'unico agente rimasto con un nome diverso dal proprio stadio
    (`indicator-verifier.md` contro `verificatore`) obbligava `pipeline_launch`
    a tenere un dizionario per tradurlo. Le due cose sono lo stesso difetto
    visto da due lati: nessuno teneva insieme "chi ha un perimetro" e "chi
    esiste".
    """

    def test_ogni_stadio_ha_il_suo_agente_e_si_chiama_come_lui(self):
        for stadio in pipeline_gate.STAGE_PATHS:
            path = AGENTI / f"{stadio}.md"
            self.assertTrue(path.exists(), f"lo stadio {stadio} non ha un agente")
            self.assertIn(f"name: {stadio}\n", path.read_text(encoding="utf-8"),
                          f"{path.name} non dichiara `name: {stadio}`")

    def test_nessun_agente_avanza_senza_un_posto_dove_stare(self):
        """Gli altri quattro sono i tipi stretti dell'officina: vivono dentro il
        workflow, non aprono run e non hanno perimetro. Elencati per nome perche'
        e' l'unico modo di accorgersi che ne e' comparso un quinto senza che
        nessuno abbia deciso dove sta."""
        officina = {"preparatore-pacchetti", "scrittore-indicatore",
                    "giudice-cieco", "pubblicatore"}
        sul_disco = {path.stem for path in AGENTI.glob("*.md")}
        self.assertEqual(sul_disco, set(pipeline_gate.STAGE_PATHS) | officina)


class UnComandoScrittoEUnComandoCheParte(unittest.TestCase):
    def test_ogni_stadio_scritto_a_riga_di_comando_esiste(self):
        """Il difetto piu' caro della documentazione, perche' costa una run.

        `AGENT_CONTRACT.md` portava
        `--stage <scout|hunter|promoter|curator|writer|reviewer|verificatore>`
        nel passo che ogni agente esegue a fine run: sei nomi su sette non
        esistono piu', e chi ne copiava uno scopriva il guasto dopo aver fatto
        il lavoro.
        """
        rotti = [f"{path}:{numero}: {script} --stage {nome}"
                 for path, numero, script, nome in _comandi_con_stadio()
                 if nome not in VOCABOLARI[script]]
        self.assertEqual(rotti, [], "comandi che non partono:\n" + "\n".join(rotti))

    def test_nessun_agente_lancia_un_interprete_che_puo_non_esserci(self):
        """Il guasto piu' ripetuto che il repo abbia registrato: quattro volte in
        quarantotto ore, `.venv/bin/python: no such file or directory`.

        Gli agenti girano su un checkout fresco, dove `.venv` puo' non esserci, e
        `python3` in questo ambiente e' una funzione di shell che senza
        `$VIRTUAL_ENV` cade su un interprete privo delle dipendenze. `bin/py`
        esiste per risolvere in un posto solo e fallire dicendo perche'.

        Il controllo copre i file che un agente **esegue** (il proprio prompt e
        le skill), non l'intera documentazione: li' `.venv/bin/python` compare
        anche nelle frasi che spiegano perche' non si usa, ed e' corretto che ci
        sia. Sono anche i file per cui il guasto e' stato misurato."""
        eseguibili = sorted(
            list((RADICE / ".claude" / "agents").glob("*.md"))
            + list((RADICE / ".claude" / "skills").rglob("SKILL.md")))
        self.assertTrue(eseguibili)
        rotti = [f"{path.relative_to(RADICE)}:{numero}: {riga.strip()}"
                 for path in eseguibili
                 for numero, riga in enumerate(
                     path.read_text(encoding="utf-8").splitlines(), 1)
                 if INTERPRETE_VIETATO.match(riga)]
        self.assertEqual(rotti, [],
                         "comandi con un interprete che puo' non esistere:\n"
                         + "\n".join(rotti))

    def test_lopzione_giusta_e_quella_gia_permessa(self):
        """La causa a monte, e non e' un documento: e' `.claude/settings.json`.

        La lista `allow` pre-approvava `.venv/bin/python` e **non** `bin/py`,
        cioe' l'unico interprete che il progetto impone. Un agente che seguiva
        `CLAUDE.md` prendeva un prompt di permesso, e quello vietato girava senza
        chiedere: l'incentivo puntava esattamente dalla parte sbagliata, ed e' la
        spiegazione piu' semplice di perche' il guasto si ripeteva."""
        import json

        permessi = json.loads(
            (RADICE / ".claude" / "settings.json").read_text(encoding="utf-8"))
        allow = permessi["permissions"]["allow"]
        self.assertIn("Bash(bin/py:*)", allow)
        self.assertEqual([r for r in allow if ".venv" in r], [])

    def test_il_controllo_vede_davvero_qualcosa(self):
        """Un controllo che non trova mai niente da controllare e' verde per il
        motivo sbagliato. Se un giorno la forma dei comandi cambia e la regex
        smette di agganciarli, questo test lo dice invece di lasciar passare
        tutto in silenzio."""
        self.assertGreaterEqual(len(list(_comandi_con_stadio())), 10)


class IlCanaryMisuraTuttiGliAgentiCheEsistono(unittest.TestCase):
    """Un canary che salta un'eval non e' un canary piu' veloce: e' un cambio di
    modello promosso senza aver guardato uno dei giudici."""

    FONTI = ("docs/CANARY.md", ".claude/skills/canary/SKILL.md")

    def _citate(self, rel):
        """Le eval nominate da **un** file.

        Per file e non in unione, ed e' la correzione di un difetto che questo
        stesso test aveva: unendo le due fonti, la skill poteva smettere di
        nominare quattro eval su cinque e restare verde sulla forza di
        `CANARY.md`. Cioe' esattamente l'omissione che il test esiste per
        prendere, un livello piu' sotto. Chi legge la skill non legge anche il
        documento: la lista che ha davanti dev'essere intera.
        """
        citate = set()
        for riga in (RADICE / rel).read_text(encoding="utf-8").splitlines():
            if RIGA_DI_REGISTRO.match(riga):
                continue
            citate.update(re.findall(r"run_eval\.py\s+([a-z][a-z-]*)", riga))
        return citate

    def _prompts(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "run_eval", RADICE / "evals" / "run_eval.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return set(modulo.PROMPTS)

    def test_ogni_eval_citata_esiste(self):
        for rel in self.FONTI:
            self.assertEqual(self._citate(rel) - self._prompts(), set(), rel)

    def test_ogni_eval_che_esiste_e_citata_da_ogni_fonte(self):
        """La meta' che prende l'omissione. `reader-editor` e' un agente vivo con
        una eval e delle fixture, e la procedura di canary non lo nominava:
        cambiare modello lo lasciava fuori dalla misura senza dirlo.

        Ogni fonte per conto suo: il documento e la skill si leggono uno senza
        l'altro, e una lista a meta' e' una lista sbagliata anche se l'altra
        pagina la completa."""
        for rel in self.FONTI:
            self.assertEqual(self._prompts() - self._citate(rel), set(), rel)


class UnaSkillSiSceglieDalSuoFrontmatter(unittest.TestCase):
    def test_la_procedura_di_chiusura_nomina_gli_stadi_che_la_devono_usare(self):
        """Non e' debito di documentazione, e' un guasto funzionale: il campo
        `description` guida la selezione della skill. Diceva "scout, hunter,
        curator, writer, reviewer o verificatore", cioe' cinque stadi che non
        esistono, e **non** `admissions` ne' `reader-editor`: i due agenti vivi
        non agganciavano la propria procedura di chiusura."""
        testo = (RADICE / ".claude" / "skills" / "pipeline-close-run"
                 / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = testo.split("---")[1]
        for stadio in pipeline_gate.STAGE_PATHS:
            self.assertIn(stadio, frontmatter,
                          f"{stadio} non trova la propria procedura di chiusura")


class IDueVocabolariNonDivergono(unittest.TestCase):
    """Il dossier parla ancora di `curator`, `writer`, `reviewer`, e non e' un
    residuo: sono i nomi con cui la pratica di trecento indicatori e' stata
    scritta su disco. Rinominarli riscriverebbe `data/pratica/`.

    Cio' che si controlla non e' che i due vocabolari coincidano, ma che il
    ponte fra loro resti percorribile in tutte e due le direzioni.
    """

    def test_ogni_vecchio_stadio_porta_a_un_ruolo_vivo(self):
        from scripts import pipeline_launch

        for stadio, ruolo in pipeline_launch.ROLE_OF_STAGE.items():
            self.assertIn(stadio, pipeline_log.HISTORICAL_STAGES, stadio)
            self.assertIn(ruolo, pipeline_launch.ROLE_ORDER, ruolo)

    def test_lo_stadio_va_al_ruolo_che_puo_scriverne_i_file(self):
        """Portare a un ruolo vivo non basta: dev'essere il ruolo che ha i file
        di quello stadio dentro il proprio perimetro.

        `curator` puntava a `producer`, cioe' all'officina, il cui perimetro e'
        `content/indicators/`. Ma curare vuol dire eseguire
        `scripts/apply_curation.py`, che scrive il layer esterno, il manifest e
        le descrizioni curate: file dell'ammissione. Il piano avrebbe mandato il
        lavoro a chi non ha ne' il gesto ne' il permesso, e non e' mai successo
        solo perche' la coda `curator` e' vuota. Un difetto che aspetta una riga
        di dati per diventare vero non e' meno difetto.

        Si controlla lo stadio di cui esiste uno script di scrittura
        identificabile. Gli altri restano coperti dal test qui sopra.
        """
        from scripts import apply_curation, curate, pipeline_launch

        ruolo = pipeline_launch.ROLE_OF_STAGE["curator"]
        perimetro = pipeline_gate.STAGE_PATHS.get(ruolo)
        self.assertIsNotNone(perimetro, f"{ruolo} non ha un perimetro")
        # Quattro file, non tre: la decisione, e i tre che `apply_curation`
        # produce leggendola. Il primo mancava, quindi la curazione sarebbe
        # stata respinta prima ancora di cominciare.
        scritti = (curate.CURATION_PATH,
                   apply_curation.EXTERNAL_DATASET,
                   apply_curation.EXTERNAL_MANIFEST,
                   apply_curation.CURATED_DESCRIPTIONS)
        for percorso in scritti:
            relativo = str(percorso.relative_to(RADICE))
            self.assertIn(relativo, perimetro,
                          f"la curazione scrive {relativo}, fuori dal perimetro di {ruolo}")

    def test_ogni_ruolo_del_piano_si_sa_lanciare(self):
        """Un ruolo o e' un agente che esiste, o e' un workflow che esiste. La
        terza possibilita' e' un puntatore morto che qualcuno lancia una volta
        sola, scoprendo il guasto quando la run muore."""
        from scripts import pipeline_launch

        for ruolo in pipeline_launch.ROLE_ORDER:
            bersaglio = pipeline_launch.target(ruolo, "ter-1")
            if bersaglio.get("workflow"):
                self.assertTrue((RADICE / bersaglio["workflow"]).exists(), ruolo)
            else:
                self.assertTrue((AGENTI / f"{bersaglio['agent']}.md").exists(), ruolo)


if __name__ == "__main__":
    unittest.main()
