"""Le storie che stanno nei dati, trovate dal codice invece che a occhio.

Un giornalista guarda una serie e trova la storia. Quel passaggio e'
calcolabile, ed e' l'unico modo perche' la struttura di un articolo nasca dai
dati invece che da uno scheletro fisso.

Ogni rilevatore restituisce zero o piu' **angoli**. Un angolo e' un fatto
strutturale della serie, con la sua forza, le cifre che lo sostengono, i
territori e gli anni coinvolti, e la cautela che va detta se c'e'. Non e' prosa
da copiare: e' materiale su cui costruire.

    {
      "type": "rottura-di-pendenza",
      "strength": 0.72,           # 0..1, confrontabile fra tipi diversi
      "figures": {...},           # le cifre citabili, gia' calcolate
      "diagnostica": {...},       # cio' che ordina l'angolo e non si scrive mai
      "territories": [...],
      "years": [2013],
      "caution": "..." | None,
    }

**La forza e' confrontabile fra tipi diversi.** E' la proprieta' che rende
l'inventario ordinabile, ed e' anche la piu' facile da sbagliare: ogni
rilevatore normalizza la propria dimensione dell'effetto in 0..1 con una
formula dichiarata nel proprio docstring, e nessuna formula usa una soglia
scelta a occhio senza dire perche'.

Stdlib pura per scelta: nessun import da `app`, nessun CSV, nessuna rete.
L'ingresso e' una matrice `{anno: {territorio: valore}}` e basta, quindi i test
girano su serie inventate di cinque righe e non su centomila righe di dati veri.
"""
from __future__ import annotations

import statistics

from packs import calibration

# Sotto questi minimi un rilevatore non parla. Non sono prudenza generica:
# una rottura di pendenza chiede due tratti su cui una retta abbia senso, e
# quattro punti per tratto e' il minimo sotto cui la retta interpola il rumore.
MIN_YEARS_FOR_TREND = 6
MIN_YEARS_PER_SEGMENT = 4
# Sotto dodici territori una dispersione descrive i pochi che rispondono, non
# il paese. E' la stessa soglia che `indicator_brief` usa per la correlazione.
MIN_TERRITORIES = 12

# Una forza sotto questa non merita di essere proposta a chi scrive: e' un
# effetto che esiste nei decimali e non nella storia.
FLOOR = 0.15


# --------------------------------------------------------------------------
# minuteria statistica, stdlib
# --------------------------------------------------------------------------

def _slope(points):
    """Pendenza dei minimi quadrati su [(x, y), ...]. None se indefinita."""
    if len(points) < 2:
        return None
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator


def _residual_sum(points):
    """Somma dei quadrati dei residui rispetto alla retta dei minimi quadrati."""
    slope = _slope(points)
    if slope is None:
        return 0.0
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    intercept = mean_y - slope * mean_x
    return sum((y - (slope * x + intercept)) ** 2 for x, y in points)


def _scale(values):
    """Una scala per rendere adimensionali le differenze su questa serie.

    Lo scarto interquartile quando c'e', altrimenti l'escursione. Serve a
    confrontare un indicatore in euro con uno in punti percentuali senza che il
    primo vinca sempre per via dell'unita' di misura.
    """
    clean = sorted(v for v in values if v is not None)
    if len(clean) < 4:
        span = (max(clean) - min(clean)) if clean else 0.0
        return span or 1.0
    half = len(clean) // 2
    lower = statistics.median(clean[:half])
    upper = statistics.median(clean[-half:])
    return (upper - lower) or (max(clean) - min(clean)) or 1.0


def _clamp(value):
    return max(0.0, min(1.0, value))


