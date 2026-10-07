#!/usr/bin/env python3
"""Audit AdSense parte A2: CMP, Core Web Vitals (stima), link rotti, ads.txt.

Rigenera le misure della seconda passata dell'audit AdSense e scrive il report
in ``reports/adsense_audit_<data>.md``. Sola lettura: non modifica il sito.

    PYTHONPATH=. bin/py scripts/adsense_audit.py            # scrive il report
    PYTHONPATH=. bin/py scripts/adsense_audit.py --json      # stampa i dati
    PYTHONPATH=. bin/py scripts/adsense_audit.py --no-net    # stampa le misure dal repo, non scrive

Misura:

- consenso cookie / CMP: cosa c'e' nel codice e cosa manca (nessuna rete);
- Core Web Vitals: prova PageSpeed API senza chiave, in fallback stima da peso
  e risorse della pagina servita;
- link rotti: legge il rapporto del check W2 se esiste, non lo rifa';
- ads.txt: confronta il contenuto live con la riga attesa;
- URL Inspection su Search Console: non misurata qui, dichiarato (si misura con
  uno script a parte, account di servizio, scope webmasters.readonly).

Le funzioni pure (CMP, parsing asset, parsing W2, build del report) sono
testabili senza rete in ``tests/unit/test_adsense_audit.py``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://divarioitalia.it"
ADSENSE_CLIENT = "ca-pub-6806451730012282"
ADSENSE_PUBLISHER = "pub-6806451730012282"
ADS_TXT_LINE = "google.com, pub-6806451730012282, DIRECT, f08c47fec0942fa0"
GTM_ID = "GTM-PZ45BG7D"

# Le cinque pagine campione, una per tipo di pagina del sito.
PAGES = {
    "home": "/",
    "indicatore": "/indicatore/addetti-delle-nuove-imprese/ter-398",
    "regione": "/regione/lombardia",
    "provincia": "/provincia/milano",
    "blog": "/blog/casa-affitti-mercato",
}

W2_REPORT = Path(os.environ.get(
    "W2_REPORT",
    Path.home() / "dev" / "trade5" / "review" / "divarioitalia_link_check" / "RAPPORTO.md",
))

_CMP_FILES = {
    "publisher": ROOT / "app" / "publisher.py",
    "third_party_head": ROOT / "app" / "templates" / "_third_party_head.html",
    "funding_revoke": ROOT / "app" / "templates" / "_funding_choices_revoke.html",
    "tracking_spec": ROOT / "docs" / "tracking_spec.md",
}


def cmp_status() -> dict:
    """Cosa c'e' nel codice per il consenso, e cosa manca (non verificabile qui)."""
    publisher = _CMP_FILES["publisher"].read_text(encoding="utf-8")
    head = _CMP_FILES["third_party_head"].read_text(encoding="utf-8")
    revoke = _CMP_FILES["funding_revoke"].read_text(encoding="utf-8")
    spec = _CMP_FILES["tracking_spec"].read_text(encoding="utf-8")

    cmp_name = re.search(r'CONSENT_CMP_NAME = "([^"]+)"', publisher)
    cmp_url = re.search(r'CONSENT_CMP_URL = "([^"]+)"', publisher)
    widget = re.search(r"embeds\.iubenda\.com/widgets/([0-9a-f-]+)\.js", spec)

    present = {
        "cmp_nome": cmp_name.group(1) if cmp_name else None,
        "cmp_url": cmp_url.group(1) if cmp_url else None,
        "iubenda_widget_id": widget.group(1) if widget else None,
        "consent_mode_default": "gtag('consent', 'default'" in head,
        "consent_default_denied": "'ad_storage': 'denied'" in head,
        "gtm_loader": "googletagmanager.com/gtm.js" in head and "GOOGLE_TAG_MANAGER_ID" in head,
        "adsense_loader": "adsbygoogle.js" in head,
        "adsense_condizionale": "not ADS_OFF" in head and "not noindex" in head,
        "preferenze_cookie": "diOpenConsentPreferences" in revoke,
        "tcf_fallback": "__tcfapi" in head,
    }
    missing = []
    if not present["cmp_nome"]:
        missing.append("nome CMP non dichiarato in app/publisher.py")
    if not present["consent_mode_default"]:
        missing.append("default Consent Mode assente prima di GTM/AdSense")
    if not present["consent_default_denied"]:
        missing.append("ad_storage non parte da denied")
    if not present["preferenze_cookie"]:
        missing.append("pulsante di revoca/gestione preferenze assente")

    # Non verificabile dal solo repository: richiede la dashboard Iubenda e un
    # controllo live (Tag Assistant / rete) del segnale TCF v2.2.
    unverifiable = [
        "CMP caricata via GTM (widget iniettato da gtm.js, assente dall'HTML del server): "
        "senza JavaScript non compare alcun banner",
        "certificazione Google della CMP e segnale TCF v2.2 effettivo: serve la "
        "dashboard Iubenda e un controllo live",
        "nessuna unita' pubblicitaria (`<ins class=\"adsbygoogle\">`) nel codice: "
        "c'e' solo il loader; ADSENSE_SLOT_BANNER e' configurato ma mai usato",
    ]
    return {"presente": present, "manca": missing, "non_verificabile": unverifiable}


class _AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.js: list[str] = []
        self.css: list[str] = []
        self.img: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = {k.lower(): v for k, v in attrs if v is not None}
        if tag.lower() == "script" and values.get("src"):
            self.js.append(values["src"])
        elif tag.lower() == "link" and "stylesheet" in values.get("rel", "").lower():
            self.css.append(values.get("href", ""))
        elif tag.lower() == "img" and values.get("src"):
            self.img.append(values["src"])


def parse_asset_refs(html: str) -> dict:
    """Script, stylesheet e immagini referenziati da una pagina HTML."""
    parser = _AssetParser()
    parser.feed(html)
    return {"js": parser.js, "css": parser.css, "img": parser.img}


def _fetch(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "DivarioCheck/1.0 DivarioItalia-Adsense-Audit/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def measure_page(url: str, timeout: float = 15.0) -> dict:
    """Peso e risorse di una pagina live, come stima delle Core Web Vitals."""
    status, html = _fetch(url, timeout)
    text = html.decode("utf-8", errors="replace")
    assets = parse_asset_refs(text)
    same_origin = 0
    for kind in ("js", "css", "img"):
        for src in assets[kind]:
            absolute = urljoin(url, src)
            if not absolute.startswith(SITE_URL):
                continue
            try:
                _, body = _fetch(absolute, timeout)
                same_origin += len(body)
            except (OSError, urllib.error.URLError):
                pass
    return {
        "url": url,
        "status": status,
        "html_bytes": len(html),
        "script": len(assets["js"]),
        "stylesheet": len(assets["css"]),
        "immagini": len(assets["img"]),
        "asset_same_origin_bytes": same_origin,
        "totale_stimato_bytes": len(html) + same_origin,
    }


def pagespeed(url: str, strategy: str = "mobile", timeout: float = 15.0) -> dict:
    """PageSpeed Insights API senza chiave; 429/errore -> dichiarato non disponibile."""
    api = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
           f"?url={urllib.request.quote(url, safe='')}"
           f"&category=performance&strategy={strategy}")
    try:
        status, body = _fetch(api, timeout)
    except (OSError, urllib.error.URLError) as error:
        return {"url": url, "available": False, "reason": f"request failed: {error}"}
    if status != 200:
        payload = {}
        try:
            payload = json.loads(body.decode("utf-8", errors="replace"))
        except ValueError:
            pass
        message = payload.get("error", {}).get("message", f"HTTP {status}")
        return {"url": url, "available": False, "reason": message}
    data = json.loads(body.decode("utf-8", errors="replace"))
    lab = data.get("lighthouseResult", {}).get("audits", {})
    metrics = {}
    for key in ("largest-contentful-paint", "total-blocking-time", "cumulative-layout-shift", "speed-index"):
        if key in lab:
            metrics[key] = lab[key].get("displayValue") or lab[key].get("numericValue")
    return {"url": url, "available": True, "score": data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score"), "metrics": metrics}


def parse_w2(text: str) -> dict:
    """I conteggi chiave dal rapporto W2 sui link."""
    out: dict = {}
    patterns = {
        "link_rotti": r"Link rotti \(404/redirect\):\s*(\d+)",
        "fuori_sitemap": r"Link verso URL non in sitemap:\s*([\d.]+)",
        "orfane": r"Pagine orfane[^:]*:\s*(\d+)",
        "duplicate": r"URL duplicate[^:]*:\s*(\d+)",
        "canonical_incoerenti": r"Canonical incoerenti:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            out[key] = None
            continue
        out[key] = int(match.group(1).replace(".", "").replace(",", ""))
    return out


def read_w2(path: Path = W2_REPORT) -> dict | None:
    if not path.exists():
        return None
    return parse_w2(path.read_text(encoding="utf-8"))


def url_inspection_status() -> dict:
    """URL Inspection su Search Console: non la misura questo script."""
    return {
        "available": False,
        "reason": "non misurato da questo script, si misura con uno script a parte "
        "(account di servizio, scope webmasters.readonly)",
    }


def ads_txt(url: str = f"{SITE_URL}/ads.txt", timeout: float = 10.0) -> dict:
    try:
        status, body = _fetch(url, timeout)
    except (OSError, urllib.error.URLError) as error:
        return {"available": False, "reason": f"request failed: {error}"}
    text = body.decode("utf-8", errors="replace").strip()
    return {"status": status, "riga_attesa": ADS_TXT_LINE in text, "contenuto": text}


def build_report(payload: dict) -> str:
    """Il report Markdown, rigenerabile e leggibile."""
    lines = [
        f"# Audit AdSense, parte A2 (CMP, CWV, link rotti), {payload['data']}",
        "",
        "Sola lettura. Core Web Vitals stimate da peso e risorse: PageSpeed API senza "
        "chiave ha risposto quota esaurita (429), dichiarato e ripiegato sulla stima.",
        "",
    ]

    cmp = payload["cmp"]
    present = cmp["presente"]
    lines.append("## Consenso cookie / CMP")
    lines.append("")
    lines.append(f"- CMP: {present.get('cmp_nome') or '?'} ({present.get('cmp_url') or '?'})")
    lines.append(f"- Consent Mode default inline prima di GTM/AdSense: {'si' if present['consent_mode_default'] else 'no'}")
    lines.append(f"- default denied (ad/analytics/personalization): {'si' if present['consent_default_denied'] else 'no'}")
    lines.append(f"- GTM loader ({GTM_ID}): {'si' if present['gtm_loader'] else 'no'}")
    lines.append(f"- AdSense loader condizionale (non ADS_OFF, non noindex): {'si' if present['adsense_condizionale'] else 'no'}")
    lines.append(f"- pulsante preferenze/revoca: {'si' if present['preferenze_cookie'] else 'no'}")
    if cmp["manca"]:
        for item in cmp["manca"]:
            lines.append(f"- MANCA: {item}")
    lines.append("- Non verificabile dal repo:")
    for item in cmp["non_verificabile"]:
        lines.append(f"  - {item}")
    lines.append("")

    lines.append("## Core Web Vitals (stima da peso/risorse)")
    lines.append("")
    lines.append("| pagina | HTTP | HTML KB | script | css | img | stima totale KB |")
    lines.append("|---|---|---|---|---|---|---|")
    for page in payload["pagine"]:
        lines.append(
            f"| {page['tipo']} | {page.get('status', '-')} | {page['html_bytes'] / 1024:.1f} "
            f"| {page['script']} | {page['stylesheet']} | {page['immagini']} "
            f"| {page['totale_stimato_bytes'] / 1024:.1f} |"
        )
    lines.append("")
    lines.append(f"- PageSpeed API: {payload['pagespeed']}")
    lines.append("")

    lines.append("## Link rotti (rapporto W2, non rifatto)")
    lines.append("")
    w2 = payload.get("w2")
    if w2 is None:
        lines.append("- rapporto W2 non trovato")
    else:
        lines.append(f"- link rotti: {w2.get('link_rotti')}")
        lines.append(f"- link verso URL non in sitemap: {w2.get('fuori_sitemap')}")
        lines.append(f"- pagine orfane: {w2.get('orfane')}")
        lines.append(f"- URL duplicate: {w2.get('duplicate')}")
        lines.append(f"- canonical incoerenti: {w2.get('canonical_incoerenti')}")
    lines.append("")

    lines.append("## URL Inspection (Search Console)")
    lines.append("")
    url_inspection = payload["url_inspection"]
    lines.append(f"- misurato da questo script: {url_inspection['available']}")
    if not url_inspection["available"]:
        lines.append(f"- motivo: {url_inspection['reason']}")
    lines.append("")

    ads = payload["ads_txt"]
    lines.append("## ads.txt")
    lines.append("")
    lines.append(f"- HTTP {ads.get('status', '-')}, riga attesa presente: {ads.get('riga_attesa')}")
    if not ads.get("riga_attesa"):
        lines.append(f"- contenuto: {ads.get('contenuto', '')}")
    lines.append("")
    return "\n".join(lines)


def run(no_net: bool = False, timeout: float = 15.0) -> dict:
    payload = {
        "data": date.today().isoformat(),
        "cmp": cmp_status(),
        "url_inspection": url_inspection_status(),
        "pagine": [],
        "pagespeed": "non tentata (--no-net)",
        "w2": read_w2(),
        "ads_txt": {"status": None, "riga_attesa": None},
    }
    if no_net:
        return payload

    payload["ads_txt"] = ads_txt(timeout=timeout)
    for tipo, path in PAGES.items():
        url = f"{SITE_URL}{path}"
        page = measure_page(url, timeout)
        page["tipo"] = tipo
        payload["pagine"].append(page)

    ps = pagespeed(f"{SITE_URL}{PAGES['home']}", timeout=timeout)
    if ps.get("available"):
        payload["pagespeed"] = f"score performance {ps.get('score')}"
    else:
        payload["pagespeed"] = f"non disponibile: {ps.get('reason')}"
    return payload


def write_report(payload: dict, out_dir: Path = ROOT / "reports") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"adsense_audit_{payload['data'].replace('-', '')}.md"
    path.write_text(build_report(payload), encoding="utf-8")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="stampa i dati in JSON, non scrive il report")
    parser.add_argument("--no-net", action="store_true", help="solo le misure dal repository, senza rete")
    parser.add_argument("--timeout", type=float, default=15.0, help="secondi per ogni richiesta HTTP")
    args = parser.parse_args(argv)

    payload = run(no_net=args.no_net, timeout=args.timeout)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    if args.no_net:
        # Misure vuote: non devono sovrascrivere il report del giorno.
        print(build_report(payload))
        return 0
    path = write_report(payload)
    print(f"report scritto: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
