"""Dal view model dell'app al pacchetto, e la lunghezza che ne discende.

Questo e' l'unico modulo di `packs` che conosce `app`. Fa tre cose che il brief
di oggi non fa:

1. **Apre l'interno della matrice.** `scripts/indicator_brief.py` porta il primo
   e l'ultimo valore di ogni territorio e la serie delle medie, e nient'altro.
   Gli articoli pubblicati citano valori a meta' serie ("nel 2014 l'Emilia-Romagna
   arrivo' a 52,13") che da li' non si potevano prendere: `docs/CANARY.md` lo
   chiama "un buco nel perimetro". Qui la matrice anno per territorio c'e'
   tutta, quindi ogni cifra citabile ha una provenienza.
2. **Ordina gli angoli invece di stampare blocchi fissi.** E' il punto: la
   forma del pacchetto cambia da un indicatore all'altro, quindi la prosa non
   puo' ereditare una forma sola.
3. **Deriva la lunghezza dalla storia.** Un minimo si', un massimo no.

Uso:

    python3 -m packs.build ter-105
    python3 -m packs.build bes-10AMB001P --level provincia
    python3 -m packs.build ter-105 --json
"""
from __future__ import annotations

import argparse
import csv
import functools
import json
import os
import sys

from app import sources
from app.data import REGION_GEO_AREA
from app.indicator_notes import build_indicator_explain
from app.indicator_view import build_indicator_view
from packs import angles as angles_module
from packs import context as context_module

# Le note metodologiche della fonte, dove Istat dichiara i cambi di metodo.
# Duecentotre righe su trecentosettantotto ne hanno una, e centoquarantasei
# nominano un anno. Finora le leggeva a mano il verificatore, e almeno un
# articolo l'ha pagata: `ter-60` aveva costruito la propria tesi sulla finestra
# prima di un cambio di metodo senza dirlo.
DEFINITIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "definitions", "istat_territoriali.csv")

# Le tre ripartizioni con cui il divario viene raccontato: Istat separa Sud e
# Isole, qui stanno insieme, come in `app/divari.py`. La mappa e' quella di
# `app/data.py`, non una seconda: due copie di una ripartizione sono due
# ripartizioni che divergono.
AREA_BY_KEY = {
    key: ("Mezzogiorno" if area in ("Sud", "Isole") else area)
    for key, area in REGION_GEO_AREA.items()
}

# Il minimo sotto cui un articolo non e' un articolo, e il passo per ogni unita'
# di storia trovata. Nessun massimo: la lunghezza la decide la storia, e un
# indicatore con quarantasei anni e tre rotture merita piu' spazio di uno con
# otto anni piatti. Provvisori: si tarano quando ci sono articoli nuovi da
# misurare.
MIN_WORDS = 300
WORDS_PER_UNIT = 260


def _resolve(code):
    """`ter-105` o `ter:105` -> (famiglia, id grezzo)."""
    text = code.replace(":", "-", 1)
    prefix, _, raw = text.partition("-")
    for family, meta in sources.SOURCES.items():
        if meta["acronym"] == prefix:
            return family, raw
    return sources.split_internal_id(code)


def matrix_by_name(level):
    """{anno: {nome territorio: valore}} dal livello del view model.

    Per nome e non per chiave: il pacchetto lo legge chi scrive, e una chiave
    slug non e' un territorio che si possa nominare in una frase.
    """
    # Da `territories` e non da `observations`, ed e' una correzione.
    # `observations` copre **solo l'ultimo anno**: un territorio con dati nei
    # primi anni e assente nell'ultimo non ha un nome, e la chiave slug filtra
    # nel pacchetto. Su `ter-30` erano tre su quindici, e chi scriveva leggeva
    # "liguria", "lombardia", "piemonte". Peggio: la guardia numerica costruisce
    # la stessa mappa, quindi una cifra attribuita a "Liguria" nella prosa non
    # combaciava con il territorio "liguria" nei dati e **non veniva
    # controllata**. Stessa classe dei 67 indicatori provinciali senza guardia:
    # un controllo che non incontra il nome resta verde e non lo dice.
    names = {row["key"]: row["name"] for row in level["territories"]}
    out = {}
    for year, row in level["matrix"].items():
        clean = {names.get(key, key): value
                 for key, value in row.items() if value is not None}
        if clean:
            out[int(year)] = clean
    return out


