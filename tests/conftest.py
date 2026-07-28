"""Shared configuration for the test suite (unittest compatible).

Clears all lru_cache decorators once, before the suite starts, so a run never
inherits whatever a previous process left cached, and disables SimpleCache
(not thread-safe).

The data these caches hold (the parsed indicator CSVs, the built catalog) is
read-only for the whole run: no test mutates it in place, so a single clear at
import time is enough to guarantee a cold, deterministic first read. Clearing
again before and after every single test method was tried and measured: it
turned test_app.py alone from 10.7s to 58.6s, because app/data.py's lru_cache
exists specifically to avoid re-filtering the ~110k-row dataset on every call
(see the comment above INDICATOR_ROWS in app/data.py). Multiplied across the
whole integration suite that pushed the run past 3 minutes for no isolation
benefit anything here actually needs.

Works with both unittest (python -m unittest, via tests/__init__.py importing
this module) and pytest (which loads conftest.py on its own).
"""

import os


def _clear_lru_caches():
    """Clear all lru_cache decorators in app modules."""
    import app.data
    import app.atlas_catalog
    import app.indicator_view
    import app.external_atlas
    import app.blog

    modules = [
        app.data,
        app.atlas_catalog,
        app.indicator_view,
        app.external_atlas,
        app.blog,
    ]
    for module in modules:
        for name in dir(module):
            obj = getattr(module, name)
            if hasattr(obj, 'cache_clear'):
                obj.cache_clear()


def disable_simple_cache():
    """Disable SimpleCache in tests (not thread-safe).

    Set CACHE_TYPE to 'null' before importing Flask app to use NullCache,
    which is safe for testing and prevents race conditions.
    """
    os.environ.setdefault('CACHE_TYPE', 'null')


# Module-level setup: runs once, when this module is first imported.
disable_simple_cache()
_clear_lru_caches()
