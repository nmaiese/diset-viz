"""Il testo che si mette davanti a chi scrive, montato dal codice.

Un solo blocco, e la separazione conta piu' del contenuto: **cio' che cambia
per ogni indicatore sta in fondo, cio' che non cambia mai sta in cima.** E' la
condizione perche' la parte costante possa restare in cache di prompt, e la
parte costante e' la maggioranza dei token.

E' il rimedio alla voce di costo misurata: 1,07 miliardi di token di lettura
cache per diciannove articoli, 235 volte l'output prodotto. Quel miliardo non
era prosa, era il repo riaperto a ogni turno perche' ogni ruolo caricava
`AGENT_CONTRACT.md`, il brief intero, `STYLE.md`, `WRITING_RUBRIC.md`, la skill
`scrittura-italiana` da 31 KB e tre skill di catena.

Qui il montaggio e' esplicito e misurabile, e la rubrica non c'e': un metro su
cui sei criteri su dieci stavano a 2,0 per entrambi i giudici ciechi non
misurava piu' niente, e caricarlo insegnava solo a scrivere per superarlo.

    python3 -m officina.brief ter-105
    python3 -m officina.brief ter-105 --parts     # quanto pesa ogni pezzo
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from officina import esempi
from packs import build as build_module

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_PATH = os.path.join(ROOT, "content", "STYLE.md")


def _voice():
    try:
        with open(VOICE_PATH, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


ISTRUZIONI = """\
Scrivi l'articolo di questa pagina indicatore.

Da dove viene la struttura: **dall'angolo piu' forte del pacchetto**, non da uno
scheletro. Se il pacchetto apre su una rottura nel tempo, l'articolo apre sul
tempo; se apre su un territorio fuori scala, apre da quel territorio. Non
esiste un ordine di sezioni obbligato, e ripetere per tutti gli indicatori la
sequenza definizione-quadro-dinamica-limiti e' il difetto che questo pacchetto
esiste per togliere: cinquantadue articoli su cinquantadue la usavano, e si
leggono come uno stampo.

Da dove vengono i numeri: **solo dal pacchetto**. La matrice ha ogni anno e ogni
territorio, quindi ogni cifra citabile e' li' dentro. Una cifra che non c'e' non
si scrive.

Da dove viene il perche': **solo dal contesto citabile**. Puoi dire perche' una
serie si muove soltanto appoggiandoti a un'affermazione del corpus, e
l'identificatore va nel campo `claims` **della sezione che se ne appoggia**,
non in fondo all'articolo. Da li' la pagina deriva la fonte che mostra al
lettore: un'attribuzione elencata altrove diventa un'istituzione nominata nel
testo e invisibile in pagina, che e' come citare senza fonte. Se il contesto e'
vuoto, l'articolo dice che cosa succede e dichiara che non sa perche': dedurre
una causa dai dati e' il modo in cui un articolo diventa falso restando
aritmeticamente corretto.

E vale al contrario: **non nominare un'istituzione che non stai citando.** Se
scrivi "Eurostat", "Banca d'Italia" o "SVIMEZ" senza un identificatore accanto,
il lettore vede un'attribuzione che non puo' controllare. La fonte del dato
(quella in cima al pacchetto) fa eccezione: quella la pagina la mostra sempre,
e nominarla per spiegare come e' costruito l'indicatore e' definizione, non
attribuzione.

Tre cose devono esserci, e sono requisiti, non divieti:
1. una frase che dice che cosa significa il numero per una persona;
2. una dinamica spiegata con un identificatore del corpus accanto;
3. una cosa che il numero non puo' dire.

Quanto lungo: **quanti angoli dice il pacchetto di sviluppare**, e ognuno deve
portare nel testo almeno una delle proprie cifre. Un angolo nominato e non
sviluppato non conta. C'e' un minimo di parole, non c'e' un massimo, e il
numero atteso e' un ordine di grandezza, non un bersaglio da centrare.

I `role` che una sezione puo' avere sono **quattro, e solo questi**:
`definizione`, `quadro`, `dinamica`, `limiti`. I tre sostanziali
(`quadro`, `dinamica`, `limiti`) ci sono sempre; `definizione` e' la sola che
si puo' omettere, e va omessa quando l'angolo piu' forte non e' una questione
di definizione. L'ordine invece e' libero: e' li' che si rompe lo stampo.

Le cifre che vedi nel pacchetto sono **tutte scrivibili**. Cio' che serviva
solo a ordinare gli angoli (pendenze di regressione, varianza spiegata,
z modificati) non e' qui apposta: non e' un'omissione, e non va cercato
altrove. Sono numeri che sembrano precisi e non dicono niente a chi legge, e
sono la ragione per cui la prima tornata di articoli e' uscita fredda.

Il modello di registro allegato si legge prima di scrivere, ad alta voce. Non se
ne copiano le parole e nemmeno le cifre: si copia il movimento, cioe' come entra
un numero nella frase, quanto dura una frase prima del punto, dove va la
cautela. E' l'unico esempio: mediarne otto produce l'assenza di registro.
"""


def compose(code, level=None):
    """(costante, variabile). Due pezzi, perche' solo il primo va in cache."""
    family, raw_id = build_module._resolve(code)
    pack = build_module.build_pack(family, raw_id, level)
    if pack is None:
        return None, None

    model = esempi.pick(pack["angles"])
    constant = "\n\n".join([
        "# Come si scrive qui",
        ISTRUZIONI,
        "# La voce",
        _voice(),
        f"# Il modello di registro: {model}",
        esempi.read(model),
    ])
    variable = "\n".join([
        "# Il pacchetto",
        build_module.render(pack),
        "",
        "# La matrice, anno per territorio",
        json.dumps(pack["matrix"], ensure_ascii=False, sort_keys=True),
    ])
    return constant, variable


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("code")
    parser.add_argument("--level", default=None)
    parser.add_argument("--parts", action="store_true",
                        help="quanto pesa ogni pezzo, invece del testo")
    args = parser.parse_args(argv)

    constant, variable = compose(args.code, args.level)
    if constant is None:
        print(f"nessun indicatore per {args.code}", file=sys.stderr)
        return 1

    if args.parts:
        # Quattro caratteri per token e' la regola del pollice sull'italiano:
        # serve a vedere le proporzioni, non a fatturare.
        for name, text in (("costante (in cache)", constant),
                           ("variabile (per indicatore)", variable)):
            print(f"{name:30} {len(text):8,} caratteri  ~{len(text) // 4:6,} token")
        share = len(constant) / (len(constant) + len(variable))
        print(f"{'quota cacheabile':30} {share:.0%}")
        return 0

    print(constant)
    print(variable)
    return 0


if __name__ == "__main__":
    sys.exit(main())