def groups_by_name(level):
    """{nome territorio: ripartizione}, vuoto sui livelli che non ne hanno.

    Le province non hanno una ripartizione in questo progetto: il rilevatore dei
    gruppi tace, invece di inventarne una.
    """
    return {row["name"]: AREA_BY_KEY[row["key"]]
            for row in level["territories"] if row["key"] in AREA_BY_KEY}


@functools.lru_cache(maxsize=1)
def _notes_by_id():
    try:
        with open(DEFINITIONS_PATH, encoding="utf-8-sig", newline="") as handle:
            return {row["id"].strip(): (row.get("note") or "").strip()
                    for row in csv.DictReader(handle, delimiter=";")
                    if (row.get("note") or "").strip()}
    except OSError:
        return {}


def source_note(family, raw_id):
    """La nota metodologica di questo indicatore, se la fonte ne pubblica una.

    Solo per la famiglia territoriale: e' l'unica per cui il progetto ha
    scaricato i metadati. Le altre restano senza, e il rilevatore delle rotture
    di metodo tace, che e' meglio di una rottura dedotta.
    """
    if family != "territorial":
        return None
    return _notes_by_id().get(str(raw_id).strip()) or None


def human_scale(meta):
    """La frase che traduce l'unita' in una vita, se il progetto ne ha una.

    Non la scrive questo modulo: la costruisce gia' `app/indicator_notes.py`
    per il blocco "Come leggere il dato" della pagina, e ricalcolarla qui
    sarebbe una seconda verita' sullo stesso fatto. Serve al pacchetto perche'
    e' il primo dei tre requisiti positivi: un articolo che non dice mai che
    cosa significa il numero per una persona resta freddo anche quando ogni
    cifra e' giusta.
    """
    try:
        explain = build_indicator_explain({
            "id": meta.get("id"),
            "indicator": meta.get("name"),
            "name": meta.get("name"),
            "theme": meta.get("theme"),
            "unit": meta.get("unit"),
            "archive": meta.get("archive") or meta.get("definition") or "",
        })
    except Exception:
        return None
    return explain.get("example") or None


def suggested_words(total):
    """La lunghezza che questa storia si merita, come banda con un pavimento."""
    target = int(MIN_WORDS + WORDS_PER_UNIT * total)
    return {"minimo": MIN_WORDS, "atteso": target, "massimo": None}


# La soglia sotto cui un angolo non merita di essere sviluppato, espressa come
# quota della forza del piu' forte. Mezzo: un angolo che vale meta' del
# migliore ha ancora qualcosa da dire, uno che vale un quarto e' rumore.
DEVELOP_SHARE = 0.5


def angles_to_develop(found):
    """Quanti angoli l'articolo deve sviluppare davvero. Almeno uno.

    E' la lunghezza detta in modo che si possa verificare. Chiedere "765
    parole" non funziona: nella prima run il pacchetto ne chiedeva 765 e 540
    per due indicatori, una forbice del 42%, e le bozze sono uscite a 657 e
    619, una forbice del 13%. **La lunghezza convergeva invece di divergere**,
    che era il criterio di fallimento scritto nel piano.

    Un numero di parole e' una richiesta che un modello media; un numero di
    angoli da sviluppare e' una richiesta che si conta. E la lunghezza segue da
    sola, perche' quattro angoli non stanno in quattrocento parole.
    """
    if not found:
        return 0
    strongest = found[0]["strength"]
    if strongest <= 0:
        return 1
    worth = [angle for angle in found if angle["strength"] >= strongest * DEVELOP_SHARE]
    return max(1, len(worth))


