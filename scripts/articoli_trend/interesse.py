"""Fase 2: quanto si cerca ogni tema, se sta crescendo, e dove.

Usa Google Trends attraverso `pytrends`, che non e' una dipendenza del sito e
non ci deve diventare: si lancia in un ambiente usa-e-getta con uv.

    ~/.local/bin/uv run --no-project --with pytrends --with "urllib3<2" \\
        --with pandas python -m scripts.articoli_trend.interesse

Per ogni tema di `config/trend_temi.json`, per ogni query in `trends`:

- **crescita**: media dell'interesse negli ultimi 7 giorni diviso la media
  degli 83 giorni prima (finestra `today 3-m`). Sopra 1 il tema sta salendo.
- **livello**: interesse medio degli ultimi 7 giorni **rispetto a una query
  di riferimento fissa** ("pensioni"), nella stessa richiesta. Google Trends
  normalizza ogni richiesta a 100 sul suo massimo, quindi due temi si
  confrontano solo se passano per la stessa ancora.
- **regioni**: interesse per regione negli ultimi 7 giorni (0-100, relativo
  alla regione dove la quota di ricerche e' piu' alta).

Sono **indici relativi, non volumi di ricerca**. Nel testo di un articolo non
si scrivono mai come "N ricerche": si puo' dire che un tema e' cresciuto, e in
quali regioni e' piu' cercato, citando Google Trends e la finestra.

Se Google risponde 429 (troppe richieste) lo script aspetta e riprova. Se
fallisce comunque, il tema resta senza interesse e la classifica lo tratta
come dato mancante, non come zero: si documenta nel rapporto.
"""

from __future__ import annotations

import argparse
import sys
import time

from scripts.articoli_trend import comuni

# "meteo" era troppo forte: al primo giro (23 settembre 2026) schiacciava
# a zero il livello di tutti i temi. Un'ancora deve stare nello stesso ordine
# di grandezza dei temi che misura.
ANCORA = "pensioni"
PAUSA = 6


def _richiesta(trend, parole, finestra, tentativi=3):
    for prova in range(tentativi):
        try:
            trend.build_payload(parole, geo="IT", timeframe=finestra)
            return trend.interest_over_time()
        except Exception as errore:  # 429 e affini
            attesa = PAUSA * (prova + 2) * 2
            print(f"    {parole} {finestra}: {errore!r}, riprovo tra {attesa}s", file=sys.stderr)
            time.sleep(attesa)
    return None


def _regioni(trend, parola, tentativi=3):
    for prova in range(tentativi):
        try:
            trend.build_payload([parola], geo="IT", timeframe="now 7-d")
            tab = trend.interest_by_region(resolution="REGION", inc_low_vol=True)
            return {str(k): int(v) for k, v in tab[parola].items()}
        except Exception as errore:
            attesa = PAUSA * (prova + 2) * 2
            print(f"    regioni {parola}: {errore!r}, riprovo tra {attesa}s", file=sys.stderr)
            time.sleep(attesa)
    return None


def misura(trend, query: str) -> dict:
    esito: dict = {"query": query}
    serie = _richiesta(trend, [query], "today 3-m")
    time.sleep(PAUSA)
    if serie is not None and not serie.empty:
        valori = serie[query].tolist()
        recenti, prima = valori[-7:], valori[:-7]
        media_prima = sum(prima) / len(prima) if prima else 0
        media_recenti = sum(recenti) / len(recenti)
        esito["media_7g"] = round(media_recenti, 1)
        esito["media_83g_prima"] = round(media_prima, 1)
        esito["crescita"] = round(media_recenti / media_prima, 2) if media_prima else None
        esito["serie_90g"] = {str(i.date()): int(v) for i, v in serie[query].items()}
    confronto = _richiesta(trend, [query, ANCORA], "now 7-d")
    time.sleep(PAUSA)
    if confronto is not None and not confronto.empty:
        ancora = confronto[ANCORA].mean()
        esito["livello_su_ancora"] = round(confronto[query].mean() / ancora, 3) if ancora else None
    esito["regioni_7g"] = _regioni(trend, query)
    time.sleep(PAUSA)
    return esito


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--giorno")
    parser.add_argument("--temi", nargs="*", help="solo questi id di tema")
    args = parser.parse_args(argv)

    from pytrends.request import TrendReq

    trend = TrendReq(hl="it-IT", tz=-120, timeout=(10, 30))
    temi = comuni.leggi_json(comuni.CONFIG_TEMI)["temi"]
    if args.temi:
        temi = [t for t in temi if t["id"] in args.temi]

    risultati = {}
    for tema in temi:
        print(f"  {tema['id']}")
        risultati[tema["id"]] = [misura(trend, q) for q in tema["trends"]]

    uscita = comuni.cartella_giorno(args.giorno) / "interesse.json"
    precedente = comuni.leggi_json(uscita)["temi"] if uscita.exists() else {}
    precedente.update(risultati)
    comuni.scrivi_json(uscita, {
        "fonte": "Google Trends (pytrends), geo=IT",
        "ancora": ANCORA,
        "rilevato": comuni.oggi(),
        "nota": "Indici relativi 0-100, non volumi di ricerca.",
        "temi": precedente,
    })
    print(f"-> {uscita.relative_to(comuni.RADICE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
