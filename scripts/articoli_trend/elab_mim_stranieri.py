"""Elaborazione: quota di alunni con cittadinanza non italiana in terza media, per regione.

Fonte: open data del Ministero dell'Istruzione e del Merito, "Alunni per
cittadinanza, scuola e anno di corso", scuole statali e paritarie
(`ALUITASTRACITSTA<anni>0831.csv` e `ALUITASTRACITPAR<anni>0831.csv` su
dati.istruzione.it). Licenza IODL 2.0.

Metodo: si tengono le righe con ORDINESCUOLA = "SCUOLA SECONDARIA I GRADO" e
ANNOCORSO = 3, si attribuisce ogni scuola alla regione dalla sigla di
provincia nelle prime due lettere del CODICESCUOLA, si sommano alunni totali e
alunni con cittadinanza non italiana. La quota e' il rapporto, per cento.

Serve a mettere alla prova un'ipotesi (piu' alunni stranieri = piu' studenti
sotto la soglia Invalsi), non a spiegare da sola un fenomeno: la cittadinanza
non e' l'origine (un ragazzo nato in Italia da genitori stranieri che ha preso
la cittadinanza conta come italiano), e un confronto fra regioni non dice
niente sui singoli studenti. Valle d'Aosta e Trentino-Alto Adige non sono
negli open data del Ministero (scuole a ordinamento autonomo).

Scrive `data/elaborazioni/mim_stranieri_terza_media.csv` e il `.json` con il
metodo, nel formato che `dossier.py` legge come indicatore `ext:`.

    bin/py -m scripts.articoli_trend.elab_mim_stranieri 201718 202425
"""

from __future__ import annotations

import argparse
import csv
import io
import sys

import requests

from scripts.articoli_trend import comuni

URL = "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/ALUITASTRACIT{tipo}{a}{b}0831.csv"
USCITA = comuni.RADICE / "data" / "elaborazioni" / "mim_stranieri_terza_media"

SIGLE = {
    "Piemonte": "TO VC NO CN AT AL BI VB",
    "Lombardia": "VA CO SO MI BG BS PV CR MN LC LO MB",
    "Veneto": "VR VI BL TV VE PD RO",
    "Friuli-Venezia Giulia": "UD GO TS PN",
    "Liguria": "IM SV GE SP",
    "Emilia-Romagna": "PC PR RE MO BO FE RA FC RN FO",
    "Toscana": "MS LU PT FI LI PI AR SI GR PO",
    "Umbria": "PG TR",
    "Marche": "PU AN MC AP FM PS",
    "Lazio": "VT RI RM LT FR",
    "Abruzzo": "AQ TE PE CH",
    "Molise": "CB IS",
    "Campania": "CE BN NA AV SA",
    "Puglia": "FG BA TA BR LE BT",
    "Basilicata": "PZ MT",
    "Calabria": "CS CZ RC KR VV",
    "Sicilia": "TP PA ME AG CL EN CT RG SR",
    "Sardegna": "SS NU CA OR SU CI VS OT OG",
}
REGIONE = {s: r for r, sigle in SIGLE.items() for s in sigle.split()}


def anno_file(anno: str) -> tuple[str, str]:
    """'201718' -> ('201718', '2018'): l'anno scolastico e l'anno della data di riferimento."""
    return anno, "20" + anno[4:6]


def quote(anno: str) -> dict[str, tuple[int, int]]:
    a, fine = anno_file(anno)
    somme: dict[str, list[int]] = {}
    for tipo in ("STA", "PAR"):
        url = URL.format(tipo=tipo, a=a, b=fine)
        testo = requests.get(url, timeout=120).content.decode("utf-8-sig")
        for r in csv.DictReader(io.StringIO(testo)):
            if r["ORDINESCUOLA"] != "SCUOLA SECONDARIA I GRADO" or r["ANNOCORSO"] != "3":
                continue
            regione = REGIONE.get(r["CODICESCUOLA"][:2])
            if regione is None:
                continue
            s = somme.setdefault(regione, [0, 0])
            s[0] += int(r["ALUNNI"] or 0)
            s[1] += int(r["ALUNNICITTADINANZANONITALIANA"] or 0)
    return {k: (v[0], v[1]) for k, v in somme.items()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("anni", nargs="+", help="anni scolastici, es. 201718 202425")
    args = parser.parse_args(argv)

    USCITA.parent.mkdir(parents=True, exist_ok=True)
    righe = []
    for anno in args.anni:
        # L'anno scolastico 2017/18 finisce con la prova di maggio 2018:
        # nella serie si usa l'anno della prova, come fa l'Istat per Invalsi.
        anno_prova = int("20" + anno[4:6])
        for regione, (tot, stra) in sorted(quote(anno).items()):
            righe.append({"territorio": regione, "anno": anno_prova, "valore": round(100 * stra / tot, 2),
                          "alunni": tot, "stranieri": stra})
            print(anno_prova, regione, tot, stra, round(100 * stra / tot, 2))
    with (USCITA.with_suffix(".csv")).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["territorio", "anno", "valore", "alunni", "stranieri"], lineterminator="\n")
        w.writeheader()
        w.writerows(righe)
    comuni.scrivi_json(USCITA.with_suffix(".json"), {
        "nome": "Alunni con cittadinanza non italiana in terza media",
        "unita": "percentuale sugli alunni della terza classe della secondaria di primo grado",
        "fonte": "Ministero dell'Istruzione e del Merito",
        "archivio": "Open data, alunni per cittadinanza, scuola e anno di corso (statali e paritarie)",
        "source_url": "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/?area=Studenti",
        "licenza": "IODL 2.0",
        "method": __doc__.split("Metodo:")[1].split("Serve a")[0].strip().replace("\n", " "),
        "script": "scripts/articoli_trend/elab_mim_stranieri.py",
        "anni_scolastici": args.anni,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
