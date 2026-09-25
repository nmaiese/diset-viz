"""Il titolo e la descrizione SERP derivati dai dati.

Prove pure: niente Flask, niente disco, niente catalogo. `meta` e `level` sono
i due dizionari che la vista passa, ridotti ai campi che il modulo legge, cosi'
un caso limite si scrive in tre righe invece che cercandolo fra 372 indicatori.

I casi non sono inventati: ognuno e' un difetto visto in produzione o un
guasto trovato scrivendo il modulo.
"""
import unittest

from app import seo_titles
from app.design import common, numfmt


def meta(name="PIL pro capite", unit="euro", institution="Istat", **extra):
    base = {"name": name, "value_unit": unit, "unit": unit,
            "institution": institution}
    base.update(extra)
    return base


def level(best=("Trentino Alto Adige", 54636.7), worst=("Calabria", 21702.2),
          key="regione", singular="regione", plural="regioni",
          year_max=2024, territory_total=20, observations=None):
    def terr(pair):
        if pair is None:
            return None
        nome, valore = pair
        return {"key": nome.lower().replace(" ", "-"), "name": nome, "value": valore}
    base = {"best": terr(best), "worst": terr(worst), "key": key,
            "singular": singular, "plural": plural, "year_max": year_max,
            "territory_total": territory_total}
    if observations is not None:
        base["observations"] = [terr(pair) for pair in observations]
    return base


def provincia(best, worst, **extra):
    return level(best=best, worst=worst, key="provincia", singular="provincia",
                 plural="province", territory_total=107, **extra)


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

    def test_lo_zero_si_scrive_zero(self):
        """"0,00" dava allo zero una precisione che non ha: in SERP si leggeva
        "dal 358% al 0,00%" e "da 3,4 a 0,00"."""
        self.assertEqual(seo_titles.format_number(0), "0")
        self.assertEqual(seo_titles.format_number(0.0), "0")
        self.assertEqual(seo_titles.format_number(-0.0), "0")
        self.assertEqual(seo_titles.format_number(0.10), "0,10")


# cifra -> (da, a, di): la preposizione la decide come la cifra si legge.
ELISIONI = {
    "89,1": ("dall'", "all'", "dell'"),     # ottantanove
    "8.000": ("dall'", "all'", "dell'"),    # ottomila
    "8": ("dall'", "all'", "dell'"),
    "1,1": ("dall'", "all'", "dell'"),      # uno virgola uno
    "1": ("dall'", "all'", "dell'"),
    "11": ("dall'", "all'", "dell'"),       # undici
    "11,3": ("dall'", "all'", "dell'"),
    "11.000": ("dall'", "all'", "dell'"),   # undicimila
    "116": ("dal ", "al ", "del "),         # centosedici, non "dell'116"
    "110": ("dal ", "al ", "del "),
    "1.022": ("dal ", "al ", "del "),       # milleventidue
    "18": ("dal ", "al ", "del "),
    "0,10": ("dallo ", "allo ", "dello "),  # zero
    "0": ("dallo ", "allo ", "dello "),
    "-64,7": ("dal ", "al ", "del "),       # meno
    "3,6": ("dal ", "al ", "del "),
}


