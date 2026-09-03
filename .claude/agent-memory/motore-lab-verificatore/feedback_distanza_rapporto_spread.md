---
name: distanza-rapporto-contro-spread
description: Classe di errore ricorrente: un articolo dice che la distanza fra massimo e minimo non e cambiata mostrando lo spread in punti dopo aver introdotto un rapporto
metadata:
  type: feedback
---

Quando un testo introduce la distanza fra il massimo e il minimo come **rapporto** (`quasi cinque a uno`) e poi ne prova la stabilita' con lo **spread in punti** (`allora come oggi vale 12,3 punti`), le due misure non sono la stessa cosa e possono muoversi in direzioni opposte.

**Why:** su multiscopo:MULTI_ZONA_CRIMINALITA lo spread e' 12,3 punti nel 2018 e nel 2025 (dossier: convergenza stabile), ma il rapporto e' passato da 3,0 (18,4 / 6,1) a 4,84. La frase regge sul secondo numero e non sul primo, e lab.controlla la segna `trovata` perche 12,3 esiste.

**How to apply:** ogni volta che il riepilogo dice `spread`, controllare che aggettivo di distanza usa la frase. Rapporto e spread vanno tenuti separati o si nomina quello che davvero non e cambiato.
