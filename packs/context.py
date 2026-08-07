"""Il contesto citabile: la licenza di dire perche' i numeri si muovono.

Questo modulo esiste per il difetto che ha fatto ripensare tutta la pipeline.
Gli articoli sono corretti e **freddi**: giusti, e senza una ragione per cui un
cittadino dovrebbe leggerli.

La causa e' architetturale, non stilistica.
`.claude/skills/indicator-review/SKILL.md` vieta l'attribuzione causale, e ha
ragione a vietarla: da una serie non si deduce una causa, e un modello che la
inventa produce disinformazione. Ma allora all'articolo resta solo la
**geometria** della serie, chi sale, chi scende, quanto e' largo il divario.
Geometria descritta bene resta geometria, e infatti cinque lead su sei fra i
riscritti fanno la stessa mossa, negare la geografia attesa: e' l'unico gancio
disponibile quando l'unica cosa dicibile e' la forma della distribuzione.

**La causalita' non si inventa, si cita.** Se un articolo puo' dire che cosa
sostiene la Banca d'Italia sul recupero dell'occupazione femminile nel
Mezzogiorno, quella e' una dinamica vera, verificabile, attribuita. Il divieto
smette di essere un bavaglio e diventa un binario.

Il corpus e' un archivio di **affermazioni verbatim** di istituzioni, ognuna
con il proprio identificatore, il proprio URL e la data in cui e' stata letta.
Tre cose che questo modulo non fa, e sono tre scelte:

- **non riassume**: quello che entra e' testo copiato, non parafrasato, perche'
  una parafrasi salvata come fonte e' gia' un'invenzione a meta';
- **non va in rete**: il corpus si popola con `scripts/fetch_corpus.py`, che
  registra URL e data. Al momento di scrivere non c'e' nessuna chiamata di rete,
  quindi due esecuzioni vedono lo stesso contesto;
- **non deduce il tema**: un'affermazione dichiara i temi a cui si applica, e se
  nessuno gliel'ha assegnato non compare da nessuna parte.

La regola che ne discende, e che il lint fa rispettare, e' **posizionale**: ogni
sezione che racconta una dinamica porta almeno un identificatore di corpus. Non
lessicale. Ho provato la variante lessicale sui 375 articoli e non regge: i
connettivi ci sono (`perche'` 114, `dipende` 96, `riflette` 44 occorrenze) ma
quasi tutti in contesto definitorio, "dipende dal denominatore", mentre la
causalita' vera viaggia senza connettivi, "si e' chiusa dal basso, pero', non
dall'alto". Un lint che cerca parole segnala le definizioni, non vede i
meccanismi, e insegna al modello a scrivere ancora piu' implicito.
"""
from __future__ import annotations

import functools
import glob
import json
import os

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "corpus")
SOURCES_PATH = os.path.join(ROOT, "sources.json")
CLAIMS_DIR = os.path.join(ROOT, "claims")

# Quante affermazioni proporre per un articolo. Il registro delle fonti lo dice
# gia' per gli URL e vale identico qui: "tre fonti in un pezzo da 600 parole
# sono troppe". Il pacchetto ne offre poche e buone, non una rassegna stampa.
PER_PACK = 4


@functools.lru_cache(maxsize=1)
def sources():
    """{id: istituzione}, il registro di docs/SECONDARY_SOURCES.md come dati."""
    try:
        with open(SOURCES_PATH, encoding="utf-8") as handle:
            return {item["id"]: item for item in json.load(handle)}
    except (OSError, ValueError):
        return {}


@functools.lru_cache(maxsize=1)
def claims():
    """Tutte le affermazioni del corpus, una per file, ordinate per id.

    Un file per affermazione e non un CSV unico: e' la stessa regola che il
    resto della catena applica ai propri registri, e qui in piu' evita che un
    punto e virgola dentro una citazione spacchi una riga, che a questo progetto
    e' gia' successo su `external_indicator_manifest.csv`.
    """
    found = []
    for path in sorted(glob.glob(os.path.join(CLAIMS_DIR, "*.json"))):
        try:
            with open(path, encoding="utf-8") as handle:
                found.append(json.load(handle))
        except (OSError, ValueError):
            continue
    return found


