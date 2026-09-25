"""Il titolo e la descrizione che si leggono su Google, quando il pezzo non c'e'.

Perche' un modulo a se' e non altre funzioni in `indicator_notes.py`: quel file
possiede il vocabolario **derivato dal nome** dell'indicatore (abbreviazioni,
marcatori di variante, collisioni fra serie che si chiamano uguale). Qui invece
si deriva **dai dati**, servono `meta` e `level` insieme, e il modulo deve
girare senza Flask perche' i test lo esercitano su centinaia di casi.

Il problema che risolve, misurato. Il sito prende 394 clic su 12.561 impression
in 90 giorni, CTR 3,14%, mentre le posizioni che occupa ne varrebbero circa 505.
Le pagine si posizionano e non vengono cliccate, e il titolo e' il motivo: dice
il nome amministrativo della serie e nient'altro. Il caso limite e'
`bes-04BEC002P`, in posizione 4,4 con 655 impression e **un** clic, il cui
titolo e' "Retribuzione media annua dei lavoratori dipendenti" mentre una delle
due query registrate e' `"34.343" "milano" "retribuzione media annua"`: la cifra
che quella persona cerca e' in pagina e non e' nel titolo.

Non e' un problema di lunghezza. Su sessanta titoli campionati la media e' 54
caratteri e 54 stanno dentro la finestra: lo spazio c'e' gia', manca il motivo
per cliccare. Quindi il titolo derivato porta **l'intervallo**, che e' la
risposta alla domanda che la gente fa davvero ("pil pro capite regioni
italiane", "pil pro capite calabria"). Copre il 64% delle pagine
indicizzabili, 237 su 372, misurato sulla catena vera di `page_title` e non su
questa funzione da sola (24 settembre 2026, dati di quel giorno). Gli estremi
esistono su 281 (76%). Delle 91 che non li hanno, 90 sono `contextual`, dove il
catalogo non espone un massimo e un minimo perche' su quelle serie un estremo
non vuol dire niente, e quella guardia non si aggira dal titolo. L'ultima e'
`bes-06POL012P`, fuori apposta (`UNVERIFIED_EXTREMES`). Le altre 44 li hanno e
li perdono al budget, perche' il nome e' troppo lungo per stare accanto
all'intervallo: li' si rinuncia alle cifre invece che al nome, ed e' lo scambio
giusto. Una forma compatta ("9,4-0,4%") ne recuperava quattro al conto di
prima, che non valgono un secondo formato di numero in SERP.

Il 70% che stava scritto qui era il conto fatto prima che `_shorten_at_joint`
sostituisse il taglio a budget, cioe' prima della correzione raccontata in
`_fit`.
"""
from __future__ import annotations

import re

from app import indicator_notes, sources
from app.design import numfmt

# Il budget SERP, lo stesso che usa il percorso derivato di `indicator_notes`.
TITLE_MAX = indicator_notes._TITLE_MAX
DESCRIPTION_MAX = 155

# Sotto questa soglia la misura non e' piu' riconoscibile: meglio rinunciare
# alle cifre che consegnare un nome mutilato.
MIN_MEASURE = 20

# Le giunture dove un nome di indicatore si puo' tagliare: davanti a una
# preposizione cio' che resta e' ancora un sintagma compiuto ("Retribuzione media
# annua" da "Retribuzione media annua dei lavoratori dipendenti"). Fuori da qui
# il taglio cade in mezzo a un'espressione e consegna un troncone.
_JOINTS = frozenset((
    "di", "del", "dello", "della", "dei", "degli", "delle", "dell'",
    "da", "dal", "dallo", "dalla", "dai", "dagli", "dalle", "dall'",
    "a", "al", "allo", "alla", "ai", "agli", "alle", "all'", "ad",
    "in", "nel", "nello", "nella", "nei", "negli", "nelle", "nell'",
    "con", "col", "coi", "su", "sul", "sullo", "sulla", "sui", "sugli", "sulle", "sull'",
    "per", "presso", "secondo", "senza", "sotto", "sopra", "verso",
))

# Una testa che contiene uno di questi non regge da sola: `che` apre una
# relativa che vuole il suo predicato, `tra` e `fra` vogliono la coppia. Da li'
# escono "Famiglie che lamentano" e "Differenza tra tasso", che in SERP valgono
# meno del nome intero.
_UNRESOLVED = frozenset(("che", "tra", "fra", "cui"))


def _decimals(value):
    """Quante cifre dopo la virgola merita un numero in un titolo.

    Non e' `it_num`, che ne prende una fissa: "34.343,0 euro" in SERP e' rumore,
    e "84,8 anni" senza decimale sarebbe una cifra diversa. La regola e' la
    grandezza, perche' e' quella che decide se il decimale porta informazione.
    Lo zero si scrive "0": "0,00" dava allo zero una precisione che non ha, e in
    SERP si leggeva "dal 358% al 0,00%". Le due copie di questa regola,
    `numfmt.magnitude_decimals` e `decimals` in `static/js/v1.js`, le tiene
    allineate `tests/unit/test_decimals_parity.py`.
    """
    magnitude = abs(float(value))
    if magnitude == 0 or magnitude >= 100:
        return 0
    if magnitude >= 10:
        return 1
    return 2 if magnitude < 1 else 1


