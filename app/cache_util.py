"""Cache che serializza anche il *calcolo*, non solo l'aggiornamento.

`functools.lru_cache` prende il lock solo per leggere/scrivere la tabella: su un
miss concorrente lascia che N thread eseguano il corpo insieme. Per i builder
pesanti del catalogo (parsing CSV, costruzione di strutture da decine di migliaia
di elementi) questo significa, all'avvio a freddo sotto gunicorn (`--threads 8`,
cache vuota), N ricostruzioni simultanee: il picco di RAM misurato passa da ~221MB
(sequenziale) a ~463MB (8 thread), ed e' quel picco - non la memoria trattenuta -
che faceva cadere il worker a 512Mi.

`synchronized_cache` avvolge l'intera chiamata in un lock, quindi un solo thread
costruisce e gli altri aspettano il valore memoizzato. Preserva l'API di
`lru_cache` (`cache_clear`, `cache_info`) usata da test e strumenti, cosi' e'
un drop-in per `@lru_cache` senza cambio di semantica.
"""
import threading
from functools import lru_cache, wraps


def synchronized_cache(maxsize=1):
    def deco(fn):
        cached = lru_cache(maxsize=maxsize)(fn)
        lock = threading.Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            with lock:
                return cached(*args, **kwargs)

        wrapper.cache_clear = cached.cache_clear
        wrapper.cache_info = cached.cache_info
        wrapper.__wrapped__ = fn
        return wrapper

    return deco
