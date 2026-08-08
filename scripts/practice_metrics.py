#!/usr/bin/env python3
"""Le metriche della revisione (mandato, sezione 5).

Il progetto non è riuscito perché usa una PR unica. È riuscito se, per ogni
indicatore, si sa senza ricostruzione manuale da dove è partito, che decisioni
ha attraversato, se è pubblicato e se quella versione è ancora valida. Questo
script misura proprio questo, dai soli artefatti committati, così il confronto
prima/dopo il cutover (Fase F) è un numero e non un'impressione.

È una **fotografia**, read-only: prende lo stato ricostruito e i run, e calcola
il sottoinsieme di metriche che una fotografia può dare. Le metriche che vogliono
una storia nel tempo (tentativi duplicati, pratiche perse dopo un'interruzione)
non si inventano da un'istantanea: sono marcate `None` con il motivo, invece di
un numero finto. Girarlo prima e dopo il cutover, e diffare, è il confronto che
il mandato mette come condizione della Fase F.

    python3 scripts/practice_metrics.py
    python3 scripts/practice_metrics.py --json
    python3 scripts/practice_metrics.py --today 2026-07-28 --soglia-giorni 30

Stdlib puro come il resto della catena.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import practice_model, practice_timeline  # noqa: E402

TERMINAL_STATES = ("chiusa", "pubblicata")
NON_MISURABILE = "richiede una storia nel tempo, non un'istantanea"


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def compute(dossier: dict, runs: list, today: str = "", soglia_giorni: int = 30,
            declared: dict | None = None) -> dict:
    """Le metriche dai dossier ricostruiti e dai run. Puro, niente disco."""
    indicators = list(dossier.values())
    n = len(indicators)

    def days_open(d):
        end = today or d.get("entered_at", "")
        return practice_model._days_between(d.get("entered_at", ""), end)

    aperte = [d for d in indicators if d["state"] not in TERMINAL_STATES]
    invalidati_pubblicati = [d for d in indicators
                             if d["published"] is True and d["state"] == "invalidata"]
    errori_pubblici = [d for d in indicators if d["flags"].get("open_smentita")
                       and d["state"] in ("pubblicata", "invalidata")]
    # Stesso predicato di `pipeline_monitor.is_stuck`: una `in-attesa` conta come
    # ferma solo se il motivo non è monte-mancante (contropressione normale). Se
    # divergesse, la metrica prima/dopo direbbe "bloccate" ciò che il cruscotto
    # non chiama bloccato.
    bloccate = [d for d in indicators
                if d["state"] == "in-quarantena"
                or (d["state"] == "in-attesa"
                    and d.get("motivo") not in (None, "", "monte-mancante"))]
    invalidate = [d for d in indicators if d["state"] == "invalidata"]
    ferme_oltre = [d for d in aperte if days_open(d) > soglia_giorni]

    run_associati = sum(1 for r in runs
                        if practice_timeline._ids_in_text(
                            (r.get("summary") or "") + "\n" + "\n".join(r.get("detail") or [])))
    touched = {ind for d in indicators for ind in [d["id"]] if d["runs"]}
    run_totali_con_indicatore = sum(len(d["runs"]) for d in indicators)

    incoerenti = None
    if declared:
        incoerenti = len(practice_timeline.reconcile(declared, dossier))

    return {
        "osservabilita": {
            "indicatori_totali": n,
            "storia_completa_pct": _pct(sum(1 for d in indicators
                                            if d["entered_at"] and d["timeline"]), n),
            "quota_run_associati_a_un_indicatore_pct": _pct(run_associati, len(runs)),
            "pratiche_stato_incoerente": incoerenti,
        },
        "affidabilita": {
            "risultati_invalidati_pubblicati": len(invalidati_pubblicati),
            "errori_pubblici_dopo_pubblicazione": len(errori_pubblici),
            "tentativi_duplicati": None,
            "transizioni_applicate_due_volte": None,
            "pratiche_perse_dopo_interruzione": None,
            "_nota": NON_MISURABILE,
        },
        "velocita": {
            "pratiche_aperte": len(aperte),
            "eta_media_aperte_giorni": (round(sum(days_open(d) for d in aperte) / len(aperte), 1)
                                        if aperte else 0),
            "ferme_oltre_soglia": len(ferme_oltre),
            "soglia_giorni": soglia_giorni,
            "bloccate": len(bloccate),
        },
        "qualita": {
            "smentite_aperte": len(errori_pubblici),
            "ritorni_a_stadio_precedente": len(invalidate),
            "controlli_saltati": None,
            "_nota": NON_MISURABILE,
        },
        "costo": {
            "indicatori_con_run_associati": len(touched),
            "run_associati_a_indicatori": run_totali_con_indicatore,
            "run_per_indicatore_toccato": (round(run_totali_con_indicatore / len(touched), 2)
                                           if touched else 0),
        },
    }


def _resolve_today(today: str = "") -> str:
    """La data di riferimento, o oggi se non è data. Senza, la fotografia userebbe
    `entered_at` come fine e ogni pratica risulterebbe di zero giorni: età media
    zero, niente oltre soglia, il confronto prima/dopo falsato. Oggi è il default
    giusto per la CLI documentata, che gira senza `--today`."""
    if today:
        return today
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_and_compute(today: str = "", soglia_giorni: int = 30):
    from scripts import pipeline_log, practice_store
    today = _resolve_today(today)
    dossier = practice_timeline.load_real(today=today)
    runs = pipeline_log.collapse_runs(pipeline_log.read_journal())
    declared = practice_store.load_all(strict=False) or None
    return compute(dossier, runs, today=today, soglia_giorni=soglia_giorni, declared=declared)


def _print(metrics: dict) -> None:
    for group, values in metrics.items():
        print(f"# {group}")
        for k, v in values.items():
            if k == "_nota":
                print(f"    ({v})")
            else:
                print(f"    {k:44} {v}")
        print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default="", help="data di riferimento YYYY-MM-DD")
    parser.add_argument("--soglia-giorni", type=int, default=30,
                        help="soglia oltre cui una pratica aperta è 'ferma'")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    metrics = load_and_compute(today=args.today, soglia_giorni=args.soglia_giorni)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=1))
    else:
        _print(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
