"""Le pagine provincia portano il valore vero, non solo il punteggio.

Per un anno una pagina provincia ha mostrato soltanto punteggi da 0 a 100,
standardizzati sulle 103 province. Un punteggio dice dove sta un territorio
rispetto agli altri, non quanto vale: chi cercava "speranza di vita provincia
di Lecce" arrivava su una pagina che non conteneva il numero di anni, mentre il
BES dei Territori ne porta 479 righe per ogni provincia.

Queste prove tengono due cose che si rompono in silenzio:

1. **il valore reso e' quello della fonte**, riga per riga. Una tabella che
   arrotonda, riscala o prende l'anno sbagliato non fa fallire niente e si vede
   solo aprendo il CSV accanto alla pagina;
2. **due province non sono la stessa pagina con un nome diverso.** Prima di
   questa tabella lo erano per il 62% del testo, ed e' esattamente il profilo
   che un revisore esterno chiama contenuto prodotto in serie.
"""
import re
import unittest

from app import app, bes_data, it_numbers, province_profile


def _visibile(html):
    corpo = re.search(r'<main class="wrap[ "].*</main>', html, re.DOTALL)
    assert corpo, "la pagina non ha il corpo atteso"
    testo = re.sub(r"<(script|style)\b.*?</\1>", "", corpo.group(0), flags=re.DOTALL)
    testo = re.sub(r"<[^>]+>", " ", testo)
    return re.sub(r"\s+", " ", testo).strip()


def _shingle(parole, n=8):
    return {tuple(parole[i:i + n]) for i in range(len(parole) - n + 1)}


