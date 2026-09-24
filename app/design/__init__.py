"""Le pagine della 1.0: i filtri delle cifre e il passaggio dalla view al template.

Il progetto sta in `design/v1/` (sistema, token, prototipi), fuori
dall'immagine che va in produzione: qui c'e' solo cio' che serve a servire le
pagine. Una pagina della 1.0 riceve lo stesso contesto di prima piu' `d`, cio'
che il suo modulo in `app/design/pages/` ricava da quel contesto.

Se il modulo o il template sollevano, la pagina si serve col template di prima
e l'errore finisce nel log: una scheda senza la regia nuova e' meglio di un
500 sulla pagina che porta l'87% dei clic. I test tengono la rete tesa
(`DIVARIO_V1_STRICT`, messo da `tests/conftest.py`) e la prova delle pagine
controlla che ne esca la versione nuova, cosi' il ripiego non nasconde un
guasto.
"""

from __future__ import annotations

import importlib
import os

from flask import current_app, render_template

from app.design import numfmt

# Il segno che una pagina e' uscita dal template della 1.0 e non dal ripiego.
MARKER = 'data-v1="'


def register(app) -> None:
    """I filtri dei template: `{{ v | num('euro') }}`, `{{ 14 | rank(20) }}`,
    `{{ d | delta('euro') }}`, e `column_decimals` per le colonne."""
    app.jinja_env.filters["num"] = numfmt.num
    app.jinja_env.filters["rank"] = numfmt.rank
    app.jinja_env.filters["delta"] = numfmt.delta
    app.jinja_env.filters["numtext"] = numfmt.text
    app.jinja_env.filters["phrase_unit"] = numfmt.phrase_unit
    app.jinja_env.filters["of_place"] = _of_place
    app.jinja_env.globals["column_decimals"] = numfmt.column_decimals
    app.jinja_env.globals["v1_paths"] = _paths()


def _of_place(name: str, level_key: str) -> str:
    """`{{ name | of_place(level.key) }}`: "della Calabria", "di Treviso", "del Sud Sardegna"."""
    from app.design.common import of_place

    return of_place(name, level_key)


def _paths() -> dict:
    """I contorni delle regioni per le mappe della 1.0, letti una volta."""
    import json
    from pathlib import Path

    return json.loads((Path(__file__).resolve().parent / "italy_paths.json").read_text(encoding="utf-8"))


def derive(page: str, ctx: dict) -> dict:
    module = importlib.import_module(f"app.design.pages.{page.replace('-', '_')}")
    return module.derive(ctx)


def render(page: str, template: str, fallback: str, **ctx) -> str:
    """Il template della 1.0 con `d`, oppure quello di prima se qualcosa cede."""
    try:
        d = derive(page, ctx)
        return render_template(template, d=d, v1_page=page, **ctx)
    except Exception:
        if os.environ.get("DIVARIO_V1_STRICT"):
            raise
        current_app.logger.exception("pagina 1.0 %s: ripiego sul template %s", page, fallback)
        return render_template(fallback, **ctx)
