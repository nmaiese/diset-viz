"""Il dossier di un indicatore: i numeri già calcolati, per chi deve scrivere.

Il principio della pipeline lite sta tutto qui: **Python calcola, il modello
interpreta**. A un agente non si chiede quale regione sia cresciuta di più e
di quanto, perché una somma sbagliata dentro una frase è indistinguibile da
una frase vera. Gli si chiede quale di questi fenomeni valga la pena
raccontare, che è l'unica domanda che un calcolo non risponde.

Non ci sono angoli con un punteggio: il dossier porta scarti, rotture e
inversioni già misurati e li chiama `anomalie`, cioè materiale da cui può
uscire una storia. Sceglierla è mestiere editoriale, non statistico.

    bin/py -m lab.dossier ter-30
    bin/py -m lab.dossier ter-30 bes-10AMB004 --out data/lab/dossier
    bin/py -m lab.dossier ter-30 --livello provincia --stdout
    bin/py -m lab.dossier --coda 1 --freschi 2025
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import re
import statistics
import sys

from app import sources
from app.atlas_catalog import get_atlas_catalog
from app.data import REGION_GEO_AREA
from app.indicator_notes import build_indicator_explain
from app.indicator_view import build_indicator_view

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFINIZIONI = os.path.join(RADICE, "data", "definitions", "istat_territoriali.csv")
USCITA = os.path.join("data", "lab", "dossier")

# Le tre ripartizioni con cui si racconta il divario: Istat separa Sud e Isole,
# qui stanno insieme come in `app/divari.py`.
AREA_PER_CHIAVE = {
    chiave: ("Mezzogiorno" if area in ("Sud", "Isole") else area)
    for chiave, area in REGION_GEO_AREA.items()
}

# Gli scarti temporali che hanno senso su una serie annuale. Il decennio è
# l'orizzonte in cui un divario territoriale si muove davvero.
PASSI = (1, 5, 10)

# Quanti parenti entrano nel dossier, e per quanti di loro si portano i valori
# regione per regione. La lista intera dei vicini di tema arriva a otto, ma una
# frase che confronta due indicatori sullo **stesso** territorio si può scrivere
# solo con i valori per territorio, e quelli costano una vista ciascuno.
PARENTI_MAX = 8
VARIANTI_CON_VALORI = 3

# Quanta della varianza fra territori deve stare **fra** i gruppi perché una
# divisione valga la pena di essere raccontata. È la soglia classica della
# bontà di adattamento (Jenks): sotto, i gruppi separano meno di quanto
# confondano e la classifica va letta come un continuo.
BONTA_MINIMA = 0.85
GRUPPI_MASSIMI = 4


def risolvi(codice):
    """`ter-30` o `ter:30` -> (famiglia, id grezzo)."""
    testo = codice.replace(":", "-", 1)
    prefisso, _, grezzo = testo.partition("-")
    for famiglia, meta in sources.SOURCES.items():
        if meta["acronym"] == prefisso:
            return famiglia, grezzo
    return sources.split_internal_id(codice)


def definizione_ufficiale(famiglia, grezzo):
    """La definizione che pubblica la fonte, testuale, o None.

    Solo per la famiglia territoriale: è l'unica per cui il progetto ha i
    metadati. Per le altre si tace, così chi scrive vede che la definizione
    manca invece di leggerne una dedotta dal nome dell'indicatore.
    """
    if famiglia != "territorial":
        return None
    try:
        with open(DEFINIZIONI, encoding="utf-8-sig", newline="") as handle:
            righe = {r["id"].strip(): r for r in csv.DictReader(handle, delimiter=";")}
    except OSError:
        return None
    riga = righe.get(str(grezzo).strip())
    if not riga or not (riga.get("definizione") or "").strip():
        return None
    campi = ("definizione", "dati_di_base", "fonti", "periodicita",
             "unita_territoriale", "anno_iniziale", "anno_finale", "note")
    return {campo: (riga.get(campo) or "").strip() for campo in campi}


def scala_umana(meta):
    """La frase che traduce l'unità in una vita, se il progetto ne ha una.

    La costruisce già `app/indicator_notes.py` per il blocco "Come leggere il
    dato" della pagina: ricalcolarla qui sarebbe una seconda verità sullo
    stesso fatto.
    """
    try:
        spiega = build_indicator_explain({
            "id": meta.get("id"),
            "indicator": meta.get("name"),
            "name": meta.get("name"),
            "theme": meta.get("theme"),
            "unit": meta.get("unit"),
            "archive": meta.get("archive") or "",
        })
    except Exception:
        return None
    return spiega.get("example") or None


def matrice_per_nome(livello):
    """{anno: {nome territorio: valore}}.

    Per nome e non per chiave slug: la legge chi deve scrivere una frase, e
    "liguria" non è un territorio che si possa nominare. Si costruisce da
    `territories` e non da `observations`, che copre solo l'ultimo anno.
    """
    nomi = {riga["key"]: riga["name"] for riga in livello["territories"]}
    fuori = {}
    for anno, riga in livello["matrix"].items():
        pulita = {nomi.get(chiave, chiave): valore
                  for chiave, valore in riga.items() if valore is not None}
        if pulita:
            fuori[int(anno)] = pulita
    return fuori


def _arrotonda(valore, cifre=2):
    return None if valore is None else round(float(valore), cifre)


def _serie(matrice, territorio):
    """[(anno, valore)] di un territorio, in ordine di anno."""
    return [(anno, matrice[anno][territorio])
            for anno in sorted(matrice) if territorio in matrice[anno]]


def _delta(matrice, anni, territorio, passo):
    """La differenza fra l'ultimo valore e quello di `passo` anni prima."""
    ultimo = anni[-1]
    prima = ultimo - passo
    if prima not in matrice or territorio not in matrice.get(prima, {}):
        return None
    if territorio not in matrice[ultimo]:
        return None
    return _arrotonda(matrice[ultimo][territorio] - matrice[prima][territorio])