def format_number(value):
    """Un numero all'italiana: punto per le migliaia, virgola per i decimali."""
    if value is None:
        return None
    try:
        number = float(value)
        text = f"{number:,.{_decimals(number)}f}"
    except (TypeError, ValueError):
        return None
    if text.startswith("-") and not text.strip("-0.,"):
        text = text[1:]  # -0.0 e' zero, e lo zero non ha segno
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _short_unit(meta):
    """L'unita' come si scrive in un titolo, o None se non si scrive.

    La percentuale si attacca al numero e non vale come parola a se'; le unita'
    lunghe ("per 100.000 abitanti") costano piu' di quanto rendano. La forma
    breve la da' `numfmt.short_unit`, la stessa della pagina: cosi' "Numero
    medio di anni" diventa "anni" anche qui. Le etichette che non sono
    un'unita' (`numfmt.GENERIC_UNITS`) non si scrivono accanto a una cifra:
    uscivano titoli come "da 0,35 a 0,27 indice" e "da 5,6 a 3,8 rapporto".
    """
    raw = (meta.get("value_unit") or meta.get("unit") or "").strip()
    if not raw or indicator_notes.is_percentage_unit(raw):
        return None
    unit = numfmt.short_unit(raw)
    if not unit or unit == "%" or len(unit) > 12 or " " in unit:
        return None
    if numfmt.lower_first(unit).lower() in numfmt.GENERIC_UNITS:
        return None
    return unit


def _is_percentage(meta):
    return indicator_notes.is_percentage_unit(
        (meta.get("value_unit") or meta.get("unit") or "")
    )


# Le serie i cui estremi non vanno in SERP finche' qualcuno non li ha
# verificati alla fonte. `bes-06POL012P`, l'affollamento delle carceri per
# provincia, ha Macerata e Savona a zero dal 2016 dopo anni sopra il 60%, e
# Fermo al 358% nel 2024: il titolo diceva "dal 358% al 0,00%". Le serie possono
# essere vere, la causa non e' verificata, e un titolo non e' il posto per
# scoprirlo. La pagina resta com'e', con la sua classifica.
UNVERIFIED_EXTREMES = frozenset({"bes-06POL012P"})


def _code(meta):
    """Il codice pubblico ("ter-598", "bes-06POL012P"), o None se `meta` non lo dice."""
    family, raw_id = meta.get("family"), meta.get("raw_id")
    if not family or raw_id in (None, ""):
        return None
    return sources.indicator_code(family, raw_id)


def extremes(meta, level):
    """(territorio col valore alto, territorio col valore basso) del livello.

    `level["best"]` e `level["worst"]` sono orientati dalla direzione: su un
    indicatore `lower_better` il migliore e' il minimo. Un titolo che dice "da X
    a Y" pero' e' un intervallo, non una classifica, quindi si ordina per
    valore, altrimenti meta' del catalogo leggerebbe al contrario.

    Su `UNVERIFIED_EXTREMES` non ci sono estremi: ne' nel titolo, ne' nella
    description, ne' in `minValue` e `maxValue` del Dataset, che leggono questa
    stessa funzione.
    """
    if _code(meta) in UNVERIFIED_EXTREMES:
        return None, None
    high, low = level.get("best"), level.get("worst")
    if not high or not low:
        return None, None
    try:
        if float(low.get("value")) > float(high.get("value")):
            high, low = low, high
    except (TypeError, ValueError):
        return None, None
    if high.get("value") is None or low.get("value") is None:
        return None, None
    return high, low


def _figures(meta, level):
    """Il pezzo ", da X a Y unita'" del titolo, e la sua variante senza unita'.

    Sulle percentuali la preposizione si articola con `numfmt.articulated`
    ("dall'89,1% allo 0,22%"), e le due varianti coincidono: l'unita' e' il
    segno di percentuale, attaccato al numero.
    """
    high, low = extremes(meta, level)
    if high is None:
        return None, None
    top, bottom = format_number(high["value"]), format_number(low["value"])
    if top is None or bottom is None or top == bottom:
        return None, None
    if _is_percentage(meta):
        both = (f", {numfmt.articulated('da', top)}{top}% "
                f"{numfmt.articulated('a', bottom)}{bottom}%")
        return both, both
    unit = _short_unit(meta)
    bare = f", da {top} a {bottom}"
    return (f"{bare} {unit}" if unit else bare), bare


_PERCENT_RANGE = re.compile(r", (?:dal |dall'|dallo )(\S+%) (?:al |all'|allo )(\S+%)")


def _unarticled(figures):
    """", dall'89,1% allo 0%" -> ", da 89,1% a 0%": l'intervallo in percentuale
    senza articolo, o None se `figures` non e' un intervallo in percentuale."""
    match = _PERCENT_RANGE.fullmatch(figures or "")
    return f", da {match.group(1)} a {match.group(2)}" if match else None


def _cost(figures):
    """Quanto conta il pezzo delle cifre quando si decide che cosa sacrificare.

    Su un intervallo in percentuale conta come "dal X% al Y%", la forma di
    prima dell'elisione: "dallo" e "allo" costano un carattere ciascuno, e un
    articolo non deve spostare la scelta fra coda del livello, nome e cifre. Se
    la forma articolata poi non ci sta, si scrive "da X% a Y%", che e' piu'
    corta di tutte e due.
    """
    bare = _unarticled(figures)
    return len(bare) + 2 if bare else len(figures or "")


def _with_figures(text, figures, max_len):
    """`text` con le cifre accanto, articolate se ci stanno e senza articolo se
    no; None se nemmeno cosi' ci sta."""
    if not figures:
        return text if len(text) <= max_len else None
    for form in (figures, _unarticled(figures)):
        if form and len(text) + len(form) <= max_len:
            return f"{text}{form}"
    return None


