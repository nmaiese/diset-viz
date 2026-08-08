"""La pipeline lite: tre comandi, cinque agenti, nessun cancello.

Vive accanto a `officina/` e `packs/` senza toccarli. Serve a misurare quanto
della macchina attuale sia necessario: qui c'è solo ciò che un modello non
deve fare da sé (calcolare cifre, scrivere file, confrontare numeri) e tutto
il resto sta nei prompt degli agenti e nelle skill.

    bin/py -m lab.dossier ter-30                 # i numeri, già calcolati
    bin/py -m lab.controlla ter-30 --salva ...   # ogni cifra del testo contro i numeri
    bin/py -m lab.pubblica ter-30 --bozza ...    # l'articolo su disco, in data/lab/

Nessuno dei tre decide se un articolo è pubblicabile: lo decide il
verificatore, che li legge.
"""
