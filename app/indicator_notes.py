import re


# Metriche che il solo nome non basta a spiegare. Le definizioni restano
# descrittive: chiariscono numeratore e denominatore senza aggiungere cause.
PLAIN_DEFINITION_OVERRIDES = {
    "MULTI_ABIT_AFFOLLAMENTO": (
        "Indica quanti componenti della famiglia vivono mediamente ogni 100 m² "
        "di superficie dell'abitazione"
    ),
    "MULTI_ABIT_SPESA_REDDITO": (
        "Indica quanti euro di spesa mensile per l'abitazione corrispondono a "
        "100 euro di reddito medio mensile familiare"
    ),
    "MULTI_SPESA_GINI": (
        "Misura quanto la spesa per consumi è concentrata tra le famiglie. Un "
        "valore più alto indica una distribuzione più diseguale"
    ),
    "MULTI_SPESA_INTERQUINTILE": (
        "Indica quante volte la spesa per consumi del quinto di famiglie con la "
        "spesa più alta supera quella del quinto con la spesa più bassa"
    ),
    "907": (
        "Indica il saldo per abitante tra prestazioni sociali ricevute e imposte "
        "e contributi versati. Un valore positivo segnala una regione "
        "beneficiaria netta"
    ),
    "906": (
        "Somma per abitante i redditi da lavoro, capitale e impresa delle "
        "famiglie, prima di imposte e trasferimenti"
    ),
    "930": (
        "Misura quanto il reddito netto familiare è distribuito in modo diseguale "
        "su una scala da 0 a 1, escludendo i fitti imputati"
    ),
    "102": (
        "Indica la quota di giovani tra 18 e 24 anni con al massimo la licenza "
        "media che non studiano e non partecipano ad attività formative"
    ),
    "199": (
        "Indica la quota di uomini tra 18 e 24 anni con al massimo la licenza "
        "media che non studiano e non partecipano ad attività formative"
    ),
    "200": (
        "Indica la quota di donne tra 18 e 24 anni con al massimo la licenza "
        "media che non studiano e non partecipano ad attività formative"
    ),
    "414": (
        "Indica la quota di bambini tra 0 e 2 anni che hanno utilizzato asili "
        "nido, micronidi o altri servizi per l'infanzia"
    ),
    "67": (
        "Indica la quota di persone tra 25 e 64 anni senza un'occupazione che "
        "partecipano ad attività formative o di istruzione"
    ),
    "187": (
        "Indica la quota di uomini tra 25 e 64 anni senza un'occupazione che "
        "partecipano ad attività formative o di istruzione"
    ),
    "188": (
        "Indica la quota di donne tra 25 e 64 anni senza un'occupazione che "
        "partecipano ad attività formative o di istruzione"
    ),
    "107": (
        "Rapporta il valore aggiunto dell'industria alimentare, delle bevande e "
        "del tabacco alle unità di lavoro equivalenti a tempo pieno del settore"
    ),
    "1": (
        "Rapporta il valore aggiunto di agricoltura, caccia e silvicoltura alle "
        "unità di lavoro equivalenti a tempo pieno del settore"
    ),
    "31": (
        "Rapporta il valore aggiunto di agricoltura, allevamento e attività "
        "connesse agli ettari di superficie agricola utilizzata"
    ),
    "419": (
        "Indica la quota di occupati nella manifattura ad alta tecnologia e nei "
        "servizi ad alta tecnologia e intensità di conoscenza"
    ),
    "408": (
        "Indica la quota di giovani tra 15 e 29 anni che non lavorano e non "
        "seguono percorsi di istruzione o formazione"
    ),
    "477": (
        "Indica la quota di uomini tra 15 e 29 anni che non lavorano e non "
        "seguono percorsi di istruzione o formazione"
    ),
    "478": (
        "Indica la quota di donne tra 15 e 29 anni che non lavorano e non "
        "seguono percorsi di istruzione o formazione"
    ),
    "133": (
        "Rapporta il valore aggiunto dei servizi alle imprese alle unità di "
        "lavoro equivalenti a tempo pieno degli stessi servizi"
    ),
    "139": (
        "Indica quanti stalli offrono i parcheggi di corrispondenza dei comuni "
        "capoluogo ogni 1.000 autovetture circolanti"
    ),
    "270": (
        "Indica quanti chilometri di rete ferroviaria sono presenti ogni 100 "
        "km² di superficie regionale"
    ),
    "273": (
        "Indica quanti chilometri di rete stradale sono presenti ogni 100 km² "
        "di superficie regionale"
    ),
    "276": (
        "Indica quanti chilometri di autostrada sono presenti ogni 100 km² di "
        "superficie regionale"
    ),
    "371": (
        "Indica la quota di persone che vivono in sovraffollamento e in "
        "abitazioni con carenze di servizi o problemi strutturali"
    ),
    "375": (
        "Rapporta i consumi elettrici delle imprese agricole, espressi in GWh, "
        "a ogni 100 milioni di euro di valore aggiunto dell'agricoltura"
    ),
    "376": (
        "Rapporta i consumi elettrici delle imprese industriali, espressi in GWh, "
        "a ogni 100 milioni di euro di valore aggiunto dell'industria"
    ),
    "377": (
        "Rapporta i consumi elettrici delle imprese private dei servizi, espressi "
        "in GWh, a ogni 100 milioni di euro di valore aggiunto del settore"
    ),
    "437": (
        "Rapporta i consumi finali di energia elettrica e termica alle unità di "
        "lavoro equivalenti a tempo pieno"
    ),
    "378": (
        "Indica quale quota dei consumi interni lordi di elettricità è coperta "
        "dalla produzione in cogenerazione"
    ),
    "379": (
        "Indica quale quota dei consumi interni lordi di elettricità è coperta "
        "dalla produzione da bioenergie"
    ),
    "85": (
        "Indica quale quota dei consumi interni lordi di elettricità è coperta "
        "da fonti rinnovabili, compreso l'idroelettrico"
    ),
    "86": (
        "Indica quale quota dei consumi interni lordi di elettricità è coperta "
        "da fonti rinnovabili, escluso l'idroelettrico"
    ),
    "373": (
        "Rapporta i consumi elettrici della pubblica amministrazione, espressi "
        "in GWh, a 100.000 unità di lavoro equivalenti a tempo pieno"
    ),
    "374": (
        "Rapporta i consumi elettrici per l'illuminazione pubblica, espressi in "
        "GWh, alla superficie dei centri abitati"
    ),
    "404": (
        "Indica quanti giorni durano in media i procedimenti civili ordinari di "
        "primo e secondo grado"
    ),
    "04BEC002": (
        "Misura quante volte il reddito complessivo del 20% più ricco supera "
        "quello del 20% più povero"
    ),
    "03LAV009-N22": (
        "Confronta il tasso di occupazione delle donne tra 25 e 49 anni con figli "
        "in età prescolare con quello delle donne della stessa età senza figli"
    ),
    "06POL012": (
        "Rapporta il numero di persone detenute ai posti regolamentari disponibili "
        "negli istituti di pena"
    ),
    "06POL012P": (
        "Rapporta il numero di persone detenute ai posti regolamentari disponibili "
        "negli istituti di pena"
    ),
    "10AMB002": (
        "Misura la quantità complessiva di materiali usati dal sistema economico e "
        "trasformati in emissioni, rifiuti, beni o infrastrutture"
    ),
    "12SER008": (
        "Misura l'offerta di trasporto pubblico locale moltiplicando i posti "
        "disponibili sui mezzi per i chilometri percorsi"
    ),
    "07SIC004": "Misura le rapine denunciate in rapporto alla popolazione",
    "SDG-3": "Misura il numero di medici in rapporto alla popolazione",
    "01SAL013": (
        "Misura la diffusione di un'alimentazione che rispetta il criterio "
        "definito dal sistema BES Istat"
    ),
    "01SAL009": (
        "Indica quante persone su 100 sono in eccesso di peso, usando un tasso "
        "corretto per confrontare popolazioni con età diverse"
    ),
    "01SAL010": (
        "Indica quante persone su 100 fumano, usando un tasso corretto per "
        "confrontare popolazioni con età diverse"
    ),
    "01SAL011": (
        "Indica la quota di persone associata al consumo di alcol secondo la "
        "definizione BES, con un tasso corretto per età"
    ),
    "01SAL012": (
        "Indica quante persone su 100 sono sedentarie, usando un tasso corretto "
        "per confrontare popolazioni con età diverse"
    ),
}


