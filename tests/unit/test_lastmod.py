"""Il `lastmod` della sitemap e' la data vera dei dati, mai quella di oggi."""
import json
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from app import lastmod

W3C_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _con_stato(sources):
    """Punta il modulo a un `source_state.json` finto e svuota la cache."""
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / "source_state.json"
    path.write_text(json.dumps({"sources": sources}), encoding="utf-8")
    patcher = mock.patch.object(lastmod, "_SOURCE_STATE", path)
    patcher.start()
    lastmod._date_fonti.cache_clear()

    def chiudi():
        patcher.stop()
        lastmod._date_fonti.cache_clear()
        tmp.cleanup()

    return chiudi


class TestLastmod(unittest.TestCase):
    def tearDown(self):
        lastmod._date_fonti.cache_clear()

    def test_voce_con_data_reale_la_porta_in_formato_w3c(self):
        self.addCleanup(_con_stato({
            "istat_indicatori_territoriali": {"last_modified": "Fri, 17 Jul 2026 07:02:57 GMT"},
            "istat_bes_regioni": {"last_modified": "Mon, 25 May 2026 15:00:11 GMT"},
        }))
        self.assertEqual(lastmod.lastmod_scheda("territorial", "regione"), "2026-07-17")
        self.assertEqual(lastmod.lastmod_scheda("bes", "regione"), "2026-05-25")
        self.assertEqual(lastmod.lastmod_regione(), "2026-07-17")
        self.assertRegex(lastmod.lastmod_regione(), W3C_DATE)

    def test_voce_senza_data_non_la_porta(self):
        self.addCleanup(_con_stato({
            "istat_indicatori_territoriali": {"last_modified": "Fri, 17 Jul 2026 07:02:57 GMT"},
        }))
        # Province BES, altre famiglie: la fonte non e' monitorata.
        self.assertIsNone(lastmod.lastmod_scheda("bes", "provincia"))
        self.assertIsNone(lastmod.lastmod_scheda("eurostat", "regione"))
        self.assertIsNone(lastmod.lastmod_scheda("multiscopo", "regione"))
        # BES regionale senza il suo stato: niente data inventata.
        self.assertIsNone(lastmod.lastmod_scheda("bes", "regione"))

    def test_file_mancante_o_data_illeggibile_non_producono_date(self):
        self.addCleanup(_con_stato({"istat_bes_regioni": {"last_modified": ""},
                                    "istat_indicatori_territoriali": {}}))
        self.assertIsNone(lastmod.lastmod_regione())
        with mock.patch.object(lastmod, "_SOURCE_STATE", Path("/nonexistent/source_state.json")):
            lastmod._date_fonti.cache_clear()
            self.assertIsNone(lastmod.lastmod_scheda("territorial", "regione"))

    def test_la_data_non_dipende_da_oggi(self):
        """Per costruzione: il modulo non legge l'orologio, ne' mtime di file."""
        self.addCleanup(_con_stato({
            "istat_indicatori_territoriali": {"last_modified": "Fri, 17 Jul 2026 07:02:57 GMT"},
        }))
        with mock.patch("app.lastmod.date", create=True) as fake:
            fake.today.return_value = date(2030, 1, 1)
            self.assertEqual(lastmod.lastmod_regione(), "2026-07-17")
        source = Path(lastmod.__file__).read_text(encoding="utf-8")
        for vietato in ("today(", "now(", "utcnow(", "st_mtime", "getmtime"):
            self.assertNotIn(vietato, source)

    def test_il_repo_ha_date_reali(self):
        lastmod._date_fonti.cache_clear()
        regione = lastmod.lastmod_regione()
        self.assertIsNotNone(regione)
        self.assertRegex(regione, W3C_DATE)


if __name__ == "__main__":
    unittest.main()
