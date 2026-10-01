"""Il fatto "Da portarti via": una frase vera sul dato, a fine partita.

**Il contratto del campo.** Il campo si chiama `fact`, una stringa, e c'e' solo
a fine partita:

- **Chi e' maggiore?** `summary.fact`, dentro il `summary` che la risposta
  all'ultima domanda gia' porta (e che le altre non hanno: il "non prima della
  fine" viene dalla forma del payload). Accanto, `summary.fact_path`, il link
  della scheda dell'indicatore DEL FATTO: ogni coppia ha il suo indicatore, e il
  `dato.path` di fine partita e' uno solo, quindi il client lo usa se c'e'.
- **Ordina le regioni.** `fact` in cima al risultato della risposta, che e' gia'
  la fine (una risposta sola). La sessione (`GET .../session`) non lo ha.

Se una regola qui sotto non e' soddisfatta il campo **manca**: meglio nessuna
frase che una falsa. Una frase sola, al massimo 260 caratteri, un solo punto
finale, mai `;`, trattini lunghi, puntini o "n.d." (`validate`: se la guardia
finale fallisce si torna a None, mai si tronca).

**Da dove parte la frase.** Dall'errore del giocatore se ne ha fatto uno
("Hai messo A sopra B: A ha X, B ha Y"), altrimenti dal caso piu' distante fra i
valori. Per Ordina il payload ha gia' `positions` e `correct_order`: il primo
errore e' la prima coppia vicina messa al contrario, e senza errori il caso piu'
distante e' il primo contro l'ultimo. Per Chi e' maggiore il server non ricorda
le coppie sbagliate, e non lo fa con una tabella: la prima coppia sbagliata (con
una scelta vera, un tempo scaduto non e' un errore di giudizio) va **nel token
firmato** come INDICE, `sfida.e`, dentro lo stesso dizionario del punteggio, che
si azzera quando il giorno cambia. Le chiavi non servono: la coppia si
ricostruisce da `daily_compare(giorno, livello)["pairs"][e]`, deterministica
su giorno e livello, e il token e' gia' firmato. Un fatto per ogni risposta
sbagliata avrebbe dato il campo prima della fine. Senza errori (o con solo tempi
scaduti) la frase parte dalla coppia piu' distante delle dieci, per scarto
relativo `|a-b| / max(|a|, |b|)`: le unita' cambiano da una coppia all'altra,
quindi la distanza assoluta non si confronta. "La coppia piu' distante" si scrive
solo se e' vero: per la coppia con lo scarto piu' ampio, quando quella ha una frase
scrivibile e tutte le dieci sono entrate nella gara. Una coppia con valori di segno
opposto (un saldo) non entra, perche' il suo scarto relativo supera 1 e vincerebbe
sempre, e una coppia che non si valuta non si confronta. Altrimenti la frase usa la
testa neutra "Una coppia lontana", e solo per una coppia nella meta' piu' distante
della partita, o non esce.

**I numeri.** Vengono dai valori che la risposta gia' porta (Ordina) o dagli
stessi `_evaluate` di Chi e' maggiore: mai un numero esterno. Si scrivono come le
scrive il sito, `app/design/numfmt` (virgola decimale, migliaia con il punto,
`%` attaccato e le altre unita' dopo uno spazio fine). Il nome dell'indicatore e'
il `nome_leggibile` di `config/game_indicators.csv`, non quello Istat da 180
caratteri. Senza un'unita' scrivibile (`phrase_unit` e' None) o con due valori
che arrotondati sono uguali la frase non esce.

**Differenza e rapporto.**
- Un'unita' percentuale (e i punti percentuali) dicono lo scarto in **punti
  percentuali**, mai "volte".
- "Volte" solo con tutti i valori in gioco positivi, rapporto grezzo almeno 1,5
  (1,49 non diventa "1,5 volte"), il valore piu' piccolo almeno il 5% della
  mediana dei valori in gioco, e mai su un saldo.

**Il piazzamento ("18ª su 20")** solo con: direzione dell'indicatore nota
(`CURATED_DIRECTION` sull'id senza prefisso, o la direzione del manifesto BES),
tutti i territori previsti presenti (20 regioni, o le province del pool), stesso
anno per tutti e graduatoria a pari merito (`profiles._ranks` per le regioni,
`province_profile._graduatoria` per le province). Per gli indicatori campionari
(la colonna `campionario` di `config/game_indicators.csv`, i prefissi BES e
Multiscopo, e tutto il livello provinciale che e' BES) il numero esatto non si da:
si scrive "fra le ultime cinque" se il territorio vi sta davvero, altrimenti
niente. Al livello "stessa regione" il piazzamento non si scrive: la graduatoria e'
sulle province d'Italia, e chi gioca la leggerebbe come della regione.

**Giudizio.** Nessun verbo di causa e nessun "migliore" o "peggiore" dedotto
dall'ordine dei numeri. La direzione serve solo al piazzamento.
"""

