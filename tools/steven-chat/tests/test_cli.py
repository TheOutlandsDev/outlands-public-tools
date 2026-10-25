"""Original MIT subprocess CLI tests; fixtures contain no real conversations."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from http_fixture import chat_reply, http_fixture

ROOT = Path(__file__).resolve().parents[1]


def cli(*args, stdin=None, module=True):
    command = [sys.executable, "-B"]
    command += ["-m", "steven"] if module else []
    return subprocess.run(command + list(args), cwd=ROOT, input=stdin, text=True,
                          encoding="utf-8", errors="replace", capture_output=True, timeout=8)


class CliTests(unittest.TestCase):
    def test_help_is_offline(self):
        result = cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("connect", result.stdout)

    def test_no_arguments_is_offline(self):
        result = cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout)

    def test_demo_is_explicitly_simulated(self):
        result = cli("--demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("simulat", result.stdout.lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_old_name_wrappers_support_demo(self):
        for wrapper in ["main.py", "chatbot.py", "stephen.py"]:
            with self.subTest(wrapper=wrapper):
                result = cli(wrapper, "--demo", module=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("simulat", result.stdout.lower())

    def test_live_action_requires_connect_before_http_contact(self):
        with http_fixture([chat_reply()]) as (endpoint, requests):
            result = cli("ask", "--endpoint", endpoint, "--model", "fixture:tiny", "--prompt", "Fictional user")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [])
        self.assertIn("connect", result.stderr.lower())

    def test_model_list_requires_connect_before_http_contact(self):
        with http_fixture([{"body": {"models": []}}]) as (endpoint, requests):
            result = cli("models", "--endpoint", endpoint)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [])

    def test_no_connect_does_not_create_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.json"
            result = cli("ask", "--model", "fixture:tiny", "--prompt", "Fictional user", "--save", str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(path.exists())

    def test_ask_connect_reaches_fixture_and_prints_reply(self):
        with http_fixture([chat_reply("Fictional result only")]) as (endpoint, requests):
            result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny", "--prompt", "Fictional user")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Fictional result only", result.stdout)
        self.assertEqual(json.loads(requests[0]["body"])["messages"], [{"role": "user", "content": "Fictional user"}])

    def test_model_list_connect_reaches_fixture(self):
        with http_fixture([{"body": {"models": [{"name": "fixture:tiny"}]}}]) as (endpoint, requests):
            result = cli("models", "--connect", "--endpoint", endpoint)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fixture:tiny", result.stdout)
        self.assertEqual(len(requests), 1)

    def test_successful_exchange_can_be_explicitly_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new.json"
            with http_fixture([chat_reply("Fictional answer")]) as (endpoint, _):
                result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny",
                             "--prompt", "Fictional question", "--save", str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            session = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(session["schema"], 1)
            self.assertEqual(session["messages"], [{"role": "user", "content": "Fictional question"},
                                                    {"role": "assistant", "content": "Fictional answer"}])

    def test_resuming_sends_history_and_does_not_modify_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.json"
            session = {"schema": 1, "model": "fixture:tiny", "messages": [
                {"role": "user", "content": "Earlier fictional question"},
                {"role": "assistant", "content": "Earlier fictional answer"}]}
            original = json.dumps(session).encode()
            path.write_bytes(original)
            with http_fixture([chat_reply()]) as (endpoint, requests):
                result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny",
                             "--prompt", "Next fictional question", "--session", str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(json.loads(requests[0]["body"])["messages"], session["messages"] + [
                {"role": "user", "content": "Next fictional question"}])

    def test_session_model_mismatch_is_refused_before_contact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.json"
            path.write_text(json.dumps({"schema": 1, "model": "other:tiny", "messages": []}), encoding="utf-8")
            with http_fixture([chat_reply()]) as (endpoint, requests):
                result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny",
                             "--prompt", "Fictional question", "--session", str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(requests, [])

    def test_failed_exchange_does_not_save_partial_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.json"
            with http_fixture([{"status": 500, "body": "PRIVATE-FIXTURE-ERROR"}]) as (endpoint, _):
                result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny",
                             "--prompt", "Fictional question", "--save", str(path))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(path.exists())
            self.assertNotIn("PRIVATE-FIXTURE-ERROR", result.stdout + result.stderr)

    def test_server_output_cannot_emit_terminal_control_sequences(self):
        with http_fixture([chat_reply("\x1b[2JRESET\r\x00\u202eFictional")]) as (endpoint, _):
            result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny", "--prompt", "Fictional question")
        self.assertEqual(result.returncode, 0, result.stderr)
        for control in ["\x1b", "\x00", "\u202e"]:
            self.assertNotIn(control, result.stdout)
        self.assertIn("Fictional", result.stdout)

    def test_unicode_reply_survives_ascii_output_encoding(self):
        with patch.dict(os.environ, {"PYTHONIOENCODING": "ascii"}), http_fixture([chat_reply("Fictional café 🧪")]) as (endpoint, _):
            result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny", "--prompt", "Fictional question")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Fictional", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_shell_like_model_text_is_printed_and_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "never-created.txt"
            malicious = f"python -c 'open({str(marker)!r}, \"w\").write(\"bad\")'"
            with http_fixture([chat_reply(malicious)]) as (endpoint, _):
                result = cli("ask", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny", "--prompt", "Fictional question")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertIn("never-created.txt", result.stdout)

    def test_eof_exits_chat_without_request_or_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-created.json"
            with http_fixture([chat_reply()]) as (endpoint, requests):
                result = cli("chat", "--connect", "--endpoint", endpoint, "--model", "fixture:tiny", "--save", str(path), stdin="")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(requests, [])
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
