"""Le porte della home portano dove porta il menu.

Le destinazioni che la home mette in evidenza sotto la testata
(`MAIN_DOORS`, `MORE_DOORS` in `app/design/pages/home.py`) si dichiarano per
percorso, e i percorsi sono quelli di `app/nav.py`. Una porta che punta a una
pagina tolta dal menu e' una porta rotta che nessun'altra prova vedrebbe, e
una tendina del menu senza nessuna porta e' una sezione che la home non
annuncia.
"""

import unittest

from app import nav
from app.design.pages import home


class LePorte(unittest.TestCase):
    def test_ogni_porta_e_una_voce_del_menu(self):
        voci = set(nav.paths())
        for path in home.MAIN_DOORS + home.MORE_DOORS:
            with self.subTest(porta=path):
                self.assertIn(path, voci)

    def test_nessuna_porta_ripetuta(self):
        porte = home.MAIN_DOORS + home.MORE_DOORS
        self.assertEqual(len(porte), len(set(porte)))

    def test_ogni_voce_del_menu_ha_una_porta(self):
        """Ogni voce di primo livello, e almeno una voce di ogni tendina."""
        porte = set(home.MAIN_DOORS + home.MORE_DOORS)
        for voce in nav.PRIMARY:
            percorsi = {v["path"] for v in voce["group"]} if voce.get("group") else {voce["path"]}
            with self.subTest(voce=voce["label"]):
                self.assertTrue(percorsi & porte, f"{voce['label']} non ha una porta in home")

    def test_le_cifre_vengono_dal_contesto(self):
        """"20 regioni" era scritto a mano in sei posti: qui ogni cifra arriva
        dal contesto della view, e senza contesto la porta resta senza cifra."""
        vuote = home.doors({})
        self.assertTrue(all(d["num"] is None for d in vuote["main"]))
        piene = home.doors({"territories": {"regions": 20, "provinces": 107}, "theme_total": 12},
                           {"regions": 20, "provinces": 107})
        self.assertEqual([d["num"] for d in piene["main"]], [20, 107, 12, 127])


if __name__ == "__main__":
    unittest.main()
