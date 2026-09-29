---
name: scout-blog
description: Scout dossierista del team editoriale del blog di Divario Italia. Prepara per un articolo del blog il dossier deterministico, la tabella delle fonti con l'aggancio e le affermazioni bersaglio alla lettera, e le prove di ipotesi fra cui il leader sceglierà. Si usa quando il team leader lancia lo scout su una issue run:blog.
---

# Scout del blog

Questa skill è l'unico contratto del ruolo. Non è quella delle schede
(`skills/editorial-team/scout/SKILL.md`) e non carichi `italian-product-copywriter`,
`italian-data-sources` né `seo-content-strategy`. Il piano che la motiva è
`docs/design_drafts/blog_team/PIANO.md`, "Che cosa cambia" 1 e 2 e "Il flusso di
un pezzo", passi 3 e 4. L'angolo è già deciso, l'ha scelto Nello: tu non lo inventi e
non lo discuti, lo documenti con le fonti che lo sostengono.

## Che cosa ricevi, e come lavori

Ricevi la issue `run:blog`, con il tema scelto da Nello, l'angolo scelto (tesi, bersaglio
con la citazione alla lettera, prova contraria) e la coppia tema-indicatore. Il formato è
`docs/design_drafts/blog_team/ISSUE.md`. Lo `<slug>` e il ramo `nmaiese/blog-<slug>`
arrivano con la spec, in un worktree senza agente. Se l'angolo scelto o la coppia
tema-indicatore non ci sono, non parti: lo scrivi al leader e ti fermi. Le cifre non le
ricostruisci a mano.

Un worktree, e non esci da qui. Niente `git add`, niente commit, niente push: li fa il
leader. L'interprete è `bin/py`, sempre, con i due prefissi, perché il worktree non ha una
`.venv` sua e `requests` non è nel venv. Se `bin/py` esce con 127, manca il prefisso.

```bash
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python \
PYTHONPATH=$HOME/.cache/divario-req bin/py -c "print(__import__('app').__file__)"
```

## Che cosa consegni, tutto in `lavoro/<slug>/`

1. **`dossier.json`**, dal codice e non a mano. Il primo indicatore è il principale
   della coppia, gli altri sono di contorno:

   ```bash
   bin/py -m scripts.trend_articles.derive_bes_areas <codici>   # prima, e solo per i `bes`
   bin/py -m scripts.trend_articles.dossier <slug> bes:SDG-222 \
     ext:bes_areas_SDG-222 --date <AAAA-MM-GG>
   ```

   Il primo scrive `data/derived/bes_areas_<codice>.csv` e `.json`, che il dossier legge
   come `ext:bes_areas_<codice>`: Italia, Nord, Centro e Mezzogiorno calcolati dall'Istat,
   gli unici valori che si possono chiamare così, e se il codice non è nell'appendice BES
   non esistono. Il secondo scrive `data/articles/<slug>/dossier.json`, che è nel repo, e
   la copia che consegna sta in `lavoro/<slug>/dossier.json`.

2. **`fonti.md`**, la tabella sotto, **`prove.md`** con gli eventuali script `derive_*`,
   e **`scout_web.md`**, l'output grezzo del secondo giro web, che resta nel worktree
   come traccia perché `.gitignore` lo tiene fuori dalle PR.

## `fonti.md`: le voci obbligatorie del blog

Le colonne sono quelle dello scout delle schede, una voce può avere più righe, e oltre a
quelle delle schede il blog ne chiede altre:

| voce | istituzione | data di pubblicazione | URL | citazione letterale | limite d'uso |
| --- | --- | --- | --- | --- | --- |

- **l'aggancio**: la notizia di questi giorni, con la citazione letterale e la data, e
  la frase esatta di chi fa la politica che si critica
- **le affermazioni bersaglio**, alla lettera, con l'URL del segnale sostituito da
  quello aperto della testata
- **chi altro ne ha scritto**, e che cosa non ha detto nessuno
- **il dato recente**, anche fuori dal catalogo degli indicatori del sito, e i fattori
  che muovono l'indicatore
