"""I testi visibili di "Chi è maggiore?" (`frontend/src/game/compare.jsx` e `game_compare.html`).

Tre difetti che non fanno fallire niente e che una rilettura non vede: una fonte scritta a
mano (il gioco ha pubblicato "Indicatore Istat" sopra una serie Eurostat), il totale delle
coppie cablato nel client (se il server cambia il numero, la riga di stato mente) e
"lunedi" senza l'accento nel testo della pagina."""

import re
import unittest
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
COMPARE_JSX = RADICE / "frontend" / "src" / "game" / "compare.jsx"
TEMPLATE = RADICE / "app" / "templates" / "game_compare.html"


def _senza_commenti(jsx):
    jsx = re.sub(r"/\*.*?\*/", "", jsx, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", riga) for riga in jsx.splitlines())


def _senza_json_ld(html):
    return re.sub(r"<script type=\"application/ld\+json\">.*?</script>", "", html, flags=re.S)


class FontiTest(unittest.TestCase):
    def test_il_client_non_scrive_un_istituto_a_mano(self):
        """L'etichetta della fonte viene dal server (`indicator.source_label`, da
        `app/sources.py`): mai "Istat" o "Eurostat" scritti nel componente."""
        codice = _senza_commenti(COMPARE_JSX.read_text(encoding="utf-8"))
        for istituto in ("Istat", "Eurostat"):
            self.assertNotIn(istituto, codice, f"`{istituto}` scritto a mano in compare.jsx")

    def test_la_pagina_non_scrive_un_istituto_a_mano(self):
        """Il lead dice chi pubblica i dati con `fonte_del_gioco`, che legge `sources.py`."""
        corpo = _senza_json_ld(TEMPLATE.read_text(encoding="utf-8"))
        corpo = re.sub(r"\{\{.*?\}\}", "", corpo, flags=re.S)
        for istituto in ("Istat", "Eurostat"):
            self.assertNotIn(istituto, corpo, f"`{istituto}` scritto a mano in game_compare.html")

    def test_il_lead_legge_la_fonte_dal_server(self):
        self.assertIn('fonte_del_gioco("compare").istituzioni', TEMPLATE.read_text(encoding="utf-8"))


class TotaleCoppieTest(unittest.TestCase):
    def test_il_client_non_cabla_il_numero_delle_coppie(self):
        """Il totale viene dalla sessione e finche' non c'e' si mostra "-"."""
        codice = _senza_commenti(COMPARE_JSX.read_text(encoding="utf-8"))
        self.assertIsNone(re.search(r"total\s*:\s*10\b", codice), "fallback `total: 10` nel client")
        self.assertIsNone(re.search(r":\s*10\s*\}", codice), "fallback `: 10` nel client")
        self.assertNotRegex(codice, r"sessione\.total\s*:\s*10")


class CablaggioTest(unittest.TestCase):
    """Il componente React non si prova con `node --test`: queste sono le guardie sul modo in
    cui usa `compare-logica.js`, che invece ha i suoi test con l'orologio finto."""

    def setUp(self):
        self.codice = _senza_commenti(COMPARE_JSX.read_text(encoding="utf-8"))

    def test_la_risposta_non_parte_dentro_un_updater_di_stato(self):
        """Un updater deve essere puro: React puo' invocarlo piu' volte, e ogni invocazione
        rifaceva la richiesta di timeout."""
        self.assertNotIn("setTimeLeft(", self.codice)
        self.assertNotRegex(self.codice, r"set[A-Z]\w*\(\s*\(?\w+\)?\s*=>\s*\{[^}]*(rispondi|submitAnswer)\(")

    def test_il_timer_passa_dalla_scadenza_assoluta(self):
        self.assertIn("avviaScadenza(", self.codice)
        self.assertNotRegex(self.codice, r"setInterval\(")

    def test_avanti_chiama_next_e_prende_il_token_nuovo(self):
        """Il server lega la coppia dopo solo con `next`: senza questa chiamata la seconda
        risposta e' `token_invalid`. Il token che torna sostituisce quello in mano."""
        self.assertIn("chiediAvanti(", self.codice)
        self.assertRegex(self.codice, r"tokenRef\.current\s*=\s*esito\.token")

    def test_il_timer_dell_allenamento_dipende_dall_interruttore(self):
        """Senza timer l'allenamento non scade: il conto si accende solo con `timer`."""
        self.assertRegex(self.codice, r"useTimerRound\(timer && status === \"answering\"")


class AccentoTest(unittest.TestCase):
    def test_lunedi_ha_l_accento(self):
        testo = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("lunedì", testo)
        self.assertNotRegex(testo, r"\blunedi\b")


if __name__ == "__main__":
    unittest.main()
