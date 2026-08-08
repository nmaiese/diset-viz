"""Chi sceglie da solo che cosa scrivere, e che cosa non sceglie mai.

`lab.dossier.da_coda` è il ramo automatico della catena minima: senza codici in
`args`, il workflow gli chiede lui quale indicatore rifare. Un articolo che
questa funzione salta non viene mai scritto e non lo dice nessuno, quindi il
filtro va provato e non riletto.

Non si prova sul catalogo vero: sul catalogo vero **nessun articolo è arretrato**
(zero righe `stale` su 668), che è esattamente la ragione per cui il difetto è
rimasto invisibile. Il predicato sbagliato (`written < sections`) e quello
giusto restituiscono oggi lo stesso identico insieme di 96 righe. Si prova quindi
su una coda finta che contiene i casi che i dati di oggi non producono, e che
i dati di domani produrranno tutti insieme il giorno di un rilascio Istat.
"""

import unittest
from unittest import mock

from lab import dossier


def _riga(codice, **cambia):
    """Una riga di `lab.coda.build_queue`, completa e sana salvo ciò che cambi.

    `written` si deriva da `missing` come fa `lab.coda.assess` invece di essere
    un numero fisso: una riga con una sezione mancante e `written == sections`
    non esiste in natura, e provare il filtro contro un dato impossibile
    proverebbe solo che il dato è impossibile.
    """
    riga = {"code": codice, "level": "regione", "default_level": "regione",
            "name": f"nome di {codice}",
            "year_max": 2025, "score": 10, "indexable": True,
            "stale": False, "lead": True, "missing": [],
            "sections": 4, "vintage": 2025}
    riga.update(cambia)
    riga["written"] = riga["sections"] - len(riga["missing"])
    return riga


class LaCodaAutomatica(unittest.TestCase):
    def _scelti(self, righe, quanti=10, anno=2025):
        """Il livello di default lo porta la riga (`default_level`), come nella
        coda vera: prima `da_coda` montava una vista per candidata solo per
        chiederglielo, cioè rifaceva un pezzo della passata già fatta."""
        with mock.patch("lab.coda.build_queue", return_value=righe):
            return [voce["codice"] for voce in dossier.da_coda(quanti, anno)]

    def test_un_articolo_completo_ma_arretrato_e_il_primo_da_rifare(self):
        """È il caso che vale `+100` nella coda, contro il `10` di una sezione
        mancante: cifre più vecchie del dato sono sbagliate, una sezione assente
        è solo scarna. Escluderlo perché `written == sections` significa saltare
        proprio la testa della coda."""
        self.assertEqual(
            self._scelti([_riga("ter-1", stale=True, vintage=2023, score=110)]),
            ["ter-1"])

    def test_un_articolo_a_cui_manca_solo_il_lead_resta_in_coda(self):
        """Il lead è la meta description della pagina. Tutte le sezioni scritte
        e nessun lead è un articolo incompleto in ciò che il motore legge per
        primo."""
        self.assertEqual(self._scelti([_riga("ter-2", lead=False, score=50)]),
                         ["ter-2"])

    def test_un_articolo_intero_e_fresco_non_torna(self):
        self.assertEqual(self._scelti([_riga("ter-3")]), [])

    def test_le_sezioni_mancanti_restano_il_caso_di_sempre(self):
        self.assertEqual(
            self._scelti([_riga("ter-4", missing=["limiti"])]),
            ["ter-4"])

    def test_i_due_filtri_della_lite_valgono_ancora(self):
        """Freschezza e indicizzabilità: una pagina che nessuno può trovare non
        vale il costo di una run, e un dato vecchio non è la storia di adesso."""
        righe = [_riga("ter-5", missing=["limiti"], indexable=False),
                 _riga("ter-6", missing=["limiti"], year_max=2019),
                 _riga("ter-7", missing=["limiti"])]
        self.assertEqual(self._scelti(righe), ["ter-7"])

    def test_ne_prende_quanti_ne_chiedi_nell_ordine_della_coda(self):
        righe = [_riga("ter-8", stale=True), _riga("ter-9", lead=False),
                 _riga("ter-10", missing=["quadro"])]
        self.assertEqual(self._scelti(righe, quanti=2), ["ter-8", "ter-9"])


class IlLivelloDeveEssereQuelloDiDefault(unittest.TestCase):
    """`content/indicators/` ha un file per **indicatore**, non per coppia.

    Un articolo provinciale di un indicatore che di default è regionale
    finirebbe nello stesso `<key>.json` di quello regionale. Non si
    aggiungerebbe: lo sostituirebbe, e siccome la pagina sceglie che cosa
    rendere leggendo `level`, la prosa regionale smetterebbe di comparire senza
    che niente diventi rosso.

    Non è provabile sui dati veri: oggi tutte e 96 le righe selezionabili sono
    `regione`, e le 34 righe con livello diverso dal default non passano il
    filtro sull'anno. Il giorno in cui lo passeranno, questo test è l'unica cosa
    che c'è fra loro e una pagina riscritta al livello sbagliato.
    """

    def _scelti(self, righe):
        with mock.patch("lab.coda.build_queue", return_value=righe):
            return [voce["codice"] for voce in dossier.da_coda(10, 2025)]

    def test_una_riga_provinciale_di_un_indicatore_regionale_non_si_sceglie(self):
        righe = [_riga("ter-11", level="provincia", default_level="regione",
                       missing=["limiti"])]
        self.assertEqual(self._scelti(righe), [])

    def test_una_riga_provinciale_di_un_indicatore_provinciale_si_sceglie(self):
        """Il filtro giusto è "livello == default", non "salta le province": 33
        delle 67 righe provinciali della coda sono di indicatori che di default
        **sono** provinciali, e per quelle non c'è nessuna collisione."""
        righe = [_riga("ter-12", level="provincia", default_level="provincia",
                       missing=["limiti"])]
        self.assertEqual(self._scelti(righe), ["ter-12"])

    def test_un_indicatore_senza_livello_di_default_resta_fuori(self):
        """`default_level` nullo non coincide con nessun livello, quindi
        esclude: è il verso giusto del dubbio."""
        righe = [_riga("ter-13", default_level=None, missing=["limiti"])]
        self.assertEqual(self._scelti(righe), [])

    def test_una_riga_scartata_non_consuma_il_posto_di_quelle_buone(self):
        """Il filtro vive dentro il ciclo che conta fino a `quanti`: se
        tagliasse dopo, una riga scartata lascerebbe la lista corta."""
        righe = [_riga("ter-14", level="provincia", default_level="regione",
                       missing=["limiti"]),
                 _riga("ter-15", missing=["limiti"])]
        self.assertEqual(self._scelti(righe), ["ter-15"])


if __name__ == "__main__":
    unittest.main()
