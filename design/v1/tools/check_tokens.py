"""Verifica i token della 1.0: contrasti WCAG, rampe, daltonismo, convivenza col marchio.

    bin/py design/v1/tools/check_tokens.py                  controlla, esce non zero se una soglia salta
    bin/py design/v1/tools/check_tokens.py --categoriale    cerca una palette categoriale che regga

Le soglie: testo 4,5:1, controlli e oggetti grafici 3:1 (WCAG 2.2, 1.4.3 e
1.4.11). Per le tinte dei dati la distanza minima in OKLab sotto le quattro
visioni (normale, protanopia, deuteranopia, tritanopia).

Il sotto-marchio del gioco (`tokens.json`, chiave "game", e il blocco `--game-*`
di `app/static/css/ds/system.css`) ha le sue soglie: contrasti, tinta lontana
dall'arancio e dalla rampa blu, niente verde e niente rosso, lontano dai colori
dei dati, e giusto e sbagliato distinguibili anche in acromatopsia.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import sys
from pathlib import Path

from colors import (
    VISIONS,
    contrast,
    distance,
    from_oklch,
    hue_gap,
    luminance,
    min_distance,
    oklch,
)

TOKENS = Path(__file__).resolve().parents[1] / "tokens" / "tokens.json"
SYSTEM_CSS = Path(__file__).resolve().parents[3] / "app" / "static" / "css" / "ds" / "system.css"

TEXT = ("ink", "text-2", "muted", "link", "accent", "error", "warning", "success")
SURFACES = ("bg", "surface-1", "surface-2")
CAT_MIN = 0.10  # distanza minima fra due tinte categoriali, in ogni visione
# Quattro tinte e non cinque: con marchio, accento e teal di oggi esclusi, una
# quinta tinta che regga in ogni visione non esiste. Oltre quattro serie si usano
# etichette dirette e la tabella.
CAT_CMP_MIN = 0.08  # distanza minima dal grigio di contesto
SEQ_STEP_MIN = 0.07  # distanza minima fra due passi vicini della rampa

# Il gioco. Le sue tinte sono d'interfaccia, mai dei dati.
# accent-strong e' solo un fondo (il bottone sotto il puntatore o premuto): si
# prova col testo che ci sta sopra e come controllo, non come testo.
GAME_TEXT = ("accent", "right", "wrong")
GAME_HUE_MIN = 40  # gradi di tinta dall'arancio e da ogni passo della rampa blu
GAME_SEMAPHORE_HUE_MIN = 35  # gradi dal verde e dal rosso: sono gia' giusto e sbagliato
GAME_DATA_MIN = 0.1  # distanza dai colori dei dati (rampa, categoriale, ripartizioni)
GAME_RW_MIN = 0.12  # giusto contro sbagliato, in ogni visione e in scala di grigi
GAME_ACTION_MIN = 0.1  # l'azione del gioco contro giusto e sbagliato
# Le quattro visioni della prova del gioco: le tre carenze e l'acromatopsia.
# L'acromatopsia qui e non in colors.VISIONS: le prove dei dati non la chiedono.
GAME_VISIONS = ("protan", "deutan", "tritan", "acroma")


def game_distance(a: str, b: str, vision: str) -> float:
    """Distanza OKLab; in acromatopsia conta solo la luminosita' (grigio a pari Y)."""
    if vision == "acroma":
        return abs(luminance(a) ** (1 / 3) - luminance(b) ** (1 / 3))
    return distance(a, b, vision)


def css_game_tokens(css: str) -> dict[str, dict[str, str]]:
    """I `--game-*` di system.css, del chiaro (`:root`) e dello scuro."""
    found: dict[str, dict[str, str]] = {}
    for theme, head in (("light", r"^:root\s*\{"), ("dark", r'^\[data-theme="dark"\]\s*\{')):
        m = re.search(head, css, re.M)
        body = css[m.end() : css.index("\n}", m.end())] if m else ""
        found[theme] = dict(re.findall(r"--game-([a-z-]+):\s*(#[0-9a-fA-F]{3,8})\s*;", body))
    return found


