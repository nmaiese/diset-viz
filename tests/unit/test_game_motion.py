"""La guardia sul movimento dei fogli del gioco (`frontend/src/game/*.css`).

Regola di prodotto: ogni `@keyframes`, `animation` e `transition` **introdotti dal gioco**
stanno dentro `@media (prefers-reduced-motion: no-preference)`. Fuori da li' lo stato finale
e' gia' quello giusto, e chi ha chiesto di ridurre il movimento non vede niente muoversi. Un
foglio che mette una transizione fuori dal blocco la da' a tutti, e nessun test fallisce:
per questo la regola sta qui.

Le eccezioni che c'erano prima di questa guardia stanno in `ECCEZIONI`, ciascuna col suo
motivo. Una voce nuova li' dentro non e' una scorciatoia: e' una decisione da spiegare. E una
voce che non corrisponde piu' a niente (il foglio e' cambiato) fa fallire il test, cosi' la
lista non invecchia in silenzio.

Dentro `@media (prefers-reduced-motion: reduce)` `animation: none` e `transition: none` sono
il contrario del movimento e si accettano."""

import re
import unittest
from pathlib import Path

GIOCO_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "game"
FOGLI = tuple(sorted(GIOCO_DIR.glob("*.css")))

NO_PREFERENCE = "@media (prefers-reduced-motion: no-preference)"
REDUCE = "@media (prefers-reduced-motion: reduce)"

# (foglio, contesto, proprieta) -> perche' sta fuori da no-preference. Il contesto e' il
# selettore (con gli spazi normalizzati) o `@keyframes nome`.
ECCEZIONI = {}


def _normalizza(testo):
    return re.sub(r"\s+", " ", testo).strip()


