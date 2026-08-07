"""The editorial layer of an indicator page: one article, four ordered roles.

The page used to concatenate eight independent prose slots, each written against
its own local brief and none written to lead into the next. That is why the text
read as disconnected even when every sentence was individually correct. It also
meant the writer agent only owned three of those slots and the rest stayed
procedural.

Now there is one article. Its structure is fixed so 621 pages stay uniform, its
surface is not: the agent writes the heading as well as the body, because
identical H2s across the whole catalogue read like a stamp (content/STYLE.md).

    definizione   what it measures, the perimeter, what a value means
    quadro        how it is distributed right now, and what that says
    dinamica      how it moved, over the series and in the latest year
    limiti        what the number does not capture

Roles the JSON does not carry are composed from the data at render time by the
template, never frozen into the file. Two reasons: composed text cannot silently
age behind a data refresh, and the vintage guard then applies only to sentences a
human or an agent actually wrote.

The prose lives in ``content/indicators/``, one file per article (never in the
.py, per the editorial pipeline), and is loaded once for the life of the
process like the other on-disk artifacts. Editing it requires a gunicorn
restart.

The layout and the reason for it live in ``scripts/indicator_store.py``, which
owns the files. The short version: writer and reviewer are the only two stages
that may touch prose, they run daily, and one JSON object holding 365 articles
made every pair of concurrent runs a merge conflict on a file no agent can
resolve by reading it.
"""

import functools

from app import sources
from packs import context
from scripts import indicator_store

# Ordered. The default heading is a fallback for pages the agent has not reached
# yet; an authored `h` always wins.
ROLES = (
    ("definizione", "Che cosa misura, in concreto"),
    ("quadro", "Come si distribuisce oggi"),
    ("dinamica", "Come è cambiato nel tempo"),
    ("limiti", "Che cosa questo dato non dice"),
)
ROLE_ORDER = [role for role, _ in ROLES]
DEFAULT_HEADINGS = dict(ROLES)

# I tre ruoli che nessuna dichiarazione `roles_covered` puo' togliere dalla
# pagina: il blocco "Come leggere il dato" copre la sola `definizione`, quindi e'
# la sola omettibile. Rispecchiato in `scripts/pending_notes.SUBSTANTIVE_ROLES` e
# in `scripts/practice_timeline`, che decidono se una pratica e' completa.
SUBSTANTIVE_ROLES = frozenset(("quadro", "dinamica", "limiti"))

# The level an entry describes when it does not say. Every article written so
# far is regional, and every family except BES has regions as its only level.
DEFAULT_LEVEL = "regione"

# Namespaces to try when a caller passes a bare id (the quality-of-life pages
# do). Read from the source registry so a new family is looked up the day it is
# registered, instead of being invisible to the editorial layer until someone
# remembers this list.
_NAMESPACES = tuple(
    meta["internal_prefix"] for meta in sources.SOURCES.values() if meta["internal_prefix"]
)


@functools.lru_cache(maxsize=1)
def _load():
    # `strict=False`: un articolo illeggibile costa quell'articolo, che ricade
    # sullo scheletro composto come una pagina non ancora scritta. In `strict`
    # solleverebbe, e il ripiego qui sotto svuoterebbe **tutto** il catalogo
    # per colpa di un file solo, senza che si veda un errore da nessuna parte.
    # A trovare il file rotto ci pensa la suite, che legge in `strict`.
    try:
        return indicator_store.load_all(strict=False)
    except (OSError, ValueError, indicator_store.StoreError):
        return {}


def get_text(indicator_id):
    """The stored entry for an indicator id, or None.

    Tries the bare id first (territorial ids and any already-namespaced key),
    then the namespaced variants, because the quality-of-life callers pass the
    bare id.
    """
    data = _load()
    if not data:
        return None
    iid = str(indicator_id)
    for key in (iid, *(f"{prefix}{iid}" for prefix in _NAMESPACES)):
        entry = data.get(key)
        if entry:
            return entry
    return None