def reload_corpus():
    sources.cache_clear()
    claims.cache_clear()
    return claims()


def problems(claim):
    """Che cosa manca a un'affermazione per essere citabile. Lista vuota: e' a posto.

    Serve al cancello prima che al lettore: un'affermazione senza URL o senza
    data di lettura e' indistinguibile da una inventata, e la cosa peggiore che
    questo corpus potrebbe fare e' rendere comoda un'invenzione.
    """
    missing = [field for field in ("id", "source_id", "url", "fetched_at", "quote")
               if not (claim.get(field) or "").strip()]
    found = [f"manca {field}" for field in missing]
    if claim.get("source_id") and claim["source_id"] not in sources():
        found.append(f"fonte sconosciuta: {claim['source_id']}")
    if not claim.get("themes"):
        found.append("nessun tema: non comparira' in nessun pacchetto")
    quote = (claim.get("quote") or "").strip()
    if quote and len(quote) < 40:
        found.append("citazione troppo corta per reggere un'attribuzione")
    return found


# I caratteri che le fonti usano e che `content/STYLE.md` vieta nella prosa.
# La citazione si conserva com'e', perche' e' verbatim e la verifica la cerca
# come stringa; ma chi scrive ha bisogno anche di una versione che, copiata,
# non faccia fallire il cancello tipografico. Senza questa riga la prima
# citazione del corpus, che ha un apostrofo curvo, avrebbe bloccato l'articolo
# che la usava, e nessuno avrebbe capito perche'.
FOR_PROSE = {"’": "'", "‘": "'", "“": '"', "”": '"',
             "—": ",", "–": "-", "…": "...", ";": ","}

# I quattro che `content/STYLE.md` vieta davvero, ed e' la meta' che conta: gli
# altri quattro di `FOR_PROSE` sono varianti di glifo delle stesse virgolette e
# dello stesso apostrofo, e non cambiano una parola. Questi quattro invece
# cambiano la frase: un `;` che diventa `,` e una lineata che diventa una
# virgola spostano dove finisce un'idea e dove ne comincia un'altra.
#
# Unica copia. `officina/lint.BANNED` e' un alias di questa riga, e un test
# tiene allineata anche quella di `scripts/apply_curation.py`, che non puo'
# importare da qui.
BANNED = ("—", "–", ";", "…")

# La sola meta' di `FOR_PROSE` che si puo' applicare a una citazione senza
# cambiare cio' che l'istituzione ha detto.
GLYPHS = {wrong: right for wrong, right in FOR_PROSE.items() if wrong not in BANNED}


def for_prose(text):
    """La stessa citazione, con i caratteri che la prosa del progetto ammette.

    **Serve a chi scrive**, per costruirci sopra senza far fallire il cancello
    tipografico, e non a mostrarla. Vedi `for_quote`: `app.indicator_texts` la
    usava per rendere la citazione fra caporali, cioe' presentava come parole
    dell'istituzione una stringa che questa funzione aveva cambiato.
    """
    for wrong, right in FOR_PROSE.items():
        text = text.replace(wrong, right)
    return text


def for_quote(text):
    """La citazione come si puo' **mostrare**: solo i glifi, nessuna parola.

    Virgolette curve e apostrofi tipografici diventano dritti, che e' una
    variante di disegno dello stesso segno. I quattro di `BANNED` restano dove
    sono: sostituirli cambierebbe la punteggiatura di una frase altrui, e una
    frase altrui cambiata fra caporali e' attribuita male.
    """
    for wrong, right in GLYPHS.items():
        text = text.replace(wrong, right)
    return text