def _classifica(ultimo, direzione):
    """L'ultimo anno, ordinato come lo legge la pagina.

    Rango 1 è il migliore quando l'indicatore ha un verso; quando non ce l'ha
    (indicatore di contesto) è semplicemente il valore più alto, e il campo
    `verso` del dossier lo dice a chi scrive.
    """
    crescente = direzione in ("lower_better", "higher_worse")
    ordinati = sorted(ultimo.items(), key=lambda voce: (voce[1] if crescente else -voce[1], voce[0]))
    valori = sorted(ultimo.values())
    mediana = statistics.median(valori)
    fuori = []
    for posizione, (territorio, valore) in enumerate(ordinati, start=1):
        fuori.append({
            "territorio": territorio,
            "valore": _arrotonda(valore),
            "rango": posizione,
            "percentile": _arrotonda(100 * (len(valori) - posizione) / max(1, len(valori) - 1), 1),
            "scarto_dalla_mediana": _arrotonda(valore - mediana),
        })
    return fuori


def _sintesi(ultimo):
    valori = list(ultimo.values())
    minimo = min(ultimo.items(), key=lambda voce: voce[1])
    massimo = max(ultimo.items(), key=lambda voce: voce[1])
    media = statistics.fmean(valori)
    return {
        "territori": len(valori),
        "media": _arrotonda(media),
        "mediana": _arrotonda(statistics.median(valori)),
        "minimo": {"territorio": minimo[0], "valore": _arrotonda(minimo[1])},
        "massimo": {"territorio": massimo[0], "valore": _arrotonda(massimo[1])},
        "spread": _arrotonda(massimo[1] - minimo[1]),
        "rapporto_max_min": _arrotonda(massimo[1] / minimo[1]) if minimo[1] else None,
        "coeff_variazione": _arrotonda(
            100 * statistics.pstdev(valori) / media, 1) if media else None,
    }


def _area_per_nome(livello):
    return {riga["name"]: AREA_PER_CHIAVE[riga["key"]]
            for riga in livello["territories"] if riga["key"] in AREA_PER_CHIAVE}