def emitted_roles(entry):
    """I ruoli che la pagina rende per questa entry: `roles_covered` normalizzato.

    Una dichiarazione e' un **filtro sui quattro ruoli**, non un vocabolario
    nuovo. Due normalizzazioni, e nessuna delle due e' cosmetica:

    - un ruolo sconosciuto si ignora. Un refuso (`dinamicha`) lasciato passare
      finiva in cio' che la pratica pretende, e l'articolo restava incompleto per
      sempre mentre la lista di consegna diceva che non manca niente: il dossier
      lo rilanciava a ogni tick senza che nessuna run potesse chiudere il buco.
    - i tre sostanziali ci sono comunque. Solo la `definizione` e' assorbibile,
      perche' e' l'unica che il blocco "Come leggere il dato" copre, e senza
      l'unione una dichiarazione parziale toglieva `dinamica` e `limiti` dalla
      pagina pubblica invece di comporli dallo scheletro.

    E' l'unica fonte della regola: renderer, code e impronta della prosa devono
    rispondere la stessa cosa, o lo stesso articolo risulta completo per una e
    incompleto per l'altra. `scripts/practice_timeline.py`,
    `scripts/pending_notes.py` e `scripts/verification_queue.py` la rispecchiano
    (sono stdlib puri e non importano `app`), e un test le tiene allineate.
    """
    declared = entry.get("roles_covered") if isinstance(entry, dict) else None
    # Un'entry che scrive le proprie sezioni **dichiara con quelle**: elencare i
    # ruoli due volte, una in `sections` e una in `roles_covered`, e' un modo
    # per farli divergere. Senza questa riga la macchina nuova pubblicava
    # articoli senza definizione e la pagina la ricomponeva lo stesso in
    # apertura, cioe' proprio il difetto che questa ricostruzione esiste per
    # togliere: cinquantadue articoli su cinquantadue aprivano sulla
    # definizione, e il cinquantatreesimo pure.
    #
    # **Solo un articolo completo dichiara.** Un articolo a meta' non sta
    # scegliendo una forma, e' solo incompleto: trecentoventidue delle entry in
    # `content/indicators/` hanno scritto `quadro` e `limiti` e nient'altro, e
    # con la condizione debole ("almeno un ruolo sostanziale") sono passate
    # tutte a `quadro, limiti, dinamica` con la definizione assorbita. Cioe' un
    # cambio di pagina su 322 articoli che nessuno aveva chiesto, e che nessun
    # test vedeva. La condizione e' quindi **tutti e tre i sostanziali**.
    if declared is None and isinstance(entry, dict) and entry.get("sections"):
        written = [section.get("role") for section in entry["sections"]
                   if isinstance(section, dict) and (section.get("body") or "").strip()]
        if SUBSTANTIVE_ROLES.issubset(set(written)):
            declared = written
    # Campo **assente** e lista **vuota** non sono la stessa cosa: assente vuol
    # dire "non dichiaro niente", cioe' i quattro ruoli di sempre, mentre
    # `roles_covered: []` e' una dichiarazione che non nomina la definizione, e
    # quindi la assorbe esattamente come farebbe `["quadro"]`. Un test di verita'
    # le confondeva, e la stessa entry rendeva quattro sezioni qui e tre nella
    # forma equivalente.
    if not isinstance(declared, (list, tuple)):
        return list(ROLE_ORDER)
    keep = {role for role in declared if role in DEFAULT_HEADINGS} | SUBSTANTIVE_ROLES
    # **L'ordine dichiarato vince, e non e' un dettaglio.** Il pacchetto dice a
    # chi scrive che la sequenza nasce dall'angolo piu' forte, e la prima prova
    # ha prodotto `quadro, limiti, dinamica`: la pagina lo riordinava in
    # `definizione, quadro, dinamica, limiti`, cioe' buttava via l'unica cosa
    # che rompe lo stampo. Una promessa fatta a chi scrive e disfatta al render
    # e' peggio di una promessa non fatta.
    #
    # I ruoli sostanziali che la dichiarazione non nomina si compongono, e
    # vanno in coda nell'ordine canonico: non hanno un posto scelto da nessuno.
    ordered = [role for role in declared if role in keep]
    return ordered + [role for role in ROLE_ORDER
                      if role in keep and role not in ordered]


def cited_claims(entry):
    """Gli identificatori di corpus che questa entry usa, per sezione e in coda.

    Le sezioni dichiarano `claims`, ed e' li' che l'attribuzione ha un posto:
    dire *quale paragrafo* si appoggia a chi e' l'unica forma che un controllo
    posizionale puo' verificare. Il campo `corpus` a livello di entry resta
    letto per le entry scritte prima, che lo usavano da sole.
    """
    if not isinstance(entry, dict):
        return []
    found = list(entry.get("corpus") or [])
    for section in entry.get("sections") or []:
        if isinstance(section, dict):
            found.extend(section.get("claims") or [])
    seen, ordered = set(), []
    for name in found:
        if isinstance(name, str) and name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def visible_sources(entry):
    """Le fonti che la pagina mostra: quelle autorate piu' quelle del corpus.

    **Derivate, non trascritte a mano, ed e' una riparazione.** L'articolo di
    `ter-176` scriveva "Eurostat scrive che..." mentre il blocco fonti visibile
    portava solo Istat: l'identificatore stava in `corpus`, che la pagina non
    rende. Un lettore vedeva un'attribuzione a un'istituzione senza un modo per
    controllarla, che e' il difetto peggiore possibile su un sito di dati
    pubblici, e nessuna guardia lo prendeva perche' le due liste non si
    parlavano.

    Ora si parlano qui, in un posto solo: cio' che la prosa attribuisce non puo'
    restare invisibile, perche' non c'e' un passo umano che lo trascriva.
    """
    authored = [item for item in (entry.get("fonti") or []) if isinstance(item, dict)]
    known = {item.get("url") for item in authored}
    registry = context.sources()
    derived = []
    for claim in context.claims():
        if claim.get("id") not in cited_claims(entry) or claim.get("url") in known:
            continue
        institution = (registry.get(claim.get("source_id")) or {}).get(
            "institution") or claim.get("source_id") or ""
        quote = context.for_prose((claim.get("quote") or "").strip())
        derived.append({"testo": f"{institution}. «{quote}»".strip(),
                        "url": claim.get("url")})
        known.add(claim.get("url"))
    return authored + derived


