# Offline Assistant Operations Status Reporter

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. It uses only Python's standard library.

## Review a fictional snapshot

```
python assistant_operations_status.py compact --input examples/status.json
python assistant_operations_status.py markdown --input examples/status.json
```

The compact JSON keeps the service and endpoint health fields. It selects the original task and endpoint fields, leaving out the example descriptions and response body. The Markdown report lists processes, schedulers, services, listeners, endpoints, expected and actual state, and issues where available.

## Input and output

Supply a UTF-8 JSON file of at most 2,000,000 bytes. Pass either a snapshot object with a programs array or a success envelope with ok set to true and a result object containing that array. The programs array can be empty. Each program can include lists of process, task, service, and endpoint objects, a listener object with optional TCP and UDP arrays, a state object or null, and an issues array. Compact mode carries through process, service, listener, state, and issue evidence and selects task and endpoint fields.

The report goes to standard output. The CLI returns 0 on successful formatting and 2 on malformed or unreadable input. Reports retain evidence such as process IDs, service labels, and endpoint URLs. Review the content before sharing a report. The sample input is fictional.

The four qualification profiles run both original formatting tests and six copied-CLI check groups. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/assistant-operations-status-reporter-v0.1.0/VALIDATION.json).
