"""Read-only discovery documents and Markdown page projections."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from flask import Response, request


AGENT_SKILL_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
SKILL_NAME = "query-divario-italia"
SKILL_FILE = (
    Path(__file__).resolve().parents[1]
    / "content"
    / "agent-skills"
    / SKILL_NAME
    / "SKILL.md"
)

_MARKDOWN_EXACT_PATHS = {
    "/",
    "/atlante",
    "/blog",
    "/catalogo-dati",
    "/metodologia",
}
_MARKDOWN_PREFIXES = ("/blog/", "/indicatore/", "/regione/", "/tema/")


def markdown_available(path):
    """Return whether a public route has a first-class Markdown variant."""
    return path in _MARKDOWN_EXACT_PATHS or path.startswith(_MARKDOWN_PREFIXES)


def prefers_markdown():
    """Honor only an explicit, acceptable ``text/markdown`` media range.

    Werkzeug treats ``*/*`` as matching every representation. Requiring the
    literal media type prevents ordinary browsers and curl from receiving
    Markdown merely because it is one of the formats the server can produce.
    """
    raw = request.headers.get("Accept", "")
    if not re.search(r"(?:^|,)\s*text/markdown\s*(?:;|,|$)", raw, re.I):
        return False
    return request.accept_mimetypes["text/markdown"] > 0


def markdown_response(body, canonical):
    response = Response(body.rstrip() + "\n", content_type="text/markdown; charset=utf-8")
    response.headers["Content-Location"] = canonical
    response.vary.add("Accept")
    return response


def discovery_link_values():
    """Registered RFC 8288 relations advertised by public responses."""
    return (
        '</.well-known/api-catalog>; rel="api-catalog"',
        '</llms.txt>; rel="service-doc"; type="text/plain"',
        '</.well-known/agent-skills/index.json>; rel="service-desc"; type="application/json"',
    )


def api_catalog_document(site_url):
    return {
        "linkset": [
            {
                "anchor": f"{site_url}/api/catalog",
                "service-desc": [
                    {
                        "href": f"{site_url}/openapi.json",
                        "type": "application/vnd.oai.openapi+json;version=3.1",
                    }
                ],
                "service-doc": [
                    {"href": f"{site_url}/catalogo-dati", "type": "text/html"},
                    {"href": f"{site_url}/llms.txt", "type": "text/plain"},
                ],
            }
        ]
    }


def api_catalog_content_type():
    return "application/linkset+json"


def openapi_document(site_url):
    """OpenAPI contract for the stable, read-only public data surface."""
    indicator_parameter = {
        "name": "indicator_id",
        "in": "path",
        "required": True,
        "description": "ID del catalogo, per esempio 901, bes:01SAL001 o eur:rd_e_gerdreg.",
        "schema": {"type": "string"},
    }
    year_parameter = {
        "name": "year",
        "in": "path",
        "required": True,
        "schema": {"type": "integer"},
    }
    json_responses = {
        "200": {
            "description": "Dati con metadati, fonte e unità della serie.",
            "content": {"application/json": {"schema": {"type": "object"}}},
        },
        "404": {"description": "Indicatore o anno non disponibile."},
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Divario Italia, API dati pubblici",
            "version": "1.0.0",
            "description": (
                "Interfaccia read-only per cercare indicatori territoriali e scaricare "
                "serie con anno, territorio, unità e fonte. Le licenze sono dichiarate "
                "nei metadati della singola serie."
            ),
        },
        "servers": [{"url": site_url}],
        "externalDocs": {
            "description": "Catalogo dati e metodologia",
            "url": f"{site_url}/catalogo-dati",
        },
        "paths": {
            "/api/catalog": {
                "get": {
                    "summary": "Elenca gli indicatori disponibili nell'atlante",
                    "operationId": "listIndicators",
                    "responses": json_responses,
                }
            },
            "/api/search": {
                "get": {
                    "summary": "Cerca indicatori per nome, tema o descrizione",
                    "operationId": "searchIndicators",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string", "minLength": 2},
                        }
                    ],
                    "responses": json_responses,
                }
            },
            "/api/indicator/{indicator_id}": {
                "get": {
                    "summary": "Restituisce metadati e serie completa di un indicatore",
                    "operationId": "getIndicator",
                    "parameters": [indicator_parameter],
                    "responses": json_responses,
                }
            },
            "/api/indicator/{indicator_id}/year/{year}": {
                "get": {
                    "summary": "Restituisce i valori territoriali di un indicatore in un anno",
                    "operationId": "getIndicatorYear",
                    "parameters": [indicator_parameter, year_parameter],
                    "responses": json_responses,
                }
            },
            "/download/indicator/{indicator_id}.json": {
                "get": {
                    "summary": "Scarica metadati e serie in JSON",
                    "operationId": "downloadIndicatorJson",
                    "parameters": [indicator_parameter],
                    "responses": json_responses,
                }
            },
            "/download/indicator/{indicator_id}.csv": {
                "get": {
                    "summary": "Scarica la serie in CSV lungo",
                    "operationId": "downloadIndicatorCsv",
                    "parameters": [indicator_parameter],
                    "responses": {
                        "200": {
                            "description": "Serie con territorio, anno, valore, unità e fonte.",
                            "content": {"text/csv": {"schema": {"type": "string"}}},
                        },
                        "404": {"description": "Indicatore non disponibile."},
                    },
                }
            },
        },
    }


def skill_text():
    return SKILL_FILE.read_text(encoding="utf-8")


def skill_index_document(site_url):
    artifact = skill_text().encode("utf-8")
    return {
        "$schema": AGENT_SKILL_SCHEMA,
        "skills": [
            {
                "name": SKILL_NAME,
                "type": "skill-md",
                "description": (
                    "Cerca, confronta e interpreta gli indicatori territoriali di "
                    "Divario Italia con anno, unità, fonte e limiti corretti."
                ),
                "url": f"{site_url}/.well-known/agent-skills/{SKILL_NAME}/SKILL.md",
                "digest": f"sha256:{hashlib.sha256(artifact).hexdigest()}",
            }
        ],
    }


def _number(value, decimals=2):
    if value is None:
        return "n.d."
    try:
        formatted = f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
    return formatted.replace(",", "§").replace(".", ",").replace("§", ".")


def _clean(value):
    return " ".join(str(value or "").split())


def _absolute(site_url, path):
    return path if str(path).startswith(("http://", "https://")) else f"{site_url}{path}"


def home_markdown(summary, featured, posts, site_url):
    lines = [
        "# Divario Italia",
        "",
        "> Atlante degli indicatori territoriali italiani, con fonti verificate, serie storiche e download aperti.",
        "",
        f"Il catalogo raccoglie {summary['total']} indicatori di {summary['institutions_label']}, "
        f"con anni dal {summary['year_min']} al {summary['year_max']}.",
        "",
        "## Esplora",
        "",
        f"- [Atlante]({site_url}/atlante)",
        f"- [Regioni]({site_url}/regioni)",
        f"- [Temi]({site_url}/temi)",
        f"- [Confronto tra regioni]({site_url}/confronto)",
        f"- [Catalogo dati]({site_url}/catalogo-dati)",
        f"- [Metodologia e fonti]({site_url}/metodologia)",
        "",
        "## Indicatori in evidenza",
        "",
    ]
    for item in featured:
        lines.append(
            f"- [{item['name']}]({_absolute(site_url, item['path'])}): "
            f"{_clean(item.get('summary'))} Ultimo anno {item['year']}."
        )
    lines += ["", "## Analisi recenti", ""]
    for post in posts:
        lines.append(f"- [{post['title']}]({post['url']}): {_clean(post['description'])}")
    return "\n".join(lines)


def atlas_markdown(featured, site_url):
    lines = [
        "# Atlante degli indicatori territoriali italiani",
        "",
        "Cerca un indicatore, confronta le regioni e apri la scheda canonica per leggere definizione, fonte, andamento e download.",
        "",
        f"- [Catalogo dati]({site_url}/catalogo-dati)",
        f"- [Metodologia]({site_url}/metodologia)",
        f"- [Confronta regioni]({site_url}/confronto)",
        "",
        "## Indicatori territoriali in evidenza",
        "",
    ]
    for item in featured:
        lines.append(
            f"- [{item['name']}]({_absolute(site_url, item['path'])}): "
            f"{_clean(item.get('summary'))} Ultimo anno {item['year']}, tema {item['theme']}."
        )
    return "\n".join(lines)


def data_catalog_markdown(datasets, description, site_url):
    lines = [
        "# Catalogo dati di Divario Italia",
        "",
        description,
        "",
        f"Metodologia: {site_url}/metodologia",
        "",
        f"## Dataset disponibili ({len(datasets)})",
        "",
    ]
    for item in datasets:
        source = f" Fonte: {item['source']}." if item.get("source") else ""
        lines.append(f"- [{item['name']}]({item['url']}).{source}")
    return "\n".join(lines)


def blog_index_markdown(posts, site_url):
    lines = [
        "# Storie dai dati",
        "",
        "Analisi brevi e basate sui dati sui divari territoriali italiani.",
        "",
    ]
    for post in posts:
        lines += [
            f"## [{post['title']}]({post['url']})",
            "",
            f"{post['date'].isoformat()} · {post['author']} · {post['read_time']} min",
            "",
            _clean(post["description"]),
            "",
        ]
    lines.append(f"Metodologia e fonti: {site_url}/metodologia")
    return "\n".join(lines)


def blog_post_markdown(post, site_url):
    lines = [
        f"# {post['title']}",
        "",
        f"Data: {post['date'].isoformat()}",
        f"Ultima modifica: {post['date_modified'].isoformat()}",
        f"Autore: {post['author']}",
        f"URL canonica: {post['url']}",
        "",
        _clean(post["description"]),
        "",
        post["body_markdown"].strip(),
    ]
    if post.get("indicator_path"):
        lines += [
            "",
            "## Dati collegati",
            "",
            f"- [Apri la scheda indicatore]({_absolute(site_url, post['indicator_path'])})",
        ]
    return "\n".join(lines)


def methodology_markdown(site_url, license_label, license_url):
    return "\n".join(
        [
            "# Metodologia e fonti",
            "",
            "Divario Italia ripubblica e organizza indicatori territoriali provenienti da Istat, Eurostat e dalle altre istituzioni dichiarate nella singola scheda.",
            "",
            "## Come leggere i valori",
            "",
            "- Ogni scheda dichiara popolazione di riferimento, unità, periodo e copertura.",
            "- Le variazioni annuali di una percentuale sono espresse in punti percentuali.",
            "- La media delle regioni è una media semplice non ponderata e non è la media nazionale italiana.",
            "- Una differenza osservata tra territori non dimostra da sola un rapporto di causa.",
            "- Un valore alto non è sempre migliore. La direzione è dichiarata per ogni indicatore.",
            "",
            "## Fonti e riuso",
            "",
            "La fonte primaria e il relativo collegamento sono riportati in ogni scheda indicatore.",
            f"Licenza di riferimento per i dati Istat: [{license_label}]({license_url}). Le altre famiglie mantengono la licenza dichiarata dalla propria fonte.",
            "",
            f"- [Catalogo dati]({site_url}/catalogo-dati)",
            f"- [Indice per modelli linguistici]({site_url}/llms.txt)",
        ]
    )


def indicator_markdown(meta, level, article, site_url):
    canonical = f"{site_url}{meta['canonical_path']}"
    unit = meta.get("value_unit") or meta.get("unit") or "unità non specificata"
    explain = meta.get("explain") or {}
    lines = [
        f"# {meta['name']}",
        "",
        article.get("lead") or explain.get("plain") or meta["name"],
        "",
        f"URL canonica: {canonical}",
        "",
        "## Scheda",
        "",
        f"- Tema: [{meta['theme']}]({_absolute(site_url, meta['theme_path'])})",
        f"- Livello territoriale: {level['label']}",
        f"- Unità di misura: {unit}",
        f"- Copertura: dal {level['year_min']} al {level['year_max']}",
        f"- Territori nell'ultimo anno: {len(level['observations'])}",
        f"- Fonte: [{meta.get('source_label') or meta.get('source')}]({meta.get('source_url')})",
    ]
    if explain.get("plain"):
        lines += ["", "## Che cosa misura", "", explain["plain"]]
    if explain.get("example"):
        lines += ["", "## Esempio di lettura", "", explain["example"]]
    if explain.get("reading"):
        lines += ["", "## Come si interpreta", "", explain["reading"]]
    if explain.get("caveat"):
        lines += ["", "## Limiti", "", explain["caveat"]]

    for section in article.get("sections") or []:
        if section.get("body"):
            lines += ["", f"## {section['heading']}", "", section["body"].strip()]

    change = level.get("annual_change")
    if change:
        sign = "+" if change["average_delta"] > 0 else ""
        lines += [
            "",
            "## Ultimo cambiamento disponibile",
            "",
            f"Dal {change['previous_year']} al {change['year']} la media semplice dei "
            f"{change['common_count']} territori presenti in entrambi gli anni è cambiata di "
            f"{sign}{_number(change['average_delta'])} {meta.get('change_unit') or unit}.",
        ]
        if level.get("annual_note"):
            lines.append(level["annual_note"])

    lines += [
        "",
        f"## Valori per {level['plural']}, {level['year_max']}",
        "",
        "La tabella è ordinata per valore. Non rappresenta una graduatoria di merito quando l'indicatore non ha una direzione univoca.",
        "",
        f"| Posizione | {level['singular'].capitalize()} | Valore |",
        "| ---: | --- | ---: |",
    ]
    for position, row in enumerate(level["observations"], 1):
        lines.append(f"| {position} | {row['name']} | {_number(row['value'])} {unit} |")

    lines += ["", "## Fonti e download", ""]
    if meta.get("source_data_url"):
        lines.append(f"- [Archivio o tavola originale]({meta['source_data_url']})")
    for source in article.get("fonti") or []:
        lines.append(f"- [{_clean(source['testo'])}]({source['url']})")
    if meta.get("downloads") and level.get("key") == "regione":
        lines += [
            f"- [Scarica CSV]({_absolute(site_url, meta['downloads']['csv'])})",
            f"- [Scarica JSON]({_absolute(site_url, meta['downloads']['json'])})",
        ]
    lines.append(f"- [Metodologia di Divario Italia]({site_url}/metodologia)")
    return "\n".join(lines)


def region_markdown(profile, site_url):
    lines = [
        f"# {profile['region']}: profilo territoriale",
        "",
        f"Il profilo confronta {profile['comparable_count']} indicatori disponibili su base regionale. "
        "Le posizioni sono descrittive e non dimostrano rapporti di causa.",
        "",
        f"URL canonica: {site_url}/regione/{profile['region_key']}",
        "",
        "## Temi in cui la regione si colloca più in alto",
        "",
    ]
    for item in profile.get("themes_strong") or []:
        lines.append(f"- [{item['theme']}]({_absolute(site_url, item['theme_path'])}), {item['count']} indicatori confrontabili")
    if profile.get("themes_weak"):
        lines += ["", "## Temi in cui la regione si colloca più in basso", ""]
        for item in profile["themes_weak"]:
            lines.append(f"- [{item['theme']}]({_absolute(site_url, item['theme_path'])}), {item['count']} indicatori confrontabili")
    lines += ["", "## Indicatori in evidenza", ""]
    for item in (profile.get("top_excels") or [])[:6]:
        lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])})")
    lines += ["", "## Indicatori da approfondire", ""]
    for item in (profile.get("top_lags") or [])[:6]:
        lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])})")
    if profile.get("similar_regions"):
        lines += ["", "## Regioni con un profilo simile", ""]
        for item in profile["similar_regions"]:
            lines.append(f"- [{item['region']}]({site_url}/regione/{item['region_key']})")
    lines += ["", f"Metodo: {site_url}/metodologia"]
    return "\n".join(lines)


def theme_markdown(profile, site_url):
    lines = [
        f"# {profile['theme']}",
        "",
        profile["description"],
        "",
        f"Macro-area: {profile['macro_area']}",
        f"Indicatori: {profile['indicator_count']}",
        f"URL canonica: {_absolute(site_url, profile['theme_path'])}",
        "",
        "## Indicatori del tema",
        "",
    ]
    for item in profile["indicators"]:
        lines.append(
            f"- [{item['name']}]({_absolute(site_url, item['path'])}), "
            f"dal {item['year_min']} al {item['year_max']}. {_clean(item.get('plain'))}"
        )
    return "\n".join(lines)