class ElisioneTest(unittest.TestCase):
    """`numfmt.articulated`: la preposizione la decide come la cifra si legge."""

    def test_ogni_forma(self):
        for cifra, (da, a, di) in ELISIONI.items():
            with self.subTest(cifra=cifra):
                self.assertEqual(numfmt.articulated("da", cifra), da)
                self.assertEqual(numfmt.articulated("a", cifra), a)
                self.assertEqual(numfmt.articulated("di", cifra), di)
                self.assertEqual(numfmt.articulated("di", f"{cifra}%"), di)

    def test_le_frasi_della_scheda_usano_la_stessa_regola(self):
        """`common.del_` aveva la sua: vedeva "11" in testa a 116."""
        self.assertEqual(common.del_("116%"), "del ")
        self.assertEqual(common.del_("11,3%"), "dell'")
        self.assertEqual(common.del_("0,5%"), "dello ")

    def test_il_titolo_articola_l_intervallo(self):
        casi = {
            (89.1, 36.7): ", dall'89,1% al 36,7%",
            (116.0, 3.9): ", dal 116% al 3,9%",
            (0.94, -2.6): ", dallo 0,94% al -2,6%",
            (18.5, 0.22): ", dal 18,5% allo 0,22%",
            (82.0, 0.0): ", dall'82,0% allo 0%",
            (11.9, 1.3): ", dall'11,9% all'1,3%",
        }
        for (alto, basso), atteso in casi.items():
            with self.subTest(atteso=atteso):
                lv = level(best=("A", alto), worst=("B", basso))
                self.assertEqual(seo_titles._figures(meta(unit="%"), lv)[0], atteso)

    def test_se_l_articolo_sfora_si_scrive_senza_e_la_coda_resta(self):
        """"dallo" e "allo" costano due caratteri: un titolo che stava nei 60
        con "dal" non deve perdere la coda del livello per colpa loro."""
        lv = level(best=("A", 0.79), worst=("B", 0.01))
        titolo = seo_titles.answer_title(meta(name="Superficie boscata percorsa", unit="%"), lv)
        self.assertEqual(titolo, "Superficie boscata percorsa per regione, da 0,79% a 0,01%")

    def test_l_articolo_non_sposta_la_scelta_dei_sacrifici(self):
        """Un nome che senza coda ci stava con "dal" non guadagna la coda con la
        forma senza articolo: l'ordine dei sacrifici resta quello di prima."""
        # 32 caratteri: con la coda ci starebbe "da 82,0% a 0%", non "dal 82,0% al 0%".
        nome = "Quota di rifiuti urbani smaltiti"
        lv = level(best=("A", 82.0), worst=("B", 0.0))
        titolo = seo_titles.answer_title(meta(name=nome, unit="%"), lv)
        self.assertEqual(titolo, "Quota di rifiuti urbani smaltiti, dall'82,0% allo 0%")


class UnitaTest(unittest.TestCase):
    def test_l_unita_breve_viene_da_numfmt(self):
        """"Numero medio di anni" era troppo lunga per il titolo, e la cifra
        restava senza unita'. `numfmt.short_unit` la riduce ad "anni"."""
        lv = level(best=("Trentino Alto Adige", 84.8), worst=("Campania", 82.1))
        titolo = seo_titles.answer_title(meta(name="Speranza di vita", unit="Numero medio di anni"), lv)
        self.assertEqual(titolo, "Speranza di vita per regione, da 84,8 a 82,1 anni")

    def test_un_etichetta_che_non_e_un_unita_non_si_scrive(self):
        """"da 0,35 a 0,27 indice" e "da 5,6 a 3,8 rapporto" erano in produzione."""
        lv = level(best=("A", 0.35), worst=("B", 0.27))
        titolo = seo_titles.answer_title(meta(name="Indice di Gini", unit="indice"), lv)
        self.assertEqual(titolo, "Indice di Gini per regione, da 0,35 a 0,27")


