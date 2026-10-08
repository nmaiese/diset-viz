"""Il lead visibile: la prosa scritta arriva in pagina, sulla vista che le appartiene.

Una riscrittura delle schede BES ha perso il campo `level` nel front matter e
la vista provinciale ha smesso di rendere il lead senza che un solo test
fallisse (fix 9321e778 e 7825564d). Il guasto è sempre lo stesso: il front
matter perde il livello o viene ignorato, `build_article` scarta l'entry e la
pagina ricade sullo scheletro composto, dove il lead scritto non c'è.

Due scelte tengono in piedi il test:

1. **Il criterio della prosa è quello di `app/editorial_state.py`.** Una scheda
   entra quando la sua entry ha parole (`editorial_state.parole`, la funzione
   che `catalogo()` usa per contare l'articolo) e ha un lead da cercare
   (`editorial_state.get_text`, la lettura che `catalogo()` fa per rilievi,
   parole e impronta). Non si usa la riga di coda `row["lead"]`: è calcolata da
   `build_article` col livello, quindi una scheda il cui `level` è andato perso
   esce dalla riga e il test diventa verde proprio sul guasto che deve
   intercettare.
2. **La frase la renderizza la pagina.** Il frammento nasce passando il lead da
   `analyst_html`, lo stesso filtro con cui la pagina lo mette in testa, e si
   cerca nell'HTML normalizzato (entity aperte, tag tolti, spazi compattati):
   un link o un grassetto dentro il lead non fa cadere il confronto.

La vista provinciale si controlla a parte: la `/province` di una scheda a due
livelli deve rendere un capoverso di testa, e se la prosa appartiene alle
province lì ci deve essere la frase autorata. Non si pretende il lead regionale
su `/province`: quel livello non è quello della entry e la pagina compone il
suo attacco, per disegno (`docs/INDICATOR_PAGES.md`, "Un articolo vale per un
livello territoriale solo").
"""

import html
import re
import unittest
from pathlib import Path

from app import app, editorial_state, sources
from app.indicator_texts import DEFAULT_LEVEL
from app.indicator_view import build_indicator_view
from app.views import analyst_html
from scripts import indicator_store


def _testo(frammento):
    """Il testo che la pagina rende: script e style via, entity aperte, tag tolti,
    spazi compattati. La stessa normalizzazione su atteso e ottenuto."""
    testo = html.unescape(str(frammento))
    testo = re.sub(r"<(script|style)\b.*?</\1>", " ", testo,
                   flags=re.DOTALL | re.IGNORECASE)
    testo = re.sub(r"<[^>]+>", " ", testo)
    return " ".join(testo.split())


def _frase(lead):
    """La prima frase del lead, resa come la rende la pagina.

    Sotto i quaranta caratteri (lead di due parole) prendo le prime dieci
    parole: una frase corta si ripete altrove e non direbbe niente.
    """
    testo = _testo(analyst_html(lead))
    frase = re.split(r"(?<=[.!?])\s+", testo, maxsplit=1)[0]
    return frase if len(frase) >= 40 else " ".join(testo.split()[:10])


def _capoverso(html_pagina):
    """Il capoverso di testa, `page-lead`, come stringa già normalizzata."""
    match = re.search(r'<p class="page-lead">(.*?)</p>', html_pagina, re.DOTALL)
    return _testo(match.group(1)) if match else ""


def _chiave_di(indicator_id, famiglia):
    """La chiave dello store per una scheda: `get_text` prova il nome così com'è,
    poi col prefisso della famiglia (`app/indicator_texts.get_text`)."""
    iid = str(indicator_id)
    if ":" in iid:
        return iid
    prefisso = sources.SOURCES[famiglia].get("internal_prefix") or ""
    return f"{prefisso}{iid}"


def _file_di(chiave):
    percorso = indicator_store.path_for(str(chiave))
    try:
        return str(percorso.relative_to(Path.cwd()))
    except ValueError:
        return str(percorso)


