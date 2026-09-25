"""Il corpo della scheda sulle province, per chi cerca la sua.

Sulla vista provinciale (le 34 `?livello=provincia` e le 33 schede solo
provinciali) la scheda ha tre cose che la vista regionale non ha:
- "Dentro le regioni": in ogni regione la provincia piu' alta, la piu' bassa
  e la distanza fra le due, con un titolo-affermazione che dice la stessa
  distanza della frase-risposta;
- un id `p-<key>` su ogni riga della classifica, a cui `/provincia/<key>`
  porta e che `:target` accende anche senza JavaScript;
- la classifica piegata: le prime e le ultime dieci in vista, le altre nello
  stesso documento dentro un `details` (SISTEMA.md, "Classifica a barre").

Il comportamento nel browser (il cambio d'anno che ridisegna le righe con i
loro id e le ripiega, il campo "Trova la tua provincia", l'ancora con e senza
JavaScript) lo provano gli script in Chrome del rapporto della PR: qui si
guarda l'HTML che il server manda.
"""

import collections
import html as html_lib
import re
import unittest

from app import app, bes_data, province_profile
from app.seo_titles import from_place, to_place

SCHEDA = "/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001?livello=provincia"
WITHIN = re.compile(r'<figure class="module within" id="dentro-le-regioni">(.*?)</figure>', re.DOTALL)
ROW = re.compile(r"<tr><th scope=\"row\"><a href=\"(/regione/[^\"]+)\">([^<]+)</a></th>(.*?)</tr>", re.DOTALL)
RANK_ROW = re.compile(r'<tr data-key="([^"]+)" id="p-([^"]+)"><td class="rank">.*?<data value="(\d+)">')
PART = re.compile(r'<tbody data-rank-body data-rank-part="(head|middle|tail)">(.*?)</tbody>', re.DOTALL)
IDS = re.compile(r'\bid="([^"]+)"')
LEAD = re.compile(r'<p class="page-lead">(.*?)</p>', re.DOTALL)


def text(fragment):
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def provincial_views():
    """Tutte le viste provinciali: il link che una pagina provincia usa per
    ogni scheda con le province."""
    with app.app_context():
        return [bes_data.bes_level_path(item["id"], "provincia")
                for item in bes_data.all_bes_indicators() if "provincia" in item["levels"]]


class ProvincialBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = app.test_client()
        cls.pages = {}
        for path in provincial_views():
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            cls.pages[path] = response.get_data(as_text=True)
        cls.scheda = client.get(SCHEDA).get_data(as_text=True)

    def test_every_provincial_view_is_here(self):
        self.assertEqual(len(self.pages), 67)

    def test_within_regions_on_a_known_page(self):
        """Speranza di vita 2024: 19 regioni con almeno due province (la Valle
        d'Aosta ne ha una), in testa la Lombardia con 2,3 anni da Lecco a
        Pavia, come dice la frase-risposta."""
        block = WITHIN.search(self.scheda).group(1)
        self.assertIn('<h3 class="h-sub">La distanza più ampia è in Lombardia, 2,3 anni da Lecco a Pavia</h3>', block)
        rows = ROW.findall(block)
        self.assertEqual(len(rows), 19)
        self.assertNotIn("Valle d'Aosta", [name for _, name, _ in rows])
        href, name, cells = rows[0]
        self.assertEqual((href, name), ("/regione/lombardia", "Lombardia"))
        self.assertEqual(text(cells), "Lecco 84,9 Pavia 82,6 2,3")
        self.assertIn('<a href="/provincia/lecco">Lecco</a>', cells)
        self.assertIn('<a href="/provincia/pavia">Pavia</a>', cells)
        self.assertIn("Qui un valore più alto è migliore.", block)
        # Le distanze in ordine, dalla piu' ampia.
        gaps = [float(re.findall(r'<data class="n n--cell" value="([^"]+)"', cells)[-1]) for _, _, cells in rows]
        self.assertEqual(gaps, sorted(gaps, reverse=True))

    def test_the_claim_says_what_the_lead_says(self):
        """Dove la frase-risposta dice "In X 2,3 anni separano A da B", il
        titolo di "Dentro le regioni" dice la stessa regione, le stesse due
        province e la stessa cifra con la stessa unita'. Le province si leggono
        dai link della frase, non dalle preposizioni."""
        names = {key: info["name"] for key, info in bes_data.get_bes_territories("provincia").items()}
        seen = 0
        for path, page in self.pages.items():
            lead = LEAD.search(page).group(1)
            if " separano " not in lead:
                continue
            seen += 1
            with self.subTest(path=path):
                sentence = lead[lead.rindex(". ", 0, lead.index(" separano ")) + 2:]
                where, figure = re.match(r"(.+) (-?[\d.]+(?:,\d+)? \S+) separano ", text(sentence)).groups()
                upper, lower = re.findall(r'href="/provincia/([^"]+)"', sentence)
                claim = text(re.search(r'<h3 class="h-sub">(.*?)</h3>', WITHIN.search(page).group(1)).group(1))
                self.assertEqual(claim, f"La distanza più ampia è {where[:1].lower()}{where[1:]}, {figure} "
                                        f"{from_place(names[upper])} {to_place(names[lower])}")
        self.assertGreater(seen, 20, "poche frasi con la distanza dentro la regione: la prova non guarda niente")

    def test_a_claim_without_a_figure_names_the_ends_like_the_table(self):
        """Dove la frase-risposta non dice la distanza (un tasso su una base
        lunga), il titolo nomina gli estremi come la tabella sotto: a pari
        merito tutti e due i nomi ("da Foggia a Bari e Brindisi"), e quando
        sono di piu' solo la regione, perche' la cella dice "3 province"."""
        checked = 0
        for path, page in self.pages.items():
            block = WITHIN.search(page).group(1)
            heading = re.search(r'<h3 class="h-sub">(.*?)</h3>', block)
            if not heading or re.search(r"\d", heading.group(1)):
                continue
            checked += 1
            claim = text(heading.group(1))
            _, region, cells = ROW.findall(block)[0]
            with self.subTest(path=path):
                self.assertIn(f" {region}", claim)
                if re.search(r"\b\d+ province\b", text(cells)):
                    self.assertTrue(claim.endswith(region), claim)
                else:
                    for name in re.findall(r'<a href="/provincia/[^"]+">([^<]+)</a>', cells):
                        self.assertIn(name.removeprefix("L'").removeprefix("La "), claim)
        self.assertGreater(checked, 10, "pochi titoli senza cifra: la prova non guarda niente")

    def test_unverified_extremes_have_no_claim(self):
        """Affollamento delle carceri: gli estremi non sono verificati
        (`seo_titles.UNVERIFIED_EXTREMES`), e il titolo li direbbe."""
        page = next(p for path, p in self.pages.items() if path.endswith("/bes-06POL012P"))
        block = WITHIN.search(page).group(1)
        self.assertNotIn("<h3", block)
        self.assertEqual(len(ROW.findall(block)), 19)

    def test_every_row_has_its_id(self):
        for path, page in self.pages.items():
            with self.subTest(path=path):
                rows = RANK_ROW.findall(page)
                self.assertGreater(len(rows), 20)
                self.assertTrue(all(anchor == key for key, anchor, _ in rows))
                self.assertEqual([int(rank) for _, _, rank in rows], list(range(1, len(rows) + 1)))

    def test_no_duplicate_ids(self):
        for path, page in self.pages.items():
            with self.subTest(path=path):
                counts = collections.Counter(IDS.findall(page))
                self.assertEqual([k for k, n in counts.items() if n > 1], [])

    def test_the_middle_rows_are_in_a_details(self):
        """107 province: 1-10 in vista, 11-97 nel details, 98-107 in vista, nello
        stesso documento. La riga della media semplice sta dove la classifica la
        incrocia."""
        parts = dict(PART.findall(self.scheda))
        ranks = {name: [int(r) for r in re.findall(r'<data value="(\d+)">', body)] for name, body in parts.items()}
        self.assertEqual(ranks["head"], list(range(1, 11)))
        self.assertEqual(ranks["middle"], list(range(11, 98)))
        self.assertEqual(ranks["tail"], list(range(98, 108)))
        details = re.search(r"<details class=\"more\" data-rank-more>(.*?)</details>", self.scheda, re.DOTALL).group(1)
        self.assertIn('data-rank-part="middle"', details)
        self.assertIn("<summary data-rank-summary>Dall&#39;11ª alla 97ª: le altre 87 province</summary>", details)
        self.assertEqual(sum("Media semplice delle 107 province" in body for body in parts.values()), 1)

    def test_a_short_ranking_is_not_folded(self):
        """29 province (elezioni regionali): sotto la soglia della classifica
        della qualita' della vita, niente details. Gli id restano."""
        page = next(p for path, p in self.pages.items() if path.endswith("/bes-06POL001P"))
        self.assertNotIn("data-rank-more", page)
        self.assertEqual(len(RANK_ROW.findall(page)), 29)

    def test_the_regional_view_is_untouched(self):
        page = app.test_client().get("/indicatore/speranza-di-vita-alla-nascita/bes-01SAL001").get_data(as_text=True)
        for mark in ('id="dentro-le-regioni"', 'id="p-', "data-rank-part", "data-rank-more"):
            self.assertNotIn(mark, page)


class ProvincePageLandsOnTheRow(unittest.TestCase):
    """`/provincia/<key>` porta a ogni scheda sulla riga della provincia
    (`#p-<key>`), e la riga c'e'. `test_link_interni` fa lo stesso controllo
    su tutte le 107 province, qui si guarda una provincia da vicino."""

    def test_pavia(self):
        client = app.test_client()
        page = client.get("/provincia/pavia").get_data(as_text=True)
        anchored = sorted(set(re.findall(r'href="(/indicatore/[^"#]+#p-pavia)"', page)))
        with app.app_context():
            rows = province_profile.indicatori("pavia")
        self.assertEqual(len(anchored), sum(r["path"].endswith("#p-pavia") for r in rows))
        self.assertGreater(len(anchored), 50)
        for link in anchored:
            with self.subTest(link=link):
                target = client.get(link.split("#")[0]).get_data(as_text=True)
                self.assertRegex(target, r'<tr data-key="pavia" id="p-pavia">')
        # Una riga senza il dato dell'ultimo anno non ha l'ancora: nella
        # classifica della scheda non ci sarebbe.
        for row in rows:
            if not row["path"].endswith("#p-pavia"):
                target = client.get(row["path"]).get_data(as_text=True)
                self.assertNotIn('id="p-pavia"', target)


if __name__ == "__main__":
    unittest.main()