_TERM_REPLACEMENTS = (
    (r"\bSAU\b", "superficie agricola utilizzata"),
    (r"\bULA\b", "unità di lavoro equivalenti a tempo pieno"),
    (r"\bR&S\b", "ricerca e sviluppo"),
    (r"\bTPL\b", "trasporto pubblico locale"),
    (r"\bCLE\b", "Condizione limite per l'emergenza, CLE"),
    (r"\bICT\b", "tecnologie dell'informazione e della comunicazione"),
    (r"\bEPO\b", "Ufficio europeo dei brevetti, EPO"),
    (r"\bPA\b", "pubblica amministrazione"),
    (r"\bUL\b", "unità locali"),
    (r"\bEta\b", "età"),
    (r"\bGwh\b", "gigawattora, GWh"),
    (r"\bMw\b", "megawatt, MW"),
    (r"\bkmq\b", "chilometro quadrato"),
    (r"\bkm2\b", "km²"),
    (r"\bm2\b", "m²"),
    (r"\bm3\b", "m³"),
)


_FEMININE_SINGULAR = {
    "acqua", "associazione", "attività", "capacità", "competenza",
    "concentrazione", "copertura", "densità", "differenza", "difficoltà",
    "diffusione", "dispersione", "disponibilità", "durata", "energia",
    "emigrazione", "erosione", "età", "fiducia", "frazione", "frequenza",
    "fruizione", "impermeabilizzazione", "incidenza", "insoddisfazione",
    "intensità", "innovazione", "irregolarità", "lettura", "lunghezza",
    "dotazione", "imprenditorialità", "media", "mobilità", "mortalità",
    "multicronicità", "occupazione", "paura",
    "partecipazione", "percezione", "percentuale", "popolazione", "presenza",
    "pressione", "preoccupazione", "produzione", "propensione", "qualità",
    "quota", "raccolta", "rete", "retribuzione", "rinuncia", "sedentarietà",
    "situazione", "soddisfazione", "somma", "spesa", "speranza", "superficie",
    "tavola", "uscita", "variazione", "velocità", "violenza",
    "adeguata", "bassa", "grande", "grave",
}

_MASCULINE_SINGULAR = {
    "abusivismo", "affollamento", "alcol", "conferimento", "consumo", "divario",
    "differenziale", "eccesso", "export", "fumo",
    "finanziamento", "grado", "giudizio", "impatto", "importo", "indice",
    "numero", "passaggio", "peso", "pil", "rapporto", "reddito", "rischio",
    "part", "saldo", "servizio", "sovraccarico", "tasso", "tempo", "totale",
    "traffico", "trattamento", "valore", "verde", "punteggio", "prodotto",
}

_FEMININE_PLURAL = {
    "amministrazioni", "aree", "aziende", "coste", "donne", "emissioni",
    "competenze", "denunce", "dimissioni", "famiglie", "forze", "giornate",
    "importazioni", "imprese", "merci", "organizzazioni", "persone", "presenze",
    "rapine", "reti", "scuole", "spese", "strade", "tonnellate",
    "trasformazioni", "unità", "zone",
}

_MASCULINE_PLURAL_GLI = {
    "15enni", "abitanti", "addetti", "adulti", "alunni", "amministratori",
    "anziani", "ingressi", "investimenti", "impieghi", "occupati", "ospiti",
    "studenti", "utenti",
}

_MASCULINE_PLURAL_I = {
    "abbandoni", "bambini", "beni", "biglietti", "borseggi", "brevetti",
    "comuni", "consumi", "delitti", "dipendenti", "elementi", "furti",
    "gigawattora", "giorni",
    "giovani", "infermieri", "laureati", "lavoratori", "maschi", "medici",
    "megawatt", "metri", "minorenni", "minori", "omicidi", "passeggeri", "pensionati",
    "gwh", "mw", "postikm", "posti", "principi", "reati", "redditi",
    "rifiuti", "servizi", "siti", "stalli",
    "tempi", "valori", "visitatori",
}


THEME_CAVEATS = {
    "Ambiente, altro": "Da leggere insieme alla geografia fisica del territorio: montagne, coste, boschi e densità urbana cambiano molto il significato del confronto.",
    "Capitale sociale": "Non riassume da solo la qualità delle relazioni sociali, ma offre una traccia quantitativa di un fenomeno più ampio.",
    "Città": "Il dato regionale può nascondere differenze forti tra capoluoghi, aree interne e cinture metropolitane.",
    "Competitività": "Non basta per dire se un'economia sta bene: va affiancato a lavoro, salari, investimenti e struttura produttiva.",
    "Cultura": "Non misura tutta la vita culturale informale, gratuita o locale, ma solo la parte intercettata dalla fonte statistica.",
    "Demografia e popolazione": "I numeri vanno letti insieme: invecchiamento, fecondità e migrazioni si influenzano a vicenda e una sola cifra non racconta la traiettoria della popolazione.",
    "Salute": "La speranza di vita è un esito medio: non dice nulla sulle disuguaglianze interne né sulla qualità degli anni vissuti, e va affiancata a indicatori di servizi e prevenzione.",
    "Demografia di impresa": "Una variazione alta non è sempre positiva: può indicare vivacità, ma anche instabilità del tessuto produttivo.",
    "Dinamiche settoriali": "Il confronto funziona meglio se si tiene conto della specializzazione economica di partenza di ogni regione.",
    "Energia": "Un valore va interpretato insieme a clima, struttura industriale e mix produttivo, perché i fabbisogni non sono uguali ovunque.",
    "Inclusione sociale": "Il numero indica una condizione misurata, non racconta da solo cause, durata e qualità degli interventi disponibili.",
    "Internazionalizzazione": "Regioni con porti, grandi imprese o filiere esportatrici partono da condizioni molto diverse.",
    "Istruzione e formazione": "Il dato fotografa un pezzo del percorso educativo, ma non spiega da solo qualità dell'offerta, contesto familiare e opportunità locali.",
    "Lavoro": "Va letto insieme a inattività, qualità del lavoro e composizione per età e genere, altrimenti rischia di essere troppo sintetico.",
    "Legalità e sicurezza": "Le denunce e la percezione non coincidono sempre con i reati effettivi: contano fiducia, controlli e propensione a segnalare.",
    "Mercato dei capitali e finanza d'impresa": "Il dato non dice tutto sulla salute delle imprese, ma illumina il rapporto con credito, rischio e capitale.",
    "Pubblica Amministrazione": "Un valore medio può nascondere amministrazioni molto diverse dentro la stessa regione.",
    "Qualità dell'aria": "Le emissioni dipendono anche da industria, traffico, agricoltura e produzione energetica: il dato non va letto come colpa unica dei residenti.",
    "Reddito e ricchezza": "Il valore pro capite va letto insieme al costo della vita, alle disuguaglianze interne e alla redistribuzione, perché la media regionale nasconde differenze tra persone e tra aree.",
    "Ricerca ed innovazione": "Non tutta l'innovazione passa da spesa formale, brevetti o addetti R&S, ma questi segnali aiutano a vedere dove il sistema investe conoscenza.",
    "Rifiuti": "Il dato non racconta da solo prevenzione, qualità della raccolta o impianti disponibili, che possono cambiare molto il quadro.",
    "Risorse idriche": "Il confronto dipende da rete, morfologia, disponibilità naturale e investimenti storici nel servizio idrico.",
    "Servizi di cura": "La copertura del servizio non dice tutto su qualità, orari, costi e liste di attesa.",
    "Società dell'informazione": "La disponibilità di strumenti digitali non coincide sempre con competenze, uso effettivo e qualità dei servizi online.",
    "Trasporti e mobilità": "Va letto insieme alla forma del territorio: una regione dispersa, montana o insulare ha bisogni diversi da una grande area urbana.",
    "Turismo": "Non misura la spesa dei visitatori, la qualità dell'offerta o la distribuzione dei flussi tra città, costa e aree interne.",
}