def _saturate(ratio):
    """Da un rapporto senza tetto a una forza in 0..1, senza mai arrivarci.

    `ratio / (1 + ratio)`: monotona, quindi due effetti diversi danno due forze
    diverse. Serviva perche' le prime formule tagliavano a 1,00 e producevano
    pareggi fra angoli che non erano affatto alla pari: su ter-105 due salti di
    graduatoria molto diversi uscivano tutti e due a 1,00, e l'ordinamento,
    che e' il prodotto di questo modulo, non ordinava piu' niente.
    """
    ratio = max(0.0, ratio)
    return ratio / (1 + ratio)


def annual_means(matrix):
    """{anno: media semplice dei territori che rispondono}, anni ordinati.

    Media semplice dei valori regionali, come tutto il resto del progetto: non
    e' l'aggregato nazionale ponderato, e chi scrive deve saperlo.
    """
    means = {}
    for year in sorted(matrix):
        values = [v for v in matrix[year].values() if v is not None]
        if values:
            means[year] = sum(values) / len(values)
    return means


def _ranks(row, higher_first=True):
    """{territorio: posizione} per un anno, 1 e' il primo. Pareggi: ordine stabile."""
    present = [(name, value) for name, value in row.items() if value is not None]
    present.sort(key=lambda pair: (-pair[1] if higher_first else pair[1], pair[0]))
    return {name: position for position, (name, _) in enumerate(present, start=1)}


# Le cifre che servono a **ordinare** un angolo e non a raccontarlo. Restano
# nel pacchetto, perche' la calibrazione e i test le leggono, ma non arrivano
# mai a chi scrive: `packs/build.render` non le stampa.
#
# Non e' una preferenza di stile, e' una misura. Nella prima run i quattro
# giudici ciechi, indipendenti l'uno dall'altro, hanno indicato **tutti e
# quattro** come paragrafo piu' freddo quello che trascriveva pendenze di
# regressione e varianza spiegata. E l'angolo `rottura-di-pendenza`, che e'
# quello che le produce, ha perso due giudizi su due.
#
# La regola per classificare: **diagnostica se il numero non e' nell'unita'
# dell'indicatore e il suo significato richiede di conoscere il metodo.** Una
# pendenza dipende dalla finestra su cui si adatta la retta; una quota spiegata
# viene da un rapporto fra residui; uno z modificato dalla deviazione assoluta
# mediana. Nessuna delle tre dice niente a chi legge, e tutte e tre sembrano
# precise. Invece "otto volte piu' largo del salto tipico" resta, perche' e'
# leggibile ad alta voce.
DIAGNOSTIC_FIGURES = frozenset((
    "pendenza_prima",
    "pendenza_dopo",
    "pendenza_prima_meta",
    "pendenza_seconda_meta",
    "quota_spiegata",
    "z_modificato",
    "salto_tipico",
))


def split_figures(figures):
    """(citabili, diagnostiche). L'unica porta fra le due, cosi' si sposta in un posto solo."""
    citable, diagnostic = {}, {}
    for field, value in figures.items():
        (diagnostic if field in DIAGNOSTIC_FIGURES else citable)[field] = value
    return citable, diagnostic


def _angle(kind, strength, figures, territories=(), years=(), caution=None):
    """Un angolo. `raw` e' la dimensione dell'effetto, `strength` il suo posto.

    I due campi coincidono finche' nessuno calibra: `find` sostituisce
    `strength` con la posizione dell'effetto nella distribuzione del proprio
    tipo, perche' ordinare per dimensione grezza vuol dire ordinare per tipo.
    Vedi `packs/calibration.py`.

    `figures` esce spaccato in due: le cifre citabili e la `diagnostica`, che
    serve a ordinare e non si scrive mai. Vedi `DIAGNOSTIC_FIGURES`.
    """
    value = round(_clamp(strength), 3)
    citable, diagnostic = split_figures(figures)
    return {
        "type": kind,
        "strength": value,
        "raw": value,
        "figures": citable,
        "diagnostica": diagnostic,
        "territories": list(territories),
        "years": list(years),
        "caution": caution,
    }


