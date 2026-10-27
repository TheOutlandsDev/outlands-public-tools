"""Fictional messages and explicit fake outcomes; no operational integrations."""
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from outbox import (Acceptance, DeliveryUncertain, FakeTransport, MAX_MESSAGES,
                    MAX_TICK, Message, Outbox, OutboxError, PermanentNotAccepted,
                    RetryableNotAccepted)
from demo import main, run_demo


def message(key="notice", **changes):
    return Message(**(dict(key=key, route="sample_route", subject="Fictional notice", body="Invented content.") | changes))


class Adapter:
    def __init__(self, function):
        self.send = function


def raises(error):
    def send(selected):
        raise error
    return Adapter(send)


def queued(**options):
    box = Outbox(**options)
    box.enqueue(message())
    return box


class ValidationTests(unittest.TestCase):
    def test_tokens_are_bounded_canonical_ascii(self):
        for field in ("key", "route"):
            for value in ("", "Upper", " space ", "bad/name", "a"*65, "\u212a", True, None):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(OutboxError, "TOKEN_INVALID"):
                    message(**{field: value})
        self.assertEqual(message(key="a"*64).key, "a"*64)

    def test_subject_exact_utf8_limit_and_one_extra_byte(self):
        self.assertEqual(len(message(subject="\u03bb"*80).subject.encode()), 160)
        self.assertEqual(message(subject="a"*160).subject, "a"*160)
        with self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_LIMIT"):
            message(subject="\u03bb"*80+"a")
        with self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_LIMIT"):
            message(subject=" "*161)

    def test_body_exact_utf8_limit_and_one_extra_byte(self):
        self.assertEqual(len(message(body="\u03bb"*4096).body.encode()), 8192)
        self.assertEqual(len(message(body="a"*8192).body), 8192)
        with self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_LIMIT"):
            message(body="\u03bb"*4096+"a")
        with self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_LIMIT"):
            message(body=" "*8193)

    def test_headers_reject_all_line_controls_and_unicode_separators(self):
        for token in ("\n", "\r", "\t", "\x00", "\x7f", "\x85", "\u2028", "\u2029"):
            with self.subTest(token=repr(token)), self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_INVALID"):
                message(subject="sample"+token+"text")

    def test_body_allows_lf_tab_but_rejects_other_controls(self):
        self.assertEqual(message(body="sample\n\ttext").body, "sample\n\ttext")
        for token in ("\r", "\x00", "\x1b", "\x7f", "\x85", "\u2028"):
            with self.subTest(token=repr(token)), self.assertRaisesRegex(OutboxError, "MESSAGE_TEXT_INVALID"):
                message(body="sample"+token+"text")

    def test_blank_non_text_and_invalid_unicode_are_refused(self):
        for field in ("subject", "body"):
            for value in ("", " \n\t", None, True, b"sample", "\ud800"):
                with self.subTest(field=field, kind=type(value).__name__), self.assertRaises(OutboxError):
                    message(**{field: value})

    def test_message_and_acceptance_are_immutable(self):
        selected = message()
        with self.assertRaises(FrozenInstanceError):
            selected.body = "changed"
        with self.assertRaises(FrozenInstanceError):
            Acceptance("receipt").receipt = "changed"
        with self.assertRaisesRegex(OutboxError, "TOKEN_INVALID"):
            Acceptance("not a receipt")

    def test_attempt_parameters_are_non_boolean_bounded_integers(self):
        for value in (0, 6, -1, True, 1.0, "3", None):
            with self.subTest(value=value), self.assertRaisesRegex(OutboxError, "OUTBOX_PARAMETER_INVALID"):
                Outbox(max_attempts=value)
        self.assertEqual(Outbox(max_attempts=5).max_attempts, 5)
        with self.assertRaises(AttributeError):
            Outbox().max_attempts = 99


