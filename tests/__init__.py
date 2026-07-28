"""Importing this package wires tests/conftest.py's one-time cache clear and
SimpleCache override into plain ``python -m unittest discover`` runs.

conftest.py by itself is a pytest convention: pytest auto-loads it, unittest
never does. Without this import, this project's tests run under a Flask
SimpleCache that is not thread-safe, and the app's lru_cache-backed data can
start the suite warm with whatever a previous process left in it.
"""

from . import conftest  # noqa: F401
