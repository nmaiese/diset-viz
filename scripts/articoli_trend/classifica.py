"""Fase 3: dal tema all'indicatore, e la classifica di che cosa scrivere.

Ogni coppia tema-indicatore prende tre punteggi fra 0 e 1, e ognuno si
legge da solo nel file di uscita, con la sua motivazione:

**interesse**, quanto il tema e' cercato e discusso adesso:
  - `notizie`: quanti titoli degli ultimi sette giorni confermano il tema
    (ricerca Google News, tenuti solo quelli dove una parola del tema compare
    davvero), in scala logaritmica sul tema piu' coperto.
  - `attualita`: 1 se il tema e' fra le ricerche di tendenza di Google o fra
    le notizie principali di oggi, 0,5 se tocca una pubblicazione Istat
    recente, 0 altrimenti.
  - `crescita` e `livello` da Google Trends (`interesse.json`), se ci sono.
    Se mancano, il peso si ridistribuisce sugli altri: un dato mancante non e'
    uno zero.

**dato**, quanto e' solido l'indicatore che da' il contesto:
  - `recenza` dell'ultimo anno (2025 = 1, poi scende),
  - `copertura` (103 province = 1, 20 regioni = 0,8),
  - `profondita'` della serie (otto anni o piu' = 1).

**storia**, se nei dati c'e' qualcosa da raccontare, calcolata dai valori:
  - `outlier`: un territorio a oltre 2,5 deviazioni dagli altri nell'ultimo anno,
  - `inversione`: la media dei territori cambia verso negli ultimi tre anni
    rispetto ai tre prima,
  - `divario`: la distanza fra Mezzogiorno e Centro-Nord si e' allargata o
    stretta di oltre un quarto dal primo anno,
  - `record`: l'ultimo anno e' il minimo o il massimo della serie.
  Il punteggio e' il piu' forte dei quattro: una storia basta.

Il **totale** e' interesse x (dato + storia) / 2, e una coppia si scarta se
l'interesse e' sotto 0,25 o il dato sotto 0,5: tanto interesse su un dato
debole produce un pezzo che non regge, un dato ottimo che nessuno cerca
produce un pezzo che nessuno legge.

    bin/py -m scripts.articoli_trend.classifica
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys

from scripts.articoli_trend import comuni

SOGLIA_INTERESSE = 0.25
SOGLIA_DATO = 0.5


def _medie_per_anno(valori: dict) -> dict[int, float]:
    anni: dict[int, list[float]] = {}
    for per in valori.values():
        for anno, v in per.items():
            anni.setdefault(anno, []).append(v)
    return {a: statistics.fmean(v) for a, v in sorted(anni.items()) if len(v) >= 3}


def punteggio_dato(meta: dict, valori: dict) -> dict:
    ultimo = meta["anni"][1]
    recenza = {2026: 1, 2025: 1, 2024: 0.9, 2023: 0.75, 2022: 0.55}.get(ultimo, 0.3)
    copertura = 1.0 if meta["territori"] >= 100 else 0.8 if meta["territori"] >= 19 else 0.4
    n_anni = len({a for per in valori.values() for a in per})
    profondita = min(1.0, n_anni / 8)
    return {
        "punteggio": round(0.5 * recenza + 0.25 * copertura + 0.25 * profondita, 2),
        "ultimo_anno": ultimo, "anni": n_anni, "territori": meta["territori"],
    }


def punteggio_storia(meta: dict, valori: dict) -> dict:
    livello = meta["livello"]
    ultimo = meta["anni"][1]
    ora = {t: per[ultimo] for t, per in valori.items() if ultimo in per}
    trovate: list[tuple[float, str]] = []

    if len(ora) >= 5:
        media = statistics.fmean(ora.values())
        dev = statistics.pstdev(ora.values())
        if dev:
            t, v = max(ora.items(), key=lambda kv: abs(kv[1] - media))
            z = abs(v - media) / dev
            trovate.append((min(1.0, z / 2.5) if z >= 1.8 else 0.0,
                            f"outlier: {t} {comuni.fmt(v, 2)} contro una media dei territori di {comuni.fmt(media, 2)} (z={z:.1f}, {ultimo})"))

    medie = _medie_per_anno(valori)
    anni = list(medie)
    if len(anni) >= 6:
        recente = medie[anni[-1]] - medie[anni[-3]]
        prima = medie[anni[-4]] - medie[anni[-6]]
        if recente * prima < 0 and abs(recente) > 0.02 * abs(medie[anni[-1]] or 1):
            trovate.append((0.9, f"inversione: la media dei territori {'sale' if recente > 0 else 'scende'} dal {anni[-3]} al {anni[-1]} dopo essere {'scesa' if prima < 0 else 'salita'} dal {anni[-6]} al {anni[-4]}"))
    if anni:
        valori_medi = list(medie.values())
        if medie[anni[-1]] in (max(valori_medi), min(valori_medi)) and len(anni) >= 5:
            quale = "massimo" if medie[anni[-1]] == max(valori_medi) else "minimo"
            trovate.append((0.7, f"record: nel {anni[-1]} la media dei territori tocca il {quale} della serie ({anni[0]}-{anni[-1]})"))

    def divario(anno):
        gruppi: dict[str, list[float]] = {}
        for t, per in valori.items():
            if anno in per:
                gruppi.setdefault(comuni.ripartizione(t, livello), []).append(per[anno])
        if len(gruppi) < 2 or min(len(g) for g in gruppi.values()) < 3:
            return None
        return statistics.fmean(gruppi["Mezzogiorno"]) - statistics.fmean(gruppi["Centro-Nord"])

    if anni:
        primo, fine = divario(anni[0]), divario(anni[-1])
        if primo and fine is not None:
            cambio = (abs(fine) - abs(primo)) / abs(primo)
            if abs(cambio) >= 0.25:
                trovate.append((min(1.0, abs(cambio)),
                                f"divario Mezzogiorno/Centro-Nord {'allargato' if cambio > 0 else 'ristretto'} del {abs(cambio) * 100:.0f}% dal {anni[0]} al {anni[-1]}"))

    trovate.sort(reverse=True)
    return {
        "punteggio": round(trovate[0][0], 2) if trovate else 0.0,
        "storie": [descr for p, descr in trovate if p > 0],
    }


def punteggio_interesse(tema: dict, segnali: list[dict], interesse: dict, massimo_notizie: int) -> dict:
    notizie = [s for s in segnali if s["tipo"] == "google_news_tema" and s.get("tema") == tema["id"] and tema["id"] in s["temi"]]
    tendenze = [s for s in segnali if s["tipo"] == "google_trends_tendenza" and tema["id"] in s["temi"]]
    principali = [s for s in segnali if s["tipo"] == "google_news_principali" and tema["id"] in s["temi"]]
    istat = [s for s in segnali if s["tipo"] == "istat_comunicato" and tema["id"] in s["temi"]]

    parti = {"notizie": math.log1p(len(notizie)) / math.log1p(max(massimo_notizie, 1))}
    parti["attualita"] = 1.0 if (tendenze or principali) else 0.5 if istat else 0.0
    pesi = {"notizie": 0.35, "attualita": 0.25}

    misure = [m for m in interesse.get(tema["id"], []) if m.get("crescita") is not None]
    if misure:
        crescita = max(m["crescita"] for m in misure)
        parti["crescita"] = max(0.0, min(1.0, (crescita - 0.8) / 1.2))
        pesi["crescita"] = 0.2
    livelli = [m["livello_su_ancora"] for m in interesse.get(tema["id"], []) if m.get("livello_su_ancora")]
    if livelli:
        parti["livello"] = max(0.0, min(1.0, 1 + math.log10(max(livelli)) / 2))
        pesi["livello"] = 0.2

    totale = sum(parti[k] * pesi[k] for k in pesi) / sum(pesi.values())
    migliori_regioni = {}
    for m in interesse.get(tema["id"], []):
        if m.get("regioni_7g"):
            migliori_regioni[m["query"]] = sorted(m["regioni_7g"].items(), key=lambda kv: -kv[1])[:5]
    return {
        "punteggio": round(totale, 2),
        "parti": {k: round(v, 2) for k, v in parti.items()},
        "notizie_7g": len(notizie),
        "tendenze_google": [s["termine"] for s in tendenze],
        "notizie_principali": [s["titolo"] for s in principali],
        "istat": [s["titolo"] for s in istat],
        "trends": [{k: m.get(k) for k in ("query", "crescita", "livello_su_ancora", "media_7g")} for m in interesse.get(tema["id"], [])],
        "regioni_piu_interessate": migliori_regioni,
        "esempi_notizie": [{"titolo": s["titolo"], "url": s["url"], "pubblicato": s["pubblicato"]} for s in notizie[:5]],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--giorno")
    args = parser.parse_args(argv)

    cartella = comuni.cartella_giorno(args.giorno)
    segnali = comuni.leggi_json(cartella / "segnali.json")["segnali"]
    interesse = comuni.leggi_json(cartella / "interesse.json")["temi"] if (cartella / "interesse.json").exists() else {}
    temi = comuni.leggi_json(comuni.CONFIG_TEMI)["temi"]

    conteggi = [
        sum(1 for s in segnali if s["tipo"] == "google_news_tema" and s.get("tema") == t["id"] and t["id"] in s["temi"])
        for t in temi
    ]
    righe = []
    for tema in temi:
        inter = punteggio_interesse(tema, segnali, interesse, max(conteggi))
        for chiave in tema["indicatori"]:
            try:
                s = comuni.serie(chiave)
            except KeyError as errore:
                print(f"  {errore}", file=sys.stderr)
                continue
            dato = punteggio_dato(s["meta"], s["valori"])
            storia = punteggio_storia(s["meta"], s["valori"])
            totale = inter["punteggio"] * (dato["punteggio"] + storia["punteggio"]) / 2
            scarto = []
            if inter["punteggio"] < SOGLIA_INTERESSE:
                scarto.append("interesse sotto soglia")
            if dato["punteggio"] < SOGLIA_DATO:
                scarto.append("dato debole")
            if storia["punteggio"] == 0:
                scarto.append("nessuna storia nei dati")
            righe.append({
                "tema": tema["id"], "tema_nome": tema["nome"], "indicatore": chiave,
                "indicatore_nome": s["meta"]["nome"], "livello": s["meta"]["livello"],
                "totale": round(totale, 3), "interesse": inter, "dato": dato, "storia": storia,
                "scartato": scarto,
            })

    righe.sort(key=lambda r: (bool(r["scartato"]), -r["totale"]))
    comuni.scrivi_json(cartella / "classifica.json", {"giorno": cartella.name, "coppie": righe})

    linee = [f"# Classifica tema-indicatore, {cartella.name}", "",
             "| # | tema | indicatore | liv. | interesse | dato | storia | totale | note |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(righe, 1):
        nota = "; ".join(r["scartato"]) or (r["storia"]["storie"][0] if r["storia"]["storie"] else "")
        linee.append(f"| {i} | {r['tema']} | {r['indicatore']} {r['indicatore_nome'][:50]} | {r['livello'][:4]} | "
                     f"{r['interesse']['punteggio']} | {r['dato']['punteggio']} | {r['storia']['punteggio']} | "
                     f"{r['totale']} | {nota} |")
    (cartella / "classifica.md").write_text("\n".join(linee) + "\n", encoding="utf-8")
    print("\n".join(linee[:30]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