def check(tokens: dict) -> list[str]:
    failures: list[str] = []
    logo = tokens["logo"]

    def need(ok: bool, message: str) -> None:
        print(("  ok   " if ok else "  NO   ") + message)
        if not ok:
            failures.append(message)

    for theme in ("light", "dark"):
        t = tokens[theme]
        print(f"\n== {theme} ==")
        print("testo, 4,5:1 su ogni superficie")
        for name in TEXT:
            for surface in SURFACES:
                r = contrast(t[name], t[surface])
                need(r >= 4.5, f"{theme} {name} su {surface}: {r:.2f}")
        for fill in ("accent", "accent-strong"):
            r = contrast(t["on-accent"], t[fill])
            need(r >= 4.5, f"{theme} on-accent su {fill} (bottone primario): {r:.2f}")
        print("controlli e oggetti grafici, 3:1")
        for name in ("control-border", "focus", "accent", "cmp"):
            for surface in SURFACES:
                r = contrast(t[name], t[surface])
                need(r >= 3, f"{theme} {name} su {surface}: {r:.2f}")
        r = contrast(t["data-null-stripe"], t["data-null"])
        need(r >= 3, f"{theme} tratteggio del dato mancante sul suo fondo: {r:.2f}")
        r = contrast(t["data-focus"], t["cmp"])
        d = min_distance(t["data-focus"], t["cmp"])
        need(r >= 1.4 and d >= 0.1, f"{theme} evidenza contro contesto: {r:.2f}:1, distanza minima {d:.3f}")

        print("rampa sequenziale")
        seq = [t[f"seq-{i}"] for i in range(1, 7)]
        lums = [luminance(c) for c in seq]
        monotone = all(a > b for a, b in itertools.pairwise(lums)) if theme == "light" else all(a < b for a, b in itertools.pairwise(lums))
        need(monotone, f"{theme} rampa monotona dal poco al molto contrasto col fondo")
        r = contrast(seq[0], t["bg"])
        need(r >= 1.15, f"{theme} primo passo staccato dal fondo: {r:.2f}")
        need(contrast(seq[-1], t["bg"]) >= 3, f"{theme} ultimo passo a 3:1 sul fondo: {contrast(seq[-1], t['bg']):.2f}")
        steps = [min_distance(a, b) for a, b in itertools.pairwise(seq)]
        need(min(steps) >= SEQ_STEP_MIN, f"{theme} passi vicini distinguibili in ogni visione: minimo {min(steps):.3f}")
        d = min(min_distance(seq[0], t["data-null"]), 9)
        print(f"  info {theme} primo passo contro dato mancante: {d:.3f} (il tratteggio li separa)")
        for i, c in enumerate(seq, 1):
            r = contrast(t[f"seq-label-{i}"], c)
            need(r >= 4.5, f"{theme} etichetta sul passo {i}: {r:.2f}")

        print("rampa divergente")
        neg, pos = luminance(t["div-neg-3"]), luminance(t["div-pos-3"])
        need(abs(neg - pos) < 0.03, f"{theme} estremi simmetrici: luminanze {neg:.3f} e {pos:.3f}")
        neg, pos = luminance(t["div-neg-2"]), luminance(t["div-pos-2"])
        need(abs(neg - pos) < 0.04, f"{theme} passi intermedi simmetrici: luminanze {neg:.3f} e {pos:.3f}")

        print("categoriale")
        cats = [t[f"cat-{i}"] for i in range(1, 5)]
        for i, c in enumerate(cats, 1):
            r = contrast(c, t["bg"])
            need(r >= 3, f"{theme} cat-{i} {c} sul fondo: {r:.2f}")
            dc = min_distance(c, t["cmp"])
            need(dc >= CAT_CMP_MIN, f"{theme} cat-{i} contro il grigio di contesto: {dc:.3f}")
            dt = distance(c, logo["old-teal"])
            need(dt >= 0.1, f"{theme} cat-{i} lontano dal teal di oggi: {dt:.3f}")
        worst = min(((min_distance(a, b), i, j) for (i, a), (j, b) in itertools.combinations(enumerate(cats, 1), 2)))
        need(worst[0] >= CAT_MIN, f"{theme} categoriale, coppia piu' vicina cat-{worst[1]}/cat-{worst[2]}: {worst[0]:.3f}")

        print("ripartizioni (Nord, Centro, Mezzogiorno)")
        areas = [t["area-nord"], t["area-centro"], t["area-sud"]]
        for name, c in zip(("nord", "centro", "sud"), areas):
            need(min(contrast(c, t[s]) for s in ("bg", "surface-1")) >= 3, f"{theme} area-{name} {c} a 3:1 sui fondi")
            need(min_distance(c, t["cmp"]) >= 0.1, f"{theme} area-{name} lontana dal grigio di contesto: {min_distance(c, t['cmp']):.3f}")
            need(distance(c, t["accent"]) >= 0.12, f"{theme} area-{name} lontana dall'accento: {distance(c, t['accent']):.3f}")
        worst = min(min_distance(a, b) for a, b in itertools.combinations(areas, 2))
        need(worst >= 0.12, f"{theme} ripartizioni distinguibili in ogni visione: minimo {worst:.3f}")

    print("\n== convivenza col simbolo ==")
    for theme in ("light", "dark"):
        acc = tokens[theme]["accent"]
        for mark in ("green", "red"):
            per = {v: round(distance(acc, logo[mark], v), 3) for v in VISIONS}
            print(f"  info {theme} accento {acc} contro {mark} del simbolo {logo[mark]}: {per}")
        d = distance(acc, logo["old-coral"])
        print(f"  info {theme} accento contro il corallo di oggi: {d:.3f}")
    for mark in ("green", "red"):
        h = oklch(logo[mark])[2]
        for i in range(1, 5):
            hc = oklch(tokens["light"][f"cat-{i}"])[2]
            need(hue_gap(h, hc) >= 20, f"cat-{i} non richiama il {mark} del simbolo: {hue_gap(h, hc):.0f} gradi di tinta")

    failures += check_game(tokens)
    return failures


