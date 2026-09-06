"""Un campo scritto in un articolo deve essere un campo che qualcuno legge.

Il 6 settembre 2026 tre articoli scritti dalla redazione portavano il titolo del
pezzo sotto la chiave `titolo`. Nessuno legge `titolo`: `indicator_texts` legge
`h1` e `seo_title`. Il titolo veniva quindi accettato dal file, salvato in git,
mostrato in PR, e buttato via a ogni render. Le tre pagine tenevano l'H1
amministrativo derivato dal nome dell'indicatore, e niente falliva.

E' il guasto che questo repo paga piu' spesso: due lati che si parlano per nome
di campo e nessuno dei due che dichiari il contratto. `load_all` non valida le
chiavi apposta (un file rotto deve costare un articolo, non il catalogo), quindi
la dichiarazione sta qui.

Le chiavi sono divise in due gruppi perche' sono due cose diverse:

- **contenuto**: qualcosa che la pagina rende. Se una di queste sparisce dal
  lettore, la pagina perde testo.
- **provenienza**: che cosa ha prodotto l'articolo e quando. La pagina non le
  legge di proposito, ma stanno nel file perche' un articolo aperto a mano
  dica da dove viene.

Aggiungere una chiave nuova vuol dire aggiungerla qui, in uno dei due gruppi.
E' il punto: nel gruppo sbagliato non ci finisce per distrazione, perche' per
metterla fra il contenuto bisogna sapere chi la legge.
"""

import json
import unittest
from pathlib import Path

from app import indicator_texts

RADICE = Path(__file__).resolve().parents[2] / "content" / "indicators"

# Rese in pagina. Ognuna ha un lettore: `indicator_texts.build_article` per
# lead, sections, h1, seo_title, roles_covered e vintage, `visible_sources` per
# fonti, `build_article` di nuovo per level, `cited_claims` per corpus.
CONTENUTO = {
    "key",            # ripete la chiave del file, la toglie `load_all`
    "lead",
    "sections",
    "fonti",
    "vintage",
    "level",
    "h1",             # titolo H1 autorato, e da qui deriva anche il titolo SERP
    "seo_title",      # titolo SERP autorato, quando diverso dall'H1
    "roles_covered",
    "corpus",
}

# Scritte dalla catena, non lette dalla pagina. Restano perche' dicono da dove
# viene l'articolo, non perche' qualcuno le renda.
PROVENIENZA = {
    "reviewed_at",
    "reviewed_vintage",
    "angolo",          # l'angolo scelto, nelle prime run
    "angolo_scelto",   # lo stesso, nel nome che usa `motore pubblica`
    "origine",
    "scritto_il",
    "costo",
}

NOTE = CONTENUTO | PROVENIENZA


class LeChiaviDegliArticoliSonoDichiarate(unittest.TestCase):
    def test_nessun_articolo_porta_una_chiave_che_nessuno_ha_dichiarato(self):
        colpevoli = []
        for percorso in sorted(RADICE.glob("*.json")):
            voce = json.loads(percorso.read_text(encoding="utf-8"))
            for chiave in sorted(set(voce) - NOTE):
                colpevoli.append(f"{percorso.name}: {chiave}")
        self.assertEqual(colpevoli, [], "\n".join(
            ["chiavi che nessuno legge e nessuno ha dichiarato: se e' contenuto va "
             "letta, se e' provenienza va messa in PROVENIENZA di questo test"]
            + colpevoli))

    def test_le_chiavi_di_contenuto_sono_davvero_lette(self):
        """Il lato opposto: una chiave dichiarata contenuto deve uscire da `build_article`.

        Senza questo, `CONTENUTO` diventa un elenco di buone intenzioni: bastava
        scriverci dentro `titolo` per far passare il test di sopra lasciando il
        difetto in pagina."""
        rese = set(indicator_texts.build_article("17"))
        # `key` la toglie `load_all`, `level` filtra l'entry invece di uscire,
        # `roles_covered` e `corpus` decidono che cosa esce senza uscire loro.
        attese = CONTENUTO - {"key", "level", "roles_covered", "corpus", "vintage"}
        self.assertLessEqual(attese, rese, f"dichiarate contenuto ma non rese: "
                                           f"{sorted(attese - rese)}")


if __name__ == "__main__":
    unittest.main()
