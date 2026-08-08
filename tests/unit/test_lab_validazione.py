"""I controlli che rifiutano una bozza: quello che devono fermare, e quello che
non devono fermare.

Fermano il file: se uno di questi resta, `lab.pubblica` non scrive, e finche'
giravano solo li' una run intera si perdeva senza che nessuno correggesse
niente. Adesso li esegue anche `lab.controlla`, cioe' il verificatore, dove il
testo si puo' ancora riparare: e allora un falso positivo non e' piu' una noia,
diventa una correzione chiesta su una frase giusta.
"""

import unittest

from lab.validazione import accenti, bloccanti


def sezione(testo, ruolo="quadro", titolo="Un titolo"):
    return {"lead": "Un lead che apre.", "sections": [{"role": ruolo, "h": titolo, "body": testo}]}


class LAccentoScrittoComeApostrofo(unittest.TestCase):
    def test_la_parola_col_difetto_viene_segnalata(self):
        """`poverta'` su una pagina pubblica e' italiano sbagliato, e il difetto
        non nasce da una svista: nasce dall'imitazione delle istruzioni, che
        sono scritte cosi'."""
        problemi = accenti(sezione("La poverta' cresce, e perche' non si sa."))
        self.assertEqual(len(problemi), 1)
        self.assertIn("poverta'", problemi[0])
        self.assertIn("perche'", problemi[0])

    def test_il_difetto_nel_titolo_conta_come_nel_corpo(self):
        self.assertTrue(accenti(sezione("Corpo pulito.", titolo="Dove la poverta' morde")))

    def test_una_citazione_fra_apici_non_e_un_accento(self):
        """Il caso che ha fermato una run vera: `'non adeguata'` e' una frase
        citata, e il secondo apice sta dopo una vocale come l'errore che questa
        guardia cerca. Con la sola regex erano indistinguibili."""
        self.assertEqual(
            accenti(sezione("Gli studenti in fascia 'non adeguata' sono uno su tre.")), [])

    def test_una_citazione_e_un_accento_sbagliato_nella_stessa_frase(self):
        """La citazione non fa da scudo al resto: il conteggio deve restare
        vero anche quando le due cose stanno vicine."""
        problemi = accenti(sezione("La quota 'non adeguata' e' cresciuta, e la poverta' pure."))
        self.assertEqual(len(problemi), 1)
        self.assertIn("poverta'", problemi[0])
        self.assertNotIn("adeguata'", problemi[0])

    def test_le_elisioni_non_c_entrano(self):
        self.assertEqual(accenti(sezione("L'anno dell'indagine, nell'area dell'obbligo.")), [])

    def test_il_troncamento_e_gli_imperativi_restano(self):
        """`po'` e `va'` sono italiano giusto. `piu'` no, e infatti non sta in
        questa lista: la forma e' `più`."""
        self.assertEqual(accenti(sezione("Un po' meno, e va' avanti.")), [])
        self.assertTrue(accenti(sezione("Un po' piu' basso di prima.")))


class CioCheRendeIlFileNonScrivibile(unittest.TestCase):
    def test_una_bozza_sana_non_ha_bloccanti(self):
        self.assertEqual(bloccanti(sezione("Una prosa qualunque, senza difetti.")), [])

    def test_senza_lead_non_si_scrive(self):
        bozza = sezione("Corpo.")
        bozza["lead"] = "   "
        self.assertIn("manca il lead", bloccanti(bozza))

    def test_un_ruolo_che_la_pagina_non_rende(self):
        """Una sezione con un ruolo sconosciuto verrebbe scartata in silenzio
        dal template: l'articolo perderebbe un pezzo senza che niente fallisca."""
        problemi = bloccanti(sezione("Corpo.", ruolo="contesto"))
        self.assertTrue(any("contesto" in p for p in problemi), problemi)

    def test_una_fonte_senza_url(self):
        bozza = sezione("Corpo.")
        bozza["fonti"] = [{"testo": "una citazione", "url": ""}]
        self.assertTrue(any("fonte 0" in p for p in bloccanti(bozza)))


if __name__ == "__main__":
    unittest.main()