LOWER_IS_BETTER = (
    "abbandono",
    "criminal",
    "deprivazione",
    "difficoltà",
    "dispersione",
    "disoccupazione",
    "discarica",
    "emigrazione ospedaliera",
    "furti",
    "gas serra",
    "grave deprivazione",
    "irregolarità",
    "microcriminalità",
    "neet",
    "omicidi",
    "povertà",
    "rapine",
    "rischio",
    "ritardo",
    "scarse competenze",
    "sovraffollamento",
)


HIGHER_IS_BETTER = (
    "accesso a internet",
    "banda",
    "brevett",
    "competenze elevate",
    "depurazione",
    "differenziata",
    "diplomati",
    "esport",
    "istruzione terziaria",
    "occupazione",
    "partecipazione",
    "rinnovabili",
    "scolarizzazione",
    "servizi pienamente interattivi",
)


# Curated direction overrides keyed by indicator id, for the "core" set used in the
# region profiles (complete + recent). The keyword heuristic in _direction() leaves
# many of these "contextual" or, worse, mislabels them (a gender employment gap is
# not "higher better"; energy covered by cogeneration/bioenergy is good, not bad).
# This map encodes the intended reading so the scoring stays honest. "higher_worse"
# and "lower_better" score identically (lower value = better); both are kept for the
# accuracy of the reading text.
CURATED_DIRECTION = {
    # Indagine Multiscopo, problemi strutturali dell'abitazione
    "MULTI_ABIT_INFISSI_FATISCENTI": "lower_better",
    "MULTI_ABIT_UMIDITA": "lower_better",
    # Competitività
    "158": "higher_better", "167": "higher_better", "471": "higher_better", "419": "higher_better",
    "115": "higher_better",  # servizi alle imprese sul totale dei servizi vendibili
    # Cultura (cultural participation / creative economy = positive; absence of offer = negative)
    "600": "higher_better", "611": "higher_better", "612": "higher_better", "27": "higher_better",
    "613": "higher_better", "610": "higher_better", "595": "higher_better", "614": "lower_better",
    "596": "higher_better", "594": "higher_better", "593": "higher_better", "25": "higher_better",
    # Demografia di impresa
    "242": "higher_better", "54": "higher_better",
    "157": "higher_better",  # saldo tra natalità e mortalità delle imprese
    # Dinamiche settoriali (labour productivity / growth = positive)
    "31": "higher_better", "1": "higher_better", "133": "higher_better", "130": "higher_better",
    "107": "higher_better", "123": "higher_better", "124": "higher_better", "250": "higher_better",
    # Energia (fix misclassification: energy covered by cogeneration/bioenergy is good)
    "378": "higher_better", "379": "higher_better",
    "437": "higher_worse",  # consumi energetici per unità di lavoro
    # Inclusione sociale (early school leaving = bad; accessible schools = good)
    "200": "lower_better", "199": "lower_better", "102": "lower_better",
    "641": "higher_better", "651": "higher_better", "647": "higher_better", "646": "higher_better",
    "645": "higher_better", "642": "higher_better", "643": "higher_better", "644": "higher_better",
    "650": "higher_better",
    # Un conteggio assoluto riflette anche la dimensione regionale: non va usato
    # per stabilire da solo quale territorio stia meglio.
    "285": "contextual",
    # Istruzione e formazione (education level / training participation = positive)
    "198": "higher_better", "197": "higher_better", "99": "higher_better", "77": "higher_better",
    "190": "higher_better", "189": "higher_better", "67": "higher_better",
    "188": "higher_better", "187": "higher_better", "63": "higher_better", "186": "higher_better",
    "185": "higher_better",
    "409": "contextual",  # quota di diplomati tecnici: composizione, non esito
    # 104 misura la popolazione 25-64 con AL PIÙ la licenza media: un valore alto è
    # sfavorevole (più adulti fermi a un titolo basso), quindi lower_better. Senza
    # questo override il nome "livello di istruzione" lo farebbe leggere al contrario.
    "104": "lower_better",
    # Competenze INVALSI/PISA: la quota di studenti che NON raggiungono un livello
    # sufficiente (617-626) è negativa, quindi lower_better (come 106/110 "scarse
    # competenze"); la quota con competenze elevate (111/112) è positiva. Senza
    # questi override l'euristica li lascia "contextual" e le pagine/i profili non
    # esprimono la direzione, pur essendo interpretabile senza ambiguità.
    "617": "lower_better", "618": "lower_better", "619": "lower_better",
    "620": "lower_better", "621": "lower_better", "622": "lower_better",
    "623": "lower_better", "624": "lower_better", "625": "lower_better",
    "626": "lower_better",
    "111": "higher_better", "112": "higher_better",
    # Lavoro (fix gender-gap indicators to lower_better; activity/entrepreneurship = positive)
    "398": "higher_better", "466": "higher_better", "61": "lower_better", "57": "lower_better",
    "402": "higher_better", "401": "higher_better", "203": "higher_better", "213": "higher_better",
    "530": "contextual",  # beneficiari di sussidi: bisogno e copertura si sovrappongono
    # Ricerca ed innovazione
    "396": "higher_better", "397": "higher_better", "417": "higher_better",
    "432": "higher_better", "93": "higher_better", "114": "higher_better",
    "416": "higher_better", "150": "higher_better", "148": "higher_better",
    # Mercato dei capitali (venture / "capitale di rischio" investment is positive;
    # the word "rischio" otherwise trips the lower-is-better heuristic)
    "163": "higher_better", "164": "higher_better",
    # Rifiuti (composting = good)
    "53": "higher_better",
    # Servizi di cura (childcare availability/coverage = good)
    "142": "higher_better", "414": "higher_better",
    "415": "higher_better", "144": "higher_better",
    # Società dell'informazione (digital uptake = positive)
    "426": "higher_better", "64": "higher_better", "72": "higher_better", "70": "higher_better",
    "434": "higher_better", "427": "higher_better", "469": "higher_better",
    # Trasporti e mobilità (rail / public transport use = positive)
    "47": "higher_better", "268": "higher_better", "269": "higher_better",
    "438": "higher_better",
    # Ambiente e territorio
    "255": "lower_better", "514": "lower_better",  # superficie percorsa dal fuoco
    "592": "higher_better",  # verde urbano disponibile
    "384": "higher_better",  # procedimenti di bonifica conclusi
    "523": "higher_better",  # occupazione nei settori ad alta conoscenza
    "244": "higher_better",  # capacità di attrarre studenti da altre regioni
    # Reddito e ricchezza (conti economici territoriali: higher GDP/income per head = better)
    "901": "higher_better", "902": "higher_better", "903": "higher_better",
    "904": "higher_better", "905": "higher_better", "906": "higher_better",
    # Salute (speranza di vita: piu alta e meglio)
    "910": "higher_better", "911": "higher_better", "912": "higher_better", "913": "higher_better",
    # Disuguaglianza (indice di Gini: piu basso e meglio)
    "930": "lower_better",
}


def direction_for(indicator_id, name):
    """Curated direction if available, otherwise the keyword heuristic."""
    return CURATED_DIRECTION.get(str(indicator_id)) or _direction(name)


# --- SEO metadata helpers -------------------------------------------------
# Indicator names come verbatim from Istat and are often very long (up to ~180
# chars). Concatenated with " per regione (anni) · site" they produce SERP
# titles and descriptions well past the ~60/155 char budgets, so Google
# truncates them. These helpers build a compact, still-unique title and a
# specific (data-derived) description within budget. They are page-only: the
# atlas API keeps consuming the full name and the explain text unchanged.

_TITLE_MAX = 60
_DESC_MAX = 155
_TITLE_TAIL = " per regione"
# Trailing connector words that must never end a truncated title (would read like
# "...della per regione" or the double "per per regione").
_TRAILING_STOP = {
    "per", "di", "del", "della", "dei", "delle", "degli", "e", "ed", "a", "ad",
    "da", "dal", "dalla", "in", "nel", "nella", "su", "sul", "con", "tra", "fra",
    "il", "lo", "la", "i", "gli", "le", "un", "una", "uno", "che", "al", "allo",
    "alla", "ai", "agli", "alle", "sui", "come", "non", "o",
}