class EnqueueTests(unittest.TestCase):
    def test_duplicate_enqueue_is_idempotent(self):
        box = queued()
        self.assertFalse(box.enqueue(message()))
        self.assertEqual(box.snapshot("notice").attempts, 0)

    def test_same_key_different_content_or_route_is_a_conflict(self):
        box = queued()
        for changes in (dict(route="other_route"), dict(subject="Other title"), dict(body="Other body")):
            with self.assertRaisesRegex(OutboxError, "IDEMPOTENCY_CONFLICT"):
                box.enqueue(message(**changes))
        self.assertEqual(box.snapshot("notice").code, "QUEUED")

    def test_capacity_retains_terminal_keys_and_allows_existing_duplicate(self):
        box = Outbox()
        for index in range(MAX_MESSAGES):
            box.enqueue(message("n"+str(index)))
        box.dispatch(FakeTransport(), now=0, limit=64)
        self.assertFalse(box.enqueue(message("n0")))
        with self.assertRaisesRegex(OutboxError, "OUTBOX_CAPACITY"):
            box.enqueue(message("extra"))

    def test_non_message_and_mutated_fields_are_revalidated(self):
        for value in (None, {}, "sample"):
            with self.assertRaisesRegex(OutboxError, "MESSAGE_REQUIRED"):
                Outbox().enqueue(value)
        selected = message()
        object.__setattr__(selected, "route", "bad route")
        with self.assertRaisesRegex(OutboxError, "TOKEN_INVALID"):
            Outbox().enqueue(selected)

    def test_defensive_copy_preserves_original_idempotency_content(self):
        selected = message()
        box = Outbox()
        box.enqueue(selected)
        object.__setattr__(selected, "body", "Changed outside the outbox.")
        self.assertFalse(box.enqueue(message()))

    def test_snapshots_omit_content_routes_and_receipts_and_are_frozen(self):
        box = queued()
        snapshot = box.dispatch(FakeTransport(), now=0)[0]
        self.assertEqual(set(snapshot.__dataclass_fields__), {"key", "state", "attempts", "next_attempt", "code"})
        self.assertNotIn("Invented content", repr(snapshot))
        self.assertNotIn("fake_receipt", repr(snapshot))
        with self.assertRaises(FrozenInstanceError):
            snapshot.state = "PENDING"

    def test_unknown_and_invalid_snapshot_keys_have_fixed_errors(self):
        with self.assertRaisesRegex(OutboxError, "MESSAGE_NOT_FOUND"):
            Outbox().snapshot("missing")
        with self.assertRaisesRegex(OutboxError, "TOKEN_INVALID"):
            Outbox().snapshot("not valid")