def build_article(indicator_id, level_key=DEFAULT_LEVEL):
    """The article sections in order, each flagged authored or composed.

    `body` is None for a composed section: the template renders that role from
    the data instead. Callers must not treat None as an empty section.

    Prose is written against one territorial level and cites that level's
    figures. The 31 BES articles that exist for two-level indicators were all
    written against the regions, so on ``?livello=provincia`` they would name
    Umbria and Piemonte under a cockpit of provinces. An entry therefore
    declares the level it describes and is used only there; every other level
    falls back to the composed skeleton, which reads the level it is given.

    **Sezioni variabili (opt-in).** Di default l'articolo ha i quattro H2 in
    ordine fisso, la `definizione` in apertura. Un'entry puo' pero' dichiarare
    ``roles_covered``: la lista dei ruoli che scrive come H2. Se la `definizione`
    non e' fra quelli, non apre piu' l'articolo: la sua meccanica va nel blocco
    "Come leggere il dato" (``indicator_page.html``), che compone lo stesso
    ``explain`` dai metadati. Il campo vive a livello di entry e **non entra nel
    ``prose_fingerprint``** (che legge solo lead + ``sections[].{role,h,body}``),
    quindi le entry senza il campo hanno impronta identica a prima: additivo, i
    trecento articoli esistenti non cambiano. ``come_leggere`` nel risultato dice
    al template quando rendere il blocco al posto dell'H2 definizione.
    """
    entry = get_text(indicator_id) or {}
    if (entry.get("level") or DEFAULT_LEVEL) != (level_key or DEFAULT_LEVEL):
        entry = {}
    authored = {
        section["role"]: section
        for section in entry.get("sections") or []
        if section.get("role") in DEFAULT_HEADINGS and (section.get("body") or "").strip()
    }
    role_sequence = emitted_roles(entry)
    sections = []
    for role in role_sequence:
        written = authored.get(role)
        heading = (written.get("h") or "").strip() if written else ""
        sections.append({
            "role": role,
            "heading": heading or DEFAULT_HEADINGS[role],
            "body": written["body"].strip() if written else None,
            "authored": written is not None,
        })
    return {
        "lead": (entry.get("lead") or "").strip() or None,
        "sections": sections,
        # La definizione e' assorbita dal blocco "Come leggere" quando non e' fra
        # gli H2 emessi. Per un'entry senza `roles_covered` la definizione e'
        # sempre presente, quindi `come_leggere` e' False e niente cambia.
        "come_leggere": "definizione" not in role_sequence,
        # Titolo H1 e titolo SERP autorati, opzionali. Quando assenti la pagina usa
        # il derivato di oggi (H1 = nome amministrativo, title = boilerplate "per
        # regione"). Un titolo in lingua comune ("Dove si lavora di piu' nella
        # ricerca") e' un giudizio editoriale, non derivabile, quindi vive nel file
        # dell'articolo. Campi di entry, non entrano nel `prose_fingerprint`.
        "h1": (entry.get("h1") or "").strip() or None,
        "seo_title": (entry.get("seo_title") or "").strip() or None,
        "fonti": visible_sources(entry),
        "vintage": entry.get("vintage") if isinstance(entry.get("vintage"), int) else None,
        "authored_count": len(authored),
    }


def composed_lead(meta, level):
    """The opening line for an indicator nobody has written a lead for yet.

    It states what the page holds, never what the numbers are. The previous
    version opened with the best region, the worst region and the mean, which is
    exactly what the KPI row prints a few centimetres below it, so 260 pages read
    as a stat dump repeated twice. It is also the SERP description and the
    Dataset JSON-LD description, so it has to stand alone and be unique per
    indicator: the plain definition supplies both.
    """
    plain = (meta.get("explain") or {}).get("plain") or ""
    count = len(level["observations"])
    noun = level["singular"] if count == 1 else level["plural"]
    institution = meta.get("institution") or "Istat"
    span = (
        f"dal {level['year_min']} al {level['year_max']}"
        if level["year_min"] != level["year_max"]
        else f"nel {level['year_max']}"
    )
    views = "con mappa, classifica e serie storica" if level["has_map"] else "con classifica e serie storica"
    if level["year_min"] == level["year_max"]:
        views = "con mappa e classifica" if level["has_map"] else "con la classifica completa"
    second = f"Dati {institution} per {count} {noun}, {span}, {views}."
    return f"{plain} {second}".strip() if plain else second
