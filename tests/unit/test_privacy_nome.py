"""Il nome del titolare non esce dalle pagine e dai documenti pubblici.

Regola di privacy: il nome del titolare (nome completo e nome di battesimo)
compare solo in `config/identita.yaml` e nel template della pagina privacy
(`app/templates/privacy.html`). Mai in firme pubbliche, box, report o docs di
gioco. Questo test legge i file tracciati da git negli ambiti `app/`,
`content/`, `config/`, `docs/GIOCO.md` e `reports/adsense_ondata_1*.md` e
fallisce se trova il nome altrove.

`Nello` e' anche una preposizione articolata (in + lo), e qui importa: il
confronto e' case-sensitive, quindi la preposizione in minuscolo `nello` non
scatta mai. Resta il falso positivo a inizio frase, dove la preposizione porta
la maiuscola. Nei file in ambito la preposizione maiuscola compare solo davanti
a due parole, trovate davvero nei file: `stesso` («Nello stesso anno», «Nello
stesso tema», «Nello stesso intervallo», «Nello stesso giorno») e `stato`
(«Nello stato»). Il lookahead negativo ignora quindi solo queste due: se un
testo nuovo scrivesse «Nello sviluppo» o «Nello spazio», il test lo segnerebbe
come nome e andrebbe aggiunto al lookahead.
"""

import re
import subprocess
import unittest
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]

# I due soli posti dove la regola ammette il nome.
CONSENTITI = {
    "config/identita.yaml",
    "app/templates/privacy.html",
}

# Eccezioni temporanee, da svuotare dopo il merge del ramo
# `agenti/identita-editoriale`: quel ramo toglie il nome da `app/publisher.py`
# (`EDITOR_NAME = "Aniello Maiese"`) e smette di stampare `{{ editor_name }}`
# fuori dal box (about.html, metodologia.html e la sua copia 1.0). Finche' non
# e' unito, il nome esce ancora da questi file.
ECCEZIONI_IN_ATTESA_IDENTITA = {
    "app/publisher.py",
    "app/templates/about.html",
    "app/templates/methodology.html",
    "app/templates/v1/metodologia.html",
}

_NOME = re.compile(r"\b(?:Aniello|Maiese)\b|\bNello\b(?!\s+(?:stesso|stato)\b)")


def _in_ambito(percorso):
    return (
        percorso.startswith(("app/", "content/", "config/"))
        or percorso == "docs/GIOCO.md"
        or percorso.startswith("reports/adsense_ondata_1")
    )


class IlNomeDelTitolare(unittest.TestCase):
    def test_compare_solo_nei_posti_ammessi(self):
        file = subprocess.run(
            ["git", "ls-files"],
            cwd=RADICE, capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        violazioni = []
        for percorso in file:
            if not _in_ambito(percorso):
                continue
            if percorso in CONSENTITI or percorso in ECCEZIONI_IN_ATTESA_IDENTITA:
                continue
            testo = (RADICE / percorso).read_text(encoding="utf-8", errors="replace")
            for match in _NOME.finditer(testo):
                riga = testo.count("\n", 0, match.start()) + 1
                violazioni.append(f"{percorso}:{riga}: {match.group(0)}")
        self.assertEqual(
            [], violazioni,
            "nome del titolare fuori dai posti ammessi:\n" + "\n".join(violazioni),
        )


if __name__ == "__main__":
    unittest.main()