def _macroaree(livello, ultimo):
    """La media semplice per ripartizione, e il divario Nord-Mezzogiorno.

    Media semplice sulle regioni, non ponderata sulla popolazione: è la stessa
    che calcola la pagina, e va detto in una riga quando entra in un articolo.
    """
    area_per_nome = _area_per_nome(livello)
    per_area = {}
    for territorio, valore in ultimo.items():
        area = area_per_nome.get(territorio)
        if area:
            per_area.setdefault(area, []).append(valore)
    medie = {area: _arrotonda(statistics.fmean(valori)) for area, valori in sorted(per_area.items())}
    if "Nord" in medie and "Mezzogiorno" in medie:
        medie["divario_nord_mezzogiorno"] = _arrotonda(medie["Nord"] - medie["Mezzogiorno"])
    return medie


def _dinamica(matrice, anni, ultimo, sintesi):
    delta = {f"delta_{passo}a": {} for passo in PASSI}
    volatilita, rotture, inversioni = {}, [], []
    for territorio in sorted(ultimo):
        for passo in PASSI:
            valore = _delta(matrice, anni, territorio, passo)
            if valore is not None:
                delta[f"delta_{passo}a"][territorio] = valore
        serie = _serie(matrice, territorio)
        variazioni = [(serie[i][0], serie[i][1] - serie[i - 1][1]) for i in range(1, len(serie))]
        if len(variazioni) < 3:
            continue
        soltanto = [v for _, v in variazioni]
        scarto = statistics.pstdev(soltanto)
        volatilita[territorio] = _arrotonda(scarto)
        # Una rottura è un salto che non somiglia agli altri salti della stessa
        # serie: due deviazioni standard, e mai sotto un centesimo, altrimenti
        # una serie piatta produce venti rotture da rumore.
        for anno, variazione in variazioni:
            if scarto > 0.01 and abs(variazione) > 2 * scarto:
                rotture.append({"territorio": territorio, "anno": anno,
                                "salto": _arrotonda(variazione)})
        # Un'inversione: il verso degli ultimi tre anni contro quello dei
        # cinque precedenti. Non è una causa, è un cambio di direzione.
        recente = _delta(matrice, anni, territorio, 3)
        vecchio = _delta(matrice, [a for a in anni if a <= anni[-1] - 3] or anni, territorio, 5)
        if recente is not None and vecchio is not None and recente * vecchio < 0:
            inversioni.append({"territorio": territorio,
                               "prima": vecchio, "poi": recente})

    medie_annue = {anno: statistics.fmean(riga.values()) for anno, riga in matrice.items()}
    nazionale = {"ultimo": _arrotonda(medie_annue[anni[-1]])}
    for passo in PASSI:
        prima = anni[-1] - passo
        if prima in medie_annue:
            nazionale[f"delta_{passo}a"] = _arrotonda(medie_annue[anni[-1]] - medie_annue[prima])

    primo = matrice[anni[0]]
    spread_iniziale = max(primo.values()) - min(primo.values()) if len(primo) > 1 else None
    convergenza = None
    if spread_iniziale is not None and sintesi["spread"] is not None:
        differenza = sintesi["spread"] - spread_iniziale
        soglia = 0.05 * spread_iniziale if spread_iniziale else 0
        convergenza = {
            "anno_iniziale": anni[0],
            "spread_iniziale": _arrotonda(spread_iniziale),
            "spread_finale": sintesi["spread"],
            "verdetto": ("divergenza" if differenza > soglia
                         else "convergenza" if differenza < -soglia else "stabile"),
        }

    tutti = [(anno, territorio, valore)
             for anno, riga in matrice.items() for territorio, valore in riga.items()]
    massimo = max(tutti, key=lambda voce: voce[2])
    minimo = min(tutti, key=lambda voce: voce[2])
    return {
        **delta,
        "nazionale": nazionale,
        "media_per_anno": {anno: _arrotonda(valore) for anno, valore in sorted(medie_annue.items())},
        "convergenza": convergenza,
        "record": {
            "massimo_storico": {"anno": massimo[0], "territorio": massimo[1],
                                "valore": _arrotonda(massimo[2])},
            "minimo_storico": {"anno": minimo[0], "territorio": minimo[1],
                               "valore": _arrotonda(minimo[2])},
        },
        "volatilita": volatilita,
        "rotture": sorted(rotture, key=lambda r: -abs(r["salto"]))[:8],
        "inversioni": inversioni,
    }


