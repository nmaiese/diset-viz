#!/usr/bin/env python3
"""La storia di ogni indicatore, ricostruita dai file committati.

Questa è la Fase B del mandato (osservabilità senza cambiare la pubblicazione)
più la Fase C in modalità di controllo (macchina a stati affiancata al flusso,
che confronta lo stato dichiarato con gli artefatti). Non pubblica niente, non
apre pull request, non tocca la catena: legge i registri che già esistono e
compone, per ogni indicatore, una **timeline** e uno **stato ricostruito**.

Oggi lo stato è emergente: sette code lo rideducono a ogni run scandendo i CSV e
gli store. Qui lo si legge una volta e lo si mette in un posto solo, per
indicatore invece che per stadio, così si può rispondere senza analisi manuale:
quando l'indicatore è entrato, cosa è successo, quali passaggi ha completato,
quali run lo hanno toccato, se è pubblicato, se la sua verifica regge.

Il nucleo (`reconstruct`) è puro: prende i dati già letti e non tocca il disco,
così un test lo prova con artefatti sintetici. La CLI collega i lettori reali
della catena, tutti stdlib puri. Stdlib puro come il resto.

    python3 scripts/practice_timeline.py                 # una riga per indicatore
    python3 scripts/practice_timeline.py --indicator dem:NMIGRATEIN   # la storia intera
    python3 scripts/practice_timeline.py --json          # per un altro programma
    python3 scripts/practice_timeline.py --write         # scrive i record in practices/
    python3 scripts/practice_timeline.py --check         # riconcilia dichiarato vs osservato
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import discovery, practice_model  # noqa: E402

# --- Mappe id <-> code, senza importare l'app -------------------------------

def code_of(key: str) -> str:
    """La forma URL di una chiave interna, come `verification_queue.code_of`.
    Copiata (non importata) per non trascinare dentro il join sul view model."""
    return f"ter-{key}" if str(key).isdigit() else str(key).replace(":", "-", 1)


def key_of_code(code: str) -> str:
    """L'inverso di `code_of`: da `ter-651` a `651`, da `eur-rd_e_gerdreg` a
    `eur:rd_e_gerdreg`. Il primo trattino torna a essere due punti."""
    if code.startswith("ter-"):
        return code[len("ter-"):]
    return code.replace("-", ":", 1)


def _target_of_candidate(row: dict):
    """L'id d'atlante a cui un candidato punta, versione tollerante di
    `promote_candidates._target_id` (che invece solleva). Restituisce None quando
    non è ricavabile, invece di fermare la ricostruzione di tutto il resto."""
    match = row.get("definition_match")
    dup = row.get("duplicate_of")
    if match in ("exact", "compatible", "proxy") and dup:
        return dup
    family = discovery.FEED_FAMILY.get(row.get("source"))
    sid = row.get("source_indicator_id")
    if family and sid:
        return discovery.public_id(family, sid)
    return None


# Gli id d'indicatore citati in un testo libero di run. Riconosce le forme
# famiglia (`dem:NMIGRATEIN`), i candidate_id (`istat_demografia:DEPENDRATE`) e i
# code (`ter-651`, `eur-rd_e_gerdreg`). Le forme nude (`BIRTHRATE`) sono rumore e
# si lasciano fuori di proposito: meglio un'associazione mancante e dichiarata
# che una inventata. Il trattino nel corpo dell'id è obbligatorio, non opzionale:
# gli id BES lo contengono (`bes:09PAE009-N25`, `bes-03LAV006-N25`), e fermarsi al
# secondo trattino inventava `bes:03LAV006` lasciando la vera pratica senza il suo
# run.
_ID_IN_TEXT = re.compile(r"\b([a-z_]+:[A-Za-z0-9_-]+|(?:ter|dem|eur|bes|multiscopo)-[A-Za-z0-9_-]+)\b")


def _ids_in_text(text: str) -> set:
    return set(_ID_IN_TEXT.findall(text or ""))


def _latest_external_year(target: str, external: list) -> int | None:
    years = [
        int(row["year"])
        for row in external
        if row.get("target_indicator_id") == target and str(row.get("year") or "").strip().isdigit()
    ]
    return max(years) if years else None


def _as_int(value):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


ARTICLE_ROLES = ("definizione", "quadro", "dinamica", "limiti")
SUBSTANTIVE_ROLES = frozenset(("quadro", "dinamica", "limiti"))


def _emitted_roles(entry) -> list:
    """I ruoli che la pagina rende per questa entry.

    Copia stdlib di `app.indicator_texts.emitted_roles`, che possiede la regola:
    una dichiarazione `roles_covered` è un filtro sui quattro ruoli (un ruolo
    sconosciuto si ignora) e i tre sostanziali ci sono comunque. Copiata e non
    importata come le altre costanti di questo file, e un test le tiene allineate.
    """
    declared = entry.get("roles_covered") if isinstance(entry, dict) else None
    # Campo assente e lista vuota non sono la stessa cosa: la seconda è una
    # dichiarazione che non nomina la definizione, quindi la assorbe.
    if not isinstance(declared, (list, tuple)):
        return list(ARTICLE_ROLES)
    keep = {role for role in declared if role in ARTICLE_ROLES} | SUBSTANTIVE_ROLES
    return [role for role in ARTICLE_ROLES if role in keep]


def reconstruct(candidates, manifest, curation, external, articles, verifiche,
                runs, today: str = "") -> dict:
    """Ricostruisce, per ogni indicatore, timeline e stato, dai soli artefatti.

    Tutti gli argomenti sono dati già letti (liste di dict, o `articles` come
    `{key: entry}`), così il nucleo resta puro e il test lo nutre a mano.
    `published` = fuso su master (il progetto ha ratificato merge = pubblicazione):
    non c'è più una verifica-sito né uno stato `fusa` intermedio.

    Restituisce `{indicator_id: dossier}`, dove ogni dossier porta: `id`,
    `type`, `state`, `entered_at`, `completed_stages`, `flags`, `error_class`,
    `published`, `verification_valid`, `score_eligible`, `runs`, `timeline`.
    """
    from scripts import verification_queue

    # 1. Costruisci l'universo degli indicatori e un evento per ogni traccia.
    dossier: dict = {}

    def slot(ind_id: str) -> dict:
        if ind_id not in dossier:
            dossier[ind_id] = {
                "id": ind_id,
                "type": "nuovo",
                "state": "in-lavorazione",
                "entered_at": "",
                "completed_stages": [],
                "flags": {},
                "error_class": None,
                "score_eligible": False,
                "published": None,
                "verification_valid": None,
                "runs": [],
                "timeline": [],
            }
        return dossier[ind_id]

    def event(ind_id, at, stage, kind, detail, **extra):
        ev = {"at": at or "", "stage": stage, "kind": kind, "detail": detail}
        ev.update(extra)
        slot(ind_id)["timeline"].append(ev)

    # --- candidati (pre-pratica): triage, promozione, rifiuti -----------------
    for row in candidates:
        target = _target_of_candidate(row)
        if not target:
            continue
        status = (row.get("triage_status") or "new").strip()
        at = row.get("discovered_at", "")
        note = row.get("triage_notes", "")
        d = slot(target)
        if status == "new":
            event(target, at, "hunter", "candidatura", note or "candidato in triage")
        elif status == "approved":
            event(target, at, "hunter", "approvata", note)
            d["flags"]["approved_candidate"] = True
        elif status == "promoted":
            event(target, at, "promoter", "promossa", note)
        elif status == "rejected":
            event(target, at, "hunter", "rifiutata", note)
            d["flags"]["rejected"] = True
            if row.get("duplicate_of"):
                d["flags"]["duplicate"] = True
        elif status == "needs-info":
            event(target, at, "hunter", "rimandata", note)
            d["flags"]["needs_info"] = True

    # --- manifest: promosso (proposed) / integrato ---------------------------
    manifest_year = {}
    for row in manifest:
        target = row.get("target_indicator_id", "")
        if not target:
            continue
        years = [_as_int(row.get(c)) for c in ("new_year", "current_year")]
        years = [y for y in years if y is not None]
        if years:
            manifest_year[target] = max(years)
        status = row.get("status")
        if status == "proposed":
            event(target, "", "promoter", "promossa", "manifest status=proposed")
            slot(target)["flags"]["approved_candidate"] = \
                slot(target)["flags"].get("approved_candidate", True)
        elif status == "integrated":
            event(target, "", "curator", "integrata", "manifest status=integrated")
            slot(target)["flags"].pop("approved_candidate", None)

    # --- curatela: verso, categoria, data_year, score_eligible ----------------
    for row in curation:
        target = row.get("target_indicator_id", "")
        if not target:
            continue
        d = slot(target)
        at = row.get("reviewed_at", "")
        data_year = _as_int(row.get("data_year"))
        score = str(row.get("score_eligible", "")).strip().lower() == "true"
        d["score_eligible"] = d["score_eligible"] or score
        if "curator" not in d["completed_stages"]:
            d["completed_stages"].append("curator")
        event(target, at, "curator", "curata",
              f"verso {row.get('reviewed_direction')} ({row.get('direction_verdict')}), "
              f"categoria {row.get('reviewed_category')}, score_eligible={score}",
              data_year=data_year)
        latest = _latest_external_year(target, external)
        if data_year is not None and latest is not None and data_year < latest:
            d["flags"]["stale_curation"] = True

    # --- articoli: scritto, firmato, vintage ---------------------------------
    for key, entry in (articles or {}).items():
        d = slot(key)
        vintage = _as_int(entry.get("vintage"))
        reviewed_at = entry.get("reviewed_at")
        reviewed_vintage = _as_int(entry.get("reviewed_vintage"))
        roles = {s.get("role") for s in (entry.get("sections") or []) if (s.get("body") or "").strip()}
        # Sezioni variabili (opt-in): un'entry può dichiarare `roles_covered`, i
        # ruoli che scrive come H2, e assorbire la `definizione` nel blocco "Come
        # leggere". "Completo" segue la dichiarazione, ma i tre ruoli sostanziali
        # (quadro, dinamica, limiti) restano sempre richiesti: solo la definizione
        # è omettibile, perché è l'unico ruolo che il blocco copre. Senza
        # `roles_covered` (i trecento esistenti) la regola resta i quattro ruoli,
        # identica a prima. Additivo: nessun articolo esistente cambia stato.
        # Un ruolo sconosciuto (un refuso) si ignora invece di entrare fra i
        # richiesti: tenerlo rendeva la pratica incompleta per sempre mentre la
        # lista di consegna diceva che non manca niente, e il dossier la
        # rilanciava a ogni tick senza che nessuna run potesse chiudere il buco.
        # Stessa normalizzazione di `app.indicator_texts.emitted_roles`.
        complete = bool((entry.get("lead") or "").strip()) \
            and set(_emitted_roles(entry)).issubset(roles)
        if "writer" not in d["completed_stages"]:
            d["completed_stages"].append("writer")
        event(key, "", "writer", "scritta",
              f"vintage {vintage}, {'completa' if complete else 'incompleta'}",
              vintage=vintage, complete=complete)
        d["flags"]["article_complete"] = complete
        d["flags"]["vintage"] = vintage
        if reviewed_at:
            if "reviewer" not in d["completed_stages"]:
                d["completed_stages"].append("reviewer")
            event(key, reviewed_at, "reviewer", "firmata",
                  f"reviewed_vintage {reviewed_vintage}",
                  reviewed_vintage=reviewed_vintage)
            if vintage is not None and reviewed_vintage is not None and reviewed_vintage != vintage:
                d["flags"]["stale_vintage"] = True

    # --- verifiche: contro l'impronta della prosa ----------------------------
    for row in verifiche:
        code = row.get("code", "")
        key = key_of_code(code)
        d = slot(key)
        esito = row.get("esito")
        smentite = _as_int(row.get("smentite")) or 0
        entry = (articles or {}).get(key)
        valid = None
        if entry is not None:
            valid = verification_queue.prose_fingerprint(entry) == row.get("prosa")
        # Una verifica conta come stadio completo, e una smentita come aperta,
        # solo se l'impronta combacia ancora con la prosa attuale. Se il testo è
        # cambiato dopo, la verifica è scaduta: il verificatore deve rigirare, e
        # marcarlo completo terrebbe l'articolo 'fusa' senza che nessuno stadio
        # pronto lo rimandi a valle. È lo stesso principio con cui il revisore
        # spegne una smentita riscrivendo la frase: l'impronta cambia, la
        # smentita non è più aperta.
        if valid is True and "verificatore" not in d["completed_stages"]:
            d["completed_stages"].append("verificatore")
        event(key, row.get("at", ""), "verificatore", "verificata",
              f"esito {esito}, smentite {smentite}, impronta {'combacia' if valid else 'scaduta' if valid is False else '?'}",
              esito=esito, smentite=smentite, prosa_valid=valid)
        if esito == "smentito" and smentite > 0 and valid is True:
            d["flags"]["open_smentita"] = True
        d["verification_valid"] = valid

    # --- run: chi ha toccato cosa, dalla prosa del diario --------------------
    for run in runs:
        text = (run.get("summary") or "") + "\n" + "\n".join(run.get("detail") or [])
        touched = set()
        for token in _ids_in_text(text):
            if token.startswith(("ter-", "dem-", "eur-", "bes-", "multiscopo-")):
                touched.add(key_of_code(token))
            else:
                touched.add(token)  # candidate_id o family id
        for token in list(touched):
            # candidate_id come istat_demografia:DEPENDRATE -> prova a mappare al target
            if token in dossier:
                continue
            fam = discovery.FEED_FAMILY.get(token.split(":", 1)[0]) if ":" in token else None
            if fam:
                mapped = discovery.public_id(fam, token.split(":", 1)[1])
                if mapped in dossier:
                    touched.discard(token)
                    touched.add(mapped)
        for ind in touched:
            d = slot(ind)
            d["runs"].append(run.get("run_id") or "")
            event(ind, run.get("at", ""), run.get("stage", ""), "run",
                  run.get("summary", ""), run_id=run.get("run_id", ""),
                  pr=run.get("pr", ""), outcome=run.get("outcome", ""))

    # 2. Stato ricostruito, entered_at, tipo, classe d'errore, priorità.
    for ind, d in dossier.items():
        dates = sorted(ev["at"] for ev in d["timeline"] if ev.get("at"))
        d["entered_at"] = dates[0] if dates else ""
        d["timeline"].sort(key=lambda e: (e.get("at") or "", EDITORIAL_ORDER.get(e.get("stage"), 9)))
        d["runs"] = sorted({r for r in d["runs"] if r})
        d["required_stages"] = _required_for(ind, "curator" in d["completed_stages"])
        d["state"], d["error_class"], d["motivo"] = _state_of(d)
        # `published` = fuso su master (= pubblicata). Vero anche se poi invalidato:
        # è ciò che serve alla reliability (un risultato pubblicato che si è rotto).
        d["published"] = _reached_publication(d)
        d["priority"] = practice_model.priority_score(
            {"flags": d["flags"], "state": d["state"], "type": d["type"],
             "completed_stages": d["completed_stages"], "score_eligible": d["score_eligible"],
             "required_stages": d["required_stages"],
             "entered_at": d["entered_at"], "attempts": 0},
            today or d["entered_at"] or "")
    return dossier


EDITORIAL_ORDER = {s: i for i, s in enumerate(
    ("scout", "hunter", "promoter", "curator", "writer", "reviewer", "verificatore"))}

# Le famiglie che passano dal curatore: solo gli esterni verticali hanno un verso
# da giudicare nel layer esterno. Il backbone territoriale (id numerici), il BES e
# il Multiscopo non hanno una curatela, quindi per loro `curator` non è uno stadio
# obbligatorio, e pretenderlo li terrebbe per sempre "in-lavorazione".
_EXTERNAL_PREFIXES = tuple(
    prefix for family, prefix in discovery.FAMILY_PREFIX.items()
    if prefix and family in discovery.FEED_FAMILY.values()
)


def _required_for(ind_id: str, has_curation: bool) -> tuple:
    req = list(practice_model.REQUIRED_STAGES["nuovo"])
    is_external = ind_id.startswith(_EXTERNAL_PREFIXES) or has_curation
    if not is_external and "curator" in req:
        req.remove("curator")
    return tuple(req)


def _reached_publication(d: dict) -> bool:
    """Vero se l'indicatore è arrivato alla pubblicazione, cioè fuso su master:
    il ciclo editoriale obbligatorio è completo e l'articolo è pieno.

    Resta vero anche se lo stato attuale è `invalidata` (un articolo pubblicato
    che poi si è rotto), perché è proprio quel caso che la reliability misura.
    Rimpiazza la vecchia lettura dalle prove sul sito: il progetto ha ratificato
    merge = pubblicazione, quindi l'articolo committato *è* la pubblicazione.
    """
    f = d["flags"]
    if f.get("rejected") or f.get("approved_candidate") and not d["completed_stages"]:
        return False
    required = d.get("required_stages") or practice_model.REQUIRED_STAGES.get(d["type"], ())
    return bool(required) and set(required).issubset(set(d["completed_stages"])) \
        and f.get("article_complete", True)


def _state_of(d: dict):
    """Lo stato ricostruito, la classe d'errore e il motivo, dalle bandiere.

    Ogni ramo è una condizione verificabile degli artefatti (§3): è ciò che
    rende lo stato riconciliabile e non solo dedotto una volta. Il `motivo` è
    valorizzato solo per `in-attesa`, l'unico stato di sosta armonizzato: dice
    perché è ferma e porta la classe d'errore giusta (§9).
    """
    f = d["flags"]
    if f.get("rejected"):
        return "chiusa", "terminale", ""
    if f.get("needs_info"):
        return "in-attesa", "ripetibile-dopo-cambio-esterno", "dipendenza-esterna"
    if f.get("open_smentita"):
        return "invalidata", "editoriale", ""
    # approvato ma senza manifest: l'orfano di PR #62, non lo riprende nessuno
    if f.get("approved_candidate") and "curator" not in d["completed_stages"] \
            and "writer" not in d["completed_stages"]:
        return "proposta", None, ""
    if f.get("stale_vintage") or f.get("stale_curation"):
        return "invalidata", "cambiamento-in-corsa", ""
    # ciclo editoriale completo? Su master l'articolo è committato, e il progetto
    # ha ratificato merge = pubblicazione: ciclo completo + articolo pieno =
    # `pubblicata`. Non c'è più uno stato `fusa` intermedio né una verifica-sito.
    required = d.get("required_stages") or practice_model.REQUIRED_STAGES.get(d["type"], ())
    if required and set(required).issubset(set(d["completed_stages"])):
        if not f.get("article_complete", True):
            return "in-lavorazione", None, ""
        return "pubblicata", None, ""
    if not d["completed_stages"]:
        return "in-attesa", None, "monte-mancante"
    return "in-lavorazione", None, ""


def reconcile(declared: dict, reconstructed: dict) -> list:
    """Confronta lo stato dichiarato (i record in practices/) con quello
    ricostruito dagli artefatti (Fase C). Restituisce le divergenze: è l'evento
    che il mandato chiede a 1.6 e 3.5, così una modifica fuori dalla pipeline non
    passa per assenza di lavoro."""
    # I record dichiarati sono indicizzati per `practice_id`, qui si riconcilia
    # per indicatore, quindi si normalizza sul campo `indicator_id` (o `id`).
    # Con i cicli (Fase E) un indicatore ha più record dichiarati: si riconcilia
    # il ciclo **attivo**, che porta lo stato corrente. Gli altri sono chiusi.
    by_ind = {}
    for rec in declared.values():
        ind = rec.get("indicator_id") or rec.get("id")
        if not ind:
            continue
        if ind not in by_ind or rec.get("active"):
            by_ind[ind] = rec

    out = []
    for ind, rec in reconstructed.items():
        want = rec["state"]
        if ind not in by_ind:
            out.append({"id": ind, "declared": None, "reconstructed": want, "kind": "mancante"})
        elif by_ind[ind].get("state") != want:
            out.append({"id": ind, "declared": by_ind[ind].get("state"),
                        "reconstructed": want, "kind": "divergente"})
    for ind, rec in by_ind.items():
        if ind not in reconstructed:
            out.append({"id": ind, "declared": rec.get("state"),
                        "reconstructed": None, "kind": "orfana"})
    return out


# --- collegamento ai lettori reali (tutti stdlib puri) ----------------------

def load_real(today: str = ""):
    from scripts import (curate, pending_notes, pipeline_log, indicator_store,
                         verification_queue)
    candidates = discovery.read_candidates()
    manifest = pending_notes.read_manifest()
    curation = curate.read_curation()
    external = curate.read_external()
    articles = indicator_store.load_all(strict=False)
    verifiche = verification_queue.load_verifications()
    runs = pipeline_log.collapse_runs(pipeline_log.read_journal())
    return reconstruct(candidates, manifest, curation, external, articles,
                       verifiche, runs, today=today)


# --- Fase E: i cicli di manutenzione, distinti ma collegati ------------------

def _cycle_trigger(ev: dict, seen_kinds: set, last_vintage) -> str | None:
    """Il tipo del ciclo che questo evento apre, o None se resta nel corrente.

    Un ciclo nuovo si apre solo su una pagina già arrivata a valle: una smentita
    è una pratica nuova (§13), un anno nuovo della fonte è un aggiornamento. Le
    prime occorrenze (la prima curatela, la prima scrittura) appartengono al ciclo
    di prima pubblicazione, non ne aprono uno.
    """
    kind = ev.get("kind")
    if kind == "verificata" and ev.get("esito") == "smentito":
        return "smentita"
    if kind == "curata" and "curata" in seen_kinds:
        return "aggiornamento"
    if kind == "scritta" and "scritta" in seen_kinds:
        v = ev.get("vintage")
        if v is not None and last_vintage is not None and v > last_vintage:
            return "aggiornamento"
    return None


def split_cycles(d: dict) -> list:
    """Spezza la storia di un indicatore in cicli distinti ma collegati (Fase E).

    Il primo ciclo è la prima pubblicazione (`nuovo`). Dopo, ogni innesco
    editoriale su una pagina già arrivata a valle apre un ciclo nuovo, legato
    allo stesso indicatore. L'ultimo ciclo è quello attivo e porta lo stato
    corrente ricostruito, i precedenti sono chiusi con esito `sostituita`, e
    restano nella storia (mai una PR eterna, mai un buco).

    Ricostruibili dagli artefatti committati sono `smentita` e `aggiornamento`,
    ritiro, rollback, integrazione e metadati esistono nel modello ma richiedono
    un segnale esplicito, quindi non si inventano qui.
    """
    events = d["timeline"]
    if not events:
        return [_cycle_record(d, 1, d["type"], [], active=True)]
    groups, cur, cur_type = [], [], "nuovo"
    seen, last_vintage = set(), None
    for ev in events:
        trig = _cycle_trigger(ev, seen, last_vintage) if cur else None
        if trig:
            groups.append((cur_type, cur))
            cur, cur_type = [], trig
        cur.append(ev)
        seen.add(ev.get("kind"))
        if ev.get("kind") == "scritta" and ev.get("vintage") is not None:
            last_vintage = ev.get("vintage")
    groups.append((cur_type, cur))
    return [_cycle_record(d, i, ctype, evs, active=(i == len(groups)))
            for i, (ctype, evs) in enumerate(groups, start=1)]


def _cycle_record(d: dict, seq: int, ctype: str, events: list, active: bool) -> dict:
    dates = [e["at"] for e in events if e.get("at")]
    rec = {
        "practice_id": practice_model.practice_id(d["id"], ctype, seq),
        "indicator_id": d["id"],
        "type": ctype,
        "seq": seq,
        "active": active,
        "opened_at": dates[0] if dates else d["entered_at"],
        "closed_at": None if active else (dates[-1] if dates else ""),
        "events": [e.get("kind") for e in events],
    }
    if active:
        rec.update({
            "state": d["state"],
            "outcome": None,
            "completed_stages": d["completed_stages"],
            "required_stages": d.get("required_stages", []),
            "flags": d["flags"],
            "error_class": d["error_class"],
            # Il motivo distingue una sosta normale (monte-mancante) da un blocco
            # esterno/tecnico: senza, il record `in-attesa` perde l'urgenza (§3, §9).
            "motivo": d.get("motivo", ""),
            "score_eligible": d["score_eligible"],
            "published": d["published"],
            "verification_valid": d["verification_valid"],
            "runs": d["runs"],
            "priority": d.get("priority"),
        })
    else:
        rec.update({"state": "chiusa", "outcome": "sostituita"})
    return rec


def cycles_for(d: dict) -> list:
    """Tutti i record di pratica di un indicatore, uno per ciclo (Fase E)."""
    return split_cycles(d)


def _dossier_to_record(d: dict) -> dict:
    """Il record della pratica **attiva** (l'ultimo ciclo), che porta lo stato
    corrente. I cicli precedenti stanno accanto, con `cycles_for`."""
    return cycles_for(d)[-1]


# --- Fase F: la priorità della pratica, mappata sullo stadio pronto ---------

def ready_stage(d: dict) -> str | None:
    """Lo stadio su cui una pratica sta aspettando, o None se non è lanciabile.

    È il ponte fra la priorità della pratica (§11) e il lanciatore, che nomina
    uno stadio: una smentita aspetta il revisore, una curatela scaduta il
    curatore, una rilettura il revisore, una proposta il promotore. Bloccata,
    in quarantena, chiusa o pubblicata non hanno uno stadio che le muova.
    """
    f, st = d["flags"], d["state"]
    if st in ("chiusa", "in-quarantena", "pubblicata"):
        return None
    if f.get("needs_info") or f.get("rejected"):
        return None
    if f.get("open_smentita"):
        return "reviewer"
    if f.get("stale_curation"):
        return "curator"
    if f.get("stale_vintage"):
        return "reviewer"
    if st == "proposta":
        return "promoter"
    for stage in d.get("required_stages") or ():
        if stage not in d["completed_stages"]:
            return stage
    return None


def stage_priorities(dossier: dict) -> dict:
    """`{stadio: priorità massima di una pratica pronta su quello stadio}`.

    È ciò che il lanciatore consulta, in modalità priorità (Fase F), per non
    far aspettare una correzione urgente dietro una coda di candidature nuove.
    """
    out = {}
    for d in dossier.values():
        stage = ready_stage(d)
        if stage:
            out[stage] = max(out.get(stage, float("-inf")), d.get("priority", 0.0))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator", help="la storia intera di un indicatore")
    parser.add_argument("--json", action="store_true", help="uscita per un altro programma")
    parser.add_argument("--write", action="store_true", help="scrive i record in practices/")
    parser.add_argument("--check", action="store_true",
                        help="riconcilia i record dichiarati con gli artefatti (esce !=0 se divergono)")
    parser.add_argument("--today", default="", help="data di riferimento YYYY-MM-DD per la priorità")
    args = parser.parse_args(argv)

    dossier = load_real(today=args.today)

    if args.check:
        from scripts import practice_store
        declared = practice_store.load_all(strict=False)
        divergenze = reconcile(declared, {k: v for k, v in dossier.items()})
        if args.json:
            print(json.dumps(divergenze, ensure_ascii=False, indent=1))
        else:
            if not divergenze:
                print("riconciliazione: nessuna divergenza")
            for row in divergenze:
                print(f"[{row['kind']}] {row['id']}: dichiarato={row['declared']} "
                      f"ricostruito={row['reconstructed']}")
        return 1 if divergenze else 0

    if args.write:
        from scripts import practice_store
        n = 0
        for d in dossier.values():
            for rec in cycles_for(d):
                practice_store.save(rec)
                n += 1
        print(f"scritti {n} record ({len(dossier)} indicatori) in {practice_store.ROOT}")
        return 0

    if args.indicator:
        d = dossier.get(args.indicator)
        if not d:
            print(f"nessuna traccia di {args.indicator}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(d, ensure_ascii=False, indent=1))
            return 0
        _print_one(d)
        return 0

    if args.json:
        print(json.dumps({k: _dossier_to_record(v) for k, v in dossier.items()},
                         ensure_ascii=False, indent=1))
        return 0
    _print_table(dossier)
    return 0


def _print_table(dossier: dict) -> None:
    rows = sorted(dossier.values(), key=lambda d: (-d.get("priority", 0), d["id"]))
    print(f"{'indicatore':32} {'stato':18} {'stadi':22} {'prio':>6}  entrato")
    print("-" * 92)
    for d in rows:
        stages = ",".join(s[:3] for s in d["completed_stages"]) or "-"
        print(f"{d['id']:32.32} {d['state']:18} {stages:22.22} "
              f"{d.get('priority', 0):6.1f}  {d['entered_at'] or '?'}")
    print(f"\n{len(rows)} indicatori. Nota: una pratica per indicatore (Fase B), "
          "gli eventi di manutenzione sono nella timeline.")


def _print_one(d: dict) -> None:
    print(f"# {d['id']}  ({d['type']})")
    print(f"  stato        {d['state']}"
          + (f"  [errore: {d['error_class']}]" if d["error_class"] else ""))
    print(f"  entrato      {d['entered_at'] or '?'}")
    print(f"  stadi        {', '.join(d['completed_stages']) or '-'}")
    print(f"  score        {'nel punteggio' if d['score_eligible'] else 'fuori'}")
    print(f"  pubblicata   {d['published'] if d['published'] is not None else 'non verificato sul sito'}")
    print(f"  verifica     {'valida' if d['verification_valid'] else 'scaduta' if d['verification_valid'] is False else 'assente'}")
    flags = ", ".join(k for k, v in d["flags"].items() if v is True)
    if flags:
        print(f"  bandiere     {flags}")
    print(f"  priorità    {d.get('priority', 0)}")
    print("  timeline:")
    for ev in d["timeline"]:
        at = ev.get("at") or "        ?"
        print(f"    {at:10} {ev.get('stage', ''):12} {ev.get('kind', ''):12} {ev.get('detail', '')}")


if __name__ == "__main__":
    raise SystemExit(main())
