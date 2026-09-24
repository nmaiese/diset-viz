"""I contorni delle 107 province per le mappe della 1.0.

Scrive `app/design/province_paths.json` ({chiave della provincia: attributo d})
nello stesso viewBox delle regioni (0 0 560 660), cosi' i confini regionali di
`italy_paths.json` si possono disegnare sopra le province e combaciano.

La sorgente sono i confini Istat ridistribuiti da openpolis
(github.com/openpolis/geojson-italy, CC BY 4.0), al tag `2023.1`: e' l'ultimo
con le 107 province che usa il BES, Sud Sardegna compresa. Dal 2025 la riforma
sarda ne ha fatte otto, e i dati non le conoscono. Il GeoJSON pesa 5 MB e non
entra nel repo: lo scarica questo script.

La proiezione non si indovina: quella delle regioni e' un Mercatore con una
trasformazione affine, e i coefficienti si ricavano ogni volta dai centroidi
delle venti regioni (`italian-regions.geo.json` contro `italy_paths.json`).
Se lo scarto supera mezzo pixel lo script si ferma.

    bin/py design/v1/tools/province_map.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
import urllib.request
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE_URL = "https://raw.githubusercontent.com/openpolis/geojson-italy/2023.1/geojson/limits_IT_provinces.geojson"
CACHE = Path("/tmp/divario-province-2023.1.geojson")
REGIONS_GEO = ROOT / "app" / "static" / "data" / "italian-regions.geo.json"
REGION_PATHS = ROOT / "app" / "design" / "italy_paths.json"
PROVINCE_CODES = ROOT / "app" / "static" / "data" / "province_codes.csv"
TARGET = ROOT / "app" / "design" / "province_paths.json"

# I nomi del BES che il GeoJSON scrive in un altro modo.
ALIASES = {
    "Aosta": "Valle d'Aosta/Vallée d'Aoste",
    "Bolzano": "Bolzano/Bozen",
    "Reggio Emilia": "Reggio nell'Emilia",
    "Reggio Calabria": "Reggio di Calabria",
}
# Quanto si semplifica, in pixel del viewBox: la mappa piu' grande ne disegna circa 560.
TOLERANCE = 0.7
# Un'isola sotto questa area (pixel quadrati) sparisce, tranne se e' tutta la provincia.
MIN_AREA = 0.6


def norm(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", ascii_name)


def mercator(lon: float, lat: float) -> tuple[float, float]:
    return lon, -math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def outer_rings(geometry: dict) -> list[list[list[float]]]:
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return [polygon[0] for polygon in polygons]


def area(ring: list[tuple[float, float]]) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])) / 2


def centroid(rings: list[list[tuple[float, float]]]) -> tuple[float, float]:
    total = cx = cy = 0.0
    for ring in rings:
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            c = x0 * y1 - x1 * y0
            total += c
            cx += (x0 + x1) * c
            cy += (y0 + y1) * c
    return cx / (3 * total), cy / (3 * total)


def _solve3(m: list[list[float]], v: list[float]) -> list[float]:
    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r in range(3):
            mi[r][i] = v[r]
        out.append(det(mi) / d)
    return out


def fit_transform() -> tuple[list[float], list[float]]:
    """I coefficienti affini dal Mercatore al viewBox, dai centroidi delle regioni."""
    regions = json.loads(REGIONS_GEO.read_text(encoding="utf-8"))
    paths = json.loads(REGION_PATHS.read_text(encoding="utf-8"))
    by_norm = {norm(key): key for key in paths}
    src, dst = [], []
    for feature in regions["features"]:
        key = by_norm.get(norm(feature["properties"]["name"]))
        if key is None:
            raise ValueError(f"regione senza tracciato: {feature['properties']['name']}")
        rings = [[mercator(lon, lat) for lon, lat in ring] for ring in outer_rings(feature["geometry"])]
        svg = [[(float(x), float(y)) for x, y in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", sub)]
               for sub in re.findall(r"M[^M]*", paths[key])]
        src.append(centroid(rings))
        dst.append(centroid(svg))
    rows = [(x, y, 1.0) for x, y in src]
    normal = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    cx = _solve3(normal, [sum(r[i] * d[0] for r, d in zip(rows, dst)) for i in range(3)])
    cy = _solve3(normal, [sum(r[i] * d[1] for r, d in zip(rows, dst)) for i in range(3)])
    worst = max(math.hypot(cx[0] * s[0] + cx[1] * s[1] + cx[2] - d[0], cy[0] * s[0] + cy[1] * s[1] + cy[2] - d[1])
                for s, d in zip(src, dst))
    if worst > 0.5:
        raise ValueError(f"la proiezione non combacia con le regioni: scarto massimo {worst:.2f} px")
    return cx, cy


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Douglas-Peucker, iterativo: le coste frastagliate superano la ricorsione."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (x0, y0), (x1, y1) = points[first], points[last]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        best, index = 0.0, None
        for i in range(first + 1, last):
            px, py = points[i]
            dist = (abs(dy * px - dx * py + x1 * y0 - y1 * x0) / length) if length else math.hypot(px - x0, py - y0)
            if dist > best:
                best, index = dist, i
        if index is not None and best > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(points, keep) if k]


def ring_path(ring: list[tuple[float, float]]) -> str | None:
    """Un anello in coordinate relative (`m`, `l`) a un decimale: a meta' peso
    delle assolute, e la mappa non si disegna mai piu' larga di 560 pixel."""
    points = []
    for x, y in ring:
        p = (round(x * 10), round(y * 10))
        if not points or points[-1] != p:
            points.append(p)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(set(points)) < 3:
        return None

    # Il meno fa gia' da separatore: "-4.4-4.7" e' una coppia valida in SVG.
    def join(parts: list[str]) -> str:
        return "".join(p if i == 0 or p.startswith("-") else " " + p for i, p in enumerate(parts))

    def pair(dx: int, dy: int) -> str:
        return join([f"{dx / 10:g}", f"{dy / 10:g}"])

    (x0, y0), steps = points[0], []
    for (ax, ay), (bx, by) in pairwise(points):
        steps.append(pair(bx - ax, by - ay))
    return f"M{pair(x0, y0)}l" + join(steps) + "z"