def _anomalie(ultimo, classifica, dinamica, sintesi):
    """Le poche righe che dicono allo scout dove cercare contesto.

    Non sono una tesi e non sono ordinate per importanza editoriale: sono i
    punti in cui questa serie non somiglia a se stessa.
    """
    valori = sorted(ultimo.values())
    q1, q3 = statistics.quantiles(valori, n=4)[0], statistics.quantiles(valori, n=4)[2]
    scarto = 1.5 * (q3 - q1)
    fuori = []
    for voce in classifica:
        if voce["valore"] > q3 + scarto or voce["valore"] < q1 - scarto:
            fuori.append(f"{voce['territorio']}: {voce['valore']}, fuori scala "
                         f"rispetto alla mediana ({sintesi['mediana']})")
    delta5 = dinamica.get("delta_5a") or {}
    if delta5:
        ordinati = sorted(delta5.items(), key=lambda voce: voce[1])
        fuori.append(f"{ordinati[-1][0]}: {ordinati[-1][1]:+} in cinque anni, "
                     f"la variazione più alta della serie")
        fuori.append(f"{ordinati[0][0]}: {ordinati[0][1]:+} in cinque anni, "
                     f"la variazione più bassa della serie")
    for rottura in dinamica["rotture"][:3]:
        fuori.append(f"{rottura['territorio']}: salto di {rottura['salto']:+} nel {rottura['anno']}")
    for inversione in dinamica["inversioni"][:3]:
        fuori.append(f"{inversione['territorio']}: cambia direzione, "
                     f"{inversione['prima']:+} nei cinque anni prima, {inversione['poi']:+} negli ultimi tre")
    if dinamica["convergenza"] and dinamica["convergenza"]["verdetto"] != "stabile":
        fuori.append(f"il divario è in {dinamica['convergenza']['verdetto']}: "
                     f"da {dinamica['convergenza']['spread_iniziale']} "
                     f"({dinamica['convergenza']['anno_iniziale']}) a {sintesi['spread']}")
    return fuori


def _radice(nome):
    """Il nome senza la parentesi finale, per riconoscere le varianti.

    "Tasso di occupazione (maschi)" e "Tasso di occupazione (totale)" sono lo
    stesso fenomeno diviso per sesso, e il catalogo lo dice solo nel nome: non
    c'è nessun campo che li lega. Sulla famiglia territoriale questa regola
    trova 41 gruppi con più di un membro, 112 indicatori in tutto.
    """
    testo = re.sub(r"\s*\([^()]*\)\s*$", "", nome or "").strip().lower()
    return re.sub(r"\s+", " ", testo)


def _codice_dal_percorso(percorso):
    """`/indicatore/tasso-di-occupazione-maschi/ter-177` -> `ter-177`.

    L'ultimo segmento del percorso canonico **è** il codice: prenderlo di lì
    evita di ricomporlo da acronimo e id, che è il gesto che una volta ha
    pubblicato una serie Istat sotto il nome di Eurostat.
    """
    return (percorso or "").rstrip("/").rsplit("/", 1)[-1]


def _valori_del_parente(codice, chiave_livello):
    """{territorio: valore} dell'ultimo anno di un altro indicatore, o None.

    Serve a chi scrive per la frase che vale davvero un link: lo stesso
    territorio letto su due indicatori. Senza questi valori il link resta
    decorativo, e chi verifica smentisce la cifra perché non è nel dossier.
    """
    try:
        famiglia, grezzo = risolvi(codice)
        vista = build_indicator_view(famiglia, grezzo)
    except Exception:
        return None, None
    if vista is None:
        return None, None
    livelli = {livello["key"]: livello for livello in vista["levels"]}
    livello = livelli.get(chiave_livello) or vista["levels"][0]
    matrice = matrice_per_nome(livello)
    if not matrice:
        return None, None
    anno = max(matrice)
    return anno, {territorio: _arrotonda(valore)
                  for territorio, valore in sorted(matrice[anno].items())}