class DispatchTests(unittest.TestCase):
    def test_acceptance_is_terminal_and_does_not_claim_delivery(self):
        box, transport = queued(), FakeTransport()
        snapshot = box.dispatch(transport, now=0)[0]
        self.assertEqual((snapshot.state, snapshot.code, snapshot.attempts, snapshot.next_attempt), ("ACCEPTED", "ADAPTER_ACCEPTED", 1, None))
        self.assertEqual(box.dispatch(transport, now=100), ())
        self.assertEqual(transport.calls, 1)
        self.assertFalse(box.enqueue(message()))

    def test_retry_is_only_scheduled_after_explicit_non_acceptance(self):
        box, transport = queued(), FakeTransport(outcomes=("retry", "accept"))
        first = box.dispatch(transport, now=10)[0]
        self.assertEqual((first.state, first.next_attempt, first.code), ("PENDING", 11, "RETRY_SCHEDULED"))
        self.assertEqual(box.dispatch(transport, now=10), ())
        self.assertEqual(box.dispatch(transport, now=11)[0].state, "ACCEPTED")
        self.assertEqual(transport.calls, 2)

    def test_exponential_delay_and_attempt_exhaustion(self):
        box, transport = queued(max_attempts=5), FakeTransport(outcomes=("retry",)*5)
        for now, due in ((0, 1), (1, 3), (3, 7), (7, 15)):
            self.assertEqual(box.dispatch(transport, now=now)[0].next_attempt, due)
        last = box.dispatch(transport, now=15)[0]
        self.assertEqual((last.state, last.code, last.attempts), ("FAILED", "RETRY_EXHAUSTED", 5))
        self.assertEqual(box.dispatch(transport, now=MAX_TICK), ())
        self.assertEqual(transport.calls, 5)

    def test_single_attempt_policy_never_retries(self):
        result = queued(max_attempts=1).dispatch(FakeTransport(outcomes=("retry",)), now=0)[0]
        self.assertEqual((result.state, result.attempts, result.next_attempt), ("FAILED", 1, None))

    def test_retry_tick_overflow_fails_without_wraparound(self):
        result = queued().dispatch(FakeTransport(outcomes=("retry",)), now=MAX_TICK)[0]
        self.assertEqual((result.state, result.code, result.next_attempt), ("FAILED", "RETRY_EXHAUSTED", None))

    def test_permanent_rejection_never_retries(self):
        box, transport = queued(), FakeTransport(outcomes=("reject",))
        result = box.dispatch(transport, now=0)[0]
        self.assertEqual((result.state, result.code), ("FAILED", "DEFINITELY_REJECTED"))
        self.assertEqual(box.dispatch(transport, now=10), ())
        self.assertEqual(transport.calls, 1)

    def test_dispatch_limit_counts_attempts_in_insertion_order(self):
        box, transport = Outbox(), FakeTransport(outcomes=("retry",))
        for key in ("one", "two", "three"):
            box.enqueue(message(key))
        self.assertEqual([s.key for s in box.dispatch(transport, now=0, limit=2)], ["one", "two"])
        self.assertEqual([s.key for s in box.dispatch(transport, now=0, limit=2)], ["three"])
        self.assertEqual(transport.calls, 3)

    def test_clock_is_bounded_non_boolean_and_monotonic(self):
        box, transport = queued(), FakeTransport(outcomes=("retry",))
        box.dispatch(transport, now=10)
        before = box.snapshot("notice")
        for value in (9, -1, MAX_TICK+1, True, 10.0, "10", None):
            with self.subTest(value=value), self.assertRaisesRegex(OutboxError, "OUTBOX_CLOCK_INVALID"):
                box.dispatch(transport, now=value)
        self.assertEqual(box.snapshot("notice"), before)
        self.assertEqual(transport.calls, 1)

    def test_invalid_limit_does_not_call_transport_or_advance_clock(self):
        box, transport = queued(), FakeTransport()
        for value in (0, 65, True, 1.0, "1", None):
            with self.assertRaisesRegex(OutboxError, "OUTBOX_PARAMETER_INVALID"):
                box.dispatch(transport, now=100, limit=value)
        self.assertEqual(box.dispatch(transport, now=0)[0].state, "ACCEPTED")

    def test_invalid_transport_is_refused_before_attempt_and_clock_change(self):
        box = queued()
        class Broken:
            @property
            def send(self):
                raise RuntimeError("FICTIONAL_DO_NOT_ECHO")
        for value in (None, object(), Adapter(None), Broken()):
            with self.assertRaisesRegex(OutboxError, "OUTBOX_TRANSPORT_INVALID"):
                box.dispatch(value, now=100)
        self.assertEqual(box.snapshot("notice").attempts, 0)
        self.assertEqual(box.dispatch(FakeTransport(), now=0)[0].state, "ACCEPTED")

    def test_callback_sees_in_flight_and_cannot_reenter_mutators(self):
        box = queued()
        def send(selected):
            self.assertEqual(box.snapshot("notice").state, "IN_FLIGHT")
            for mutate in (lambda: box.enqueue(message("extra")), lambda: box.dispatch(FakeTransport(), now=0), lambda: box.report_delivery("notice", receipt="receipt")):
                with self.assertRaisesRegex(OutboxError, "OUTBOX_BUSY"):
                    mutate()
            return Acceptance("receipt")
        self.assertEqual(box.dispatch(Adapter(send), now=0)[0].state, "ACCEPTED")
        self.assertTrue(box.enqueue(message("extra")))

    def test_adapter_gets_a_copy_instead_of_owned_idempotency_message(self):
        box = queued()
        def send(selected):
            object.__setattr__(selected, "body", "Changed by fake adapter.")
            return Acceptance("receipt")
        box.dispatch(Adapter(send), now=0)
        self.assertFalse(box.enqueue(message()))


