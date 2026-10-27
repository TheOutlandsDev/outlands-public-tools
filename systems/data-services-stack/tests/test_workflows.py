from base import Fixture, canonical, fictional_configuration, fictional_input
from copy import deepcopy
import json
from unittest import mock

from data_services.components.outbox import Acceptance, FakeTransport
from data_services.contracts import StackError
from data_services.service import Stack
import data_services.service as service


class Workflows(Fixture):
    def test_complete_run_persists_forecast_score_and_one_notification(self):
        self.create(run=True)
        with Stack(self.root) as app:
            result = app.result("notice")["result"]
            self.assertEqual([p["value"] for p in result["forecast"]], [10,10,10])
            self.assertEqual(result["score"], dict(count=3,mae=4,rmse=4))
            self.assertEqual(app.queue()[0]["state"], "PENDING")

    def test_same_run_key_input_and_configuration_do_not_reexecute(self):
        self.create(run=True)
        with Stack(self.root) as app, mock.patch.object(service,"_calculate",side_effect=AssertionError("REEXECUTED")):
            before = app.sequence
            self.assertEqual(app.run("sample","notice",fictional_input())["state"], "COMPLETED")
            self.assertEqual(app.sequence, before)

    def test_changed_input_or_job_under_existing_key_is_a_conflict(self):
        self.create(run=True)
        with Stack(self.root) as app:
            with self.assertRaisesRegex(StackError,"RUN_IDEMPOTENCY_CONFLICT"):
                app.run("sample","notice",fictional_input()+b"\n")
            config = json.loads(fictional_configuration())
            config["jobs"][0]["horizon"] = 2
            app.configure(canonical(config))
            with self.assertRaisesRegex(StackError,"RUN_IDEMPOTENCY_CONFLICT"):
                app.run("sample","notice",fictional_input())

    def test_rejected_rows_never_reach_forecasting_or_notification(self):
        self.create()
        with Stack(self.root) as app, mock.patch.object(service,"forecast",side_effect=AssertionError("FORECASTED")):
            result = app.run("sample","bad",b"null")
            self.assertEqual((result["state"],result["code"]), ("REJECTED","BATCH_REVIEW_REQUIRED"))
            self.assertEqual(app.queue(), [])

    def test_forecast_gaps_and_insufficient_history_never_enqueue(self):
        self.create()
        for key,raw in (("gap",b'{"series":"sample","period":0,"value":1}\n{"series":"sample","period":2,"value":2}'),
                        ("short",b'{"series":"sample","period":0,"value":1}')):
            with Stack(self.root) as app:
                self.assertEqual(app.run("sample",key,raw)["state"], "REJECTED")
                self.assertEqual(app.queue(), [])

    def test_invalid_utf8_is_recorded_without_retaining_raw_data_or_path(self):
        self.create()
        with Stack(self.root) as app:
            self.assertEqual(app.run("sample","bad",b"\xffFICTIONAL_DO_NOT_ECHO")["code"], "INPUT_ENCODING_INVALID")
        for path in self.root.rglob("state.json"):
            self.assertNotIn(b"FICTIONAL_DO_NOT_ECHO", path.read_bytes())
            self.assertNotIn(str(self.root).encode(), path.read_bytes())

    def test_multiple_jobs_and_csv_use_one_shared_contract(self):
        self.create()
        config = json.loads(fictional_configuration())
        config["jobs"].append(dict(config["jobs"][0],id="csv_job",input_format="csv"))
        csv = b"series,period,value\n"+b"\n".join(f"sample,{i},{2*(i+1)}".encode() for i in range(6))
        with Stack(self.root) as app:
            app.configure(canonical(config))
            app.run("sample","one",fictional_input())
            app.run("csv_job","two",csv)
            self.assertEqual(app.result("one")["result"], app.result("two")["result"])

    def test_configuration_replacement_preserves_historical_job_snapshot(self):
        self.create(run=True)
        config = json.loads(fictional_configuration())
        config["jobs"][0]["route"] = "other_route"
        with Stack(self.root) as app:
            app.configure(canonical(config))
            self.assertEqual(app.result("notice")["job"]["route"], "sample_route")

    def test_configuration_repetition_is_idempotent(self):
        self.create()
        with Stack(self.root) as app:
            before = app.sequence
            self.assertFalse(app.configure(fictional_configuration())["changed"])
            self.assertEqual(app.sequence,before)

    def test_unknown_jobs_and_oversized_inputs_do_not_start_runs(self):
        self.create()
        with Stack(self.root) as app:
            for job,raw in (("missing",b"sample"),("sample",b"x"*65537)):
                with self.assertRaises(StackError):
                    app.run(job,"key",raw)
            self.assertEqual(app.status()["runs"], [])

    def test_handled_run_interruption_is_reviewed_without_enqueue(self):
        self.create()
        with Stack(self.root) as app, mock.patch.object(service,"_calculate",side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                app.run("sample","interrupted",fictional_input())
            self.assertEqual(app.result("interrupted")["state"], "REVIEW_REQUIRED")
            self.assertEqual(app.queue(), [])

    def test_retry_survives_restart_with_monotonic_ticks(self):
        self.create(run=True)
        with Stack(self.root) as app:
            self.assertEqual(app.dispatch(FakeTransport(outcomes=("retry",)),now=10)[0]["next_attempt"],11)
        with Stack(self.root) as app:
            with self.assertRaisesRegex(StackError,"CLOCK_INVALID"):
                app.dispatch(FakeTransport(),now=9)
            self.assertEqual(app.dispatch(FakeTransport(),now=10), [])
            self.assertEqual(app.dispatch(FakeTransport(),now=11)[0]["attempts"],2)

    def test_retry_exhaustion_and_permanent_rejection_are_terminal(self):
        self.create(run=True)
        with Stack(self.root) as app:
            for tick in (0,1,3):
                result = app.dispatch(FakeTransport(outcomes=("retry",)),now=tick)[0]
            self.assertEqual((result["state"],result["attempts"]), ("FAILED",3))
            app.run("sample","second",fictional_input())
            self.assertEqual(app.dispatch(FakeTransport(outcomes=("reject",)),now=4)[0]["code"],"DEFINITELY_REJECTED")
            self.assertEqual(app.dispatch(FakeTransport(),now=100), [])

    def test_uncertain_acceptance_is_not_replayed_after_restart(self):
        self.create(run=True)
        fake = FakeTransport(outcomes=("accepted_then_unknown",))
        with Stack(self.root) as app:
            self.assertEqual(app.dispatch(fake,now=0)[0]["state"], "REVIEW_REQUIRED")
        self.assertEqual(fake.accepted_keys, ("notice",))
        with Stack(self.root) as app:
            fresh = FakeTransport()
            self.assertEqual(app.dispatch(fresh,now=100), [])
            self.assertEqual(fresh.calls,0)

    def test_generic_adapter_error_and_invalid_receipt_are_never_retried(self):
        self.create(run=True)
        class Adapter:
            def send(self,selected):
                raise RuntimeError("FICTIONAL_DO_NOT_ECHO")
        with Stack(self.root) as app:
            self.assertEqual(app.dispatch(Adapter(),now=0)[0]["code"], "DELIVERY_UNCERTAIN")
            self.assertNotIn("FICTIONAL_DO_NOT_ECHO", repr(app.queue()))
            app.run("sample","second",fictional_input())
            class Invalid:
                def send(self,selected):return "FICTIONAL_DO_NOT_ECHO"
            self.assertEqual(app.dispatch(Invalid(),now=1)[0]["code"],"ADAPTER_RESULT_INVALID")

    def test_delivery_report_requires_matching_accepted_receipt(self):
        self.create(run=True)
        with Stack(self.root) as app:
            with self.assertRaisesRegex(StackError,"DELIVERY_REPORT_REFUSED"):
                app.report_delivery("notice","fake_receipt")
            app.dispatch(FakeTransport(),now=0)
            with self.assertRaisesRegex(StackError,"DELIVERY_REPORT_REFUSED"):
                app.report_delivery("notice","wrong_receipt")
            self.assertTrue(app.report_delivery("notice","fake_receipt")["changed"])
            self.assertFalse(app.report_delivery("notice","fake_receipt")["changed"])
        with Stack(self.root) as app:
            self.assertEqual(app.queue()[0]["state"],"DELIVERY_REPORTED")

    def test_callback_mutations_and_close_are_refused_while_in_flight(self):
        self.create(run=True)
        with Stack(self.root) as app:
            test = self
            class Adapter:
                def send(self,selected):
                    test.assertEqual(app.queue()[0]["state"],"IN_FLIGHT")
                    for call in (lambda:app.recover(confirm_stopped=True),app.close,
                                 lambda:app.configure(fictional_configuration())):
                        with test.assertRaisesRegex(StackError,"OPERATION_IN_PROGRESS"):
                            call()
                    return Acceptance("receipt")
            self.assertEqual(app.dispatch(Adapter(),now=0)[0]["state"],"ACCEPTED")

    def test_result_reads_are_defensive_and_status_omits_records(self):
        self.create(run=True)
        with Stack(self.root) as app:
            selected = app.result("notice")
            selected["result"]["forecast"][0]["value"] = 99
            self.assertEqual(app.result("notice")["result"]["forecast"][0]["value"],10)
            self.assertNotIn("forecast",canonical(app.status()).decode())
