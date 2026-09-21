"""Il titolo e la descrizione SERP derivati dai dati.

Prove pure: niente Flask, niente disco, niente catalogo. `meta` e `level` sono
i due dizionari che la vista passa, ridotti ai campi che il modulo legge, cosi'
un caso limite si scrive in tre righe invece che cercandolo fra 372 indicatori.

I casi non sono inventati: ognuno e' un difetto visto in produzione o un
guasto trovato scrivendo il modulo.
"""
import unittest

from app import seo_titles


def meta(name="PIL pro capite", unit="euro", institution="Istat", **extra):
    base = {"name": name, "value_unit": unit, "unit": unit,
            "institution": institution}
    base.update(extra)
    return base


def level(best=("Trentino Alto Adige", 54636.7), worst=("Calabria", 21702.2),
          key="regione", singular="regione", plural="regioni",
          year_max=2024, territory_total=20):
    def terr(pair):
        if pair is None:
            return None
        nome, valore = pair
        return {"key": nome.lower().replace(" ", "-"), "name": nome, "value": valore}
    return {"best": terr(best), "worst": terr(worst), "key": key,
            "singular": singular, "plural": plural, "year_max": year_max,
            "territory_total": territory_total}


class NumeriTest(unittest.TestCase):
    def test_le_migliaia_hanno_il_punto_e_nessun_decimale(self):
        """"34.343,0 euro" in SERP e' rumore: sopra il centinaio i decimali no."""
        self.assertEqual(seo_titles.format_number(34343.0), "34.343")
        self.assertEqual(seo_titles.format_number(54636.7), "54.637")

    def test_sotto_il_centinaio_il_decimale_porta_informazione(self):
        """"84,8 anni" senza decimale sarebbe una cifra diversa."""
        self.assertEqual(seo_titles.format_number(84.8), "84,8")
        self.assertEqual(seo_titles.format_number(2.00067), "2,0")

    def test_sotto_l_unita_servono_due_decimali(self):
        self.assertEqual(seo_titles.format_number(0.137), "0,14")

    def test_un_valore_che_non_e_un_numero_non_esplode(self):
        self.assertIsNone(seo_titles.format_number(None))
        self.assertIsNone(seo_titles.format_number("n.d."))


class EstremiTest(unittest.TestCase):
    def test_si_ordina_per_valore_non_per_merito(self):
        """Su `lower_better` il migliore e' il minimo, ma il titolo e' un
        intervallo: senza questo, meta' del catalogo leggerebbe al contrario."""
        lv = level(best=("Trentino Alto Adige", 2.0), worst=("Campania", 13.9))
        high, low = seo_titles.extremes(meta(), lv)
        self.assertEqual(high["name"], "Campania")
        self.assertEqual(low["name"], "Trentino Alto Adige")

    def test_senza_estremi_non_si_inventa_niente(self):
        """`contextual` non espone best/worst: su quelle serie un estremo non
        vuol dire niente, e la guardia non si aggira dal titolo."""
        self.assertEqual(seo_titles.extremes(meta(), level(best=None, worst=None)),
                         (None, None))


