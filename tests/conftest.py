"""Shared configuration for the test suite (unittest compatible).

Clears all lru_cache decorators between tests to prevent state contamination,
disables SimpleCache (not thread-safe), and provides common test setup.

Works with both unittest (python -m unittest) and pytest.
"""

import os
import unittest
import sys


def _clear_lru_caches():
    """Clear all lru_cache decorators in app modules."""
    import app.data
    import app.atlas_catalog
    import app.indicator_view
    import app.eurostat_atlas
    import app.blog

    modules = [
        app.data,
        app.atlas_catalog,
        app.indicator_view,
        app.eurostat_atlas,
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


# Module-level setup: disable SimpleCache before any tests run
disable_simple_cache()


# Monkey-patch unittest.TestCase to auto-clear caches before/after each test
_original_run = unittest.TestCase.run

def _run_with_cache_cleanup(self, result=None):
    """Clear lru_caches before and after each test method."""
    _clear_lru_caches()
    try:
        return _original_run(self, result)
    finally:
        _clear_lru_caches()

unittest.TestCase.run = _run_with_cache_cleanup
