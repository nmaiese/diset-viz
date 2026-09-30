"""RLS di `scripts/supabase_setup.sql` (R1 punto 8): il server scrive i punteggi con il suo
ruolo (BYPASSRLS), quindi il browser, con la chiave anon e il suo JWT, non deve poter
scrivere `daily_scores`, `daily_results`, `player_stats` e `achievements`. Un controllo sul
testo: Postgres vero non c'e' in questa suite."""

import re
import unittest
from pathlib import Path

SQL = (Path(__file__).resolve().parents[2] / "scripts" / "supabase_setup.sql").read_text(encoding="utf-8")


class RlsScrittureTest(unittest.TestCase):
    def test_daily_scores_e_deny_all(self):
        self.assertIn("ALTER TABLE public.daily_scores ENABLE ROW LEVEL SECURITY;", SQL)
        self.assertEqual(re.findall(r"CREATE POLICY \w+\s+ON public\.daily_scores\b", SQL), [])
        self.assertIn("DROP POLICY IF EXISTS own_daily_scores ON public.daily_scores;", SQL)

    def test_le_tabelle_scritte_dal_server_si_leggono_soltanto(self):
        for tabella in ("daily_results", "player_stats", "achievements"):
            with self.subTest(tabella=tabella):
                creazioni = re.findall(rf"CREATE POLICY (\w+)\s+ON public\.{tabella}\b(.*?);", SQL, re.S)
                self.assertEqual(len(creazioni), 1, tabella)
                nome, corpo = creazioni[0]
                self.assertRegex(corpo, r"FOR SELECT TO authenticated")
                self.assertNotRegex(corpo, r"FOR (ALL|INSERT|UPDATE|DELETE)")
                self.assertNotIn("WITH CHECK", corpo)
                self.assertIn("(auth.jwt() ->> 'sub') = auth_id", corpo)

    def test_ogni_policy_si_ricrea_dopo_aver_tolto_la_vecchia_e_la_nuova(self):
        """Il coordinatore lancia il file su una base che ha gia' le vecchie policy: ogni
        CREATE POLICY e' preceduta da un DROP POLICY IF EXISTS per lo stesso nome, e le
        vecchie policy rinominate si tolgono per nome."""
        for nome, tabella in re.findall(r"CREATE POLICY (\w+)\s+ON public\.(\w+)", SQL):
            with self.subTest(nome=nome):
                self.assertIn(f"DROP POLICY IF EXISTS {nome} ON public.{tabella};", SQL)
                self.assertLess(SQL.index(f"DROP POLICY IF EXISTS {nome} ON public.{tabella};"),
                                SQL.index(f"CREATE POLICY {nome} "))
        for vecchia, tabella in (("own_daily_results", "daily_results"), ("own_player_stats", "player_stats"),
                                 ("own_achievements", "achievements"), ("own_daily_scores", "daily_scores")):
            with self.subTest(vecchia=vecchia):
                self.assertIn(f"DROP POLICY IF EXISTS {vecchia} ON public.{tabella};", SQL)

    def test_nessuna_policy_di_scrittura_sulle_quattro_tabelle(self):
        for tabella in ("daily_scores", "daily_results", "player_stats", "achievements"):
            with self.subTest(tabella=tabella):
                for _, corpo in re.findall(rf"CREATE POLICY (\w+)\s+ON public\.{tabella}\b(.*?);", SQL, re.S):
                    self.assertNotRegex(corpo, r"FOR (ALL|INSERT|UPDATE|DELETE)")


if __name__ == "__main__":
    unittest.main()