def _level_tail(level):
    """" per regione" o " per provincia", dal livello che la pagina rende.

    La usano il titolo derivato e il ripiego: `page_title` la passa a
    `indicator_notes.seo_title`, che da solo appenderebbe `_TITLE_TAIL`, fissa
    su " per regione", anche sopra dati provinciali. Quella coda fissa e' il
    motivo per cui e' nato `taxonomy.PROVINCE_ONLY_TITLE_COLLISIONS`: prima di
    toglierlo va visto se serve ancora ai titoli scritti, che la coda del
    livello non la portano.
    """
    singular = (level.get("singular") or "").strip()
    return f" per {singular}" if singular else ""


def _fit(measure, marker, room, guarded=True, strict=True):
    """La misura dentro `room` caratteri, tenendo cio' che la distingue se si puo'.

    Due accorciatori, in quest'ordine.

    `_compact_title` tiene `testa (coda)`, e serve perche' su certi nomi cio'
    che distingue sta in fondo: "Famiglie con fonte principale di reddito **da
    lavoro autonomo**" contro "**da lavoro dipendente**". Tagliando dalla testa
    le tre pagine di quella famiglia uscivano con lo stesso `<title>`.

    Ma `_compact_title` **non rispetta il budget che riceve**: con venti
    caratteri a disposizione restituisce "Retribuzione (Retribuzione media
    annua)", trentanove caratteri e per giunta ridicolo. Il percorso derivato di
    `indicator_notes` lo avvolge in `_clamp_title`, che taglia e basta.

    Qui, se sfora, si ripiega su `_shorten_at_joint`, non su `_truncate_words`.
    `_truncate_words` taglia dove finisce il budget: rispetta il conteggio e
    sfigura il nome. Su 594 schede ne mutilava 138 e ne faceva collidere parecchie
    ("Differenza tra tasso per regione" su due pagine diverse, "Famiglie che
    lamentano per regione" su tre), cioe' proprio il guasto che `_compact_title`
    esiste per evitare. Quando nemmeno la giuntura basta si torna vuoti, e chi
    chiama rinuncia alle cifre invece che al nome.

    Con `guarded` tutti e due passano da `_keeps_meaning`: un accorciamento che
    tiene una parola sola ("Impermeabilizzazione") o che butta una negazione
    ("Ospiti anziani" da "Ospiti anziani non autosufficienti") dice un'altra
    cosa, e vale meno del nome intero senza cifre. `strict` protegge anche
    cifre, sigle e soglie ("PM10", "con meno di 40 anni", "di basso importo").
    """
    def keeps(text):
        return not guarded or _keeps_meaning(measure, text, marker, strict=strict)

    compact = indicator_notes._compact_title(measure, marker, room)
    if (compact and len(compact) <= room and _whole_words(compact, measure)
            and _head_holds(compact) and keeps(compact)):
        return compact
    trimmed = _shorten_at_joint(measure, room - len(marker))
    if trimmed and keeps(f"{trimmed}{marker}"):
        return f"{trimmed}{marker}"
    return ""


# Parole che un accorciamento non puo' buttare. Le negazioni rovesciano la
# misura: "Competenza numerica" da "Competenza numerica non adeguata" e'
# l'opposto. Le soglie la cambiano: "Tasso di partecipazione" senza "mancata",
# "Pensionati con reddito pensionistico" senza "di basso importo".
_NEGATIONS = frozenset(("non", "senza"))
_THRESHOLDS = frozenset((
    "almeno", "mancata", "mancato", "mancate", "mancati",
    "basso", "bassa", "bassi", "basse",
))


def _carries_meaning(word, strict):
    """Una parola che il titolo non puo' perdere: sempre una negazione, e con
    `strict` anche una cifra, una sigla o una soglia."""
    clean = word.strip(",.:()'\"").lower()
    if clean in _NEGATIONS:
        return True
    if not strict:
        return False
    if any(char.isdigit() for char in clean):
        return True
    letters = [char for char in word if char.isalpha()]
    if len(letters) >= 2 and all(char.isupper() for char in letters):
        return True
    return clean in _THRESHOLDS


def _keeps_meaning(measure, text, marker, strict=True):
    """La misura accorciata a `text` dice ancora la stessa cosa?

    La testa tiene almeno due parole, perche' una sola non dice mai di che
    cosa si parla: `_shorten_at_joint` misura in caratteri, e
    "Impermeabilizzazione" ne ha venti. E le parole buttate non portano una
    negazione e, con `strict`, nemmeno una cifra, una sigla o una soglia
    (`_carries_meaning`). Il nome intero passa sempre: non ha buttato niente.
    """
    kept = text[: len(text) - len(marker)] if marker and text.endswith(marker) else text
    if kept == measure:
        return True
    head, _, paren = kept.partition(" (")
    paren = paren.removesuffix(")")
    if len(head.split()) < 2 or not measure.startswith(head):
        return False
    dropped = measure[len(head):].strip()
    if paren and dropped.endswith(paren):
        dropped = dropped[: -len(paren)]
    return not any(_carries_meaning(word, strict) for word in dropped.split())