# --------------------------------------------------------------------------
# i rilevatori
# --------------------------------------------------------------------------

def slope_break(matrix):
    """L'anno in cui la serie cambia pendenza.

    Si prova ogni anno come punto di rottura, si adattano due rette invece di
    una, e si tiene quello che riduce di piu' i residui. Forza: la quota di
    residuo che la rottura spiega, `1 - RSS(due rette) / RSS(una retta)`, che e'
    zero quando la rottura non serve e tende a uno quando la serie e' due rette
    diverse incollate.

    E' il rilevatore che copre il caso piu' importante e oggi assente: una serie
    che cambia regime, che e' quasi sempre la storia vera di un indicatore
    territoriale.
    """
    means = annual_means(matrix)
    if len(means) < MIN_YEARS_FOR_TREND:
        return []
    points = [(year, value) for year, value in means.items()]
    whole = _residual_sum(points)
    if whole <= 0:
        return []

    best = None
    for index in range(MIN_YEARS_PER_SEGMENT, len(points) - MIN_YEARS_PER_SEGMENT + 1):
        left, right = points[:index], points[index - 1:]
        split = _residual_sum(left) + _residual_sum(right)
        gain = 1 - split / whole
        if best is None or gain > best[0]:
            best = (gain, points[index - 1][0], _slope(left), _slope(right))
    if best is None:
        return []

    gain, year, before, after = best
    if gain < FLOOR or before is None or after is None:
        return []
    turned = (before < 0) != (after < 0)
    return [_angle(
        "rottura-di-pendenza", gain,
        {"anno": year,
         "pendenza_prima": round(before, 4),
         "pendenza_dopo": round(after, 4),
         "cambia_verso": turned,
         "quota_spiegata": round(gain, 3)},
        years=[year],
        caution="Una rottura nella serie puo' essere un cambio di metodo della "
                "fonte e non del fenomeno: va controllata contro le note "
                "metodologiche prima di raccontarla come un fatto.",
    )]


def acceleration(matrix):
    """La serie va nella stessa direzione ma a un'altra velocita'.

    Confronta la pendenza della prima meta' con quella della seconda, a parita'
    di verso. Forza: quanto la seconda pendenza si discosta dalla prima, in
    rapporto alla piu' grande delle due, cosi' un raddoppio vale 0,5 e un
    fermarsi vale 1.

    Distinto da `slope_break`: li' la serie cambia regime in un anno preciso,
    qui rallenta o accelera senza uno scalino.
    """
    means = annual_means(matrix)
    if len(means) < MIN_YEARS_FOR_TREND:
        return []
    points = [(year, value) for year, value in means.items()]
    half = len(points) // 2
    early, late = _slope(points[:half + 1]), _slope(points[half:])
    if early is None or late is None:
        return []
    if (early < 0) != (late < 0):
        return []  # cambio di verso: e' materia di slope_break, non di velocita'
    biggest = max(abs(early), abs(late))
    if biggest == 0:
        return []
    change = _saturate(abs(late - early) / biggest)
    if change < FLOOR:
        return []
    return [_angle(
        "accelerazione" if abs(late) > abs(early) else "rallentamento", change,
        {"pendenza_prima_meta": round(early, 4),
         "pendenza_seconda_meta": round(late, 4),
         "anni": [points[0][0], points[half][0], points[-1][0]]},
        years=[points[0][0], points[-1][0]],
    )]


