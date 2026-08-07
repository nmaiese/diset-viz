"""Il contratto di misura: le tre trappole che rendevano il costo non confrontabile.

Non prova che la misura sia *giusta* (per quello serve un trascritto vero), ma
che continui a essere la misura decisa. Le tre trappole vengono dalla prima run
del workflow nuovo, e ognuna da sola falsava il numero abbastanza da cambiare
una decisione:

1. due record per richiesta, contati due volte: fattore 1,75;
2. `usage` che non conta i subagent;
3. le chiamate advisor, che l'aggregato di primo livello **esclude**: erano il
   26% del costo di quella run e non comparivano in nessun contatore.

Un file che rimisura senza queste tre non e' confrontabile col precedente, ed
e' esattamente il modo in cui un bersaglio di costo smette di essere
aggiudicabile.
"""
import json
import os
import tempfile
import unittest

from scripts import baseline_tokens as bt


def _usage(inp=0, out=0, read=0, write=0, iterations=None):
    usage = {"input_tokens": inp, "output_tokens": out,
             "cache_read_input_tokens": read, "cache_creation_input_tokens": write}
    if iterations is not None:
        usage["iterations"] = iterations
    return usage


def _iter(kind, inp=0, out=0, read=0, write=0):
    step = _usage(inp, out, read, write)
    step["type"] = kind
    return step


def _line(request_id, usage, agent="a1", kind="assistant", content=None):
    return json.dumps({
        "type": kind, "requestId": request_id, "agentId": agent,
        "timestamp": "2026-08-07T09:00:00Z",
        "message": {"usage": usage, "content": content or []},
    })


class SplitUsage(unittest.TestCase):
    def test_without_iterations_the_aggregate_is_everything(self):
        model, advisor = bt.split_usage(_usage(inp=10, out=20, read=30, write=40))
        self.assertEqual(model, {"in": 10, "out": 20, "cache_r": 30, "cache_w": 40})
        self.assertEqual(sum(advisor.values()), 0)

    def test_the_advisor_is_counted_apart_and_not_lost(self):
        """L'aggregato di primo livello esclude le iterazioni advisor.

        Caso vero, `req_011CdoB1PWrYCt9Pzdnaunzf`: aggregato `input_tokens: 4`
        mentre l'iterazione advisor ne portava 71.870, non in cache.
        """
        usage = _usage(inp=4, out=2059, read=140272, write=2377, iterations=[
            _iter("message", inp=2, out=138, read=69955, write=362),
            _iter("advisor_message", inp=71870, out=7089),
            _iter("message", inp=2, out=1921, read=70317, write=2015),
        ])
        model, advisor = bt.split_usage(usage)
        self.assertEqual(model["in"], 4)
        self.assertEqual(model["out"], 2059)
        self.assertEqual(advisor["in"], 71870)
        self.assertEqual(advisor["out"], 7089)

    def test_the_advisor_is_not_folded_into_the_model_total(self):
        """Sommarli sarebbe piu' comodo e cancellerebbe la scoperta."""
        usage = _usage(inp=2, out=100, iterations=[
            _iter("message", inp=2, out=100),
            _iter("advisor_message", inp=80000, out=5000),
        ])
        model, _ = bt.split_usage(usage)
        self.assertEqual(model["in"], 2)


