"""Il sito non legge niente da `design/` a runtime.

`design/` e' il cantiere della 1.0 (sistema, token, prototipi, dati catturati):
sta nel repo, e quindi nel checkout della CI, ma il Dockerfile non lo copia
nell'immagine di Cloud Run. Un modulo di `app/` che apre un file la' dentro
passa in locale e nei test, e in produzione solleva al primo render. I moduli
di `app/design/` sono nati come script dei prototipi, che quei file li
leggevano: questa prova e' il solo posto dove l'errore si vede prima del
deploy.
"""

import ast
import re
import unittest
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
VIETATI = re.compile(r"design/v1|design-system/|\.context\.json")


def _docstring_ids(albero):
    """Gli id dei nodi che sono docstring: raccontano il cantiere, non lo aprono."""
    ids = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = nodo.body
            if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant):
                ids.add(id(corpo[0].value))
    return ids


class NienteDesignARuntime(unittest.TestCase):
    def test_nessun_modulo_dell_app_legge_il_cantiere(self):
        """Stringhe nel codice (non docstring, non commenti) che nominano il
        cantiere, un segmento di percorso "design" nudo, o un `sys.path` toccato."""
        trovati = []
        for percorso in sorted((RADICE / "app").rglob("*.py")):
            albero = ast.parse(percorso.read_text(encoding="utf-8"))
            docstring = _docstring_ids(albero)
            for nodo in ast.walk(albero):
                dove = f"{percorso.relative_to(RADICE)}:{getattr(nodo, 'lineno', '?')}"
                if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and id(nodo) not in docstring:
                    if VIETATI.search(nodo.value) or nodo.value == "design":
                        trovati.append(f"{dove}: {nodo.value[:60]!r}")
                elif isinstance(nodo, ast.Attribute) and nodo.attr == "insert" and \
                        isinstance(nodo.value, ast.Attribute) and nodo.value.attr == "path":
                    trovati.append(f"{dove}: sys.path.insert")
        self.assertEqual(trovati, [])

    def test_il_dockerfile_non_copia_il_cantiere(self):
        dockerfile = (RADICE / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotRegex(dockerfile, r"COPY\s+(\.\s|design)")

    def test_i_file_che_le_pagine_leggono_stanno_in_app(self):
        self.assertTrue((RADICE / "app" / "design" / "italy_paths.json").is_file())