def return_to_level(matrix, tolerance=0.02):
    """Il valore di oggi e' quello di allora, dopo esserne uscito.

    Cerca l'anno piu' lontano il cui valore medio coincide con l'ultimo entro
    `tolerance` della scala della serie, a patto che nel mezzo la serie se ne
    sia allontanata di almeno tre volte tanto. Senza quest'ultima condizione una
    serie piatta produrrebbe l'angolo tutti gli anni, che e' il modo in cui un
    rilevatore diventa rumore.

    Forza: quanto e' ampia l'escursione in mezzo, rapportata alla scala, piu' un
    premio per la distanza nel tempo.
    """
    means = annual_means(matrix)
    if len(means) < MIN_YEARS_FOR_TREND:
        return []
    years = sorted(means)
    scale = _scale(list(means.values()))
    last_year = years[-1]
    last = means[last_year]

    for year in years[:-MIN_YEARS_PER_SEGMENT]:
        if abs(means[year] - last) > tolerance * scale:
            continue
        between = [means[y] for y in years if year < y < last_year]
        if not between:
            continue
        excursion = max(abs(value - last) for value in between)
        if excursion < 3 * tolerance * scale:
            continue
        span = (last_year - year) / max(1, last_year - years[0])
        return [_angle(
            "ritorno-al-livello", 0.5 * _clamp(excursion / scale) + 0.5 * span,
            {"anno_di_allora": year,
             "valore_di_allora": round(means[year], 3),
             "anno_di_oggi": last_year,
             "valore_di_oggi": round(last, 3),
             "escursione_nel_mezzo": round(excursion, 3)},
            years=[year, last_year],
            caution="Tornare al livello di allora non vuol dire tornare alla "
                    "situazione di allora: la media coincide, la composizione no.",
        )]
    return []


def dispersion_trend(matrix):
    """Le distanze fra territori si allargano o si chiudono.

    Si prende lo scarto fra il primo e l'ultimo territorio in ogni anno, e se ne
    misura la pendenza. Forza: quanto e' cambiato il divario fra il primo e
    l'ultimo anno, in rapporto al divario iniziale.

    Riporta anche **da che parte** si e' chiusa, che e' la meta' della storia:
    un divario che si chiude perche' il fondo sale non e' un divario che si
    chiude perche' la testa scende.
    """
    years = sorted(matrix)
    gaps = {}
    tops, bottoms = {}, {}
    for year in years:
        values = [v for v in matrix[year].values() if v is not None]
        if len(values) < MIN_TERRITORIES:
            continue
        gaps[year] = max(values) - min(values)
        tops[year], bottoms[year] = max(values), min(values)
    if len(gaps) < MIN_YEARS_FOR_TREND:
        return []

    ordered = sorted(gaps)
    first, last = ordered[0], ordered[-1]
    if gaps[first] == 0:
        return []
    change = (gaps[last] - gaps[first]) / abs(gaps[first])
    if _saturate(abs(change)) < FLOOR:
        return []

    top_move = tops[last] - tops[first]
    bottom_move = bottoms[last] - bottoms[first]
    if abs(top_move) > abs(bottom_move) * 1.5:
        side = "dall'alto"
    elif abs(bottom_move) > abs(top_move) * 1.5:
        side = "dal basso"
    else:
        side = "dalle due parti insieme"

    return [_angle(
        "divario-che-si-allarga" if change > 0 else "divario-che-si-chiude",
        _saturate(abs(change)),
        {"divario_primo_anno": round(gaps[first], 3),
         "divario_ultimo_anno": round(gaps[last], 3),
         "variazione_relativa": round(change, 3),
         "si_muove": side,
         "spostamento_della_testa": round(top_move, 3),
         "spostamento_del_fondo": round(bottom_move, 3)},
        years=[first, last],
    )]


