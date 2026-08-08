"""L'impronta della bozza: che cosa identifica, e chi la ricalcola dall'altra parte.

Fra chi scrive e chi verifica il testo passa dentro un prompt, e il verificatore
lo ribatte in un heredoc. L'impronta è l'unica cosa che sta fra una ribattitura
infedele e il file che finisce su una pagina pubblica.

Due proprietà, e nessuna delle due si legge guardando il codice:

1. **identifica il testo**, cioè cambia quando cambia una lettera sola. I soli
   conteggi non bastavano: `sale` che diventa `cale` lascia identici caratteri,
   parole, cifre, sezioni e fonti, e ribalta il verso della frase.
2. **si calcola uguale in JavaScript**, perché il confronto lo fa lo script del
   workflow, che non è Python. Sono due implementazioni della stessa funzione,
   che è la forma che diverge: qui si esegue davvero quella JavaScript, estratta
   dal workflow, sulla stessa bozza.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab.controlla import impronta

RADICE = Path(__file__).resolve().parents[2]
WORKFLOW = RADICE / ".claude" / "workflows" / "indicatore-lite.js"

BOZZA = {
    "lead": "Il divario sale di 2,4 punti in un anno, e non e' un caso isolato.",
    "sections": [
        {"role": "quadro", "h": "Dove si vede",
         "body": "In Calabria il valore sale a 19,10 nel 2025.\n\nAltrove tiene."},
        {"role": "dinamica", "h": "Che cosa e' cambiato",
         "body": "Dal 2018 la distanza cresce di 3 punti."},
    ],
    "fonti": [{"testo": "Istat, rapporto 2025", "url": "https://www.istat.it/esempio"}],
}


def _cambia_una_lettera(bozza):
    """`sale` che diventa `cale`: una lettera, stessa lunghezza, verso opposto."""
    copia = json.loads(json.dumps(bozza))
    copia["sections"][0]["body"] = copia["sections"][0]["body"].replace("sale", "cale", 1)
    return copia


class LImprontaIdentificaIlTesto(unittest.TestCase):
    def test_una_lettera_cambiata_lascia_identici_tutti_i_conteggi(self):
        """Il caso che l'impronta a soli conteggi faceva passare. Se un giorno
        questo test fallisce perche' un conteggio cambia, non e' l'impronta a
        essersi rotta: e' l'esempio a non provare piu' niente."""
        prima, dopo = impronta(BOZZA), impronta(_cambia_una_lettera(BOZZA))
        for campo in ("caratteri", "parole", "cifre", "sezioni", "fonti"):
            with self.subTest(campo=campo):
                self.assertEqual(prima[campo], dopo[campo])

    def test_e_il_digest_se_ne_accorge(self):
        self.assertNotEqual(impronta(BOZZA)["digest"],
                            impronta(_cambia_una_lettera(BOZZA))["digest"])

    def test_il_digest_e_stabile_fra_una_run_e_l_altra(self):
        """Otto caratteri esadecimali, sempre gli stessi per lo stesso testo:
        un hash che dipendesse dal seed del processo (come `hash()` di Python)
        fermerebbe ogni articolo, perche' i due lati girano in processi
        diversi."""
        self.assertEqual(impronta(BOZZA)["digest"], impronta(BOZZA)["digest"])
        self.assertRegex(impronta(BOZZA)["digest"], r"^[0-9a-f]{8}$")

    def test_lo_spazio_non_conta(self):
        """Un a capo in piu' in un heredoc non e' una ribattitura infedele, e
        fermare un articolo per quello insegnerebbe a ignorare il blocco."""
        spaziata = json.loads(json.dumps(BOZZA))
        spaziata["lead"] = "  " + spaziata["lead"].replace(" ", "  ") + "\n"
        self.assertEqual(impronta(BOZZA)["digest"], impronta(spaziata)["digest"])


class LoStessoNumeroDallAltraParte(unittest.TestCase):
    """La meta' JavaScript, eseguita davvero e non riletta.

    Le due funzioni si estraggono dal workflow contando le graffe: importare il
    file intero lo eseguirebbe, e uno script di workflow senza il suo runtime
    (`agent`, `pipeline`, `args`) non parte.
    """

    def _estrai(self, sorgente, nome):
        inizio = sorgente.index(f"function {nome}(")
        livello, dentro = 0, False
        for posizione in range(inizio, len(sorgente)):
            if sorgente[posizione] == "{":
                livello, dentro = livello + 1, True
            elif sorgente[posizione] == "}":
                livello -= 1
                if dentro and livello == 0:
                    return sorgente[inizio:posizione + 1]
        raise AssertionError(f"funzione {nome} non chiusa in {WORKFLOW}")

    @unittest.skipIf(shutil.which("node") is None, "node non installato")
    def test_javascript_e_python_calcolano_la_stessa_impronta(self):
        sorgente = WORKFLOW.read_text(encoding="utf-8")
        modulo = "\n".join([self._estrai(sorgente, "digestDi"),
                            self._estrai(sorgente, "improntaDi"),
                            "const bozza = JSON.parse(process.argv[2])",
                            "console.log(JSON.stringify(improntaDi(bozza)))"])
        with tempfile.TemporaryDirectory() as cartella:
            script = Path(cartella) / "impronta.mjs"
            script.write_text(modulo, encoding="utf-8")
            uscita = subprocess.run(
                ("node", str(script), json.dumps(BOZZA, ensure_ascii=False)),
                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(uscita.stdout), impronta(BOZZA))


if __name__ == "__main__":
    unittest.main()