class IlLeadVisibile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        per_scheda = {}
        for riga in editorial_state.build_queue():
            per_scheda.setdefault(riga["id"], []).append(riga)

        cls.casi = []
        for indicator_id, righe in per_scheda.items():
            entry = editorial_state.get_text(indicator_id)
            # Il criterio della prosa, e solo quello: entry con parole scritte.
            if not entry or editorial_state.parole(entry) <= 0:
                continue
            lead = (entry.get("lead") or "").strip()
            famiglia = righe[0]["family"]
            _, raw_id = sources.parse_indicator_code(righe[0]["code"])
            view = build_indicator_view(famiglia, raw_id)
            viste = [(livello["key"], livello["canonical_path"])
                     for livello in view["levels"]]

            caso = {
                "id": indicator_id,
                "file": _file_di(_chiave_di(indicator_id, famiglia)),
                "slug": (viste[0][1].split("/") or ["", "", "?"])[2],
                "lead": lead,
                "frase": _frase(lead) if lead else "",
                "dichiarato": (entry.get("level") or DEFAULT_LEVEL),
                "viste": viste,
                "pagine": {},
            }
            for key, path in viste:
                risposta = cls.client.get(path)
                corpo = risposta.data.decode("utf-8", "replace")
                caso["pagine"][path] = {
                    "livello": key,
                    "stato": risposta.status_code,
                    "testo": _testo(corpo),
                    "capo": _capoverso(corpo),
                }
            cls.casi.append(caso)

    def _problemi(self, condizione):
        """Raccoglie i casi che non passano, con file, slug e URL."""
        return [f"{caso['file']} (slug {caso['slug']}): {problema}"
                for caso in self.casi for problema in condizione(caso)]

    def test_il_lead_scritto_compare_nella_pagina_del_suo_livello(self):
        """La prosa vale per il livello che dichiara: quella pagina deve
        renderla, e una scheda senza nessuna pagina a quel livello ha un front
        matter che la pagina non legge."""
        self.assertTrue(self.casi, "nessuna scheda con prosa scritta trovata")

        def problemi(caso):
            if not caso["lead"]:
                return [f"prosa scritta senza lead ({caso['dichiarato']})"]
            pagine = [p for p in caso["pagine"].values()
                      if p["livello"] == caso["dichiarato"]]
            if not pagine:
                url = ", ".join(path for _, path in caso["viste"])
                return [f"il front matter dichiara '{caso['dichiarato']}' ma la "
                        f"scheda non ha quella vista: {url}"]
            rotte = [f"{path} risponde {p['stato']}"
                     for path, p in caso["pagine"].items()
                     if p["livello"] == caso["dichiarato"] and p["stato"] != 200]
            return rotte + [
                f"{path} non rende il lead: atteso «{caso['frase'][:90]}»"
                for path, p in caso["pagine"].items()
                if p["livello"] == caso["dichiarato"]
                and p["stato"] == 200
                and caso["frase"] not in p["testo"]]

        problemi_trovati = self._problemi(problemi)
        self.assertEqual(problemi_trovati, [],
                         "lead scritto non in pagina:\n"
                         + "\n".join(problemi_trovati))

    def test_il_lead_scritto_compare_in_almeno_una_vista(self):
        """Nessun front matter perso o ignorato: se la scheda ha una prosa, il
        suo lead deve comparire da qualche parte nell'HTML della scheda. Qui
        diventa rosso un `level` tolto dal front matter."""
        def problemi(caso):
            if not caso["lead"]:
                return []
            if any(caso["frase"] in p["testo"] for p in caso["pagine"].values()):
                return []
            url = ", ".join(path for _, path in caso["viste"])
            return [f"il lead non compare su nessuna vista ({url})"]

        problemi_trovati = self._problemi(problemi)
        self.assertEqual(problemi_trovati, [],
                         "lead scritto assente dall'HTML:\n"
                         + "\n".join(problemi_trovati))

    def test_la_vista_provinciale_rende_un_lead(self):
        """La `/province` di una scheda a due livelli ha una testa sua: un
        capoverso ci deve essere sempre, e la frase autorata quando la prosa
        appartiene alle province."""
        def problemi(caso):
            for path, pagina in caso["pagine"].items():
                if pagina["livello"] != "provincia":
                    continue
                if not pagina["capo"]:
                    yield f"{path} non rende nessun capoverso di testa"
                if caso["dichiarato"] == "provincia" and caso["lead"]:
                    if caso["frase"] not in pagina["testo"]:
                        yield f"{path} non rende il lead provinciale: " \
                              f"atteso «{caso['frase'][:90]}»"

        problemi_trovati = self._problemi(lambda caso: list(problemi(caso)))
        self.assertEqual(problemi_trovati, [],
                         "vista provinciale senza lead:\n"
                         + "\n".join(problemi_trovati))


if __name__ == "__main__":
    unittest.main()