def _head_holds(compact):
    """La testa di `testa (coda)` si legge da sola?

    `_compact_title` guarda il budget, non il senso: su "Differenza tra tasso di
    occupazione maschile e femminile" consegnava "Differenza (maschile e
    femminile)", dieci caratteri di testa che non dicono di che cosa sia la
    differenza, e identici a quelli della scheda gemella sul tasso di attivita'.
    La soglia e' in parole, non in caratteri: `MIN_MEASURE` qui bocciava anche
    "Famiglie con fonte" (diciotto), cioe' la testa che tiene distinte le tre
    schede di quella famiglia, ed e' proprio il caso per cui `_compact_title`
    esiste. Una parola sola non dice mai di che cosa si parla, tre gia' si'.
    """
    head = compact.split(" (", 1)[0]
    words = head.split()
    if head == compact:
        return True
    if len(words) < 2:
        return False
    return not any(word.lower().rstrip(",") in _UNRESOLVED for word in words)


def _shorten_at_joint(measure, room):
    """La misura accorciata a una sua giuntura, o stringa vuota.

    Si taglia solo davanti a una preposizione, dove cio' che resta e' ancora un
    sintagma che si legge da solo, e si tiene la testa piu' lunga che ci sta.
    Niente scende sotto `MIN_MEASURE`, e una testa che contiene una relativa o un
    `tra` senza coppia si scarta: meglio il nome intero senza cifre che un
    troncone con le cifre accanto.
    """
    words = (measure or "").split()
    scelta = ""
    for index in range(1, len(words)):
        if words[index].lower().rstrip(",") not in _JOINTS:
            continue
        head = " ".join(words[:index]).rstrip(" ,.;:-(")
        if len(head) < MIN_MEASURE or len(head) > room or len(head) >= len(measure):
            continue
        if any(word.lower().rstrip(",") in _UNRESOLVED for word in head.split()):
            continue
        # Una giuntura dopo una congiunzione lascia la testa appesa: "Tasso di
        # criminalita' organizzata e" da "... organizzata e di tipo mafioso".
        if head.split()[-1].lower() in indicator_notes._TRAILING_STOP:
            continue
        if len(head) > len(scelta):
            scelta = head
    return scelta


def _whole_words(compact, measure):
    """La testa di `testa (coda)` finisce su una parola intera?

    `_truncate_words` taglia a meta' parola quando il budget e' piu' corto della
    prima parola: `text[:budget].rsplit(" ", 1)[0]` senza spazi restituisce il
    troncone. Cosi' "Speranza di vita alla nascita" diventava "Sper (di vita
    alla nascita)". Meglio un nome accorciato che un nome mutilato.
    """
    head = compact.split(" (", 1)[0]
    if not head or head == measure:
        return True
    if not measure.startswith(head):
        return False
    return measure[len(head)] == " "


def answer_title(meta, level, max_len=TITLE_MAX):
    """Il titolo derivato: la misura, il livello, e l'intervallo.

    Sopra budget si sacrifica in quest'ordine: prima l'unita', poi la coda del
    livello, poi si accorcia la misura, e solo se neanche cosi' ci sta si
    rinuncia alle cifre. La misura non scende sotto `MIN_MEASURE`, perche' un
    nome irriconoscibile non lo clicca nessuno neanche con un numero accanto.

    L'ordine sta scritto qui e non in due cicli annidati: annidandoli l'unita'
    sopravviveva alla coda del livello, e usciva "Retribuzione media annua, da
    34.343 a 13.388 euro" invece di "Retribuzione media annua per provincia, da
    34.343 a 13.388". Dire "euro" accanto a una cifra in euro non aggiunge
    niente; dire "per provincia" risponde a meta' della domanda.

    Dove c'e' un nome breve curato (`indicator_notes.SHORT_NAMES`) la misura e'
    quello, senza marcatore, e non si accorcia oltre: o ci sta intero, o si
    rinuncia al pezzo successivo.

    Sulle pagine provinciali l'ordine e' un altro, e lo scrive `_province_title`.
    """
    curated = indicator_notes.short_name(_code(meta), level.get("key"))
    if curated:
        measure, marker = curated, ""
    else:
        measure = indicator_notes._short_name_for_title(meta.get("name") or "")
        marker = indicator_notes._variant_marker(meta.get("name") or "")
    if not measure:
        return None
    if level.get("key") == "provincia":
        return _province_title(meta, level, measure, marker, bool(curated), max_len)
    tail = _level_tail(level)
    with_unit, without_unit = _figures(meta, level)

    tentativi = (
        (with_unit, tail), (without_unit, tail),
        (with_unit, ""), (without_unit, ""),
        (None, tail), (None, ""),
    )
    for guarded in (True, False):
        for figures, tail_part in tentativi:
            room = max_len - len(tail_part) - _cost(figures)
            if room - len(marker) < MIN_MEASURE:
                continue
            if curated:
                text = measure if len(measure) <= room else ""
            else:
                text = _fit(measure, marker, room, guarded=guarded, strict=False)
            if not text:
                continue
            candidate = _with_figures(f"{text}{tail_part}", figures, max_len)
            if candidate:
                return candidate
    return None


