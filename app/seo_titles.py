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
italiane", "pil pro capite calabria"). Copre il 61% delle pagine
indicizzabili, 228 su 372, misurato sulla catena vera di `page_title` e non su
questa funzione da sola. Gli estremi esistono su 273 (73%): le 99 che non li
hanno sono quasi tutte `contextual`, dove il catalogo non espone un massimo e
un minimo perche' su quelle serie un estremo non vuol dire niente, e quella
guardia non si aggira dal titolo. Le altre 45 li hanno e li perdono al budget,
perche' il nome e' troppo lungo per stare accanto all'intervallo: li' si
rinuncia alle cifre invece che al nome, ed e' lo scambio giusto. Una forma
compatta ("9,4-0,4%") ne recupererebbe quattro, che non valgono un secondo
formato di numero in SERP.

Il 70% che stava scritto qui era il conto fatto prima che `_shorten_at_joint`
sostituisse il taglio a budget, cioe' prima della correzione raccontata in
`_fit`.
"""
from __future__ import annotations

from app import indicator_notes

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
    """
    magnitude = abs(float(value))
    if magnitude >= 100:
        return 0
    if magnitude >= 10:
        return 1
    return 2 if magnitude < 1 else 1


def format_number(value):
    """Un numero all'italiana: punto per le migliaia, virgola per i decimali."""
    if value is None:
        return None
    try:
        text = f"{float(value):,.{_decimals(value)}f}"
    except (TypeError, ValueError):
        return None
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _short_unit(meta):
    """L'unita' come si scrive in un titolo, o None se non si scrive.

    La percentuale si attacca al numero e non vale come parola a se'; le unita'
    lunghe ("numero medio di componenti") costano piu' di quanto rendano.
    """
    unit = (meta.get("value_unit") or meta.get("unit") or "").strip()
    if not unit or indicator_notes.is_percentage_unit(unit):
        return None
    if len(unit) > 12 or " " in unit:
        return None
    return unit


def _is_percentage(meta):
    return indicator_notes.is_percentage_unit(
        (meta.get("value_unit") or meta.get("unit") or "")
    )


def extremes(meta, level):
    """(territorio col valore alto, territorio col valore basso) del livello.

    `level["best"]` e `level["worst"]` sono orientati dalla direzione: su un
    indicatore `lower_better` il migliore e' il minimo. Un titolo che dice "da X
    a Y" pero' e' un intervallo, non una classifica, quindi si ordina per
    valore, altrimenti meta' del catalogo leggerebbe al contrario.
    """
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
    """Il pezzo ", da X a Y unita'" del titolo, e la sua variante senza unita'."""
    high, low = extremes(meta, level)
    if high is None:
        return None, None
    top, bottom = format_number(high["value"]), format_number(low["value"])
    if top is None or bottom is None or top == bottom:
        return None, None
    if _is_percentage(meta):
        both = f", dal {top}% al {bottom}%"
        return both, both
    unit = _short_unit(meta)
    bare = f", da {top} a {bottom}"
    return (f"{bare} {unit}" if unit else bare), bare


def _level_tail(level):
    """" per regione" o " per provincia", dal livello che la pagina rende.

    `indicator_notes._TITLE_TAIL` e' fissa su " per regione" e viene appesa
    anche sopra dati provinciali: e' il motivo per cui esiste
    `taxonomy.PROVINCE_ONLY_TITLE_COLLISIONS`, che rattoppa il sintomo.
    """
    singular = (level.get("singular") or "").strip()
    return f" per {singular}" if singular else ""


def _fit(measure, marker, room):
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
    """
    compact = indicator_notes._compact_title(measure, marker, room)
    if compact and len(compact) <= room and _whole_words(compact, measure) and _head_holds(compact):
        return compact
    trimmed = _shorten_at_joint(measure, room - len(marker))
    return f"{trimmed}{marker}" if trimmed else ""


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
    """
    measure = indicator_notes._short_name_for_title(meta.get("name") or "")
    if not measure:
        return None
    marker = indicator_notes._variant_marker(meta.get("name") or "")
    tail = _level_tail(level)
    with_unit, without_unit = _figures(meta, level)

    tentativi = (
        (with_unit, tail), (without_unit, tail),
        (with_unit, ""), (without_unit, ""),
        (None, tail), (None, ""),
    )
    for figures, tail_part in tentativi:
        room = max_len - len(tail_part) - len(figures or "")
        if room - len(marker) < MIN_MEASURE:
            continue
        text = _fit(measure, marker, room)
        if not text:
            continue
        candidate = f"{text}{tail_part}{figures or ''}"
        if len(candidate) <= max_len:
            return candidate
    return None


def enrich(title, meta, level, max_len=TITLE_MAX):
    """Appende l'intervallo a un titolo gia' scritto, se ci sta nel budget."""
    if not title:
        return title
    with_unit, without_unit = _figures(meta, level)
    for figures in (with_unit, without_unit):
        if figures and len(title) + len(figures) <= max_len:
            return f"{title}{figures}"
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


def answer_description(meta, level, max_len=DESCRIPTION_MAX):
    """La descrizione derivata, per le pagine che non hanno un lead scritto.

    Dove il pezzo c'e', la descrizione e' il suo attacco e non si tocca: quella
    di `ter-901` dice gia' cifra, territorio e anno. Questa serve solo dove oggi
    esce una formula che non dice niente.

    La forma e' "Misura, anno: da X a Y." e non "Nel 2023 la misura va da...",
    per non dover indovinare l'articolo: in italiano sarebbe la/il/lo/l'/i/le a
    seconda della parola, e sbagliarlo si legge subito.
    """
    high, low = extremes(meta, level)
    if high is None:
        return None
    top, bottom = format_number(high["value"]), format_number(low["value"])
    if top is None or bottom is None:
        return None
    measure = (indicator_notes._short_name_for_title(meta.get("name") or "") or "").strip()
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
               f"da {value_high} {_preposition(high['name'], level)} "
               f"a {value_low} {_preposition(low['name'], level)}.")

    total = level.get("territory_total")
    plural = level.get("plural") or "territori"
    institution = (meta.get("institution") or "").strip()
    closing = f" {total} {plural} a confronto" if total else f" Tutte le {plural} a confronto"
    closing += f", dati {institution}." if institution else "."

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
    return indicator_notes.seo_title(
        meta.get("name") or "", site_name or "", max_len=max_len,
        source_qualifier=source_qualifier,
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