def build_pack(family, raw_id, level_key=None, notes=None):
    view = build_indicator_view(family, raw_id)
    if view is None:
        return None
    meta = view["meta"]
    level = next((lv for lv in view["levels"] if lv["key"] == level_key),
                 view["levels"][0])

    matrix = matrix_by_name(level)
    if notes is None:
        notes = source_note(family, raw_id)
    found = angles_module.find(matrix, groups=groups_by_name(level), notes=notes)
    found, constraints = angles_module.split_constraints(found)
    total = angles_module.total_strength(found)

    return {
        "meta": {
            "id": meta["id"],
            "name": meta.get("name"),
            "unit": meta.get("unit"),
            "theme": meta.get("theme"),
            "source": meta.get("source"),
            "direction": meta.get("direction"),
        },
        "level": level["key"],
        "years": sorted(matrix),
        "territories": sorted({name for row in matrix.values() for name in row}),
        # L'interno della matrice: la cosa che il brief non ha mai portato.
        "matrix": matrix,
        "stats": level["stats"],
        "angles": found,
        # I vincoli valgono su tutto l'articolo, non su un paragrafo: una
        # rottura di metodo dentro la finestra decide che cosa si puo'
        # confrontare, e non e' una storia con cui aprire.
        "constraints": constraints,
        # La licenza di spiegare perche' i numeri si muovono. Senza questo
        # blocco l'articolo puo' descrivere solo la geometria della serie, ed
        # e' il motivo per cui i cinquantadue riscritti sono corretti e freddi.
        "context": context_module.as_context(
            meta["id"], meta.get("theme"), human_scale(meta),
            indicator_name=meta.get("name")),
        "total_strength": total,
        "words": suggested_words(total),
        # La lunghezza detta in modo verificabile: quanti angoli vanno
        # sviluppati, non quante parole. Vedi `angles_to_develop`.
        "develop": angles_to_develop(found),
    }


def render(pack):
    meta = pack["meta"]
    out = [
        f"{meta['id']}  {meta.get('name') or ''}",
        f"  unita': {meta.get('unit') or '?'}   verso: {meta.get('direction') or '?'}"
        f"   livello: {pack['level']}",
        f"  anni: {pack['years'][0]}-{pack['years'][-1]}"
        f"   territori: {len(pack['territories'])}",
        "",
        f"STORIA TROVATA: {pack['total_strength']}",
        f"  ANGOLI DA SVILUPPARE: {pack['develop']}. Ognuno deve portare nel testo"
        f" almeno una delle proprie cifre.",
        f"  Un angolo nominato e non sviluppato non conta. Da qui viene la"
        f" lunghezza: minimo {pack['words']['minimo']} parole, nessun massimo,"
        f" e {pack['words']['atteso']} e' l'ordine di grandezza, non un bersaglio.",
        "",
    ]
    for constraint in pack.get("constraints") or []:
        out.append(f"VINCOLO: {constraint['type']}, "
                   f"anni {constraint['figures'].get('anni_citati_nella_nota')}")
        out.append(f"  {constraint['figures'].get('nota', '')[:300]}")
        out.append(f"  {constraint['caution']}")
        out.append("")
    ctx = pack.get("context") or {}
    if ctx.get("scala_umana"):
        out.append(f"SCALA UMANA: {ctx['scala_umana']}")
        out.append("")
    out.append("PERCHE' SI MUOVE, CITABILE")
    if ctx.get("senza_contesto"):
        out.append("  niente nel corpus per questo tema.")
        out.append("  L'articolo non ha il diritto di spiegare la dinamica:")
        out.append("  lo dice, invece di dedurre una causa dai dati.")
    for claim in ctx.get("affermazioni") or []:
        out.append(f"  [{claim['id']}] {claim['istituzione']}, letta il {claim['letta_il']}")
        out.append(f"     «{claim['citazione']}»")
        out.append(f"     {claim['url']}")
    out.append("")
    out.append("ANGOLI, DAL PIU' FORTE")
    if not pack["angles"]:
        out.append("  nessuno: questa serie non ha una storia strutturale.")
        out.append("  Un articolo qui e' una nota breve, non un pezzo.")
    for position, angle in enumerate(pack["angles"], start=1):
        out.append(f"  {position}. [{angle['strength']:.2f}] {angle['type']}")
        for field, value in angle["figures"].items():
            out.append(f"       {field}: {value}")
        if angle["territories"]:
            out.append(f"       territori: {', '.join(angle['territories'][:8])}")
        if angle["caution"]:
            out.append(f"       cautela: {angle['caution']}")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Il pacchetto di un indicatore.")
    parser.add_argument("code", help="es. ter-105, bes-10AMB001P")
    parser.add_argument("--level", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--notes", default=None,
                        help="nota metodologica della fonte, per le rotture di metodo")
    args = parser.parse_args(argv)

    family, raw_id = _resolve(args.code)
    pack = build_pack(family, raw_id, args.level, notes=args.notes)
    if pack is None:
        print(f"nessun indicatore per {args.code}", file=sys.stderr)
        return 1
    print(json.dumps(pack, ensure_ascii=False, indent=1) if args.json else render(pack))
    return 0


if __name__ == "__main__":
    sys.exit(main())