def _province_title(meta, level, measure, marker, curated, max_len):
    """Il titolo derivato di una pagina provinciale: " per provincia" non cade mai.

    Sulle regioni la coda del livello e' la prima cosa che si sacrifica, e va
    bene: "per regione" e' il livello che chi cerca si aspetta. Sulle province
    no. Delle 43 pagine provinciali con il livello indicizzabile 24 uscivano
    senza "per provincia" (24 settembre 2026), e in SERP non si capiva che la
    pagina ha le 107 province, cioe' l'unica cosa che la distingue dalla scheda
    regionale. Con questa regola sono 42 su 43: l'ultima ha un titolo scritto.

    Quindi la coda resta, e se il titolo sfora si rinuncia nell'ordine a:

    1. l'unita';
    2. il nome intero, per il nome breve curato (`indicator_notes.SHORT_NAMES`),
       che se c'e' prende il suo posto da subito e non si accorcia oltre;
    3. un accorciamento con guardia (`_fit` con `strict`): almeno due parole, e
       niente cifre, sigle, negazioni o soglie buttate;
    4. le cifre, che diventano ", dati {anno}";
    5. l'anno.

    L'anno sostituisce le cifre solo dove le cifre c'erano e non ci stavano:
    una serie senza estremi (`contextual`, `UNVERIFIED_EXTREMES`) resta col nome
    e il livello, come prima.
    """
    tail = _level_tail(level)
    with_unit, without_unit = _figures(meta, level)
    figures = [option for option in dict.fromkeys((with_unit, without_unit)) if option]
    year = level.get("year_max")
    dated = f", dati {year}" if figures and year else None
    whole = f"{measure}{marker}"

    def shortened(option):
        room = max_len - len(tail) - _cost(option)
        if room - len(marker) < MIN_MEASURE:
            return ""
        return _fit(measure, marker, room, guarded=True, strict=True)

    # 1 e 2: il nome (o il nome breve) con le cifre, prima con l'unita' e poi
    # senza. 3: accorciato, sempre con le cifre. 4 e 5: l'anno, poi niente.
    attempts = [(whole, option) for option in figures]
    if not curated:
        attempts += [(shortened, option) for option in figures]
    for option in ((dated, None) if dated else (None,)):
        attempts.append((whole, option))
        if not curated:
            attempts.append((shortened, option))

    for name, option in attempts:
        text = name(option) if callable(name) else name
        if not text:
            continue
        candidate = _with_figures(f"{text}{tail}", option, max_len)
        if candidate:
            return candidate
    return None


def enrich(title, meta, level, max_len=TITLE_MAX):
    """Appende l'intervallo a un titolo gia' scritto, se ci sta nel budget."""
    if not title:
        return title
    with_unit, without_unit = _figures(meta, level)
    for figures in (with_unit, without_unit):
        if figures and len(title) + _cost(figures) <= max_len:
            return _with_figures(title, figures, max_len)
    return title


def _figures_before_brand(title, meta, level, site_name, max_len):
    """Lo spazio che avanza a un titolo autorato: prima le cifre, poi la marca.

    `authored_seo_title` appende la marca appena ci sta, e su `ter-901` questo
    produceva "PIL pro capite per regione · Divario Italia": quarantatre
    caratteri, di cui diciassette spesi in un nome che in posizione 9,5 non
    riconosce nessuno, e nessuno dei due numeri che quella pagina ha in casa.
    Qui si prova prima l'intervallo, e la marca si aggiunge solo se le cifre non
    ci stavano. Il nome del sito Google lo sintetizza comunque dal nodo
    `WebSite` della home.
    """
    if not title:
        return title
    enriched = enrich(title, meta, level, max_len=max_len)
    if enriched != title:
        return enriched
    brand = f" · {site_name}" if site_name else ""
    if brand and len(title) + len(brand) <= max_len:
        return title + brand
    return title


def _preposition(name, level):
    """"in Lombardia", ma "a Milano": la preposizione la decide il livello.

    Non il nome: "Calabria" e' una parola sola come "Milano", e indovinare dalla
    forma produceva "a Calabria". Il livello lo sa gia' e non sbaglia mai.
    """
    name = (name or "").strip()
    if not name:
        return ""
    return at_place(name) if level.get("key") == "provincia" else f"in {name}"


_MASCULINE_REGIONS = {
    "Piemonte", "Veneto", "Lazio", "Molise", "Trentino Alto Adige",
    "Trentino-Alto Adige", "Friuli-Venezia Giulia",
}
_PLURAL_REGIONS = {"Marche"}


def of_region(name):
    """"del Veneto", "della Puglia", "dell'Umbria", "delle Marche".

    Le regioni prendono l'articolo, e "Le province di Puglia" non e' come lo
    si dice. Il genere non si indovina dalla desinenza (il Piemonte, il
    Molise), quindi i maschili e il plurale sono scritti qui.
    """
    name = (name or "").strip()
    if name in _PLURAL_REGIONS:
        return f"delle {name}"
    if name in _MASCULINE_REGIONS:
        return f"dell'{name}" if name[:1].lower() in "aeiou" else f"del {name}"
    if name[:1].lower() in "aeiou":
        return f"dell'{name}"
    return f"della {name}"


# Le regioni che nello stato in luogo prendono l'articolo: "nel Lazio", "nelle
# Marche". Tutte le altre vogliono "in" nudo, anche i maschili ("in Piemonte",
# "in Veneto", "in Trentino Alto Adige"), dove l'articolo suona di burocrazia.
_ARTICLED_IN = {"Lazio": "nel", "Molise": "nel", "Marche": "nelle"}


def in_region(name):
    """"in Puglia", "nel Lazio", "nelle Marche": lo stato in luogo davanti a
    una regione, accanto a `of_region`. Minuscolo: chi apre una frase con
    questa preposizione alza lui la prima lettera."""
    name = (name or "").strip()
    return f"{_ARTICLED_IN.get(name, 'in')} {name}"


# Le province che non sono una citta' e prendono l'articolo: "il Sud Sardegna",
# "nel Verbano-Cusio-Ossola". Tutte e due maschili.
ARTICLED_PROVINCES = frozenset({"Sud Sardegna", "Verbano-Cusio-Ossola"})


