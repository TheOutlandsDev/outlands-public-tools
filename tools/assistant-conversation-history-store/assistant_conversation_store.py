"""Store assistant conversation history in a caller-selected SQLite database."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class Chat:
    id: str
    title: str
    model: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class Message:
    id: int
    chat_id: str
    role: str
    content: str
    thinking: str
    tool_name: str
    tool_calls: list[dict[str, Any]]
    created_at: str

    def as_ollama(self) -> dict[str, Any]:
        message: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_name:
            message["tool_name"] = self.tool_name
        if self.tool_calls:
            message["tool_calls"] = self.tool_calls
        return message


class ChatDatabase:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    thinking TEXT NOT NULL DEFAULT '',
                    tool_name TEXT NOT NULL DEFAULT '',
                    tool_calls_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_chat
                    ON messages(chat_id, id);
                CREATE INDEX IF NOT EXISTS idx_chats_updated
                    ON chats(updated_at DESC);
                """
            )

    def create_chat(self, model: str, title: str = "New conversation") -> Chat:
        chat_id = str(uuid.uuid4())
        now = utc_now()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO chats(id, title, model, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (chat_id, title, model, now, now),
            )
        return Chat(chat_id, title, model, now, now)

    def get_chat(self, chat_id: str) -> Chat | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT * FROM chats WHERE id = ?", (chat_id,)
            ).fetchone()
        return Chat(**dict(row)) if row else None

    def list_chats(self, search: str = "") -> list[Chat]:
        with closing(self._connect()) as connection, connection:
            if search.strip():
                rows = connection.execute(
                    "SELECT * FROM chats WHERE title LIKE ? "
                    "ORDER BY updated_at DESC",
                    (f"%{search.strip()}%",),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM chats ORDER BY updated_at DESC"
                ).fetchall()
        return [Chat(**dict(row)) for row in rows]

    def rename_chat(self, chat_id: str, title: str) -> None:
        title = " ".join(title.strip().split())[:80] or "New conversation"
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
                (title, utc_now(), chat_id),
            )

    def delete_chat(self, chat_id: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str = "",
        *,
        thinking: str = "",
        tool_name: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> int:
        now = utc_now()
        encoded_calls = json.dumps(tool_calls or [], ensure_ascii=False)
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO messages(
                    chat_id, role, content, thinking, tool_name,
                    tool_calls_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    role,
                    content,
                    thinking,
                    tool_name,
                    encoded_calls,
                    now,
                ),
            )
            connection.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id)
            )
            message_id = int(cursor.lastrowid)

        if role == "user":
            chat = self.get_chat(chat_id)
            if chat and chat.title == "New conversation":
                first_line = next(
                    (line.strip() for line in content.splitlines() if line.strip()),
                    "New conversation",
                )
                if first_line.startswith("[Attached local file:"):
                    first_line = "Local file conversation"
                self.rename_chat(chat_id, first_line[:56])
        return message_id

    def list_messages(self, chat_id: str) -> list[Message]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY id",
                (chat_id,),
            ).fetchall()
        messages: list[Message] = []
        for row in rows:
            data = dict(row)
            try:
                tool_calls = json.loads(data.pop("tool_calls_json"))
            except json.JSONDecodeError:
                tool_calls = []
            messages.append(Message(tool_calls=tool_calls, **data))
        return messages

    def clear_messages_after(self, chat_id: str, message_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "DELETE FROM messages WHERE chat_id = ? AND id > ?",
                (chat_id, message_id),
            )
            connection.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?",
                (utc_now(), chat_id),
            )


def _demo(path: Path) -> dict[str, Any]:
    if any(os.path.lexists(path.with_name(path.name + suffix)) for suffix in ("-wal", "-shm", "-journal")):
        raise FileExistsError
    with path.open("xb"):
        pass
    store = ChatDatabase(path)
    primary = store.create_chat("fictional-model")
    store.add_message(primary.id, "user", "Sketch a sample report")
    calls = [{"function": {"name": "preview_note", "arguments": {"section": "summary"}}}]
    keep = store.add_message(primary.id, "assistant", "", tool_calls=calls)
    store.add_message(primary.id, "tool", '{"ok": true}', tool_name="preview_note")

    other = store.create_chat("fictional-model", "Independent conversation")
    store.add_message(other.id, "user", "Keep this example unchanged")
    before = [asdict(message) for message in store.list_messages(primary.id)]
    store.clear_messages_after(primary.id, keep)
    return {
        "chat": asdict(store.get_chat(primary.id)),
        "before_trim": before,
        "after_trim": [asdict(message) for message in store.list_messages(primary.id)],
        "other_chat": asdict(other),
        "other_messages": [asdict(message) for message in store.list_messages(other.id)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Write and inspect a fresh fictional conversation database")
    demo.add_argument("--database", required=True, type=Path, help="Path to a new database in an existing directory")
    args = parser.parse_args()
    try:
        result = _demo(args.database)
    except FileExistsError:
        parser.exit(2, "The database path or a SQLite sidecar already exists.\n")
    except (OSError, sqlite3.Error):
        parser.exit(2, "Could not create or use the demo database.\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