def check_game(tokens: dict, css: str | None = None) -> list[str]:
    """Il sotto-marchio del gioco: contrasti, tinta, distanza dai dati, giusto e sbagliato."""
    failures: list[str] = []
    logo = tokens["logo"]

    def need(ok: bool, message: str) -> None:
        print(("  ok   " if ok else "  NO   ") + message)
        if not ok:
            failures.append(message)

    for theme in ("light", "dark"):
        t, g = tokens[theme], tokens["game"][theme]
        print(f"\n== gioco, {theme} ==")
        print("testo, 4,5:1")
        for name in GAME_TEXT:
            for surface in SURFACES:
                r = contrast(g[name], t[surface])
                need(r >= 4.5, f"{theme} game-{name} su {surface}: {r:.2f}")
        for name, wash in (("accent", "wash"), ("right", "right-wash"), ("wrong", "wrong-wash")):
            r = contrast(g[name], g[wash])
            need(r >= 4.5, f"{theme} game-{name} su game-{wash}: {r:.2f}")
        for wash in ("wash", "right-wash", "wrong-wash"):
            r = contrast(t["ink"], g[wash])
            need(r >= 4.5, f"{theme} ink su game-{wash}: {r:.2f}")
        for fill in ("accent", "accent-strong"):
            r = contrast(g["on-accent"], g[fill])
            need(r >= 4.5, f"{theme} game-on-accent su game-{fill} (bottone di gioco): {r:.2f}")
        print("controlli, 3:1")
        for name in ("accent", "accent-strong", "right", "wrong"):
            r = min(contrast(g[name], t[s]) for s in SURFACES)
            need(r >= 3, f"{theme} game-{name} come bordo o icona, sul fondo peggiore: {r:.2f}")

        print("tinta: lontana dall'arancio e dalla rampa, ne' verde ne' rosso")
        semaphore = {"success": t["success"], "error": t["error"], "game-right": g["right"],
                     "game-wrong": g["wrong"], "verde del simbolo": logo["green"], "rosso del simbolo": logo["red"]}
        for name in ("accent", "accent-strong"):
            h = oklch(g[name])[2]
            gap = hue_gap(h, oklch(t["accent"])[2])
            need(gap >= GAME_HUE_MIN, f"{theme} game-{name} (tinta {h:.0f}) dall'arancio: {gap:.0f} gradi")
            gap = min(hue_gap(h, oklch(t[f"seq-{i}"])[2]) for i in range(1, 7))
            need(gap >= GAME_HUE_MIN, f"{theme} game-{name} dalla rampa blu: {gap:.0f} gradi")
            near, gap = min(((k, hue_gap(h, oklch(v)[2])) for k, v in semaphore.items()), key=lambda x: x[1])
            need(gap >= GAME_SEMAPHORE_HUE_MIN, f"{theme} game-{name} dal verde e dal rosso: {gap:.0f} gradi ({near})")

        print("un colore d'interfaccia, non dei dati")
        data = {k: v for k, v in t.items() if k.startswith(("seq-", "cat-", "area-", "div-")) and "label" not in k}
        data["accent"] = t["accent"]
        for name in ("accent", "accent-strong"):
            near = min(data, key=lambda k: distance(g[name], data[k]))
            d = distance(g[name], data[near])
            need(d >= GAME_DATA_MIN, f"{theme} game-{name} dal colore dei dati piu' vicino ({near}): {d:.3f}")
            cvd = min(min_distance(g[name], t[f"seq-{i}"]) for i in range(1, 7))
            print(f"  info {theme} game-{name} dalla rampa blu, visione peggiore: {cvd:.3f} (mai sulla mappa dei dati)")

        print("giusto e sbagliato, nelle quattro visioni")
        for vision in ("normale", *GAME_VISIONS):
            d = game_distance(g["right"], g["wrong"], vision)
            need(d >= GAME_RW_MIN, f"{theme} game-right contro game-wrong, {vision}: {d:.3f}")
        for vision in ("normale", *GAME_VISIONS):
            d = game_distance(t["success"], t["error"], vision)
            print(f"  info {theme} success contro error del sito, {vision}: {d:.3f}")
        for mark in ("right", "wrong"):
            d = min(distance(g["accent"], g[mark], v) for v in VISIONS)
            need(d >= GAME_ACTION_MIN, f"{theme} game-accent contro game-{mark}, visione peggiore: {d:.3f}")

    print("\n== gioco, system.css allineato a tokens.json ==")
    if css is None:
        css = SYSTEM_CSS.read_text(encoding="utf-8")
    found = css_game_tokens(css)
    for theme in ("light", "dark"):
        want = {k: v.lower() for k, v in tokens["game"][theme].items()}
        got = {k: v.lower() for k, v in found[theme].items()}
        need(got == want, f"{theme} --game-* di system.css uguali a tokens.json"
             + ("" if got == want else f": diversi {sorted(set(want.items()) ^ set(got.items()))}"))
    return failures


