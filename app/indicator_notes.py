import re


THEME_EXAMPLES = {
    "Ambiente, altro": "Esempio: aiuta a capire se un territorio è più esposto a pressioni ambientali, rischi naturali o consumo di suolo rispetto ad altri.",
    "Capitale sociale": "Esempio: rende visibile la presenza di reti civiche, cooperative o organizzazioni che tengono insieme servizi e comunità.",
    "Città": "Esempio: permette di confrontare la qualità della vita urbana, dai servizi quotidiani allo spazio pubblico disponibile.",
    "Competitività": "Esempio: serve a leggere quanto il sistema produttivo regionale usa risorse, tecnologia e lavoro per stare sul mercato.",
    "Cultura": "Esempio: fa vedere se musei, spettacoli e imprese culturali sono una parte viva dell'economia locale o restano marginali.",
    "Demografia e popolazione": "Esempio: aiuta a leggere se una regione invecchia, si svuota o si rinnova, confrontando struttura per età, natalità e movimenti di popolazione.",
    "Salute": "Esempio: traduce le condizioni di salute di un territorio in anni di vita attesi, un esito che riassume prevenzione, servizi e condizioni sociali.",
    "Demografia di impresa": "Esempio: aiuta a distinguere territori dove nascono nuove attività da quelli in cui il tessuto produttivo si rinnova meno.",
    "Dinamiche settoriali": "Esempio: mette a confronto la forza economica di un settore tra regioni, al netto della diversa dimensione dei territori.",
    "Energia": "Esempio: consente di leggere consumi, continuità dei servizi e peso delle fonti rinnovabili nella vita economica e quotidiana.",
    "Inclusione sociale": "Esempio: porta l'attenzione su persone, famiglie e servizi che spesso restano fuori dai soli indicatori economici.",
    "Internazionalizzazione": "Esempio: mostra quanto una regione sia collegata ai mercati esteri, tra esportazioni, importazioni e investimenti.",
    "Istruzione e formazione": "Esempio: aiuta a capire dove la scuola e la formazione riescono a trattenere, preparare e accompagnare le persone.",
    "Lavoro": "Esempio: fa vedere quante persone lavorano, chi resta fuori e quanto è stabile la partecipazione al mercato del lavoro.",
    "Legalità e sicurezza": "Esempio: segnala aspetti della sicurezza quotidiana e del funzionamento della giustizia che incidono sulla fiducia nei territori.",
    "Mercato dei capitali e finanza d'impresa": "Esempio: racconta quanto sia facile o rischioso finanziare imprese e investimenti in una regione.",
    "Pubblica Amministrazione": "Esempio: rende visibili tempi, trasparenza e capacità attuativa delle amministrazioni, cioè pezzi concreti della macchina pubblica.",
    "Qualità dell'aria": "Esempio: aiuta a confrontare l'impatto ambientale di attività produttive, trasporti e consumi energetici.",
    "Reddito e ricchezza": "Esempio: misura quanta ricchezza un territorio produce e quanto reddito resta davvero nelle tasche delle famiglie, al netto della sua dimensione.",
    "Ricerca ed innovazione": "Esempio: mostra se università, imprese e istituzioni producono conoscenza, brevetti e innovazione in modo diffuso.",
    "Rifiuti": "Esempio: serve a leggere quanto il ciclo dei rifiuti sia orientato al recupero o ancora dipendente dallo smaltimento.",
    "Risorse idriche": "Esempio: fa emergere differenze molto concrete, come perdite di rete, qualità dell'acqua e continuità del servizio.",
    "Servizi di cura": "Esempio: aiuta a capire se famiglie, bambini e anziani trovano servizi di cura accessibili nel territorio in cui vivono.",
    "Società dell'informazione": "Esempio: misura quanto famiglie, imprese e pubbliche amministrazioni siano dentro la transizione digitale.",
    "Trasporti e mobilità": "Esempio: racconta come persone e merci si muovono, e quanto una regione dipenda da strada, ferrovia, porti, aeroporti o trasporto pubblico.",
    "Turismo": "Esempio: distingue i territori dove il turismo pesa molto sulla vita locale da quelli in cui resta un fenomeno più contenuto.",
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


# Non-destructive macro-area overlay over the 26 verbatim Istat themes. The themes
# stay exactly as published (single source of truth: the CSV "Tema" column); this map
# only groups them into ~6 higher-level areas used as a coarse filter in the atlas and
# region pages. When a new theme is added to the dataset, add it here too (see
# docs/DATA_PIPELINE.md), otherwise macro_area_for() falls back to "Altro".
MACRO_AREAS = {
    "Economia e produzione": (
        "Competitività",
        "Dinamiche settoriali",
        "Demografia di impresa",
        "Reddito e ricchezza",
        "Mercato dei capitali e finanza d'impresa",
        "Internazionalizzazione",
        "Turismo",
        "Ricerca ed innovazione",
    ),
    "Lavoro e istruzione": (
        "Lavoro",
        "Istruzione e formazione",
    ),
    "Società e inclusione": (
        "Inclusione sociale",
        "Servizi di cura",
        "Cultura",
        "Capitale sociale",
        "Legalità e sicurezza",
    ),
    "Ambiente, energia e territorio": (
        "Ambiente, altro",
        "Energia",
        "Qualità dell'aria",
        "Rifiuti",
        "Risorse idriche",
        "Città",
    ),
    "Demografia e salute": (
        "Demografia e popolazione",
        "Salute",
    ),
    "Istituzioni e infrastrutture": (
        "Pubblica Amministrazione",
        "Trasporti e mobilità",
        "Società dell'informazione",
    ),
}

# Display order for the macro-areas (mirrors MACRO_AREAS insertion order).
MACRO_AREA_ORDER = tuple(MACRO_AREAS.keys())

_THEME_TO_MACRO = {
    theme: area for area, themes in MACRO_AREAS.items() for theme in themes
}


def macro_area_for(theme):
    """Macro-area label for a theme, or 'Altro' if the theme is not mapped yet."""
    return _THEME_TO_MACRO.get(_clean(theme), "Altro")


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
    # Competitività
    "158": "higher_better", "167": "higher_better", "471": "higher_better", "419": "higher_better",
    # Cultura (cultural participation / creative economy = positive; absence of offer = negative)
    "600": "higher_better", "611": "higher_better", "612": "higher_better", "27": "higher_better",
    "613": "higher_better", "610": "higher_better", "595": "higher_better", "614": "lower_better",
    "596": "higher_better", "594": "higher_better", "593": "higher_better", "25": "higher_better",
    # Demografia di impresa
    "242": "higher_better", "54": "higher_better",
    # Dinamiche settoriali (labour productivity / growth = positive)
    "31": "higher_better", "1": "higher_better", "133": "higher_better", "130": "higher_better",
    "107": "higher_better", "123": "higher_better", "124": "higher_better", "250": "higher_better",
    # Energia (fix misclassification: energy covered by cogeneration/bioenergy is good)
    "378": "higher_better", "379": "higher_better",
    # Inclusione sociale (early school leaving = bad; accessible schools = good)
    "200": "lower_better", "199": "lower_better", "102": "lower_better",
    "641": "higher_better", "651": "higher_better", "647": "higher_better", "646": "higher_better",
    "645": "higher_better", "642": "higher_better", "643": "higher_better", "644": "higher_better",
    "650": "higher_better",
    # Istruzione e formazione (education level / training participation = positive)
    "198": "higher_better", "197": "higher_better", "99": "higher_better", "77": "higher_better",
    "190": "higher_better", "189": "higher_better", "104": "higher_better", "67": "higher_better",
    "188": "higher_better", "187": "higher_better", "63": "higher_better", "186": "higher_better",
    "185": "higher_better",
    # Lavoro (fix gender-gap indicators to lower_better; activity/entrepreneurship = positive)
    "398": "higher_better", "466": "higher_better", "61": "lower_better", "57": "lower_better",
    "402": "higher_better", "401": "higher_better", "203": "higher_better", "213": "higher_better",
    # Ricerca ed innovazione
    "396": "higher_better", "397": "higher_better",
    # Mercato dei capitali (venture / "capitale di rischio" investment is positive;
    # the word "rischio" otherwise trips the lower-is-better heuristic)
    "163": "higher_better", "164": "higher_better",
    # Rifiuti (composting = good)
    "53": "higher_better",
    # Servizi di cura (childcare availability/coverage = good)
    "142": "higher_better", "414": "higher_better",
    # Società dell'informazione (digital uptake = positive)
    "426": "higher_better", "64": "higher_better", "72": "higher_better", "70": "higher_better",
    "434": "higher_better",
    # Trasporti e mobilità (rail / public transport use = positive)
    "47": "higher_better", "268": "higher_better", "269": "higher_better",
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


def build_indicator_explain(item):
    name = _clean(item.get("indicator") or item.get("name"))
    theme = _clean(item.get("theme"))
    unit = _clean(item.get("unit"))
    archive = _clean(item.get("archive"))
    indicator_id = str(item.get("id", ""))
    base_name = _display_name(name)
    lens = _lens(name)
    direction = direction_for(indicator_id, name)

    return {
        "plain": _plain_text(base_name, theme, archive, unit, indicator_id),
        "example": _example_text(name, theme, lens),
        "reading": _reading_text(name, theme, unit, direction),
        "caveat": _caveat_text(name, theme, lens),
        "direction": direction,
    }


def _plain_text(name, theme, archive, unit, indicator_id):
    subject = _subject_from_archive(archive) or name
    end = "" if subject.endswith("...") else "."
    openings = [
        f"Misura {subject}{end}",
        f"Mette a fuoco {subject}{end}",
        f"Legge {subject}{end}",
        f"Racconta {subject}{end}",
        f"Osserva {subject}{end}",
    ]
    text = openings[_pick(indicator_id, len(openings))]
    unit_note = _unit_note(unit)
    if unit_note:
        text = f"{text} {unit_note}"
    return text


def _example_text(name, theme, lens):
    specific = _specific_example(name)
    if specific:
        text = specific
    else:
        text = THEME_EXAMPLES.get(theme, "Esempio: consente di confrontare regioni diverse senza fermarsi alla sola dimensione demografica o economica.")
    if lens:
        text = f"{text} {lens}"
    return text


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
        return "Valori più bassi sono in genere preferibili, perché segnalano minore disagio, minore rischio o minore inefficienza."
    if direction == "higher_better":
        return "Valori più alti sono in genere un segnale favorevole, perché indicano maggiore copertura, partecipazione o capacità del territorio."
    if direction == "higher_worse":
        return "Valori più alti segnalano una pressione maggiore sul territorio o sul servizio osservato. Non sono automaticamente negativi, ma chiedono contesto."
    if theme in ("Turismo", "Trasporti e mobilità", "Cultura"):
        return "Valori più alti indicano maggiore intensità del fenomeno. Possono essere un punto di forza, ma anche una pressione da gestire."
    if theme in ("Energia", "Competitività", "Dinamiche settoriali"):
        return "Valori più alti indicano maggiore intensità economica o produttiva. Il giudizio dipende dal tipo di risorsa usata e dal risultato che produce."
    return "Il valore va letto come intensità del fenomeno: più sale, più quel tratto pesa nel profilo della regione."


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


def _subject_from_archive(archive):
    if not archive:
        return ""
    text = archive.strip().rstrip(".")
    text = re.sub(r"\s*\([^)]*percentuale[^)]*\)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s*\([^)]*valori?[^)]*\)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {
        "percentuale",
        "numero",
        "punteggio standardizzato",
        "punteggio standadizzato",
        "giornate",
    }:
        return ""
    if len(text) > 135:
        text = text[:132].rsplit(" ", 1)[0].rstrip(" (,.;:") + "..."
        if text.count("(") > text.count(")"):
            text = text.rsplit("(", 1)[0].rstrip(" ,.;:") + "..."
    if not text:
        return ""
    return text[0].lower() + text[1:]


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


def _specific_example(name):
    lowered = name.lower()
    if "turistic" in lowered:
        return "Esempio: una regione piccola e molto visitata può avere un valore alto anche se registra meno presenze assolute di una regione più grande."
    if "disoccupazione" in lowered:
        return "Esempio: due regioni possono avere lo stesso numero di persone in cerca di lavoro, ma un tasso diverso se cambia la dimensione delle forze di lavoro."
    if "tempo medio" in lowered or "durata media" in lowered or "giacenza media" in lowered or "ritardo" in lowered:
        return "Esempio: traduce l'efficienza amministrativa o logistica in tempo atteso, cioè giorni, minuti o ritardi che persone e imprese sentono davvero."
    if "occupazione" in lowered:
        return "Esempio: mostra quanta parte della popolazione in età lavorativa ha effettivamente un impiego, senza fermarsi al numero assoluto di occupati."
    if "neet" in lowered:
        return "Esempio: intercetta i giovani che non studiano e non lavorano, una zona grigia che spesso anticipa esclusione e perdita di competenze."
    if "abbandon" in lowered:
        return "Esempio: segnala dove il percorso scolastico si interrompe prima del tempo, spesso prima che il problema emerga nel mercato del lavoro."
    if "competen" in lowered or "apprendimento" in lowered:
        return "Esempio: sposta l'attenzione dal titolo di studio a quello che gli studenti riescono davvero a fare in lettura, matematica o inglese."
    if "povert" in lowered or "deprivazione" in lowered:
        return "Esempio: aiuta a vedere dove il reddito e le condizioni materiali rendono più fragile la vita quotidiana delle persone."
    if "disabil" in lowered:
        return "Esempio: permette di osservare se scuole, presidi e servizi sono attrezzati per includere persone con bisogni specifici."
    if "banda" in lowered or "internet" in lowered or "wi-fi" in lowered or "e-government" in lowered:
        return "Esempio: fa capire se cittadini, imprese o amministrazioni possono usare servizi digitali senza partire svantaggiati."
    if "rifiut" in lowered:
        return "Esempio: mette in chiaro se il sistema locale recupera materiali o continua a dipendere dallo smaltimento."
    if "acqua" in lowered or "idr" in lowered or "depurazione" in lowered:
        return "Esempio: traduce il servizio idrico in esperienza concreta, tra acqua disponibile, reti efficienti e depurazione."
    if "ferrovi" in lowered or "trasporto pubblico" in lowered or "tpl" in lowered:
        return "Esempio: mostra se muoversi senza auto è una possibilità reale o un'opzione debole nel territorio."
    if "merci" in lowered or "porto" in lowered or "interport" in lowered or "sdoganamento" in lowered:
        return "Esempio: aiuta a leggere la logistica, cioè il modo in cui imprese e territori portano prodotti dentro e fuori dai mercati."
    if "rinnovabil" in lowered or "bioenergie" in lowered or "cogenerazione" in lowered:
        return "Esempio: segnala quanto il sistema energetico regionale si appoggia a fonti o processi meno tradizionali."
    if "criminal" in lowered or "furti" in lowered or "rapine" in lowered or "omicidi" in lowered:
        return "Esempio: rende confrontabili fenomeni di sicurezza che, guardati solo in valori assoluti, penalizzerebbero le regioni più popolose."
    if "ricerca" in lowered or "r&s" in lowered or "brevett" in lowered or "innovazione" in lowered:
        return "Esempio: fa emergere dove imprese, università e istituzioni investono in conoscenza invece di competere solo sui costi."
    if "export" in lowered or "esport" in lowered or "import" in lowered or "estero" in lowered:
        return "Esempio: mostra quanto l'economia regionale dialoghi con il resto del mondo, sia vendendo sia comprando beni e servizi."
    if "credito" in lowered or "fidi" in lowered or "finanziamenti" in lowered or "capitale di rischio" in lowered:
        return "Esempio: indica se il denaro per crescere arriva con relativa facilità o se il sistema finanziario è più prudente."
    if "spettacolo" in lowered or "muse" in lowered or "cultural" in lowered:
        return "Esempio: aiuta a capire se la domanda culturale è concentrata in pochi poli o diffusa nella vita ordinaria del territorio."
    if "verde" in lowered:
        return "Esempio: collega la qualità urbana a spazi che le persone possono usare ogni giorno, oltre i grandi parchi simbolici."
    return ""


def _unit_note(unit):
    lowered = unit.lower()
    if not lowered:
        return ""
    if "percentuale" in lowered:
        return "La percentuale rende più pulito il confronto tra regioni grandi e piccole."
    if "per abitante" in lowered or "per cento abitanti" in lowered or "per mille abitanti" in lowered or "centomila" in lowered:
        return "Il rapporto sulla popolazione evita confronti falsati dalla dimensione."
    if "migliaia di euro" in lowered or lowered == "euro" or "milioni di euro" in lowered:
        return "Il valore economico va letto come intensità o produttività, non come ricchezza complessiva."
    if "punteggio" in lowered or "numero indice" in lowered:
        return "Il punteggio serve soprattutto per ordinare e confrontare."
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


def _clean(value):
    return " ".join((value or "").split())


def _pick(seed, modulo):
    try:
        number = int(seed)
    except (TypeError, ValueError):
        number = sum(ord(char) for char in str(seed))
    return number % modulo
