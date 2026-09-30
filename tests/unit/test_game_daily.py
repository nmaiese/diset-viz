import unittest
from datetime import date, datetime, timezone

from app.game_daily import oggi_roma, prossima_sfida_roma


class TestOggiRoma(unittest.TestCase):
    def test_dopo_le_23_utc_a_roma_e_gia_il_giorno_dopo(self):
        # 23:30 UTC del 30 settembre: a Roma (CEST, UTC+2) sono le 01:30 del 1 ottobre.
        now = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(oggi_roma(now), date(2026, 10, 1))

    def test_prima_delle_22_utc_il_giorno_e_lo_stesso(self):
        now = datetime(2026, 9, 30, 21, 59, tzinfo=timezone.utc)
        self.assertEqual(oggi_roma(now), date(2026, 9, 30))

    def test_ora_solare_cambia_la_soglia(self):
        # In inverno (CET, UTC+1) il giorno cambia alle 23:00 UTC, non alle 22:00.
        self.assertEqual(oggi_roma(datetime(2026, 12, 15, 22, 30, tzinfo=timezone.utc)), date(2026, 12, 15))
        self.assertEqual(oggi_roma(datetime(2026, 12, 15, 23, 30, tzinfo=timezone.utc)), date(2026, 12, 16))

    def test_prossima_sfida_e_la_mezzanotte_di_roma(self):
        # Mezzanotte del 1 ottobre a Roma (CEST) = 22:00 UTC del 30 settembre.
        self.assertEqual(prossima_sfida_roma(date(2026, 9, 30)), "2026-09-30T22:00:00+00:00")
        # In inverno (CET) = 23:00 UTC.
        self.assertEqual(prossima_sfida_roma(date(2026, 12, 15)), "2026-12-15T23:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