def search_categorical(tokens: dict, theme: str) -> list[str]:
    """Cerca cinque tinte che reggano in ogni visione, lontane da marchio, teal e accento."""
    t, logo = tokens[theme], tokens["logo"]
    green_h, red_h = oklch(logo["green"])[2], oklch(logo["red"])[2]
    accent = t["accent"]
    accent_h = oklch(accent)[2]
    lightness = [x / 100 for x in range(32, 73, 3)] if theme == "light" else [x / 100 for x in range(62, 93, 3)]
    candidates = []
    for L in lightness:
        for C in (0.07, 0.09, 0.11, 0.13) if theme == "dark" else (0.07, 0.09, 0.11, 0.13, 0.15, 0.17):
            for H in range(0, 360, 6):
                # Niente verde e rosso del simbolo, niente arancio dell'accento:
                # una serie arancio accanto all'evidenza arancio si confonde.
                if hue_gap(H, green_h) < 25 or hue_gap(H, red_h) < 22 or hue_gap(H, accent_h) < 35:
                    continue
                c = from_oklch(L, C, H)
                if not c:
                    continue
                if min(contrast(c, t[s]) for s in ("bg", "surface-1")) < 3:
                    continue
                if min_distance(c, t["cmp"]) < CAT_CMP_MIN + 0.02:
                    continue
                if distance(c, logo["old-teal"]) < 0.12 or distance(c, accent) < 0.1:
                    continue
                candidates.append(c)
    print(f"{theme}: {len(candidates)} candidati")
    # Il primo e' il blu notte della rampa, che lega la categoriale ai dati.
    start = tokens[theme]["seq-6"] if theme == "light" else tokens[theme]["seq-5"]
    best: tuple[float, list[str]] = (0.0, [])
    for first in [start] + candidates[:: max(1, len(candidates) // 40)]:
        chosen = [first]
        while len(chosen) < 5:
            pool = [c for c in candidates if c not in chosen]
            nxt = max(pool, key=lambda c: min(min_distance(c, x) for x in chosen))
            chosen.append(nxt)
        score = min(min_distance(a, b) for a, b in itertools.combinations(chosen, 2))
        if score > best[0]:
            best = (score, chosen)
    score, chosen = best
    # In ordine di luminosita', cosi' la palette regge anche in scala di grigi.
    chosen.sort(key=luminance)
    print(f"{theme}: distanza minima {score:.3f}")
    for c in chosen:
        L, C, H = oklch(c)
        print(f"  {c}  L {L:.2f}  C {C:.2f}  H {H:.0f}  su fondo {contrast(c, t['bg']):.2f}  dal contesto {min_distance(c, t['cmp']):.3f}")
    return chosen


def main() -> None:
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    if "--categoriale" in sys.argv:
        for theme in ("light", "dark"):
            search_categorical(tokens, theme)
        return
    failures = check(tokens)
    print(f"\n{len(failures)} soglie saltate" if failures else "\ntutte le soglie reggono")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