def _truncate_words(text, budget, add_period=False):
    """Trim to at most `budget` chars on a word boundary (no ellipsis char).

    Drops trailing punctuation and dangling connector words so the cut reads as a
    finished fragment rather than a mid-phrase stub.
    """
    text = (text or "").strip()
    if len(text) <= budget:
        cut = text
    else:
        cut = text[:budget].rsplit(" ", 1)[0]
    cut = cut.rstrip(" ,.;:-(")
    words = cut.split()
    while words and words[-1].lower() in _TRAILING_STOP:
        words.pop()
    cut = " ".join(words).rstrip(" ,.;:-(")
    if add_period and cut and not cut.endswith("."):
        cut = cut + "."
    return cut


def _variant_marker(name, extra=None):
    """Keep a compact parenthetical so sibling indicator titles stay unique.

    `extra`, when given (e.g. a source qualifier for a BES id that duplicates a
    territorial series, see `DUPLICATE_BES_IDS`), is folded into the same
    parenthetical instead of stacking a second one.
    """
    def _wrap(parts):
        joined = _truncate_words(", ".join(p for p in parts if p), 40)
        return f" ({joined})" if joined else ""

    low = (name or "").lower()
    for marker in ("femmine", "maschi", "totale"):
        if f"({marker})" in low:
            return _wrap([marker, extra])
    groups = re.findall(r"\(([^()]*)\)", name or "")
    # A "pari a N" clause (e.g. a satisfaction-level scale, one page per point)
    # sits at the end of the name, right before a scale parenthetical shared by
    # every sibling ("(scala 0-10)"): that shared parenthetical alone made all
    # of them collapse onto the same truncated title. Fold the level into the
    # marker itself, ahead of the truncatable core, so it survives the cut.
    level_match = re.search(r"\bpari a (\d+)\b", name or "", flags=re.I)
    if level_match:
        level = f"livello {level_match.group(1)}"
        return _wrap([level, groups[-1] if groups else None, extra])
    if groups:
        marker = groups[-1]
        marker = re.sub(r"studenti classi?\s+", "classe ", marker, flags=re.I)
        marker = re.sub(r"scuola secondaria primo grado", "secondaria I grado", marker, flags=re.I)
        marker = re.sub(r"scuola secondaria secondo grado", "secondaria II grado", marker, flags=re.I)
        marker = _truncate_words(marker, 27)
        return _wrap([marker, extra])
    return _wrap([extra])


def _short_name_for_title(name):
    n = re.sub(r"^TAVOLA DISMESSA\s*-\s*", "", name or "", flags=re.I).strip()
    # Drop parentheticals; the gender/total marker is re-added separately so it
    # survives truncation instead of being cut off with the tail of a long name.
    n = re.sub(r"\s*\([^)]*\)", "", n)
    # Same for a trailing "pari a N" (a scale level): _variant_marker() carries
    # it instead, so it is not left dangling at the end of a name long enough
    # to be truncated before reaching it.
    n = re.sub(r"\s*\bpari a \d+\s*$", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip()


def _compact_title(core, marker, max_len):
    combined = f"{core}{marker}"
    if len(combined) <= max_len:
        return combined
    if marker:
        return f"{_truncate_words(core, max_len - len(marker))}{marker}"

    words = core.split()
    tail_words = words[-4:]
    while len(" ".join(tail_words)) > 24 and len(tail_words) > 1:
        tail_words.pop(0)
    tail = " ".join(tail_words).rstrip(" ,.;:-")
    separator = " ("
    head = _truncate_words(core, max_len - len(separator) - len(tail) - 1)
    dangling = {"a", "al", "alla", "da", "dal", "dalla", "di", "del", "della", "dei", "delle", "e", "in", "nei", "nelle", "per", "tra", "fra"}
    head_words = head.split()
    while len(head_words) > 1 and head_words[-1].lower() in dangling:
        head_words.pop()
    head = " ".join(head_words)
    if not head or tail.lower() in head.lower():
        return _truncate_words(core, max_len)
    return f"{head}{separator}{tail})"


def meta_description_from_attacco(attacco, max_len=_DESC_MAX):
    """Turn an analyst-note lead (the visible page opener, with real regional
    numbers) into a SERP meta description, trimmed to budget on a word boundary.

    Prefers this over the procedural description because it carries concrete
    figures that lift click-through, and it is the same text already visible on
    the page (so structured/visible content stay consistent). Markdown links are
    flattened to their label and any residual markup is dropped."""
    text = (attacco or "").strip()
    if not text:
        return ""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"[*_`]", "", text)                       # stray markdown emphasis
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    # Keep whole sentences that fit; fall back to a clean word-boundary cut.
    sentences = re.split(r"(?<=\.)\s+", text)
    kept = ""
    for sentence in sentences:
        candidate = f"{kept} {sentence}".strip() if kept else sentence
        if len(candidate) <= max_len:
            kept = candidate
        else:
            break
    return kept or _truncate_words(text, max_len, add_period=True)


def seo_title(name, site_name="Divario Italia", max_len=_TITLE_MAX, source_qualifier=None):
    """Compact SERP title: shortened name + variant marker + 'per regione'.

    `source_qualifier`, when given, disambiguates a name that another
    indicator also carries (see `app.taxonomy.DUPLICATE_BES_IDS`), so the two
    pages do not compete on an identical SERP title."""
    marker = _variant_marker(name, extra=source_qualifier)
    core = _short_name_for_title(name) or (name or "").strip()
    core = core.rstrip(" ,.;:-(")  # a trailing comma/colon must not sit before the tail
    suffix = f" · {site_name}"
    with_tail = f"{core}{marker}{_TITLE_TAIL}"
    # Short names: keep the "per regione" intent cue, add the brand if it still fits.
    if len(with_tail) + len(suffix) <= max_len:
        return with_tail + suffix
    if len(with_tail) <= max_len:
        return with_tail
    # Long names: the name itself already carries the intent and, for sibling
    # indicators, the distinguishing tail (agricoltura vs industria, assenza vs
    # presenza). Spend the budget on the name, not on the " per regione" boilerplate.
    body = f"{core}{marker}"
    if len(body) <= max_len:
        return body
    return _compact_title(core, marker, max_len)


def seo_description(
    plain,
    year_max,
    region_count,
    max_len=_DESC_MAX,
    name="",
    territory_label="regioni",
):
    """SERP description from the data-derived plain text: keep whole sentences that
    fit, then append the data vintage. Never cut a sentence to a dangling stub."""
    base = (plain or "").strip()
    # Keep the provenance compact so the explanation, which is the useful part
    # for the reader and for search intent, can remain a complete sentence.
    tail = f" Dati Istat: {region_count} {territory_label}, al {year_max}."
    prefix = (
        f"{_compact_title(_short_name_for_title(name), _variant_marker(name), 58)}: "
        if name else ""
    )
    room = max_len - len(tail)
    # Add the indicator name only when the first explanatory sentence still fits
    # in full. The title already names the indicator, so clarity wins over
    # repetition in tighter snippets.
    first_sentence = re.split(r"(?<=\.)\s+", base)[0] if base else ""
    if prefix and len(prefix) + len(first_sentence) <= room:
        room -= len(prefix)
    else:
        prefix = ""
    sentences = re.split(r"(?<=\.)\s+", base) if base else []
    kept = ""
    for sentence in sentences:
        candidate = f"{kept} {sentence}".strip() if kept else sentence
        if len(candidate) <= room:
            kept = candidate
        else:
            break
    if not kept:
        # A clipped statistical definition can change meaning or leave a broken
        # phrase. For long definitions use a complete, search-specific fallback
        # and leave the full explanation to the visible page section.
        compact_name = _compact_title(
            _short_name_for_title(name) or name or "Indicatore",
            _variant_marker(name),
            78,
        )
        return (
            f"{compact_name}: cosa misura e confronto tra "
            f"{region_count} {territory_label}. Dati Istat al {year_max}."
        )[:max_len].rstrip(" ,.;:-") + "."
    return prefix + kept + tail


