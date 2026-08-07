"""L'unico cancello editoriale: deterministico, senza modelli, eseguibile da solo.

Sostituisce una rubrica a venti punti che non discriminava piu' (sei criteri su
dieci a 2,0 per entrambi i giudici ciechi, punteggi finali 19,3 e 18,9) e un
critico di leggibilita' che non ha mai girato nemmeno una volta.

Fa due cose che prima erano separate o assenti.

**Raccoglie le guardie che gia' funzionavano.** Le verifiche numeriche vivevano
dentro `tests/integration/test_indicator_texts.py`, quindi controllare un
articolo voleva dire eseguire l'intera suite. Adesso stanno qui e la suite le
importa: una implementazione, due chiamanti.

**Aggiunge la regola che toglie il freddo.** Ogni sezione che racconta una
dinamica deve portare almeno un identificatore del corpus
(`data/corpus/claims/`). E' un controllo **posizionale**, non lessicale, e la
differenza non e' un dettaglio: cercare i connettivi causali non funziona
perche' nei 375 articoli sono quasi tutti definitori ("dipende dal
denominatore") mentre la causalita' vera viaggia senza connettivi ("si e'
chiusa dal basso, pero', non dall'alto"). Un lint lessicale segnalerebbe le
definizioni, non vedrebbe i meccanismi, e insegnerebbe al modello a scrivere
ancora piu' implicito, cioe' ancora piu' freddo.

    python3 -m officina.lint                 # tutto il catalogo
    python3 -m officina.lint ter-105         # un articolo
    python3 -m officina.lint --json
    python3 -m officina.lint --severity blocca

Uscita diversa da zero se qualcosa blocca. Le due severita':

- `blocca`  l'articolo non esce. Cifre false, caratteri vietati, gemelli.
- `segnala` va guardato, non ferma niente. E' dove stanno le regole nuove
            finche' il catalogo non le rispetta: una regola che boccia
            trecento articoli il giorno che nasce non e' un cancello, e'
            un blocco della produzione.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import sys
from collections import Counter

from app import indicator_texts, sources
from app.indicator_view import build_indicator_view
from packs import context as context_module
from scripts import indicator_store

# `content/STYLE.md` li vieta in ogni prosa autorata, titoli compresi.
BANNED = ("—", "–", ";", "…")
# Il lead e' anche la meta description: una prima frase piu' lunga di cosi' non
# puo' funzionare come tale.
LEAD_FIRST_SENTENCE_MAX = 200
# Sotto questa somiglianza due articoli fratelli si leggono come lo stesso
# stampo. E' anche l'argine contro cio' che Google chiama scaled content abuse:
# "molte pagine generate allo scopo primario di manipolare il ranking".
TWIN_SIMILARITY = 0.82
MIN_WORDS = 300
# Sotto le venticinque parole un blocco e' una didascalia, non un paragrafo che
# deve reggersi; sotto i tre paragrafi la quota vale 0, 1/2 o 1 e non misura.
PARAGRAPH_MIN_WORDS = 25
PARAGRAPH_MIN_COUNT = 3
CALIBRAZIONE_PROSA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "calibrazione_prosa.json")

BLOCKS = "blocca"
FLAGS = "segnala"


# --------------------------------------------------------------------------
# lettura del catalogo, condivisa con la suite
# --------------------------------------------------------------------------

def level_of(entry):
    return entry.get("level") or indicator_texts.DEFAULT_LEVEL


def view_of(key):
    family, raw_id = sources.split_internal_id(key)
    return build_indicator_view(family, raw_id)


def view_level(key, entry):
    """Il livello per cui l'articolo e' stato scritto.

    Tutto cio' che dipende dal livello si legge da `levels`, mai da `meta`:
    `meta.year_min/year_max` valgono su tutti i livelli insieme, ed e'
    esattamente cosi' che un articolo provinciale e' finito giudicato contro
    gli anni regionali.
    """
    view = view_of(key)
    if view is None:
        return None
    wanted = level_of(entry)
    return next((lv for lv in view["levels"] if lv["key"] == wanted), None)


def values_of(key, entry, year=None):
    """{territorio: valore} per un anno del livello che l'articolo descrive.

    Senza `year`, l'anno che l'articolo descrive. Con `year`, quell'anno: e' cio'
    che serve per controllare le cifre storiche invece di saltarle.
    """
    level = view_level(key, entry)
    if level is None:
        return {}
    wanted = year or entry.get("vintage") or level["year_max"]
    matrix = level["matrix"].get(str(wanted)) or {}
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
    return {names.get(territory_key, territory_key): value
            for territory_key, value in matrix.items() if value is not None}


def prose_of(entry):
    """Ogni pezzo di prosa autorata, come (campo, testo). Titoli compresi."""
    fields = []
    for field in ("h1", "seo_title"):
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            fields.append((field, value))
    if entry.get("lead"):
        fields.append(("lead", entry["lead"]))
    for section in entry.get("sections") or []:
        if section.get("body"):
            fields.append((f"sections.{section.get('role')}", section["body"]))
    return fields


def territory_alternation(texts):
    """L'alternativa regex dei nomi di territorio, derivata dai dati.

    Elencarli a mano e' il modo in cui 67 indicatori provinciali su 103
    province sono rimasti senza nessuna verifica: la lista diceva venti
    regioni, le guardie giravano, non incontravano nessun nome e restavano
    verdi. Una lista scritta a mano non si accorge di aver smesso di coprire.
    """
    names = set()
    for key, entry in texts.items():
        names.update(values_of(key, entry))
    ordered = sorted(names, key=lambda name: (-len(name), name))
    return "|".join(re.escape(name) for name in ordered)


# --------------------------------------------------------------------------
# i pattern numerici
# --------------------------------------------------------------------------

NUMBER = r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"
ABOVE = r"(?:supera(?:no)?|sopra|oltre|più di|almeno|maggiore di)"
BELOW = r"(?:scende|scendono|sotto|meno di|inferiore a|non arriva)"
# Solo presente e passato prossimo: l'imperfetto ("Molise stava a 1,71") parla
# di un altro anno.
STATE = (r"(?:è(?: (?:scesa|sceso|salita|salito|arrivata|arrivato))?|sta|"
         r"si ferma|arriva|resta|vale|segna|tocca|scende|sale)")
HEDGE = re.compile(r"(?:circa|quasi|poco (?:più|meno) di|intorno a|attorno a|sui|"
                   r"sulle|oltre|almeno|appena)\s*$", re.I)
A_GAP = re.compile(r"\s*punti\b", re.I)
ANOTHER_YEAR = re.compile(r"\s*(?:nel|del|in)\s+(?:19|20)\d\d\b", re.I)
ANOTHER_INDICATOR = re.compile(r"\]\(/indicatore/")


def patterns(alternation):
    """I tre pattern numerici sopra un'alternativa di territori."""
    gap = r"(?:(?!" + alternation + r"|\d)[^.,;])"
    return {
        "value_of": re.compile(
            NUMBER + r"\s*(?:%|per cento|punti|anni|euro)?\s+"
            r"(?:di|del|della|dell'|degli|delle|in|a|ad|nel|nella)\s+"
            r"\b(" + alternation + r")\b"),
        "states_value": re.compile(
            r"\b(" + alternation + r")\b" + gap + r"{0,18}?\s" + STATE +
            r"\s+(?:a|al|allo|alla|ad)?\s*" + NUMBER, re.I),
        "threshold": re.compile(
            rf"\b({ABOVE}|{BELOW})\s+(?:il|lo|la|i|gli|le|a|ai|al)?\s*"
            rf"{NUMBER}\s*(?:%|per cento)?\s*(?:in|a|nel|nella|per)\s+"
            rf"\b((?:{alternation})(?:\s*(?:,|e)\s*(?:{alternation}))*)\b", re.I),
    }


