#!/usr/bin/env python3
"""Lo store delle pratiche editoriali: un file per record.

Rispetta l'invariante della catena (`content/indicators/`, `data/pipeline/runs/`,
`data/pipeline/verifiche/` sono tutti a un file per record): il conflitto fra due
scrittori non è meno probabile, è impossibile. Un record vive in
`data/pipeline/practices/<slug>.json`, e la sua identità autorevole è il campo
`practice_id` **dentro** il file, non il nome del file. Il nome è solo un
raccoglitore leggibile e stabile.

Perché l'id sta dentro e non nel nome: una chiave di pratica contiene `:`, `#` e
può contenere `-` (`bes:09PAE009-N25#nuovo-1`), e nessuna codifica di quei
caratteri in un nome di file è reversibile senza ambiguità. Invece di
inventarne una fragile, il nome è uno slug ripulito più un'impronta corta e
deterministica della chiave, che toglie ogni collisione senza dover tornare
indietro dal nome all'id. È la stessa filosofia dei nomi in `verifiche/`.

Stdlib puro come il resto della catena.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "data" / "pipeline" / "practices"

ID_FIELD = "practice_id"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class StoreError(RuntimeError):
    pass


def filename_for(practice_id: str) -> str:
    """Il nome del file che contiene la pratica `practice_id`.

    Slug leggibile più impronta della chiave: due chiavi diverse che
    ripuliscono allo stesso slug restano su due file diversi, perché l'impronta
    è della chiave intera. Deterministica: nessun `random`, come ogni cosa che
    deve reggere una ripresa a freddo.
    """
    pid = str(practice_id)
    slug = _UNSAFE.sub("_", pid).strip("_") or "practice"
    digest = hashlib.sha1(pid.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:80]}-{digest}.json"


def path_for(practice_id: str, root=None) -> Path:
    return Path(root or ROOT) / filename_for(practice_id)


def paths(root=None):
    base = Path(root or ROOT)
    if not base.is_dir():
        return []
    return sorted(base.glob("*.json"))


def load_all(root=None, strict=True) -> dict:
    """Tutte le pratiche, come `{practice_id: record}`.

    `strict` decide che cosa costa un file rotto, come in `indicator_store`: per
    chi lavora sulla catena un record illeggibile deve fermare tutto, forte; per
    una vista tollerante ripiega saltando il record.
    """
    base = Path(root or ROOT)
    entries: dict = {}
    for path in paths(base):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or not record.get(ID_FIELD):
                raise StoreError(f"{path.name} non ha un campo '{ID_FIELD}'")
            pid = record[ID_FIELD]
            if pid in entries:
                raise StoreError(f"due file per la stessa pratica '{pid}'")
            entries[pid] = record
        except (StoreError, json.JSONDecodeError):
            if strict:
                raise
    return entries


def load(practice_id: str, root=None):
    path = path_for(practice_id, root=root)
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    return record if isinstance(record, dict) else None


def save(record: dict, root=None) -> Path:
    """Scrive un record. Deve portare `practice_id`; il file prende il nome da lì."""
    pid = record.get(ID_FIELD)
    if not pid:
        raise StoreError(f"il record non ha un campo '{ID_FIELD}': {record!r}")
    base = Path(root or ROOT)
    base.mkdir(parents=True, exist_ok=True)
    path = base / filename_for(pid)
    payload = {ID_FIELD: pid, **{k: v for k, v in record.items() if k != ID_FIELD}}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def remove(practice_id: str, root=None) -> bool:
    path = path_for(practice_id, root=root)
    if path.exists():
        path.unlink()
        return True
    return False