def _blocchi(css):
    """Le dichiarazioni di movimento di un foglio: una lista di `(contesto, proprieta,
    valore, dentro_no_preference, dentro_reduce)`, con `@keyframes nome` come contesto dei
    suoi fotogrammi. Un parser a parentesi graffe: il CSS del gioco e' piatto e non ha
    stringhe con graffe dentro."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    pila = []  # le intestazioni dei blocchi aperti
    trovate = []
    corrente = ""
    for carattere in css:
        if carattere == "{":
            pila.append(_normalizza(corrente))
            corrente = ""
        elif carattere == "}":
            _dichiarazioni(corrente, pila, trovate)
            corrente = ""
            if pila:
                pila.pop()
        elif carattere == ";":
            _dichiarazioni(corrente, pila, trovate)
            corrente = ""
        else:
            corrente += carattere
    return trovate


def _dichiarazioni(testo, pila, trovate):
    testo = _normalizza(testo)
    if not pila:
        return
    media = [h for h in pila if h.startswith("@media")]
    dentro_no_pref = any(_normalizza(h) == NO_PREFERENCE for h in media)
    dentro_reduce = any(_normalizza(h) == REDUCE for h in media)
    keyframes = [h for h in pila if h.startswith("@keyframes")]
    if testo == "" and keyframes and pila[-1] == keyframes[-1]:
        # La chiusura di un @keyframes: il blocco stesso e' la novita'.
        trovate.append((keyframes[-1], "@keyframes", "", dentro_no_pref, dentro_reduce))
        return
    if ":" not in testo:
        return
    proprieta, _, valore = testo.partition(":")
    proprieta = proprieta.strip().lower()
    if proprieta.startswith("transition") or proprieta.startswith("animation"):
        # Il contesto e' il selettore piu' vicino che non e' un @media.
        contesto = next((h for h in reversed(pila) if not h.startswith("@media")), pila[-1])
        trovate.append((contesto, proprieta, _normalizza(valore), dentro_no_pref, dentro_reduce))


def violazioni(css):
    """Le voci fuori da `no-preference` che non sono un `none` dentro `reduce`."""
    fuori = set()
    for contesto, proprieta, valore, no_pref, reduce in _blocchi(css):
        if no_pref:
            continue
        if reduce and proprieta != "@keyframes" and valore in ("none", "0s", "0ms"):
            continue
        fuori.add((contesto, proprieta))
    return fuori


class ParserTest(unittest.TestCase):
    """La guardia sa fallire: senza queste prove un parser che non trova niente passerebbe."""

    def test_trova_una_transizione_fuori_dal_blocco(self):
        css = ".a { color: red; transition: opacity .3s; }"
        self.assertEqual(violazioni(css), {(".a", "transition")})

    def test_trova_animation_e_le_sue_proprieta(self):
        css = ".a { animation-name: x; animation-duration: 1s; }"
        self.assertEqual(violazioni(css), {(".a", "animation-name"), (".a", "animation-duration")})

    def test_trova_un_keyframes_fuori_dal_blocco(self):
        css = "@keyframes x { from { opacity: 0 } to { opacity: 1 } }"
        self.assertEqual(violazioni(css), {("@keyframes x", "@keyframes")})

    def test_accetta_tutto_dentro_no_preference(self):
        css = """@media (prefers-reduced-motion: no-preference) {
            .a { transition: opacity .3s; animation: x 1s; }
            @keyframes x { from { opacity: 0 } to { opacity: 1 } }
        }"""
        self.assertEqual(violazioni(css), set())

    def test_no_preference_su_piu_righe_vale_lo_stesso(self):
        css = "@media (prefers-reduced-motion: no-preference)\n  {\n .a { transition: opacity .3s }\n}"
        self.assertEqual(violazioni(css), set())

    def test_un_altro_media_non_basta(self):
        css = "@media (max-width: 600px) { .a { transition: opacity .3s } }"
        self.assertEqual(violazioni(css), {(".a", "transition")})
        css = "@media (prefers-reduced-motion: reduce) { .a { transition: opacity .3s } }"
        self.assertEqual(violazioni(css), {(".a", "transition")})

    def test_none_dentro_reduce_e_il_contrario_del_movimento(self):
        css = "@media (prefers-reduced-motion: reduce) { .a { animation: none; transition: none } }"
        self.assertEqual(violazioni(css), set())

    def test_i_commenti_non_contano(self):
        css = "/* .a { transition: opacity .3s } */ .b { color: red }"
        self.assertEqual(violazioni(css), set())

    def test_non_confonde_proprieta_che_non_c_entrano(self):
        css = ".a { transform: scale(1); will-change: transform; color: red }"
        self.assertEqual(violazioni(css), set())


class FogliDelGiocoTest(unittest.TestCase):
    def test_ci_sono_i_fogli(self):
        self.assertTrue(FOGLI, "nessun foglio in frontend/src/game/")
        self.assertIn("game-base.css", {f.name for f in FOGLI})

    def test_ogni_movimento_sta_dentro_no_preference_salvo_le_eccezioni_motivate(self):
        trovate = {}
        for foglio in FOGLI:
            for contesto, proprieta in violazioni(foglio.read_text(encoding="utf-8")):
                trovate[(foglio.name, contesto, proprieta)] = True
        nuove = sorted(set(trovate) - set(ECCEZIONI))
        self.assertEqual(
            nuove, [],
            "movimento fuori da @media (prefers-reduced-motion: no-preference): spostalo li' dentro "
            "(lo stato finale fuori dal blocco e' gia' quello giusto) o, se e' un'eccezione "
            "preesistente, motivala in ECCEZIONI",
        )

    def test_ogni_eccezione_ha_un_motivo_e_corrisponde_a_qualcosa(self):
        viste = set()
        for foglio in FOGLI:
            for contesto, proprieta in violazioni(foglio.read_text(encoding="utf-8")):
                viste.add((foglio.name, contesto, proprieta))
        for chiave, motivo in ECCEZIONI.items():
            with self.subTest(chiave=chiave):
                self.assertGreaterEqual(len(motivo.strip()), 20, "l'eccezione va motivata")
                self.assertIn(chiave, viste, "l'eccezione non corrisponde piu' a niente: toglila")

    def test_il_blocco_dei_token_di_movimento_c_e(self):
        base = (GIOCO_DIR / "game-base.css").read_text(encoding="utf-8")
        for token in ("--mo-fast: 120ms", "--mo-base: 220ms", "--mo-slow: 360ms", "--mo-out:", "--mo-in:"):
            self.assertIn(token, base)


if __name__ == "__main__":
    unittest.main()