class TitoloTest(unittest.TestCase):
    def test_il_titolo_porta_misura_livello_e_intervallo(self):
        self.assertEqual(
            seo_titles.answer_title(meta(), level()),
            "PIL pro capite per regione, da 54.637 a 21.702 euro",
        )

    def test_la_coda_segue_il_livello_della_pagina(self):
        """`indicator_notes._TITLE_TAIL` e' fissa su " per regione" e finiva
        anche sopra dati provinciali. Qui la decide il livello."""
        lv = level(best=("Milano", 34343.0), worst=("Vibo Valentia", 13387.8),
                   key="provincia", singular="provincia", plural="province",
                   year_max=2023, territory_total=103)
        titolo = seo_titles.answer_title(meta(name="Retribuzione media annua"), lv)
        self.assertIn(" per provincia", titolo)
        self.assertNotIn(" per regione", titolo)

    def test_la_misura_si_accorcia_solo_a_una_giuntura(self):
        """Il taglio a caratteri consegnava tronconi, e li faceva collidere.

        "Differenza tra tasso di occupazione maschile e femminile" usciva come
        "Differenza tra tasso per regione", identico alla scheda del tasso di
        attivita'. Su 594 schede il taglio a budget ne mutilava 138. Ora o si
        taglia dove il nome ha una giuntura, o si rinuncia alle cifre.
        """
        nome = "Differenza tra tasso di occupazione maschile e femminile"
        lv = level(best=("Basilicata", 26.3), worst=("Valle d'Aosta", 6.1))
        titolo = seo_titles.answer_title(meta(name=nome, unit="%"), lv)
        self.assertNotIn("Differenza tra tasso per", titolo)
        self.assertIn(nome, titolo)

    def test_una_giuntura_vera_accorcia_e_lascia_spazio_alle_cifre(self):
        """Dove il nome ha una preposizione la testa regge da sola, e le cifre
        ci stanno: e' il caso che vale il 71% delle impression."""
        lv = level(best=("Milano", 34343.0), worst=("Vibo Valentia", 13387.8),
                   key="provincia", singular="provincia", plural="province",
                   year_max=2023, territory_total=103)
        nome = "Retribuzione media annua dei lavoratori dipendenti"
        titolo = seo_titles.answer_title(meta(name=nome, unit="euro"), lv)
        self.assertTrue(titolo.startswith("Retribuzione media annua"), titolo)
        self.assertIn(" per provincia", titolo)
        self.assertIn("34.343", titolo)
        self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)

    def test_la_percentuale_si_attacca_al_numero(self):
        lv = level(best=("Trentino Alto Adige", 2.0), worst=("Campania", 13.9))
        titolo = seo_titles.answer_title(meta(name="Tasso di disoccupazione", unit="%"), lv)
        self.assertEqual(titolo, "Tasso di disoccupazione per regione, dal 13,9% al 2,0%")

    def test_nessun_titolo_sfora_il_budget(self):
        lungo = ("Incidenza della spesa delle imprese in ricerca e sviluppo "
                 "sul prodotto interno lordo regionale")
        titolo = seo_titles.answer_title(meta(name=lungo), level())
        self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)

    def test_sopra_budget_cade_prima_l_unita_poi_la_coda(self):
        """Le cifre valgono piu' dell'unita', e l'unita' piu' della coda."""
        lungo = "Adulti che partecipano all'apprendimento permanente nel corso dell'anno"
        titolo = seo_titles.answer_title(meta(name=lungo), level())
        self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)
        self.assertIn("54.637", titolo)

    def test_la_misura_non_scende_sotto_il_minimo(self):
        """Un nome irriconoscibile non lo clicca nessuno neanche con un numero
        accanto: piuttosto si rinuncia alle cifre."""
        lv = level(best=("A", 123456789.0), worst=("B", 987654321.0))
        titolo = seo_titles.answer_title(meta(name="Prodotto interno lordo"), lv)
        self.assertTrue(titolo.startswith("Prodotto interno lordo"))

    def test_cio_che_distingue_sopravvive_al_taglio(self):
        """Tre serie della stessa famiglia differiscono solo in fondo al nome.
        Tagliando dalla testa uscivano con lo stesso `<title>`."""
        lv = level(best=None, worst=None)
        a = seo_titles.answer_title(
            meta(name="Famiglie con fonte principale di reddito da lavoro autonomo"), lv)
        b = seo_titles.answer_title(
            meta(name="Famiglie con fonte principale di reddito da lavoro dipendente"), lv)
        self.assertNotEqual(a, b)
        self.assertIn("autonomo", a)
        self.assertIn("dipendente", b)

    def test_mai_un_nome_tagliato_a_meta_parola(self):
        """`_compact_title` con poco spazio produceva "Sper (di vita alla
        nascita)": la testa va a finire in mezzo alla prima parola."""
        titolo = seo_titles.answer_title(meta(name="Speranza di vita alla nascita"), level())
        self.assertNotIn("Sper ", titolo)
        self.assertTrue(titolo.startswith("Speranza di vita"), titolo)

    def test_senza_estremi_resta_il_nome_e_il_livello(self):
        self.assertEqual(
            seo_titles.answer_title(meta(), level(best=None, worst=None)),
            "PIL pro capite per regione",
        )

    def test_due_estremi_uguali_non_fanno_un_intervallo(self):
        lv = level(best=("A", 10.0), worst=("B", 10.0))
        self.assertEqual(seo_titles.answer_title(meta(), lv), "PIL pro capite per regione")


