"""Retry policy of the SDMX client.

A transient 5xx on the dataflow catalogue used to abort the whole scout run:
`_fetch_with_retry` retried 429/503 but let a 500 through, and one 500 meant a
dispatch run that came back with every proposal at `needs-info` and zero
approvals. The fault was the server's for a minute, not the catalogue's. These
tests pin the recovery, with an injected opener and a no-op sleeper, so no real
network and no real backoff are involved.
"""

import tempfile
import unittest
import urllib.error

from scripts import istat_sdmx


def http_error(code):
    return urllib.error.HTTPError("http://x/df", code, "boom", {}, None)


class Opener:
    """A fake network layer. `script` is the sequence of things a request does:
    an int is an HTTP status to raise as HTTPError, a bytes value is a 200 body."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def __call__(self, url, headers):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, int):
            raise http_error(step)
        return 200, step


def client(opener):
    sleeps = []
    c = istat_sdmx.SdmxClient(
        cache_dir=tempfile.mkdtemp(),
        min_interval=0.0,
        initial_backoff=0.0,
        max_retries=4,
        sleeper=lambda s: sleeps.append(s),
        clock=lambda: 0.0,
        opener=opener,
    )
    return c, sleeps


class Retry(unittest.TestCase):
    def test_a_transient_500_recovers(self):
        """Two 500s then a body: the run does not die, it waits and gets there."""
        opener = Opener([500, 500, b"ok"])
        c, sleeps = client(opener)
        self.assertEqual(c._fetch_with_retry("http://x/df", "application/xml"), b"ok")
        self.assertEqual(opener.calls, 3)
        self.assertEqual(len(sleeps), 2)

    def test_500_502_504_are_all_retried(self):
        for code in (500, 502, 504):
            with self.subTest(code=code):
                opener = Opener([code, b"ok"])
                c, _ = client(opener)
                self.assertEqual(
                    c._fetch_with_retry("http://x/df", "application/xml"), b"ok"
                )

    def test_a_persistent_500_is_a_server_error_not_a_rate_limit(self):
        """Exhausted 5xx names the fault honestly: the server is faulting, not
        throttling, so it is not an IstatRateLimitError and not a bare one."""
        opener = Opener([500, 500, 500, 500, 500])
        c, _ = client(opener)
        with self.assertRaises(istat_sdmx.IstatServerError):
            c._fetch_with_retry("http://x/df", "application/xml")

    def test_a_throttle_is_still_a_rate_limit(self):
        opener = Opener([503, 503, 503, 503, 503])
        c, _ = client(opener)
        with self.assertRaises(istat_sdmx.IstatRateLimitError):
            c._fetch_with_retry("http://x/df", "application/xml")

    def test_a_403_is_a_block_and_is_not_retried(self):
        opener = Opener([403, b"never"])
        c, _ = client(opener)
        with self.assertRaises(istat_sdmx.IstatBlockedError):
            c._fetch_with_retry("http://x/df", "application/xml")
        self.assertEqual(opener.calls, 1)


if __name__ == "__main__":
    unittest.main()
