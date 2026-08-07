#!/usr/bin/env python3
"""Nega l'advisor agli agenti dell'officina, come hook invece che come frase.

Perche' esiste. Il campo `disallowedTools: advisor` nel frontmatter **non
funziona**: l'advisor non e' un tool della lista che quel campo filtra, e la
prova su `ter-30` lo ha visto nel trascritto (*"let me check my plan with the
advisor"*) con il divieto gia' scritto. La mitigazione e' finita in prosa,
dentro ognuno dei tre agenti, ed e' rimasta l'unico pezzo di perimetro affidato
al prompt invece che agli strumenti: cioe' l'unico che puo' cedere in silenzio.

Quanto vale: nove chiamate nella prima run, $5,58, il 26% del costo, e due
nella prova, $1,78, il 29%. Sono richieste a contesto pieno **senza cache**, e
non compaiono in nessun contatore aggregato: stanno in `usage.iterations` col
tipo `advisor_message`, che e' il motivo per cui `scripts/baseline_tokens.py`
le somma a mano.

Uscita 0 = permesso, 2 = bloccato con la ragione su stderr, che e' il canale
che l'harness rilegge all'agente. Come `agent_guard.py`: un errore interno
esce 0, perche' un hook che si rompe non deve fermare una catena non
presidiata per un guasto che non e' dell'agente.

Se al giro dopo il trascritto mostra ancora chiamate advisor, allora nemmeno
`PreToolUse` vede quella chiamata, e la sola via rimasta e' una configurazione
di sessione da chiedere. La differenza si legge in una riga di
`baseline_tokens.py --workflow`.

Stdlib puro, come tutto il resto della catena.
"""

from __future__ import annotations

import json
import sys

MOTIVO = (
    "L'advisor e' negato agli agenti dell'officina. Hai gia' tutto cio' che ti "
    "serve nel messaggio della run: se qualcosa sembra mancare, non manca, non "
    "e' li' perche' non deve entrare nel tuo lavoro. Una consulenza a contesto "
    "pieno e senza cache e' la voce di costo piu' cara di questa catena "
    "(il 26% della prima run) e non lascia traccia in nessun contatore. "
    "Prosegui con quello che hai."
)


def main() -> int:
    try:
        evento = json.load(sys.stdin)
    except Exception:
        return 0
    nome = str(evento.get("tool_name") or "")
    if "advisor" not in nome.lower():
        return 0
    print(MOTIVO, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