class GuardiaTest(unittest.TestCase):
    """`_keeps_meaning`: un accorciamento che dice un'altra cosa vale meno del
    nome intero senza cifre."""

    def test_mai_una_parola_sola(self):
        nome = "Impermeabilizzazione del suolo da copertura artificiale"
        titolo = seo_titles.answer_title(meta(name=nome, unit="%"),
                                         provincia(("Napoli", 40.8), ("Aosta", 2.2)))
        self.assertFalse(titolo.startswith("Impermeabilizzazione per"), titolo)
        self.assertTrue(titolo.startswith("Impermeabilizzazione del suolo"), titolo)

    def test_una_negazione_non_si_butta(self):
        nome = ("Ospiti anziani non autosufficienti dei presidi residenziali "
                "socio-assistenziali e socio-sanitari per centomila anziani")
        titolo = seo_titles.answer_title(meta(name=nome, unit="centomila anziani"),
                                         level(best=None, worst=None))
        self.assertIn("non autosufficienti", titolo)

    def test_sulle_province_non_si_buttano_cifre_sigle_e_soglie(self):
        casi = {
            "Concentrazione media annua di PM10": "PM10",
            "Amministratori comunali con meno di 40 anni": "40",
            "Pensionati con reddito pensionistico di basso importo": "basso",
        }
        for nome, parola in casi.items():
            with self.subTest(nome=nome):
                titolo = seo_titles.answer_title(meta(name=nome, unit="%"),
                                                 provincia(("A", 38.3), ("B", 16.2)))
                self.assertIn(parola, titolo)

    def test_una_giuntura_non_lascia_la_testa_appesa(self):
        """"Tasso di criminalita' organizzata e per regione": il taglio cadeva
        davanti a "di" e lasciava la congiunzione in fondo."""
        nome = "Tasso di criminalità organizzata e di tipo mafioso"
        titolo = seo_titles.answer_title(meta(name=nome, unit="per 100.000 abitanti"),
                                         level(best=("A", 2.7), worst=("B", 0.0)))
        self.assertNotIn(" e per ", titolo)
        self.assertNotIn(" e,", titolo)

    def test_se_nessun_accorciamento_regge_resta_quello_di_prima(self):
        """La guardia sceglie fra gli accorciamenti, non li vieta tutti: senza
        alternative la pagina tiene il titolo di prima invece di cadere sul
        ripiego, che taglierebbe allo stesso modo e senza cifre."""
        nome = ("Incidenza della popolazione residente in comuni senza offerta "
                "di spettacolo, intrattenimento e sport")
        titolo = seo_titles.answer_title(meta(name=nome, unit="%"),
                                         level(best=("A", 11.2), worst=("B", 0.03)))
        self.assertIsNotNone(titolo)
        self.assertIn("11,2%", titolo)


