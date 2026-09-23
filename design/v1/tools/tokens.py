"""Genera `src/css/tokens.css` da `tokens/tokens.json`.

    bin/py design/v1/tools/tokens.py

Le taglie sono fluide fra 375 e 1200 pixel di finestra, dal valore "mobile" al
valore "desktop". Il tema scuro segue il sistema, a meno che la pagina non porti
`data-theme="light"`, e si forza con `data-theme="dark"`: lo stesso schema del
sito. Ogni blocco scuro ridefinisce tutti i colori, cosi' niente del chiaro
trapela.
"""

from __future__ import annotations

import json
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SOURCE = V1 / "tokens" / "tokens.json"
TARGET = V1 / "src" / "css" / "tokens.css"
VW_MIN, VW_MAX = 375, 1200


def fluid(mobile: float, desktop: float) -> str:
    if mobile == desktop:
        return f"{mobile}px"
    slope = (desktop - mobile) / (VW_MAX - VW_MIN)
    base = mobile - slope * VW_MIN
    return f"clamp({mobile}px, {base:.3f}px + {slope * 100:.4f}vw, {desktop}px)"


def colors(block: dict, indent: str) -> str:
    return "\n".join(f"{indent}--{name}: {value};" for name, value in block.items())


def build(tokens: dict) -> str:
    lines = [
        "/* Generato da design/v1/tools/tokens.py a partire da tokens/tokens.json.",
        "   Non si modifica a mano: si cambia il JSON e si rigenera. */",
        "",
        ":root {",
        "  color-scheme: light;",
        f"  --font-sans: {tokens['fonts']['sans']};",
        f"  --font-mono: {tokens['fonts']['mono']};",
    ]
    for role, spec in tokens["type"].items():
        lines += [
            f"  --fs-{role}: {fluid(spec['mobile'], spec['desktop'])};",
            f"  --lh-{role}: {spec['lh']};",
            f"  --fw-{role}: {spec['weight']};",
            f"  --tr-{role}: {spec['tracking']};",
        ]
    for step, px in tokens["space"].items():
        lines.append(f"  --space-{step}: {px}px;")
    for name, value in tokens["layout"].items():
        lines.append(f"  --{name}: {value};")
    for name, value in tokens["motion"].items():
        lines.append(f"  --motion-{name}: {value};")
    lines.append(colors(tokens["light"], "  "))
    lines += [
        "}",
        "",
        "@media (prefers-color-scheme: dark) {",
        '  :root:not([data-theme="light"]) {',
        "    color-scheme: dark;",
        colors(tokens["dark"], "    "),
        "  }",
        "}",
        "",
        ':root[data-theme="dark"] {',
        "  color-scheme: dark;",
        colors(tokens["dark"], "  "),
        "}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    tokens = json.loads(SOURCE.read_text(encoding="utf-8"))
    missing = set(tokens["light"]) ^ set(tokens["dark"])
    if missing:
        raise ValueError(f"chiaro e scuro devono avere gli stessi colori, differiscono su: {sorted(missing)}")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(build(tokens), encoding="utf-8")
    print(f"scritto {TARGET.relative_to(V1)}")


if __name__ == "__main__":
    main()
