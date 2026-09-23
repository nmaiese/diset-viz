"""Aritmetica del colore per i token della 1.0: contrasto WCAG, OKLab, daltonismo.

Il daltonismo si simula con le matrici di Machado, Oliveira e Fernandes (2009) a
severita' piena, applicate in RGB lineare. Le distanze sono euclidee in OKLab:
0,1 e' la soglia sotto cui due tinte cominciano a confondersi in un grafico.
"""

from __future__ import annotations

import math

MACHADO = {
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}
VISIONS = ("normale", "protan", "deutan", "tritan")


def hex_to_rgb(value: str) -> tuple[float, ...]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError(f"colore non valido: #{value}")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def linear(hex_value: str) -> tuple[float, ...]:
    return tuple(_lin(c) for c in hex_to_rgb(hex_value))


def luminance(hex_value: str) -> float:
    r, g, b = linear(hex_value)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _oklab_linear(r: float, g: float, b: float) -> tuple[float, ...]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def simulate(hex_value: str, vision: str) -> tuple[float, ...]:
    """RGB lineare visto con la carenza indicata."""
    rgb = linear(hex_value)
    if vision == "normale":
        return rgb
    m = MACHADO[vision]
    return tuple(max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3))


def oklab(hex_value: str, vision: str = "normale") -> tuple[float, ...]:
    return _oklab_linear(*simulate(hex_value, vision))


def distance(a: str, b: str, vision: str = "normale") -> float:
    return math.dist(oklab(a, vision), oklab(b, vision))


def min_distance(a: str, b: str) -> float:
    return min(distance(a, b, v) for v in VISIONS)


def oklch(hex_value: str) -> tuple[float, ...]:
    L, a, b = oklab(hex_value)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def from_oklch(L: float, C: float, H: float) -> str | None:
    """Esadecimale del colore OKLCH, o None se esce dal gamut sRGB."""
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    rgb = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    if any(c < -1e-4 or c > 1 + 1e-4 for c in rgb):
        return None
    return rgb_to_hex(tuple(_gam(c) for c in rgb))


def hue_gap(h1: float, h2: float) -> float:
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)
