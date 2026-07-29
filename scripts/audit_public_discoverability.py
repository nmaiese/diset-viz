#!/usr/bin/env python3
"""Read-only audit of the public crawl and server-rendering contract."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "DivarioItalia-Discoverability-Audit/1.0 (+https://divarioitalia.it/llms.txt)"


def load_contract(path: Path = ROOT / "app" / "views.py") -> dict:
    """Read the route owner's literal without importing Flask or loading data."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PUBLIC_DISCOVERABILITY_EXPECTATIONS"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"PUBLIC_DISCOVERABILITY_EXPECTATIONS missing from {path}")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _SeoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = None
        self.robots = None

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href")
        if tag.lower() == "meta" and values.get("name", "").lower() == "robots":
            self.robots = values.get("content")


def _request(url: str, timeout: float, accept: str = "*/*") -> tuple[int, dict[str, str], bytes]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        response = build_opener(_NoRedirect).open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    body = response.read()
    headers = {key.lower(): value for key, value in response.headers.items()}
    # items() collapses repeated headers to the last value. A CDN that appends a
    # second, restrictive X-Robots-Tag next to the app's own must not disappear
    # here, or the audit would report PASS while crawlers honour the noindex.
    headers["x-robots-tag-all"] = list(response.headers.get_all("X-Robots-Tag") or [])
    headers["link-all"] = list(response.headers.get_all("Link") or [])
    return response.status, headers, body


def fetch(url: str, timeout: float, max_redirects: int = 5, accept: str = "*/*") -> dict:
    redirects = []
    current = url
    for _ in range(max_redirects + 1):
        status, headers, body = _request(current, timeout, accept=accept)
        location = headers.get("location")
        if status not in (301, 302, 303, 307, 308) or not location:
            break
        target = urljoin(current, location)
        redirects.append({"status": status, "from": current, "to": target})
        current = target
    else:
        raise RuntimeError(f"too many redirects from {url}")
    return {"url": url, "final_url": current, "status": status, "headers": headers, "body": body, "redirects": redirects}


def parse_robots(body: str) -> list[dict]:
    groups = []
    agents = []
    rules = []
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if rules:
                groups.append({"agents": agents, "rules": rules})
                agents, rules = [], []
            agents.append(value)
        elif agents:
            rules.append((field, value))
    if agents:
        groups.append({"agents": agents, "rules": rules})
    return groups


def audit_robots(text: str, contract: dict) -> list[str]:
    failures = []
    groups = parse_robots(text)
    # Ogni agente puo' comparire in piu' gruppi, quindi si tiene la **lista** dei
    # suoi gruppi, non l'ultimo che vince. Collassare in un dizionario nascondeva
    # un gruppo restrittivo iniettato da un CDN (es. `OAI-SearchBot: Disallow: /`)
    # dietro il gruppo permissivo dell'app che lo segue: l'audit passava mentre un
    # crawler sotto contratto aveva regole contraddittorie. Un agente auditato con
    # piu' di un gruppo e' esso stesso un fallimento (possibile iniezione).
    by_agent: dict = {}
    for group in groups:
        for agent in group["agents"]:
            by_agent.setdefault(agent, []).append(group["rules"])
    shared = [("allow", "/")] + [("disallow", path) for path in contract["shared_disallow"]]
    if sum("*" in group["agents"] for group in groups) != 1:
        failures.append("robots must contain exactly one default User-agent group (possible CDN injection)")

    def _one_group(agent):
        rule_sets = by_agent.get(agent, [])
        if len(rule_sets) > 1:
            # Il gruppo `*` doppio lo segnala gia' il controllo esplicito sopra,
            # con il suo messaggio: qui non si raddoppia.
            if agent != "*":
                failures.append(
                    f"robots must contain exactly one group for {agent} (possible CDN injection), got {len(rule_sets)}"
                )
            return None
        return rule_sets[0] if rule_sets else []

    for agent in ("*", *contract["answer_bots"]):
        rules = _one_group(agent)
        if rules is None:
            continue
        # Exact match, not membership: an extra rule such as ``Disallow: /blog``
        # keeps every required rule present yet blocks an audited public page.
        crawl_rules = [rule for rule in rules if rule[0] in ("allow", "disallow")]
        if crawl_rules != shared:
            failures.append(
                f"robots effective crawl rules for {agent} must be exactly {shared}, got {crawl_rules}"
            )
    for agent in contract["training_bots"]:
        rules = _one_group(agent)
        if rules is None:
            continue
        crawl_rules = [rule for rule in rules if rule[0] in ("allow", "disallow")]
        if crawl_rules != [("disallow", "/")]:
            failures.append(f"robots effective rules for {agent} must be exactly Disallow: /")
    if text.count("# As a condition of accessing this website") != 1:
        failures.append("robots content-signals preamble must occur exactly once (possible CDN injection)")
    return failures