from __future__ import annotations

import re
import statistics

from app import bes_data, game_daily, profiles, province_profile
from app.data import REGION_ORDER
from app.design import numfmt
from app.indicator_notes import CURATED_DIRECTION
from app.seo_titles import ARTICLED_PROVINCES, of_region

MAX_LEN = 260
# Il rapporto "volte" si dice solo da qui in su, e solo se il valore piu' piccolo
# non e' trascurabile rispetto ai valori in gioco.
TIMES_THRESHOLD = 1.5
SMALL_THRESHOLD = 0.05
LAST_N = 5
FORBIDDEN = ("—", "–", ";", "…", "n.d.")
_NON_FINAL_DOT = re.compile(r"\.(?!\d)(?!$)")


def validate(text):
    """La frase se rispetta la guardia finale, altrimenti None. Mai troncare: una
    frase tagliata e' una frase falsa. "Un solo punto finale" non vuol dire un solo
    carattere `.`: "1.234" e "ogni 1.000 abitanti" ne contengono, e restano buoni."""
    if not isinstance(text, str) or not text or len(text) > MAX_LEN:
        return None
    if not text.endswith(".") or _NON_FINAL_DOT.search(text):
        return None
    if any(v in text for v in FORBIDDEN) or re.search(r"\bnan\b", text, re.IGNORECASE):
        return None
    return text


# I nomi dei territori

def name_with_article(name, level):
    """"la Lombardia", "il Lazio", "l'Umbria", "le Marche" per le regioni, "il Sud
    Sardegna" per le due province che lo vogliono, il nome nudo per tutte le altre
    ("Trieste", "La Spezia"). Il genere delle regioni sta in `seo_titles.of_region`
    (il Piemonte, il Molise): si deriva da la', e un nome che non e' una delle venti
    regioni resta nudo, perche' l'articolo non si indovina."""
    if level == "regioni":
        if name not in REGION_ORDER:
            return name
        of_name = of_region(name)
        for form, article in (("della ", "la "), ("del ", "il "), ("delle ", "le "), ("dell'", "l'")):
            if of_name.startswith(form):
                return article + of_name[len(form):]
        return name
    return f"il {name}" if name in ARTICLED_PROVINCES else name


# Cifre e unita'

def _figure_text(value, extra=0):
    return numfmt.text(value, numfmt.magnitude_decimals(value) + extra)


def written_unit(unit):
    """L'unita' da scrivere dopo la cifra, o None se non ce n'e' una onesta. La regola
    del sito (`numfmt.phrase_unit`) e' la prima; se rinuncia solo perche' l'etichetta
    e' lunga ("metri quadrati per abitante") la frase la scrive per intero. Una coda
    dopo la virgola ("ogni 10.000 abitanti, tasso standardizzato") si lascia cadere:
    la base resta vera. Un'etichetta generica non e' un'unita': senza, la frase non
    esce."""
    written = numfmt.phrase_unit(unit)
    if written:
        return written
    raw = numfmt.lower_first((unit or "").strip())
    head, _, tail = raw.partition(",")
    if tail and head.startswith(("ogni ", "per ")):
        raw = head
    if not raw or raw in numfmt.GENERIC_UNITS or "," in raw or len(raw) > 40:
        return None
    return raw