class NomeBreveTest(unittest.TestCase):
    def test_due_pagine_che_collidevano_si_distinguono(self):
        a = seo_titles.answer_title(
            meta(name="Incidenza di dipendenti di genere femminile delle imprese nei settori culturali e creativi",
                 unit="%", family="territorial", raw_id="598"),
            level(best=None, worst=None))
        b = seo_titles.answer_title(
            meta(name="Incidenza di dipendenti in età giovanile delle imprese nei settori culturali e creativi",
                 unit="%", family="territorial", raw_id="599"),
            level(best=None, worst=None))
        self.assertEqual(a, "Donne fra i dipendenti delle imprese culturali per regione")
        self.assertEqual(b, "Giovani fra i dipendenti delle imprese culturali per regione")

    def test_la_negazione_resta_e_le_cifre_entrano(self):
        nome = "Competenza numerica non adeguata (studenti classi III scuola secondaria primo grado)"
        titolo = seo_titles.answer_title(
            meta(name=nome, unit="%", family="bes", raw_id="SDG-310"),
            level(best=("Calabria", 62.0), worst=("Trento", 33.6)))
        self.assertEqual(titolo, "Competenza numerica non adeguata, dal 62,0% al 33,6%")

    def test_il_nome_breve_vale_per_il_suo_livello(self):
        """La chiave e' (codice, livello): la stessa scheda su un altro livello
        non lo prende."""
        titolo = seo_titles.answer_title(
            meta(name="Affollamento degli istituti di pena", unit="%", family="bes", raw_id="06POL012"),
            provincia(None, None))
        self.assertNotIn("carceri", titolo)

    def test_l_unita_non_cambia_la_misura_accorciata(self):
        """ter-84 usciva "Rifiuti urbani smaltiti per regione, da 317 a 0
        chilogrammi", un totale regionale, e bes-01SAL008 "Speranza di vita
        senza limitazioni, da 12,2 a 8,8 anni", una vita di dodici anni: lo
        zero scritto "0" aveva fatto spazio all'unita', e l'accorciatore aveva
        buttato il denominatore e l'eta'."""
        rifiuti = seo_titles.answer_title(
            meta(name="Rifiuti urbani smaltiti in discarica per abitante", unit="chilogrammi",
                 family="territorial", raw_id="84"),
            level(best=("Molise", 317.0), worst=("Campania", 0.0)))
        self.assertEqual(rifiuti, "Rifiuti urbani in discarica per abitante, da 317 a 0")
        self.assertNotIn("chilogrammi", rifiuti)
        speranza = seo_titles.answer_title(
            meta(name="Speranza di vita senza limitazioni nelle attività a 65 anni",
                 unit="Numero medio di anni", family="bes", raw_id="01SAL008"),
            level(best=("Veneto", 12.2), worst=("Calabria", 8.8)))
        self.assertEqual(speranza, "Speranza di vita a 65 anni senza limitazioni, da 12,2 a 8,8")

    def test_la_misura_non_si_restringe(self):
        """ter-255 misura il bosco e il resto della superficie forestale: la
        guardia sulle negazioni scartava "Superficie boscata (percorsa dal
        fuoco)", che del resto diceva solo il bosco, e restava "Superficie
        boscata e non boscata percorsa", senza il fuoco."""
        titolo = seo_titles.answer_title(
            meta(name="Superficie boscata e non boscata percorsa dal fuoco", unit="%",
                 family="territorial", raw_id="255"),
            level(best=("Calabria", 2.4), worst=("Valle d'Aosta", 0.02)))
        self.assertEqual(titolo, "Superficie forestale percorsa dal fuoco, dal 2,4% allo 0,02%")

    def test_sulle_province_il_nome_breve_tiene_cio_che_distingue_la_misura(self):
        """Con la coda " per provincia" che non cade, l'accorciatore buttava
        la parte che distingue: frane e alluvioni uscivano tutte e due
        "Popolazione esposta al rischio per provincia", e 06POL007P
        "Amministrazioni provinciali: capacita' per provincia"."""
        casi = {
            ("10AMB011", "Popolazione esposta al rischio di frane"):
                "Popolazione a rischio frane per provincia, dal 15,5% allo 0%",
            ("10AMB012", "Popolazione esposta al rischio di alluvioni"):
                "Popolazione a rischio alluvioni per provincia, da 100% a 0%",
            ("06POL007P", "Amministrazioni provinciali: capacità di riscossione"):
                "Riscossione delle Province per provincia, dal 96,4% al 44,1%",
            ("06POL009P", "Comuni: capacità di riscossione"):
                "Riscossione dei Comuni per provincia, dall'87,1% al 45,1%",
        }
        estremi = {"10AMB011": (15.5, 0.0), "10AMB012": (100.0, 0.0),
                   "06POL007P": (96.4, 44.1), "06POL009P": (87.1, 45.1)}
        for (codice, nome), atteso in casi.items():
            with self.subTest(codice=codice):
                alto, basso = estremi[codice]
                titolo = seo_titles.answer_title(
                    meta(name=nome, unit="%", family="bes", raw_id=codice),
                    provincia(("A", alto), ("B", basso)))
                self.assertEqual(titolo, atteso)
                self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)


class EstremiNonVerificatiTest(unittest.TestCase):
    """bes-06POL012P: zeri dal 2016 e 358% a Fermo, causa non verificata."""

    def setUp(self):
        self.meta = meta(name="Affollamento degli istituti di pena", unit="%",
                         family="bes", raw_id="06POL012P")
        self.lv = provincia(("Fermo", 358.1), ("Macerata", 0.0))

    def test_niente_estremi(self):
        self.assertEqual(seo_titles.extremes(self.meta, self.lv), (None, None))

    def test_niente_estremi_anche_col_minimo_vero(self):
        """Gli zeri di Macerata e Savona oggi sono n.d. (`bes_data.NOT_MEASURED`)
        e il minimo e' Arezzo, un valore vero. Fermo resta non verificato, e
        un intervallo con un capo solo non va in SERP."""
        lv = provincia(("Fermo", 358.1), ("Arezzo", 35.2))
        self.assertEqual(seo_titles.extremes(self.meta, lv), (None, None))
        self.assertEqual(seo_titles.page_title({}, self.meta, lv, site_name="Divario Italia"),
                         "Affollamento delle carceri per provincia")
        self.assertIsNone(seo_titles.answer_description(self.meta, lv))

    def test_il_titolo_non_porta_cifre_e_dice_carceri(self):
        titolo = seo_titles.page_title({}, self.meta, self.lv, site_name="Divario Italia")
        self.assertEqual(titolo, "Affollamento delle carceri per provincia")

    def test_la_descrizione_non_porta_cifre(self):
        self.assertIsNone(seo_titles.answer_description(self.meta, self.lv))
        composto = "Rapporta il numero di persone detenute ai posti regolamentari."
        self.assertEqual(seo_titles.page_description({}, self.meta, self.lv, composed=composto),
                         composto)


