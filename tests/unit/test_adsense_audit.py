import unittest
from pathlib import Path

from scripts import adsense_audit as audit


class CmpStatusTest(unittest.TestCase):
    def test_le_tre_righe_del_consenso_ci_sono(self):
        status = audit.cmp_status()
        present = status["presente"]
        self.assertEqual(present["cmp_nome"], "Iubenda")
        self.assertTrue(present["consent_mode_default"])
        self.assertTrue(present["consent_default_denied"])
        self.assertTrue(present["gtm_loader"])
        self.assertTrue(present["adsense_loader"])
        self.assertTrue(present["preferenze_cookie"])

    def test_nessun_difetto_catastrofico(self):
        status = audit.cmp_status()
        self.assertEqual(status["manca"], [])


class AssetParserTest(unittest.TestCase):
    def test_separa_script_css_immagini(self):
        html = (
            '<html><head>'
            '<link rel="stylesheet" href="/static/css/site.css">'
            '<script src="/static/js/x.js"></script>'
            '</head><body><img src="/static/img/a.png"></body></html>'
        )
        assets = audit.parse_asset_refs(html)
        self.assertEqual(assets["css"], ["/static/css/site.css"])
        self.assertEqual(assets["js"], ["/static/js/x.js"])
        self.assertEqual(assets["img"], ["/static/img/a.png"])

    def test_ignora_script_inline_e_tag_estranei(self):
        html = '<script>var x = 1;</script><div></div>'
        assets = audit.parse_asset_refs(html)
        self.assertEqual(assets["js"], [])


class W2Test(unittest.TestCase):
    def test_legge_i_conteggi_del_rapporto(self):
        text = (
            "Link rotti (404/redirect): 0 (0 pagine)\n"
            "Link verso URL non in sitemap: 6.513 (618 pagine)\n"
            "Pagine orfane (in sitemap, nessun link in ingresso): 10\n"
            "URL duplicate/non canoniche in sitemap: 0\n"
            "Canonical incoerenti: 0\n"
        )
        parsed = audit.parse_w2(text)
        self.assertEqual(parsed["link_rotti"], 0)
        self.assertEqual(parsed["fuori_sitemap"], 6513)
        self.assertEqual(parsed["orfane"], 10)
        self.assertEqual(parsed["duplicate"], 0)
        self.assertEqual(parsed["canonical_incoerenti"], 0)


class UrlInspectionTest(unittest.TestCase):
    def test_dichiarato_non_misurato_da_questo_script(self):
        status = audit.url_inspection_status()
        self.assertFalse(status["available"])
        self.assertIn("non misurato da questo script", status["reason"])
        self.assertIn("webmasters.readonly", status["reason"])


class BuildReportTest(unittest.TestCase):
    def _payload(self):
        return {
            "data": "2026-10-03",
            "cmp": {
                "presente": {
                    "cmp_nome": "Iubenda", "cmp_url": "https://x",
                    "consent_mode_default": True, "consent_default_denied": True,
                    "gtm_loader": True, "adsense_loader": True,
                    "adsense_condizionale": True, "preferenze_cookie": True,
                },
                "manca": [],
                "non_verificabile": ["a", "b"],
            },
            "pagespeed": "non disponibile: quota esaurita",
            "pagine": [
                {"tipo": "home", "status": 200, "html_bytes": 1024,
                 "script": 1, "stylesheet": 2, "immagini": 0,
                 "totale_stimato_bytes": 2048},
            ],
            "w2": {"link_rotti": 0, "fuori_sitemap": 6513, "orfane": 10,
                   "duplicate": 0, "canonical_incoerenti": 0},
            "url_inspection": {"available": False, "reason": "nessuno script"},
            "ads_txt": {"status": 200, "riga_attesa": True},
        }

    def test_report_contiene_le_sezioni(self):
        report = audit.build_report(self._payload())
        for heading in ("Consenso cookie / CMP", "Core Web Vitals",
                        "Link rotti", "URL Inspection", "ads.txt"):
            self.assertIn(f"## {heading}", report)
        self.assertIn("Iubenda", report)
        self.assertIn("link rotti: 0", report)

    def test_scrive_il_report_sul_disco(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = audit.write_report(self._payload(), Path(tmp))
            self.assertEqual(path.name, "adsense_audit_20261003.md")
            self.assertTrue(path.exists())


class NoNetTest(unittest.TestCase):
    def test_no_net_stampa_e_non_scrive_il_report_del_giorno(self):
        from unittest import mock
        import contextlib
        import io

        with mock.patch.object(audit, "write_report") as write, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(audit.main(["--no-net"]), 0)
        write.assert_not_called()
        self.assertIn("URL Inspection", out.getvalue())


if __name__ == "__main__":
    unittest.main()