def main() -> None:
    if not CACHE.exists():
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
            CACHE.write_bytes(response.read())
    geo = json.loads(CACHE.read_text(encoding="utf-8"))
    cx, cy = fit_transform()

    def project(lon: float, lat: float) -> tuple[float, float]:
        mx, my = mercator(lon, lat)
        return cx[0] * mx + cx[1] * my + cx[2], cy[0] * mx + cy[1] * my + cy[2]

    features = {norm(f["properties"]["prov_name"]): f for f in geo["features"]}
    with PROVINCE_CODES.open(encoding="utf-8", newline="") as handle:
        provinces = list(csv.DictReader(handle, delimiter=";"))
    out = {}
    for row in provinces:
        feature = features.pop(norm(ALIASES.get(row["name"], row["name"])), None)
        if feature is None:
            raise ValueError(f"provincia senza confine: {row['name']}")
        rings = [simplify([project(lon, lat) for lon, lat in ring], TOLERANCE)
                 for ring in outer_rings(feature["geometry"])]
        rings.sort(key=lambda r: abs(area(r)), reverse=True)
        kept = [rings[0]] + [r for r in rings[1:] if abs(area(r)) >= MIN_AREA]
        parts = [p for p in (ring_path(r) for r in kept) if p]
        if not parts:
            raise ValueError(f"il tracciato di {row['name']} e' rimasto vuoto")
        out[row["province_key"]] = "".join(parts)
    if features:
        raise ValueError(f"confini senza provincia nei dati: {sorted(features)}")
    TARGET.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(out)} province, {TARGET.stat().st_size} byte")


if __name__ == "__main__":
    main()