def _with_unit(text, unit):
    return text + ("%" if unit == "%" else numfmt.THIN + unit)


def _distinct_figures(va, vb):
    """I testi di due valori diversi, con un decimale in piu' (fino a due) se
    arrotondati sarebbero uguali: "12,3 e 12,3" non dice niente. None se non si
    distinguono."""
    for extra in (0, 1, 2):
        ta, tb = _figure_text(va, extra), _figure_text(vb, extra)
        if ta != tb:
            return ta, tb
    return None


def relation(unit, name, values, va, vb):
    """La relazione fra i due valori, o "" se non ce n'e' una dicibile.

    Percentuale (e punti percentuali): lo scarto in punti, mai "volte". Altrimenti
    il rapporto, solo con valori in gioco tutti positivi, rapporto grezzo almeno
    1,5, il piu' piccolo almeno il 5% della mediana dei valori in gioco, e mai su un
    saldo. Il rapporto si decide sul valore grezzo: 1,49 non diventa "1,5 volte"."""
    high, low = max(va, vb), min(va, vb)
    written = numfmt.phrase_unit(unit)
    if written in ("%", numfmt.POINTS):
        gap = numfmt.text(high - low)
        return f", uno scarto di {gap} punti percentuali" if re.search(r"[1-9]", gap) else ""
    if "saldo" in (name or "").lower():
        return ""
    if not values or min(values) <= 0 or low <= 0:
        return ""
    if low < SMALL_THRESHOLD * statistics.median(values):
        return ""
    ratio = high / low
    if ratio < TIMES_THRESHOLD:
        return ""
    return f", un rapporto di {numfmt.text(ratio, 1)} volte"


# Il piazzamento

def direction(ind_id, scope):
    """"higher_better", "lower_better" o None (non si giudica). `higher_worse`
    ordina come `lower_better`. Mai l'euristica sul nome (`direction_for`): una
    direzione indovinata darebbe un piazzamento falso."""
    if scope == "province":
        info = bes_data.get_bes_manifest("provincia").get(game_daily.provincial_id(ind_id))
        raw = (info or {}).get("direction")
    elif ind_id.startswith("bes:"):
        info = bes_data.get_bes_manifest("regione").get(ind_id[len("bes:"):])
        raw = (info or {}).get("direction")
    else:
        raw = CURATED_DIRECTION.get(ind_id.split(":", 1)[-1])
    if raw == "higher_better":
        return "higher_better"
    if raw in ("lower_better", "higher_worse"):
        return "lower_better"
    return None


def is_sample_survey(ind_id, scope):
    """Il numero esatto della posizione non regge su un'indagine campionaria, la
    fascia si'. Lo dice la colonna `campionario` di `config/game_indicators.csv`,
    perche' un prefisso non basta (`426` e' Multiscopo, `57` Forze di lavoro, `72` ICT
    nelle imprese). BES e Multiscopo restano campionari per prefisso, il livello
    provinciale e' tutto BES, e un id che non sta nel CSV, nel dubbio, e' campionario."""
    if scope == "province" or ind_id.startswith(("bes:", "multiscopo:")):
        return True
    flags = {i["id"]: i["sample_survey"] for i in game_daily.game_indicators()}
    return flags.get(ind_id, True)


