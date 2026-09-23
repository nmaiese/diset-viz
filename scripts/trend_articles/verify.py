"""Fase 8: le guardie che fermano un pezzo prima della PR.

Ogni guardia e' una smentita ricalcolabile, non un giudizio di stile. Un
**ERRORE** ferma il pezzo, un **AVVISO** va letto da una persona.

1. Frontmatter: titolo, descrizione, data, copertina, alt, il trend d'origine
   (`trend:` con topic, detected, signals con fonte, URL e data), il blocco
   `dataset:` con metodo e download, l'attribuzione della foto.
2. Foto: la scheda `<slug>.photo.json` esiste, la licenza e' fra quelle
   ammesse, e `cover_credit` del pezzo dice le stesse cose della scheda.
3. Tipografia: niente `—`, `–`, `;`, `…` (content/STYLE.md).
4. Cifre: ogni numero del testo sta nel dossier del pezzo (con la stessa
   scrittura, virgola decimale e precisione), oppure fra le
   `external_figures` del frontmatter con la loro fonte. Anni e piccoli
   conteggi passano come avvisi.
5. "Media nazionale" e "media italiana" sono vietate sulle medie semplici dei
   territori, quando non le dichiara una fonte esterna.
6. Link interni: ogni `/indicatore/`, `/tema/`, `/blog/`, `/regione/`,
   `/provincia/` risponde 200 dall'app, senza redirect.
7. Link esterni nel testo: rispondono, e stanno anche nella sezione delle fonti.
8. Figure: ogni `<!-- figura: nome -->` ha il suo SVG.
9. Lunghezza: oltre mille parole di prosa (tabelle e fonti escluse) e' un
   avviso (REVIEW.md).

    bin/py -m scripts.trend_articles.verify content/posts/2026-09-23-<slug>.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import frontmatter
import requests

from scripts.trend_articles import common
from scripts.trend_articles.photo import ALLOWED_LICENSES

FORBIDDEN = {"—": "em-dash", "–": "en-dash", ";": "punto e virgola", "…": "ellissi"}
NUMBER = re.compile(r"(?<![\w/.-])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\w/])")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
INTERNAL = ("/indicatore/", "/tema/", "/blog/", "/regione/", "/provincia/", "/qualita-della-vita")
# I denominatori delle unita' ("ogni 100.000 anziani") non sono cifre da verificare.
UNIT_DENOMINATORS = {"100", "1.000", "10.000", "100.000", "1.000.000"}


def _clean_body(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = LINK.sub(lambda m: m.group(1), text)  # il testo del link resta, l'URL no
    return re.sub(r"\{:[^}]*\}", " ", text)


def _check_frontmatter(m: dict, errors: list, warnings: list) -> None:
    for field in ("title", "description", "date", "cover", "cover_alt", "cover_credit", "trend", "dataset"):
        if not m.get(field):
            errors.append(f"frontmatter: manca `{field}`")
    trend = m.get("trend") or {}
    for field in ("topic", "detected", "signals"):
        if not trend.get(field):
            errors.append(f"trend: manca `{field}` (perche' questo pezzo, oggi?)")
    for i, s in enumerate(trend.get("signals") or []):
        for field in ("type", "text", "source", "url", "date"):
            if not s.get(field):
                errors.append(f"trend.signals[{i}]: manca `{field}`")
    ds = m.get("dataset") or {}
    for field in ("name", "description", "method", "download", "source_url"):
        if not ds.get(field):
            errors.append(f"dataset: manca `{field}`")
    if ds.get("download") and not (common.ROOT / "app" / ds["download"].lstrip("/")).is_file():
        errors.append(f"dataset.download: {ds['download']} non esiste")
    if len(m.get("description", "")) > 160:
        warnings.append(f"description di {len(m['description'])} caratteri (oltre 160 Google la taglia)")


def _check_photo(m: dict, slug: str, errors: list) -> None:
    record_path = common.BLOG_IMG_DIR / f"{slug}.photo.json"
    if not record_path.is_file():
        errors.append(f"foto: manca la scheda {record_path.relative_to(common.ROOT)} (usa photo.py choose)")
        return
    record = common.read_json(record_path)
    if not ALLOWED_LICENSES.match(record.get("license", "")):
        errors.append(f"foto: licenza non ammessa {record.get('license')!r}")
    credit = m.get("cover_credit") or {}
    for field in ("author", "license", "license_url", "source_url"):
        if str(credit.get(field, "")).strip() != str(record["cover_credit"].get(field, "")).strip():
            errors.append(f"cover_credit.{field} diverso dalla scheda della foto")
    if m.get("cover") != record.get("site_file"):
        errors.append(f"cover {m.get('cover')} diversa dalla foto registrata {record.get('site_file')}")


def _check_figures(m: dict, body: str, slug: str, errors: list, warnings: list) -> None:
    dossier_path = common.ARTICLES_DIR / slug / "dossier.json"
    if not dossier_path.is_file():
        errors.append(f"cifre: manca il dossier {dossier_path.relative_to(common.ROOT)}")
        return
    dossier = common.read_json(dossier_path)
    allowed = {f["figure"] for entry in dossier["indicators"] for f in entry["figures"]}
    allowed |= {f.replace(".", "") for f in list(allowed)}
    # le cifre che fanno parte della definizione (15-34 anni, per 10.000)
    for entry in dossier["indicators"]:
        meta_text = " ".join(str(entry["meta"].get(k, "")) for k in ("name", "unit", "definition"))
        allowed |= set(re.findall(r"\d+(?:\.\d{3})*(?:,\d+)?", meta_text))
    external = m.get("external_figures") or []
    for e in external:
        if not e.get("source") or not e.get("url"):
            errors.append(f"external_figures: {e.get('value')} senza fonte o url")
    allowed |= {str(e.get("value")) for e in external}
    allowed |= UNIT_DENOMINATORS
    text = _clean_body(body) + " " + m.get("description", "") + " " + m.get("title", "")
    for n in sorted(set(NUMBER.findall(text))):
        if n in allowed or re.fullmatch(r"(19|20)\d\d", n):
            continue
        if re.fullmatch(r"\d{1,3}", n) and int(n) <= 110:
            warnings.append(f"cifre: {n} non e' nel dossier (un conteggio? controllalo)")
            continue
        errors.append(f"cifre: {n} non sta nel dossier ne' fra le external_figures")


def _check_links(body: str, errors: list, warnings: list) -> None:
    from app import app  # l'app si carica solo qui

    client = app.test_client()
    external = set()
    sources_section = body.split("## Fonti", 1)[1] if "## Fonti" in body else ""
    for _, url in LINK.findall(body):
        if url.startswith(INTERNAL) or url.startswith("/"):
            status = client.get(url.split("#")[0]).status_code
            if status != 200:
                errors.append(f"link interno {url} risponde {status}")
        elif url.startswith("http"):
            external.add(url)
    for url in sorted(external):
        if url not in sources_section:
            errors.append(f"fonte {url} citata nel testo ma assente dalla sezione '## Fonti'")
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 divarioitalia-verifica"}, allow_redirects=True)
        except requests.RequestException as error:
            warnings.append(f"fonte {url} non raggiunta: {error.__class__.__name__}")
            continue
        if r.status_code >= 400:
            errors.append(f"fonte {url} risponde {r.status_code}")


def verify(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    post = frontmatter.load(path)
    m, body = post.metadata, post.content
    slug = m.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)

    _check_frontmatter(m, errors, warnings)
    _check_photo(m, slug, errors)

    full_text = body + " " + " ".join(str(m.get(k, "")) for k in ("title", "description", "cover_alt", "seo_title"))
    for char, name in FORBIDDEN.items():
        n = full_text.count(char)
        if n:
            errors.append(f"tipografia: {n} volte {name} {char!r}")

    _check_figures(m, body, slug, errors, warnings)

    external_text = " ".join(str(e.get("what", "")) for e in (m.get("external_figures") or [])).lower()
    for phrase in ("media nazionale", "media italiana", "media dell'italia"):
        # "non e' la media nazionale" e' proprio la frase giusta: si guarda solo l'uso affermativo.
        uses = [hit.start() for hit in re.finditer(re.escape(phrase), body.lower())]
        if any("non " not in body.lower()[max(0, i - 20):i] for i in uses) and phrase not in external_text:
            errors.append(f"'{phrase}': il dossier ha solo medie semplici dei territori")

    _check_links(body, errors, warnings)

    for name in re.findall(r"<!--\s*figura:\s*([a-z0-9-]+)\s*-->", body):
        if not (common.FIGURES_DIR / slug / f"{name}.svg").is_file():
            errors.append(f"figura {name}: manca content/figures/{slug}/{name}.svg")

    # Si contano le parole della prosa: fuori le tabelle e l'elenco delle fonti.
    prose = body.split("## Fonti", 1)[0]
    words = len(re.findall(r"\w+", _clean_body(re.sub(r"^\|.*\|$", "", prose, flags=re.MULTILINE))))
    if words > 1000:
        warnings.append(f"lunghezza: {words} parole di prosa, tabelle e fonti escluse (REVIEW.md ne chiede al massimo mille)")
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("posts", nargs="+")
    args = parser.parse_args(argv)
    failed = 0
    for p in args.posts:
        errors, warnings = verify(Path(p))
        print(f"\n{p}: {len(errors)} errori, {len(warnings)} avvisi")
        for e in errors:
            print(f"  ERRORE  {e}")
        for w in warnings:
            print(f"  avviso  {w}")
        failed |= bool(errors)
    return failed


if __name__ == "__main__":
    sys.exit(main())
