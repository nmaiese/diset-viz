"""Il pacchetto: tutto cio' che serve a scrivere un indicatore, calcolato.

Tre moduli soltanto, e una regola che li tiene separati:

- `angles`  trova le storie nei dati. Stdlib pura, nessun import da `app`:
            prende una matrice `{anno: {territorio: valore}}` e restituisce
            angoli ordinati per forza. Si testa senza Flask e senza CSV.
- `build`   adatta il view model dell'app a quella matrice, e monta il
            pacchetto completo. E' l'unico posto che conosce `app`.
- `render`  stampa il pacchetto per chi scrive.

Il motivo della separazione non e' l'eleganza. Il brief di oggi
(`scripts/indicator_brief.py`) stampa sempre gli stessi blocchi nello stesso
ordine, e tutti e 52 gli articoli riscritti hanno la stessa sequenza di
sezioni: la prosa eredita la forma della sua fonte d'informazione. Un
inventario di angoli ordinati per forza ha una forma diversa per ogni
indicatore, ed e' l'unico modo perche' la struttura dell'articolo nasca dai
dati invece che da uno scheletro.
"""
