"""La data vera di aggiornamento dei dati, per il `lastmod` della sitemap.

La fonte e' `data/source_state.json`, che il monitoraggio delle fonti
(`scripts/update_bes_regions.py` e `update_data.py`) scrive dall'intestazione `Last-Modified`
del file Istat scaricato: la data in cui Istat ha pubblicato quei dati, non
quella del deploy ne' del checkout (la data di modifica dei file nell'immagine
e' quella della build, ed e' proprio il `lastmod` bugiardo che Google
penalizza). Il file sta in `data/`, che l'immagine copia.

Si dichiara solo cio' che il file sa. Il monitoraggio segue due fonti, e ogni
pagina ha la sua o nessuna:

- scheda della famiglia territoriale: `istat_indicatori_territoriali`;
- scheda BES regionale: `istat_bes_regioni`;
- pagina regione: la piu' recente delle due, perche' le legge entrambe. E' la
  data dell'ultimo aggiornamento dei dati a cui la pagina attinge, un limite
  alto: non dice che le cifre di quella regione siano cambiate quel giorno;
- tutto il resto (province, `/province` delle schede, altre famiglie, pagine
  statiche): nessuna data, quindi nessun `lastmod`.
"""
import json
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.cache_util import synchronized_cache

_SOURCE_STATE = Path(__file__).resolve().parent.parent / "data" / "source_state.json"

_TERRITORIALI = "istat_indicatori_territoriali"
_BES_REGIONI = "istat_bes_regioni"

# (famiglia della scheda, livello) -> fonte monitorata che la alimenta.
_FONTE_SCHEDA = {
    ("territorial", "regione"): _TERRITORIALI,
    ("bes", "regione"): _BES_REGIONI,
}


@synchronized_cache(maxsize=1)
def _date_fonti():
    """`{fonte: 'YYYY-MM-DD'}` da `source_state.json`; vuoto se manca o e' guasto."""
    try:
        sources = json.loads(_SOURCE_STATE.read_text(encoding="utf-8")).get("sources", {})
        sources = dict(sources)
    except (OSError, ValueError, AttributeError, TypeError):
        # File assente, non JSON o di forma diversa da quella attesa: nessuna
        # data, e la sitemap resta valida invece di rispondere 500.
        return {}
    dates = {}
    for name, state in sources.items():
        try:
            dates[name] = parsedate_to_datetime(state["last_modified"]).date().isoformat()
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return dates


def lastmod_scheda(family, level_key):
    """La data dei dati di una pagina scheda, o None."""
    source = _FONTE_SCHEDA.get((family, level_key))
    return _date_fonti().get(source) if source else None


def lastmod_regione():
    """La data piu' recente fra le fonti che alimentano le pagine regione, o None."""
    dates = [_date_fonti().get(name) for name in (_TERRITORIALI, _BES_REGIONI)]
    dates = [d for d in dates if d]
    return max(dates) if dates else None
