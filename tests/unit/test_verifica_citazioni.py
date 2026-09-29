"""La verifica delle citazioni: che cosa entra in `fonti.md` e che cosa no.

Il difetto che questa prova chiude e' la citazione inventata. Il 28 settembre
2026 un modello gratuito ne aveva date 1 su 18 nel `fonti.md` del pilota
(`docs/design_drafts/team/09_valutazione_pilota_ter12.md`): una citazione che
non si ritrova aprendo l'URL non entra nella tabella, e il numero di frammenti
trovati dice perche' e' falsa (parafrasi, oppure due frasi incollate).

Nessuna rete: lo scaricamento e' iniettato, il resto e' funzione pura.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.trend_articles import verifica_citazioni as vc

PAGINA = """
<html><body><p>Nel 2025 il tasso di disoccupazione scende al 5,8% (-0,1 punti),
mentre quello giovanile sale al 18,9%.</p><script>var x = "Il tasso di
disoccupazione scende al 5,8%"</script></body></html>
"""

FONTIC = """# Fonti per <slug>

Una riga che non ha niente da verificare.

| voce | istituzione | data | URL | citazione letterale | limite d'uso |
| --- | --- | --- | --- | --- | --- |
| aggancio | Istat | 30 settembre 2026 | https://istat.it/x | "Il tasso di disoccupazione scende al 5,8% (-0,1 punti), mentre quello giovanile sale al 18,9%." | Nazionale e provvisorio |
| dato recente | Banca d'Italia | settembre 2026 | https://bancaditalia.it/x | "le famiglie spendono di piu' per l'abitazione" | Solo da leggere come periodo |
| scena umana | Openpolis | 20 settembre 2026 | | non trovata | |
"""

# Due righe, lo stesso URL: serve a provare che la pagina si scarica una volta.
FONTIC_STESSO_URL = """
| voce | data | URL | citazione letterale | limite d'uso |
| --- | --- | --- | --- | --- |
| dato recente | 30 settembre 2026 | https://istat.it/x | "quello giovanile sale al 18,9%" | Nazionale |
| fattori | 30 settembre 2026 | https://istat.it/x | "quello giovanile scende al 18,9%" | Nazionale |
"""


def _scrivi(testo: str) -> Path:
    cartella = tempfile.mkdtemp()
    path = Path(cartella) / "fonti.md"
    path.write_text(testo, encoding="utf-8")
    return path


class Normalizza(unittest.TestCase):
    def test_virgolette_curve_spazi_e_maiuscole_non_contano(self):
        self.assertEqual(
            vc.normalizza("  Nel 2025  il\n\ntasso  SCENDE al 5,8%"),
            "nel 2025 il tasso scende al 5,8%",
        )

    def test_apici_e_doppi_apici_vengono_raddrizzati(self):
        self.assertEqual(
            vc.normalizza("“nel 2025 il tasso scende”"),
            vc.normalizza('"nel 2025 il tasso scende"'),
        )

    def test_il_tag_e_il_contenuto_di_script_escono(self):
        testo = vc.normalizza(PAGINA)
        self.assertIn("tasso di disoccupazione scende al 5,8%", testo)
        self.assertNotIn("var x", testo)


class Valuta(unittest.TestCase):
    def test_la_citazione_ritrovata_e_trovata(self):
        giudizio = vc.valuta(PAGINA, "quello giovanile sale al 18,9%")
        self.assertEqual(giudizio["esito"], vc.TROVATA)
        self.assertEqual(giudizio["frammenti"], "")

    def test_una_parfrasi_si_conta_a_zero_frammenti(self):
        giudizio = vc.valuta(PAGINA, "la disoccupazione giovanile e' diminuita nel 2025")
        self.assertEqual(giudizio["esito"], vc.NON_TROVATA)
        self.assertTrue(giudizio["frammenti"].startswith("0/"))

    def test_due_citazioni_incollate_non_passano_per_una(self):
        # Una meta' e' vera e una meta' arriva da un'altra pagina: e' il difetto
        # del 28 settembre, e i frammenti servono a vederlo.
        giudizio = vc.valuta(
            PAGINA,
            "il tasso di disoccupazione scende al 5,8% e gli immobili valgono "
            "un terzo del reddito delle famiglie italiane",
        )
        self.assertEqual(giudizio["esito"], vc.NON_TROVATA)
        self.assertIn("/", giudizio["frammenti"])

    def test_la_citazione_vuota_e_un_vuoto_non_un_esito(self):
        self.assertEqual(vc.valuta(PAGINA, "  ")["esito"], vc.NON_VERIFICABILE)


class Frammenti(unittest.TestCase):
    def test_una_citazione_corta_e_un_pezzo_solo(self):
        self.assertEqual(vc.frammenti("il tasso scende"), ["il tasso scende"])

    def test_quelle_lunghe_si_sovrappongono_e_coprono_tutto(self):
        parole = [f"p{i}" for i in range(12)]
        pezzi = vc.frammenti(" ".join(parole))
        self.assertEqual(pezzi[0], "p0 p1 p2 p3 p4 p5")
        self.assertEqual(pezzi[-1], "p6 p7 p8 p9 p10 p11")


class RigheFonti(unittest.TestCase):
    def test_solo_le_righe_con_un_url(self):
        righe = vc.righe_fonti(FONTIC)
        self.assertEqual([r["url"] for r in righe], [
            "https://istat.it/x", "https://bancaditalia.it/x",
        ])

    def test_le_celle_vanno_lette_per_nome_e_non_per_posizione_fissa(self):
        riga = vc.righe_fonti(FONTIC)[0]
        self.assertEqual(riga["voce"], "aggancio")
        self.assertEqual(riga["istituzione"], "30 settembre 2026")
        self.assertTrue(riga["citazione"].startswith("Il tasso di disoccupazione scende"))
        self.assertIn("Nazionale e provvisorio", riga["limite"])

    def test_la_riga_senza_url_non_e_una_fonte(self):
        self.assertEqual(len(vc.righe_fonti(FONTIC)), 2)

    def test_la_nota_di_chi_ha_preso_la_citazione_non_e_parte_di_essa(self):
        # Il file del pilota porta "(leader)" e "(leader, da una pista di
        # nemotron)": dentro la cella, dopo la virgoletta. Una riga vera non
        # deve risultare falsa per quello.
        with_nota = FONTIC.replace('al 18,9%." | Nazionale',
                                   'al 18,9%." (leader, da una pista) | Nazionale')
        self.assertEqual(vc.righe_fonti(with_nota)[0]["citazione"],
                         vc.righe_fonti(FONTIC)[0]["citazione"])


class Verifica(unittest.TestCase):
    """Il percorso intero, con uno scaricamento finto al posto della rete."""

    def test_un_url_non_aperto_non_e_una_citazione_falsa(self):
        path = _scrivi(FONTIC)
        righe = {r["url"]: r for r in vc.verifica(path, scarica_url=lambda u, timeout=60: (None, "http 403"))}
        for riga in righe.values():
            self.assertEqual(riga["esito"], vc.NON_APERTO)
            self.assertEqual(riga["motivo"], "http 403")

    def test_la_pagina_aperta_rende_trovata_e_non_trovata(self):
        path = _scrivi(FONTIC)
        righe = {
            r["url"]: r for r in vc.verifica(
                path, scarica_url=lambda u, timeout=60: (PAGINA, "html 320 byte")
            )
        }
        self.assertEqual(righe["https://istat.it/x"]["esito"], vc.TROVATA)
        self.assertEqual(righe["https://bancaditalia.it/x"]["esito"], vc.NON_TROVATA)

    def test_il_pdf_senza_pypdf_e_non_verificabile_non_falso(self):
        path = _scrivi(FONTIC)
        righe = {
            r["url"]: r for r in vc.verifica(
                path, scarica_url=lambda u, timeout=60: (None, "pdf, serve pypdf")
            )
        }
        for riga in righe.values():
            self.assertEqual(riga["esito"], vc.NON_VERIFICABILE)

    def test_un_url_si_scaria_una_volta_solo(self):
        chiamate = []

        def scarica(url, timeout=60):
            chiamate.append(url)
            return PAGINA, "html"

        vc.verifica(_scrivi(FONTIC_STESSO_URL), scarica_url=scarica)
        self.assertEqual(chiamate, ["https://istat.it/x"])

    def test_la_riga_senza_citazione_e_vuota_e_il_conte_esce(self):
        righe = vc.verifica(_scrivi(FONTIC_STESSO_URL), scarica_url=lambda u, timeout=60: (PAGINA, "html"))
        esiti = [r["esito"] for r in righe]
        self.assertEqual(esiti, [vc.TROVATA, vc.NON_TROVATA])

    def test_una_citazione_non_trovata_fa_uscire_con_codice_1(self):
        path = _scrivi(FONTIC)
        with mock.patch.object(vc, "scarica", return_value=(PAGINA, "html")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vc.main([str(path)]), 1)

    def test_un_tavolo_senza_url_esce_zero_e_lo_dice(self):
        path = _scrivi("# Fonti\n\nNessuna fonte.\n")
        with contextlib.redirect_stdout(io.StringIO()) as via:
            self.assertEqual(vc.main([str(path)]), 0)
        self.assertIn("vuoto", via.getvalue())


if __name__ == "__main__":
    unittest.main()
