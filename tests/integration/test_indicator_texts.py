"""Indicator articles: structure, editorial style, vintage drift, and figures.

The article replaced the three loose analyst-note fields, so these guards are the
old ones re-aimed at the new schema, plus what the schema itself now needs
(known roles, no duplicate headings, a lead that can stand alone as a SERP
description).

The two numeric checks are the valuable ones and they exist because of real
mistakes that shipped: a claim that prison overcrowding exceeded capacity
"everywhere" while three regions were under it, and a note putting Sardegna above
78% of separate waste collection when it was at 76,6%. They are mechanical by
design. The interpretive half of an article still needs a human, and
docs/INDICATOR_PAGES.md lists what stays uncovered.
"""

import re
import unittest
import unittest.mock

from app import indicator_texts
from app.atlas_catalog import get_atlas_indicator
from officina import lint
from scripts import indicator_store

# Le guardie vere vivono in `officina/lint.py`, non qui. Ci stavano, ed era il
# motivo per cui controllare un articolo voleva dire eseguire millecento test:
# adesso il lint gira da solo in undici secondi e questa suite lo chiama. Una
# implementazione, due chiamanti, nessuna delle due che invecchia per conto suo.
BANNED = lint.BANNED
LEAD_FIRST_SENTENCE_MAX = lint.LEAD_FIRST_SENTENCE_MAX

_level_of = lint.level_of
_view = lint.view_of
_view_level = lint.view_level
_values_of = lint.values_of
_territory_alternation = lint.territory_alternation
_prose = lint.prose_of


def _load():
    return indicator_store.load_all()


def _level_year_max(key, entry):
    level = _view_level(key, entry)
    return level["year_max"] if level else None


class ArticleStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_entries_have_the_expected_shape(self):
        for key, entry in self.texts.items():
            with self.subTest(indicator=key):
                self.assertIsInstance(entry.get("sections", []), list)
                self.assertIsInstance(entry.get("fonti", []), list)
                for source in entry.get("fonti") or []:
                    self.assertIn("testo", source)
                    self.assertIn("url", source)

    def test_declared_level_is_one_the_indicator_actually_has(self):
        """A typo in `level` does not fail loudly, it hides the article.

        An entry is used only on the level it declares, so `"level": "provincie"`
        renders nowhere and the page silently falls back to the composed
        skeleton, looking exactly like an article nobody has written.
        """
        from app.indicator_view import build_indicator_view

        wrong = []
        for key, entry in self.texts.items():
            declared = entry.get("level")
            if not declared:
                continue
            family, raw_id = __import__("app.sources", fromlist=["x"]).split_internal_id(key)
            view = build_indicator_view(family, raw_id)
            if view is None:
                continue
            available = [level["key"] for level in view["levels"]]
            if declared not in available:
                wrong.append((key, declared, available))
        self.assertEqual(wrong, [], f"level declared but not available: {wrong[:10]}")

    def test_reviewed_at_is_a_date_when_present(self):
        """`reviewed_at` takes an article out of the review queue, so a value the
        queue cannot read would silently mark it as never reviewed."""
        bad = [
            (key, entry["reviewed_at"])
            for key, entry in self.texts.items()
            if entry.get("reviewed_at") is not None
            and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("reviewed_at")))
        ]
        self.assertEqual(bad, [], f"reviewed_at must be YYYY-MM-DD: {bad[:10]}")

    def test_reviewed_vintage_is_an_integer_when_present(self):
        """`reviewed_vintage` records the data year a reviewer actually read, and
        `scripts/review_queue.py` compares it to the article's current `vintage`
        to decide whether the signature has expired. A string "2023" would never
        equal the integer 2023, so a typed slip would re-open every signed
        article forever and make the reading order meaningless.
        """
        bad = [
            (key, entry.get("reviewed_vintage"))
            for key, entry in self.texts.items()
            if entry.get("reviewed_vintage") is not None
            and not isinstance(entry.get("reviewed_vintage"), int)
        ]
        self.assertEqual(bad, [], f"reviewed_vintage must be an integer: {bad[:10]}")

    def test_a_signed_article_records_what_it_was_signed_against(self):
        """A signature with no vintage is one the re-entry rule cannot trust, so
        it re-opens. That is the safe direction, but it is also silent: an agent
        that keeps forgetting the field would rewrite the same article every run
        and never notice. Fail loudly instead."""
        unsigned = [
            key
            for key, entry in self.texts.items()
            if (entry.get("reviewed_at") or "").strip()
            and entry.get("reviewed_vintage") is None
        ]
        self.assertEqual(
            unsigned, [], f"reviewed_at without reviewed_vintage: {unsigned[:10]}"
        )

    def test_an_opted_in_article_declares_a_coherent_set_of_roles(self):
        """La coerenza di `roles_covered`, non il divieto di usarlo.

        Fino ad agosto 2026 questo test asseriva che l'elenco fosse **vuoto**:
        nessun articolo poteva dichiarare `roles_covered`, cioe' nessuno poteva
        usare il solo meccanismo costruito per non aprire sulla definizione.
        Progettato, implementato, documentato in `docs/INDICATOR_PAGES.md`, e
        usato da 0 file su 375, perche' un test lo vietava. Il freno di
        sicurezza di un rilascio graduale era diventato il motivo per cui il
        rilascio non partiva mai, e intanto 52 articoli su 52 aprivano allo
        stesso modo.

        Adesso il vincolo e' quello vero: se opti, dichiara ruoli che esistono,
        e `definizione` resta l'unico assorbibile, perche' quadro, dinamica e
        limiti sono l'articolo.
        """
        wrong = []
        for key, entry in self.texts.items():
            declared = entry.get("roles_covered")
            if not declared:
                continue
            if not isinstance(declared, list):
                wrong.append((key, "roles_covered non e' una lista"))
                continue
            known = set(indicator_texts.DEFAULT_HEADINGS)
            unknown = [role for role in declared if role not in known]
            if unknown:
                wrong.append((key, f"ruoli sconosciuti: {unknown}"))
            written = {section.get("role") for section in entry.get("sections") or []}
            for role in sorted(indicator_texts.SUBSTANTIVE_ROLES):
                if role not in written:
                    wrong.append((key, f"manca la sezione {role}"))
        self.assertEqual(wrong, [], f"opt-in incoerenti: {wrong[:10]}")