class RipiegoTest(unittest.TestCase):
    def test_la_coda_del_ripiego_segue_il_livello(self):
        """La vista province dei NEET usciva "... (NEET) per regione": il
        derivato non ci stava, e il ripiego aveva la coda fissa."""
        titolo = seo_titles.page_title(
            {}, meta(name="Giovani che non lavorano e non studiano (NEET)", unit="%"),
            provincia(("Taranto", 34.6), ("Padova", 6.1)), site_name="Divario Italia")
        self.assertEqual(titolo, "Giovani che non lavorano e non studiano (NEET) per provincia")
        self.assertLessEqual(len(titolo), seo_titles.TITLE_MAX)


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
        # Sulle province i territori stanno fra parentesi (`province_answer`).
        self.assertIn("(Milano)", seo_titles.page_description({}, meta(), prov))

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

    def test_un_estremo_condiviso_si_dice_tutto(self):
        """"a 0,00 ad Aosta" era la prima in ordine alfabetico di sedici
        province a zero."""
        zeri = [(nome, 0.0) for nome in ("Aosta", "Belluno", "Rovigo")]
        lv = provincia(("Nuoro", 3.4), ("Aosta", 0.0), observations=[("Nuoro", 3.4), ("Lecce", 1.2), *zeri])
        d = seo_titles.answer_description(meta(name="Omicidi volontari", unit="per 100.000 abitanti"), lv)
        self.assertIn("da 3,4 per 100.000 abitanti (Nuoro) a 0 (3 province).", d)

    def test_due_a_pari_merito_si_nominano(self):
        lv = provincia(("Lecco", 84.9), ("Napoli", 81.4),
                       observations=[("Lecco", 84.9), ("Treviso", 84.9), ("Napoli", 81.4)])
        d = seo_titles.answer_description(meta(name="Speranza di vita", unit="anni"), lv)
        self.assertIn("(Lecco e Treviso)", d)

    def test_il_conteggio_e_quello_dei_territori_col_dato(self):
        """"107 province a confronto" su una serie che ne ha 106 nell'anno."""
        osservate = [(f"P{i}", float(i)) for i in range(1, 107)]
        lv = provincia(("P106", 106.0), ("P1", 1.0), observations=osservate)
        d = seo_titles.answer_description(meta(unit="euro"), lv)
        self.assertIn("106 province con dato", d)
        self.assertNotIn("107", d)

    def test_senza_cifre_si_ripiega_sul_lead_composto(self):
        composto = "Una frase generata dal sito."
        d = seo_titles.page_description({}, meta(), level(best=None, worst=None),
                                        composed=composto)
        self.assertIn("generata dal sito", d)