def placement_from_values(values, key, rank_direction, is_sample, scope, expected):
    """"18ª su 20", "fra le ultime cinque" o None, sui valori di TUTTI i territori
    dello stesso anno. None senza direzione, senza copertura completa (`attesi`
    territori, tutti con un valore) o per un territorio che non c'e'. A pari merito,
    come `profiles._ranks` e `province_profile._graduatoria`: due valori uguali
    hanno la stessa posizione."""
    if rank_direction is None or key not in values or len(values) != expected:
        return None
    if any(v is None for v in values.values()):
        return None
    if scope == "regioni":
        ranking = profiles._ranks(values, rank_direction)
    else:
        ranking = province_profile._graduatoria(values, rank_direction)
    place, total = ranking[key], len(values)
    if is_sample:
        return "fra le ultime cinque" if place >= total - LAST_N + 1 else None
    return f"{place}ª su {total}"


def placement(level, indicator, key):
    """Il piazzamento di un territorio per l'indicatore del gioco, dai dati veri.
    Si legge dalla stessa funzione che ha composto la sfida e solo se l'anno e'
    quello del gioco. Al livello "stessa regione" niente: la graduatoria e' sulle
    province d'Italia e si leggerebbe come della regione."""
    if level == "stessa_regione":
        return None
    scope = "regioni" if level == "regioni" else "province"
    ind_id = indicator["id"]
    found = game_daily._indicator_rows({"id": ind_id}, scope)
    if found is None or found[0] != indicator["year"]:
        return None
    expected = len(REGION_ORDER) if scope == "regioni" else len(game_daily.province_pool())
    values = {r["key"]: r["value"] for r in found[1]}
    return placement_from_values(
        values, key, direction(ind_id, scope), is_sample_survey(ind_id, scope), scope, expected,
    )


# La frase

LEAD_INS = {
    "errore": "Hai messo {a} sopra {b}: ",
    "distante": "La coppia più distante: ",
    "lontana": "Una coppia lontana: ",
    "perfetto": "Tutto al posto giusto, con la distanza maggiore fra il primo e l'ultimo: ",
}


def sentence(level, indicator, case, a, b, values):
    """La frase di un caso ("errore", "distante", "lontana" o "perfetto") o None. `a` e `b` sono
    `{"name", "key", "value"}`, `valori` tutti i valori in gioco (per il rapporto).
    La relazione e' la prima cosa che salta se la frase sfora la lunghezza."""
    unit = written_unit(indicator.get("unit"))
    if not unit or a.get("value") is None or b.get("value") is None:
        return None
    if a["value"] == b["value"]:
        return None
    texts = _distinct_figures(a["value"], b["value"])
    if texts is None:
        return None
    name_a = name_with_article(a["name"], level)
    name_b = name_with_article(b["name"], level)
    name = numfmt.lower_first(indicator["name"])
    placement_text = placement(level, indicator, a["key"])
    place = f" ({placement_text})" if placement_text else ""
    head = LEAD_INS[case].format(a=name_a, b=name_b)
    for with_relation in (True, False):
        relation_text = relation(indicator["unit"], indicator["name"], values, a["value"], b["value"]) if with_relation else ""
        text = (f"{head}per «{name}» ({indicator['year']}) {name_a} ha {_with_unit(texts[0], unit)}{place}, "
                f"{name_b} ha {_with_unit(texts[1], unit)}{relation_text}.")
        if validate(text):
            return text
    return None


def _row(r):
    return {"name": r["region"], "key": r["region_key"], "value": r["value"]}


# Ordina le regioni

def order_fact(level, indicator, positions, correct_order):
    """Il fatto di fine partita di Ordina, o None. `indicatore` e' quello del gioco
    (`id`, `name`, `unit`, `year`), `positions` le righe nell'ordine del giocatore
    (con `value`) e `correct_order` quelle nell'ordine giusto."""
    if not isinstance(positions, list) or not isinstance(correct_order, list) or len(positions) < 2:
        return None
    moves = sorted(positions, key=lambda r: r.get("guessed_position", 0))
    values = [r["value"] for r in moves]
    if any(v is None for v in values):
        return None
    for above, below in zip(moves, moves[1:]):
        if above["value"] < below["value"]:
            return sentence(level, indicator, "errore", _row(above), _row(below), values)
    if len(correct_order) < 2:
        return None
    return sentence(level, indicator, "perfetto", _row(correct_order[0]), _row(correct_order[-1]), values)


