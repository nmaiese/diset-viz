"""Il gancio del cruscotto: legge i trascritti di un workflow e li posta al sito.

Sta **fuori** dal workflow, ed e' l'unica cosa che conta di questo file. Il
monitoraggio non deve diventare un dovere in piu' per un agente: i turni sono il
costo di questa architettura e crescono col quadrato, quindi nessun agente batte,
nessun prompt cambia. Il runtime dei workflow scrive gia' tutto quello che serve,
e qui lo si legge da fuori.

    bin/py -m lab.cruscotto --segui           # in background, mentre la run gira
    bin/py -m lab.cruscotto --consuntivo wf_… # riparazione a mano
    bin/py -m lab.cruscotto --leggi wf_… --stdout   # legge e stampa, non posta

## Che cosa esiste quando, misurato e non supposto

Sonda vera (`wf_90bf85dd-65e`, due agenti, file guardati ogni otto secondi):

    journal.jsonl            VIVO   `started` e `result`, col valore di ritorno
    agent-<id>.meta.json     VIVO   solo {"agentType", "spawnDepth"}
    agent-<id>.jsonl         VIVO   il prompt, poi un `usage` per richiesta
    <sessione>/workflows/<runId>.json   SOLO A RUN FINITA

Da qui discendono le due regole del file:

1. **`label` e `phaseTitle` non esistono dal vivo.** Stanno solo in
   `<runId>.json`. Dal vivo si ha il tipo di agente, e la fase si **stima** da
   quello (`FASE_PER_TIPO`); a run finita arriva la verita', e finisce in
   colonne diverse invece di sovrascrivere la stima.
2. **La comparsa di `<runId>.json` e' il segnale di fine run.** Nessuno deve
   dire a questo processo che la run e' finita: lo vede.

## Il contratto di misura non si riscrive

Turni, token e costo per agente li calcola `scripts/baseline_tokens.py`, che si
importa. La regola "un record per `requestId`, il piu' completo" e le tre
trappole che la circondano (il doppio record, `usage` che non conta i subagent,
l'advisor invisibile) stanno scritte la' e valgono una volta sola. Due
implementazioni della stessa misura sono il difetto che questo repo ha gia'
pagato con l'impronta della bozza.

**Un totale di costo e' un pavimento, non una cifra esatta.** In una run reale
il trascritto di un agente ha registrato `output_tokens: 2` sulla richiesta che
restituiva una bozza intera. Il trascritto e' incompleto, non lo e' la misura,
quindi ogni riga postata porta `costo_pavimento` e il cruscotto lo dice.

Stdlib pura, sola lettura sui trascritti, non tocca il repo.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.baseline_tokens import (  # noqa: E402
    PROJECTS, add, cost, labels, read_agents, zero,
)

# La fase di un agente **stimata dal vivo**, quando `<runId>.json` non c'e'
# ancora. Una mappa sola, e un test
# (`tests/unit/test_cruscotto.py::test_ogni_tipo_del_workflow_ha_una_fase`)
# rilegge `.claude/workflows/indicatore-lite.js` ed esige che ogni `agentType`
# citato la' dentro stia qui. Un agente nuovo senza fase fa fallire la suite,
# non il cruscotto: e' il posto giusto dove accorgersene.
FASE_PER_TIPO = {
    "lab-dossierista": "Dossier",
    "lab-scout": "Contesto",
    "lab-scout-europa": "Contesto",
    "lab-scrittore": "Scrittura",
    "lab-verificatore": "Verifica",
    "lab-pubblicatore": "Pubblicazione",
}

# L'ordine delle fasi, per dire quale e' la piu' avanzata fra gli agenti aperti.
ORDINE_FASI = ["Dossier", "Contesto", "Scrittura", "Verifica", "Pubblicazione"]

# Il codice di un indicatore dentro un prompt. Le famiglie sono quelle vere
# (`app/sources.py`): una regex piu' larga prenderebbe `wf-90` o una data.
CODICE = re.compile(r"\b(?:ter|bes|ims|eur|dem)-[0-9A-Za-z_.:-]+\b")

TETTO_RISULTATO = 20000
UA = "divarioitalia-cruscotto/1 (+https://divarioitalia.it)"


def _ora():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------- dove sono i file

class RadiceMancante(RuntimeError):
    """La cartella dei trascritti non si risolve. Fatale, e per scelta.

    Diverso da "nessuna run dentro una radice risolta", che e' lo stato normale
    dei primi secondi (questo processo parte prima del workflow). Confonderle
    ammazzerebbe la run che conta, o peggio la lascerebbe girare a vuoto
    postando zero righe con la faccia di chi non ha trovato niente."""


def radice_progetto(cwd=None):
    """La cartella `~/.claude/projects/<slug>` di questo checkout.

    Claude Code costruisce lo slug dal percorso di lavoro sostituendo ogni
    carattere non alfanumerico con un trattino. Si prova prima quello, che e'
    esatto, poi la glob per nome di `baseline_tokens` come ripiego.

    La glob da sola non basta, ed e' il motivo per cui questa funzione esiste:
    `PROJECTS` cerca `*diset-viz*`, cioe' un **nome**, e nell'ambiente cloud il
    percorso di lavoro puo' non contenere quella stringa. Il guasto sarebbe un
    risultato vuoto in silenzio."""
    base = os.path.expanduser("~/.claude/projects")
    percorso = os.path.abspath(cwd or os.getcwd())
    slug = re.sub(r"[^A-Za-z0-9]", "-", percorso)
    esatta = os.path.join(base, slug)
    if os.path.isdir(esatta):
        return esatta
    ripiego = sorted(p for p in glob.glob(os.path.expanduser(PROJECTS)) if os.path.isdir(p))
    if ripiego:
        return ripiego[-1]
    raise RadiceMancante(
        f"nessuna cartella di trascritti: ne' {esatta} ne' {PROJECTS}. "
        f"cwd = {percorso}")


def sessioni(radice):
    """Le cartelle di sessione dentro una radice, quelle che possono avere run."""
    return sorted(p for p in glob.glob(os.path.join(radice, "*"))
                  if os.path.isdir(os.path.join(p, "subagents", "workflows")))


def run_viste(radice):
    """`{runId: {"trascritti": [...], "meta": [...], "sessione": ...}}`.

    **Liste, e non e' pedanteria.** Una run ripresa (`resumeFromRunId`) tiene lo
    stesso `runId` ma scrive nella cartella della sessione nuova, quindi lo
    stesso identificatore esiste sotto due sessioni: gli agenti replicati da
    cache stanno di qua, quelli rigirati di la'. Tenerne una sola vuol dire
    misurare meta' run e presentarla con la faccia di un totale, che e' il
    difetto che `scripts/baseline_tokens.find_workflow` esiste per chiudere.

    `meta` e' `<sessione>/workflows/<runId>.json`, che compare solo a run
    finita: c'e' sempre come percorso, non sempre come file."""
    trovate = {}
    for sessione in sessioni(radice):
        for cartella in sorted(glob.glob(os.path.join(sessione, "subagents", "workflows", "wf_*"))):
            if not os.path.isdir(cartella):
                continue
            run_id = os.path.basename(cartella)
            dove = trovate.setdefault(run_id, {
                "trascritti": [], "meta": [],
                "sessione": os.path.basename(sessione),
                "progetto": os.path.basename(radice),
            })
            dove["trascritti"].append(cartella)
            dove["meta"].append(os.path.join(sessione, "workflows", run_id + ".json"))
    return trovate


# ------------------------------------------------------------------- il vivo

def _prima_riga_utente(percorso):
    """Il primo record dell'agente, che porta il prompt. Scritto all'avvio."""
    try:
        with open(percorso, errors="replace") as handle:
            for riga in handle:
                try:
                    record = json.loads(riga)
                except ValueError:
                    continue
                if record.get("type") == "user":
                    return record
    except OSError:
        return None
    return None


def _testo_messaggio(record):
    contenuto = ((record or {}).get("message") or {}).get("content")
    if isinstance(contenuto, str):
        return contenuto
    if not isinstance(contenuto, list):
        return ""
    pezzi = [b.get("text") or "" for b in contenuto
             if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(pezzi)


def indicatore_del_prompt(testo):
    """Il codice indicatore su cui lavora un agente, dal suo prompt.

    Il primo che compare: nei prompt di `indicatore-lite` il codice del pezzo
    apre la frase, e i codici dei parenti compaiono al massimo dentro il
    dossier, che sta su disco e non nel prompt."""
    trovato = CODICE.search(testo or "")
    return trovato.group(0) if trovato else ""


def _mtime(percorso):
    try:
        return os.path.getmtime(percorso)
    except OSError:
        return None


def _iso(epoca):
    if epoca is None:
        return ""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(epoca, timezone.utc).isoformat(timespec="seconds")


def tipo_di(cartella, agent_id):
    """Il tipo di un agente, da `agent-<id>.meta.json`. Scritto al suo avvio."""
    meta = os.path.join(cartella, f"agent-{agent_id}.meta.json")
    try:
        with open(meta, encoding="utf-8") as handle:
            return (json.load(handle) or {}).get("agentType") or ""
    except (OSError, ValueError):
        return ""


def stato_vivo(cartelle):
    """Lo stato di una run leggendo solo i file che esistono mentre gira.

    `journal.jsonl` porta una riga `started` per agente avviato e una `result`
    per agente chiuso, col valore di ritorno completo. `agent-<id>.meta.json`
    porta il tipo. Non c'e' altro, e in particolare non c'e' la fase."""
    if isinstance(cartelle, str):
        cartelle = [cartelle]
    agenti, dove_sta, giornali = {}, {}, []
    for cartella in cartelle:
        journal = os.path.join(cartella, "journal.jsonl")
        giornali.append(journal)
        try:
            with open(journal, errors="replace") as handle:
                righe = list(handle)
        except OSError:
            righe = []
        for riga in righe:
            try:
                record = json.loads(riga)
            except ValueError:
                continue
            agent_id = record.get("agentId")
            if not agent_id:
                continue
            voce = agenti.setdefault(agent_id, {"agent_id": agent_id, "stato_vivo": "aperto"})
            dove_sta[agent_id] = cartella
            if record.get("type") == "result":
                voce["stato_vivo"] = "chiuso"
                voce["risultato"] = record.get("result")

    for agent_id, voce in agenti.items():
        cartella = dove_sta[agent_id]
        voce["agent_type"] = tipo_di(cartella, agent_id)
        voce["fase_stimata"] = FASE_PER_TIPO.get(voce["agent_type"], "")
        meta = os.path.join(cartella, f"agent-{agent_id}.meta.json")
        trascritto = os.path.join(cartella, f"agent-{agent_id}.jsonl")
        voce["avviato_il"] = _iso(_mtime(meta) or _mtime(trascritto))
        voce["chiuso_il"] = _iso(_mtime(trascritto)) if voce["stato_vivo"] == "chiuso" else ""
        voce["indicatore"] = indicatore_del_prompt(
            _testo_messaggio(_prima_riga_utente(trascritto)))

    ordinati = sorted(agenti.values(), key=lambda a: (a["avviato_il"], a["agent_id"]))
    fasi_viste = [a["fase_stimata"] for a in ordinati if a["fase_stimata"] in ORDINE_FASI]
    fase = max(fasi_viste, key=ORDINE_FASI.index) if fasi_viste else ""
    inizi = [_mtime(g) for g in giornali] + [_mtime(c) for c in cartelle]
    inizi = [i for i in inizi if i is not None]
    return {
        "avviata_il": _iso(min(inizi) if inizi else None),
        "fase_stimata": fase,
        "agenti_visti": len(ordinati),
        "agenti": ordinati,
    }


# -------------------------------------------------------------- il consuntivo

def consuntivo(cartelle, meta_paths):
    """La run finita: `<runId>.json` per la verita' su fasi e agenti, i
    `agent-*.jsonl` per turni, strumenti e token via `baseline_tokens`.

    Restituisce `None` se nessun `<runId>.json` c'e' ancora: e' il segnale che la
    run non e' finita, non un errore.

    Liste in ingresso perche' una run ripresa vive in due sessioni (vedi
    `run_viste`): si legge il `<runId>.json` piu' recente, si misurano tutte le
    cartelle e si tiene ogni agente una volta sola."""
    if isinstance(cartelle, str):
        cartelle = [cartelle]
    if isinstance(meta_paths, str):
        meta_paths = [meta_paths]

    meta, quando_meta = None, -1.0
    for percorso in meta_paths:
        istante = _mtime(percorso)
        if istante is None or istante <= quando_meta:
            continue
        try:
            with open(percorso, encoding="utf-8") as handle:
                meta, quando_meta = json.load(handle), istante
        except (OSError, ValueError):
            continue
    if meta is None:
        return None

    passi = {p.get("agentId"): p for p in (meta.get("workflowProgress") or [])
             if isinstance(p, dict) and p.get("type") == "workflow_agent"}
    misure, tipi, etichette = {}, {}, {}
    for cartella in cartelle:
        # `labels()` legge lo stesso `<runId>.json`: si riusa invece di
        # rileggerlo, cosi' l'etichetta e' la stessa che stampa `baseline_tokens`.
        etichette.update(labels(cartella))
        for misura in read_agents(cartella):
            # Un agente ripreso da cache compare in due cartelle: si tiene una
            # volta sola, altrimenti il totale conta due volte proprio i turni
            # che la ripresa non ha pagato.
            misure.setdefault(misura["id"], misura)
            tipi.setdefault(misura["id"], tipo_di(cartella, misura["id"]))

    agenti, totale, totale_advisor = [], zero(), zero()
    turni = tool = chiamate = 0
    for agent_id in sorted(set(passi) | set(misure)):
        passo = passi.get(agent_id, {})
        misura = misure.get(agent_id, {})
        modello = misura.get("model") or zero()
        advisor = misura.get("advisor") or zero()
        add(totale, modello)
        add(totale_advisor, advisor)
        turni += misura.get("turns") or 0
        strumenti = misura.get("tools") or {}
        tool += sum(strumenti.values())
        chiamate += misura.get("advisor_calls") or 0
        # Un agente puo' avere il file e non il passo: succede su una run
        # ripresa, dove `<runId>.json` racconta l'ultimo giro e le cartelle
        # tengono anche quelli di prima. Senza ripiego la riga uscirebbe vuota
        # e si leggerebbe come un guasto del cruscotto. Con il ripiego dice
        # quello che si sa: chi e', di che tipo, quanto e' costato. La `fase`
        # resta nulla, cosi' la vista puo' cadere sulla stima del battito e
        # dichiararla tale invece di spacciarla per la verita'.
        tipo = passo.get("agentType") or tipi.get(agent_id) or ""
        agenti.append({
            "agent_id": agent_id,
            "label": passo.get("label") or etichette.get(agent_id)
            or (f"{tipo} {agent_id[:8]}" if tipo else agent_id[:8]),
            "fase": passo.get("phaseTitle") or None,
            "modello": passo.get("model") or "",
            "stato": passo.get("state") or "",
            "turni": misura.get("turns"),
            "tool": sum(strumenti.values()) if strumenti else None,
            "strumenti": strumenti,
            "token_in": modello["in"], "token_cache_w": modello["cache_w"],
            "token_cache_r": modello["cache_r"], "token_out": modello["out"],
            "advisor_in": advisor["in"], "advisor_out": advisor["out"],
            "advisor_chiamate": misura.get("advisor_calls"),
            "costo": round(cost(modello) + cost(advisor), 4),
        })

    fasi = [p.get("title") for p in (meta.get("workflowProgress") or [])
            if isinstance(p, dict) and p.get("type") == "workflow_phase" and p.get("title")]
    run = {
        "workflow": meta.get("workflowName") or "",
        "args": meta.get("args"),
        "stato": meta.get("status") or "",
        "durata_ms": meta.get("durationMs"),
        "fasi": fasi,
        "esito": meta.get("result"),
        "logs": meta.get("logs") or [],
        "agenti": len(agenti),
        "turni": turni,
        "tool": tool,
        "token_in": totale["in"], "token_cache_w": totale["cache_w"],
        "token_cache_r": totale["cache_r"], "token_out": totale["out"],
        "advisor_in": totale_advisor["in"], "advisor_out": totale_advisor["out"],
        "advisor_chiamate": chiamate,
        "costo": round(cost(totale) + cost(totale_advisor), 4),
        # Sempre vero, e per costruzione: il trascritto puo' essere incompleto,
        # la misura no. Il campo c'e' perche' il cruscotto lo dica invece di
        # mostrare un totale come esatto.
        "costo_pavimento": 1,
    }
    return {"run": run, "agenti": agenti}


# ------------------------------------------------------------------ il POST

class Postino:
    """Chi manda i battiti al sito. Best effort, e mai fatale.

    Un User-Agent esplicito perche' Cloudflare banna `Python-urllib` con
    error 1010: e' gia' successo a questo progetto, e il sintomo era la
    telemetria che spariva senza un errore leggibile."""

    def __init__(self, url=None, token=None, stampa=False):
        self.url = (url or os.environ.get("PIPELINE_INGEST_URL", "")).rstrip("/")
        self.token = token or os.environ.get("PIPELINE_INGEST_TOKEN", "")
        self.stampa = stampa
        self.guasti = 0

    @property
    def acceso(self):
        return bool(self.url and self.token)

    def manda(self, payload):
        if self.stampa:
            print(json.dumps(payload, ensure_ascii=False)[:4000])
            return True
        if not self.acceso:
            return False
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        richiesta = urllib.request.Request(
            f"{self.url}/_pipeline/beat", data=corpo, method="POST",
            headers={"Content-Type": "application/json",
                     "X-Pipeline-Key": self.token, "User-Agent": UA})
        try:
            with urllib.request.urlopen(richiesta, timeout=20) as risposta:
                return 200 <= risposta.status < 300
        except (urllib.error.URLError, OSError, ValueError) as errore:
            self.guasti += 1
            print(f"cruscotto: POST fallito ({errore})", file=sys.stderr)
            return False


# ------------------------------------------------------------------ il giro

def _tronca(valore):
    if valore is None:
        return None
    testo = valore if isinstance(valore, str) else json.dumps(valore, ensure_ascii=False)
    return testo[:TETTO_RISULTATO]


class Giro:
    """Un giro di lettura, con memoria di quello che ha gia' mandato.

    La memoria e' l'unica ragione per cui questa e' una classe: senza, ogni
    intervallo riposterebbe tutta la storia, e il costo del monitoraggio
    crescerebbe con la durata della run invece che con quello che succede."""

    def __init__(self, postino, radice):
        self.postino = postino
        self.radice = radice
        self.viste = {}       # run_id -> impronta dell'ultimo battito mandato
        self.consuntivate = set()

    def passa(self):
        mandati = 0
        for run_id, dove in run_viste(self.radice).items():
            if run_id in self.consuntivate:
                continue
            finita = consuntivo(dove["trascritti"], dove["meta"])
            vivo = stato_vivo(dove["trascritti"])
            mandati += self._battito(run_id, dove, vivo)
            if finita:
                self.postino.manda({"action": "consuntivo", "run_id": run_id,
                                    "run": finita["run"], "agenti": finita["agenti"]})
                self.consuntivate.add(run_id)
                mandati += 1
        return mandati

    def _battito(self, run_id, dove, vivo):
        impronta = json.dumps(vivo, ensure_ascii=False, sort_keys=True)
        if self.viste.get(run_id) == impronta:
            return 0
        self.viste[run_id] = impronta
        self.postino.manda({
            "action": "run", "run_id": run_id,
            "avviata_il": vivo["avviata_il"], "fase_stimata": vivo["fase_stimata"],
            "agenti_visti": vivo["agenti_visti"],
            "sessione": dove["sessione"], "progetto": dove["progetto"],
        })

        for agente in vivo["agenti"]:
            self.postino.manda({
                "action": "agente", "run_id": run_id,
                "agent_id": agente["agent_id"], "agent_type": agente["agent_type"],
                "fase_stimata": agente["fase_stimata"], "indicatore": agente["indicatore"],
                "avviato_il": agente["avviato_il"], "chiuso_il": agente["chiuso_il"],
                "stato_vivo": agente["stato_vivo"],
                "risultato": _tronca(agente.get("risultato")),
            })
        return 1 + len(vivo["agenti"])


def segui(postino, intervallo=5, per=None, radice=None):
    """Il giro, ogni `intervallo` secondi, per `per` secondi (o all'infinito).

    Stampa la radice risolta una volta all'avvio: in cloud quella riga di log e'
    l'unica prova che la derivazione del percorso ha funzionato, e senza di lei
    un poller che gira su una cartella sbagliata sembra un poller che funziona.
    """
    radice = radice or radice_progetto()
    print(f"cruscotto: guardo {radice}", flush=True)
    if not postino.acceso and not postino.stampa:
        print("cruscotto: PIPELINE_INGEST_URL o PIPELINE_INGEST_TOKEN mancanti, "
              "leggo e non posto", file=sys.stderr, flush=True)
    giro = Giro(postino, radice)
    scadenza = time.monotonic() + per if per else None
    while True:
        mandati = giro.passa()
        if mandati:
            print(f"cruscotto: {mandati} righe, {len(giro.consuntivate)} run chiuse",
                  flush=True)
        if scadenza and time.monotonic() >= scadenza:
            return 0
        time.sleep(intervallo)


def _trova(run_id, radice):
    dove = run_viste(radice).get(run_id)
    if not dove:
        raise SystemExit(f"cruscotto: nessuna run {run_id} sotto {radice}")
    return dove


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--segui", action="store_true",
                        help="legge finche' non scade, e posta i cambiamenti")
    parser.add_argument("--intervallo", type=float, default=5.0)
    parser.add_argument("--per", type=float, default=None,
                        help="secondi, poi si ferma (senza, non si ferma)")
    parser.add_argument("--consuntivo", metavar="RUN_ID", default=None,
                        help="posta il consuntivo di una run finita")
    parser.add_argument("--leggi", metavar="RUN_ID", default=None,
                        help="legge una run e la stampa, senza postare")
    parser.add_argument("--stdout", action="store_true",
                        help="stampa i payload invece di postarli")
    args = parser.parse_args(argv)

    try:
        radice = radice_progetto()
    except RadiceMancante as errore:
        print(f"cruscotto: {errore}", file=sys.stderr)
        return 2

    postino = Postino(stampa=args.stdout)

    if args.leggi:
        dove = _trova(args.leggi, radice)
        print(json.dumps({"vivo": stato_vivo(dove["trascritti"]),
                          "consuntivo": consuntivo(dove["trascritti"], dove["meta"])},
                         ensure_ascii=False, indent=1))
        return 0

    if args.consuntivo:
        dove = _trova(args.consuntivo, radice)
        finita = consuntivo(dove["trascritti"], dove["meta"])
        if not finita:
            print(f"cruscotto: {args.consuntivo} non e' finita "
                  f"(manca {', '.join(dove['meta'])})",
                  file=sys.stderr)
            return 1
        postino.manda({"action": "consuntivo", "run_id": args.consuntivo,
                       "run": finita["run"], "agenti": finita["agenti"]})
        return 0

    if args.segui:
        return segui(postino, intervallo=args.intervallo, per=args.per, radice=radice)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
