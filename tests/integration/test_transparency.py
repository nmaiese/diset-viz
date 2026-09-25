"""Come nasce il testo, e dove la pagina lo dice.

Fino al 22 settembre 2026 in fondo a ogni scheda con prosa c'era questa frase:
"Il testo di questa scheda e' scritto automaticamente ... e pubblicato senza
riscrittura umana". Era vera, ed era li' per l'articolo 50(4) del regolamento
europeo sull'intelligenza artificiale, in vigore dal 2 agosto 2026: chi pubblica
un testo "with the purpose of informing the public on matters of public
interest" deve dichiarare che e' generato, e l'esenzione del comma 4 e'
**cumulativa**, cioe' chiede "human review **or editorial control**" E una
persona fisica o giuridica che detenga la responsabilita' editoriale.

Adesso il controllo editoriale c'e': nessuna scheda va online senza che una
persona approvi la proposta di modifica che la porta, e quella persona risponde
di quello che si legge. L'esenzione si applica, e la vecchia frase descriveva un
processo che non esiste piu'.

Queste prove difendono la verita' nuova, non le vecchie stringhe. Tre cose,
nell'ordine in cui contano:

1. la frase vecchia non e' piu' servita da nessuna pagina, perche' dire di se'
   di essere contenuto prodotto in serie e mai riletto e' falso e costa caro;
2. la pagina dichiara come e' fatta comunque, e dice cose diverse quando il
   testo e' scritto da un modello e quando e' composto dal codice sui dati
   della fonte, perche' chiamare generata la seconda sarebbe impreciso in
   eccesso;
3. la pagina di metodo continua a dire anche che cosa il controllo **non**
   garantisce, e continua a rifiutare le firme di redattori che non esistono.

Il blocco sta nel guscio (`indicator_page.html`) e non nel JSON degli articoli,
come prima stava nel template dell'articolo: cosi' copre trecentottantatre file
senza toccarne una riga di prosa.
"""
import re
import unittest

from app import app
from scripts import indicator_store


# La frase che il sito non deve piu' dire di se'.
VECCHIE = ("senza riscrittura umana", "scritto automaticamente")


def _codici_indicizzabili(quanti):
    from app import indicator_universe
    codici = []
    for vista in indicator_universe.indexable_catalog():
        meta = vista["meta"]
        codici.append(meta["canonical_path"])
        if len(codici) >= quanti:
            break
    return codici