def inspect_result(raw: dict, expected: dict, contract: dict) -> dict:
    body = raw.pop("body")
    text = body.decode("utf-8", errors="replace")
    content_type = raw["headers"].get("content-type", "")
    parser = _SeoParser()
    if "text/html" in content_type:
        parser.feed(text)
    result = {
        "url": raw["url"], "status": raw["status"], "redirects": raw["redirects"],
        "final_url": raw["final_url"], "content_type": content_type,
        "x_robots_tag": raw["headers"].get("x-robots-tag"),
        "canonical": parser.canonical, "robots_meta": parser.robots,
        "response_bytes": len(body), "server_rendered": expected["marker"] in text,
        "failures": [],
    }
    failures = result["failures"]
    canonical = contract["site_url"] + expected["path"]
    if raw["status"] != 200:
        failures.append(f"expected status 200, got {raw['status']}")
    if raw["redirects"]:
        failures.append("canonical URL unexpectedly redirects")
    if expected["content_type"] not in content_type.lower():
        failures.append(f"expected content type {expected['content_type']}, got {content_type or '<missing>'}")
    x_robots_all = raw["headers"].get("x-robots-tag-all")
    if x_robots_all is None:
        x_robots_all = [result["x_robots_tag"]] if result["x_robots_tag"] is not None else []
    expected_x_robots = expected.get("x_robots", contract["index_header"])
    if x_robots_all != [expected_x_robots]:
        failures.append(f"unexpected X-Robots-Tag header(s): {x_robots_all!r}")
    if not result["server_rendered"]:
        failures.append(f"server-rendered marker missing: {expected['marker']!r}")
    if expected["kind"] == "html":
        if parser.canonical != canonical:
            failures.append(f"expected canonical {canonical!r}, got {parser.canonical!r}")
        if parser.robots != contract["index_header"]:
            failures.append(f"unexpected robots meta: {parser.robots!r}")
    elif parser.canonical or parser.robots:
        failures.append("non-HTML document unexpectedly exposes HTML SEO metadata")
    if expected["kind"] == "robots":
        failures.extend(audit_robots(text, contract["robots"]))
    if expected["path"] == "/":
        link_headers = raw["headers"].get("link-all", [])
        for relation in contract["link_relations"]:
            if not any(f'rel="{relation}"' in value for value in link_headers):
                failures.append(f"homepage Link header missing relation {relation!r}")
    return result


def inspect_markdown(raw: dict, expected: dict, contract: dict) -> dict:
    body = raw.pop("body")
    text = body.decode("utf-8", errors="replace")
    content_type = raw["headers"].get("content-type", "")
    canonical = contract["site_url"] + expected["path"]
    result = {
        "url": raw["url"] + "#markdown",
        "status": raw["status"],
        "redirects": raw["redirects"],
        "final_url": raw["final_url"],
        "content_type": content_type,
        "x_robots_tag": raw["headers"].get("x-robots-tag"),
        "response_bytes": len(body),
        "server_rendered": expected["markdown_marker"] in text,
        "failures": [],
    }
    failures = result["failures"]
    if raw["status"] != 200:
        failures.append(f"expected status 200, got {raw['status']}")
    if raw["redirects"]:
        failures.append("canonical Markdown URL unexpectedly redirects")
    if "text/markdown" not in content_type.lower():
        failures.append(f"expected content type text/markdown, got {content_type or '<missing>'}")
    if expected["markdown_marker"] not in text:
        failures.append(f"Markdown marker missing: {expected['markdown_marker']!r}")
    if "accept" not in raw["headers"].get("vary", "").lower():
        failures.append("Markdown response must vary on Accept")
    if raw["headers"].get("content-location") != canonical:
        failures.append(f"expected Content-Location {canonical!r}")
    expected_x_robots = expected.get("x_robots", contract["index_header"])
    x_robots_all = raw["headers"].get("x-robots-tag-all", [])
    if x_robots_all != [expected_x_robots]:
        failures.append(f"unexpected X-Robots-Tag header(s): {x_robots_all!r}")
    return result


def run(timeout: float = 20.0) -> dict:
    contract = load_contract()
    results = []
    for expected in contract["pages"]:
        url = contract["site_url"] + expected["path"]
        try:
            results.append(inspect_result(fetch(url, timeout), expected, contract))
            if expected.get("markdown_marker"):
                results.append(inspect_markdown(
                    fetch(url, timeout, accept="text/markdown"), expected, contract,
                ))
        except (OSError, RuntimeError, URLError) as error:
            results.append({"url": url, "failures": [f"request failed: {error}"]})

    www_url = "https://www." + urlparse(contract["site_url"]).netloc + "/"
    try:
        www = fetch(www_url, timeout)
        failures = []
        expected_target = contract["site_url"] + "/"
        first = www["redirects"][0] if www["redirects"] else None
        if not first or first["status"] != 301 or first["to"] != expected_target:
            failures.append(f"www must issue one 301 to {expected_target}")
        if www["status"] != 200 or www["final_url"] != expected_target:
            failures.append("www redirect chain must finish on the healthy apex homepage")
        html = www["body"].decode("utf-8", errors="replace")
        seo = _SeoParser()
        seo.feed(html)
        home_marker = next(page["marker"] for page in contract["pages"] if page["path"] == "/")
        results.append({"url": www_url, "status": www["status"], "redirects": www["redirects"], "final_url": www["final_url"], "content_type": www["headers"].get("content-type", ""), "x_robots_tag": www["headers"].get("x-robots-tag"), "canonical": seo.canonical, "robots_meta": seo.robots, "response_bytes": len(www["body"]), "server_rendered": home_marker in html, "failures": failures})
    except (OSError, RuntimeError, URLError) as error:
        results.append({"url": www_url, "failures": [f"request failed: {error}"]})
    return {"verdict": "PASS" if all(not item["failures"] for item in results) else "FAIL", "results": results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=20.0, help="seconds per HTTP request")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON document")
    args = parser.parse_args(argv)
    report = run(args.timeout)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in report["results"]:
            state = "PASS" if not item["failures"] else "FAIL"
            print(f"{state:4} {item['url']} status={item.get('status', '-')} bytes={item.get('response_bytes', '-')} redirects={len(item.get('redirects', []))}")
            for failure in item["failures"]:
                print(f"     - {failure}")
        print(f"VERDICT: {report['verdict']}")
    return report["verdict"] != "PASS"


if __name__ == "__main__":
    sys.exit(main())
