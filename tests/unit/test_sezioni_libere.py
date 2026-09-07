"""La forma libera: un articolo che non fa le quattro fermate obbligate.

I quattro ruoli (`definizione`, `quadro`, `dinamica`, `limiti`) sono la forma
dei dati, non la forma di un racconto: obbligano ogni pezzo a passare dagli
stessi quattro titoli nello stesso ordine, qualunque cosa i dati abbiano da
dire. Una sezione `libera` porta il proprio titolo, sta dove l'autore l'ha
messa, e non ha nessuno scheletro dietro.

Le due garanzie che contano, e sono garanzie opposte:

1. **I trecento articoli a quattro ruoli non si muovono di un pixel.** La forma
   libera e' un'aggiunta, non un allentamento: se una sola di queste asserzioni
   cade, il cambiamento ha toccato pagine che nessuno voleva toccare.
2. **Un articolo libero risulta completo**, alla pagina e alla lista di
   consegna. Se `pending_notes` non lo sa, il produttore lo rilancia a ogni
   giro chiedendo sezioni che quell'articolo ha deciso di non avere.
"""

import unittest

from app import indicator_texts
from scripts import pending_notes


def libera(titolo, corpo="Un corpo qualsiasi."):
    return {"role": "libera", "h": titolo, "body": corpo}


class LaFormaLiberaVinceSuTutto(unittest.TestCase):
    def test_le_sezioni_sono_quelle_scritte_nel_loro_ordine(self):
        entry = {"sections": [libera("Il seggio non è la poltrona"),
                              libera("Chi sale e chi torna indietro")]}
        self.assertEqual(indicator_texts.emitted_roles(entry), ["libera", "libera"])

    def test_nessun_ruolo_sostanziale_si_aggiunge(self):
        # E' la differenza con `roles_covered`, che invece unisce sempre i tre
        # sostanziali: qui non c'e' niente da completare.
        entry = {"sections": [libera("Una sola sezione")]}
        emessi = indicator_texts.emitted_roles(entry)
        self.assertNotIn("quadro", emessi)
        self.assertNotIn("limiti", emessi)

    def test_una_dichiarazione_roles_covered_non_la_ribalta(self):
        entry = {"roles_covered": ["quadro", "limiti"],
                 "sections": [libera("Comanda la sezione, non la dichiarazione")]}
        self.assertEqual(indicator_texts.emitted_roles(entry), ["libera"])

    def test_si_puo_mescolare_con_un_ruolo_di_sempre(self):
        entry = {"sections": [libera("Apro io"), {"role": "limiti", "h": "Limiti", "body": "x"}]}
        self.assertEqual(indicator_texts.emitted_roles(entry), ["libera", "limiti"])

    def test_una_sezione_libera_senza_titolo_non_esiste(self):
        # La pagina non ha un titolo di scorta da darle, e un H2 vuoto e' peggio
        # di una sezione in meno.
        entry = {"sections": [{"role": "libera", "h": "  ", "body": "x"},
                              {"role": "quadro", "h": "Q", "body": "y"},
                              {"role": "dinamica", "h": "D", "body": "z"},
                              {"role": "limiti", "h": "L", "body": "w"}]}
        self.assertNotIn("libera", indicator_texts.emitted_roles(entry))


class IQuattroRuoliNonSiMuovono(unittest.TestCase):
    def test_un_articolo_di_sempre_rende_i_quattro_ruoli(self):
        entry = {"sections": [{"role": "quadro", "h": "Q", "body": "x"}]}
        self.assertEqual(indicator_texts.emitted_roles(entry),
                         ["definizione", "quadro", "dinamica", "limiti"])

    def test_un_entry_vuota_rende_i_quattro_ruoli(self):
        self.assertEqual(indicator_texts.emitted_roles({}),
                         ["definizione", "quadro", "dinamica", "limiti"])

    def test_roles_covered_continua_a_unire_i_sostanziali(self):
        entry = {"roles_covered": ["quadro"]}
        emessi = indicator_texts.emitted_roles(entry)
        self.assertNotIn("definizione", emessi)
        self.assertEqual(set(emessi), {"quadro", "dinamica", "limiti"})


class LAncora(unittest.TestCase):
    def test_nasce_dal_titolo_non_dal_ruolo(self):
        # `libera`, `libera-2`, `libera-3` non dicono niente a chi condivide un
        # link, e cambiano appena qualcuno riordina il pezzo.
        self.assertEqual(indicator_texts._ancora("Il seggio non è la poltrona"),
                         "il-seggio-non-e-la-poltrona")

    def test_regge_un_titolo_senza_lettere(self):
        self.assertEqual(indicator_texts._ancora("...!"), "sezione")


class LaListaDiConsegnaLoSa(unittest.TestCase):
    """Lo specchio stdlib in `scripts/pending_notes` deve rispondere lo stesso."""

    def test_un_articolo_libero_non_ha_ruoli_mancanti(self):
        entry = {"sections": [libera("Una"), libera("Due")]}
        self.assertEqual(pending_notes.unwritten_roles(entry), [])

    def test_i_due_specchi_rispondono_lo_stesso_sulla_forma_libera(self):
        entry = {"sections": [libera("Una"), {"role": "limiti", "h": "L", "body": "x"}]}
        self.assertEqual(indicator_texts.emitted_roles(entry), pending_notes.emitted_roles(entry))

    def test_i_due_specchi_rispondono_lo_stesso_sui_quattro_ruoli(self):
        for entry in ({}, {"roles_covered": ["quadro"]}, {"roles_covered": []},
                      {"sections": [{"role": "quadro", "h": "Q", "body": "x"}]}):
            self.assertEqual(set(indicator_texts.emitted_roles(entry)),
                             set(pending_notes.emitted_roles(entry)), entry)


if __name__ == "__main__":
    unittest.main()