class PrecedenzaTest(unittest.TestCase):
    def test_il_seo_title_scritto_vince_e_guadagna_le_cifre(self):
        titolo = seo_titles.page_title(
            {"seo_title": "PIL pro capite per regione"}, meta(), level(),
            site_name="Divario Italia")
        self.assertEqual(titolo, "PIL pro capite per regione, da 54.637 a 21.702 euro")

    def test_le_cifre_battono_la_marca(self):
        """Diciassette caratteri di un nome che in posizione 9,5 nessuno
        riconosce non comprano un clic. Google la marca la sintetizza da se'."""
        titolo = seo_titles.page_title(
            {"seo_title": "PIL pro capite per regione"}, meta(), level(),
            site_name="Divario Italia")
        self.assertNotIn("Divario Italia", titolo)

    def test_senza_cifre_la_marca_torna(self):
        titolo = seo_titles.page_title(
            {"seo_title": "PIL pro capite"}, meta(), level(best=None, worst=None),
            site_name="Divario Italia")
        self.assertEqual(titolo, "PIL pro capite · Divario Italia")

    def test_nessun_separatore_orfano(self):
        """Chiamare `authored_seo_title` con un nome vuoto lasciava un "·"
        appeso: "PIL pro capite per regione · , da 54.637 a 21.702"."""
        titolo = seo_titles.page_title(
            {"seo_title": "PIL pro capite per regione"}, meta(), level(),
            site_name="Divario Italia")
        self.assertNotIn("· ,", titolo)
        self.assertFalse(titolo.rstrip().endswith("·"))

    def test_un_h1_lungo_non_viene_mutilato_ma_scartato(self):
        """`_authored_short` affetta a caratteri dalla fine e produceva
        "Disoccupazione di lunga durata (rte dov'era piu' alta)". Meglio il
        titolo derivato, che almeno porta una cifra."""
        h1 = ("Disoccupazione di lunga durata, il divario fra le regioni "
              "si e' ristretto dove era piu' alta")
        titolo = seo_titles.page_title({"h1": h1}, meta(), level(),
                                       site_name="Divario Italia")
        self.assertNotIn("rte", titolo)
        self.assertIn("54.637", titolo)

    def test_un_h1_che_ci_sta_intero_si_usa(self):
        titolo = seo_titles.page_title({"h1": "Dove si vive piu' a lungo"},
                                       meta(), level(), site_name="Divario Italia")
        self.assertTrue(titolo.startswith("Dove si vive piu' a lungo"))

    def test_senza_articolo_si_deriva_dai_dati(self):
        titolo = seo_titles.page_title({}, meta(), level(), site_name="Divario Italia")
        self.assertEqual(titolo, "PIL pro capite per regione, da 54.637 a 21.702 euro")


class DescrizioneTest(unittest.TestCase):
    def test_l_attacco_del_pezzo_vince_su_tutto(self):
        attacco = "Nel 2024 in Calabria si sono prodotti 21.702 euro per abitante."
        self.assertIn("Calabria",
                      seo_titles.page_description({"lead": attacco}, meta(), level()))

    def test_senza_pezzo_escono_le_cifre_al_posto_della_formula_vuota(self):
        d = seo_titles.page_description({}, meta(), level())
        self.assertIn("54.637", d)
        self.assertIn("21.702", d)
        self.assertIn("20 regioni", d)
        self.assertIn("Istat", d)

    def test_la_preposizione_la_decide_il_livello(self):
        """"Calabria" e' una parola sola come "Milano": indovinare dalla forma
        produceva "a Calabria"."""
        self.assertIn("in Calabria", seo_titles.page_description({}, meta(), level()))
        prov = level(best=("Milano", 34343.0), worst=("Vibo Valentia", 13387.8),
                     key="provincia", singular="provincia", plural="province")
        self.assertIn("a Milano", seo_titles.page_description({}, meta(), prov))

    def test_gli_acronimi_restano_maiuscoli(self):
        """Minuscolare la prima lettera per attaccarla a un articolo produceva
        "pIL pro capite". La forma "Misura, anno: da X a Y" evita il problema."""
        d = seo_titles.page_description({}, meta(), level())
        self.assertTrue(d.startswith("PIL pro capite"))

    def test_la_descrizione_sta_nel_budget(self):
        lungo = ("Incidenza della spesa delle imprese pubbliche e private in "
                 "ricerca e sviluppo sul prodotto interno lordo regionale")
        d = seo_titles.page_description({}, meta(name=lungo), level())
        self.assertLessEqual(len(d), seo_titles.DESCRIPTION_MAX)

    def test_senza_cifre_si_ripiega_sul_lead_composto(self):
        composto = "Una frase generata dal sito."
        d = seo_titles.page_description({}, meta(), level(best=None, worst=None),
                                        composed=composto)
        self.assertIn("generata dal sito", d)


class CaratteriVietatiTest(unittest.TestCase):
    """Le regole di `content/STYLE.md` valgono anche sul testo che va in SERP."""

    VIETATI = ("—", "–", ";", "…")

    def test_ne_il_titolo_ne_la_descrizione_li_contengono(self):
        casi = [
            (meta(), level()),
            (meta(name="Tasso di disoccupazione", unit="%"),
             level(best=("Trentino Alto Adige", 2.0), worst=("Campania", 13.9))),
            (meta(name="Retribuzione media annua dei lavoratori dipendenti"),
             level(best=("Milano", 34343.0), worst=("Vibo Valentia", 13387.8),
                   key="provincia", singular="provincia", plural="province")),
        ]
        for m, lv in casi:
            for testo in (seo_titles.answer_title(m, lv),
                          seo_titles.answer_description(m, lv)):
                for c in self.VIETATI:
                    with self.subTest(testo=testo, carattere=c):
                        self.assertNotIn(c, testo or "")


if __name__ == "__main__":
    unittest.main()