def rank_reversals(matrix, higher_first=True, top=3):
    """Chi ha scavalcato chi, e quando, restandoci.

    Solo i sorpassi che tengono: la coppia deve essere invertita nell'ultimo
    anno e restare invertita per almeno tre anni consecutivi. Un sorpasso di un
    anno e' rumore, e raccontarlo come un cambiamento e' un errore che le
    guardie numeriche non prendono, perche' ogni singola cifra e' giusta.

    Forza: la distanza in posizioni percorsa, sulla lunghezza della graduatoria.
    """
    years = sorted(matrix)
    if len(years) < MIN_YEARS_FOR_TREND:
        return []
    ranks = {year: _ranks(matrix[year], higher_first) for year in years}
    first, last = years[0], years[-1]
    shared = set(ranks[first]) & set(ranks[last])
    if len(shared) < MIN_TERRITORIES:
        return []

    found = []
    for one in sorted(shared):
        for other in sorted(shared):
            if one >= other:
                continue
            was = ranks[first][one] < ranks[first][other]
            now = ranks[last][one] < ranks[last][other]
            if was == now:
                continue
            held = 0
            for year in reversed(years):
                pair = ranks[year]
                if one not in pair or other not in pair:
                    break
                if (pair[one] < pair[other]) != now:
                    break
                held += 1
            if held < 3:
                continue
            distance = abs((ranks[last][one] - ranks[first][one]) -
                           (ranks[last][other] - ranks[first][other]))
            found.append((distance, held, one, other))

    found.sort(reverse=True)
    angles = []
    for distance, held, one, other in found[:top]:
        # `distance` somma i due spostamenti, quindi puo' superare la lunghezza
        # della graduatoria: su 101 province arrivava a 122 e tagliava a 1,00,
        # appiattendo sorpassi molto diversi sullo stesso valore.
        strength = _saturate(distance / len(shared))
        if strength < FLOOR:
            continue
        angles.append(_angle(
            "sorpasso", strength,
            {"posizioni_scambiate": distance,
             "anni_di_tenuta": held,
             "prima": {one: ranks[first][one], other: ranks[first][other]},
             "adesso": {one: ranks[last][one], other: ranks[last][other]}},
            territories=[one, other],
            years=[first, last],
        ))
    return angles


def outliers(matrix, threshold=3.5):
    """Il territorio che sta fuori scala, non solo primo o ultimo.

    Scarto assoluto mediano invece che deviazione standard: con venti valori una
    sola coda tira la media e la deviazione, e l'anomalia si nasconde nella
    misura che dovrebbe scovarla. La soglia 3,5 sullo z modificato e' quella di
    Iglewicz e Hoaglin.

    Forza: di quanto lo z modificato supera la soglia, saturando a tre volte.
    """
    years = sorted(matrix)
    if not years:
        return []
    row = {name: value for name, value in matrix[years[-1]].items() if value is not None}
    if len(row) < MIN_TERRITORIES:
        return []
    values = list(row.values())
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    mad = statistics.median(deviations)
    if mad == 0:
        return []

    angles = []
    for name, value in sorted(row.items(), key=lambda pair: -abs(pair[1] - median)):
        score = 0.6745 * (value - median) / mad
        if abs(score) < threshold:
            break
        angles.append(_angle(
            "valore-fuori-scala", _saturate(abs(score) / threshold - 1),
            {"valore": round(value, 3),
             "mediana": round(median, 3),
             "z_modificato": round(score, 2),
             "distanza_dalla_mediana": round(value - median, 3)},
            territories=[name],
            years=[years[-1]],
        ))
    return angles


def distribution_breaks(matrix, top=2):
    """Dove la graduatoria si spezza davvero, non dove finisce il podio.

    Il salto piu' largo fra due posizioni consecutive nell'ultimo anno. Forza:
    quanto quel salto e' piu' grande del salto tipico, saturando a cinque volte.
    Cosi' una graduatoria a scaletta regolare non produce nessun angolo, che e'
    il comportamento giusto: li' non c'e' nessuna spaccatura da raccontare.
    """
    years = sorted(matrix)
    if not years:
        return []
    row = [(name, value) for name, value in matrix[years[-1]].items() if value is not None]
    if len(row) < MIN_TERRITORIES:
        return []
    row.sort(key=lambda pair: -pair[1])
    steps = [(row[i][1] - row[i + 1][1], i) for i in range(len(row) - 1)]
    typical = statistics.median(size for size, _ in steps)
    if typical <= 0:
        return []

    angles = []
    for size, index in sorted(steps, reverse=True)[:top]:
        ratio = size / typical
        strength = _saturate(ratio - 1)
        if strength < FLOOR:
            continue
        angles.append(_angle(
            "graduatoria-spezzata", strength,
            {"dopo_la_posizione": index + 1,
             "salto": round(size, 3),
             "salto_tipico": round(typical, 3),
             "quante_volte_il_tipico": round(ratio, 2),
             "sopra": row[index][0], "sotto": row[index + 1][0]},
            territories=[row[index][0], row[index + 1][0]],
            years=[years[-1]],
        ))
    return angles