def build_indicator_explain(item):
    name = _clean(item.get("indicator") or item.get("name"))
    theme = _clean(item.get("theme"))
    unit = _clean(item.get("unit"))
    archive = _clean(item.get("archive"))
    indicator_id = str(item.get("id", ""))
    base_name = _display_name(name)
    lens = _lens(name)
    direction = direction_for(indicator_id, name)

    plain = _plain_text(base_name, theme, archive, unit, indicator_id)
    return {
        "plain": plain,
        "example": _unit_explanation(name, unit, archive),
        "scope": _scope_text(name, "territori regionali", archive),
        "reading": _reading_text(name, theme, unit, direction),
        "caveat": _caveat_text(name, theme, lens),
        "direction": direction,
    }


def build_bes_indicator_explain(item, level="territori"):
    """Spiegazione comune a catalogo BES, pagine pubbliche e quiz."""
    name = _clean(item.get("name") or item.get("indicator"))
    unit = display_unit(item.get("unit"))
    theme = _clean(item.get("domain_name") or item.get("theme"))
    indicator_id = str(item.get("id", ""))
    direction = item.get("direction") or direction_for(indicator_id, name)
    return {
        "plain": _bes_plain_text(name, unit, indicator_id),
        "example": _unit_explanation(name, unit),
        "scope": _scope_text(name, level, name),
        "reading": _reading_text(name, theme, unit, direction),
        "caveat": _bes_caveat(unit, level),
        "direction": direction,
    }


def _bes_plain_text(name, unit, indicator_id):
    """Turn the BES label and unit into an explanation, not a label echo."""
    override = PLAIN_DEFINITION_OVERRIDES.get(indicator_id)
    if override:
        return _finish_sentence(override)

    subject = _expand_terms(name)
    lowered_unit = unit.lower().replace("²", "2").replace("³", "3")
    with_article = _with_article(subject)

    if "puntegg" in lowered_unit or "standardizz" in lowered_unit and "tass" not in lowered_unit:
        return _finish_sentence(
            f"Riassume {with_article} in un punteggio riportato su una scala comune, utile per confrontare territori diversi"
        )
    if "valor" in lowered_unit and "percent" in lowered_unit or lowered_unit.strip() == "%":
        return _finish_sentence(
            f"Esprime come percentuale {with_article} nel gruppo di riferimento definito dalla fonte"
        )

    rate_match = re.search(r"per\s+([\d\.]+|milione)\s+(.+)", lowered_unit)
    if rate_match:
        denominator = f"{rate_match.group(1)} {rate_match.group(2)}".strip()
        denominator = denominator.replace("km2", "km²").replace("m2", "m²").replace("m3", "m³")
        standardised = " Il tasso è inoltre corretto per rendere confrontabili popolazioni con età diverse." if "standardizz" in lowered_unit else ""
        return (
            _finish_sentence(
                f"Rapporta {with_article} a {denominator}, così territori di dimensioni diverse sono confrontabili"
            )
            + standardised
        )
    if "numero medio di anni" in lowered_unit or lowered_unit in {"età media", "eta media"}:
        return _finish_sentence(f"Esprime in anni {with_article} come valore medio per il gruppo osservato")
    if "numero di giorni" in lowered_unit:
        return _finish_sentence(f"Esprime in giorni {with_article} nel periodo osservato")
    if "euro" in lowered_unit:
        qualifier = "pro capite" if "pro capite" in lowered_unit else "nel perimetro medio definito dalla fonte"
        return _finish_sentence(f"Esprime in euro {with_article}, {qualifier}")
    if "valore medio" in lowered_unit or "numero medio" in lowered_unit:
        return _finish_sentence(f"Riporta il valore medio di {subject} per il gruppo osservato")
    if unit:
        return _finish_sentence(
            f"Esprime {with_article} nell'unità usata dalla fonte, {unit}"
        )
    return _finish_sentence(f"Misura {with_article}")


def _plain_text(name, theme, archive, unit, indicator_id):
    # L'archivio Istat contiene quasi sempre la definizione più precisa. La
    # riportiamo direttamente, senza alternare verbi ornamentali scelti in base
    # all'id ("racconta", "osserva", "mette a fuoco"), che rendevano le schede
    # artificiose e in alcuni casi poco grammaticali.
    override = PLAIN_DEFINITION_OVERRIDES.get(indicator_id)
    if override:
        return _finish_sentence(override)

    subject = _expand_terms(_subject_from_archive(archive) or name)
    subject = subject.replace("puo'", "può").replace("piu'", "più")
    if len(subject) < 8 or subject.startswith("("):
        subject = name
    return _finish_sentence(f"Misura {_with_article(subject)}")


def _scope_text(name, level, definition=""):
    lowered = f"{name} {definition}".lower()
    focus = ""
    has_female = "femmine" in lowered or "donne" in lowered or "femminile" in lowered
    has_male = "maschi" in lowered or "uomini" in lowered or "maschile" in lowered
    age_match = re.search(r"(?:tra\s+|in età\s+)?(\d+)\s*-\s*(\d+)\s*anni", lowered)
    if has_female and has_male:
        focus = " Il perimetro comprende sia la popolazione femminile sia quella maschile indicate nella definizione."
    elif has_female:
        focus = " Il perimetro riguarda la popolazione femminile indicata nel nome."
    elif has_male:
        focus = " Il perimetro riguarda la popolazione maschile indicata nel nome."
    if age_match:
        focus += (
            f" La fascia da {age_match.group(1)} a {age_match.group(2)} anni fa parte "
            "della definizione e non va estesa ad altri gruppi."
        )
    elif re.search(r"\d+ anni e più|\d+ anni e meno", lowered):
        focus += " La fascia di età indicata nella definizione non va estesa ad altri gruppi."
    territory_phrase = {
        "regioni": "in tutte le regioni",
        "province": "in tutte le province",
        "regioni e province": "in tutte le regioni e le province",
        "territori regionali": "in tutti i territori regionali",
        "territori": "in tutti i territori",
    }.get(level, f"nei territori indicati, {level}")
    return f"Il confronto applica la stessa definizione {territory_phrase} e per ciascun anno.{focus}"


def _percentage_denominator(definition):
    """Extract a readable denominator from common Istat percentage definitions."""
    text = _clean(definition).rstrip(" .")
    patterns = (
        r"in percentuale\s+(dell'|della|delle|degli|dei|del|sull'|sulla|sulle|sugli|sui|sul|al|alla)\s+(.+)",
        r"\b(sull'|sulla|sulle|sugli|sui|sul|su)\s+(.+?)(?:\s*\([^)]*\))?$",
        r"\brispetto\s+(al|alla)\s+(.+?)(?:\s*\([^)]*\))?$",
    )
    article = {
        "dell'": "dell'",
        "della": "della ",
        "delle": "delle ",
        "degli": "degli ",
        "dei": "dei ",
        "del": "del ",
        "sull'": "dell'",
        "sulla": "della ",
        "sulle": "delle ",
        "sugli": "degli ",
        "sui": "dei ",
        "sul": "del ",
        "su": "di ",
        "al": "del ",
        "alla": "della ",
    }
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue
        denominator = match.group(2)
        denominator = re.sub(r"\s*\([^)]*\)\s*$", "", denominator).strip(" .,;")
        if denominator:
            return article[match.group(1).lower()] + denominator
    return ""


