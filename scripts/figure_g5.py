"""Sweep G5 dei testi pubblici delle figure SVG e delle schede rese."""

from __future__ import annotations

import argparse
import re
from html import unescape
from pathlib import Path

from app.figure_contract import missing_fields, visible_svg_fields


def _plain(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", html)).strip()


def page_findings(html: str) -> list[tuple[str, list[str]]]:
    findings = []
    for index, figure in enumerate(re.findall(r"<figure\b.*?</figure>", html, re.S), 1):
        if 'class="module' not in figure and 'class="lead-figure' not in figure:
            continue
        caption = re.search(r"<figcaption\b.*?</figcaption>", figure, re.S)
        if not caption:
            findings.append((str(index), ["titolo", "misura", "popolazione", "territorio", "periodo"]))
            continue
        head = caption.group()
        title = re.search(r'<(?:h3|span)\b[^>]*class="(?:h-sub|lead-figure__title)"[^>]*>(.*?)</(?:h3|span)>', head, re.S)
        subtitle = re.search(r'<p class="subline"[^>]*>(.*?)</p>', head, re.S)
        source = re.search(r'<p class="source"[^>]*>(.*?)</p>', figure, re.S)
        axis = re.findall(r'<text[^>]*>\s*(Valore)\s*</text>', figure, re.I)
        fields = missing_fields(title=_plain(title.group(1)) if title else "",
                                subtitle=_plain(subtitle.group(1)) if subtitle else "",
                                axis_labels=tuple(axis) or ((_plain(subtitle.group(1)),) if subtitle else ()),
                                source=_plain(source.group(1)) if source else "")
        if fields:
            findings.append((str(index), fields))
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", default="content/figures")
    parser.add_argument("--pages", action="store_true", help="render tutte le schede del catalogo pubblico")
    args = parser.parse_args(argv)
    count = 0
    for path in sorted(Path(args.figures).rglob("*.svg")):
        missing = missing_fields(**visible_svg_fields(path.read_text(encoding="utf-8")))
        if missing:
            print(f"{path}: {', '.join(missing)}")
            count += 1
    if args.pages:
        from app import app, indicator_universe

        client = app.test_client()
        paths = []
        for record in indicator_universe.projection():
            path = record["meta"]["canonical_path"]
            paths.append(path)
            if record["default_level"] != "provincia" and any(
                    level["key"] == "provincia" for level in record["levels"]):
                paths.append(path + "/province")
        for path in dict.fromkeys(paths):
            response = client.get(path, follow_redirects=True)
            if response.status_code != 200:
                print(f"{path}: HTTP {response.status_code}")
                count += 1
                continue
            for figure, missing in page_findings(response.get_data(as_text=True)):
                print(f"{path}#figure-{figure}: {', '.join(missing)}")
                count += 1
    print(f"G5: {count} figure con rilievi")
    return bool(count)


if __name__ == "__main__":
    raise SystemExit(main())
