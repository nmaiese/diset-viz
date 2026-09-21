"""Lo stage deve comportarsi da stage.

Il rischio che questi test sorvegliano non e' "il deploy fallisce", che si vede
subito, ma "il deploy riesce e Google indicizza un duplicato completo del sito
su un secondo dominio", che non si vede affatto finche' non e' successo. La SEO
tecnica di divarioitalia.it questo repo se l'e' gia' dovuta riprendere una volta
(il default-deny in `add_security_headers` esiste per quello), quindi la
modalita' stage viene verificata invece che dedotta.

`STAGING` si legge come attributo del modulo a ogni richiesta, non alla
importazione, ed e' per questo che si puo' accendere e spegnere qui.
"""
import base64
import unittest

from app import app, config
from app.cache import cache


class StagingModeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._staging = config.STAGING
        self._password = config.STAGING_PASSWORD
        # La home e' cachata per 300s: senza svuotare, questi test leggerebbero
        # la risposta prodotta da un altro test nell'altra modalita'.
        cache.clear()

    def tearDown(self):
        config.STAGING = self._staging
        config.STAGING_PASSWORD = self._password
        cache.clear()

    # --- stage acceso -----------------------------------------------------
    def test_every_response_is_noindex(self):
        config.STAGING = True
        for path in ("/", "/blog", "/atlante", "/metodologia", "/ricerca?q=lavoro"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""), path)

    def test_robots_txt_forbids_everything(self):
        config.STAGING = True
        body = self.client.get("/robots.txt").get_data(as_text=True)
        self.assertIn("Disallow: /", body)
        # Il robots di produzione dice il contrario e pubblica la sitemap del
        # dominio vero: nessuna delle due cose deve uscire da qui.
        self.assertNotIn("Allow: /", body)
        self.assertNotIn("Sitemap:", body)

    def test_pages_carry_the_staging_meta_and_banner(self):
        config.STAGING = True
        # Le tre famiglie di shell: chrome nuovo, chrome legacy, e le due che
        # montano la SPA. /confronto e' qui perche' la fascia le mancava: e'
        # una shell a se', e una shell nuova non eredita niente.
        for path in ("/", "/blog", "/atlante", "/confronto"):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn('<meta name="robots" content="noindex, nofollow, noarchive">', html)
                # Senza la fascia la copia e' indistinguibile dal sito vero, che
                # e' l'errore che uno stage identico all'originale invita a fare.
                self.assertIn("Ambiente di stage", html)

    def test_staging_does_not_serve_an_index_signal_anywhere(self):
        config.STAGING = True
        for path in ("/", "/blog", "/sitemap.xml", "/llms.txt"):
            with self.subTest(path=path):
                header = self.client.get(path).headers.get("X-Robots-Tag", "")
                self.assertNotIn("index, follow", header, path)

    # --- la password ------------------------------------------------------
    # `noindex` parla ai crawler educati. La password parla a tutti gli altri:
    # senza, una copia intera del sito sta su una URL pubblica e chiunque la
    # riceva per sbaglio (un Referer, un link incollato) la legge tutta.

    def _auth(self, user="divario", password="parola-di-prova"):
        raw = f"{user}:{password}".encode("utf-8")
        return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}

    def test_without_credentials_nothing_is_served(self):
        config.STAGING = True
        config.STAGING_PASSWORD = "parola-di-prova"
        for path in ("/", "/blog", "/atlante", "/sitemap.xml", "/api/indicators"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401, path)
                self.assertIn("Basic", response.headers.get("WWW-Authenticate", ""), path)

    def test_the_right_password_opens_the_stage(self):
        config.STAGING = True
        config.STAGING_PASSWORD = "parola-di-prova"
        response = self.client.get("/", headers=self._auth())
        self.assertEqual(response.status_code, 200)
        # La password apre lo stage, non lo trasforma nel sito vero: le altre
        # garanzie devono valere anche dopo il login.
        self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))
        self.assertIn("Ambiente di stage", response.get_data(as_text=True))

    def test_a_wrong_password_is_refused(self):
        config.STAGING = True
        config.STAGING_PASSWORD = "parola-di-prova"
        for user, password in (("divario", "sbagliata"), ("altro", "parola-di-prova")):
            with self.subTest(user=user):
                response = self.client.get("/", headers=self._auth(user, password))
                self.assertEqual(response.status_code, 401)

    def test_a_non_ascii_password_is_refused_not_crashed(self):
        # `hmac.compare_digest` sulle str esplode con TypeError sui caratteri
        # non ASCII: una password sbagliata deve dare 401, mai 500.
        config.STAGING = True
        config.STAGING_PASSWORD = "parola-di-prova"
        response = self.client.get("/", headers=self._auth("divario", "passwòrd"))
        self.assertEqual(response.status_code, 401)

    def test_robots_txt_stays_readable_without_the_password(self):
        # Dietro al 401 un crawler vedrebbe un errore, non un divieto. Il file
        # che nega la scansione vale solo se si puo' leggere.
        config.STAGING = True
        config.STAGING_PASSWORD = "parola-di-prova"
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Disallow: /", response.get_data(as_text=True))

    def test_without_a_password_the_stage_stays_open(self):
        # L'anteprima locale (`STAGING=1 gunicorn ...`) non ha niente da
        # proteggere. Sul servizio deployato la password la mette sempre
        # bin/deploy-staging.
        config.STAGING = True
        config.STAGING_PASSWORD = ""
        self.assertEqual(self.client.get("/").status_code, 200)

    # --- stage spento: la produzione non cambia ---------------------------
    def test_production_still_indexes(self):
        config.STAGING = False
        response = self.client.get("/")
        self.assertIn("index, follow", response.headers.get("X-Robots-Tag", ""))
        html = response.get_data(as_text=True)
        self.assertNotIn("Ambiente di stage", html)
        self.assertIn('content="index, follow', html)

    def test_production_robots_is_unchanged(self):
        config.STAGING = False
        body = self.client.get("/robots.txt").get_data(as_text=True)
        self.assertIn("Allow: /", body)
        self.assertIn("Sitemap:", body)

    def test_production_is_never_password_protected(self):
        # Il ramo della password non deve poter chiudere il sito vero, nemmeno
        # se la variabile resta impostata per errore sul servizio di produzione.
        config.STAGING = False
        config.STAGING_PASSWORD = "parola-di-prova"
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_noindex_paths_stay_noindex_in_production(self):
        # La modalita' stage aggiunge un ramo prima di questa logica: va
        # verificato che non l'abbia scavalcata.
        config.STAGING = False
        header = self.client.get("/account").headers.get("X-Robots-Tag", "")
        self.assertIn("noindex", header)


if __name__ == "__main__":
    unittest.main()