class IValoriSonoQuelliDellaFonte(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.righe = bes_data.get_bes_rows("provincia")

    def test_ogni_valore_combacia_con_la_riga_del_dataset(self):
        """Non "e' vicino": e' lo stesso numero, dello stesso anno."""
        atteso = {}
        for riga in self.righe:
            if riga["value"] is not None:
                atteso[(riga["territory_key"], riga["id"], riga["year"])] = riga["value"]
        for chiave in ("lecce", "milano", "isernia", "bolzano-bozen"):
            voci = province_profile.indicatori(chiave)
            if not voci:
                continue
            with self.subTest(provincia=chiave):
                self.assertGreater(len(voci), 50, "la provincia ha perso indicatori per strada")
                for voce in voci:
                    self.assertEqual(
                        voce["value"], atteso[(chiave, voce["id"], voce["year"])],
                        f"{chiave}/{voce['id']}/{voce['year']}")

    def test_l_anno_reso_e_l_ultimo_che_quella_provincia_ha(self):
        anni = {}
        for riga in self.righe:
            if riga["value"] is not None:
                sinora = anni.get((riga["territory_key"], riga["id"]))
                if sinora is None or riga["year"] > sinora:
                    anni[(riga["territory_key"], riga["id"])] = riga["year"]
        for voce in province_profile.indicatori("lecce"):
            with self.subTest(indicatore=voce["id"]):
                self.assertEqual(voce["year"], anni[("lecce", voce["id"])])

    def test_la_posizione_uno_e_la_migliore_secondo_il_verso(self):
        """Un verso letto al contrario mette in testa l'ultima provincia, e la
        pagina resta credibile: e' il guasto piu' facile da non vedere."""
        manifesto = bes_data.get_bes_manifest("provincia")
        per_indicatore = {}
        for chiave in province_profile.chiavi():
            for voce in province_profile.indicatori(chiave):
                per_indicatore.setdefault(voce["id"], []).append((voce["year"], voce["rank"], voce["value"]))
        for id_indicatore, voci in per_indicatore.items():
            direzione = manifesto[id_indicatore]["direction"]
            anno = max(a for a, _, _ in voci)
            stesso_anno = [(r, v) for a, r, v in voci if a == anno]
            migliore = min(stesso_anno)[1]
            with self.subTest(indicatore=id_indicatore):
                if direzione == "lower_better":
                    self.assertEqual(migliore, min(v for _, v in stesso_anno))
                else:
                    self.assertEqual(migliore, max(v for _, v in stesso_anno))

    def test_la_posizione_si_conta_solo_fra_chi_ha_un_dato_quell_anno(self):
        for voce in province_profile.indicatori("lecce"):
            with self.subTest(indicatore=voce["id"]):
                quante = sum(1 for r in self.righe
                             if r["id"] == voce["id"] and r["year"] == voce["year"]
                             and r["value"] is not None)
                self.assertEqual(voce["province_count"], quante)
                self.assertLessEqual(voce["rank"], quante)

    def test_il_confronto_dentro_la_regione_usa_solo_province_della_regione(self):
        territori = bes_data.get_bes_territories("provincia")
        pugliesi = {k for k, v in territori.items() if v.get("region") == "Puglia"}
        self.assertGreater(len(pugliesi), 1)
        for voce in province_profile.indicatori("lecce"):
            if not voce["in_regione"]:
                continue
            with self.subTest(indicatore=voce["id"]):
                self.assertLessEqual(voce["in_regione"]["quante"], len(pugliesi))
                self.assertLessEqual(voce["in_regione"]["posizione"], voce["in_regione"]["quante"])


class LaPaginaMostraQuelloCheHa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_il_valore_e_l_unita_arrivano_in_pagina(self):
        html = self.client.get("/provincia/lecce").get_data(as_text=True)
        testo = _visibile(html)
        formatta = app.jinja_env.filters["it_num"]
        voci = province_profile.indicatori("lecce")
        self.assertGreater(len(voci), 50)
        for voce in voci[:12]:
            with self.subTest(indicatore=voce["name"]):
                self.assertIn(voce["name"], testo)
                self.assertIn(formatta(voce["value"], voce["decimals"]), testo)
        unita = {v["unit"] for v in voci if v["unit"]}
        for misura in list(unita)[:5]:
            self.assertIn(misura, testo)

    def test_ogni_indicatore_porta_al_suo_indicatore(self):
        """Il link e' il canonico della scheda, non un path ricostruito: lo slug
        dal nome provinciale portava tre schede su un 301. Che il link risponda
        lo controlla `test_link_interni`."""
        html = self.client.get("/provincia/lecce").get_data(as_text=True)
        with app.app_context():
            voci = province_profile.indicatori("lecce")
            for voce in voci:
                with self.subTest(indicatore=voce["id"]):
                    self.assertEqual(voce["path"], bes_data.bes_path(voce["id"]))
                    self.assertIn(f'href="{voce["path"]}"', html)

    def test_due_province_non_sono_la_stessa_pagina(self):
        """Prima della tabella dei valori due province condividevano il 62% del
        testo. La soglia qui e' larga, perche' l'apparato e le intestazioni
        sono uguali per costruzione ed e' giusto che lo siano: serve a fermare
        un ritorno alla pagina-modello, non a inseguire un decimale."""
        for a, b in (("lecce", "isernia"), ("milano", "napoli"), ("lecce", "brindisi")):
            with self.subTest(coppia=f"{a}/{b}"):
                pa = _visibile(self.client.get(f"/provincia/{a}").get_data(as_text=True)).split()
                pb = _visibile(self.client.get(f"/provincia/{b}").get_data(as_text=True)).split()
                sa, sb = _shingle(pa), _shingle(pb)
                quota = len(sa & sb) / len(sa)
                self.assertLess(quota, 0.40,
                                f"{a} e {b} condividono il {quota:.0%} del testo")

    def test_la_pagina_non_e_piu_sottile_come_prima(self):
        """Trecentotrenta parole erano il motivo per cui centotre pagine
        indicizzate sembravano riempitivo."""
        for chiave in ("lecce", "isernia", "milano"):
            with self.subTest(provincia=chiave):
                parole = len(_visibile(self.client.get(f"/provincia/{chiave}").get_data(as_text=True)).split())
                self.assertGreater(parole, 1200)

    def test_niente_di_quello_che_si_calcola_resta_fuori_dalla_pagina(self):
        """Tre campi sono stati calcolati a ogni render e non resi da nessuna
        parte: la media delle altre province della regione, la variazione
        dall'inizio della serie e il flag di citta' metropolitana. Lavoro fatto
        centotre volte per niente, e invisibile: nessuna prova guarda cio' che
        un modulo produce e un template non chiede.
        """
        pagina = self.client.get("/provincia/napoli").get_data(as_text=True)
        testo = _visibile(pagina)
        profilo = province_profile.profilo("napoli")
        self.assertTrue(profilo["metro_city"], "Napoli e' citta' metropolitana")
        self.assertIn("Città metropolitana", testo)

        voci = province_profile.indicatori("napoli")
        formatta = app.jinja_env.filters["it_num"]
        con_media = [v for v in voci if v["in_regione"]]
        self.assertTrue(con_media, "nessun confronto dentro la regione da rendere")
        for voce in con_media[:5]:
            with self.subTest(indicatore=voce["name"]):
                self.assertIn(formatta(voce["in_regione"]["media"], voce["decimals"]), testo)

        con_variazione = [v for v in voci if v["variazione"] is not None]
        self.assertTrue(con_variazione, "nessuna variazione da rendere")
        self.assertIn(f"dal {con_variazione[0]['year_from']}", testo)

    def test_il_markdown_porta_le_stesse_risposte_dell_html(self):
        """HTML e Markdown sono lo stesso documento alla stessa URL: ogni cifra
        che l'HTML mostra c'e' anche nel Markdown, scritta allo stesso modo. Il
        Markdown scriveva i numeri col punto decimale (8.829 cifre su 103
        pagine), e la prova di prima lo fissava con `str(valore)`."""
        for chiave in ("lecce", "aosta", "napoli", "l-aquila", "trieste"):
            html = _visibile(self.client.get(f"/provincia/{chiave}").get_data(as_text=True))
            markdown = self.client.get(
                f"/provincia/{chiave}", headers={"Accept": "text/markdown"}).get_data(as_text=True)
            profilo = province_profile.profilo(chiave)
            with self.subTest(provincia=chiave, cosa="punteggio"):
                punteggio = it_numbers.number(profilo["score"])
                self.assertIn(punteggio, html)
                self.assertIn(punteggio, markdown)
                self.assertIn(f"{profilo['rank']}ª su {profilo['total']}", markdown)
            for voce in province_profile.indicatori(chiave):
                valore = it_numbers.number(voce["value"], voce["decimals"])
                with self.subTest(provincia=chiave, indicatore=voce["id"]):
                    self.assertIn(voce["name"], markdown)
                    self.assertIn(voce["theme"], markdown)
                    self.assertIn(valore, html)
                    self.assertIn(valore, markdown)
                    if voce["variazione"] is not None:
                        variazione = it_numbers.change(voce["variazione"], voce["decimals"])
                        self.assertIn(f"dal {voce['year_from']} {variazione}", html)
                        self.assertIn(f"dal {voce['year_from']} {variazione}", markdown)

    def test_una_cifra_una_forma(self):
        """I difetti che l'audit del 22/9 ha trovato su tutte le 103 pagine."""
        for chiave in province_profile.chiavi():
            pagina = self.client.get(f"/provincia/{chiave}").get_data(as_text=True)
            markdown = self.client.get(
                f"/provincia/{chiave}", headers={"Accept": "text/markdown"}).get_data(as_text=True)
            with self.subTest(provincia=chiave):
                # anno e variazione attaccati: "2023dal 2015"
                self.assertNotRegex(pagina, r"\d{4}</small><small>dal")
                self.assertNotRegex(pagina + markdown, r"[+-]0,0+(?!\d)")
                # il Markdown all'italiana: niente decimali col punto, niente "13a"
                # "72.1" col punto decimale. "1.047" e' un migliaio all'italiana.
                # Fuori dai link, dove "PM2.5" e' un nome e non una cifra.
                cifre = re.sub(r"\[[^\]]*\]\([^)]*\)", "", markdown)
                self.assertNotRegex(cifre, r"(?<![\d.])\d+\.\d{1,2}(?![\d.])")
                self.assertNotIn("qualita'", markdown)
                self.assertNotRegex(markdown, r"\b\d+a su \d+")
                # quattro macro-aree, non gli undici domini BES
                self.assertLessEqual(pagina.count('class="macro-pill"'), 4)
                # "a Aosta", "a L'Aquila"
                self.assertNotRegex(pagina + markdown, r"\ba (?:A|L'|L&#39;|La )")

    def test_le_vicine_sono_sempre_sei(self):
        """La finestra centrata sull'ultima in classifica ne dava tre."""
        chiavi = province_profile.chiavi()
        for chiave in (chiavi[0], chiavi[1], chiavi[len(chiavi) // 2], chiavi[-2], chiavi[-1]):
            with self.subTest(provincia=chiave):
                vicine = province_profile.vicine(chiave)
                self.assertEqual(len(vicine), 6)
                self.assertNotIn(chiave, [v["key"] for v in vicine])

    def test_il_creatore_e_divario_italia_e_la_fonte_istat(self):
        """"creator: Istat" su un punteggio che Istat non ha mai pubblicato."""
        import json
        pagina = self.client.get("/provincia/l-aquila").get_data(as_text=True)
        blocchi = [json.loads(b) for b in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', pagina, re.DOTALL)]
        dataset = next(b for b in blocchi if b.get("@type") == "Dataset")
        self.assertEqual(dataset["name"], "Qualità della vita all'Aquila")
        self.assertEqual(dataset["creator"], {"@id": "https://divarioitalia.it/chi-siamo#organizzazione"})
        self.assertEqual(dataset["isBasedOn"]["creator"]["name"], "Istat")
        self.assertRegex(dataset["temporalCoverage"], r"^\d{4}/\d{4}$")
        self.assertGreater(len(dataset["variableMeasured"]), 50)


class LeProvinceSonoQuelleDellaFonte(unittest.TestCase):
    """Le invarianti del dataset provinciale, dopo la regex che ne perdeva
    quattro e la nota pubblica che ne dava la colpa al BES."""

    @classmethod
    def setUpClass(cls):
        import csv
        dati = bes_data.PROVINCE_CODES.parent
        with bes_data.PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
            cls.codici = list(csv.DictReader(handle, delimiter=";"))
        with (dati / "Assoluti_Provincia.csv").open(encoding="utf-8", newline="") as handle:
            cls.righe = list(csv.DictReader(handle, delimiter=";"))

    def test_sono_centosette_e_tutte_nuts3(self):
        from scripts.province_sources import NUTS3_PATTERN
        self.assertEqual(len(self.codici), 107)
        for riga in self.codici:
            with self.subTest(codice=riga["code"]):
                self.assertRegex(riga["code"], NUTS3_PATTERN)

    def test_ogni_provincia_sta_in_una_regione_vera(self):
        from app.data import REGION_ORDER
        for riga in self.codici:
            with self.subTest(provincia=riga["name"]):
                self.assertIn(riga["region"], REGION_ORDER)

    def test_bolzano_e_trento_stanno_nel_trentino(self):
        """Avevano come regione la loro provincia autonoma: niente link al
        Trentino-Alto Adige e niente confronto fra loro."""
        regione = {r["name"]: r["region"] for r in self.codici}
        self.assertEqual(regione["Bolzano"], "Trentino Alto Adige")
        self.assertEqual(regione["Trento"], "Trentino Alto Adige")
        voci = {v["id"]: v for v in province_profile.indicatori("bolzano")}
        self.assertTrue(any(v["in_regione"] and v["in_regione"]["quante"] == 2 for v in voci.values()))

    def test_nessuna_riga_doppia(self):
        chiavi = [(r["idIndicatore"], r["Territorio"], r["Anno"]) for r in self.righe]
        self.assertEqual(len(chiavi), len(set(chiavi)))

    def test_nessun_conteggio_di_province_scritto_a_mano(self):
        """Un "103 province" scritto a mano e' diventato una frase falsa appena
        la causa delle assenze e' risultata un'altra. Nei template il numero si
        calcola; nei commenti Jinja, che raccontano la storia, puo' restare."""
        from pathlib import Path
        cartella = Path(app.root_path) / "templates"
        for template in sorted(cartella.glob("*.html")):
            testo = re.sub(r"\{#.*?#\}", "", template.read_text(encoding="utf-8"), flags=re.DOTALL)
            with self.subTest(template=template.name):
                self.assertNotRegex(testo, r"\b10[37] province\b")
                self.assertNotIn("Sud Sardegna non è presente", testo)

    def test_la_nota_di_copertura_e_calcolata(self):
        client = app.test_client()
        for percorso in ("/qualita-della-vita/classifica/province", "/metodologia"):
            with self.subTest(pagina=percorso):
                testo = client.get(percorso).get_data(as_text=True)
                self.assertIn("107 province", testo)
                for nome in province_profile.unmeasured_provinces():
                    self.assertIn(nome, testo)


if __name__ == "__main__":
    unittest.main()