class VariableSectionsAreOptIn(unittest.TestCase):
    """Le sezioni variabili: un'entry che dichiara `roles_covered` assorbe la
    definizione nel blocco "Come leggere" invece di aprire con la metodologia.
    Senza il campo, il comportamento e' identico a prima."""

    OPT_IN = {
        "level": "regione", "lead": "Un lead che apre sulla geografia.",
        "vintage": 2023, "reviewed_at": "2026-08-01", "reviewed_vintage": 2023,
        "roles_covered": ["quadro", "dinamica", "limiti"],
        "sections": [
            {"role": "quadro", "h": "Un vertice solo", "body": "Corpo quadro."},
            {"role": "dinamica", "h": "Cinque anni fermi", "body": "Corpo dinamica."},
            {"role": "limiti", "h": "Quanto lavoro", "body": "Corpo limiti."},
        ],
    }
    LEGACY = {
        "level": "regione", "lead": "Un lead.", "vintage": 2023,
        "sections": [
            {"role": "definizione", "h": None, "body": "Che cosa misura."},
            {"role": "quadro", "h": None, "body": "Come si distribuisce."},
            {"role": "dinamica", "h": None, "body": "Come e' cambiato."},
            {"role": "limiti", "h": None, "body": "Che cosa non dice."},
        ],
    }

    def _build(self, entry):
        with unittest.mock.patch.object(indicator_texts, "get_text", lambda _id: entry):
            return indicator_texts.build_article("432", "regione")

    def test_an_opt_in_entry_omits_the_definizione_h2(self):
        art = self._build(self.OPT_IN)
        self.assertEqual([s["role"] for s in art["sections"]], ["quadro", "dinamica", "limiti"])
        self.assertTrue(art["come_leggere"])

    def test_the_coherence_guard_accepts_a_well_formed_opt_in(self):
        """Il divieto e' caduto davvero, non solo sulla carta.

        La guardia che prima vietava `roles_covered` adesso ne controlla la
        coerenza. Un test che gira su un catalogo dove nessuno opta ancora non
        dimostra niente: qui l'entry opt-in viene passata alla guardia vera.
        """
        guard = ArticleStructure("test_an_opted_in_article_declares_a_coherent_set_of_roles")
        guard.texts = {"432": self.OPT_IN}
        guard.test_an_opted_in_article_declares_a_coherent_set_of_roles()

    def test_the_coherence_guard_still_catches_a_broken_opt_in(self):
        """E la guardia non e' diventata un colabrodo mentre smetteva di vietare."""
        guard = ArticleStructure("test_an_opted_in_article_declares_a_coherent_set_of_roles")
        guard.texts = {"432": dict(self.OPT_IN, roles_covered=["inventato"])}
        with self.assertRaises(AssertionError):
            guard.test_an_opted_in_article_declares_a_coherent_set_of_roles()

        missing = dict(self.OPT_IN,
                       sections=[s for s in self.OPT_IN["sections"]
                                 if s["role"] != "dinamica"])
        guard.texts = {"432": missing}
        with self.assertRaises(AssertionError):
            guard.test_an_opted_in_article_declares_a_coherent_set_of_roles()

    def test_a_partial_declaration_still_renders_the_three_substantive_roles(self):
        """Solo la definizione e' assorbibile. Senza questa invariante nel
        renderer, un `roles_covered` scritto male (o parziale) toglieva dalla
        pagina pubblica `dinamica` e `limiti` invece di comporli dallo
        scheletro: due sezioni perse per un errore di battitura in un JSON."""
        art = self._build(dict(self.LEGACY, roles_covered=["quadro"]))
        self.assertEqual([s["role"] for s in art["sections"]],
                         ["quadro", "dinamica", "limiti"])
        self.assertTrue(art["come_leggere"])

    def test_an_empty_declaration_is_still_a_declaration(self):
        """`roles_covered: []` non e' il campo assente: e' una dichiarazione che
        non nomina la definizione, quindi la assorbe come farebbe `["quadro"]`.
        Un test di verita' le confondeva, e la stessa entry rendeva quattro
        sezioni in una forma e tre nell'altra."""
        art = self._build(dict(self.LEGACY, roles_covered=[]))
        self.assertEqual([s["role"] for s in art["sections"]],
                         ["quadro", "dinamica", "limiti"])
        self.assertTrue(art["come_leggere"])

    def test_an_absorbed_section_stops_weighing_on_the_fingerprint(self):
        """Una sezione assorbita resta nel file e non e' piu' in pagina, quindi il
        verificatore non puo' leggerla: continuare a pesarla avrebbe fatto scadere
        la verifica a ogni ritocco di un testo invisibile."""
        from scripts import verification_queue as vq
        absorbed = dict(self.LEGACY, roles_covered=["quadro", "dinamica", "limiti"])
        edited = dict(absorbed, sections=[
            dict(section, body="Definizione riscritta da capo.")
            if section["role"] == "definizione" else section
            for section in absorbed["sections"]
        ])
        self.assertEqual(vq.prose_fingerprint(absorbed), vq.prose_fingerprint(edited))
        # La stessa modifica su un articolo che la definizione la rende cambia
        # l'impronta, come e' sempre stato.
        legacy_edited = dict(self.LEGACY, sections=edited["sections"])
        self.assertNotEqual(vq.prose_fingerprint(dict(self.LEGACY)),
                            vq.prose_fingerprint(legacy_edited))

    def test_a_legacy_entry_keeps_four_sections_and_no_block(self):
        art = self._build(self.LEGACY)
        self.assertEqual([s["role"] for s in art["sections"]],
                         ["definizione", "quadro", "dinamica", "limiti"])
        self.assertFalse(art["come_leggere"])

    def test_roles_covered_does_not_enter_the_prose_fingerprint(self):
        """La chiave di sicurezza: dichiarare i quattro ruoli non tocca
        l'impronta, perche' la pagina rende esattamente come prima. I trecento
        articoli esistenti, che il campo non ce l'hanno, tanto meno."""
        from scripts import verification_queue as vq
        without = dict(self.LEGACY)
        with_field = dict(self.LEGACY, roles_covered=["definizione", "quadro", "dinamica", "limiti"])
        self.assertEqual(vq.prose_fingerprint(without), vq.prose_fingerprint(with_field))

    def test_absorbing_the_definizione_does_change_the_fingerprint(self):
        """L'altra meta', e senza di essa il campo era una scorciatoia per
        cambiare la pagina senza riverificarla: un'entry gia' verificata poteva
        togliersi la definizione dalla pagina senza toccare una parola di prosa,
        la verifica vecchia continuava a combaciare, e una smentita appesa alla
        definizione ora nascosta restava aperta su una sezione che nessuno vede
        piu'. Cambiare cio' che la pagina mostra e' un cambio della pagina."""
        from scripts import verification_queue as vq
        absorbed = dict(self.LEGACY, roles_covered=["quadro", "dinamica", "limiti"])
        self.assertNotEqual(vq.prose_fingerprint(dict(self.LEGACY)),
                            vq.prose_fingerprint(absorbed))