class TitoloProvincialeTest(unittest.TestCase):
    """Sulle province " per provincia" non cade mai (`_province_title`)."""

    def test_la_coda_resta_e_cadono_le_cifre(self):
        """Il tasso di occupazione 20-64 per provincia usciva senza "per
        provincia": il livello era la prima cosa sacrificata alle cifre."""
        titolo = seo_titles.answer_title(meta(name="Tasso di occupazione (20-64 anni)", unit="%"),
                                         provincia(("Bolzano", 79.9), ("Taranto", 44.2)))
        self.assertEqual(titolo, "Tasso di occupazione (20-64 anni) per provincia, dati 2024")

    def test_prima_cade_l_unita_poi_il_nome(self):
        titolo = seo_titles.answer_title(
            meta(name="Speranza di vita alla nascita", unit="Numero medio di anni"),
            provincia(("Lecco", 84.9), ("Napoli", 81.4)))
        self.assertEqual(titolo, "Speranza di vita alla nascita per provincia, da 84,9 a 81,4")

    def test_il_nome_breve_curato_prende_il_posto_del_nome(self):
        titolo = seo_titles.answer_title(
            meta(name="Speranza di vita alla nascita", unit="Numero medio di anni",
                 family="bes", raw_id="01SAL001"),
            provincia(("Lecco", 84.9), ("Napoli", 81.4)))
        self.assertEqual(titolo, "Speranza di vita per provincia, da 84,9 a 81,4 anni")

    def test_senza_estremi_niente_anno(self):
        """L'anno prende il posto delle cifre che non ci stanno, non delle cifre
        che non ci sono: una serie `contextual` resta col nome e il livello."""
        titolo = seo_titles.answer_title(meta(name="Tasso di occupazione (20-64 anni)", unit="%"),
                                         provincia(None, None))
        self.assertEqual(titolo, "Tasso di occupazione (20-64 anni) per provincia")

    def test_le_regioni_non_cambiano(self):
        """Sulle regioni l'ordine resta quello di prima: la coda cade prima
        delle cifre."""
        titolo = seo_titles.answer_title(meta(name="Tasso di occupazione (20-64 anni)", unit="%"),
                                         level(best=("Bolzano", 79.9), worst=("Taranto", 44.2)))
        self.assertEqual(titolo, "Tasso di occupazione (20-64 anni), dal 79,9% al 44,2%")


class PreposizioneRegioneTest(unittest.TestCase):
    def test_in_nel_nelle(self):
        casi = {"Puglia": "in Puglia", "Lazio": "nel Lazio", "Molise": "nel Molise",
                "Marche": "nelle Marche", "Piemonte": "in Piemonte",
                "Trentino Alto Adige": "in Trentino Alto Adige",
                "Friuli-Venezia Giulia": "in Friuli-Venezia Giulia", "Umbria": "in Umbria"}
        for regione, atteso in casi.items():
            with self.subTest(regione=regione):
                self.assertEqual(seo_titles.in_region(regione), atteso)