def against_the_grain(matrix):
    """Chi si e' mosso contro la direzione generale.

    E' il contro-esempio che impedisce di scrivere "e' cresciuto ovunque"
    quando non e' vero. Forza: la quota di territori controcorrente, saturata a
    un terzo, perche' oltre quella soglia non c'e' piu' una direzione generale
    da contraddire.
    """
    years = sorted(matrix)
    if len(years) < 2:
        return []
    first, last = matrix[years[0]], matrix[years[-1]]
    moves = {name: last[name] - first[name]
             for name in set(first) & set(last)
             if first.get(name) is not None and last.get(name) is not None}
    if len(moves) < MIN_TERRITORIES:
        return []
    overall = sum(moves.values()) / len(moves)
    if overall == 0:
        return []
    counter = sorted(name for name, move in moves.items() if (move < 0) != (overall < 0))
    if not counter:
        return []
    share = len(counter) / len(moves)
    return [_angle(
        "controcorrente", _clamp(share / (1 / 3)),
        {"quanti": len(counter), "su": len(moves),
         "movimento_medio": round(overall, 3),
         "movimenti": {name: round(moves[name], 3) for name in counter}},
        territories=counter,
        years=[years[0], years[-1]],
    )]


def group_divergence(matrix, groups):
    """Due gruppi di territori che si avvicinano o si allontanano.

    `groups` e' `{territorio: gruppo}`, tipicamente la macroarea. Si calcola la
    distanza fra le medie dei due gruppi piu' distanti nel primo e nell'ultimo
    anno. Forza: quanto e' cambiata quella distanza, in rapporto a quella
    iniziale.

    Serve perche' "il divario Nord-Sud" e' l'affermazione che questo progetto fa
    piu' spesso, ed e' quella che finora nessun rilevatore misurava: si guardava
    il primo contro l'ultimo territorio, che e' un'altra cosa.
    """
    years = sorted(matrix)
    if len(years) < 2 or not groups:
        return []

    def by_group(year):
        buckets = {}
        for name, value in matrix[year].items():
            group = groups.get(name)
            if group is None or value is None:
                continue
            buckets.setdefault(group, []).append(value)
        return {group: sum(v) / len(v) for group, v in buckets.items() if v}

    first, last = by_group(years[0]), by_group(years[-1])
    shared = sorted(set(first) & set(last))
    if len(shared) < 2:
        return []

    high = max(shared, key=lambda group: last[group])
    low = min(shared, key=lambda group: last[group])
    # **Distanze, quindi valori assoluti.** I due gruppi si scelgono sull'ordine
    # dell'**ultimo** anno, e nel primo quell'ordine puo' essere rovesciato: li'
    # `first[high] - first[low]` e' negativo, e non e' una distanza, e' una
    # distanza col segno di un ordinamento che non vale piu'. Con la sottrazione
    # firmata un divario fermo attraverso un sorpasso (da -10 a 10) risultava
    # +200% di divergenza, cioe' l'angolo piu' forte del pacchetto costruito su
    # una distanza che non si e' mossa di un punto.
    partenza = abs(first[high] - first[low])
    now = last[high] - last[low]          # >= 0 per costruzione: high e' il max
    invertito = (first[high] - first[low]) < 0
    if partenza == 0:
        return []
    change = (now - partenza) / partenza
    if _saturate(abs(change)) < FLOOR:
        return []
    return [_angle(
        "gruppi-che-divergono" if change > 0 else "gruppi-che-convergono",
        _saturate(abs(change)),
        {"gruppo_alto": high, "gruppo_basso": low,
         "distanza_primo_anno": round(partenza, 3),
         "distanza_ultimo_anno": round(now, 3),
         "variazione_relativa": round(change, 3),
         # Quando l'ordine si e' rovesciato, "il divario si e' allargato" e'
         # vero e insieme fuorviante: chi sta sopra oggi stava sotto allora, e un
         # articolo che non lo dicesse racconterebbe una crescita al posto di un
         # sorpasso. Il fatto viaggia col fatto, non lasciato dedurre.
         "ordine_invertito": invertito,
         "medie_ultimo_anno": {group: round(last[group], 3) for group in shared}},
        years=[years[0], years[-1]],
        caution="Medie semplici dei territori del gruppo, non aggregati "
                "ponderati: un'istituzione che pubblica lo stesso divario con "
                "i pesi ottiene un altro numero, ed entrambi sono corretti.",
    )]


