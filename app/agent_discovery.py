"""Read-only discovery documents and Markdown page projections."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from flask import Response, request

from app import it_numbers


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
    "/province",
}
_MARKDOWN_PREFIXES = ("/blog/", "/indicatore/", "/provincia/", "/regione/", "/tema/")


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
    level_parameter = {
        "name": "level",
        "in": "path",
        "required": True,
        "description": "Livello territoriale.",
        "schema": {"type": "string", "enum": ["regioni", "province"]},
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
                    "summary": "Cerca indicatori per nome, tema o descrizione, e territori per nome",
                    "description": "`results` sono gli indicatori, `territories` le regioni e le province il cui nome risponde alla domanda (anche senza accenti o con \"provincia di\" davanti).",
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
                    "description": "La serie servita e' quella regionale. I valori provinciali stanno nelle pagine /provincia/<key>, anche in Markdown.",
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
            "/api/quality-life/{level}/rankings": {
                "get": {
                    "summary": "Classifica della qualita' della vita, profilo predefinito",
                    "operationId": "getQualityLifeRanking",
                    "parameters": [level_parameter],
                    "responses": json_responses,
                }
            },
            "/api/quality-life/{level}/rankings/{profile}": {
                "get": {
                    "summary": "Classifica della qualita' della vita con un altro profilo di pesi",
                    "operationId": "getQualityLifeRankingByProfile",
                    "parameters": [level_parameter, {
                        "name": "profile", "in": "path", "required": True,
                        "description": "Slug del profilo, da /api/quality-life/profiles.",
                        "schema": {"type": "string"},
                    }],
                    "responses": json_responses,
                }
            },
            "/api/quality-life/{level}/{key}": {
                "get": {
                    "summary": "Punteggio, posizione e categorie di una regione o di una provincia",
                    "operationId": "getQualityLifeTerritory",
                    "parameters": [level_parameter, {
                        "name": "key", "in": "path", "required": True,
                        "description": "Chiave del territorio, per esempio lombardia o lecce. L'elenco delle province e' in /province.",
                        "schema": {"type": "string"},
                    }],
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
                    "description": "Serie regionale. Gli indicatori misurati solo per provincia non hanno download.",
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
    return it_numbers.number(value, decimals)


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
        f"- [Province]({site_url}/province)",
        f"- [Temi]({site_url}/temi)",
        f"- [Confronto tra regioni]({site_url}/confronto)",
        f"- [Qualità della vita, regioni e province]({site_url}/qualita-della-vita)",
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
            "## Regioni e province",
            "",
            ("Le regioni usano il BES nazionale e gli indicatori territoriali Istat, le province il BES dei Territori. "
             "Le schede indicatore con una serie regionale offrono il download in CSV e JSON, i valori provinciali "
             "si leggono nelle pagine delle province."),
            "",
            f"- [Catalogo dati]({site_url}/catalogo-dati)",
            f"- [Le regioni]({site_url}/regioni)",
            f"- [Le province]({site_url}/province)",
            f"- [Indice per modelli linguistici]({site_url}/llms.txt)",
        ]
    )


def _composed_indicator_section(role, meta, level):
    """Project the HTML article fallbacks into plain Markdown.

    ``build_article`` uses a missing body as an instruction to compose the
    section from the live view model.  Markdown is another representation of
    the same page, so it must preserve that instruction rather than treating a
    missing body as an empty section.
    """
    explain = level.get("explain") or meta.get("explain") or {}
    stats = level["stats"]

    if role == "definizione":
        return "\n\n".join(
            text for text in (
                explain.get("plain"),
                explain.get("example"),
                explain.get("scope"),
                explain.get("reading"),
            ) if text
        )

    if role == "quadro":
        paragraphs = []
        if level.get("best") and level.get("worst") and stats.get("gap_abs") is not None:
            paragraphs.append(
                f"Lo scarto tra {level['best']['name']} e {level['worst']['name']} è quello "
                f"osservato nell'anno più recente, {level['year_max']}. Da solo non dice se "
                "la differenza sia statisticamente significativa, e non spiega da che cosa dipenda."
            )
        if stats.get("above_avg_count") is not None and stats.get("below_avg_count") is not None:
            paragraphs.append(
                f"La media divide le {level['plural']} in due gruppi, "
                f"{stats['above_avg_count']} sopra e {stats['below_avg_count']} sotto."
            )
        if not meta.get("scoreable"):
            paragraphs.append(
                "Questo indicatore non ha una direzione univoca. L'ordinamento descrive "
                "l'intensità del fenomeno e non è una graduatoria di merito."
            )
        return "\n\n".join(paragraphs)

    if role == "dinamica":
        if not stats.get("has_multi_year"):
            return (
                f"La fonte pubblica un solo anno per questa serie, il {level['year_max']}. "
                "Non è quindi possibile calcolare una variazione rispetto a un anno precedente "
                "con la stessa definizione, e la fotografia va letta come tale."
            )
        paragraphs = []
        if stats.get("avg_change_abs") is not None:
            unit = meta.get("value_unit") or meta.get("unit") or "unità non specificata"
            level_adjective = "regionali" if level["key"] == "regione" else "provinciali"
            paragraphs.append(
                f"Dal {stats['year_min']} al {stats['year_max']} la media semplice dei valori "
                f"{level_adjective} è passata da {_number(stats['year_min_avg'])} a "
                f"{_number(stats['year_avg'])} {unit}."
            )
        annual = level.get("annual_change")
        if annual:
            paragraphs.append(
                f"Nell'ultimo passaggio disponibile, tra il {annual['previous_year']} e il "
                f"{annual['year']}, il valore è diminuito in {annual['decrease_count']} "
                f"{level['plural']}, è aumentato in {annual['increase_count']} e il confronto "
                f"usa i {annual['common_count']} territori presenti in entrambi gli anni. "
                f"{level.get('annual_note') or ''}"
            )
        return "\n\n".join(paragraphs)

    if role == "limiti":
        paragraphs = [explain.get("caveat")] if explain.get("caveat") else []
        if level.get("coverage") is not None and level["coverage"] < 1:
            paragraphs.append(
                f"Nell'anno più recente la copertura è parziale, "
                f"{len(level['observations'])} {level['plural']} su {level['territory_total']}. "
                "I territori mancanti non entrano nei calcoli della pagina."
            )
        return "\n\n".join(paragraphs)
    return ""


def indicator_markdown(meta, level, article, site_url):
    canonical = f"{site_url}{meta['canonical_path']}"
    unit = meta.get("value_unit") or meta.get("unit") or "unità non specificata"
    explain = level.get("explain") or meta.get("explain") or {}
    # Il titolo autorato vale anche qui: la proiezione markdown è una
    # rappresentazione di prima classe della stessa pagina, non un ripiego, e
    # dare all'agente il nome amministrativo mentre il lettore HTML legge il
    # titolo in lingua comune vuol dire due pagine diverse allo stesso URL.
    lines = [
        f"# {article.get('h1') or meta['name']}",
        "",
        article.get("lead") or explain.get("plain") or meta["name"],
        "",
        f"URL canonica: {canonical}",
        "",
        "## Scheda",
        "",
        # Il nome ufficiale della serie, sempre. Con un H1 autorato il titolo in
        # lingua comune sostituisce quello amministrativo, e nella proiezione
        # markdown non c'è nessun altro posto dove il nome ricompaia (la pagina
        # HTML ce l'ha nel blocco "Dato originale"): un agente avrebbe letto
        # cifre e fonte senza sapere **quale** serie sta leggendo, che è il modo
        # più facile di citarla per un'altra.
        f"- Serie: {meta['name']}",
        f"- Tema: [{meta['theme']}]({_absolute(site_url, meta['theme_path'])})",
        f"- Livello territoriale: {level['label']}",
        f"- Unità di misura: {unit}",
        f"- Copertura: dal {level['year_min']} al {level['year_max']}",
        f"- Territori nell'ultimo anno: {len(level['observations'])}",
        f"- Fonte: [{meta.get('source_label') or meta.get('source')}]({meta.get('source_url')})",
    ]
    # La definizione che ne da' l'istituto (`meta["archive"]`, che arriva da
    # `data/definitions/`). La pagina HTML la mostra da sempre nell'apparato,
    # sotto "Definizione della fonte", la proiezione markdown no: e' lo stesso
    # documento alla stessa URL, quindi o sta in tutte e due o e' una pagina
    # diversa con lo stesso canonico. Copre 346 delle 372 schede indicizzabili,
    # ed e' la prima cosa che un agente deve poter citare invece di
    # parafrasare la formula che il sito si compone da se'.
    if (meta.get("archive") or "").strip():
        lines += ["", "## Definizione della fonte", "", meta["archive"].strip(),
                  "", f"Fonte: [{meta.get('source_label') or meta.get('source')}]({meta.get('source_url')})"]
    if explain.get("plain"):
        lines += ["", "## Che cosa misura", "", explain["plain"]]
    if explain.get("example"):
        lines += ["", "## Esempio di lettura", "", explain["example"]]
    if explain.get("reading"):
        lines += ["", "## Come si interpreta", "", explain["reading"]]
    if explain.get("caveat"):
        lines += ["", "## Limiti", "", explain["caveat"]]

    for section in article.get("sections") or []:
        body = section.get("body") or _composed_indicator_section(
            section.get("role"), meta, level
        )
        if body:
            lines += ["", f"## {section['heading']}", "", body.strip()]

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

    means = level.get("annual_means") or []
    if len(means) > 1:
        # La stessa serie della tabella HTML. Senza, la rappresentazione markdown
        # restava l'unica vista della pagina priva della serie storica, cioè
        # esattamente ciò che questo cambio vuole rendere leggibile a chi non
        # esegue JavaScript: e un agente che chiede `text/markdown` è il lettore
        # senza JavaScript per definizione.
        lines += [
            "",
            f"## Serie storica, media delle {level['plural']} per anno",
            "",
            f"| Anno | Media ({unit}) |",
            "| ---: | ---: |",
        ]
        for point in means:
            lines.append(f"| {point['year']} | {_number(point['avg'])} |")

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


def region_markdown(profile, site_url, provinces=()):
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
    if provinces:
        from app.seo_titles import of_region
        title = "La provincia" if len(provinces) == 1 else "Le province"
        lines += ["", f"## {title} {of_region(profile['region'])}", ""]
        for item in provinces:
            lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])}), "
                         f"{item['rank']}ª per qualità della vita")
    lines += ["", "## Indicatori in evidenza", ""]
    for item in (profile.get("top_excels") or [])[:6]:
        lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])})")
    lines += ["", "## Indicatori da approfondire", ""]
    for item in (profile.get("top_lags") or [])[:6]:
        lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])})")
    # La tabella dei temi col rango sta anche qui: HTML e Markdown sono lo stesso
    # documento alla stessa URL, e il rango e' cio' che la pagina ha guadagnato.
    # Senza, la variante per le macchine resta all'elenco di nomi che la versione
    # visibile ha smesso di essere.
    con_rango = [t for t in (profile.get("theme_table") or []) if t.get("rank")]
    if con_rango:
        lines += ["", f"## Tutti i temi, con la posizione fra le {profile['region_total']} regioni", ""]
        lines.append(f"| tema | posizione | indicatori |")
        lines.append("| --- | ---: | ---: |")
        for item in con_rango:
            lines.append(
                f"| [{item['theme']}]({_absolute(site_url, item['theme_path'])}) "
                f"| {item['rank']} su {item['rank_total']} | {item['count']} |"
            )
    if profile.get("similar_regions"):
        lines += ["", "## Regioni con un profilo simile", ""]
        for item in profile["similar_regions"]:
            lines.append(f"- [{item['region']}]({site_url}/regione/{item['region_key']})")
    lines += ["", f"Metodo: {site_url}/metodologia"]
    return "\n".join(lines)


def province_markdown(profile, neighbours, site_url, indicators=None,
                      gains=(), losses=(), first_in_region=(), last_in_region=()):
    """La stessa pagina provincia, per chi chiede `text/markdown`.

    HTML e Markdown sono lo stesso documento alla stessa URL, quindi questa
    funzione segue il template sezione per sezione, con le stesse cifre scritte
    nello stesso modo. Fino al 23/9 era una pagina diversa: numeri col punto
    decimale, "qualita'" con l'apostrofo, "13a" invece di "13ª", quattro sezioni
    e la colonna Tema in meno.
    """
    from app.seo_titles import at_place

    name = profile["name"]
    region = profile.get("region") or ""
    total = profile["total"]
    score = it_numbers.number(profile["score"])
    kicker = "Qualità della vita"
    if region:
        kicker += f" · {region}"
    if profile.get("metro_city"):
        kicker += " · Città metropolitana"
    lead = (f"Con il profilo {profile['profile'].get('name', '').lower()}, {name} "
            f"ottiene {score} su 100.")
    if profile.get("strongest"):
        lead += f" Va meglio su {profile['strongest'][0]['name'].lower()}"
        if profile.get("weakest"):
            lead += f" e peggio su {profile['weakest'][0]['name'].lower()}"
        lead += "."
    lines = [
        f"# {name} è {profile['rank']}ª su {total} province",
        "",
        kicker,
        "",
        lead,
        "",
        f"URL canonica: {_absolute(site_url, profile['path'])}",
        "",
        "## Scheda",
        "",
        f"- Posizione: {profile['rank']}ª su {total}",
        f"- Punteggio: {score} su 100, dove 50 è la media",
    ]
    if region:
        label = f"[{region}]({_absolute(site_url, profile['region_path'])})" if profile.get("region_path") else region
        lines.append(f"- Regione: {label}")
    if profile.get("metro_city"):
        lines.append("- Città metropolitana: sì")
    if profile.get("strongest"):
        lines.append(f"- Forza: {profile['strongest'][0]['name']}")
    if profile.get("weakest"):
        lines.append(f"- Debole: {profile['weakest'][0]['name']}")

    if profile.get("categories"):
        lines += ["", "## Le dimensioni, dalla più forte alla più debole", "",
                  "| dimensione | punteggio |", "| --- | ---: |"]
        for entry in profile["categories"]:
            lines.append(f"| {entry['name']} | {it_numbers.number(entry['score'])} |")
        lines += ["", f"Punteggi da 0 a 100 sul profilo {profile['profile'].get('name', '').lower()}, "
                      f"dove 50 è la media delle {total} province. Non è una classifica ufficiale."]

    if indicators:
        in_region = any(row.get("in_regione") for row in indicators)
        lines += ["", f"## Tutti gli indicatori misurati {at_place(name)}", "",
                  f"I {len(indicators)} indicatori del BES dei Territori con un dato per {name}: "
                  "quanto valgono, in che anno, e in che posizione fra le province che quell'anno "
                  "hanno un dato (1 è la migliore)."
                  + (" Accanto alla posizione c'è quella fra le province della sua regione, "
                     "con la media delle altre." if in_region else ""),
                  "",
                  "| indicatore | tema | valore | posizione | movimento |",
                  "| --- | --- | ---: | ---: | ---: |"]
        for row in indicators:
            decimals = row.get("decimals", 1)
            value = it_numbers.number(row["value"], decimals)
            unit = f" {row['unit']}" if row.get("unit") else ""
            value_cell = f"{value}{unit}, {row['year']}"
            if row.get("variazione") is not None:
                value_cell += f", dal {row['year_from']} {it_numbers.change(row['variazione'], decimals)}"
            rank_cell = f"{row['rank']} su {row['province_count']}"
            if row.get("in_regione"):
                ir = row["in_regione"]
                rank_cell += (f", {ir['posizione']}ª di {ir['quante']} in {region}, media delle altre "
                              f"{ir['quante'] - 1}: {it_numbers.number(ir['media'], decimals)}")
            movement = row.get("movement")
            move_cell = "-" if movement is None else ("=" if movement == 0 else f"{movement:+d}")
            lines.append(f"| [{row['name']}]({_absolute(site_url, row['path'])}) | {row['theme']} "
                         f"| {value_cell} | {rank_cell} | {move_cell} |")

    def _value_list(title, rows):
        lines.extend(["", f"## {title}", ""])
        for row in rows:
            unit = f" {row['unit']}" if row.get("unit") else ""
            lines.append(f"- [{row['name']}]({_absolute(site_url, row['path'])}), "
                         f"{it_numbers.number(row['value'], row.get('decimals', 1))}{unit}, {row['year']}")

    if first_in_region or last_in_region:
        if first_in_region:
            _value_list("Prima della sua regione", first_in_region)
        else:
            lines += ["", "## Prima della sua regione", "",
                      f"Su nessuno degli indicatori misurati {name} è la prima fra le province di {region}."]
        if last_in_region:
            _value_list("Ultima della sua regione", last_in_region)
        else:
            lines += ["", "## Ultima della sua regione", "",
                      f"Su nessuno degli indicatori misurati {name} è l'ultima fra le province di {region}."]

    if gains or losses:
        lines += ["", "## Dove ha guadagnato posizioni", ""]
        for row in gains:
            lines.append(f"- [{row['name']}]({_absolute(site_url, row['path'])}), "
                         f"+{row['movement']} posizioni, {row['rank']}ª nel {row['year']}")
        lines += ["", "## Dove ne ha perse", ""]
        for row in losses:
            lines.append(f"- [{row['name']}]({_absolute(site_url, row['path'])}), "
                         f"{row['movement']} posizioni, {row['rank']}ª nel {row['year']}")

    for title, entries in (("Gli indicatori che la tirano su", profile.get("top_positive")),
                           ("Gli indicatori che la tirano giù", profile.get("top_negative"))):
        if entries:
            lines += ["", f"## {title}", ""]
            for entry in entries:
                year = f" ({entry['year_max']})" if entry.get("year_max") else ""
                lines.append(f"- [{entry['name']}]({_absolute(site_url, entry['path'])}){year}")

    if neighbours:
        lines += ["", "## Le province che le stanno intorno in classifica", ""]
        for entry in neighbours:
            lines.append(f"- {entry['rank']}ª [{entry['name']}]({_absolute(site_url, entry['path'])}), "
                         f"{it_numbers.number(entry['score'])}")

    coverage = round((profile.get("coverage") or 0) * 100)
    lines += ["", "## Fonti e metodo", "",
              f"- Fonte: {profile['methodology'].get('source') or 'Istat, BES dei Territori'}",
              f"- Come è calcolato: {profile['profile'].get('description', '')} I punteggi di dimensione "
              f"sono standardizzati sulle {total} province e mostrati da 0 a 100, dove 50 è la media.",
              f"- Copertura: {coverage}% degli indicatori del punteggio ha un dato per {name}.",
              f"- Classifica completa: {_absolute(site_url, '/qualita-della-vita/classifica/province')}",
              f"- Metodologia: {_absolute(site_url, '/metodologia#qualita-della-vita')}"]
    return "\n".join(lines)


def provinces_index_markdown(regions, total, site_url):
    """L'indice delle province, regione per regione, come la pagina HTML."""
    lines = [
        f"# Le {total} province italiane, regione per regione",
        "",
        (f"Il profilo di ognuna delle {total} province misurate dal BES dei Territori di Istat, "
         "in ordine geografico. La posizione è quella della classifica della qualità della vita, "
         "profilo equilibrato."),
        "",
        f"URL canonica: {site_url}/province",
        f"Classifica: {site_url}/qualita-della-vita/classifica/province",
    ]
    for region in regions:
        if not region["provinces"]:
            continue
        lines += ["", f"## {region['region']}", "",
                  f"Profilo della regione: {_absolute(site_url, region['path'])}", ""]
        for item in region["provinces"]:
            lines.append(f"- [{item['name']}]({_absolute(site_url, item['path'])}), "
                         f"{item['rank']}ª su {total}")
    return "\n".join(lines)


