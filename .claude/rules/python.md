---
paths:
  - "**/*.py"
---

# Python

Valgono per il codice di questo repo. Il codice della redazione
(`nmaiese/redazione-ai`) ha le sue regole li'.

- Nessun LLM dove basta un parser. L'ingest, la validazione, le metriche e le bande sono deterministici.
- Un errore è un'eccezione con contesto (status, URL, sito), mai una lista vuota o un `return None` silenzioso.
- Date esplicite come parametri: mai `date.today()` dentro un connettore o una query. Il chiamante decide la finestra.
- Identificatori in inglese, docstring e messaggi in italiano. `ruff check` pulito, `pytest -q` verde prima di aprire una PR.
- Test senza rete: risposte registrate in `tests/fixtures/`; gli smoke reali portano `@pytest.mark.live`.
