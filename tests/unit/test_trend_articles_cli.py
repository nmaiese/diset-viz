"""Smoke test dei moduli di scripts/trend_articles/: ognuno si avvia e dice cosa fa.

La pipeline dei trend vive fuori dal processo web ed e' l'unica parte del
repository che non ha test sotto gli occhi: nessuno la lancia se non serve
qualcosa, quindi una dipendenza non dichiarata o un `argparse` rotto restano
invisibili fino al giorno in cui un pezzo deve uscire. Qui ogni modulo viene
lanciato in un processo separato con `--help`, che e' il modo piu' economico
per provarlo intero: se l'interprete parte, i suoi import reggono e la riga di
comando e' costruita.

Processo separato e non import, perche' un import in-process direbbe "il modulo
si carica" mentre quello che si vuole sapere e' "il comando si puo' lanciare",
come fa un operatore.

Due moduli non ci sono, e non perche' il test sia comodo:

- `derive_sector_injuries` non ha una riga di comando e ignora `--help`: lo
  lancia, va in rete a prendere gli occupati per branca da Istat e **riscrive
  `data/derived/`**, quindi in un test farebbe un download e lascerebbe il
  lavoro sporco. Va messo un `--help` vero nel modulo, non tollerato qui.
- `common` e' una libreria, non un programma: si importa e basta, e questo test
  basta a dirlo perche' lo carica davvero.
"""

import subprocess
import sys
import unittest

from scripts.trend_articles import common

MODULES_DIR = common.ROOT / "scripts" / "trend_articles"
MODULES = sorted(p.stem for p in MODULES_DIR.glob("*.py") if p.stem != "__init__")
# Fuori dal giro, col motivo: vedi il docstring.
SENZA_CLI = {"derive_sector_injuries"}


def _esci(modulo: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", f"scripts.trend_articles.{modulo}", "--help"],
        cwd=common.ROOT, capture_output=True, text=True, timeout=300,
    )


class SmokeTrendArticles(unittest.TestCase):
    def test_il_giro_copre_ogni_modulo_del_pacchetto(self):
        """Il giro non puo' passare perche' l'elenco si e' svuotato, e ogni
        esclusione deve corrispondere a un modulo che esiste davvero: un nome
        sbagliato lascerebbe fuori un modulo senza accorgersene."""
        self.assertLessEqual(SENZA_CLI, set(MODULES))
        self.assertGreaterEqual(len(MODULES) - len(SENZA_CLI), 10)

    def test_ogni_modulo_accoglie_help_ed_esce_zero(self):
        for modulo in MODULES:
            if modulo in SENZA_CLI:
                continue
            with self.subTest(modulo=modulo):
                esito = _esci(modulo)
                self.assertEqual(
                    esito.returncode, 0,
                    f"--help esce {esito.returncode}\n{esito.stdout}\n{esito.stderr}",
                )

    def test_chi_ha_argparse_stampa_il_modo_d_uso(self):
        """Un exit 0 senza testo non dimostra niente: puo' essere un modulo che
        ignora i suoi argomenti. Chi costruisce un parser deve descriverlo."""
        for modulo in MODULES:
            if modulo in SENZA_CLI or "argparse" not in (MODULES_DIR / f"{modulo}.py").read_text(encoding="utf-8"):
                continue
            with self.subTest(modulo=modulo):
                self.assertIn("usage:", _esci(modulo).stdout.lower())


if __name__ == "__main__":
    unittest.main()