def at_place(name):
    """"a Milano", "ad Aosta", "all'Aquila", "alla Spezia", "nel Sud Sardegna".

    La preposizione davanti al nome di una citta' o di una provincia. Scritta a
    mano nei template dava "a Aosta" e "a L'Aquila" su sei pagine.
    """
    name = (name or "").strip()
    if name in ARTICLED_PROVINCES:
        return f"nel {name}"
    return to_place(name)


def _from_parts(name):
    """("da ", "Milano"), ("dall'", "Aquila"), ("dalla ", "Spezia"), ("dal ",
    "Sud Sardegna"): la preposizione e il resto del nome, separati perche' chi
    scrive un link ci mette dentro solo il nome."""
    name = (name or "").strip()
    if name in ARTICLED_PROVINCES:
        return "dal ", name
    if name.startswith("L'"):
        return "dall'", name[2:]
    if name.startswith("La "):
        return "dalla ", name[3:]
    return "da ", name


def from_place(name):
    """"da Milano", "dall'Aquila", "dalla Spezia", "dal Sud Sardegna": il
    complemento di separazione ("separano Lecco da Pavia"). Scritto a mano
    usciva "da Sud Sardegna", come prima "a Aosta" e "a L'Aquila"."""
    return "".join(_from_parts(name))


def to_place(name):
    """"a Milano", "all'Aquila", "al Sud Sardegna": il complemento di termine
    ("davanti a"), che per le province con l'articolo non e' lo stato in luogo."""
    name = (name or "").strip()
    if name in ARTICLED_PROVINCES:
        return f"al {name}"
    if name.startswith("L'"):
        return f"all'{name[2:]}"
    if name.startswith("La "):
        return f"alla {name[3:]}"
    if name[:1].lower() == "a":
        return f"ad {name}"
    return f"a {name}"


def _places(extreme, level):
    """Dove sta un estremo: "a Nuoro", "a Lecco e a Treviso", "in 16 province".

    I pari merito si leggono da `level["observations"]`, i territori dell'ultimo
    anno: `best` e `worst` ne nominano uno solo, il primo in ordine alfabetico.
    Oltre due si conta, perche' una fila di nomi in SERP non si legge.
    """
    names = [row["name"] for row in level.get("observations") or ()
             if row.get("value") is not None and row.get("value") == extreme.get("value")]
    if extreme["name"] not in names:
        names = [extreme["name"]]
    if len(names) > 2:
        return f"in {len(names)} {level.get('plural') or 'territori'}"
    return " e ".join(_preposition(name, level) for name in names)


def _coverage_closing(meta, level):
    """" 107 province a confronto, dati Istat." o " 106 province con dato, dati
    Istat.": quanti territori hanno il dato nell'anno, e di chi e' il dato."""
    total = level.get("territory_total")
    plural = level.get("plural") or "territori"
    observed = sum(1 for row in level.get("observations") or () if row.get("value") is not None)
    institution = (meta.get("institution") or "").strip()
    if observed and total and observed < total:
        closing = f" {observed} {plural} con dato"
    elif total:
        closing = f" {total} {plural} a confronto"
    else:
        closing = f" Tutte le {plural} a confronto"
    return closing + (f", dati {institution}." if institution else ".")


# Un tasso col suo denominatore: "Tassi standardizzati per 10.000 residenti",
# "tasso standardizzato per 10.000". Il denominatore comincia con una cifra,
# cosi' "Tasso specifico per coorte" non ne ha uno.
_RATE_DENOMINATOR = re.compile(r"(?i)^tass[oi]\b.*?\s(per\s+\d[\d.]*(?:\s+\S.*)?)$")


def _rate_unit(raw):
    """Il denominatore di un tasso ("per 10.000 residenti"), o None.

    `numfmt.phrase_unit` rinuncia alle etichette lunghe, e sulle serie di
    mortalita' la frase-risposta usciva con la cifra nuda ("da 1,9 (Vercelli)"),
    che si legge come un totale. Qui si tiene solo la coda "per N ...": il resto
    ("standardizzati") lo dice la pagina. Resta locale alla frase delle
    province, perche' `phrase_unit` scrive anche tessere, celle e mappe di
    tutte le altre pagine.
    """
    match = _RATE_DENOMINATOR.match((raw or "").strip())
    return match.group(1) if match else None


