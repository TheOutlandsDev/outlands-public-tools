# Offline Lot-Start Reservation Cancellation Preview

Preview a proposed cancellation using a saved reservation and a reason. The CLI reads two local JSON files and prints a report to stdout. It makes no database, MES, or network calls.

## Setup

Use Windows x64 or Ubuntu x64 with CPython 3.12.16 or 3.15.2. Verify the source ZIP against the published SHA-256 checksum and extract it. From the extracted directory, create an environment and install the hash-pinned dependencies.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe lot_reservation_cancellation.py examples/reservation.json examples/cancellation.json
```

Ubuntu

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python lot_reservation_cancellation.py examples/reservation.json examples/cancellation.json
```

## Input and results

- The saved reservation declares a UUID, source request key, request status, optional cancellation reason, and up to 100 lot records. Each lot has a unique identity and sequence position.
- The cancellation file contains one `reason` field. The reason must have 8–500 characters after trimming.
- The fictional example projects a `RESERVED` request to `CANCELLED`, lists two retained lot IDs in sequence, and proposes one `CANCELLED` audit event. Keep the IDs in the observed-ID input to any later lot proposal.
- To preview a replay, save the report's `reservation` object as a separate JSON file and run the CLI with that file. It returns the existing cancellation reason and a null audit event.
- Invalid input or a disallowed state exits with code 2 and prints a brief diagnostic to stderr. Each input is limited to 1 MiB. The report echoes supplied reservation IDs and the reason.

The [release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-reservation-cancellation-preview-v0.1.0) includes validation records for the exact source ZIP.