def _unit_explanation(name, unit, definition=""):
    lowered_name = name.lower()
    lowered_unit = unit.lower().replace("²", "2").replace("³", "3")
    lowered_definition = definition.lower()
    lowered_context = f"{lowered_name} {lowered_definition}"

    if "s80/s20" in lowered_name:
        return "Un valore di 5 significa che il reddito del 20% più ricco è cinque volte quello del 20% più povero."
    if "rapporto tra i tassi di occupazione" in lowered_name:
        return "Un valore di 100 indica due tassi uguali. Sotto 100, il tasso delle donne con figli è più basso."
    if "differenza tra tasso" in lowered_context or "differenza assoluta fra tasso" in lowered_context or "differenza tra il tasso" in lowered_context:
        return "Un valore di 5 indica che i due tassi differiscono di 5 punti percentuali."
    if "variazione rispetto all'anno precedente" in lowered_context:
        return "Un valore di 5 indica una variazione del 5% rispetto all'anno precedente."
    if "parcheggi di corrispondenza" in lowered_name:
        return "Un valore di 12 indica 12 stalli ogni 1.000 autovetture circolanti."
    if "densità di verde storico" in lowered_name:
        return "Un valore di 12 indica 12 m² di verde storico ogni 100 m² della superficie di riferimento."
    if "puntegg" in lowered_unit and "standardizz" in lowered_unit:
        return "È un punteggio riportato su una scala comune: serve per confrontare territori e anni, non come conteggio assoluto."
    per_match = re.search(
        r"(?:numero\s+|valori\s+|tassi?\s+standardizzati?\s+)?per\s+"
        r"(cento|mille|centomila|milione|100|1[\. ]?000|10[\. ]?000|100[\. ]?000)\s+(.+)",
        lowered_unit,
    )
    if per_match is None:
        per_match = re.fullmatch(
            r"(cento|mille|centomila|milione|100|1[\. ]?000|10[\. ]?000|100[\. ]?000)\s+(.+)",
            lowered_unit,
        )
    if per_match:
        raw_base = per_match.group(1).replace(".", "").replace(" ", "")
        base_map = {
            "cento": "100",
            "mille": "1.000",
            "centomila": "100.000",
            "milione": "1.000.000",
        }
        base = base_map.get(raw_base)
        if base is None:
            base = f"{int(raw_base):,}".replace(",", ".")
        denominator = (
            per_match.group(2).strip().replace("km2", "km²").replace("m2", "m²").replace("m3", "m³")
        )
        prefix = lowered_unit[: per_match.start()].strip()
        quantity = {
            "gwh": "GWh",
            "tonnellate": "tonnellate",
            "chilometro": "chilometri",
        }.get(prefix, "casi")
        explanation = f"Un valore di 12 corrisponde a 12 {quantity} ogni {base} {denominator}."
        if "standardizz" in lowered_unit or "standardizz" in lowered_name:
            explanation += " Il tasso è corretto per confrontare popolazioni con una diversa struttura per età."
        return explanation
    if re.fullmatch(r"valori\s+per\s+1[\. ]?000", lowered_unit):
        return "Un valore di 12 indica 12 casi ogni 1.000 unità del gruppo definito dalla fonte."
    if re.search(r"(^|\s)%($|\s)", lowered_unit) or "percentual" in lowered_unit:
        per_hundred = re.search(r"\bper\s+100\s+(.+?)(?:\s*\([^)]*\))?$", definition, flags=re.I)
        if per_hundred:
            denominator = re.sub(r"\s+\(.*$", "", per_hundred.group(1)).strip(" .,;")
            return f"Un valore di 20 indica 20 casi ogni 100 {denominator}."
        denominator = _percentage_denominator(definition)
        if denominator:
            return f"Un valore di 20 indica che il fenomeno misurato equivale al 20% {denominator}."
        return "Un valore di 20 indica che la condizione descritta riguarda 20 unità ogni 100 nel gruppo di riferimento."
    if "standardizz" in lowered_unit or "standardizz" in lowered_name:
        return "Il tasso è corretto per rendere più confrontabili territori con una diversa struttura della popolazione."
    if "tasso specifico di coorte" in lowered_unit:
        return "Il valore confronta le persone che compongono la stessa generazione o fascia di ingresso, seguendone il percorso nel tempo."
    if "gini" in lowered_name and "0-1" in lowered_unit:
        return "L'indice va da 0 a 1: valori vicini a 0 indicano redditi più uniformi, valori vicini a 1 una maggiore disuguaglianza."
    if "co2" in lowered_unit and "emission" in lowered_name:
        return "Le emissioni sono espresse in CO2 equivalente, così gas diversi possono essere confrontati in base al loro effetto sul clima."
    if "posti-km" in lowered_unit:
        return "Il valore combina i posti disponibili sui mezzi con i chilometri percorsi e li rapporta agli abitanti."
    if "microgrammi per m3" in lowered_unit:
        return "Il valore indica quanti microgrammi di inquinante sono presenti in media in un metro cubo d'aria."
    if "m2 per abitante" in lowered_unit or "metri quadrati per abitante" in lowered_unit:
        return "Il valore indica quanti metri quadrati sono disponibili in media per ogni abitante."
    if "per abitante" in lowered_unit or "pro capite" in lowered_unit or "per abitante" in lowered_name:
        return "Il totale è diviso per il numero di abitanti, così territori grandi e piccoli sono più confrontabili."
    if "per km" in lowered_unit or "per chilometro quadrato" in lowered_unit:
        return "Il valore rapporta il fenomeno alla superficie del territorio, non al numero di abitanti."
    if "euro" in lowered_unit:
        if "prezzi correnti" in lowered_unit:
            return "Sono euro dell'anno osservato, non corretti per l'inflazione."
        if "pro capite" in lowered_unit or "per abitante" in lowered_unit:
            return "Il valore indica quanti euro corrispondono in media a ogni abitante."
        if "migliaia" in lowered_unit:
            return "Un valore di 12 equivale a 12.000 euro nel perimetro indicato dalla fonte."
        if "milioni" in lowered_unit:
            return "Un valore di 12 equivale a 12 milioni di euro nel perimetro indicato dalla fonte."
        return "Il valore è espresso in euro. Il nome dell'indicatore specifica se si tratta di un totale, una media o un dato per abitante."
    if "anno" in lowered_unit or "anni" in lowered_unit:
        return "Il valore indica un numero medio di anni, non la durata garantita per ogni persona."
    if lowered_unit in {"età media", "eta media"}:
        return "Il valore indica l'età media del gruppo osservato, non l'età di ogni singola persona."
    if "numero medio per utente" in lowered_unit:
        return "Il valore indica il numero medio di eventi registrati per ciascun utente, non il totale complessivo."
    if lowered_unit == "numero medio":
        return "Il valore è una media, non un conteggio totale."
    if "giorn" in lowered_unit:
        return "Il valore conta i giorni associati al fenomeno nel periodo osservato."
    if lowered_unit == "minuti" or "ore, minuti, secondi" in lowered_unit:
        return "Il valore esprime il tempo necessario: più aumenta, più lunga è l'attesa o il percorso misurato."
    if "km/ora" in lowered_unit:
        return "Il valore indica la velocità media in chilometri orari."
    if "valore medio" in lowered_unit:
        return "È un punteggio medio: riassume le risposte del gruppo osservato e serve per confrontare territori e anni."
    if "puntegg" in lowered_unit or "numero indice" in lowered_unit:
        return "È un punteggio sintetico: serve soprattutto per confrontare territori e anni sulla stessa scala."
    if "rapporto" in lowered_unit or "numero puro" in lowered_unit:
        return "È un rapporto tra due quantità, non una percentuale o un conteggio di persone."
    if lowered_unit in {"numero", "classi", "ettari", "giornate", "metri quadrati", "quintali"}:
        return "È un valore assoluto: la dimensione del territorio può influire sul confronto con le altre regioni."
    if any(token in lowered_unit for token in ("milioni", "migliaia", "tonnellate", "quintali", "gwh")):
        return "È un valore assoluto o di intensità: la dimensione del territorio e dell'economia può influire sul confronto."
    if unit:
        return f"La fonte esprime il dato in {unit}. Il confronto è valido solo usando la stessa unità e lo stesso perimetro."
    return "La fonte non specifica un'unità leggibile: il valore va interpretato insieme alla definizione originale."


def _reading_text(name, theme, unit, direction=None):
    lowered = name.lower()
    if direction is None:
        direction = _direction(name)

    if "differenza tra tasso" in lowered:
        return "Valori più alti indicano un divario più ampio tra uomini e donne. In questo caso la distanza conta più del livello complessivo del mercato del lavoro."
    if "tavola dismessa" in lowered:
        return "La serie è utile soprattutto come memoria storica. Va confrontata con attenzione con indicatori più recenti, perché la tavola non appartiene più al set corrente."
    if "standardizzato" in unit.lower() or "punteggio" in unit.lower():
        return "Il valore è un punteggio confrontabile tra territori. La distanza tra regioni conta più del numero preso da solo."
    if direction == "lower_better":
        return "Per questo indicatore il valore più basso occupa la posizione migliore. La graduatoria è quindi ordinata dal dato minore al maggiore."
    if direction == "higher_better":
        return "Per questo indicatore il valore più alto occupa la posizione migliore. La graduatoria è quindi ordinata dal dato maggiore al minore."
    if direction == "higher_worse":
        return "Un valore alto segnala maggiore pressione o consumo. La graduatoria assegna quindi la posizione migliore al valore più basso."
    if theme in ("Turismo", "Trasporti e mobilità", "Cultura"):
        return "Valori più alti indicano maggiore intensità del fenomeno. Possono essere un punto di forza, ma anche una pressione da gestire."
    if theme in ("Energia", "Competitività", "Dinamiche settoriali"):
        return "Valori più alti indicano maggiore intensità economica o produttiva. Il giudizio dipende dal tipo di risorsa usata e dal risultato che produce."
    return "Non esiste una direzione univoca: un valore alto descrive una maggiore intensità del fenomeno, non una regione automaticamente migliore o peggiore."