def quotable(text):
    """Se questa citazione si puo' mostrare verbatim senza rompere le pagine.

    Le pagine non portano i quattro caratteri di `BANNED`, ed e' un invariante
    con dei test suoi. Quando una citazione ne contiene uno restano due strade
    oneste, e questa funzione serve a prendere la seconda: cambiarla e
    presentarla lo stesso come sua, oppure non mostrarla e lasciare
    l'istituzione con il proprio link. La terza, mostrare parole che
    l'istituzione non ha scritto, non e' una strada.
    """
    return not any(char in text for char in BANNED)


def for_theme(theme, limit=PER_PACK):
    """Le affermazioni valide per un tema, dalla piu' recente."""
    if not theme:
        return []
    matching = [claim for claim in claims()
                if theme in (claim.get("themes") or []) and not problems(claim)]
    matching.sort(key=lambda claim: (claim.get("fetched_at", ""), claim["id"]),
                  reverse=True)
    return matching[:limit]


def matches_keys(claim, indicator_name):
    """Se un'affermazione dichiara delle chiavi, almeno una deve stare nel nome.

    E' il secondo vincolo oltre al tema, e nasce da un difetto letto in pagina.
    Nella prima run del workflow la stessa citazione Eurostat sulla
    disoccupazione di lunga durata e' finita **sia** sul tasso di
    disoccupazione **sia** sul tasso di attivita', perche' condividono il tema
    "Lavoro e conciliazione". Sul secondo era forzata: un'affermazione sulla
    sensibilita' ciclica della disoccupazione non spiega il tasso di attivita'.

    Il tema e' una cartella, non una pertinenza. Le chiavi sono facoltative:
    un'affermazione che vale per tutto un tema non le dichiara, e continua a
    valere per tutto il tema.
    """
    keys = claim.get("chiavi") or []
    if not keys:
        return True
    name = (indicator_name or "").lower()
    return any(str(key).lower() in name for key in keys)


def for_indicator(indicator_id, theme, limit=PER_PACK, indicator_name=None):
    """Le affermazioni per questo indicatore, le sue prima di quelle del tema.

    Un'affermazione che nomina l'indicatore vale piu' di una che parla del tema:
    e' la differenza fra "la Banca d'Italia dice questo di questa serie" e "la
    Banca d'Italia dice questo del lavoro". E chi arriva per tema deve passare
    anche dalle chiavi, se ne dichiara: vedi `matches_keys`.
    """
    named, general = [], []
    for claim in claims():
        if problems(claim):
            continue
        if indicator_id and indicator_id in (claim.get("indicators") or []):
            named.append(claim)
        elif theme and theme in (claim.get("themes") or []) \
                and matches_keys(claim, indicator_name):
            general.append(claim)
    for bucket in (named, general):
        bucket.sort(key=lambda claim: (claim.get("fetched_at", ""), claim["id"]),
                    reverse=True)
    return (named + general)[:limit]


def as_context(indicator_id, theme, human_scale=None, indicator_name=None):
    """Il blocco `context` del pacchetto.

    `citabili` sono gli identificatori che una sezione di dinamica puo' portare.
    Se e' vuoto, l'articolo non ha il diritto di spiegare perche' la serie si
    muove, e deve dirlo invece di girarci intorno: e' meglio di una causa
    dedotta dai dati, che e' il modo in cui un articolo diventa falso restando
    aritmeticamente corretto.
    """
    picked = for_indicator(indicator_id, theme, indicator_name=indicator_name)
    return {
        "scala_umana": human_scale,
        "citabili": [claim["id"] for claim in picked],
        "affermazioni": [{
            "id": claim["id"],
            "istituzione": sources().get(claim["source_id"], {}).get("institution",
                                                                     claim["source_id"]),
            "titolo": claim.get("title"),
            "url": claim["url"],
            "letta_il": claim["fetched_at"],
            "citazione": claim["quote"],
            "citazione_per_prosa": for_prose(claim["quote"]),
            "lingua": claim.get("language", "it"),
            "riguarda": claim.get("about"),
        } for claim in picked],
        "senza_contesto": not picked,
    }