def method_breaks(notes, years):
    """Le rotture di metodo dichiarate dalla fonte, come eventi datati.

    `notes` e' il testo libero della nota metodologica. Oggi lo legge a mano il
    verificatore, ed e' costato almeno un articolo: `ter-60` aveva costruito la
    propria tesi sulla finestra prima di un cambio di metodo senza dirlo.

    Non e' un rilevatore statistico, e la sua forza e' fissa e alta: una rottura
    di metodo che cade dentro la finestra dell'articolo non e' una storia fra le
    altre, e' un vincolo su tutto il resto.
    """
    if not notes or not years:
        return []
    import re

    span = range(min(years), max(years) + 1)
    found = sorted({int(hit) for hit in re.findall(r"\b(?:19|20)\d\d\b", notes)
                    if int(hit) in span})
    if not found:
        return []
    return [_angle(
        "rottura-di-metodo", 0.9,
        {"anni_citati_nella_nota": found, "nota": notes.strip()[:400]},
        years=found,
        caution="La serie prima e dopo questa data puo' non essere la stessa "
                "misura: un confronto che attraversa la rottura va dichiarato.",
    )]


# --------------------------------------------------------------------------
# l'inventario
# --------------------------------------------------------------------------

DETECTORS = (
    slope_break,
    acceleration,
    return_to_level,
    dispersion_trend,
    rank_reversals,
    outliers,
    distribution_breaks,
    against_the_grain,
)

# Gruppi di tipi che, sugli stessi territori, raccontano una storia sola.
#
# - la forma della distribuzione: su una serie con una regione fuori scala
#   sparano insieme "salto dopo il primo", "salto dopo il secondo" e "valore
#   fuori scala", che sono tre modi di dire "il Trentino sta lontanissimo";
# - i sorpassi: una regione che scala dodici posizioni ne scavalca tante, e
#   ognuno di quei sorpassi e' un angolo. Sono tutti "la Basilicata e' salita".
#
# Tipi di famiglie diverse sopravvivono insieme anche sullo stesso territorio,
# perche' li' i fatti sono davvero due: `sorpasso` e `controcorrente` sulla
# stessa regione dicono cose distinte, e sopprimerne uno sarebbe perdere
# materiale.
SAME_STORY_FAMILIES = (
    ("graduatoria-spezzata", "valore-fuori-scala"),
    ("sorpasso",),
)
SAME_STORY = tuple(kind for family in SAME_STORY_FAMILIES for kind in family)


def _family_of(kind):
    return next((family for family in SAME_STORY_FAMILIES if kind in family), None)


