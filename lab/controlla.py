"""Ogni cifra della bozza contro il dossier. La metà deterministica della verifica.

Il verificatore ha un modello forte per giudicare se una fonte regge e se un
nesso è autorizzato. Non deve invece confrontare numeri a mente: è proprio
lì che un controllo sembra fatto e non lo è. Questo comando prende ogni
numero scritto nella prosa e lo cerca fra i numeri che il dossier contiene
davvero (valori, medie, mediane, spread, delta, ranghi, anni). Ciò che non
trova, lo dice, con la frase attorno.

Non è un cancello e non decide niente: stampa un elenco. Una cifra
`non_trovata` può essere un errore di chi scrive o una cifra legittima che il
dossier non contiene (un'età, una data, un numero di una fonte esterna): a
distinguerle è il verificatore, che ha il testo davanti.

    bin/py -m lab.controlla ter-30 < bozza.json
    bin/py -m lab.controlla ter-30 --bozza bozza.json --salva data/lab/bozze/ter-30.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from app.atlas_catalog import get_atlas_catalog
from app.indicator_view import build_indicator_view
from lab.dossier import costruisci, matrice_per_nome, risolvi

BOZZE = os.path.join("data", "lab", "bozze")

# Un numero come lo scrive l'italiano: `48,3`, `1.240`, `12`, `-0,5`.
NUMERO = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+,\d+|-?\d+")

# Un link a un'altra pagina indicatore, come si scrive in markdown.
LINK = re.compile(r"\]\((/indicatore/[^)\s]+)\)")

# Il bersaglio di un link markdown e ogni url nudo. Si tolgono prima di cercare
# le cifre: `ter-177` dentro un percorso non è un numero che il lettore legge,
# ma `NUMERO` ci pesca dentro `-177` e lo manda fra le non trovate. Quattro
# falsi allarmi su una bozza corretta, tutti nati il giorno in cui la prosa ha
# cominciato a linkare gli altri indicatori.
BERSAGLIO = re.compile(r"\]\([^)\s]*\)|https?://\S+")

# Una fascia d'età: `15-64 anni`, `tra i 15 e i 64 anni`. I due numeri sono
# etichette come un anno di calendario, non grandezze della serie, e vanno
# riconosciuti prima di cercarli fra i valori. Su `ter-13` il 64 di "tra i 15 e
# i 64 anni" è stato accoppiato al Lazio (64,17) e marcato **trovata**: un
# falso positivo, che è peggio di un falso allarme perché il falso allarme si
# vede. Solo l'intervallo, non il numero singolo: "negli ultimi 5 anni" è una
# durata, e chiamarla età sarebbe un'etichetta sbagliata al posto di nessuna.
ETA = re.compile(r"\b\d{1,3}\s*(?:-|e i|ed i|ai|e|a)\s*\d{1,3}\s*anni\b")

# Un anno dentro l'etichetta di una corrispondenza.
ANNO = re.compile(r"\b(?:19|20)\d{2}\b")

# La stessa tolleranza del controllo che oggi vive in officina/lint.py: sei
# centesimi in assoluto, o l'1,1% del valore, perché la prosa arrotonda.
def _tollera(atteso):
    return max(0.06, abs(atteso) * 0.011)


def _numero(testo):
    """`1.240,5` -> 1240.5. Le migliaia col punto, i decimali con la virgola."""
    return float(testo.replace(".", "").replace(",", "."))


def _accoppia(candidate, valore, esatto=False):
    """(voce più vicina, se la tolleranza la ammette).

    `esatto` serve ai tentativi di ripiego, dove il territorio è dedotto o il
    segno è stato tolto: lì l'etichetta è già una supposizione, e sommarci la
    tolleranza dell'1,1% rende il controllo cieco. Misurato su un articolo di
    109 cifre: col ripiego tollerante le cifre alterate di mezzo punto venivano
    smentite nel 20% dei casi contro il 53% di prima, cioè i falsi allarmi
    sparivano portandosi via la capacità di smentire. Con il ripiego esatto si
    tengono tutte e due le cose, perché chi scrive le cifre del dossier le
    copia, non le arrotonda a mano.

    A parità di distanza vince la corrispondenza **esatta**, e a parità di
    esattezza vince l'etichetta più corta, che è sempre quella meno dedotta:
    "valore di Puglia nel 2025" prima di "valore di Puglia nel 2025 (territorio
    non nominato nella frase)". Serve perché un'etichetta sbagliata su una
    cifra giusta costa a chi verifica quanto una cifra sbagliata.
    """
    if not candidate:
        return None, False
    migliore = min(candidate, key=lambda voce: (abs(voce[0] - valore), len(voce[1])))
    quanto = 0.005 if esatto else _tollera(migliore[0])
    return migliore, abs(migliore[0] - valore) <= quanto


ALTERNATIVE_MASSIME = 4


def _alternative(candidate, valore, scelto):
    """Le altre voci compatibili con lo stesso numero, la migliore per prima.

    Solo quelle che portano un valore **diverso** da quello scelto. Un dossier
    ricco dà quasi sempre più etichette allo stesso numero (`valore di Sicilia
    nel 2025`, `massimo dell'ultimo anno`, `estremo alto del gruppo 3`): sono
    sinonimi, non ambiguità, e stamparle riempirebbe tre quarti delle righe
    seppellendo i casi veri. Il caso vero è un **altro numero** che la
    tolleranza ammette lo stesso: `19,10` che combacia con la media del 2023
    mentre per il 2025 non c'è niente.
    """
    viste = {round(scelto[0], 2)}
    fuori = []
    for valore_candidato, etichetta, _ in sorted(
            candidate, key=lambda voce: abs(abs(voce[0]) - abs(valore))):
        arrotondato = round(valore_candidato, 2)
        if arrotondato in viste:
            continue
        vicino = min(abs(valore_candidato - valore), abs(abs(valore_candidato) - abs(valore)))
        if vicino > _tollera(valore_candidato):
            break
        viste.add(arrotondato)
        fuori.append(f"{valore_candidato} ({etichetta})")
        if len(fuori) == ALTERNATIVE_MASSIME:
            break
    return fuori


def cerca(dossier, matrice, valore):
    """Ogni voce del dossier compatibile con un numero, con la sua etichetta.

    L'interrogazione che completa lo spazzolamento. Lo spazzolamento garantisce
    la **copertura**, perché un modello a cui si chiede di guardare centonove
    cifre ne salta; questa serve alla **risoluzione**, nei due o tre casi per
    articolo in cui la riga non convince e chi verifica vuole vedere il
    ventaglio invece del migliore.
    """
    voci = list(_voci_derivate(dossier))
    for anno, riga in matrice.items():
        for territorio, presente in riga.items():
            voci.append((round(float(presente), 2), f"valore di {territorio} nel {anno}", territorio))
    fuori = []
    for valore_candidato, etichetta, territorio in voci:
        scarto = min(abs(valore_candidato - valore), abs(abs(valore_candidato) - abs(valore)))
        if scarto <= _tollera(valore_candidato):
            fuori.append({"valore": valore_candidato, "etichetta": etichetta,
                          "territorio": territorio, "scarto": round(scarto, 4)})
    fuori.sort(key=lambda voce: voce["scarto"])
    return fuori


def impronta(bozza):
    """Tre numeri che identificano il testo, calcolabili anche fuori da Python.

    Servono a chiudere l'unico punto in cui il testo passa ancora dentro un
    prompt: fra chi lo scrive e chi lo verifica. Il workflow calcola gli stessi
    tre numeri sulla bozza che ha in mano e li confronta con questi, e una
    ribattitura infedele smette di essere invisibile.
    """
    pezzi = [bozza.get("lead") or ""] + [
        (sezione.get("h") or "") + (sezione.get("body") or "")
        for sezione in bozza.get("sections") or []
    ]
    # Anche le fonti, testo e url: contarle soltanto lascerebbe passare un url
    # storpiato nella ribattitura, che è proprio la cosa che non deve
    # arrivare su disco.
    pezzi += [(fonte.get("testo") or "") + (fonte.get("url") or "")
              for fonte in bozza.get("fonti") or []]
    testo = "".join(pezzi)
    return {
        "caratteri": len("".join(testo.split())),
        "parole": len(testo.split()),
        # `isdecimal` e non `isdigit`: `isdigit` è vero anche per l'esponente
        # di `km²`, che l'espressione `\d` di JavaScript non conta. Il workflow
        # ricalcola questi numeri in JavaScript, e due definizioni diverse di
        # "cifra" fermerebbero un articolo giusto.
        "cifre": sum(1 for carattere in testo if carattere.isdecimal()),
        "sezioni": len(bozza.get("sections") or []),
        "fonti": len(bozza.get("fonti") or []),
    }


def _prosa(bozza):
    """[(dove, testo)] di tutto ciò che un lettore legge."""
    pezzi = []
    if bozza.get("lead"):
        pezzi.append(("lead", bozza["lead"]))
    for indice, sezione in enumerate(bozza.get("sections") or []):
        dove = sezione.get("role") or f"sezione {indice}"
        if sezione.get("h"):
            pezzi.append((f"{dove}/h", sezione["h"]))
        if sezione.get("body"):
            pezzi.append((dove, sezione["body"]))
    return pezzi


def _voci_derivate(dossier):
    """[(valore, etichetta, territorio)] per i numeri già calcolati.

    Ogni numero ammesso porta la propria etichetta, e l'etichetta è metà del
    prodotto: dire "trovata" non aiuta nessuno, dire che il 41,73 scritto in una
    frase sulla Toscana corrisponde alla **media nazionale del 2007** mette il
    verificatore in condizione di decidere in un colpo solo.
    """
    voci = []
    for voce in dossier["ultimo"]:
        territorio = voce["territorio"]
        voci.append((voce["valore"], f"valore di {territorio} nel {dossier['vintage']}", territorio))
        voci.append((voce["rango"], f"rango di {territorio}", territorio))
        voci.append((voce["percentile"], f"percentile di {territorio}", territorio))
        voci.append((voce["scarto_dalla_mediana"], f"scarto dalla mediana di {territorio}", territorio))
    dinamica = dossier["dinamica"]
    for campo in ("delta_1a", "delta_5a", "delta_10a", "volatilita"):
        for territorio, valore in (dinamica.get(campo) or {}).items():
            voci.append((valore, f"{campo} di {territorio}", territorio))
    for rottura in dinamica["rotture"]:
        voci.append((rottura["salto"],
                     f"salto di {rottura['territorio']} nel {rottura['anno']}", rottura["territorio"]))
    for inversione in dinamica["inversioni"]:
        voci.append((inversione["prima"], f"variazione precedente di {inversione['territorio']}",
                     inversione["territorio"]))
        voci.append((inversione["poi"], f"variazione recente di {inversione['territorio']}",
                     inversione["territorio"]))

    sintesi = dossier["sintesi"]
    for campo in ("media", "mediana", "spread", "rapporto_max_min", "coeff_variazione", "territori"):
        voci.append((sintesi.get(campo), f"{campo} dell'ultimo anno", None))
    for estremo in ("minimo", "massimo"):
        voci.append((sintesi[estremo]["valore"],
                     f"{estremo} dell'ultimo anno ({sintesi[estremo]['territorio']})", None))
    for area, valore in dossier["macroaree"].items():
        voci.append((valore, f"media di {area}", None))
    for campo, valore in dinamica["nazionale"].items():
        voci.append((valore, f"media nazionale, {campo}", None))
    for anno, valore in dinamica["media_per_anno"].items():
        voci.append((valore, f"media nazionale nel {anno}", None))
    if dinamica["convergenza"]:
        voci.append((dinamica["convergenza"]["spread_iniziale"],
                     f"spread nel {dinamica['convergenza']['anno_iniziale']}", None))
    for quale, record in dinamica["record"].items():
        voci.append((record["valore"], f"{quale}: {record['territorio']} nel {record['anno']}", None))

    # Le bontà dei gruppi si scrivono in prosa come percentuali ("le macroaree
    # spiegano l'80% di questa divisione") e nel dossier stanno come frazioni.
    # Senza le due forme, una cifra corretta e centrale nell'articolo finisce
    # fra le non trovate: è successo all'80 di `ter-13`.
    gruppi = dossier.get("gruppi") or {}
    for campo in ("bonta", "bonta_delle_macroaree", "sovrapposizione_con_macroaree"):
        valore = gruppi.get(campo)
        if valore is None:
            continue
        voci.append((valore, f"{campo} dei gruppi", None))
        voci.append((valore * 100, f"{campo} dei gruppi, in percentuale", None))
    for indice, gruppo in enumerate(gruppi.get("gruppi") or [], start=1):
        voci.append((gruppo["da"], f"estremo basso del gruppo {indice}", None))
        voci.append((gruppo["a"], f"estremo alto del gruppo {indice}", None))
        voci.append((len(gruppo["territori"]), f"territori nel gruppo {indice}", None))

    return [(float(valore), etichetta, territorio)
            for valore, etichetta, territorio in voci if valore is not None]


def _leggibile(testo):
    """Il testo senza i bersagli dei link: quello che una persona legge davvero."""
    return BERSAGLIO.sub("]", testo)


def _voci_dei_parenti(dossier, testo):
    """[(valore, etichetta, territorio)] degli indicatori linkati in questo pezzo.

    Il dossier porta i valori dei parenti apposta: la frase che vale un link è
    quella che legge **lo stesso territorio su due indicatori**, e senza questi
    numeri chi verifica smentirebbe la cifra del fratello perché non è nel
    dossier di questo indicatore. Al secondo giro chi scrive toglierebbe un
    link buono, cioè esattamente il contrario di quello che serve.

    Si ammettono solo i parenti **linkati in questo pezzo di prosa**, non tutti:
    aprire il paniere a ogni fratello allargherebbe le corrispondenze possibili
    senza che nessuna frase le abbia chieste.
    """
    voci = []
    for parente in dossier.get("parenti") or []:
        percorso = parente.get("percorso_canonico") or ""
        if not parente.get("valori") or percorso not in testo:
            continue
        anno = parente.get("anno")
        for territorio, valore in parente["valori"].items():
            voci.append((float(valore),
                         f"valore di {parente['nome']} ({parente['codice']}) "
                         f"per {territorio} nel {anno}", territorio))
    return voci


def _link(bozza, dossier):
    """Ogni link a un'altra pagina indicatore, e se porta da qualche parte.

    Un percorso inventato è la stessa classe di difetto di una cifra
    inventata, e finora nessuno lo guardava: nella catena attuale i link sono
    validati solo dalla suite, che gira su `content/indicators/` e non vede i
    file della lite.

    Tre esiti distinti, perché confonderli farebbe togliere link buoni: il
    percorso è fra i parenti del dossier, oppure esiste nel catalogo ma non è
    fra i parenti (chi scrive l'ha composto a mano invece di copiarlo), oppure
    non esiste, e allora è una smentita.
    """
    ammessi = {dossier["meta"]["percorso_canonico"]: "questo indicatore"}
    for parente in dossier.get("parenti") or []:
        ammessi[parente["percorso_canonico"]] = f"{parente['relazione']}: {parente['nome']}"
    catalogo = {item["path"] for item in get_atlas_catalog()["indicators"]}
    fuori = []
    for dove, testo in _prosa(bozza):
        for trovato in LINK.finditer(testo):
            percorso = trovato.group(1)
            if percorso in ammessi:
                stato, nota = "nel dossier", ammessi[percorso]
            elif percorso in catalogo:
                stato, nota = "esiste, fuori dai parenti", "composto a mano invece che copiato"
            else:
                stato, nota = "non esiste", "nessuna pagina a questo percorso"
            fuori.append({"percorso": percorso, "dove": dove, "stato": stato, "nota": nota})
    return fuori


def _territori_vicini(testo, inizio, fine, territori):
    """I territori nominati nella stessa frase della cifra.

    Finestra corta apposta: è la frase, non il paragrafo. Un territorio
    nominato tre righe sopra non attribuisce questa cifra.

    Si prendono tutti quelli dentro la finestra e non solo il più vicino,
    perché l'italiano attribuisce nei due versi ("il Lazio segna 68,24" e
    "68,24 del Lazio") e in una frase con due territori la distanza da sola
    sbaglia: in "il Lazio segna 68,24 e l'Umbria 0,04" il più vicino a 68,24
    è Umbria.
    """
    finestra = testo[max(0, inizio - 60):fine + 40]
    dentro = [territorio for territorio in territori if territorio in finestra]
    if dentro:
        return dentro
    # Nessun territorio nella frase: vale l'ultimo nominato prima, nello stesso
    # paragrafo. In "la quota calabrese sale al 45,1%. Nel 2023 scende a 38,66"
    # la seconda cifra è della Calabria come la prima, e senza questa ricaduta
    # finiva fra le non trovate. Tre falsi allarmi su quattro, al primo giro
    # reale, erano di questa forma.
    prima = testo[:inizio]
    ultimo = max(((prima.rfind(t), t) for t in territori), default=(-1, None))
    return [ultimo[1]] if ultimo[0] >= 0 else []


def _anni_vicini(testo, inizio, fine, anni):
    """Gli anni della serie nominati nella stessa frase della cifra.

    L'anno cambia la domanda: "il Lazio segna 68,24" si giudica sull'anno
    dell'articolo, "nel 2014 il Lazio segnava 41,73" su quell'anno. Senza
    questa distinzione un valore vero preso da metà serie e attribuito
    all'ultimo anno passerebbe, ed è la classe di errore più facile da fare.
    """
    finestra = testo[max(0, inizio - 60):fine + 40]
    return [anno for anno in anni if str(anno) in finestra]


def controlla(dossier, matrice, bozza):
    derivate = _voci_derivate(dossier)
    anni = sorted(matrice)
    mancanti = set(dossier.get("anni_mancanti") or [])
    territori = sorted({t for riga in matrice.values() for t in riga}, key=len, reverse=True)
    vintage = dossier["vintage"]

    cifre = []
    for dove, grezzo_testo in _prosa(bozza):
        # I valori dei fratelli valgono solo dove il fratello è linkato, quindi
        # si calcolano per pezzo di prosa e non una volta per tutta la bozza.
        # Si cercano nel testo grezzo, perché è lì che sta il percorso.
        dei_parenti = _voci_dei_parenti(dossier, grezzo_testo)
        testo = _leggibile(grezzo_testo)
        eta = [trovato.span() for trovato in ETA.finditer(testo)]
        for trovato in NUMERO.finditer(testo):
            grezzo = trovato.group(0)
            valore = _numero(grezzo)
            vicini = _territori_vicini(testo, trovato.start(), trovato.end(), territori)
            citati = _anni_vicini(testo, trovato.start(), trovato.end(), anni) or [vintage]

            dentro_una_eta = any(da <= trovato.start() and trovato.end() <= a for da, a in eta)

            # **Un anno si riconosce esatto, mai per tolleranza.** L'1,1% di
            # 2025 vale ventidue anni, quindi il 2014 di "nel 2014 la regione
            # stava a" passava come "l'anno 2025" e con esso passava qualunque
            # data dentro un quarto di secolo. Un anno è un'etichetta, non una
            # grandezza misurata, e si confronta come tale.
            # Anche un anno **assente** dalla serie è un anno legittimo da
            # nominare, ed è spesso la cosa più interessante da dire: su
            # `ter-6` il 2004 manca perché l'Istat spostò la rilevazione, e
            # l'articolo lo diceva giustamente mentre il controllo lo smentiva.
            if grezzo.isdecimal() and int(grezzo) in anni:
                nota = f"l'anno {grezzo} della serie"
            elif grezzo.isdecimal() and int(grezzo) in mancanti:
                nota = f"l'anno {grezzo}, che manca nella serie"
            elif dentro_una_eta:
                nota = "un'età in anni, non una grandezza della serie"
            else:
                nota = None
            if nota:
                inizio = max(0, trovato.start() - 45)
                cifre.append({
                    "numero": grezzo, "dove": dove,
                    "territori_in_frase": vicini or ["nessuno"],
                    "anni_in_frase": citati,
                    "contesto": testo[inizio:trovato.end() + 45].strip(),
                    "stato": "trovata", "corrisponde_a": nota,
                    "via": "etichetta", "alternative": [], "fuori_anno": None,
                    "valore_piu_vicino": None,
                })
                continue

            # Gli aggregati valgono sempre: una media o uno spread compaiono
            # anche in una frase che nomina un territorio ("l'Umbria sta a
            # 0,04, il divario è 68,2"), e negarglieli sarebbe un falso
            # allarme. Ciò che li rende innocui è che ognuno porta la propria
            # etichetta: chi legge vede subito se la corrispondenza ha senso.
            candidate = [voce for voce in derivate + dei_parenti
                         if voce[2] is None or voce[2] in vicini]
            for anno in citati:
                for territorio in vicini:
                    presente = matrice.get(anno, {}).get(territorio)
                    if presente is not None:
                        candidate.append((round(float(presente), 2),
                                          f"valore di {territorio} nel {anno}", territorio))
            # Il ripiego, quando fra i candidati stretti non c'è niente: tutti
            # i territori degli anni citati, con l'etichetta che dichiara che
            # l'attribuzione è dedotta e non scritta.
            #
            # Serve in due casi opposti. Quando nessun territorio è nominato,
            # perché la prosa italiana lo dice con l'aggettivo ("la quota
            # calabrese"), che nessun elenco di nomi intercetta. E quando ne è
            # nominato uno **sbagliato**: `_territori_vicini` guarda una
            # finestra di caratteri, e su `ter-13` ha attribuito al Trentino il
            # 51,01 della Puglia, rimasto dalla frase precedente. Lì il
            # territorio dedotto **cancellava** il candidato giusto, ed è il
            # difetto peggiore dei due, perché toglie invece di aggiungere.
            larghi = []
            for anno in citati:
                for territorio, presente in matrice.get(anno, {}).items():
                    larghi.append((round(float(presente), 2),
                                   f"valore di {territorio} nel {anno} "
                                   f"(territorio non nominato nella frase)", territorio))
            larghi += [(valore_parente, f"{etichetta_parente} (territorio non nominato nella frase)", None)
                       for valore_parente, etichetta_parente, _ in dei_parenti]
            # Anche le voci calcolate che appartengono a un territorio (delta,
            # salti, volatilità, scarti). Senza, il ripiego rimetteva in gioco
            # solo i **valori** delle regioni, quindi una frase che nomina il
            # territorio sbagliato perdeva comunque la volatilità o il delta
            # giusto: due cifre corrette su `bes-04BEC003` finivano lì.
            larghi += [(valore_derivato, f"{etichetta_derivata} (territorio non nominato nella frase)", None)
                       for valore_derivato, etichetta_derivata, territorio_derivato in derivate
                       if territorio_derivato is not None and territorio_derivato not in vicini]

            # L'italiano porta il segno nel verbo, non nella cifra. Il dossier
            # tiene `salto di Molise nel 2023: -9.9`, e chi scrive dice "il
            # Molise perde 9,9 punti": la stessa cosa, e un confronto sui numeri
            # con segno sbaglia di 19,8. Su un solo articolo erano sei cifre
            # giuste finite fra le non trovate, sciolte a mano dal verificatore,
            # cioè aritmetica pagata a prezzo di opus.
            #
            # Solo come terzo tentativo, e con l'etichetta che lo dichiara: una
            # cifra che combacia in valore assoluto **non** dice che la frase
            # abbia il verso giusto, e distinguere una perdita da un guadagno
            # resta lavoro di chi legge.
            assoluti = [(abs(valore_candidato), f"{etichetta_candidata}, in valore assoluto", territorio_candidato)
                        for valore_candidato, etichetta_candidata, territorio_candidato in candidate + larghi
                        if (valore_candidato < 0) != (valore < 0)]

            via = "diretta"
            migliore, trovata = _accoppia(candidate, valore)
            if not trovata:
                di_ripiego, trovata_di_ripiego = _accoppia(candidate + larghi, valore, esatto=True)
                if trovata_di_ripiego:
                    migliore, trovata, via = di_ripiego, trovata_di_ripiego, "ripiego"
            if not trovata and assoluti:
                senza_segno, trovata_senza_segno = _accoppia(assoluti, abs(valore), esatto=True)
                if trovata_senza_segno:
                    migliore, trovata, via = senza_segno, trovata_senza_segno, "segno"
            # La tolleranza è quella di officina (l'1,1%, perché la prosa
            # arrotonda), ma su un valore di 45 vale mezzo punto: dentro quel
            # mezzo punto una cifra sbagliata resta "trovata". Quando la
            # corrispondenza non è esatta lo scarto si scrive, così chi
            # giudica vede la differenza fra un arrotondamento e un errore.
            etichetta = migliore[1] if trovata else None
            if trovata and abs(migliore[0] - valore) > 0.005:
                etichetta += f" [scritto {grezzo}, dato {migliore[0]}]"

            # Le **altre** voci che quel numero potrebbe essere. Stampate solo
            # dove c'è davvero da scegliere, cioè quando un secondo candidato
            # sta anch'esso nella tolleranza o quando la corrispondenza è
            # arrivata da un ripiego: su un articolo sono una manciata di
            # cifre, non tutte, e non costano una chiamata in più.
            #
            # Serve perché una riga sola induce a fidarsi. `19,10` combacia con
            # "media nazionale nel 2023", che è un'etichetta plausibile, e chi
            # legge passa oltre; vedendo che nel 2025 non c'è **nessun**
            # candidato, la stessa riga diventa una smentita in un colpo
            # d'occhio.
            # Le alternative solo dove l'etichetta è già una supposizione
            # (territorio dedotto, segno tolto). Provate su tutte le cifre
            # riempivano tre quarti delle righe di sinonimi dello stesso
            # valore, e il risultato del comando cresceva di due volte e mezzo:
            # rumore che seppellisce i casi veri, cioè il contrario dello scopo.
            alternative = (_alternative(candidate + larghi + assoluti, valore, migliore)
                           if trovata and via != "diretta" else [])
            # Il caso che ha motivato tutto: `19,10` accoppiato alla media
            # **del 2023** in una frase che parla del 2025. L'etichetta è
            # plausibile e chi legge passa oltre. Un'etichetta che nomina un
            # anno che la frase non nomina va detta, perché è lì che una
            # corrispondenza per tolleranza diventa una corrispondenza assurda.
            fuori_anno = None
            if trovata:
                anni_etichetta = {int(a) for a in ANNO.findall(migliore[1])}
                estranei = anni_etichetta - set(citati) - {vintage}
                if estranei:
                    fuori_anno = (f"l'etichetta parla del {min(estranei)}, "
                                  f"la frase del {citati[0] if citati else vintage}")
            inizio = max(0, trovato.start() - 45)
            cifre.append({
                "numero": grezzo,
                "dove": dove,
                "territori_in_frase": vicini or ["nessuno"],
                "anni_in_frase": citati,
                "contesto": testo[inizio:trovato.end() + 45].strip(),
                "stato": "trovata" if trovata else "non_trovata",
                "corrisponde_a": etichetta,
                "via": via if trovata else None,
                "alternative": alternative,
                "fuori_anno": fuori_anno,
                "valore_piu_vicino": None if trovata else (
                    f"{migliore[0]} ({migliore[1]})" if migliore else None),
            })
    non_trovate = [voce for voce in cifre if voce["stato"] == "non_trovata"]
    link = _link(bozza, dossier)
    return {
        "codice": dossier["codice"],
        "cifre_controllate": len(cifre),
        "non_trovate": len(non_trovate),
        "link": link,
        "link_inesistenti": len([voce for voce in link if voce["stato"] == "non esiste"]),
        # Una riga per cifra, per leggere l'esito senza scorrere l'elenco lungo:
        # è qui che si vede a colpo d'occhio una corrispondenza assurda, tipo
        # una cifra detta di una regione che combacia con una media nazionale.
        # Le alternative finiscono nel riepilogo, non solo nel dettaglio: se
        # stanno solo in `cifre` nessuno le legge, ed e' il riepilogo che il
        # verificatore scorre riga per riga.
        "riepilogo": [f"{voce['numero']} ({voce['dove']}) -> "
                      f"{voce['corrisponde_a'] or 'NESSUNA CORRISPONDENZA, piu vicino: ' + str(voce['valore_piu_vicino'])}"
                      + (f"   [oppure: {'; '.join(voce['alternative'])}]" if voce["alternative"] else "")
                      + (f"   [ATTENZIONE: {voce['fuori_anno']}]" if voce.get("fuori_anno") else "")
                      for voce in cifre],
        "cifre": cifre,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codice")
    parser.add_argument("--livello", default=None)
    parser.add_argument("--bozza", default=None, help="file JSON della bozza (default: stdin)")
    parser.add_argument("--salva", nargs="?", const=BOZZE, default=None,
                        help=f"congela la bozza controllata (cartella, default {BOZZE})")
    parser.add_argument("--cerca", default=None, metavar="NUMERO",
                        help="che cosa può essere questo numero nel dossier (non serve una bozza)")
    args = parser.parse_args(argv)

    # `--cerca` non legge nessuna bozza: è l'interrogazione, non lo
    # spazzolamento. Sta qui e non in un comando a parte perché il contratto
    # del verificatore gli concede un solo eseguibile, e un comando in più
    # allargherebbe il suo perimetro senza dargli niente di nuovo.
    bozza = None
    if args.cerca is None:
        testo = open(args.bozza, encoding="utf-8").read() if args.bozza else sys.stdin.read()
        try:
            bozza = json.loads(testo)
        except json.JSONDecodeError as errore:
            print(json.dumps({"errore": f"la bozza non è JSON valido: {errore}"}, ensure_ascii=False))
            return 2

    dossier = costruisci(args.codice, args.livello)
    if dossier is None:
        print(json.dumps({"errore": f"indicatore sconosciuto: {args.codice}"}, ensure_ascii=False))
        return 2

    # La serie intera, non la matrice ridotta del dossier: una cifra vera presa
    # da metà serie non è inventata, e questo comando misura le invenzioni.
    famiglia, grezzo = risolvi(args.codice)
    vista = build_indicator_view(famiglia, grezzo)
    livelli = {livello["key"]: livello for livello in vista["levels"]}
    matrice = matrice_per_nome(livelli[dossier["livello"]])

    if args.cerca is not None:
        try:
            cercato = _numero(args.cerca.strip())
        except ValueError:
            print(json.dumps({"errore": f"non è un numero: {args.cerca}"}, ensure_ascii=False))
            return 2
        compatibili = cerca(dossier, matrice, cercato)
        print(json.dumps({"codice": dossier["codice"], "cercato": cercato,
                          "compatibili": len(compatibili), "voci": compatibili},
                         ensure_ascii=False, indent=1))
        return 0

    esito = controlla(dossier, matrice, bozza)
    esito["impronta"] = impronta(bozza)
    if args.salva:
        cartella = args.salva if os.path.isdir(args.salva) or not args.salva.endswith(".json") else None
        if cartella:
            os.makedirs(cartella, exist_ok=True)
            percorso = os.path.join(cartella, f"{args.codice.replace(':', '-')}.json")
        else:
            percorso = args.salva
            os.makedirs(os.path.dirname(percorso) or ".", exist_ok=True)
        with open(percorso, "w", encoding="utf-8") as handle:
            json.dump(bozza, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
        # È il pezzo che rende vera la verifica: da qui in poi l'articolo
        # viaggia come file, e chi lo pubblica non lo ribatte.
        esito["bozza_salvata"] = os.path.abspath(percorso)

    json.dump(esito, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
