# Offline Assistant Conversation History Store

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. The tool uses Python's standard library.

## Walk through a fictional conversation

Run this command once with an unused path in an existing directory.

```
python assistant_conversation_store.py demo --database sample-history.sqlite3
```

The command creates a SQLite database and prints a JSON report. The first conversation starts with user, assistant, and tool messages. The assistant message includes a structured tool-call record. The demo trims the first conversation after the assistant message and shows that a second conversation still has its own message. The CLI refuses to reuse an existing database or SQLite sidecar path. Pick a fresh file for another run.

## Use the Python API

```
from pathlib import Path
from assistant_conversation_store import ChatDatabase

store = ChatDatabase(Path("my-history.sqlite3"))
chat = store.create_chat("fictional-model")
store.add_message(chat.id, "user", "Sketch a sample report")
print(store.get_chat(chat.id).title)
for message in store.list_messages(chat.id):
    print(message.role, message.content)
```

Pass a database path explicitly. Opening a store initializes its SQLite schema and enables write-ahead logging. The API also supports title search, rename, deletion, and trimming by message ID. Deleting a conversation removes its messages. Message text and tool-call arguments are stored in the database, so keep real history files private.

The saved model and tool names are data values. The demo produces its report locally. Release qualification uses the original round-trip test and six command-line check groups in disposable databases. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/assistant-conversation-history-store-v0.1.0/VALIDATION.json).