def _parenti(vista, meta, famiglia, chiave_livello):
    """Gli altri indicatori del catalogo che raccontano una storia vicina.

    Tre relazioni, tutte già ricavabili da quello che il progetto ha:

    - `variante`: stesso nome a meno della parentesi finale, cioè lo stesso
      fenomeno diviso per sesso, età o grado. Sono i più utili e sono pochi,
      quindi per i primi tre si portano i valori regione per regione.
    - `stessa misura, altra famiglia`: stessa radice, famiglia diversa.
    - `stesso tema`: `vista["related"]`, che `app/indicator_view.py` calcola
      già dentro la vista che questo dossier costruisce.

    Serve a colmare un buco misurato: sei articoli su 364 linkano un altro
    indicatore, e nessuno strumento dava finora a chi scrive la lista dei
    vicini linkabili con il percorso già pronto.
    """
    mio_percorso = meta.get("canonical_path")
    radice = _radice(meta.get("name"))
    voci, visti = [], {mio_percorso}
    for item in get_atlas_catalog()["indicators"]:
        percorso = item.get("path")
        if percorso in visti or _radice(item.get("name")) != radice:
            continue
        visti.add(percorso)
        stessa_famiglia = item.get("catalog_family") == famiglia
        voci.append({
            "codice": _codice_dal_percorso(percorso),
            "nome": item.get("name"),
            "percorso_canonico": percorso,
            "anno_max": item.get("year_max"),
            "unita": item.get("unit"),
            "relazione": "variante" if stessa_famiglia else "stessa misura, altra famiglia",
        })
    for item in vista.get("related") or []:
        percorso = item.get("path")
        if percorso in visti or len(voci) >= PARENTI_MAX:
            continue
        visti.add(percorso)
        voci.append({
            "codice": _codice_dal_percorso(percorso),
            "nome": item.get("name"),
            "percorso_canonico": percorso,
            "anno_max": item.get("year_max"),
            "unita": item.get("unit"),
            "relazione": "stesso tema",
        })
    for voce in [v for v in voci if v["relazione"] != "stesso tema"][:VARIANTI_CON_VALORI]:
        anno, valori = _valori_del_parente(voce["codice"], chiave_livello)
        if valori:
            voce["anno"] = anno
            voce["valori"] = valori
    return voci


def _devianza(valori):
    """La somma degli scarti al quadrato dalla media. Zero se c'è un valore solo."""
    if len(valori) < 2:
        return 0.0
    media = statistics.fmean(valori)
    return sum((valore - media) ** 2 for valore in valori)


def _bonta(blocchi, totale):
    """Quanta varianza sta **fra** i gruppi invece che dentro, da 0 a 1.

    È il criterio di Jenks. Un raggruppamento vale quando i territori dentro
    un gruppo si somigliano molto più di quanto somiglino a quelli di un altro
    gruppo, e questo numero lo dice in un colpo solo. Cresce sempre aggiungendo
    gruppi, quindi non si guarda da solo: si cerca **il numero più piccolo** di
    gruppi che lo porta sopra la soglia.
    """
    if totale <= 0:
        return 0.0
    return 1 - sum(_devianza(blocco) for blocco in blocchi) / totale