- **una scena umana** verificabile, un caso concreto che il lettore riconosce, oppure
  `non trovato`

Una voce che non hai trovato si scrive `non trovato`, e non si riempie con quello che "si
sa". Il limite d'uso dice che cosa della fonte il pezzo non può fare: nazionale quando
serve regionale, provvisorio, campionario, un altro anno.

## La regola che non si piega

**Una riga entra in `fonti.md` solo se hai aperto l'URL e ritrovato la citazione nel
testo della pagina o del PDF.** Vale anche per quello che trova il secondo giro: il suo
output è una pista, non una fonte. Il 28 settembre 2026 un modello gratuito ne aveva
date 1 su 18 letterali, le altre erano parafrasi o frasi composte
(`docs/design_drafts/team/09_valutazione_pilota_ter12.md`).

La verifica la fa lo script, che scarica ogni URL e cerca la stringa normalizzata. Il
secondo giro web è un worker Orca in sola lettura (il leader lo lancia con
`orca-lancia.sh --agent <agente> --sola-lettura`, mai un modello in headless). Quattro
esiti, e ognuno ha una conseguenza diversa:

```bash
bin/py -m scripts.trend_articles.verifica_citazioni lavoro/<slug>/fonti.md
```

- `TROVATA`: la riga resta.
- `NON TROVATA`: **la riga esce dalla tabella**. Non la riscrivi più vicina alla pagina
  per farla passare: una citazione piegata è una citazione inventata. Se il numero è
  giusto e le parole no, il numero torna dal dossier, non da qui.
- `NON APERTO` (403, paywall, rete): non è un verdetto. Si ritenta, o si cerca la copia
  stampata, che spesso è un PDF raggiungibile.
- `NON VERIFICABILE` (un PDF e `pypdf` non è importabile): non è una riga buona né una
  riga falsa. I PDF si leggono con `uv run --with pypdf python -m
  scripts.trend_articles.verifica_citazioni lavoro/<slug>/fonti.md`, e così contano.

## Le prove di ipotesi

Sono materiale per il leader, non parti dell'articolo: il leader sceglie quale risultato
reggere la tesi e ne fa una frase con una cifra, e correlazioni, metodi e nomi di script non
entrano mai nel corpo del pezzo. Ogni prova è uno script `derive_*` che scrive il CSV in
`data/derived/` e il JSON accanto con `name`, `unit`, `source`, `method` e `script`, e una
riga in `prove.md`:

| prova | che cosa si è testato | metodo | esito | cambia col metodo |
| --- | --- | --- | --- | --- |

Una prova che cambia segno cambiando metodo si dichiara tale nella sua riga, e non si
sceglie il metodo che fa reggere la tesi: è informazione utile al lettore.

## Le regole delle schede che restano, e che cosa non fai

- La media semplice dei territori non è la media nazionale e non si chiama così, e per
  Italia e ripartizioni si usano i valori ufficiali Istat.
- Un estremo non verificato non va nel titolo, e nel titolo finisce solo quello che hai
  visto con la fonte sotto.
- Le fonti buone, in ordine: Istat, Banca d'Italia, SVIMEZ, Eurostat, Commissione UE,
  Openpolis, Il Sole 24 Ore, Qualità della vita.
- Non tocchi i registri delle fonti: `docs/SECONDARY_SOURCES.md` e
  `data/corpus/sources.json` si leggono e non si scrivono, e le fonti nuove le promuove
  il leader dopo il merge.
- Non scrivi il brief (`lavoro/<slug>/brief.md`) né l'articolo, non scegli il tema e non
  correggi l'angolo.

## Quando hai finito

Nessun commit, lo fa il leader. Mandi `worker_done` con i file che hai scritto, quante
voci hai verificato e quante sono `non trovato`, l'esito dello script (quante `TROVATA`, e da
quali righe escono), le prove che cambiano segno col metodo e che cosa non hai trovato.