class SectionsUseKnownRoles(unittest.TestCase):
    def setUp(self):
        self.texts = indicator_store.load_all()

    def test_sections_use_known_roles_once_each(self):
        offenders = []
        for key, entry in self.texts.items():
            roles = [section.get("role") for section in entry.get("sections") or []]
            for role in roles:
                if role not in indicator_texts.DEFAULT_HEADINGS:
                    offenders.append((key, role, "unknown role"))
            duplicates = {role for role in roles if roles.count(role) > 1}
            for role in duplicates:
                offenders.append((key, role, "duplicated"))
        self.assertEqual(offenders, [], f"bad section roles: {offenders[:10]}")

    def test_sections_have_a_non_empty_body(self):
        """A role present with an empty body would render as a bare heading.

        Omitting the role is the supported way to say "not written yet": the page
        then composes that section from the data.
        """
        empty = [
            (key, section.get("role"))
            for key, entry in self.texts.items()
            for section in entry.get("sections") or []
            if not (section.get("body") or "").strip()
        ]
        self.assertEqual(empty, [], f"sections present but empty: {empty[:10]}")

    def test_authored_headings_are_not_reused_across_indicators(self):
        """Identical H2s across the catalogue read as a stamp (content/STYLE.md).

        The role defaults are shared on purpose and excluded; this only catches an
        author copying the same custom heading onto several indicators.
        """
        seen = {}
        clashes = []
        defaults = set(indicator_texts.DEFAULT_HEADINGS.values())
        for key, entry in self.texts.items():
            for section in entry.get("sections") or []:
                heading = (section.get("h") or "").strip()
                if not heading or heading in defaults:
                    continue
                if heading in seen:
                    clashes.append((heading, seen[heading], key))
                seen[heading] = key
        self.assertEqual(clashes, [], f"headings reused across indicators: {clashes[:10]}")

    def test_lead_opens_with_a_sentence_that_can_stand_alone(self):
        too_long = []
        for key, entry in self.texts.items():
            lead = (entry.get("lead") or "").strip()
            if not lead:
                continue
            first = re.split(r"(?<=[.!?])\s", lead)[0]
            if len(first) > LEAD_FIRST_SENTENCE_MAX:
                too_long.append((key, len(first)))
        self.assertEqual(too_long, [], f"lead first sentences too long for a SERP description: {too_long[:10]}")

    def test_prose_respects_editorial_style(self):
        offenders = [
            (key, field, char)
            for key, entry in self.texts.items()
            for field, text in _prose(entry)
            for char in BANNED
            if char in text
        ]
        self.assertEqual(offenders, [], f"style violations: {offenders[:10]}")


