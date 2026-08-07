"""La scelta dell'esempio misurata sul **catalogo vero**.

Costruisce sessanta pacchetti veri, quindi ha bisogno di un giro reale: era il
file piu' lento di `tests/unit/` (2,1 s dei 4,7 s della suite veloce) per questa
sola classe. La mappa e la funzione di scelta, che girano su angoli sintetici,
restano in `tests/unit/test_officina_esempi.py`.

Che cosa compra: che la scelta **vari**. Una biblioteca di esempi che ne serve
sempre uno e' l'uniformita' rientrata dalla porta che questa mappa esiste per
chiudere, e non la vedrebbe nessun test su un angolo inventato: serve la
distribuzione degli angoli che il catalogo produce davvero.
"""
import unittest

from officina import esempi


class OnTheRealCatalogue(unittest.TestCase):
    def test_the_choice_varies_across_indicators(self):
        from app import sources
        from app.atlas_catalog import get_atlas_catalog
        from collections import Counter
        from packs import build

        chosen = Counter()
        for item in get_atlas_catalog()["indicators"][:60]:
            family, raw = sources.split_internal_id(item["id"])
            try:
                pack = build.build_pack(family, raw)
            except Exception:
                continue
            if pack:
                chosen[esempi.pick(pack["angles"])] += 1

        self.assertGreater(sum(chosen.values()), 40)
        self.assertGreaterEqual(len(chosen), 3,
                                f"un solo modello per tutti: {chosen}")
        top = chosen.most_common(1)[0][1] / sum(chosen.values())
        self.assertLess(top, 0.7, f"un modello copre il {top:.0%}: {chosen}")


if __name__ == "__main__":
    unittest.main()