def theme_markdown(profile, site_url, standings=None, province_total=None):
    lines = [
        f"# {profile['theme']}",
        "",
        profile["description"],
        "",
        f"Macro-area: {profile['macro_area']}",
        f"Indicatori: {profile['indicator_count']}",
        f"URL canonica: {_absolute(site_url, profile['theme_path'])}",
        "",
    ]
    # La classifica sta anche qui, e non per completezza: HTML e Markdown sono
    # lo stesso documento alla stessa URL, e una variante che non porta la
    # risposta principale della pagina e' una pagina diversa con lo stesso
    # canonico.
    if standings and standings.get("rated") and standings.get("rows"):
        lines += [
            f"## Le regioni su questo tema, {standings['year_max']}",
            "",
            "Media semplice dei percentili orientati dei "
            f"{standings['indicator_count']} indicatori direzionali del tema, "
            "da 0 a 1. Non è una classifica ufficiale.",
            "",
            "| # | regione | punteggio |",
            "| ---: | --- | ---: |",
        ]
        for row in standings["rows"]:
            lines.append(
                f"| {row['rank']} | [{row['region']}]({_absolute(site_url, row['path'])}) "
                f"| {row['score']:.2f} |"
            )
        lines.append("")
    lines += [
        "## Indicatori del tema",
        "",
    ]
    for item in profile["indicators"]:
        lines.append(
            f"- [{item['name']}]({_absolute(site_url, item['path'])}), "
            f"dal {item['year_min']} al {item['year_max']}. {_clean(item.get('plain'))}"
        )
    if province_total:
        lines += ["", "## Gli altri modi di guardare", "",
                  f"- [Il profilo di ognuna delle regioni]({site_url}/regioni)",
                  f"- [Il profilo di ognuna delle {province_total} province]({site_url}/province)"]
    return "\n".join(lines)