def _gruppi(classifica, area_per_nome):
    """I gruppi in cui la classifica si spacca da sola, se si spacca.

    Non è una partizione geografica e non è una griglia di terzili. I terzili
    esistono sempre, anche su una distribuzione perfettamente continua, e
    stamparli vorrebbe dire dare a chi scrive un confine che nessun dato
    sostiene. Qui si cerca il numero **più piccolo** di gruppi che spiega la
    varianza sopra `BONTA_MINIMA`, provando ogni taglio possibile sui valori
    ordinati. Se nessuno ci arriva, la risposta è `null` con il motivo, e anche
    quella è un'informazione: la classifica va raccontata come un continuo.

    Il blocco riporta sempre come si comporta la ripartizione geografica sullo
    stesso metro, perché la domanda editoriale non è "quali gruppi ci sono"
    ma **"si dispongono come la geografia o no"**, e serve la risposta in tutti
    e due i versi. Un raggruppamento che ricalca Nord, Centro e Mezzogiorno è
    un risultato quanto uno che li taglia di traverso.
    """
    if len(classifica) < 8:
        return {"gruppi": None, "motivo": "troppo pochi territori per cercare dei gruppi"}
    ordinati = sorted(classifica, key=lambda voce: voce["valore"])
    valori = [voce["valore"] for voce in ordinati]
    totale = _devianza(valori)
    if totale <= 0:
        return {"gruppi": None, "motivo": "tutti i territori hanno lo stesso valore"}

    geografia = {}
    for voce in classifica:
        geografia.setdefault(area_per_nome.get(voce["territorio"]), []).append(voce["valore"])
    bonta_geografia = _arrotonda(_bonta(list(geografia.values()), totale), 2)

    scelta = None
    for quanti in range(2, GRUPPI_MASSIMI + 1):
        migliore = None
        for tagli in itertools.combinations(range(2, len(valori) - 1), quanti - 1):
            confini = (0,) + tagli + (len(valori),)
            blocchi = [valori[confini[i]:confini[i + 1]] for i in range(quanti)]
            if min(len(blocco) for blocco in blocchi) < 2:
                continue
            punteggio = _bonta(blocchi, totale)
            if migliore is None or punteggio > migliore[0]:
                migliore = (punteggio, confini)
        if migliore and migliore[0] >= BONTA_MINIMA:
            scelta = migliore
            break
    if scelta is None:
        return {"gruppi": None,
                "bonta_delle_macroaree": bonta_geografia,
                "motivo": f"nessuna divisione fino a {GRUPPI_MASSIMI} gruppi separa i territori "
                          f"abbastanza da valere: la classifica è un continuo"}

    bonta, confini = scelta
    fuori, concordi = [], 0
    for i in range(len(confini) - 1):
        blocco = ordinati[confini[i]:confini[i + 1]]
        aree = {}
        for voce in blocco:
            area = area_per_nome.get(voce["territorio"])
            if area:
                aree[area] = aree.get(area, 0) + 1
        dominante = max(aree.items(), key=lambda voce: voce[1]) if aree else (None, 0)
        concordi += dominante[1]
        fuori.append({
            "territori": [voce["territorio"] for voce in blocco],
            "da": blocco[0]["valore"],
            "a": blocco[-1]["valore"],
            "macroarea_prevalente": dominante[0],
        })
    sovrapposizione = _arrotonda(concordi / len(classifica), 2)
    return {
        "gruppi": fuori,
        "bonta": _arrotonda(bonta, 2),
        "bonta_delle_macroaree": bonta_geografia,
        "sovrapposizione_con_macroaree": sovrapposizione,
        "coincide_con_macroaree": sovrapposizione >= 0.8,
        "motivo": None,
    }