class ParagraphsSurviveRendering(unittest.TestCase):
    """A section written in paragraphs must render in paragraphs.

    The body goes through `analyst_html`, which is Markdown, where a single `\\n`
    is a soft wrap and not a paragraph break. So a section separated by single
    newlines produces exactly one `<p>`, which the filter then strips (it strips
    the wrapper only when there is one), and the whole section lands on the page
    as an unbroken wall of text. Three of ten freshly written articles had it.

    It is invisible in the JSON, invisible in the diff, and invisible to a render
    check that strips the tags and splits on newlines, because that rebuilds the
    paragraphs the browser would never show. The only honest check counts the
    `<p>` the filter actually emits, which is what this does.
    """

    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_every_authored_section_renders_inside_a_block_element(self):
        """A section body must never reach the page as a bare text node.

        `analyst_html` strips the single wrapping <p>, which is right for the
        page lead (the template already opened one) and wrong for a section
        body (the macro does not). Under the wrong filter a one-paragraph
        section rendered unwrapped, and `.prose > * + *` in site.css applies its
        spacing to elements only, so that section sat flush against its own h2
        while the multi-paragraph ones kept the gap. 710 sections in 355 of the
        364 articles, on every page, and invisible in the JSON.
        """
        from app.views import prose_html

        bare = []
        for key, entry in self.texts.items():
            for section in entry.get("sections") or []:
                body = (section.get("body") or "").strip()
                if body and not str(prose_html(body)).startswith("<"):
                    bare.append((key, section.get("role")))
        self.assertEqual(bare, [], f"sections rendering as a bare text node: {bare[:10]}")

    def test_the_lead_filter_still_strips_its_wrapper(self):
        """The other half of the same split, and the reason it exists.

        The lead sits inside a <p class="page-lead"> the template opens, so a
        second <p> nested in it is invalid HTML and the browser closes the outer
        one early. Whoever unifies these two filters has to break one of these
        two tests to do it.
        """
        from app.views import analyst_html, prose_html

        self.assertEqual(str(analyst_html("Una frase sola.")), "Una frase sola.")
        self.assertEqual(str(prose_html("Una frase sola.")), "<p>Una frase sola.</p>")

    def test_a_body_written_in_paragraphs_produces_more_than_one(self):
        from app.views import analyst_html

        collapsed = []
        for key, entry in self.texts.items():
            for section in entry.get("sections") or []:
                body = section.get("body") or ""
                if "\n" not in body:
                    continue
                paragraphs = str(analyst_html(body)).count("<p>")
                if paragraphs < 2:
                    collapsed.append((key, section.get("role"), body.count("\n")))
        self.assertEqual(
            collapsed, [],
            "sections whose newlines do not survive rendering, so they show as one "
            f"block (id, role, newlines): {collapsed[:10]}",
        )


class InternalLinksInProse(unittest.TestCase):
    """Cross-references in an article, checked the way the blog's already are.

    The prose is rendered through `analyst_html`, so a markdown link in a body
    becomes a real anchor on a real page. Two ways that goes wrong and nothing
    else catches it: a path shape that does not resolve (the atlas link forms
    `/?indicator=` and `/atlante?indicator=` reach the indicator only through
    JavaScript, which is why `tests/test_url_migration.py` bans them in the blog),
    and a path that is canonical in shape but points at an indicator that does
    not exist, because the slug was hand-built instead of copied from the brief.

    The anchor text is checked too, and that one is editorial rather than
    mechanical: Google's own guidance is that the linked words should say where
    they lead, and "clicca qui" in the middle of a paragraph is both worse for a
    reader and worse for the internal-linking model the theme hubs rest on.
    """

    LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    BANNED_FORMS = ("/?indicator=", "/atlante?indicator=", "?indicator=")
    GENERIC_ANCHORS = {
        "qui", "clicca qui", "clicca", "leggi", "leggi di più", "leggi di piu",
        "leggi tutto", "questa pagina", "la pagina", "questo link", "link",
        "vedi", "vedi qui", "scopri di più", "scopri di piu", "approfondisci",
    }

    @classmethod
    def setUpClass(cls):
        from app.atlas_catalog import get_atlas_catalog

        cls.texts = _load()
        cls.canonical = {item["path"] for item in get_atlas_catalog()["indicators"]}

    def _internal_links(self):
        for key, entry in self.texts.items():
            for field, text in _prose(entry):
                for match in self.LINK.finditer(text):
                    anchor, url = match.group(1).strip(), match.group(2).strip()
                    if url.startswith(("http://", "https://", "mailto:")):
                        continue
                    yield key, field, anchor, url

    def test_no_prose_link_uses_a_form_that_needs_javascript(self):
        wrong = [
            (key, field, url)
            for key, field, _, url in self._internal_links()
            if any(form in url for form in self.BANNED_FORMS)
        ]
        self.assertEqual(wrong, [], f"non-canonical indicator links: {wrong[:10]}")

    def test_every_indicator_link_resolves_to_an_indicator_that_exists(self):
        broken = [
            (key, field, url)
            for key, field, _, url in self._internal_links()
            if url.startswith("/indicatore/") and url.split("#")[0].split("?")[0] not in self.canonical
        ]
        self.assertEqual(broken, [], f"links to indicators that do not exist: {broken[:10]}")

    def test_internal_links_point_somewhere_the_site_actually_serves(self):
        """Anything internal that is not an indicator must at least be a path we
        publish, so a theme hub link cannot rot into a 404 unnoticed."""
        from app import app

        client = app.test_client()
        dead = []
        for key, field, _, url in self._internal_links():
            if url.startswith("/indicatore/") or not url.startswith("/"):
                continue
            if client.get(url).status_code not in (200, 301, 308):
                dead.append((key, field, url))
        self.assertEqual(dead, [], f"internal links that do not resolve: {dead[:10]}")

    def test_anchor_text_says_where_it_leads(self):
        generic = [
            (key, field, anchor)
            for key, field, anchor, _ in self._internal_links()
            if anchor.lower().strip(" .,:") in self.GENERIC_ANCHORS
        ]
        self.assertEqual(generic, [], f"anchors that could be any link: {generic[:10]}")


class ArticleVintageDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = _load()

    def test_every_entry_declares_an_integer_vintage(self):
        missing = [key for key, entry in self.texts.items() if not isinstance(entry.get("vintage"), int)]
        self.assertEqual(missing, [], f"entries without an integer vintage: {missing[:10]}")

    def test_articles_are_not_stale_against_current_data(self):
        """The vintage must be >= the latest year of the level it describes.

        When the data moves forward this fails, flagging the hand-written figures
        for review before the page shows prose that contradicts the cockpit
        directly above it.

        Against the *level*, not against `metadata.year_max`, which spans every
        level at once. 10AMB011 is 2017-2020 by province and 2015-2024 by region,
        so a correct provincial article with vintage 2020 was reported stale
        against the regional 2024. The only way to make the suite green was to
        declare a vintage the provincial series never reaches, and that in turn
        pointed the figure guards at the wrong year.
        """
        stale = []
        for key, entry in self.texts.items():
            year_max = _level_year_max(key, entry)
            vintage = entry.get("vintage")
            if isinstance(year_max, int) and isinstance(vintage, int) and year_max > vintage:
                stale.append((key, entry.get("level", indicator_texts.DEFAULT_LEVEL), vintage, year_max))
        self.assertEqual(
            stale, [],
            f"articles older than the data they describe (id, level, vintage, data year): {stale[:10]}",
        )

    def test_every_key_resolves_to_an_indicator(self):
        """Due domande e non una, perche' ci sono due modi legittimi di esistere.

        La guardia chiedeva solo al catalogo dell'atlante, e il catalogo per
        costruzione non conosce le serie BES solo provinciali: senza copertura
        regionale non c'e' niente da canonicalizzare, quindi non entrano. Una
        pagina pero' ce l'hanno, e risponde 200 (`app/indicator_view.py`, il ramo
        `payload is None`).

        Cosi' tre strumenti della catena si contraddicevano sulla stessa chiave:
        `text_queue` offriva `bes-10AMB001P` come lavoro da scrivere, la pagina
        rendeva l'articolo, e questa guardia lo dichiarava orfano. L'articolo sul
        PM10 e' rimasto scritto e non pubblicabile, e con lui ogni altro
        indicatore solo provinciale della coda.

        La protezione non si allarga: una chiave inventata non risolve ne' nel
        catalogo ne' nella vista, e resta orfana come prima.
        """
        orphans = [key for key in self.texts
                   if get_atlas_indicator(key) is None and _view(key) is None]
        self.assertEqual(orphans, [], f"articles for missing indicators: {orphans[:10]}")

    def test_an_invented_key_is_still_an_orphan(self):
        """Il rischio di allargare una guardia e' spegnerla. Questa resta accesa."""
        self.assertIsNone(get_atlas_indicator("bes:NON-ESISTE-999"))
        self.assertIsNone(_view("bes:NON-ESISTE-999"))


