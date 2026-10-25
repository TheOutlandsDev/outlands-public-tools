"""Original MIT context and session tests using generated disposable data."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from steven import ChatError, Conversation, load_session, save_session


class FakeClient:
    def __init__(self, answer="Fictional answer.", error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def chat(self, model, messages):
        self.calls.append((model, copy.deepcopy(messages)))
        if self.error:
            raise self.error
        return self.answer


def pair(user="Fictional user", assistant="Fictional assistant"):
    return [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]


class ConversationTests(unittest.TestCase):
    def test_new_conversation_is_empty_and_model_explicit(self):
        conversation = Conversation("fixture:tiny")
        self.assertEqual(conversation.to_dict(), {"schema": 1, "model": "fixture:tiny", "messages": []})

    def test_success_appends_one_complete_pair(self):
        conversation = Conversation("fixture:tiny")
        client = FakeClient()
        self.assertEqual(conversation.ask(client, "Fictional user"), "Fictional answer.")
        self.assertEqual(conversation.messages, pair(assistant="Fictional answer."))
        self.assertEqual(client.calls, [("fixture:tiny", [{"role": "user", "content": "Fictional user"}])])

    def test_multiple_turns_send_retained_context(self):
        conversation = Conversation("fixture:tiny", pair())
        client = FakeClient()
        conversation.ask(client, "Second fictional user")
        self.assertEqual(client.calls[0][1], pair() + [{"role": "user", "content": "Second fictional user"}])
        self.assertEqual(len(conversation.messages), 4)

    def test_backend_failure_is_transactional(self):
        conversation = Conversation("fixture:tiny", pair())
        before = conversation.to_dict()
        with self.assertRaises(ChatError):
            conversation.ask(FakeClient(error=ChatError("Fictional failure")), "Do not retain failed prompt")
        self.assertEqual(conversation.to_dict(), before)

    def test_invalid_prompt_does_not_contact_client_or_change_history(self):
        for prompt in ["", "   ", "x" * 8193, None, 4, "\ud800"]:
            conversation = Conversation("fixture:tiny", pair())
            client = FakeClient()
            before = conversation.to_dict()
            with self.subTest(prompt=repr(prompt)[:50]), self.assertRaises(ChatError):
                conversation.ask(client, prompt)
            self.assertEqual(client.calls, [])
            self.assertEqual(conversation.to_dict(), before)

    def test_messages_property_is_a_defensive_copy(self):
        conversation = Conversation("fixture:tiny", pair())
        exposed = conversation.messages
        exposed[0]["content"] = "Changed outside"
        exposed.append({"role": "user", "content": "Extra"})
        self.assertEqual(conversation.messages, pair())

    def test_constructor_does_not_retain_input_list(self):
        source = pair()
        conversation = Conversation("fixture:tiny", source)
        source[0]["content"] = "Changed outside"
        self.assertEqual(conversation.messages, pair())

    def test_dict_export_is_a_defensive_copy(self):
        conversation = Conversation("fixture:tiny", pair())
        exported = conversation.to_dict()
        exported["messages"][0]["content"] = "Changed outside"
        self.assertEqual(conversation.messages, pair())

    def test_trim_drops_whole_pairs_and_preserves_system(self):
        system = {"role": "system", "content": "s" * 100}
        conversation = Conversation("fixture:tiny", [system], context_chars=1024)
        client = FakeClient(answer="a" * 300)
        conversation.ask(client, "u" * 500)
        conversation.ask(client, "v" * 500)
        self.assertEqual(client.calls[-1][1], [system, {"role": "user", "content": "v" * 500}])
        self.assertEqual(conversation.messages, [system] + pair("v" * 500, "a" * 300))
        self.assertLessEqual(sum(len(m["content"]) for m in conversation.messages), 1024)

    def test_failure_after_planned_trim_preserves_old_history(self):
        history = pair("u" * 500, "a" * 300)
        conversation = Conversation("fixture:tiny", history, context_chars=1024)
        before = conversation.messages
        with self.assertRaises(ChatError):
            conversation.ask(FakeClient(error=ChatError("Fictional failure")), "v" * 500)
        self.assertEqual(conversation.messages, before)

    def test_oversized_current_exchange_is_refused_without_partial_commit(self):
        conversation = Conversation("fixture:tiny", pair(), context_chars=1024)
        before = conversation.messages
        with self.assertRaises(ChatError):
            conversation.ask(FakeClient(answer="a" * 1200), "Fictional user")
        self.assertEqual(conversation.messages, before)

    def test_prompt_larger_than_context_is_refused_before_contact(self):
        conversation = Conversation("fixture:tiny", context_chars=1024)
        client = FakeClient()
        with self.assertRaises(ChatError):
            conversation.ask(client, "u" * 1025)
        self.assertEqual(client.calls, [])

    def test_context_budget_bounds_and_types(self):
        for value in [0, 1023, 65537, True, 1024.0, "1024"]:
            with self.subTest(value=value), self.assertRaises(ChatError):
                Conversation("fixture:tiny", context_chars=value)

    def test_invalid_history_role_order_and_fields_refused(self):
        histories = [None, "wrong", [{}], [{"role": "assistant", "content": "orphan"}],
                     [{"role": "user", "content": "unfinished"}],
                     pair() + [{"role": "system", "content": "late system"}],
                     [{"role": "tool", "content": "unsupported"}],
                     [{"role": "system", "content": "s", "extra": True}],
                     [{"role": "system", "content": 4}],
                     [{"role": "system", "content": "\ud800"}],
                     [{"role": "system", "content": "s" * 8193}]]
        # None is the documented empty-history default; every other value is invalid.
        for messages in histories[1:]:
            with self.subTest(messages=repr(messages)[:80]), self.assertRaises(ChatError):
                Conversation("fixture:tiny", messages)

    def test_too_many_history_messages_refused(self):
        with self.assertRaises(ChatError):
            Conversation("fixture:tiny", pair() * 65)

    def test_total_history_size_refused(self):
        with self.assertRaises(ChatError):
            Conversation("fixture:tiny", pair("u" * 8192, "a" * 8192) * 5)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, value, name="session.json"):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_session_round_trip(self):
        conversation = Conversation("fixture:tiny", pair("café", "Fictional response"))
        path = self.root / "new-session.json"
        save_session(path, conversation)
        self.assertEqual(load_session(path).to_dict(), conversation.to_dict())

    def test_save_refuses_overwrite_and_retains_old_bytes(self):
        path = self.root / "existing.json"
        original = b"Existing fixture bytes"
        path.write_bytes(original)
        with self.assertRaises(ChatError):
            save_session(path, Conversation("fixture:tiny"))
        self.assertEqual(path.read_bytes(), original)

    def test_save_does_not_create_parent_directories(self):
        parent = self.root / "absent"
        with self.assertRaises(ChatError):
            save_session(parent / "new.json", Conversation("fixture:tiny"))
        self.assertFalse(parent.exists())

    def test_session_requires_exact_versioned_schema(self):
        valid = Conversation("fixture:tiny", pair()).to_dict()
        invalid = [[], {}, {**valid, "schema": 2}, {**valid, "schema": True}, {**valid, "extra": "private"},
                   {k: v for k, v in valid.items() if k != "model"}, {**valid, "messages": "not a list"},
                   {**valid, "model": "model:cloud"}]
        for number, value in enumerate(invalid):
            with self.subTest(value=value), self.assertRaises(ChatError):
                load_session(self.write(value, f"invalid-{number}.json"))

    def test_session_duplicate_keys_refused(self):
        path = self.root / "duplicate.json"
        path.write_bytes(b'{"schema":1,"schema":1,"model":"fixture:tiny","messages":[]}')
        with self.assertRaises(ChatError):
            load_session(path)

    def test_session_nonfinite_json_refused(self):
        path = self.root / "nan.json"
        path.write_bytes(b'{"schema":NaN,"model":"fixture:tiny","messages":[]}')
        with self.assertRaises(ChatError):
            load_session(path)

    def test_session_invalid_utf8_refused(self):
        path = self.root / "bad-encoding.json"
        path.write_bytes(b"\xff\xfe")
        with self.assertRaises(ChatError):
            load_session(path)

    def test_session_oversized_bytes_refused(self):
        path = self.root / "oversized.json"
        path.write_bytes(b" " * (1024 * 1024 + 1))
        with self.assertRaises(ChatError):
            load_session(path)

    def test_session_missing_or_directory_refused(self):
        for path in [self.root / "missing.json", self.root]:
            with self.subTest(path=path.name), self.assertRaises(ChatError):
                load_session(path)

    def test_symlink_input_and_output_refused(self):
        target = self.write(Conversation("fixture:tiny").to_dict(), "target.json")
        link = self.root / "linked.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks is unavailable for this test account")
        with self.assertRaises(ChatError):
            load_session(link)
        with self.assertRaises(ChatError):
            save_session(link, Conversation("fixture:tiny"))

    def test_symlink_parent_input_and_output_refused(self):
        target = self.root / "real"
        target.mkdir()
        (target / "existing.json").write_text(json.dumps(Conversation("fixture:tiny").to_dict()), encoding="utf-8")
        link = self.root / "linked-parent"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks is unavailable for this test account")
        with self.assertRaises(ChatError):
            load_session(link / "existing.json")
        with self.assertRaises(ChatError):
            save_session(link / "new.json", Conversation("fixture:tiny"))
        self.assertFalse((target / "new.json").exists())


if __name__ == "__main__":
    unittest.main()
