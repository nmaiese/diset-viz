#!/usr/bin/env python3
"""Polite, cached client for the Istat SDMX REST web service.

The Istat endpoint (https://esploradati.istat.it/SDMXWS/rest) enforces a hard
limit of **5 queries per minute per IP**; going over blocks the IP for 1-2 days.
Everything here is built around never tripping that:

- one process, never parallel;
- a minimum spacing between *network* calls (default 16s, i.e. <= ~4/min);
- an on-disk cache keyed by URL+Accept: a cached response costs no network call
  and no rate budget, so a rerun is idempotent and resumable after any stop;

The cache is deliberately split in two by lifetime. **Structures** (dataflows,
DSDs, codelists) change rarely and are cached forever: re-fetching them only
burns rate budget. **Data** responses are the whole point of a scheduled
refresh, so they carry a max age (`data_max_age`, default `DATA_MAX_AGE`): past
it the entry is refetched. Without that split a long-lived cache (a CI cache
restored on every run, for instance) would pin the job to the first response
ever saved and no new Istat release would ever be discovered.

Rate-limit safety is unaffected: an expired entry costs one throttled request,
and `cache_only` mode still serves whatever is on disk regardless of age.
- exponential backoff on 429/503/transient errors;
- explicit detection of an IP block (403 / empty 200) that stops with a clear
  message instead of hammering the endpoint.

Format is selected through the Accept header only (Istat ignores `format=`):
data as SDMX-CSV (parsed with the stdlib `csv` module), structures as SDMX-JSON
(parsed with `json`). Standard library only, matching `scripts/update_data.py`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://esploradati.istat.it/SDMXWS/rest"
AGENCY = "IT1"
USER_AGENT = "diset-viz-data-updater/1.0 (+https://divarioitalia.it)"
# Istat is picky about these exact strings: data CSV is version 1.0.0, but the
# structure JSON media type is version 1.0 (a 1.0.0 there returns HTTP 406).
ACCEPT_CSV = "application/vnd.sdmx.data+csv;version=1.0.0"
ACCEPT_STRUCTURE_JSON = "application/vnd.sdmx.structure+json;version=1.0"
# Data responses go stale; structures do not. Six days is just under the weekly
# refresh cadence, so a scheduled run always re-reads the data it is there for.
DATA_MAX_AGE = 6 * 24 * 3600
# Sentinel for "this response never expires" (structures).
CACHE_FOREVER = None


class IstatRateLimitError(RuntimeError):
    """Raised after retries when the endpoint keeps throttling (429/503)."""


class IstatServerError(RuntimeError):
    """Raised after retries on a transient server fault (500/502/504).

    The SDMX endpoint 500s intermittently on the dataflow catalogue, and a bare
    500 that aborts the whole run is exactly how a scout dispatch run came back
    with every proposal at `needs-info` and zero approvals: the fault was the
    server's for one minute, not the catalogue's. A 5xx is transient far more
    often than not, so it is retried with backoff like a 503, and only a run of
    them in a row is a real outage worth stopping on.
    """


# Status codes worth a backoff-and-retry rather than an immediate abort: the
# throttles (429/503) and the transient server faults (500/502/504). A 403 is
# NOT here on purpose: it means a block, and retrying a block wastes the budget
# that the wait needs.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
THROTTLE_STATUS = frozenset({429, 503})


class IstatBlockedError(RuntimeError):
    """Raised when the endpoint looks like it has blocked the IP (403/empty)."""


class CacheMissError(RuntimeError):
    """Raised in cache_only mode when a response is not already on disk."""


class SdmxClient:
    """Cache-first, rate-limited HTTP client for the Istat SDMX REST API."""

    def __init__(
        self,
        cache_dir,
        base_url=BASE_URL,
        min_interval=16.0,
        max_retries=4,
        timeout=120,
        initial_backoff=30.0,
        accept_language="it",
        cache_only=False,
        data_max_age=DATA_MAX_AGE,
        refresh_data=False,
        sleeper=time.sleep,
        clock=time.monotonic,
        wall_clock=time.time,
        opener=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.accept_language = accept_language
        self.cache_only = cache_only
        self.data_max_age = data_max_age
        self.refresh_data = bool(refresh_data)
        self.min_interval = float(min_interval)
        self.max_retries = int(max_retries)
        self.timeout = timeout
        self.initial_backoff = float(initial_backoff)
        self._sleep = sleeper
        self._clock = clock
        # Wall clock, separate from the monotonic throttle clock: cache ages are
        # compared against file mtimes, which survive the process.
        self._wall_clock = wall_clock
        # Test seam: opener(url, headers) -> (status:int, body:bytes). When None
        # we hit the network with urllib.
        self._opener = opener
        self._last_request = None  # monotonic time of the last *network* call
        self.request_count = 0     # network calls actually made (not cache hits)

    # -- public API ---------------------------------------------------------

    def get(self, path, accept, max_age=CACHE_FOREVER, force=False):
        """Return the raw response bytes for `path`, cache-first.

        `max_age` is the entry's lifetime in seconds (None = never expires).
        `force` refetches even a fresh entry. In `cache_only` mode whatever is
        on disk is served regardless of age, since no network call is allowed.
        """
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        cache_path = self._cache_path(url, accept)
        if cache_path.exists():
            if self.cache_only or (not force and self._is_fresh(cache_path, max_age)):
                return cache_path.read_bytes()
        if self.cache_only:
            raise CacheMissError(f"Not cached and cache_only is set: {url}")
        body = self._fetch_with_retry(url, accept)
        tmp = cache_path.with_suffix(".part")
        tmp.write_bytes(body)
        tmp.replace(cache_path)
        return body

    def dataflows(self, force=False):
        """All dataflows for the IT1 agency, parsed to a list of dicts.

        The catalogue is cache-forever by default (one request, shared with the
        scout and the province discovery). `force=True` refetches it even when a
        copy is on disk: that is how the scout re-polls for dataflows Istat has
        published since its last run, so source discovery stays continuous
        instead of freezing on the first cached snapshot.
        """
        body = self.get(f"dataflow/{AGENCY}", ACCEPT_STRUCTURE_JSON, force=force)
        return parse_dataflows(body)

    def datastructure(self, dsd_id, agency=AGENCY):
        body = self.get(f"datastructure/{agency}/{dsd_id}", ACCEPT_STRUCTURE_JSON)
        return parse_datastructure(body)

    def codelist(self, codelist_id, agency=AGENCY):
        body = self.get(f"codelist/{agency}/{codelist_id}", ACCEPT_STRUCTURE_JSON)
        return parse_codelist(body)

    def data(self, flow_ref, key="", start=None):
        """Fetch data for a dataflow as SDMX-CSV; returns parsed list of dicts.

        `key` is the dot-separated dimension filter (empty = all). Only
        `startPeriod` is used: Istat has an off-by-one bug on `endPeriod`, so we
        keep all recent years and filter later.
        """
        path = f"data/{flow_ref}"
        if key:
            path += f"/{key}"
        if start is not None:
            path += f"?startPeriod={start}"
        body = self.get(
            path, ACCEPT_CSV, max_age=self.data_max_age, force=self.refresh_data
        )
        return parse_sdmx_csv(body)

    # -- internals ----------------------------------------------------------

    def _is_fresh(self, cache_path, max_age):
        if max_age is None:
            return True
        try:
            age = self._wall_clock() - cache_path.stat().st_mtime
        except OSError:
            return False
        return age <= float(max_age)

    def _cache_path(self, url, accept):
        digest = hashlib.sha256(
            f"{url}|{accept}|{self.accept_language}".encode("utf-8")
        ).hexdigest()[:32]
        return self.cache_dir / f"{digest}.bin"

    def _throttle(self):
        if self._last_request is None:
            return
        wait = self.min_interval - (self._clock() - self._last_request)
        if wait > 0:
            self._sleep(wait)

    def _network_get(self, url, accept):
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        if self.accept_language:
            headers["Accept-Language"] = self.accept_language
        if self._opener is not None:
            return self._opener(url, headers)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return getattr(response, "status", 200), response.read()

    def _fetch_with_retry(self, url, accept):
        backoff = self.initial_backoff
        for attempt in range(self.max_retries + 1):
            self._throttle()
            self._last_request = self._clock()
            self.request_count += 1
            try:
                status, body = self._network_get(url, accept)
            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    raise IstatBlockedError(
                        f"HTTP 403 for {url}: the IP may be blocked. Stop and wait "
                        "1-2 days before retrying."
                    ) from exc
                if exc.code in RETRYABLE_STATUS and attempt < self.max_retries:
                    self._sleep(backoff)
                    backoff *= 2
                    continue
                if exc.code in THROTTLE_STATUS:
                    raise IstatRateLimitError(
                        f"HTTP {exc.code} for {url} after {self.max_retries} retries. "
                        "Back off for several minutes."
                    ) from exc
                if exc.code in RETRYABLE_STATUS:
                    raise IstatServerError(
                        f"HTTP {exc.code} for {url} after {self.max_retries} retries. "
                        "The endpoint is faulting, not blocking: retry in a few minutes."
                    ) from exc
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                # A read timeout on a large SDMX response surfaces as a bare
                # TimeoutError (not wrapped in URLError), so catch it here and
                # retry with backoff instead of aborting the whole run.
                if attempt < self.max_retries:
                    self._sleep(backoff)
                    backoff *= 2
                    continue
                raise
            if status == 200 and body:
                return body
            if status == 403 or (status == 200 and not body):
                raise IstatBlockedError(
                    f"Suspicious response ({status}, {len(body)} bytes) for {url}: "
                    "possible IP block. Stop and wait before retrying."
                )
            if status in RETRYABLE_STATUS and attempt < self.max_retries:
                self._sleep(backoff)
                backoff *= 2
                continue
            raise RuntimeError(f"HTTP {status} for {url}")
        raise RuntimeError(f"Exhausted retries for {url}")


# -- parsers (pure functions, easy to unit-test offline) --------------------


def _as_text(data):
    if isinstance(data, bytes):
        return data.decode("utf-8-sig")
    return data


def parse_sdmx_csv(data):
    """Parse an SDMX-CSV 1.0 payload into a list of row dicts.

    SDMX-CSV is plain comma-separated with a header row whose columns are the
    dataflow ref, each dimension id, then TIME_PERIOD, OBS_VALUE and attributes.
    """
    text = _as_text(data)
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _localized_name(node):
    """Best Italian label from an SDMX-JSON item (name/names by language)."""
    names = node.get("names")
    if isinstance(names, dict):
        return names.get("it") or names.get("en") or next(iter(names.values()), "")
    return node.get("name", "")


def _structure_section(payload, *keys):
    """Return the first present section, tolerating SDMX-JSON 1.0 vs 2.0 shapes."""
    root = payload.get("data", payload)
    for key in keys:
        if key in root and root[key]:
            return root[key]
        structures = root.get("structures")
        if isinstance(structures, dict) and structures.get(key):
            return structures[key]
    return []


def parse_dataflows(data):
    payload = json.loads(_as_text(data))
    dataflows = _structure_section(payload, "dataflows")
    result = []
    for flow in dataflows:
        structure = flow.get("structure", "")
        result.append({
            "id": flow.get("id", ""),
            "agency": flow.get("agencyID", AGENCY),
            "version": flow.get("version", ""),
            "name": _localized_name(flow),
            "dsd": structure,
        })
    return result


def parse_datastructure(data):
    payload = json.loads(_as_text(data))
    structures = _structure_section(payload, "dataStructures", "datastructures")
    if not structures:
        return {}
    dsd = structures[0]
    components = dsd.get("dataStructureComponents", {})
    dim_list = (components.get("dimensionList") or {}).get("dimensions", [])
    dimensions = []
    for dim in dim_list:
        enumeration = (dim.get("localRepresentation") or {}).get("enumeration", "")
        dimensions.append({
            "id": dim.get("id", ""),
            "position": dim.get("position"),
            "codelist": enumeration,
        })
    dimensions.sort(key=lambda d: (d["position"] is None, d["position"]))
    time_dims = (components.get("dimensionList") or {}).get("timeDimensions", [])
    return {
        "id": dsd.get("id", ""),
        "dimensions": dimensions,
        "time_dimension": time_dims[0].get("id") if time_dims else "TIME_PERIOD",
    }


def parse_codelist(data):
    payload = json.loads(_as_text(data))
    codelists = _structure_section(payload, "codelists")
    if not codelists:
        return {"id": "", "codes": {}}
    codelist = codelists[0]
    codes = {}
    for code in codelist.get("codes", []):
        codes[code.get("id", "")] = {
            "id": code.get("id", ""),
            "name": _localized_name(code),
            "parent": code.get("parent"),
        }
    return {"id": codelist.get("id", ""), "codes": codes}