def number_of(raw):
    return float(raw.replace(".", "").replace(",", "."))


def states_a_value(text, match):
    """Il match e' davvero un valore di quel territorio in quest'anno?

    Le tre esclusioni vengono da tre falsi allarmi veri: un divario ("il Molise
    sta 39,4 punti sopra le Marche"), un anno esplicito ("la Sardegna segna
    81,67 nel 2020"), e le cifre di una serie linkata nella stessa frase.
    """
    before = text[max(0, match.start() - 30):match.start(2)]
    if "," not in match.group(2) and HEDGE.search(before.rstrip()):
        return False
    after = text[match.end():match.end() + 24]
    if A_GAP.match(after) or ANOTHER_YEAR.match(after):
        return False
    start = text.rfind(".", 0, match.start()) + 1
    stop = text.find(".", match.end())
    sentence = text[start:stop if stop != -1 else len(text)]
    return not ANOTHER_INDICATOR.search(sentence)


# --------------------------------------------------------------------------
# le regole
# --------------------------------------------------------------------------

def _finding(rule, severity, detail, field=None):
    return {"rule": rule, "severity": severity, "detail": detail, "field": field}


@functools.lru_cache(maxsize=1)
def calibrazione_prosa():
    """Le soglie misurate su `content/esempi/`. Vuoto se il file non c'e'.

    Assente vuol dire regola spenta, non lint rotto: la calibrazione si
    rigenera, e un cancello che muore perche' manca un file di misura ferma la
    produzione per la ragione sbagliata.
    """
    try:
        with open(CALIBRAZIONE_PROSA, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def check_banned_characters(entry, **_):
    found = []
    for field, text in prose_of(entry):
        for char in BANNED:
            if char in text:
                found.append(_finding("caratteri-vietati", BLOCKS,
                                      f"contiene {char!r}", field))
    return found


def check_lead(entry, **_):
    lead = (entry.get("lead") or "").strip()
    if not lead:
        return [_finding("lead", BLOCKS, "manca")]
    first = re.split(r"(?<=[.!?])\s", lead)[0]
    if len(first) > LEAD_FIRST_SENTENCE_MAX:
        return [_finding("lead", BLOCKS,
                         f"prima frase di {len(first)} caratteri, non puo' "
                         f"servire da meta description", "lead")]
    return []


def check_figures(entry, key=None, compiled=None, **_):
    """Ogni cifra attribuita a un territorio contro il valore vero.

    Copre i due versi in cui la prosa lo scrive, perche' quella provinciale usa
    l'opposto di quella regionale: "il 24,3% del Molise" e "Gorizia si ferma a
    18". Gli interi contano solo nel secondo verso e con mezzo punto di
    tolleranza: su una serie provinciale un intero e' il valore, non
    un'approssimazione.
    """
    values = values_of(key, entry)
    if not values or not compiled:
        return []
    found = []
    for field, text in prose_of(entry):
        for match in compiled["value_of"].finditer(text):
            raw, territory = match.group(1), match.group(2)
            if "," not in raw or territory not in values:
                continue
            actual = values[territory]
            if abs(number_of(raw) - actual) > max(0.06, abs(actual) * 0.011):
                found.append(_finding("cifra-falsa", BLOCKS,
                                      f"{territory} detto {raw}, dato "
                                      f"{round(actual, 2)}", field))
        for match in compiled["states_value"].finditer(text):
            territory, raw = match.group(1), match.group(2)
            if territory not in values:
                continue
            # Una cifra con l'anno scritto accanto ("segna 81,67 nel 2020") non
            # si salta piu': si controlla **contro quell'anno**. L'esclusione
            # nasceva da un falso allarme vero, ma nascondeva un buco che la
            # macchina nuova allarga, perche' gli angoli sono quasi tutti
            # storici (rotture di pendenza, ritorni a un livello, sorpassi):
            # la prosa cita molte piu' cifre di anni passati di quante ne
            # citasse quella vecchia, e nessuna era controllata.
            stated = ANOTHER_YEAR.match(text[match.end():match.end() + 24])
            if stated:
                year = int(re.search(r"(?:19|20)\d\d", stated.group(0)).group(0))
                historic = values_of(key, entry, year=year)
                if territory not in historic:
                    continue
                actual, when = historic[territory], f" nel {year}"
            elif states_a_value(text, match):
                actual, when = values[territory], ""
            else:
                continue
            floor = 0.06 if "," in raw else 0.5
            if abs(number_of(raw) - actual) > max(floor, abs(actual) * 0.011):
                found.append(_finding("cifra-falsa", BLOCKS,
                                      f"{territory} detto {raw}{when}, dato "
                                      f"{round(actual, 2)}", field))
        for match in compiled["threshold"].finditer(text):
            verb, raw, listed = match.group(1), match.group(2), match.group(3)
            threshold, above = number_of(raw), bool(re.match(ABOVE, verb, re.I))
            for territory in re.findall(compiled["alternation"], listed):
                if territory not in values:
                    continue
                actual = values[territory]
                ok = (actual >= threshold - 0.06) if above else (actual <= threshold + 0.06)
                if not ok:
                    found.append(_finding("soglia-falsa", BLOCKS,
                                          f"{territory} {verb} {raw}, dato "
                                          f"{round(actual, 2)}", field))
    return found


def check_dynamics_cite_a_source(entry, key=None, **_):
    """La regola che toglie il freddo, e l'unica nuova che conta.

    Posizionale: la sezione `dinamica` porta almeno un identificatore del
    corpus. Se il corpus non ha niente per quel tema, la colpa non e'
    dell'articolo e il rilievo lo dice, perche' altrimenti chi scrive
    imparerebbe a inventare una fonte per far tacere un lint.
    """
    sections = entry.get("sections") or []
    dynamics = [section for section in sections if section.get("role") == "dinamica"]
    if not dynamics:
        return []

    view = view_of(key)
    meta = (view or {}).get("meta", {})
    theme = meta.get("theme")
    # Il nome serve: un'affermazione che dichiara delle `chiavi` arriva per tema
    # solo se una chiave compare nel nome dell'indicatore. Senza passarlo, il
    # lint vedeva un corpus vuoto e diceva all'articolo di non spiegare mentre
    # una citazione buona c'era.
    available = {claim["id"] for claim in context_module.for_indicator(
        key, theme, limit=50, indicator_name=meta.get("name"))}
    cited = set(indicator_texts.cited_claims(entry))
    esistenti = {claim["id"] for claim in context_module.claims()}

    # Prima i due modi in cui una citazione e' sbagliata, e sono diversi.
    inventate = sorted(cited - esistenti)
    if inventate:
        return [_finding("fonte-inesistente", BLOCKS,
                         f"identificatori non nel corpus: {inventate}",
                         "corpus")]
    # Un'affermazione vera, verificabile, e che non riguarda questo indicatore.
    # E' il caso peggiore da leggere, perche' regge a ogni controllo tranne
    # quello che conta: nella prima run la citazione Eurostat sulla
    # disoccupazione di lunga durata e' finita a spiegare il tasso di
    # attivita'. Bloccante come una fonte inventata: su una pagina pubblica una
    # spiegazione attribuita a chi non l'ha data e' un'attribuzione falsa,
    # anche se la frase esiste davvero da un'altra parte.
    fuori_tema = sorted(cited - available)
    if fuori_tema:
        return [_finding("fonte-non-pertinente", BLOCKS,
                         f"nel corpus ma non per questo indicatore: {fuori_tema}",
                         "corpus")]

    if not available:
        return [_finding("dinamica-senza-fonte", FLAGS,
                         f"il corpus non ha niente per {meta.get('name') or key!r}: "
                         "l'articolo deve dire che non spiega, non spiegare "
                         "lo stesso", "sections.dinamica")]
    if not cited:
        return [_finding("dinamica-senza-fonte", FLAGS,
                         f"nessun identificatore, ma il corpus ne offre "
                         f"{len(available)}", "sections.dinamica")]
    return []


def check_positive_requirements(entry, key=None, **_):
    """I tre requisiti positivi: scala umana, dinamica citata, limite dichiarato.

    Requisiti, non divieti. Trenta divieti hanno prodotto articoli che
    rispettavano ogni divieto e non somigliavano a niente, ed e' il README di
    `content/esempi/` a dirlo per primo.
    """
    found = []
    roles = {section.get("role") for section in entry.get("sections") or []}
    if "limiti" not in roles:
        found.append(_finding("manca-il-limite", FLAGS,
                              "nessuna sezione dice che cosa il numero non puo' dire"))
    words = sum(len((text or "").split()) for _, text in prose_of(entry))
    if words < MIN_WORDS:
        found.append(_finding("troppo-corto", FLAGS,
                              f"{words} parole, sotto il minimo di {MIN_WORDS}"))
    return found


def check_named_institutions_are_visible(entry, key=None, **_):
    """Un'istituzione nominata nella prosa deve avere una fonte in pagina.

    E' la riparazione del difetto peggiore trovato finora, e nessuna guardia
    esistente lo vedeva. `ter-176` scriveva "Eurostat scrive che quando
    l'economia riparte..." mentre il blocco fonti della pagina portava solo
    Istat: l'identificatore stava nel campo `corpus`, che la pagina non rende.
    Un lettore vedeva un'attribuzione a un'istituzione **senza un modo per
    controllarla**. Su un sito di dati pubblici e' la cosa che consuma piu'
    fiducia di un errore, perche' un errore si corregge e questa somiglia a una
    fonte inventata.

    Il controllo e' lessicale, e qui va bene, al contrario di quello sulla
    causalita': il vocabolario e' **chiuso e nostro**, sono i nomi delle
    istituzioni in `data/corpus/sources.json`. Non si cerca un concetto, si
    cerca un nome proprio che qualcuno ha scritto in un registro.

    `app.indicator_texts.visible_sources` deriva ormai le fonti dagli
    identificatori citati, quindi in regime questo rilievo scatta solo quando la
    prosa nomina un'istituzione **senza** citarne l'affermazione: cioe' quando
    l'attribuzione non ha proprio un appiglio.
    """
    prose = " ".join(text for _, text in prose_of(entry))
    if not prose.strip():
        return []
    visibili = " ".join(
        f"{item.get('testo', '')} {item.get('url', '')}"
        for item in indicator_texts.visible_sources(entry) if isinstance(item, dict))
    # La fonte del dato non conta: la pagina la mostra sempre nella riga
    # "Fonte", e nominarla e' definitorio, non un'attribuzione. Senza questa
    # esclusione la regola bocciava sei articoli per frasi come "Istat lo
    # calcola come media annua", che non attribuiscono niente a nessuno.
    meta = ((view_of(key) or {}).get("meta") or {})
    propria = " ".join(str(meta.get(field) or "")
                       for field in ("institution", "source_label", "source"))
    found = []
    for name in _institution_names():
        if not re.search(rf"\b{re.escape(name)}\b", prose):
            continue
        if name in visibili or name in propria:
            continue
        found.append(_finding(
            "istituzione-senza-fonte", BLOCKS,
            f"la prosa nomina {name}, che non e' la fonte del dato, e la pagina "
            "non mostra una sua fonte: cita l'affermazione del corpus, o non "
            "attribuire", "fonti"))
    return found


# Nomi che nel registro identificano un'istituzione ma in italiano sono anche
# una frase comune. Su una regola bloccante il falso positivo costa piu' del
# falso negativo, quindi si escludono per nome invece che con un'euristica.
GENERIC_INSTITUTIONS = frozenset(("Politiche di coesione", "Commissione europea"))


@functools.lru_cache(maxsize=1)
def _institution_names():
    """I nomi delle istituzioni del registro, dal piu' lungo al piu' corto.

    Il registro scrive `institution` come "istituzione, pubblicazione"
    ("Istat, Rapporto BES"), e cio' che la prosa nomina e' la prima parte. Una
    prima versione cercava la stringa intera e trovava cinque nomi su diciotto,
    perdendo proprio Istat ed Eurostat, cioe' le due che compaiono davvero.

    Tre filtri, tutti per non bloccare a torto: almeno cinque caratteri
    (cercare "UE" prenderebbe mezza lingua), al massimo tre parole, e nessun
    nome che sia anche una frase comune.
    """
    names = set()
    for item in context_module.sources().values():
        name = (item.get("institution") or "").split(",")[0].strip()
        if len(name) < 5 or name in GENERIC_INSTITUTIONS:
            continue
        if len(name.split()) > 3 or not name[:1].isupper():
            continue
        if not all(part.replace("'", "").isalpha() for part in name.split()):
            continue
        names.add(name)
    return tuple(sorted(names, key=len, reverse=True))


def _paragraphs(text):
    return [block for block in re.split(r"\n\s*\n", text or "")
            if len(re.findall(r"[^\W\d_]+", block, re.UNICODE)) >= PARAGRAPH_MIN_WORDS]


def check_unsupported_paragraphs(entry, key=None, **_):
    """Paragrafi che affermano senza portare niente: ne' una cifra ne' una fonte.

    E' la misura che separa davvero il nostro corpus dal giornalismo vero, e
    non e' quella che mi aspettavo. L'ipotesi era la **densita' numerica**, che
    Thäsler-Kordonouri et al. (Journalism 26(9) 2025, n=3135) misurano come
    mediatore della comprensibilita'. Provata su questo corpus, non regge: i
    nostri articoli hanno mediana 2,91 numeri ogni cento parole contro i 3,54
    degli esempi, cioe' sono meno densi, non piu'.

    Regge invece la **quota di paragrafi scoperti**: esempi 0,25 di mediana e
    0,33 di massimo, pubblicati 0,67 di mediana, con 313 articoli su 376 sopra
    il massimo degli esempi. Le due distribuzioni quasi non si toccano.

    Che cosa dice il numero: i nostri articoli separano le cifre dal
    significato. Un paragrafo ammucchia i dati e due commentano a vuoto, mentre
    il giornalismo vero intreccia. Un paragrafo senza una cifra e senza un
    identificatore di corpus non e' sobrio, e' vuoto: e' `dinamica-senza-fonte`
    vista da un'altra porta, la stessa che aveva gia' segnato 52 articoli su 52.

    La soglia e' il q90 degli esempi, da `officina/calibrazione_prosa.json`,
    rigenerabile con `bin/py -m scripts.calibra_prosa`. Non si scrive a mano.
    """
    threshold = calibrazione_prosa().get("soglia_paragrafi_scoperti")
    if not threshold:
        return []
    blocks = []
    for _, text in prose_of(entry):
        blocks.extend(_paragraphs(text))
    if len(blocks) < PARAGRAPH_MIN_COUNT:
        return []
    # "Senza una cifra", e basta. Una prima versione lasciava passare anche i
    # paragrafi con un identificatore di corpus fra parentesi quadre: cercato
    # sui 376 articoli, quel caso ricorre **zero volte**, perche' gli
    # identificatori stanno nel campo `corpus` e non nel testo (ed e' la ragione
    # per cui `check_dynamics_cite_a_source` e' posizionale invece che
    # lessicale). Una scappatoia che non scatta mai si legge come una garanzia
    # e non lo e', e soprattutto rendeva la regola diversa dalla misura su cui
    # e' calibrata: negli esempi il conteggio e' "paragrafi senza cifre".
    bare = [block for block in blocks if not re.search(r"\d", block)]
    share = len(bare) / len(blocks)
    if share <= threshold:
        return []
    return [_finding("paragrafi-scoperti", FLAGS,
                     f"{len(bare)} paragrafi su {len(blocks)} ({share:.0%}) senza "
                     f"nemmeno una cifra, oltre il {threshold:.0%} degli esempi")]


def _shingles(text, size=5):
    words = re.findall(r"\w+", (text or "").lower())
    return {tuple(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}


def check_distance_from_siblings(entry, key=None, texts=None, **_):
    """Due articoli che si leggono come lo stesso stampo.

    Assorbe `scripts/seriality_queue.py`, ed e' anche la difesa contro cio' che
    Google chiama abuso di contenuti in scala: non il volume, la mancanza di
    differenza vera fra pagine sorelle.
    """
    if not texts:
        return []
    mine = _shingles(" ".join(text for _, text in prose_of(entry)))
    if len(mine) < 20:
        return []
    found = []
    for other_key, other in texts.items():
        if other_key == key:
            continue
        theirs = _shingles(" ".join(text for _, text in prose_of(other)))
        if len(theirs) < 20:
            continue
        overlap = len(mine & theirs) / min(len(mine), len(theirs))
        if overlap >= TWIN_SIMILARITY:
            found.append(_finding("gemello", BLOCKS,
                                  f"{overlap:.0%} in comune con {other_key}"))
    return found


RULES = (
    check_banned_characters,
    check_lead,
    check_figures,
    check_dynamics_cite_a_source,
    check_positive_requirements,
    check_named_institutions_are_visible,
    check_unsupported_paragraphs,
    check_distance_from_siblings,
)


# --------------------------------------------------------------------------
# esecuzione
# --------------------------------------------------------------------------

def lint_entry(key, entry, texts=None, compiled=None):
    texts = texts if texts is not None else {}
    found = []
    for rule in RULES:
        found.extend(rule(entry, key=key, texts=texts, compiled=compiled))
    return found


def resolve_codes(codes, texts):
    """(chiavi selezionate, codici che non esistono).

    Le chiavi in `content/indicators/` sono `176` per gli indicatori interni e
    `famiglia:ID` per gli esterni, mentre chi scrive e chi lancia dice
    `ter-176`. Le tre forme si risolvono qui, in un posto solo.

    E soprattutto: un codice che non risolve **si nomina**. Prima
    `officina.lint ter-176` selezionava zero articoli e stampava "articoli con
    rilievi: 0", che si legge come promosso. Nella prima run il pubblicatore ha
    eseguito proprio quella forma e ha letto un verde che nessuno aveva
    guadagnato. Un cancello che passa quando non capisce l'argomento non e' un
    cancello.
    """
    selected, missing = set(), []
    for code in codes:
        candidates = {code, code.replace("-", ":", 1)}
        family, _, tail = code.partition("-")
        if tail and family.isalpha():
            candidates.add(tail)
        hit = candidates & set(texts)
        if hit:
            selected |= hit
        else:
            missing.append(code)
    return selected, missing


def lint_all(only=None):
    """{chiave: rilievi}. Solo le chiavi con almeno un rilievo."""
    texts = indicator_store.load_all()
    alternation = territory_alternation(texts)
    compiled = patterns(alternation)
    compiled["alternation"] = alternation

    targets = texts if only is None else {
        key: entry for key, entry in texts.items() if key in only}
    report = {}
    for key, entry in targets.items():
        found = lint_entry(key, entry, texts=texts, compiled=compiled)
        if found:
            report[key] = found
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codes", nargs="*", help="es. ter-105; vuoto = tutti")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--severity", choices=(BLOCKS, FLAGS), default=None)
    args = parser.parse_args(argv)

    only = None
    if args.codes:
        only, missing = resolve_codes(args.codes, indicator_store.load_all())
        if missing:
            print(f"nessun articolo per: {', '.join(missing)}", file=sys.stderr)
            return 2
    report = lint_all(only)

    if args.severity:
        report = {key: [f for f in found if f["severity"] == args.severity]
                  for key, found in report.items()}
        report = {key: found for key, found in report.items() if found}

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        counts = Counter(f["rule"] for found in report.values() for f in found)
        for key in sorted(report):
            print(key)
            for finding in report[key]:
                where = f" [{finding['field']}]" if finding["field"] else ""
                print(f"  {finding['severity']:8} {finding['rule']:26}"
                      f"{where} {finding['detail']}")
        print(f"\narticoli con rilievi: {len(report)}")
        for rule, count in counts.most_common():
            print(f"  {rule:26} {count}")

    blocking = sum(1 for found in report.values()
                   for finding in found if finding["severity"] == BLOCKS)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