class UncertaintyTests(unittest.TestCase):
    def test_generic_exception_and_explicit_uncertainty_require_review(self):
        class Unprintable(OutboxError):
            def __str__(self):
                raise AssertionError("EXCEPTION_TEXT_TOUCHED")
        for error in (RuntimeError("FICTIONAL_DO_NOT_ECHO"), DeliveryUncertain("FICTIONAL_DO_NOT_ECHO"), TimeoutError("FICTIONAL_DO_NOT_ECHO"), Unprintable()):
            box = queued()
            result = box.dispatch(raises(error), now=0)[0]
            self.assertEqual((result.state, result.code, result.next_attempt), ("REVIEW_REQUIRED", "DELIVERY_UNCERTAIN", None))
            self.assertNotIn("FICTIONAL_DO_NOT_ECHO", repr(result))
            self.assertEqual(box.dispatch(FakeTransport(), now=10), ())

    def test_provider_acceptance_followed_by_lost_response_is_not_replayed(self):
        box, transport = queued(), FakeTransport(outcomes=("accepted_then_unknown",))
        result = box.dispatch(transport, now=0)[0]
        self.assertEqual(result.state, "REVIEW_REQUIRED")
        self.assertEqual(transport.accepted_keys, ("notice",))
        for now in (1, 100, MAX_TICK):
            self.assertEqual(box.dispatch(transport, now=now), ())
        self.assertEqual(transport.calls, 1)

    def test_invalid_result_or_mutated_receipt_is_review_not_retry(self):
        damaged = Acceptance("receipt")
        object.__setattr__(damaged, "receipt", "FICTIONAL_DO_NOT_ECHO")
        for value in (None, "receipt", {}, damaged):
            box = queued()
            result = box.dispatch(Adapter(lambda selected: value), now=0)[0]
            self.assertEqual((result.state, result.code), ("REVIEW_REQUIRED", "ADAPTER_RESULT_INVALID"))
            self.assertNotIn("FICTIONAL_DO_NOT_ECHO", repr(result))
            self.assertEqual(box.dispatch(FakeTransport(), now=1), ())

    def test_control_exceptions_record_uncertainty_and_are_reraised(self):
        for error in (KeyboardInterrupt(), SystemExit(3), GeneratorExit()):
            box = queued()
            with self.assertRaises(type(error)):
                box.dispatch(raises(error), now=0)
            snapshot = box.snapshot("notice")
            self.assertEqual((snapshot.state, snapshot.code), ("REVIEW_REQUIRED", "DELIVERY_INTERRUPTED"))
            self.assertEqual(box.dispatch(FakeTransport(), now=1), ())
            self.assertTrue(box.enqueue(message("extra")))

    def test_interruption_stops_later_pending_messages(self):
        box = queued()
        box.enqueue(message("later"))
        with self.assertRaises(KeyboardInterrupt):
            box.dispatch(FakeTransport(outcomes=("interrupt",)), now=0)
        self.assertEqual(box.snapshot("later").attempts, 0)
        self.assertEqual([s.key for s in box.dispatch(FakeTransport(), now=1)], ["later"])

    def test_generic_failure_can_be_inspected_without_blocking_other_messages(self):
        box = queued()
        box.enqueue(message("later"))
        result = box.dispatch(FakeTransport(outcomes=("uncertain", "accept")), now=0)
        self.assertEqual([s.state for s in result], ["REVIEW_REQUIRED", "ACCEPTED"])


class DeliveryReportTests(unittest.TestCase):
    def test_matching_report_is_explicit_caller_assertion_and_idempotent(self):
        box = queued()
        box.dispatch(FakeTransport(), now=0)
        self.assertTrue(box.report_delivery("notice", receipt="fake_receipt"))
        self.assertFalse(box.report_delivery("notice", receipt="fake_receipt"))
        result = box.snapshot("notice")
        self.assertEqual((result.state, result.code), ("DELIVERY_REPORTED", "CALLER_REPORTED_DELIVERY"))
        self.assertEqual(box.dispatch(FakeTransport(), now=1), ())

    def test_wrong_receipt_is_refused_without_changing_acceptance(self):
        box = queued()
        box.dispatch(FakeTransport(), now=0)
        before = box.snapshot("notice")
        with self.assertRaisesRegex(OutboxError, "DELIVERY_REPORT_REFUSED"):
            box.report_delivery("notice", receipt="different_receipt")
        self.assertEqual(box.snapshot("notice"), before)

    def test_pending_failed_or_uncertain_state_cannot_be_reported_delivered(self):
        for transport in (None, FakeTransport(outcomes=("reject",)), FakeTransport(outcomes=("accepted_then_unknown",))):
            box = queued()
            if transport is not None:
                box.dispatch(transport, now=0)
            with self.assertRaisesRegex(OutboxError, "DELIVERY_REPORT_REFUSED"):
                box.report_delivery("notice", receipt="fake_receipt")

    def test_report_keys_and_receipts_are_validated(self):
        with self.assertRaisesRegex(OutboxError, "MESSAGE_NOT_FOUND"):
            Outbox().report_delivery("missing", receipt="receipt")
        with self.assertRaisesRegex(OutboxError, "TOKEN_INVALID"):
            queued().report_delivery("notice", receipt="bad receipt")


