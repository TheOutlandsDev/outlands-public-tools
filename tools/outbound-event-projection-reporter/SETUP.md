# Run the Offline Outbound Event Projection Reporter

Download the source ZIP and SHA256SUMS.txt together. In the download folder, compare the output of Get-FileHash .\outbound-event-projection-reporter-0.1.0.zip -Algorithm SHA256 in PowerShell with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Use Python 3.12 or 3.15.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe outbound_event_projection.py examples/fictional-shipments.json
```

Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python outbound_event_projection.py examples/fictional-shipments.json
```

The example reports one new event with a lot count of two. The output keeps the original shipment field allowlist, including the order and revision identifiers and part number. Share output only where those retained fields may be shared.

Supply a JSON snapshot shaped like the example. Include the saved events, a run UUID, and a projection timestamp with a time zone. Put previously observed event identities in seen_event_ids. To exercise replay, copy the example and add its event_identity to seen_event_ids. A replay contributes to the replay count and produces no projected row. The CLI rejects a snapshot with 500 or more events, duplicate event identities, or ambiguous lot allocations in new events.

The CLI reports to stdout, leaves inputs unchanged, and uses no live database. Exit status is 0 for a report or 2 for invalid input. Qualification used Windows and Ubuntu x64, Python 3.12.16 and 3.15.2, and hash-pinned Pydantic 2.14.3.
