"""L'impronta della prosa: che cosa identifica, e che cosa deve ignorare.

Il cruscotto la usa per dire se la pagina servita e' quella che l'ultima run ha
scritto. Prima confrontava le sole **parole**, e i conteggi non identificano un
testo: due riscritture della stessa lunghezza si leggevano `in linea` con
certezza `alta` mentre in produzione c'era ancora l'altra.

Le due proprieta' stanno insieme, e nessuna si legge guardando il codice:
cambia quando cambia una parola, e non cambia quando cambia solo un a capo,
perche' la run la stampa dall'oggetto in memoria e il sito la ricalcola dal JSON
riletto da disco.
"""

import json
import unittest

from app.editorial_state import impronta_prosa, parole

ENTRY = {
    "lead": "Il divario si chiude dall'alto, e non perche' il Sud corra.",
    "sections": [
        {"role": "quadro", "h": "Dove sta l'Italia", "body": "La distanza vale sedici punti."},
        {"role": "dinamica", "h": "Il decennio", "body": "In dieci anni il sale e' finito."},
    ],
    "key": "13", "level": "regione", "vintage": 2025,
}


def _con(percorso, valore):
    copia = json.loads(json.dumps(ENTRY))
    if percorso == "lead":
        copia["lead"] = valore
    else:
        indice, campo = percorso
        copia["sections"][indice][campo] = valore
    return copia


class LImprontaIdentificaIlTesto(unittest.TestCase):
    def test_una_parola_diversa_a_parita_di_conteggio(self):
        """`sale` che diventa `cale` lascia identiche parole e caratteri e
        ribalta il verso della frase: e' il caso esatto in cui il conteggio
        diceva `in linea`."""
        altra = _con((1, "body"), "In dieci anni il cale e' finito.")
        self.assertEqual(parole(altra), parole(ENTRY))
        self.assertNotEqual(impronta_prosa(altra), impronta_prosa(ENTRY))

    def test_un_titolo_riscritto_conta(self):
        """L'H2 e' prosa scritta da chi scrive, non un derivato: una pagina che
        cambia titolo alle sezioni non e' la pagina di prima."""
        self.assertNotEqual(impronta_prosa(_con((0, "h"), "Le due Italie")),
                            impronta_prosa(ENTRY))

    def test_due_sezioni_scambiate_non_sono_lo_stesso_articolo(self):
        """L'ordine e' una scelta editoriale e la pagina lo rende: entra."""
        scambiate = json.loads(json.dumps(ENTRY))
        scambiate["sections"].reverse()
        self.assertNotEqual(impronta_prosa(scambiate), impronta_prosa(ENTRY))

    def test_assorbire_la_definizione_cambia_la_pagina_senza_toccare_una_parola(self):
        """`roles_covered` decide se la definizione apre l'articolo o finisce nel
        blocco "Come leggere il dato": la stessa prosa rende due pagine diverse,
        e una che si legge "in linea" perche' le parole sono le stesse sarebbe un
        deploy in attesa invisibile."""
        assorbita = json.loads(json.dumps(ENTRY))
        assorbita["sections"].append(
            {"role": "definizione", "h": "Come si misura", "body": "Il rapporto fra due totali."})
        dichiarata = json.loads(json.dumps(assorbita))
        dichiarata["roles_covered"] = ["quadro", "dinamica", "limiti"]
        self.assertEqual(parole(dichiarata), parole(assorbita))
        self.assertNotEqual(impronta_prosa(dichiarata), impronta_prosa(assorbita))

    def test_lo_stesso_corpo_sotto_un_altro_ruolo(self):
        """Il ruolo decide dove la sezione finisce in pagina, quindi identifica
        l'articolo quanto il corpo."""
        self.assertNotEqual(impronta_prosa(_con((0, "role"), "limiti")),
                            impronta_prosa(ENTRY))


class LImprontaIgnoraCioCheNonESteso(unittest.TestCase):
    def test_gli_spazi_e_gli_a_capo_non_sono_una_riscrittura(self):
        """La run la stampa dall'oggetto in memoria, il sito la ricalcola dal
        JSON riletto: un a capo di differenza fra i due direbbe "non in linea"
        per sempre."""
        spaziata = _con((0, "body"), "La distanza\n  vale   sedici punti. ")
        self.assertEqual(impronta_prosa(spaziata), impronta_prosa(ENTRY))

    def test_i_campi_che_non_sono_prosa_non_entrano(self):
        """`vintage` e `level` sono campi di entry: cambiano senza che una
        parola cambi, e farli pesare qui direbbe "riscritto" a chi non ha
        riscritto niente."""
        altra = json.loads(json.dumps(ENTRY))
        altra["vintage"] = 2024
        altra["angolo_scelto"] = "una tesi diversa"
        self.assertEqual(impronta_prosa(altra), impronta_prosa(ENTRY))

    def test_un_giro_su_disco_non_la_muove(self):
        riletta = json.loads(json.dumps(ENTRY, ensure_ascii=False, indent=1, sort_keys=True))
        self.assertEqual(impronta_prosa(riletta), impronta_prosa(ENTRY))

    def test_un_articolo_che_non_esiste_non_ha_impronta_uguale_a_uno_vuoto(self):
        """Un'entry senza prosa e' un caso reale (un file scritto a mano a
        meta'), e non deve collidere con un articolo vero."""
        self.assertNotEqual(impronta_prosa({}), impronta_prosa(ENTRY))
        self.assertEqual(impronta_prosa({}), impronta_prosa({"sections": []}))


if __name__ == "__main__":
    unittest.main()