class OneRecordPerRequest(unittest.TestCase):
    def _write(self, lines):
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                             encoding="utf-8")
        handle.write("\n".join(lines) + "\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_the_partial_and_the_final_are_one_turn(self):
        path = self._write([
            _line("req_a", _usage(inp=1, out=5, read=100)),
            _line("req_a", _usage(inp=1, out=5, read=100)),
        ])
        rows = bt.turns(path)
        self.assertEqual(len(rows), 1, "due record per richiesta contano uno")
        self.assertEqual(rows[0]["model"]["cache_r"], 100)

    def test_the_kept_record_is_the_one_that_carries_the_advisor(self):
        """Il parziale non ha `iterations`: tenerlo perderebbe l'advisor."""
        path = self._write([
            _line("req_a", _usage(inp=2, out=10, read=500)),
            _line("req_a", _usage(inp=2, out=10, read=500, iterations=[
                _iter("message", inp=2, out=10, read=500),
                _iter("advisor_message", inp=9000, out=400),
            ])),
        ])
        rows = bt.turns(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["advisor"]["in"], 9000)

    def test_distinct_requests_stay_distinct(self):
        path = self._write([
            _line("req_a", _usage(read=100)),
            _line("req_b", _usage(read=200)),
        ])
        self.assertEqual(len(bt.turns(path)), 2)

    def test_only_assistant_records_carry_usage(self):
        path = self._write([
            _line("req_a", _usage(read=100)),
            _line("req_b", _usage(read=999), kind="user"),
        ])
        rows = bt.turns(path)
        self.assertEqual(len(rows), 1)

    def test_a_broken_line_does_not_stop_the_count(self):
        path = self._write([
            _line("req_a", _usage(read=100)),
            "{non json",
            _line("req_b", _usage(read=200)),
        ])
        self.assertEqual(len(bt.turns(path)), 2)


class TheInflationFactorIsReal(unittest.TestCase):
    def test_counting_every_record_would_inflate_by_the_measured_factor(self):
        """Sulla run vera: 406 record grezzi contro 224 richieste, 1,81 volte.

        Il test non riproduce quel numero (serve il trascritto), riproduce la
        forma dell'errore: contare i record invece delle richieste raddoppia.
        """
        lines, requests = [], 12
        for index in range(requests):
            usage = _usage(read=1000, out=10)
            lines.append(_line(f"req_{index}", usage))
            lines.append(_line(f"req_{index}", usage))
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                             encoding="utf-8")
        handle.write("\n".join(lines) + "\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)

        rows = bt.turns(handle.name)
        self.assertEqual(len(rows), requests)
        self.assertEqual(sum(row["model"]["cache_r"] for row in rows), requests * 1000)
        self.assertEqual(len(lines), requests * 2,
                         "il doppio record e' la trappola, non un caso limite")


class Cost(unittest.TestCase):
    def test_cache_read_is_a_tenth_of_input(self):
        self.assertAlmostEqual(bt.PRICE["cache_r"] * 10, bt.PRICE["in"])

    def test_a_million_of_each_costs_the_listed_price(self):
        million = {field: 1_000_000 for field in bt.FIELDS}
        self.assertAlmostEqual(bt.cost(million), sum(bt.PRICE.values()))


class OnlyProseCountsAsProse(unittest.TestCase):
    """Chi entra nel costo per articolo si dichiara, non si deduce per esclusione.

    La lista era `NOT_WRITING`, cioe' per esclusione, e una lista per esclusione
    mente per omissione: `verificatore`, `reader-editor` e `launch` non
    c'erano, quindi una sessione con dentro **solo** un giro di verifica finiva
    sotto "SESSIONI CHE PRODUCONO PROSA" con tutti i suoi token dentro il costo
    per articolo. I tre non scrivono una riga, e il confronto fra la catena
    vecchia e l'officina, che e' l'unica cosa per cui questo script esiste,
    usciva gonfiato dalla parte sbagliata.
    """

    def test_the_year_is_a_shape_not_a_value(self):
        """Il ruolo si staccava con `split("-2026")`, un anno di calendario
        scritto dentro il codice. Dal primo gennaio 2027 quello split non taglia
        piu' niente, nessun ruolo combacia con `WRITING`, e il rapporto dichiara
        zero sessioni che producono prosa senza dire perche': un guasto che
        aspetta una data, invisibile finche' non e' tardi. `RUN_ID` e
        `pipeline_log.new_run_id()` accettano qualunque anno da sempre."""
        for anno in ("2026", "2027", "2031", "1999"):
            with self.subTest(anno=anno):
                self.assertEqual(bt.role_of(f"producer-{anno}0807T101010Z-abcd"), "producer")
                self.assertEqual(bt.writing_only([f"producer-{anno}0807T101010Z-abcd"]),
                                 [f"producer-{anno}0807T101010Z-abcd"])
                self.assertEqual(bt.writing_only([f"verificatore-{anno}0807T101010Z-abcd"]), [])

    def test_a_run_id_it_does_not_recognise_is_left_whole(self):
        """Meglio un ruolo che non combacia con niente di uno troncato a caso."""
        self.assertEqual(bt.role_of("qualcosa-che-non-e-un-run-id"),
                         "qualcosa-che-non-e-un-run-id")

    def test_the_critics_are_not_writers(self):
        runs = ["verificatore-20260807T101010Z-aaaa",
                "reader-editor-20260807T101010Z-bbbb",
                "launch-20260807T101010Z-cccc",
                "admissions-20260807T101010Z-dddd"]
        self.assertEqual(bt.writing_only(runs), [])

    def test_the_writers_still_are(self):
        runs = ["producer-20260807T101010Z-aaaa",
                "writer-20260728T101010Z-bbbb",
                "verificatore-20260807T101010Z-cccc"]
        self.assertEqual(bt.writing_only(runs),
                         ["producer-20260807T101010Z-aaaa",
                          "writer-20260728T101010Z-bbbb"])

    def test_the_list_is_the_producer_role_and_nothing_else(self):
        """Il commento in `baseline_tokens` promette questo allineamento, e un
        commento che promette una guardia inesistente e' il difetto che questa
        PR sta chiudendo. `baseline_tokens` resta stdlib pura e ricopia i nomi:
        il test importa tutti e due e li confronta."""
        from scripts import pipeline_launch
        dal_lanciatore = {stage for stage, role in pipeline_launch.ROLE_OF_STAGE.items()
                          if role == "producer"}
        self.assertEqual(set(bt.WRITING), dal_lanciatore | {"producer"})

    def test_every_stage_that_can_open_a_run_is_recognised(self):
        """`RUN_ID` e' un'altra enumerazione, e un ruolo che le manca non viene
        contato male: **sparisce**, e con lui l'intera sessione che lo conteneva,
        senza che una riga del rapporto lo dica.

        I quattro stadi `legacy-*` non combaciano per intero: la regex li tronca
        al ruolo che portano dentro (`legacy-writer` -> `writer`). E' senza
        conseguenze e vale la pena saperlo invece di scoprirlo: il prefisso
        distingue da dove viene la run, non che cosa ha fatto, quindi i due che
        scrivevano restano dentro il costo per articolo e i due che criticavano
        restano fuori. Un prefisso che cambiasse anche il mestiere spaccherebbe
        questa assunzione in silenzio."""
        from scripts import pipeline_log
        for stage in pipeline_log.HISTORICAL_STAGES:
            with self.subTest(stage=stage):
                run_id = f"{stage}-20260807T101010Z-abcd"
                trovato = bt.RUN_ID.search(run_id)
                self.assertIsNotNone(trovato, f"{stage} non apre nessuna run agli occhi del rapporto")
                ruolo = bt.role_of(trovato.group(0))
                atteso = stage[len("legacy-"):] if stage.startswith("legacy-") else stage
                self.assertEqual(ruolo, atteso)
                self.assertEqual(ruolo in bt.WRITING, atteso in bt.WRITING)


if __name__ == "__main__":
    unittest.main()
