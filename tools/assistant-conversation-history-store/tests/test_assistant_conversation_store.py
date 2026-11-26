import tempfile
import unittest
from pathlib import Path

from assistant_conversation_store import ChatDatabase


class DatabaseTests(unittest.TestCase):
    def test_chat_and_tool_history_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = ChatDatabase(Path(directory) / "chat.sqlite3")
            chat = database.create_chat("fictional-model")
            database.add_message(chat.id, "user", "Sketch a sample report")
            calls = [
                {
                    "function": {
                        "name": "preview_note",
                        "arguments": {"section": "summary"},
                    }
                }
            ]
            database.add_message(
                chat.id, "assistant", "", tool_calls=calls
            )
            database.add_message(
                chat.id, "tool", '{"ok": true}', tool_name="preview_note"
            )

            messages = database.list_messages(chat.id)
            self.assertEqual([message.role for message in messages], ["user", "assistant", "tool"])
            self.assertEqual(messages[1].tool_calls, calls)
            self.assertEqual(messages[2].tool_name, "preview_note")
            self.assertEqual(database.get_chat(chat.id).title, "Sketch a sample report")
