"""I documenti controllati contro il codice, invece che riletti.

Un documento che sbaglia non è inerte come un commento che sbaglia: qualcuno lo
esegue. Il `description` di una skill decide se la skill viene scelta, un
comando in un README viene copiato e incollato, e un agente che nessuno dichiara
è un agente che nessuno sa di avere.

Si controlla solo ciò che è **dereferenziabile**: un nome che il codice può
risolvere e su cui può dire sì o no senza interpretare la prosa intorno. Un
comando copiaincollabile, un file che c'è o non c'è, un frontmatter che si
carica o no.

La versione precedente controllava il contratto della catena editoriale
autonoma, che non esiste più. Restano i controlli che valgono sulla catena
minima, ed è la ragione per cui il file non è stato cancellato con il resto: è
il posto dove si dichiara che cosa esiste.
"""

import os
import re
import unittest
from pathlib import Path

import yaml

RADICE = Path(__file__).resolve().parents[2]
# Agent e skill vivono nel plugin `motore` del repo platform (una sola definizione
# per tutti i siti), caricato da `.claude/settings.json`. In CI il plugin può non
# esserci: i controlli che lo leggono si saltano, non falliscono.
PLUGIN = Path(os.environ.get("MOTORE_PLUGIN_DIR", Path.home() / "dev" / "platform" / "plugin"))
AGENTI = PLUGIN / "agents"
SKILL = PLUGIN / "skills"

# I sei tipi della catena minima. Uno in più su disco senza una riga qui è un
# agente che nessuno sa di avere; uno in meno è un workflow che chiama un tipo
# inesistente e muore al primo lancio.
LITE = {"lab-dossierista", "lab-scout", "lab-scout-europa",
        "lab-scrittore", "lab-verificatore", "lab-pubblicatore"}

# I cinque ruoli riusabili dal vero Agent Team editoriale. Il lead e la
# sessione principale, quindi non ha una definizione da teammate.
TEAM = {"data-editor", "source-researcher", "search-strategist",
        "data-journalist", "skeptical-editor"}
MEMORIA_TEAM = {"source-researcher", "skeptical-editor"}

# Il giudice cieco non appartiene alla catena: legge due bozze e dice quale si
# legge fino in fondo, senza avere il progetto in contesto. È un lavoro che
# sopravvive a qualunque catena produca i due testi. `admissions` decide che
# cosa entra nell'atlante, ed è a monte della scrittura.
ALTRI = {"giudice-cieco", "admissions"}

# I ruoli del modello operativo di platform (analytics, intake, SEO, sviluppo,
# postmortem, strategia): vivono nel plugin, non nella catena di questo repo.
OPERATIVI = {"analista", "scopritore", "auditor-seo", "pianificatore",
             "costruttore", "revisore", "postmortem", "direttore"}


def _frontmatter(percorso):
    testo = percorso.read_text(encoding="utf-8")
    if not testo.startswith("---"):
        return None
    return yaml.safe_load(testo.split("---")[1])


