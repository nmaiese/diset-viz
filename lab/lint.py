"""Il metro della prosa: la facciata da riga di comando.

Le regole stanno in `scripts/prose_rules.py`, non qui, perche' le legge anche
l'app servita e `lab/` non entra nell'immagine Docker. Qui resta il modo di
chiamarle a mano, che e' quello che la catena scrive nei suoi prompt:

    bin/py -m lab.lint content/indicators/30.json
"""
import sys

from scripts.prose_rules import (  # noqa: F401  (re-export: la catena importa da qui)
    CIFRA,
    LEAD_MASSIMO,
    LINK_VECCHIO,
    PAROLE_MINIME,
    SCOPERTI_MASSIMI,
    SPIEGA,
    VIETATI,
    main,
    rilievi,
)

if __name__ == "__main__":
    sys.exit(main())
