"""Controlli del leader sull'insight del brief: oltre-soglia contro raggiungibilita dei servizi.

Scelti PRIMA di calcolare: (a) tutti gli anni in comune 2019-2023, (b) senza Lombardia e Molise (gli estremi
dell'oltre-soglia). Riusa le funzioni di calcola.py. Da lanciare dalla radice del worktree con bin/py.
"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("c", Path(__file__).with_name("calcola.py"))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
d = c.load()
for nome in ("difficolta_servizi", "fila_asl", "emigrazione", "salute_75", "pronto_soccorso"):
    anni = sorted(set(d["oltre_soglia"]) & set(d[nome]))
    serie = []
    for y in anni:
        keys, r = c.paired(d, "oltre_soglia", nome, y)
        serie.append((y, len(keys), None if r is None else round(r, 3)))
    a, b = c.year_values(d, "oltre_soglia", anni[-1]), c.year_values(d, nome, anni[-1])
    ks = [k for k in sorted(a.keys() & b.keys()) if k not in ("lombardia", "molise")]
    r2 = c.spearman([a[k] for k in ks], [b[k] for k in ks])
    print(nome, serie[-5:], "senza lombardia e molise", anni[-1], len(ks), round(r2, 3))
