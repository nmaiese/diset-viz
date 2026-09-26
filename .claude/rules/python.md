---
paths:
  - "**/*.py"
---

# Python

Valgono per il codice di questo repository.

- Nessun LLM dove basta un parser. L'ingest, la validazione, le metriche e le bande sono deterministici.
- Un errore è un'eccezione con contesto (status, URL, sito), mai una lista vuota o un `return None` silenzioso.
- Date esplicite come parametri: mai `date.today()` dentro un connettore o una query. Il chiamante decide la finestra.
- Identificatori in inglese, docstring e messaggi in italiano. La suite canonica `bin/py -m unittest discover -s tests -v` deve essere verde prima di aprire una PR.
  Tre moduli sono nati con identificatori italiani e restano cosi', perche' rinominarli costa un diff grande e non corregge niente: `app/province_profile.py`, `scripts/duplicazione.py`, `scripts/togli_domande_retoriche.py`. L'eccezione e' chiusa: il codice nuovo va in inglese, anche quando si aggiunge a quei moduli (decisione del 23/9).
- Test senza rete: risposte registrate in `tests/fixtures/`; gli smoke reali portano `@pytest.mark.live`.