class RispostaProvincialeTest(unittest.TestCase):
    """`province_answer`: la description e la frase-risposta delle province."""

    def setUp(self):
        osservate = [("Lecco", 84.9), ("Treviso", 84.9), ("Pavia", 82.6), ("Napoli", 81.4), ("Caserta", 81.9)]
        self.lv = provincia(("Lecco", 84.9), ("Napoli", 81.4), observations=osservate, year_max=2024)
        self.lv["region_of"] = {"lecco": "Lombardia", "pavia": "Lombardia", "treviso": "Veneto",
                                "napoli": "Campania", "caserta": "Campania"}
        self.meta = meta(name="Speranza di vita alla nascita", unit="Numero medio di anni",
                         family="bes", raw_id="01SAL001")

    def test_la_forma(self):
        self.assertEqual(
            seo_titles.province_answer(self.meta, self.lv),
            "Speranza di vita per provincia, 2024: da 84,9 anni (Lecco e Treviso) a 81,4 (Napoli). "
            "In Lombardia 2,3 anni separano Lecco da Pavia.")

    def test_i_territori_linkati_dicono_la_stessa_frase(self):
        from app.indicator_notes import strip_markdown

        linkata = seo_titles.province_answer(self.meta, self.lv, link_prefix="/provincia/")
        self.assertIn("([Lecco](/provincia/lecco) e [Treviso](/provincia/treviso))", linkata)
        self.assertIn("separano [Lecco](/provincia/lecco) da [Pavia](/provincia/pavia).", linkata)
        self.assertEqual(strip_markdown(linkata), seo_titles.province_answer(self.meta, self.lv))

    def test_senza_un_unita_breve_niente_distanza(self):
        """"2,1 per 100.000 abitanti separano" non si legge: si dice il
        conteggio. L'unita' lunga resta accanto al primo estremo."""
        d = seo_titles.province_answer(meta(name="Omicidi volontari", unit="per 100.000 abitanti"), self.lv)
        self.assertIn("da 84,9 per 100.000 abitanti (Lecco e Treviso)", d)
        self.assertNotIn("separano", d)
        self.assertTrue(d.endswith("5 province con dato, dati Istat."), d)

    def test_un_tasso_standardizzato_porta_il_suo_denominatore(self):
        """Sulle serie di mortalita' la frase usciva "da 1,9 (Vercelli)": una
        cifra nuda che si legge come un totale. `phrase_unit` resta com'e',
        perche' scrive anche tessere, celle e mappe delle altre pagine: il
        denominatore lo aggiunge solo la frase delle province."""
        for unita, atteso in (("Tassi standardizzati per 10.000 residenti", "per 10.000 residenti"),
                              ("tasso standardizzato per 10.000", "per 10.000")):
            with self.subTest(unita=unita):
                self.assertIsNone(numfmt.phrase_unit(unita))
                d = seo_titles.province_answer(meta(name="Mortalità evitabile (0-74 anni)", unit=unita), self.lv)
                self.assertIn(f"da 84,9 {atteso} (Lecco e Treviso) a 81,4 (Napoli).", d)
                self.assertNotIn("separano", d)

    def test_un_tasso_senza_denominatore_resta_nudo(self):
        d = seo_titles.province_answer(meta(name="Passaggio all'università", unit="tasso specifico per coorte"),
                                       self.lv)
        self.assertIn("da 84,9 (Lecco e Treviso)", d)

    def test_la_regione_prende_la_sua_preposizione(self):
        self.lv["region_of"] = {key: "Marche" for key in self.lv["region_of"]}
        d = seo_titles.province_answer(meta(name="Tasso", unit="%"), self.lv)
        self.assertIn(" Nelle Marche 3,5 punti separano Lecco da Napoli.", d)

    def test_solo_sulle_province(self):
        self.assertIsNone(seo_titles.province_answer(self.meta, level()))

    def test_la_provincia_prende_la_sua_preposizione(self):
        """"separano Cagliari da Sud Sardegna" era in pagina: le province con
        l'articolo lo vogliono anche qui, e il link non se lo prende."""
        from app.indicator_notes import strip_markdown

        casi = {
            ("Cagliari", "Sud Sardegna"): "separano Cagliari dal Sud Sardegna.",
            ("Sud Sardegna", "Cagliari"): "separano il Sud Sardegna da Cagliari.",
            ("Teramo", "L'Aquila"): "separano Teramo dall'Aquila.",
            ("Genova", "La Spezia"): "separano Genova dalla Spezia.",
            ("Novara", "Verbano-Cusio-Ossola"): "separano Novara dal Verbano-Cusio-Ossola.",
        }
        for (alta, bassa), atteso in casi.items():
            with self.subTest(coppia=(alta, bassa)):
                lv = provincia((alta, 60.0), (bassa, 40.0), observations=[(alta, 60.0), (bassa, 40.0)])
                lv["region_of"] = {alta.lower().replace(" ", "-"): "Regione",
                                   bassa.lower().replace(" ", "-"): "Regione"}
                d = seo_titles.province_answer(meta(name="Tasso", unit="%"), lv)
                self.assertTrue(d.endswith(atteso), d)
                linkata = seo_titles.province_answer(meta(name="Tasso", unit="%"), lv, link_prefix="/provincia/")
                self.assertEqual(strip_markdown(linkata), d)

    def test_da_con_l_articolo(self):
        for nome, atteso in {"Milano": "da Milano", "L'Aquila": "dall'Aquila", "La Spezia": "dalla Spezia",
                             "Sud Sardegna": "dal Sud Sardegna", "Aosta": "da Aosta"}.items():
            with self.subTest(nome=nome):
                self.assertEqual(seo_titles.from_place(nome), atteso)


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