def province_answer(meta, level, link_prefix=None, max_len=DESCRIPTION_MAX):
    """La frase-risposta di una pagina provinciale senza pezzo, o None.

    "Speranza di vita per provincia, 2024: da 84,9 anni (Lecco e Treviso) a
    81,4 (Napoli). In Lombardia 2,3 anni separano Lecco da Pavia."

    E' la description e, con i territori linkati (`link_prefix`, il prefisso dei
    profili, "/provincia/"), la frase che apre la pagina: le due dicono la
    stessa cosa, e la `description` del Dataset e' la seconda senza Markdown.

    Tre scelte, tutte contro difetti che si leggevano:

    - i territori stanno fra parentesi. Con la preposizione ("da 84,9 anni a
      Lecco e a Treviso a 81,4 a Napoli") la frase era una catena di "a" in cui
      non si capiva quale "a" fosse una cifra e quale un luogo;
    - la seconda frase e' la distanza piu' ampia dentro una stessa regione, che
      e' cio' che la vista regionale non puo' dire. Solo dove la misura ha
      un'unita' che regge "2,3 anni separano" o e' una percentuale ("punti"),
      e solo se sta nel budget. Altrimenti si dice quante province hanno il
      dato. "da" e non "e" fra i due nomi: "separano Fermo e Pesaro e Urbino"
      non si legge;
    - l'unita' accanto al primo estremo e' quella delle frasi (`phrase_unit`),
      che porta anche il denominatore ("3,4 per 100.000 abitanti", "46,0 per
      100 km²"): il nome breve non lo dice, e senza l'unita' la cifra si
      leggerebbe come un totale. Dove `phrase_unit` non scrive niente perche'
      l'etichetta e' lunga ("Tassi standardizzati per 10.000 residenti"), il
      denominatore lo estrae `_rate_unit`. Se non sta nel budget, la cifra
      resta nuda.

    Gli estremi sono quelli di `extremes`, gli stessi del titolo: sulle serie
    `contextual` e su `UNVERIFIED_EXTREMES` non ce ne sono, e la frase non c'e'.
    La regione di ogni provincia la mette il modello della scheda in
    `level["region_of"]`; senza, la seconda frase dice il conteggio.
    """
    if level.get("key") != "provincia":
        return None
    high, low = extremes(meta, level)
    if high is None:
        return None
    top, bottom = format_number(high["value"]), format_number(low["value"])
    if top is None or bottom is None or top == bottom:
        return None
    # Il nome breve curato, o il nome col suo marcatore: "(25-39 anni)" e'
    # parte della misura, e la description regionale lo perde.
    name = meta.get("name") or ""
    measure = (indicator_notes.short_name(_code(meta), "provincia")
               or (indicator_notes._short_name_for_title(name) + indicator_notes._variant_marker(name))).strip()
    if not measure:
        return None

    rows = [row for row in level.get("observations") or () if row.get("value") is not None]
    plural = level.get("plural") or "territori"
    percent = _is_percentage(meta)
    raw_unit = meta.get("value_unit") or meta.get("unit")
    unit = None if percent else (numfmt.phrase_unit(raw_unit) or _rate_unit(raw_unit))
    year = level.get("year_max")

    def show(row, linked, text=None):
        text = text or row["name"]
        if linked and link_prefix and row.get("key"):
            return f"[{text}]({link_prefix}{row['key']})"
        return text

    def subject(row, linked):
        """"il Sud Sardegna" come soggetto, l'articolo fuori dal link."""
        article = "il " if row["name"] in ARTICLED_PROVINCES else ""
        return article + show(row, linked)

    def separated(row, linked):
        """"da Pavia", "dall'Aquila", "dal Sud Sardegna": la preposizione
        fuori dal link, cosi' il testo senza Markdown e' la stessa frase."""
        preposition, rest = _from_parts(row["name"])
        return preposition + show(row, linked, rest)

    def where(extreme, linked):
        tied = [row for row in rows if row["value"] == extreme["value"]]
        if not any(row["name"] == extreme["name"] for row in tied):
            tied = [extreme]
        if len(tied) > 2:
            return f"({len(tied)} {plural})"
        return "(" + " e ".join(show(row, linked) for row in tied) + ")"

    def opening(linked, with_unit):
        first = f"{top}%" if percent else (f"{top} {unit}" if with_unit and unit else top)
        second = f"{bottom}%" if percent else bottom
        return (f"{measure}{_level_tail(level)}{f', {year}' if year else ''}: "
                f"da {first} {where(high, linked)} a {second} {where(low, linked)}.")

    within = _widest_within_region(meta, level, rows, percent)

    def inside(linked):
        if not within:
            return ""
        gap, region, upper, lower = within
        where_region = in_region(region)
        return (f" {where_region[:1].upper()}{where_region[1:]} {gap} separano "
                f"{subject(upper, linked)} {separated(lower, linked)}.")

    closing = _coverage_closing(meta, level)
    linked = bool(link_prefix)
    # Le scelte si fanno sul testo semplice, che e' quello che conta nel budget:
    # i link del Markdown non si leggono in SERP.
    for with_unit in (True, False):
        plain = opening(False, with_unit)
        if len(plain) > max_len:
            continue
        if within and len(plain) + len(inside(False)) <= max_len:
            return opening(linked, with_unit) + inside(linked)
        if len(plain) + len(closing) <= max_len:
            return opening(linked, with_unit) + closing
        return opening(linked, with_unit)
    return None


def _widest_within_region(meta, level, rows, percent):
    """(distanza scritta, regione, provincia piu' alta, piu' bassa) della
    regione dove le sue province si allontanano di piu', o None.

    Solo con un'unita' che si scrive dopo una cifra sola ("anni", "euro") o
    con le percentuali, in punti: "2,1 per 100.000 abitanti separano" non si
    legge. A parita' di distanza vince la regione prima in ordine alfabetico,
    cosi' la frase non cambia da un avvio all'altro.
    """
    unit = "punti" if percent else _short_unit(meta)
    region_of = level.get("region_of") or {}
    if not unit or not region_of:
        return None
    by_region = {}
    for row in rows:
        region = region_of.get(row.get("key"))
        if region:
            by_region.setdefault(region, []).append(row)
    best = None
    for region in sorted(by_region):
        members = by_region[region]
        if len(members) < 2:
            continue
        upper = min(members, key=lambda row: (-row["value"], row["name"]))
        lower = min(members, key=lambda row: (row["value"], row["name"]))
        gap = upper["value"] - lower["value"]
        if gap > 0 and (best is None or gap > best[0]):
            best = (gap, region, upper, lower)
    if best is None:
        return None
    gap, region, upper, lower = best
    text = format_number(gap)
    if text is None or text == "0":
        return None
    return f"{text} {unit}", region, upper, lower