class FakeTests(unittest.TestCase):
    def test_fake_parameter_contract_is_bounded_and_explicit(self):
        for value in ([], "accept", None, ("unknown",), (True,), ("accept",)*65):
            with self.assertRaisesRegex(OutboxError, "FAKE_PARAMETER_INVALID"):
                FakeTransport(outcomes=value)

    def test_fake_idempotency_prevents_second_acceptance_and_conflicts(self):
        transport = FakeTransport(outcomes=("accept", "retry"))
        self.assertEqual(transport.send(message()), Acceptance("fake_receipt"))
        self.assertEqual(transport.send(message()), Acceptance("fake_receipt"))
        self.assertEqual(transport.accepted_keys, ("notice",))
        with self.assertRaises(PermanentNotAccepted):
            transport.send(message(body="Different body."))

    def test_fake_cache_is_bounded_and_does_not_claim_delivery(self):
        transport = FakeTransport()
        for index in range(64):
            transport.send(message("n"+str(index)))
        with self.assertRaises(PermanentNotAccepted):
            transport.send(message("extra"))
        self.assertEqual(len(transport.accepted_keys), 64)


class CliTests(unittest.TestCase):
    def test_demo_uses_no_file_network_process_or_shell_adapter(self):
        with mock.patch("builtins.open", side_effect=AssertionError("FILE_OPENED")), mock.patch.object(socket, "socket", side_effect=AssertionError("NETWORK")), mock.patch.object(subprocess, "run", side_effect=AssertionError("PROCESS")), mock.patch.object(os, "system", side_effect=AssertionError("SHELL")):
            result = run_demo()
        self.assertEqual(result, run_demo())
        self.assertTrue(result["uncertain_not_replayed"])
        self.assertTrue(result["fake_acceptance_occurred"])
        self.assertFalse(result["real_delivery_verified"])

    def test_actual_cli_creates_no_files_and_preserves_source(self):
        def hashes():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob("*.py")}
        before = hashes()
        with tempfile.TemporaryDirectory(prefix="fictional-outbox-", dir=os.environ.get("OUTLANDS_TEST_TEMP")) as folder:
            result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), "--demo"], cwd=folder, capture_output=True, text=True, timeout=20)
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            self.assertEqual(json.loads(result.stdout), run_demo())
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(hashes(), before)

    def test_help_and_no_arguments_have_static_program_name(self):
        for arguments in ([], ["--help"]):
            result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), *arguments], capture_output=True, text=True, timeout=20)
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            self.assertIn("notification-outbox", result.stdout)
            self.assertNotIn(str(ROOT), result.stdout)

    def test_invalid_arguments_do_not_echo_supplied_values(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT/"demo.py"), "--unknown", "FICTIONAL_DO_NOT_ECHO"], capture_output=True, text=True, timeout=20)
        self.assertEqual((result.returncode, result.stderr), (2, ""))
        self.assertEqual(json.loads(result.stdout), dict(status="ERROR", code="ARGUMENTS_INVALID"))

    def test_interruption_has_fixed_cli_code(self):
        output = io.StringIO()
        with mock.patch("demo.run_demo", side_effect=KeyboardInterrupt), mock.patch("sys.stdout", output):
            status = main(["--demo"])
        self.assertEqual((status, json.loads(output.getvalue())), (130, dict(status="ERROR", code="INTERRUPTED")))


if __name__ == "__main__":
    unittest.main()