def _matrice_ridotta(matrice, anni):
    """Primo anno, uno di mezzo, gli ultimi tre. Il resto sta nel calcolo.

    La matrice intera è il doppio del dossier e chi scrive non deve rifare a
    mano nessuna sottrazione: i delta sono già calcolati sopra.
    """
    scelti = {anni[0], anni[len(anni) // 2], *anni[-3:]}
    return {anno: {territorio: _arrotonda(valore)
                   for territorio, valore in sorted(matrice[anno].items())}
            for anno in sorted(scelti)}


def _buchi(matrice, anni, livello):
    fuori = []
    for riga in livello["territories"]:
        mancanti = [anno for anno in anni if riga["name"] not in matrice.get(anno, {})]
        if mancanti:
            fuori.append({"territorio": riga["name"], "anni_mancanti": mancanti})
    return fuori


def _anni_mancanti(anni):
    """Gli anni che l'intervallo contiene e la serie no.

    `_buchi` non li vede: itera sugli anni presenti, quindi un anno assente per
    **tutti** i territori è invisibile. Su `ter-6` manca il 2004, l'anno in cui
    l'Istat ha spostato il periodo di rilevazione, e l'articolo lo diceva
    giustamente mentre il controllo delle cifre lo smentiva.
    """
    return [anno for anno in range(anni[0], anni[-1] + 1) if anno not in set(anni)]


def costruisci(codice, chiave_livello=None):
    """Il dossier completo di un indicatore, o None se non esiste."""
    famiglia, grezzo = risolvi(codice)
    vista = build_indicator_view(famiglia, grezzo)
    if vista is None:
        return None
    livelli = {livello["key"]: livello for livello in vista["levels"]}
    livello = livelli.get(chiave_livello or vista["default_level"])
    if livello is None:
        return None

    meta = vista["meta"]
    matrice = matrice_per_nome(livello)
    anni = sorted(matrice)
    ultimo = matrice[anni[-1]]
    classifica = _classifica(ultimo, meta["direction"])
    sintesi = _sintesi(ultimo)
    dinamica = _dinamica(matrice, anni, ultimo, sintesi)

    return {
        "codice": codice,
        "livello": livello["key"],
        "vintage": anni[-1],
        "meta": {
            "id": meta["id"],
            "nome": meta["name"],
            "unita": meta["unit"],
            "unita_del_valore": meta["value_unit"],
            "unita_della_variazione": meta["change_unit"],
            "percentuale": meta["percentage_like"],
            "verso": meta["direction"],
            "tema": meta["theme"],
            "fonte": meta["source_label"],
            "istituzione": meta["institution"],
            "archivio": meta["archive"],
            "percorso_canonico": meta["canonical_path"],
            "scala_umana": scala_umana(meta),
        },
        "definizione": definizione_ufficiale(famiglia, grezzo),
        "anni": anni,
        "anni_mancanti": _anni_mancanti(anni),
        "ultimo": classifica,
        "sintesi": sintesi,
        "macroaree": _macroaree(livello, ultimo),
        "gruppi": _gruppi(classifica, _area_per_nome(livello)),
        "parenti": _parenti(vista, meta, famiglia, livello["key"]),
        "dinamica": dinamica,
        "anomalie": _anomalie(ultimo, classifica, dinamica, sintesi),
        "matrice_ridotta": _matrice_ridotta(matrice, anni),
        "buchi": _buchi(matrice, anni, livello),
    }


def da_coda(quanti, anno_minimo):
    """I primi `quanti` codici della coda editoriale con dati almeno di `anno_minimo`.

    Il punteggio non lo calcola questo modulo: è `lab.coda`, che
    ordina il catalogo intero (cifre arretrate prima di tutto, poi le sezioni
    che mancano, poi se la pagina è indicizzabile). Qui si aggiunge l'unico
    filtro che la lite vuole e la coda non ha, **il dato dell'anno che chiedi**,
    e si riusa il predicato di incompletezza della coda invece di riscriverlo.

    Riscriverlo era un difetto: `written < sections` esclude proprio l'articolo
    che la coda mette per primo, quello **completo ma con le cifre più vecchie
    del dato**, che vale `+100` mentre una sezione mancante ne vale `10`. Oggi
    non se ne vede nessuno perché nessun articolo è arretrato, ma il giorno in
    cui Istat pubblica un anno nuovo l'insieme da rifare diventa esattamente
    quello, e `--coda` lo salterebbe tutto. Stessa sorte per un articolo a cui
    manca solo il `lead`, che è la meta description della pagina.

    L'unità della coda è la coppia (indicatore, livello), quindi si riporta
    anche il livello. Si tengono però **solo le righe al livello di default
    dell'indicatore**, e non è un dettaglio di comodo: `content/indicators/`
    ha un file per indicatore, non per coppia. Un articolo provinciale di un
    indicatore che di default è regionale finirebbe nello stesso `<key>.json`
    dell'articolo regionale, e siccome la pagina sceglie che cosa rendere
    leggendo `level`, il secondo articolo non si aggiungerebbe al primo: lo
    sostituirebbe, e la prosa regionale smetterebbe di comparire senza che
    niente diventi rosso.

    Il filtro giusto è quindi `livello == livello di default`, non "salta le
    province": 33 delle 67 righe provinciali della coda sono di indicatori che
    di default **sono** provinciali, e per quelle non c'è nessuna collisione. Le
    34 che restano fuori diventeranno raggiungibili quando lo store saprà
    tenere due articoli per indicatore.

    La vista si costruisce **una candidata alla volta e solo per le candidate**:
    è la parte cara di questa funzione, e montarne 668 per restituirne una
    sarebbe il costo di un catalogo intero per una riga.
    """
    from lab.coda import build_queue

    scelti = []
    for riga in build_queue():
        if len(scelti) >= quanti:
            break
        if not (riga["indexable"] and riga["year_max"] >= anno_minimo):
            continue
        if not (riga["missing"] or not riga["lead"] or riga["stale"]):
            continue
        if riga["level"] != _livello_di_default(riga["code"]):
            continue
        scelti.append({"codice": riga["code"], "livello": riga["level"],
                       "nome": riga["name"], "anno_max": riga["year_max"],
                       "punteggio": riga["score"]})
    return scelti


def _livello_di_default(codice):
    """Il livello su cui `lab.controlla` e `lab.pubblica` lavorano se nessuno lo dice.

    Un indicatore che non si risolve o senza vista restituisce `None`, che non
    coincide con nessun livello e quindi esclude la riga. È il verso giusto del
    dubbio: oggi le righe senza vista sono zero, e uno zero smette di essere
    zero senza avvisare.
    """
    try:
        famiglia, grezzo = risolvi(codice)
        vista = build_indicator_view(famiglia, grezzo)
    except Exception:
        return None
    return (vista or {}).get("default_level")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("codici", nargs="*", help="ter-30, bes-10AMB004, ...")
    parser.add_argument("--livello", default=None, help="regione (default) o provincia")
    parser.add_argument("--coda", type=int, default=None,
                        help="scegli i codici dalla coda editoriale invece di riceverli")
    parser.add_argument("--freschi", type=int, default=2025,
                        help="con --coda: solo indicatori con dati almeno di quest'anno")
    parser.add_argument("--out", default=USCITA, help=f"cartella di uscita (default {USCITA})")
    parser.add_argument("--stdout", action="store_true",
                        help="stampa il dossier invece dei percorsi (un codice solo)")
    args = parser.parse_args(argv)

    if bool(args.codici) == bool(args.coda):
        parser.error("servono dei codici, oppure --coda N, non tutti e due e non nessuno dei due")

    scelti = [{"codice": c, "livello": args.livello} for c in args.codici]
    if args.coda:
        scelti = da_coda(args.coda, args.freschi)
        if not scelti:
            json.dump({"dossier": [], "mancanti": [],
                       "coda": f"nessun indicatore incompleto con dati dal {args.freschi}"},
                      sys.stdout, ensure_ascii=False, indent=1)
            print()
            return 1

    os.makedirs(args.out, exist_ok=True)
    fatti, mancanti, ultimo = [], [], None
    for scelta in scelti:
        codice = scelta["codice"]
        dossier = costruisci(codice, scelta.get("livello") or args.livello)
        if dossier is None:
            mancanti.append(codice)
            continue
        ultimo = dossier
        percorso = os.path.join(args.out, f"{codice.replace(':', '-')}.json")
        with open(percorso, "w", encoding="utf-8") as handle:
            json.dump(dossier, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
        # Il livello sta nell'uscita e non solo dentro il file: `lab.controlla`
        # e `lab.pubblica` lo ricalcolano dal default se nessuno glielo dice, e
        # un livello che si perde qui non si vede piu' da nessuna parte finche'
        # non esce una prosa provinciale etichettata come regionale.
        fatti.append({"codice": codice, "percorso": os.path.abspath(percorso),
                      "livello": dossier["livello"],
                      "byte": os.path.getsize(percorso), "anomalie": dossier["anomalie"]})

    # `--stdout` ristampa il dossier già costruito, non ne costruisce un
    # secondo: montarlo due volte costava il doppio delle viste, e da quando il
    # blocco `parenti` ne apre una per variante quel doppio si vede.
    if args.stdout and len(scelti) == 1 and ultimo is not None:
        json.dump(ultimo, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
        print()
    else:
        json.dump({"dossier": fatti, "mancanti": mancanti}, sys.stdout,
                  ensure_ascii=False, indent=1)
        print()
    return 1 if mancanti else 0


if __name__ == "__main__":
    sys.exit(main())