class LaFraseVecchiaNonEPiuServita(unittest.TestCase):
    """E' la prova che difende il risultato, non solo la correttezza.

    Un campione, non una pagina: la frase stava in un template incluso da
    tutte, quindi un ritorno la riporterebbe su tutte insieme.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_nessuna_scheda_del_campione_confessa_di_non_essere_riletta(self):
        for percorso in _codici_indicizzabili(12):
            with self.subTest(percorso=percorso):
                pagina = self.client.get(percorso, follow_redirects=True)
                self.assertEqual(pagina.status_code, 200, percorso)
                testo = pagina.get_data(as_text=True)
                for frase in VECCHIE:
                    self.assertNotIn(frase, testo)

    def test_nessun_template_la_rende_piu(self):
        """I commenti Jinja non contano, e non e' un cavillo.

        Il commento di `_indicator_article.html` cita la frase vecchia per
        dire perche' non c'e' piu': e' la memoria del cambiamento, sta nel
        sorgente e non esce dal render. Vietare la stringa ovunque
        obbligherebbe a cancellare la spiegazione per far passare la prova.
        """
        from pathlib import Path
        radice = Path(__file__).resolve().parents[2] / "app" / "templates"
        for template in sorted(radice.rglob("*.html")):
            reso = re.sub(r"\{#.*?#\}", "", template.read_text(encoding="utf-8"), flags=re.S)
            for frase in VECCHIE:
                with self.subTest(template=template.name, frase=frase):
                    self.assertNotIn(frase, reso)


class LaSchedaDiceComeENata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def _pagina(self, code):
        risposta = self.client.get(f"/indicatore/x/{code}", follow_redirects=True)
        self.assertEqual(risposta.status_code, 200, code)
        return risposta.get_data(as_text=True)

    def test_una_scheda_con_prosa_dice_che_una_persona_la_approva(self):
        pagina = self._pagina("ter-176")
        self.assertIn("Come nasce questa scheda", pagina)
        from app import publisher
        self.assertIn(f"lo approva {publisher.EDITOR_NAME}", pagina)

    def test_una_scheda_composta_dal_codice_non_si_dichiara_generata(self):
        """Le sezioni composte sono template deterministici sui dati della
        fonte. Dichiararle scritte da un modello sarebbe impreciso in eccesso,
        e su una pagina di dati pubblici l'imprecisione in eccesso costa
        fiducia quanto quella in difetto.

        L'indicatore si sceglie a run-time fra quelli senza articolo firmato:
        fissarne uno a mano vorrebbe dire che la prova fallisce il giorno in
        cui la catena lo scrive, cioe' per il motivo giusto ma col messaggio
        sbagliato.
        """
        scritti = set(indicator_store.load_all())
        for raw in ("120", "30", "45", "60", "72", "88", "140"):
            if raw in scritti:
                continue
            risposta = self.client.get(f"/indicatore/x/ter-{raw}", follow_redirects=True)
            if risposta.status_code != 200:
                continue
            pagina = risposta.get_data(as_text=True)
            self.assertIn("costruito sui dati della fonte", pagina)
            self.assertNotIn("lo approva", pagina)
            return
        self.skipTest("nessun indicatore senza articolo firmato fra quelli provati")

    def test_rimanda_alla_pagina_che_lo_spiega(self):
        self.assertIn("/metodologia#come-nasce-il-testo", self._pagina("ter-176"))

    def test_dice_che_le_cifre_sono_ricalcolate_non_congelate(self):
        self.assertIn("ricalcolate dal codice a ogni caricamento", self._pagina("ter-176"))


class LaPaginaDiMetodo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = app.test_client().get("/metodologia").get_data(as_text=True)

    def test_l_ancora_a_cui_puntano_le_schede_esiste(self):
        self.assertIn('id="come-nasce-il-testo"', self.page)

    def test_separa_cio_che_e_generato_da_cio_che_non_lo_e(self):
        self.assertIn("I dati non sono generati", self.page)

    def test_dice_che_cosa_viene_verificato(self):
        self.assertIn("riverificata contro il valore vero", self.page)

    def test_dice_che_niente_va_online_senza_una_persona(self):
        """E' la frase che regge l'esenzione del comma 4, quindi o e' vera e
        sta scritta, o la dichiarazione di generazione deve tornare."""
        self.assertIn("Niente arriva online da solo", self.page)
        self.assertIn("approva", self.page)

    def test_dice_anche_che_cosa_il_controllo_non_garantisce(self):
        """Una pagina di metodo che elenca solo le garanzie e' marketing."""
        self.assertIn("non garantisce", self.page)
        self.assertIn("non una dimostrazione", self.page)

    def test_nomina_una_responsabilita_e_rifiuta_le_firme_inventate(self):
        """Un nome finto non e' una persona che detiene responsabilita'
        editoriale: la simula. E le linee guida di Google danno il rating
        minimo a una pagina che attribuisce il contenuto a una fonte fittizia
        "even if the page assigns credit for the content to another source".
        """
        self.assertIn("responsabilità editoriale", self.page)
        self.assertIn("non firmiamo le schede con nomi di redattori che non esistono",
                      self.page.lower())

    def test_manda_a_chi_siamo_e_non_alla_pagina_che_non_esiste(self):
        self.assertIn('href="/chi-siamo"', self.page)
        self.assertNotIn('href="/about"', self.page)


class IlBloccoStaNelGuscioNonNegliArticoli(unittest.TestCase):
    def test_la_riga_viene_dal_template_non_dal_file_dell_articolo(self):
        """Se stesse nei file degli articoli, cambiarla vorrebbe dire
        riscriverne trecentottantatre."""
        from pathlib import Path
        guscio = (Path(__file__).resolve().parents[2]
                  / "app" / "templates" / "indicator_page.html").read_text(encoding="utf-8")
        self.assertIn("Come nasce questa scheda", guscio)

    def test_nessun_articolo_committato_porta_la_dichiarazione_nella_prosa(self):
        """Questa prova girava a vuoto.

        Faceva `glob("content/indicators/*.json")`, e in quella cartella ci
        sono trecentottantatre file `.md` e zero `.json` dal travaso a
        Markdown: cicla su una lista vuota e passa sempre. La guardia che
        doveva impedire alla dichiarazione di finire dentro la prosa non
        guardava niente. Ora legge gli articoli dallo store.
        """
        articoli = indicator_store.load_all()
        self.assertGreater(len(articoli), 300, "lo store non sta leggendo gli articoli")
        for chiave, voce in sorted(articoli.items()):
            testo = " ".join(
                [voce.get("lead") or ""]
                + [(s.get("body") or "") + " " + (s.get("h") or "") for s in voce.get("sections") or []]
            )
            for frase in VECCHIE + ("Come nasce questa scheda",):
                with self.subTest(articolo=chiave, frase=frase):
                    self.assertNotIn(
                        frase, testo,
                        f"{chiave} ha la dichiarazione nella prosa invece che nel guscio")


if __name__ == "__main__":
    unittest.main()