def trend_framing(direction, avg_change_pct):
    """Short qualitative fragment (no numbers) describing whether a national
    average's movement reads as favorable, unfavorable, or neutral, given the
    indicator's direction. Returns '' if avg_change_pct is None (caller must guard
    rendering on that)."""
    if avg_change_pct is None:
        return ""
    if abs(avg_change_pct) < 1:
        return "un andamento sostanzialmente stabile"
    if direction not in ("higher_better", "lower_better", "higher_worse"):
        return "un aumento" if avg_change_pct > 0 else "una diminuzione"
    favorable = (direction == "higher_better" and avg_change_pct > 0) or (
        direction in ("lower_better", "higher_worse") and avg_change_pct < 0
    )
    return "una variazione media favorevole" if favorable else "una variazione media sfavorevole"


def it_plural(count, singular, plural):
    """Pick the Italian singular or plural form for a count. Shared by the Python
    prose helpers and the `it_plural` Jinja filter, so a count of 1 never reads as
    "1 regioni" / "1 territori" and verbs agree ("supera" vs "superano")."""
    try:
        n = abs(int(count))
    except (TypeError, ValueError):
        return plural
    return singular if n == 1 else plural


def is_percentage_unit(unit):
    """Se l'unita' e' una percentuale, non un tasso su base cento.

    La distinzione sembra pedante e non lo e': da qui esce l'etichetta stampata
    accanto a ogni cifra e la parola usata per ogni variazione. Il test cercava
    la sottostringa "per cento", che compare dentro **"per centomila"**: cosi'
    "numero per centomila abitanti" passava per percentuale, e la pagina del
    tasso di omicidi diceva "0,54%" e "0,93 punti percentuali" su un tasso ogni
    centomila. Dodici indicatori ne erano toccati, fra cui "tonnellate per cento
    abitanti" e "chilometro per cento chilometri quadrati", che percentuali non
    sono in nessun senso.

    Percentuale e' `%` (anche "% del PIL") o "percentuale". "X per cento Y" e'
    un rapporto: quante X ogni cento Y. Solo un "per cento" in fondo, senza
    niente misurato dopo, e' davvero una percentuale.
    """
    lowered = (unit or "").strip().lower()
    if "%" in lowered or "percentual" in lowered:
        return True
    return lowered.endswith("per cento")


def value_unit_label(name, unit):
    lowered_name = (name or "").lower()
    if is_percentage_unit(unit):
        if "differenza tra tasso" in lowered_name or "differenza assoluta fra tasso" in lowered_name:
            return "punti percentuali"
        return "%"
    return rate_label(unit) or "valore"


def rate_label(unit):
    """L'unita' come si legge accanto a una cifra, non come sta nel CSV.

    Le unita' Istat sono descrizioni, non etichette: "numero per centomila
    abitanti" letto dopo un valore da "0,54 numero per centomila abitanti", che
    e' corretto e non e' italiano. La forma naturale e' "0,54 ogni centomila
    abitanti".

    Solo presentazione: il CSV non si tocca, come per le altre correzioni in
    `display_unit`.
    """
    value = display_unit(unit)
    if not value:
        return value
    # "numero per cento(mila) X" -> "ogni cento(mila) X". Il "numero" iniziale e'
    # gia' detto dalla cifra che precede l'etichetta.
    value = re.sub(r"^numero\s+per\s+", "ogni ", value, flags=re.I)
    # "tonnellate per cento abitanti" -> "tonnellate ogni cento abitanti": qui la
    # quantita' misurata serve, cambia solo la preposizione.
    value = re.sub(r"\bper\s+(cento(?:mila)?\s+\S)", r"ogni \1", value, flags=re.I)
    return value

def change_unit_label(name, unit):
    if is_percentage_unit(unit):
        return "punti percentuali"
    return value_unit_label(name, unit)


def annual_change_framing(name, direction, delta):
    """Interpret a mean movement without adding causal claims."""
    if delta is None:
        return ""
    if abs(delta) < 1e-12:
        return "La media è rimasta invariata."
    # "aumento" is masculine, "diminuzione" feminine: keep the article agreeing.
    indef_movement = "un aumento" if delta > 0 else "una diminuzione"
    def_movement = "L'aumento" if delta > 0 else "La diminuzione"
    lowered_name = (name or "").lower()
    if "differenza tra tasso" in lowered_name or "differenza assoluta fra tasso" in lowered_name:
        outcome = "si è ampliato" if delta > 0 else "si è ridotto"
        return f"{def_movement} indica che il divario medio tra i due tassi {outcome}."
    if direction not in ("higher_better", "lower_better", "higher_worse"):
        return (
            f"Il dato descrive {indef_movement}, ma non indica da solo un "
            "miglioramento o un peggioramento."
        )
    favorable = (direction == "higher_better" and delta > 0) or (
        direction in ("lower_better", "higher_worse") and delta < 0
    )
    outcome = "favorevole" if favorable else "sfavorevole"
    return f"Per la direzione di questo indicatore, il movimento medio è {outcome}."


def _caveat_text(name, theme, lens):
    lowered = name.lower()
    if "maschi" in lowered or "femmine" in lowered:
        return "Il taglio per genere è prezioso, ma va confrontato con il totale e con la struttura per età della popolazione."
    if "totale" in lowered and theme in ("Lavoro", "Istruzione e formazione", "Inclusione sociale"):
        return "Il totale è una buona sintesi, ma può nascondere differenze forti tra uomini, donne, giovani e adulti."
    if "tavola dismessa" in lowered:
        return "Essendo una tavola dismessa, serve più per ricostruire una traiettoria che per descrivere da sola la situazione attuale."
    if "per abitante" in lowered or "per cento abitanti" in lowered:
        return "Il rapporto per abitante rende confrontabili territori grandi e piccoli, ma non dice dove il fenomeno si concentra dentro la regione."
    if lens:
        return f"{THEME_CAVEATS.get(theme, 'Va letto insieme ad altri indicatori dello stesso tema.')} {lens}"
    return THEME_CAVEATS.get(theme, "Va letto insieme ad altri indicatori dello stesso tema, per evitare conclusioni troppo rapide.")


def _bes_caveat(unit, level):
    lowered = unit.lower()
    if any(token in lowered for token in ("milioni", "migliaia", "tonnellate", "quintali")):
        first = "Il valore assoluto risente della dimensione demografica ed economica del territorio. "
    elif "medio" in lowered or "media" in lowered:
        first = "La media può nascondere differenze importanti tra persone e aree dello stesso territorio. "
    elif "%" in lowered or "percentual" in lowered:
        first = "La percentuale non mostra da sola quante persone o unità siano coinvolte in valore assoluto. "
    else:
        first = "Il dato va letto insieme a unità di misura, anno e copertura. "
    return first + f"Il confronto tra {level} descrive una differenza osservata, ma non ne dimostra le cause."


def _subject_from_archive(archive):
    if not archive:
        return ""
    text = re.sub(r"^TAVOLA DISMESSA\s*-\s*", "", archive.strip().rstrip("."), flags=re.I)
    text = re.sub(r"\.?\s*Indicatori demografici Istat\.?$", "", text, flags=re.I)
    text = re.sub(r"\s*\([^)]*percentuale[^)]*\)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s*\([^)]*valori?[^)]*\)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {
        "percentuale",
        "numero",
        "valori percentuali",
        "punteggio standardizzato",
        "punteggio standadizzato",
        "giornate",
    }:
        return ""
    if re.fullmatch(r"per (mille|centomila|[\d.]+) (abitanti|persone|occupati)", text, flags=re.I):
        return ""
    if not text:
        return ""
    return text[0].lower() + text[1:]