@unittest.skipUnless(AGENTI.exists(), "plugin motore non presente (MOTORE_PLUGIN_DIR)")
class GliAgentiSonoDichiarati(unittest.TestCase):
    def test_nessun_agente_avanza_senza_un_posto_dove_stare(self):
        sul_disco = {percorso.stem for percorso in AGENTI.glob("*.md")}
        self.assertEqual(sul_disco, LITE | TEAM | ALTRI | OPERATIVI)

    def test_ogni_agente_ha_un_frontmatter_che_si_carica(self):
        """Un `: ` dentro un `description` su riga sola non è YAML valido, e il
        file viene scartato **in silenzio**: l'agente non esiste e nessuno lo
        dice. È già successo a `scrittore-indicatore.md`, che per settimane non
        si caricava senza che niente diventasse rosso."""
        for percorso in sorted(AGENTI.glob("*.md")):
            with self.subTest(agente=percorso.stem):
                meta = _frontmatter(percorso)
                self.assertIsNotNone(meta, f"{percorso.name} senza frontmatter")
                self.assertEqual(meta.get("name"), percorso.stem)

    def test_solo_i_ruoli_durevoli_hanno_memoria_di_progetto(self):
        con_memoria = set()
        for nome in TEAM:
            meta = _frontmatter(AGENTI / f"{nome}.md") or {}
            if meta.get("memory"):
                con_memoria.add(nome)
                self.assertEqual(meta["memory"], "project")
                self.assertTrue(
                    (RADICE / ".claude" / "agent-memory" / nome / "MEMORY.md").exists(),
                    f"{nome} dichiara memoria senza MEMORY.md versionato",
                )
        self.assertEqual(con_memoria, MEMORIA_TEAM)

        settings = yaml.safe_load(
            (RADICE / ".claude" / "settings.json").read_text(encoding="utf-8")
        )
        self.assertIs(settings.get("autoMemoryEnabled"), True)

    def test_i_teammate_con_memoria_restano_senza_scrittura_generica(self):
        for nome in MEMORIA_TEAM:
            meta = _frontmatter(AGENTI / f"{nome}.md") or {}
            dichiarati = meta.get("tools") or []
            if isinstance(dichiarati, str):
                dichiarati = [voce.strip() for voce in dichiarati.split(",")]
            strumenti = set(dichiarati)
            self.assertNotIn("Write", strumenti)
            self.assertNotIn("Edit", strumenti)
            self.assertNotIn("Bash", strumenti)

    def test_le_skill_dichiarate_da_un_agente_esistono(self):
        """Una skill precaricata che non esiste non fa fallire niente: l'agente
        lavora senza, e la differenza si vede solo nel prodotto."""
        for percorso in sorted(AGENTI.glob("*.md")):
            meta = _frontmatter(percorso) or {}
            for nome in meta.get("skills") or []:
                with self.subTest(agente=percorso.stem, skill=nome):
                    self.assertTrue((SKILL / nome / "SKILL.md").exists(),
                                    f"{percorso.stem} precarica la skill inesistente {nome}")


@unittest.skipUnless(SKILL.exists(), "plugin motore non presente (MOTORE_PLUGIN_DIR)")
class LeSkillSiCaricano(unittest.TestCase):
    def test_ogni_skill_ha_un_frontmatter_valido(self):
        for percorso in sorted(SKILL.glob("*/SKILL.md")):
            with self.subTest(skill=percorso.parent.name):
                meta = _frontmatter(percorso)
                self.assertIsNotNone(meta, f"{percorso} senza frontmatter")
                self.assertEqual(meta.get("name"), percorso.parent.name)
                self.assertTrue((meta.get("description") or "").strip(),
                                f"{percorso.parent.name} senza description: "
                                f"è il campo su cui viene scelta")


class IComandiScrittiSonoEseguibili(unittest.TestCase):
    """I `bin/py -m qualcosa` citati nei documenti della catena minima.

    Un modulo citato e inesistente costa un turno a chi lo esegue, e il turno è
    il costo di questa architettura.
    """

    MODULO = re.compile(r"bin/py -m ([a-z_]+(?:\.[a-z_]+)+)")

    def _moduli_citati(self, percorso):
        return set(self.MODULO.findall(percorso.read_text(encoding="utf-8")))

    def _esiste(self, modulo):
        return (RADICE / Path(modulo.replace(".", "/") + ".py")).exists()

    def test_i_moduli_citati_dal_readme_del_lab_esistono(self):
        for modulo in sorted(self._moduli_citati(RADICE / "lab" / "README.md")):
            with self.subTest(modulo=modulo):
                self.assertTrue(self._esiste(modulo),
                                f"il README cita `bin/py -m {modulo}`, che non esiste")

    def test_i_moduli_citati_dagli_agenti_esistono(self):
        if not AGENTI.exists():
            self.skipTest("plugin motore non presente")
        for percorso in sorted(AGENTI.glob("*.md")):
            for modulo in sorted(self._moduli_citati(percorso)):
                with self.subTest(agente=percorso.stem, modulo=modulo):
                    self.assertTrue(self._esiste(modulo),
                                    f"{percorso.stem} esegue `bin/py -m {modulo}`, che non esiste")


@unittest.skipUnless(SKILL.exists(), "plugin motore non presente (MOTORE_PLUGIN_DIR)")
class IlGateDiPubblicazioneECompleto(unittest.TestCase):
    def test_la_skill_non_pubblica_solo_per_exit_code_zero(self):
        testo = (SKILL / "redazione-indicatore" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for requisito in (
            "non_trovate == 0",
            "link_inesistenti == 0",
            "`bloccanti` è vuoto",
            "`bozza_salvata` esiste",
            "--bozza <bozza_salvata>",
        ):
            with self.subTest(requisito=requisito):
                self.assertIn(requisito, testo)
        self.assertIn("ritorna exit code 0 anche quando", testo)
        self.assertIn("secondo controllo non è", testo)


if __name__ == "__main__":
    unittest.main()