def answer_description(meta, level, max_len=DESCRIPTION_MAX):
    """La descrizione derivata, per le pagine che non hanno un lead scritto.

    Dove il pezzo c'e', la descrizione e' il suo attacco e non si tocca: quella
    di `ter-901` dice gia' cifra, territorio e anno. Questa serve solo dove oggi
    esce una formula che non dice niente.

    La forma e' "Misura, anno: da X a Y." e non "Nel 2023 la misura va da...",
    per non dover indovinare l'articolo: in italiano sarebbe la/il/lo/l'/i/le a
    seconda della parola, e sbagliarlo si legge subito.

    Un estremo condiviso si dice tutto: "a 0 in 16 province", non "a 0 ad
    Aosta", che era solo la prima in ordine alfabetico delle sedici. E il
    conteggio e' quello dei territori col dato nell'anno, "106 province con
    dato", quando non sono tutti.

    Sulle province la forma e' quella di `province_answer`.
    """
    if level.get("key") == "provincia":
        answer = province_answer(meta, level, max_len=max_len)
        if answer:
            return answer
    high, low = extremes(meta, level)
    if high is None:
        return None
    top, bottom = format_number(high["value"]), format_number(low["value"])
    if top is None or bottom is None:
        return None
    measure = (indicator_notes.short_name(_code(meta), level.get("key"))
               or indicator_notes._short_name_for_title(meta.get("name") or "") or "").strip()
    if not measure:
        return None

    unit = (meta.get("value_unit") or meta.get("unit") or "").strip()
    if _is_percentage(meta):
        value_high, value_low = f"{top}%", f"{bottom}%"
    elif unit and len(unit) <= 16:
        value_high, value_low = f"{top} {unit}", bottom
    else:
        value_high, value_low = top, bottom

    year = level.get("year_max")
    opening = (f"{measure}{f', {year}' if year else ''}: "
               f"da {value_high} {_places(high, level)} "
               f"a {value_low} {_places(low, level)}.")

    closing = _coverage_closing(meta, level)
    if len(opening) + len(closing) <= max_len:
        return opening + closing
    if len(opening) <= max_len:
        return opening
    return indicator_notes._truncate_words(opening, max_len, add_period=True)


def page_title(article, meta, level, site_name=None, source_qualifier=None,
               max_len=TITLE_MAX):
    """Il `<title>` della scheda, in ordine di forza.

    1. il `seo_title` dell'articolo, che una persona ha scritto apposta;
    2. l'`h1` dell'articolo, **ma solo se ci sta intero**. Prima un H1 lungo
       veniva ridotto a `testa (coda)` da `_authored_short`, che e' fatto per i
       nomi amministrativi: su un titolo editoriale produce cose come
       "Disoccupazione di lunga durata (rte dov'era piu' alta)". Un titolo
       sfigurato rende meno di un titolo derivato con dentro una cifra, quindi
       qui si cade al punto 3 invece di mutilarlo;
    3. il titolo-risposta derivato dai dati;
    4. il derivato di sempre, quando i dati non bastano a riempire la formula.

    Ai primi due si prova ad appendere l'intervallo.
    """
    authored = (article or {}).get("seo_title")
    if authored:
        brand = f" · {site_name}" if site_name else ""
        base = indicator_notes.authored_seo_title(
            authored, site_name or "", max_len=max_len,
            source_qualifier=source_qualifier,
        )
        # La marca si toglie qui e si rimette dopo, se le cifre non ci stanno.
        # Non si chiama `authored_seo_title` con un nome vuoto: costruisce il
        # suffisso come " · {nome}" e con il nome vuoto lascia un "·" orfano.
        if brand and base.endswith(brand):
            base = base[: -len(brand)]
        return _figures_before_brand(base, meta, level, site_name, max_len)

    h1 = (article or {}).get("h1")
    if h1:
        qualifier = f" ({source_qualifier})" if source_qualifier else ""
        whole = f"{h1.strip()}{qualifier}"
        if len(whole) <= max_len:
            return _figures_before_brand(whole, meta, level, site_name, max_len)

    derived = answer_title(meta, level, max_len=max_len)
    if derived:
        return derived
    # La coda e' quella del livello anche qui: fissa su " per regione", la
    # vista province dei NEET prendeva il `<title>` della vista regioni.
    return indicator_notes.seo_title(
        meta.get("name") or "", site_name or "", max_len=max_len,
        source_qualifier=source_qualifier, tail=_level_tail(level),
    )


def page_description(article, meta, level, composed=None, max_len=DESCRIPTION_MAX):
    """La descrizione SERP: l'attacco del pezzo se c'e', altrimenti le cifre.

    `composed` e' il lead che il sito genera da solo. Si usa solo come ultima
    spiaggia, perche' e' la formula che oggi produce descrizioni che non dicono
    niente ("Esprime in euro la retribuzione media annua dei lavoratori
    dipendenti, nel perimetro medio definito dalla fonte.").
    """
    authored = (article or {}).get("lead")
    if authored:
        return indicator_notes.meta_description_from_attacco(authored)
    derived = answer_description(meta, level, max_len=max_len)
    if derived:
        return derived
    if composed:
        return indicator_notes.meta_description_from_attacco(composed)
    return None