def _expand_terms(text):
    expanded = text
    for pattern, replacement in _TERM_REPLACEMENTS:
        expanded = re.sub(pattern, replacement, expanded, flags=re.I)
    cleanups = (
        (r"\bde settore\b", "del settore"),
        (r"\bfecondita\b", "fecondità"),
        (r"\bstandadizzat", "standardizzat"),
        (r"\bValore aggiunto\b", "valore aggiunto"),
        (r"\bUnità di [Ll]avoro\b", "unità di lavoro"),
        (r"\bServizi alle imprese\b", "servizi alle imprese"),
        (r"\bdalla Regione\b", "dalla regione"),
    )
    for pattern, replacement in cleanups:
        expanded = re.sub(pattern, replacement, expanded)
    return re.sub(r"\s+", " ", expanded).strip()


def _with_article(text):
    value = text.strip().rstrip(".")
    if not value:
        return "il fenomeno descritto"
    first = re.sub(r"[^a-zA-Zàèéìòóù0-9]", "", value.split()[0]).lower()
    lowered = value[:1].lower() + value[1:]
    if first in _FEMININE_SINGULAR:
        return f"l'{lowered}" if first[0] in "aeiou" else f"la {lowered}"
    if first in _MASCULINE_SINGULAR:
        return f"l'{lowered}" if first[0] in "aeiou" else f"il {lowered}"
    if first in _FEMININE_PLURAL:
        return f"le {lowered}"
    if first in _MASCULINE_PLURAL_GLI:
        return f"gli {lowered}"
    if first in _MASCULINE_PLURAL_I:
        return f"gli {lowered}" if first[0] in "aeiou" else f"i {lowered}"
    if first == "altri":
        return f"gli {lowered}"
    # Unknown term (not in the curated gender lists): never leave it bare, which
    # would read "Misura popolazione..." with no article. Guess a definite article
    # so the generated sentence stays grammatical; a new term should still be added
    # to the lists above, and tests/integration/test_indicator_text.py flags a bare result.
    if first[:1] in "aeiou":
        return f"l'{lowered}"
    if first.endswith("a") or re.search(r"(zione|sione|tà|trice|udine|aggine)$", first):
        return f"la {lowered}"
    return f"il {lowered}"


def _finish_sentence(text):
    value = " ".join((text or "").split()).strip()
    if not value:
        return ""
    value = value[:1].upper() + value[1:]
    return value if value.endswith((".", "?", "!")) else f"{value}."


def _display_name(name):
    name = re.sub(r"^TAVOLA DISMESSA\s*-\s*", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    return name[0].lower() + name[1:] if name else ""


def _lens(name):
    lowered = name.lower()
    if "maschi" in lowered:
        return "Qui il confronto riguarda gli uomini, quindi è utile affiancarlo al dato femminile e al totale."
    if "femmine" in lowered:
        return "Qui il confronto riguarda le donne, quindi aiuta a leggere divari di genere che il totale può coprire."
    if "giovanile" in lowered or "giovani" in lowered or "neet" in lowered:
        return "Il focus sui giovani è importante per capire se il territorio offre occasioni all'inizio della vita adulta."
    if "anziani" in lowered:
        return "Il focus sugli anziani aiuta a leggere il carico sui servizi e sulle famiglie."
    if "minori" in lowered or "alunni" in lowered:
        return "Il focus su minori e studenti è utile per valutare opportunità e fragilità prima dell'ingresso nel lavoro."
    if "straniera" in lowered:
        return "Il riferimento alla popolazione straniera aiuta a leggere integrazione economica e accesso alle opportunità."
    return ""


def _direction(name):
    lowered = name.lower()
    if any(token in lowered for token in LOWER_IS_BETTER):
        return "lower_better"
    if (
        "emissioni" in lowered
        or "interruzioni" in lowered
        or "insoddisfazione" in lowered
        or "tempo medio" in lowered
        or "durata media" in lowered
        or "giacenza media" in lowered
    ):
        return "lower_better"
    if any(token in lowered for token in HIGHER_IS_BETTER):
        return "higher_better"
    if "fertilizzanti" in lowered or "fitosanitari" in lowered or "consumi di energia" in lowered:
        return "higher_worse"
    return "contextual"


# Same two hex stops as --map-ramp-from/--map-ramp-to (colors.css) and the
# SPA's MAP_RAMP (frontend/src/main.jsx): a linear RGB interpolation, not a
# perceptual color space, to stay pixel-identical with the interactive map.
_MAP_RAMP_FROM = (0xE7, 0xEC, 0xF3)
_MAP_RAMP_TO = (0x15, 0x23, 0x3B)


def region_choropleth_colors(values):
    """Per-region hex fill for the static indicator-page choropleth: {region_key: "#rrggbb"},
    scaled over the raw value range like the SPA's d3.scaleSequential(MAP_RAMP)."""
    numeric = [row["value"] for row in values if row.get("value") is not None]
    if not numeric:
        return {}
    lo, hi = min(numeric), max(numeric)
    span = hi - lo
    colors = {}
    for row in values:
        value = row.get("value")
        if value is None:
            continue
        t = (value - lo) / span if span else 1.0
        rgb = tuple(
            round(_MAP_RAMP_FROM[i] + (_MAP_RAMP_TO[i] - _MAP_RAMP_FROM[i]) * t)
            for i in range(3)
        )
        colors[row["region_key"]] = "#%02x%02x%02x" % rgb
    return colors


def cover_bars(values, best, worst, scoreable, limit=4):
    """Top `limit` regions (already best-to-worst ordered) plus the worst one,
    for the auto-generated indicator cover card's bar chart. Bar width is the
    value scaled over the full observed range, like region_choropleth_colors."""
    if not values:
        return []
    numeric = [row["value"] for row in values if row.get("value") is not None]
    if not numeric:
        return []
    lo, hi = min(numeric), max(numeric)
    span = (hi - lo) or 1.0

    rows = list(values[:limit])
    if scoreable and worst is not None and all(row["region_key"] != worst["region_key"] for row in rows):
        rows.append(worst)

    best_key = values[0]["region_key"] if scoreable and values else None
    worst_key = worst["region_key"] if scoreable and worst is not None else None

    bars = []
    for row in rows:
        value = row.get("value")
        if value is None:
            continue
        t = (value - lo) / span
        bars.append({
            "region": row["region"],
            "region_key": row["region_key"],
            "value": value,
            "width_pct": round(6 + t * 94),
            "is_best": row["region_key"] == best_key,
            "is_worst": row["region_key"] == worst_key,
        })
    return bars


def sparkline_points(spark, width=320, height=64, pad=4):
    """SVG <polyline> "x,y x,y ..." string for the indicator page's inline trend
    chart, from the national-average series in get_indicator()'s metadata.spark."""
    values = [point["value"] for point in spark if point.get("value") is not None]
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    count = len(spark)
    step = (width - 2 * pad) / (count - 1) if count > 1 else 0
    coords = []
    for index, point in enumerate(spark):
        value = point.get("value")
        if value is None:
            continue
        x = pad + index * step
        y = pad + (height - 2 * pad) * (1 - (value - lo) / span)
        coords.append(f"{x:.1f},{y:.1f}")
    return " ".join(coords)


def _clean(value):
    return " ".join((value or "").split())


def display_unit(unit):
    """Correct presentation-only typos and notation without changing source CSVs."""
    value = _clean(unit)
    value = re.sub(r"\bstandadizzato\b", "standardizzato", value, flags=re.I)
    value = re.sub(r"\bGwh\b", "GWh", value, flags=re.I)
    value = re.sub(r"\bUla\b", "ULA", value, flags=re.I)
    value = re.sub(r"\bKm/ora\b", "km/ora", value, flags=re.I)
    value = re.sub(r"\bM2\b", "m²", value, flags=re.I)
    value = re.sub(r"\bM3\b", "m³", value, flags=re.I)
    value = re.sub(r"\bKm2\b", "km²", value, flags=re.I)
    return value
