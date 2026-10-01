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
finale, mai `;`, trattini lunghi, puntini o "n.d." (`valida`: se la guardia
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
ricostruisce da `compare_del_giorno(giorno, livello)["pairs"][e]`, deterministica
su giorno e livello, e il token e' gia' firmato. Un fatto per ogni risposta
sbagliata avrebbe dato il campo prima della fine. Senza errori (o con solo tempi
scaduti) la frase parte dalla coppia piu' distante delle dieci, per scarto
relativo `|a-b| / max(|a|, |b|)`: le unita' cambiano da una coppia all'altra,
quindi la distanza assoluta non si confronta.

**I numeri.** Vengono dai valori che la risposta gia' porta (Ordina) o dagli
stessi `_valuta` di Chi e' maggiore: mai un numero esterno. Si scrivono come le
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
(BES, Multiscopo, e tutto il livello provinciale che e' BES) il numero esatto non
si da: si scrive "fra le ultime cinque" se il territorio vi sta davvero, altrimenti
niente.

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
SOGLIA_VOLTE = 1.5
SOGLIA_PICCOLO = 0.05
ULTIME = 5
VIETATI = ("—", "–", ";", "…", "n.d.")
_PUNTO_NON_FINALE = re.compile(r"\.(?!\d)(?!$)")


def valida(testo):
    """La frase se rispetta la guardia finale, altrimenti None. Mai troncare: una
    frase tagliata e' una frase falsa. "Un solo punto finale" non vuol dire un solo
    carattere `.`: "1.234" e "ogni 1.000 abitanti" ne contengono, e restano buoni."""
    if not isinstance(testo, str) or not testo or len(testo) > MAX_LEN:
        return None
    if not testo.endswith(".") or _PUNTO_NON_FINALE.search(testo):
        return None
    if any(v in testo for v in VIETATI) or re.search(r"\bnan\b", testo, re.IGNORECASE):
        return None
    return testo


# I nomi dei territori

def nome_con_articolo(nome, livello):
    """"la Lombardia", "il Lazio", "l'Umbria", "le Marche" per le regioni, "il Sud
    Sardegna" per le due province che lo vogliono, il nome nudo per tutte le altre
    ("Trieste", "La Spezia"). Il genere delle regioni sta in `seo_titles.of_region`
    (il Piemonte, il Molise): si deriva da la', e un nome che non e' una delle venti
    regioni resta nudo, perche' l'articolo non si indovina."""
    if livello == "regioni":
        if nome not in REGION_ORDER:
            return nome
        di = of_region(nome)
        for forma, articolo in (("della ", "la "), ("del ", "il "), ("delle ", "le "), ("dell'", "l'")):
            if di.startswith(forma):
                return articolo + di[len(forma):]
        return nome
    return f"il {nome}" if nome in ARTICLED_PROVINCES else nome


# Cifre e unita'

def _testo_cifra(valore, extra=0):
    return numfmt.text(valore, numfmt.magnitude_decimals(valore) + extra)


def unita_scritta(unita):
    """L'unita' da scrivere dopo la cifra, o None se non ce n'e' una onesta. La regola
    del sito (`numfmt.phrase_unit`) e' la prima; se rinuncia solo perche' l'etichetta
    e' lunga ("metri quadrati per abitante") la frase la scrive per intero. Una coda
    dopo la virgola ("ogni 10.000 abitanti, tasso standardizzato") si lascia cadere:
    la base resta vera. Un'etichetta generica non e' un'unita': senza, la frase non
    esce."""
    scritta = numfmt.phrase_unit(unita)
    if scritta:
        return scritta
    grezza = numfmt.lower_first((unita or "").strip())
    testa, _, coda = grezza.partition(",")
    if coda and testa.startswith(("ogni ", "per ")):
        grezza = testa
    if not grezza or grezza in numfmt.GENERIC_UNITS or "," in grezza or len(grezza) > 40:
        return None
    return grezza


def _con_unita(testo, unita):
    return testo + ("%" if unita == "%" else numfmt.THIN + unita)


def _cifre_distinte(va, vb):
    """I testi di due valori diversi, con un decimale in piu' (fino a due) se
    arrotondati sarebbero uguali: "12,3 e 12,3" non dice niente. None se non si
    distinguono."""
    for extra in (0, 1, 2):
        ta, tb = _testo_cifra(va, extra), _testo_cifra(vb, extra)
        if ta != tb:
            return ta, tb
    return None


def relazione(unita, nome, valori, va, vb):
    """La relazione fra i due valori, o "" se non ce n'e' una dicibile.

    Percentuale (e punti percentuali): lo scarto in punti, mai "volte". Altrimenti
    il rapporto, solo con valori in gioco tutti positivi, rapporto grezzo almeno
    1,5, il piu' piccolo almeno il 5% della mediana dei valori in gioco, e mai su un
    saldo. Il rapporto si decide sul valore grezzo: 1,49 non diventa "1,5 volte"."""
    alto, basso = max(va, vb), min(va, vb)
    scritta = numfmt.phrase_unit(unita)
    if scritta in ("%", numfmt.POINTS):
        scarto = numfmt.text(alto - basso)
        return f", uno scarto di {scarto} punti percentuali" if re.search(r"[1-9]", scarto) else ""
    if "saldo" in (nome or "").lower():
        return ""
    if not valori or min(valori) <= 0 or basso <= 0:
        return ""
    if basso < SOGLIA_PICCOLO * statistics.median(valori):
        return ""
    rapporto = alto / basso
    if rapporto < SOGLIA_VOLTE:
        return ""
    return f", un rapporto di {numfmt.text(rapporto, 1)} volte"


# Il piazzamento

def direzione(ind_id, ambito):
    """"higher_better", "lower_better" o None (non si giudica). `higher_worse`
    ordina come `lower_better`. Mai l'euristica sul nome (`direction_for`): una
    direzione indovinata darebbe un piazzamento falso."""
    if ambito == "province":
        info = bes_data.get_bes_manifest("provincia").get(game_daily.id_provinciale(ind_id))
        grezza = (info or {}).get("direction")
    elif ind_id.startswith("bes:"):
        info = bes_data.get_bes_manifest("regione").get(ind_id[len("bes:"):])
        grezza = (info or {}).get("direction")
    else:
        grezza = CURATED_DIRECTION.get(ind_id.split(":", 1)[-1])
    if grezza == "higher_better":
        return "higher_better"
    if grezza in ("lower_better", "higher_worse"):
        return "lower_better"
    return None


def campionario(ind_id, ambito):
    """BES e Multiscopo sono indagini campionarie, e il livello provinciale e' tutto
    BES: il numero esatto della posizione non regge, la fascia si'."""
    return ambito == "province" or ind_id.startswith(("bes:", "multiscopo:"))


def piazzamento_da_valori(valori, chiave, direz, e_campionario, ambito, attesi):
    """"18ª su 20", "fra le ultime cinque" o None, sui valori di TUTTI i territori
    dello stesso anno. None senza direzione, senza copertura completa (`attesi`
    territori, tutti con un valore) o per un territorio che non c'e'. A pari merito,
    come `profiles._ranks` e `province_profile._graduatoria`: due valori uguali
    hanno la stessa posizione."""
    if direz is None or chiave not in valori or len(valori) != attesi:
        return None
    if any(v is None for v in valori.values()):
        return None
    if ambito == "regioni":
        graduatoria = profiles._ranks(valori, direz)
    else:
        graduatoria = province_profile._graduatoria(valori, direz)
    posto, totale = graduatoria[chiave], len(valori)
    if e_campionario:
        return "fra le ultime cinque" if posto >= totale - ULTIME + 1 else None
    return f"{posto}ª su {totale}"


def piazzamento(livello, indicatore, chiave):
    """Il piazzamento di un territorio per l'indicatore del gioco, dai dati veri.
    Si legge dalla stessa funzione che ha composto la sfida e solo se l'anno e'
    quello del gioco."""
    ambito = "regioni" if livello == "regioni" else "province"
    ind_id = indicatore["id"]
    dato = game_daily._righe_indicatore({"id": ind_id}, ambito)
    if dato is None or dato[0] != indicatore["year"]:
        return None
    attesi = len(REGION_ORDER) if ambito == "regioni" else len(game_daily.province_pool())
    valori = {r["key"]: r["value"] for r in dato[1]}
    return piazzamento_da_valori(
        valori, chiave, direzione(ind_id, ambito), campionario(ind_id, ambito), ambito, attesi,
    )


# La frase

TESTE = {
    "errore": "Hai messo {a} sopra {b}: ",
    "distante": "La coppia più distante: ",
    "perfetto": "Tutto al posto giusto, con la distanza maggiore fra il primo e l'ultimo: ",
}


def frase(livello, indicatore, caso, a, b, valori):
    """La frase di un caso ("errore", "distante" o "perfetto") o None. `a` e `b` sono
    `{"name", "key", "value"}`, `valori` tutti i valori in gioco (per il rapporto).
    La relazione e' la prima cosa che salta se la frase sfora la lunghezza."""
    unita = unita_scritta(indicatore.get("unit"))
    if not unita or a.get("value") is None or b.get("value") is None:
        return None
    if a["value"] == b["value"]:
        return None
    testi = _cifre_distinte(a["value"], b["value"])
    if testi is None:
        return None
    nome_a = nome_con_articolo(a["name"], livello)
    nome_b = nome_con_articolo(b["name"], livello)
    nome = numfmt.lower_first(indicatore["name"])
    luogo = piazzamento(livello, indicatore, a["key"])
    posto = f" ({luogo})" if luogo else ""
    testa = TESTE[caso].format(a=nome_a, b=nome_b)
    for con_relazione in (True, False):
        rel = relazione(indicatore["unit"], indicatore["name"], valori, a["value"], b["value"]) if con_relazione else ""
        testo = (f"{testa}per «{nome}» ({indicatore['year']}) {nome_a} ha {_con_unita(testi[0], unita)}{posto}, "
                 f"{nome_b} ha {_con_unita(testi[1], unita)}{rel}.")
        if valida(testo):
            return testo
    return None


def _riga(r):
    return {"name": r["region"], "key": r["region_key"], "value": r["value"]}


# Ordina le regioni

def fatto_ordina(livello, indicatore, positions, correct_order):
    """Il fatto di fine partita di Ordina, o None. `indicatore` e' quello del gioco
    (`id`, `name`, `unit`, `year`), `positions` le righe nell'ordine del giocatore
    (con `value`) e `correct_order` quelle nell'ordine giusto."""
    if not isinstance(positions, list) or not isinstance(correct_order, list) or len(positions) < 2:
        return None
    mosse = sorted(positions, key=lambda r: r.get("guessed_position", 0))
    valori = [r["value"] for r in mosse]
    if any(v is None for v in valori):
        return None
    for sopra, sotto in zip(mosse, mosse[1:]):
        if sopra["value"] < sotto["value"]:
            return frase(livello, indicatore, "errore", _riga(sopra), _riga(sotto), valori)
    if len(correct_order) < 2:
        return None
    return frase(livello, indicatore, "perfetto", _riga(correct_order[0]), _riga(correct_order[-1]), valori)


# Chi e' maggiore?

def errore_firmato(precedente, giorno, indice, esito, scelta):
    """Il pezzo di `sfida` che il token firma per ricordare la PRIMA coppia sbagliata:
    `{"e": indice}`, o niente. `precedente` e' il `sfida` del token prima di questa
    risposta. Vale solo per il giorno di oggi, e solo con una scelta vera: un tempo
    scaduto non dice quale lato il giocatore aveva in mente."""
    if precedente.get("d") == giorno and isinstance(precedente.get("e"), int):
        return {"e": precedente["e"]}
    if not esito["correct"] and scelta in ("region_a", "region_b"):
        return {"e": indice}
    return {}


def _riga_compare(t):
    return {"name": t["name"], "key": t["key"], "value": t["value"]}


def fatto_compare(livello, coppie, indice_errore, valuta):
    """`{"fact", "path"}` di fine partita di Chi e' maggiore, o None. `coppie` sono le
    dieci della sfida, `indice_errore` il `sfida.e` del token e `valuta(coppia,
    "region_a")` i valori veri della coppia (gli stessi `_valuta` della risposta). Con
    un errore la frase parte da li' ("Hai messo A sopra B": A e' il piu' basso, e'
    quello che il giocatore ha scelto), senza la coppia piu' distante per scarto
    relativo."""
    if isinstance(indice_errore, int) and 0 <= indice_errore < len(coppie):
        esito = valuta(coppie[indice_errore], "region_a")
        if esito is not None:
            alto, basso = sorted((esito["a"], esito["b"]), key=lambda t: t["value"], reverse=True)
            testo = frase(livello, coppie[indice_errore]["indicator"], "errore",
                          _riga_compare(basso), _riga_compare(alto), [alto["value"], basso["value"]])
            if testo:
                return {"fact": testo, "path": esito["indicator"].get("path")}
    migliore = None
    for coppia in coppie:
        esito = valuta(coppia, "region_a")
        if esito is None:
            continue
        alto, basso = sorted((esito["a"], esito["b"]), key=lambda t: t["value"], reverse=True)
        massimo = max(abs(alto["value"]), abs(basso["value"]))
        if massimo == 0:
            continue
        scarto = (alto["value"] - basso["value"]) / massimo
        if migliore is not None and scarto <= migliore[0]:
            continue
        testo = frase(livello, coppia["indicator"], "distante", _riga_compare(alto), _riga_compare(basso),
                      [alto["value"], basso["value"]])
        if testo:
            migliore = (scarto, testo, esito["indicator"].get("path"))
    if migliore is None:
        return None
    return {"fact": migliore[1], "path": migliore[2]}