# Chi e' maggiore?

def signed_error(previous, day, index, outcome, choice):
    """Il pezzo di `sfida` che il token firma per ricordare la PRIMA coppia sbagliata:
    `{"e": indice}`, o niente. `precedente` e' il `sfida` del token prima di questa
    risposta. Vale solo per il giorno di oggi, e solo con una scelta vera: un tempo
    scaduto non dice quale lato il giocatore aveva in mente."""
    if previous.get("d") == day and isinstance(previous.get("e"), int):
        return {"e": previous["e"]}
    if not outcome["correct"] and choice in ("region_a", "region_b"):
        return {"e": index}
    return {}


def _compare_row(t):
    return {"name": t["name"], "key": t["key"], "value": t["value"]}


def compare_fact(level, pairs, error_index, evaluate):
    """`{"fact", "path"}` di fine partita di Chi e' maggiore, o None. `coppie` sono le
    dieci della sfida, `indice_errore` il `sfida.e` del token e `valuta(coppia,
    "region_a")` i valori veri della coppia (gli stessi `_evaluate` della risposta). Con
    un errore la frase parte da li' ("Hai messo A sopra B": A e' il piu' basso, e'
    quello che il giocatore ha scelto), altrimenti dalla coppia piu' distante per
    scarto relativo (`_widest_fact`)."""
    if isinstance(error_index, int) and 0 <= error_index < len(pairs):
        outcome = evaluate(pairs[error_index], "region_a")
        if outcome is not None:
            high, low = sorted((outcome["a"], outcome["b"]), key=lambda t: t["value"], reverse=True)
            text = sentence(level, pairs[error_index]["indicator"], "errore",
                            _compare_row(low), _compare_row(high), [high["value"], low["value"]])
            if text:
                return {"fact": text, "path": outcome["indicator"].get("path")}
    return _widest_fact(level, pairs, evaluate)


def _widest_fact(level, pairs, evaluate):
    """La frase sulla coppia piu' distante, o None. Prima la gara, poi la frase: la
    coppia con lo scarto relativo piu' ampio e' "la piu' distante" solo se ha una frase
    scrivibile e se tutte le coppie sono entrate nella gara. Escono dalla gara una
    coppia che non si valuta (non si sa quanto e' distante) e una con valori di segno
    opposto (lo scarto relativo supera 1: il saldo vincerebbe sempre). Altrimenti
    "Una coppia lontana", per la prima scrivibile nella meta' piu' distante delle
    coppie in gara: mai l'ultima rimasta, che lontana puo' non esserlo."""
    ranked, complete = [], True
    for pair in pairs:
        outcome = evaluate(pair, "region_a")
        if outcome is None:
            complete = False
            continue
        high, low = sorted((outcome["a"], outcome["b"]), key=lambda t: t["value"], reverse=True)
        if high["value"] > 0 > low["value"]:
            complete = False
            continue
        maximum = max(abs(high["value"]), abs(low["value"]))
        gap = 0.0 if maximum == 0 else (high["value"] - low["value"]) / maximum
        ranked.append((gap, pair, outcome, high, low))
    if not ranked:
        return None
    # A pari scarto vince la prima coppia della partita (l'ordinamento e' stabile). La
    # meta' piu' distante comprende chi e' a pari merito con l'ultima che ci sta.
    ranked.sort(key=lambda r: -r[0])
    cutoff = ranked[(len(ranked) + 1) // 2 - 1][0]
    for position, (gap, pair, outcome, high, low) in enumerate(r for r in ranked if r[0] >= cutoff):
        if gap == 0:
            break
        case = "distante" if position == 0 and complete else "lontana"
        text = sentence(level, pair["indicator"], case, _compare_row(high), _compare_row(low),
                        [high["value"], low["value"]])
        if text:
            return {"fact": text, "path": outcome["indicator"].get("path")}
    return None