def _suppress_repeats(angles):
    """Toglie l'angolo piu' debole che ripete una storia gia' raccontata.

    L'angolo tolto non sparisce: resta nominato in `implied_by` di quello che
    lo assorbe, cosi' chi scrive sa che quella cifra e' disponibile e sa anche
    che non e' una seconda storia. La differenza fra le due cose e' tutta la
    ragione di questo modulo.
    """
    kept = []
    for angle in angles:
        family = _family_of(angle["type"])
        if family is None:
            kept.append(angle)
            continue
        touched = set(angle["territories"])
        covering = next(
            (other for other in kept
             if _family_of(other["type"]) is family and touched & set(other["territories"])),
            None)
        if covering is None:
            kept.append(angle)
        else:
            covering.setdefault("implied_by", []).append(
                {"type": angle["type"], "strength": angle["strength"],
                 "figures": angle["figures"]})
    return kept


def raw_angles(matrix, groups=None, notes=None, higher_first=True):
    """Gli angoli con la sola dimensione dell'effetto, non ordinati.

    Separato da `find` perche' e' cio' che serve alla calibrazione: per
    costruire la tabella dei quantili bisogna vedere le dimensioni grezze di
    tutto il catalogo, prima che qualcuno le trasformi.
    """
    matrix = {int(year): row for year, row in matrix.items() if row}
    angles = []
    for detector in DETECTORS:
        if detector is rank_reversals:
            angles.extend(detector(matrix, higher_first=higher_first))
        else:
            angles.extend(detector(matrix))
    angles.extend(group_divergence(matrix, groups or {}))
    angles.extend(method_breaks(notes, sorted(matrix)))
    return angles


def find(matrix, groups=None, notes=None, higher_first=True):
    """Tutti gli angoli di una serie, dal piu' forte al piu' debole.

    L'ordine e' il prodotto: e' quello che decide su che cosa aprira'
    l'articolo, e quindi che due indicatori diversi non aprano allo stesso modo.
    A parita' di forza si ordina per tipo, cosi' il risultato e' deterministico
    e due esecuzioni non producono due articoli diversi.
    """
    angles = raw_angles(matrix, groups, notes, higher_first)
    for angle in angles:
        angle["strength"] = round(_clamp(calibration.calibrate(
            angle["type"], angle["raw"])), 3)
    angles.sort(key=lambda angle: (-angle["strength"], -angle["raw"], angle["type"]))
    return _suppress_repeats(angles)


# Una rottura di metodo non e' una storia: e' un vincolo su tutte le altre.
# Modellarla come angolo era sbagliato, e si e' visto appena l'ho collegata
# alle note vere: con forza fissa 0,9 sarebbe diventata l'apertura di sessanta
# articoli territoriali su centotrentadue, e sessanta articoli avrebbero aperto
# su una nota metodologica invece che su un fatto del paese.
CONSTRAINT_TYPES = ("rottura-di-metodo",)


def split_constraints(angles):
    """(storie, vincoli). I vincoli non competono per l'apertura.

    Restano nel pacchetto, e con la stessa forza: chi scrive deve saperli, e
    l'articolo che attraversa una rottura senza dirlo e' un errore che nessuna
    guardia numerica prende, perche' ogni cifra e' giusta da entrambe le parti.
    """
    stories = [angle for angle in angles if angle["type"] not in CONSTRAINT_TYPES]
    constraints = [angle for angle in angles if angle["type"] in CONSTRAINT_TYPES]
    return stories, constraints


def total_strength(angles):
    """Quanta storia c'e' in questo indicatore, in una cifra sola.

    Serve a decidere la lunghezza dell'articolo: la somma con rendimenti
    decrescenti (il secondo angolo vale meta' del primo, il terzo un terzo)
    perche' dieci angoli deboli non fanno un articolo lungo quanto tre forti.
    """
    return round(sum(angle["strength"] / (index + 1)
                     for index, angle in enumerate(angles)), 3)