class ArticleAgainstTheData(unittest.TestCase):
    """Figures and threshold claims, checked against the series they describe.

    The vintage guard catches an article that fell behind the data. It says
    nothing about one that was wrong when written, which is what these two cover.
    Only figures carrying a decimal are checked: a bare integer in this prose is
    almost always an approximation ("circa 27%", "quasi 78%").

    The gap these used to carry is closed: the territory names come from the
    data now, not from a list of the twenty regions typed into this file, so a
    figure attributed to a *province* is checked against provinces. Under the
    old list 67 provincial indicators over 103 provinces were verified by
    nothing, and nothing failed to say so.

    What is still uncovered, and stays uncovered on purpose: a name the prose
    spells differently from the dataset ("Reggio Emilia" for "Reggio
    nell'Emilia") matches nothing and passes. That misses coverage, it never
    invents a failure.
    """

    # I pattern, le esclusioni e la logica stanno in `officina/lint.py`: qui
    # c'erano le uniche copie, e una copia in un file di test e' una copia che
    # nessuno aggiorna quando cambia la prosa.
    NUMBER, ABOVE, BELOW, STATE = lint.NUMBER, lint.ABOVE, lint.BELOW, lint.STATE
    HEDGE, A_GAP = lint.HEDGE, lint.A_GAP
    ANOTHER_YEAR, ANOTHER_INDICATOR = lint.ANOTHER_YEAR, lint.ANOTHER_INDICATOR

    @classmethod
    def setUpClass(cls):
        cls.texts = _load()
        cls.TERRITORIES = lint.territory_alternation(cls.texts)
        compiled = lint.patterns(cls.TERRITORIES)
        cls.VALUE_OF_TERRITORY = compiled["value_of"]
        cls.TERRITORY_STATES_VALUE = compiled["states_value"]
        cls.THRESHOLD_OVER_TERRITORIES = compiled["threshold"]

    @staticmethod
    def _number(raw):
        return float(raw.replace(".", "").replace(",", "."))

    def test_figures_attributed_to_a_territory_match_that_territory(self):
        wrong = []
        for key, entry in self.texts.items():
            values = _values_of(key, entry)
            if not values:
                continue
            for field, text in _prose(entry):
                for match in self.VALUE_OF_TERRITORY.finditer(text):
                    raw, territory = match.group(1), match.group(2)
                    if "," not in raw or territory not in values:
                        continue
                    actual = values[territory]
                    if abs(self._number(raw) - actual) > max(0.06, abs(actual) * 0.011):
                        wrong.append((key, field, territory, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"figures that contradict the data: {wrong[:10]}")

    @classmethod
    def _states_a_value(cls, text, match):
        return lint.states_a_value(text, match)

    def test_figures_stated_after_the_territory_match_it(self):
        """Il verso che la prosa provinciale usa davvero.

        Qui gli interi contano, con una tolleranza di mezzo punto: su una serie
        provinciale come il PM10 un intero e' il valore, non un'approssimazione,
        e saltarlo lasciava scoperta l'intera famiglia.
        """
        wrong = []
        for key, entry in self.texts.items():
            values = _values_of(key, entry)
            if not values:
                continue
            for field, text in _prose(entry):
                for match in self.TERRITORY_STATES_VALUE.finditer(text):
                    territory, raw = match.group(1), match.group(2)
                    if territory not in values or not self._states_a_value(text, match):
                        continue
                    actual = values[territory]
                    floor = 0.06 if "," in raw else 0.5
                    if abs(self._number(raw) - actual) > max(floor, abs(actual) * 0.011):
                        wrong.append((key, field, territory, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"figures that contradict the data: {wrong[:10]}")

    def test_thresholds_hold_for_every_territory_they_name(self):
        wrong = []
        for key, entry in self.texts.items():
            values = _values_of(key, entry)
            if not values:
                continue
            for field, text in _prose(entry):
                for match in self.THRESHOLD_OVER_TERRITORIES.finditer(text):
                    verb, raw, listed = match.group(1), match.group(2), match.group(3)
                    threshold = self._number(raw)
                    above = bool(re.match(self.ABOVE, verb, re.I))
                    for territory in re.findall(self.TERRITORIES, listed):
                        if territory not in values:
                            continue
                        actual = values[territory]
                        ok = (actual >= threshold - 0.06) if above else (actual <= threshold + 0.06)
                        if not ok:
                            wrong.append((key, field, territory, verb, raw, round(actual, 2)))
        self.assertEqual(wrong, [], f"claims the data contradicts: {wrong[:10]}")

    def test_the_guard_actually_reaches_the_provinces(self):
        """Una guardia che non copre piu' niente non lo dice da sola.

        E' esattamente come sono passati i 67 indicatori provinciali: i test
        sopra giravano, non incontravano nessun nome, e restavano verdi. Questo
        e' il test che si accorge dello spegnimento.
        """
        provincial = {key: entry for key, entry in self.texts.items()
                      if _level_of(entry) == "provincia"}
        self.assertTrue(provincial, "nessun articolo provinciale da coprire")

        names = set()
        for key, entry in provincial.items():
            names.update(_values_of(key, entry))
        self.assertGreater(len(names), 50,
                           f"solo {len(names)} nomi provinciali nell'alternativa")
        province = sorted(names)[0]
        self.assertRegex(f"il 24,3% di {province}", self.VALUE_OF_TERRITORY)
        self.assertRegex(f"{province} si ferma a 18", self.TERRITORY_STATES_VALUE)

    def test_a_wrong_figure_does_not_slip_through(self):
        """Verde per merito, non per inerzia.

        Le due guardie sono passate per mesi perche' non incontravano niente da
        controllare. Qui la prosa e' sintetica: se una di queste smette di
        vedere una cifra sbagliata, il test lo dice subito, senza dipendere da
        che cosa c'e' scritto oggi negli articoli.
        """
        # I due pattern portano il numero in gruppi opposti: nel primo la cifra
        # precede il territorio, nel secondo lo segue.
        cases = (
            ("il 40,1% della Campania", self.VALUE_OF_TERRITORY, 1, "40,1"),
            ("la Campania si ferma a 40,1", self.TERRITORY_STATES_VALUE, 2, "40,1"),
            ("Gorizia si ferma a 18", self.TERRITORY_STATES_VALUE, 2, "18"),
        )
        for text, pattern, group, expected in cases:
            with self.subTest(text=text):
                match = pattern.search(text)
                self.assertIsNotNone(match, "la guardia non vede questa forma")
                self.assertEqual(match.group(group), expected)

        # e le tre esclusioni restano esclusioni
        for text in ("il Molise sta 39,4 punti sopra le Marche",
                     "la Sardegna segna 81,67 nel 2020",
                     "il [tasso](/indicatore/x/ter-407), dove la Campania si ferma a 21,80"):
            with self.subTest(text=text):
                match = self.TERRITORY_STATES_VALUE.search(text)
                self.assertFalse(match and self._states_a_value(text, match),
                                 "questa non e' una cifra da confrontare")


class ArticleRendering(unittest.TestCase):
    def test_a_missing_role_is_composed_not_blank(self):
        """The fallback contract: an unwritten role still produces a section.

        This is what keeps 621 pages structurally identical while only some of
        them have been through an editor.
        """
        article = indicator_texts.build_article("__does-not-exist__")
        self.assertEqual([s["role"] for s in article["sections"]], list(indicator_texts.ROLE_ORDER))
        for section in article["sections"]:
            self.assertFalse(section["authored"])
            self.assertIsNone(section["body"])
            self.assertTrue(section["heading"])

    def test_an_authored_section_keeps_its_heading_and_body(self):
        """Structural, and deliberately not pinned to one indicator's content.

        This used to assert that id 178 showed the *default* heading on
        `definizione`, which was true only while nobody had written that section.
        But 178 is the worked example in every doc and every command, so it is
        the first article an editor completes, and the moment the writer did the
        thing it is told to do (write its own h2) the suite went red on correct
        work. The writer's own contract says to run the guards and read the
        result, so it would have removed the heading to make the test pass.
        """
        key, entry = next(
            (key, entry) for key, entry in sorted(_load().items())
            if any((s.get("body") or "").strip() for s in entry.get("sections") or [])
        )
        authored_roles = {
            s["role"] for s in entry["sections"] if (s.get("body") or "").strip()
        }
        article = indicator_texts.build_article(key, entry.get("level", indicator_texts.DEFAULT_LEVEL))
        for section in article["sections"]:
            with self.subTest(indicator=key, role=section["role"]):
                self.assertTrue(section["heading"], "every section renders a heading")
                if section["role"] in authored_roles:
                    self.assertTrue(section["authored"])
                    self.assertTrue(section["body"])
                else:
                    # Not written: the template composes it, so body stays None.
                    self.assertFalse(section["authored"])
                    self.assertIsNone(section["body"])

    def test_an_authored_heading_wins_over_the_default(self):
        """The `h` an author writes must reach the page. Synthetic on purpose."""
        entry = {"sections": [{"role": "quadro", "h": "Un titolo scritto a mano", "body": "Corpo."}]}
        with unittest.mock.patch.object(indicator_texts, "get_text", return_value=entry):
            article = indicator_texts.build_article("__synthetic__")
        by_role = {section["role"]: section for section in article["sections"]}
        self.assertEqual(by_role["quadro"]["heading"], "Un titolo scritto a mano")
        # I ruoli che l'entry non scrive si compongono e prendono
        # l'intestazione di default. Un articolo a meta' non dichiara niente,
        # quindi la definizione resta: e' il caso dei trecento incompleti.
        self.assertEqual(
            by_role["definizione"]["heading"],
            indicator_texts.DEFAULT_HEADINGS["definizione"],
        )

    def test_a_half_written_article_is_not_making_a_declaration(self):
        """Incompleto non vuol dire "ho scelto questa forma".

        Trecentoventidue entry in `content/indicators/` hanno scritto `quadro` e
        `limiti` e nient'altro. Con la condizione debole ("almeno un ruolo
        sostanziale") sono passate tutte a `quadro, limiti, dinamica` con la
        definizione assorbita: un cambio di pagina su 322 articoli che nessuno
        aveva chiesto. Dichiara solo chi scrive **tutti e tre** i sostanziali.
        """
        entry = {"sections": [{"role": "quadro", "h": "a", "body": "Corpo."},
                              {"role": "limiti", "h": "b", "body": "Corpo."}]}
        with unittest.mock.patch.object(indicator_texts, "get_text", return_value=entry):
            article = indicator_texts.build_article("__synthetic__")
        self.assertEqual([section["role"] for section in article["sections"]],
                         list(indicator_texts.ROLE_ORDER))
        self.assertFalse(article["come_leggere"])

    def test_the_committed_catalogue_does_not_move(self):
        """Il guardiano dei trecento, contato invece che promesso."""
        from scripts import indicator_store
        canonica = tuple(indicator_store.load_all() and indicator_texts.ROLE_ORDER)
        mossi = [key for key, entry in indicator_store.load_all().items()
                 if tuple(indicator_texts.emitted_roles(entry)) != canonica
                 and not indicator_texts.SUBSTANTIVE_ROLES.issubset(
                     {s.get("role") for s in entry.get("sections") or []
                      if (s.get("body") or "").strip()})]
        self.assertEqual(mossi, [],
                         "un articolo incompleto ha cambiato forma in pagina")

    def test_the_authored_order_survives_to_the_page(self):
        """La sequenza che chi scrive sceglie non si riordina al render.

        Il pacchetto gli dice che la struttura nasce dall'angolo piu' forte, e
        la prima prova ha prodotto `quadro, limiti, dinamica`: la pagina lo
        rimetteva in ordine canonico, cioe' buttava via l'unica cosa che rompe
        lo stampo. Una promessa fatta a chi scrive e disfatta al render e'
        peggio di una promessa non fatta.
        """
        entry = {"sections": [
            {"role": "quadro", "h": "a", "body": "Corpo."},
            {"role": "limiti", "h": "b", "body": "Corpo."},
            {"role": "dinamica", "h": "c", "body": "Corpo."},
        ]}
        with unittest.mock.patch.object(indicator_texts, "get_text", return_value=entry):
            article = indicator_texts.build_article("__synthetic__")
        self.assertEqual([section["role"] for section in article["sections"]],
                         ["quadro", "limiti", "dinamica"])

    def test_a_committed_four_section_article_keeps_the_canonical_order(self):
        """I trecento non si muovono: scrivono i quattro ruoli in ordine."""
        entry = {"sections": [{"role": role, "h": role, "body": "Corpo."}
                              for role in indicator_texts.ROLE_ORDER]}
        with unittest.mock.patch.object(indicator_texts, "get_text", return_value=entry):
            article = indicator_texts.build_article("__synthetic__")
        self.assertEqual([section["role"] for section in article["sections"]],
                         list(indicator_texts.ROLE_ORDER))
        self.assertFalse(article["come_leggere"])


class ProseStaysOnTheLevelItWasWrittenFor(unittest.TestCase):
    """An article cites one level's figures and must not travel to the other.

    Every article that exists was written against the regions. 31 BES indicators
    also have a provincial level, and on those the regional lead named Umbria and
    Piemonte and gave the mean of the regions above a cockpit of provinces. The
    fix is the composed fallback, which reads whichever level it is handed.
    """

    @classmethod
    def setUpClass(cls):
        from app.bes_data import all_bes_indicators

        cls.two_level = [
            item["id"] for item in all_bes_indicators()
            if len(item.get("levels") or {}) > 1
        ]

    def test_a_regional_article_does_not_render_on_the_provincial_view(self):
        checked = 0
        for raw_id in self.two_level:
            regional = indicator_texts.build_article(f"bes:{raw_id}", "regione")
            if not regional["lead"] and not regional["authored_count"]:
                continue
            checked += 1
            provincial = indicator_texts.build_article(f"bes:{raw_id}", "provincia")
            self.assertIsNone(provincial["lead"], raw_id)
            self.assertEqual(provincial["authored_count"], 0, raw_id)
            for section in provincial["sections"]:
                self.assertFalse(section["authored"], f"{raw_id} {section['role']}")
        self.assertGreater(checked, 20, "expected the two-level BES articles to still exist")

    def test_a_single_level_indicator_is_left_exactly_as_it_was(self):
        """Nothing to retarget, so nothing may change.

        The first version of the level scoping substituted the bare noun, which
        turned the territorial "in tutti i territori regionali" into "in tutti i
        regioni" on 393 pages that never had the bug. This is the invariant that
        would have caught it, and it costs one comparison.
        """
        from app.indicator_view import build_indicator_view

        for family, raw_id in (("territorial", "178"), ("bes", "01SAL003")):
            view = build_indicator_view(family, raw_id)
            if view is None or len(view["levels"]) != 1:
                continue
            with self.subTest(indicator=f"{family}:{raw_id}"):
                self.assertEqual(view["levels"][0]["explain"], view["meta"]["explain"])

    def test_the_composed_article_names_the_level_it_is_rendered_at(self):
        """The composed text is level-scoped too, not just the authored one.

        `meta.explain` is built once per indicator with a fixed level, and two of
        its sentences name that level. On the provincial view of all 34 two-level
        BES indicators the definizione said "in tutte le regioni" and the limiti
        said "il confronto tra regioni", above 103 provinces. It is the only
        article those pages can show, since every authored one is regional.
        """
        from app.indicator_view import build_indicator_view

        checked = 0
        for raw_id in self.two_level:
            view = build_indicator_view("bes", raw_id)
            levels = {level["key"]: level for level in view["levels"]}
            if "provincia" not in levels:
                continue
            checked += 1
            explain = levels["provincia"]["explain"]
            for field in ("scope", "caveat"):
                with self.subTest(indicator=raw_id, field=field):
                    self.assertNotIn("regioni", (explain.get(field) or "").lower())
        self.assertGreater(checked, 20)

    def test_the_page_reports_the_rendered_levels_own_coverage(self):
        """meta.year_min/year_max span every level at once, level's do not.

        10AMB011 is 2017-2020 by province and 2015-2024 by region, so the
        apparatus used to announce a period the provincial series never covered.
        """
        from app import app
        from app.indicator_view import build_indicator_view

        client = app.test_client()
        pattern = re.compile(r'Dato più recente</dt>\s*<dd>(\d+), serie (\d+)-(\d+)', re.S)
        for raw_id in self.two_level:
            view = build_indicator_view("bes", raw_id)
            levels = {level["key"]: level for level in view["levels"]}
            if "provincia" not in levels:
                continue
            level = levels["provincia"]
            if level["year_min"] == level["year_max"]:
                continue
            url = f"{view['meta']['canonical_path']}?livello=provincia"
            found = pattern.search(client.get(url).get_data(as_text=True))
            self.assertIsNotNone(found, url)
            self.assertEqual(
                [int(value) for value in found.groups()],
                [level["year_max"], level["year_min"], level["year_max"]],
                url,
            )


if __name__ == "__main__":
    unittest.main()
