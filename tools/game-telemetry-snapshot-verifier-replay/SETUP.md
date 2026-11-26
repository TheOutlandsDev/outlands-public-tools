# Run the Offline Game Telemetry Snapshot Verifier and Replay Tool

Download the source ZIP and `SHA256SUMS.txt`. Compare the ZIP's SHA-256 using `Get-FileHash .\game-telemetry-snapshot-verifier-replay-0.1.0.zip -Algorithm SHA256` in PowerShell or `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal there. The CLI uses Python's standard library. Qualification covered Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python telemetry_snapshot_replay.py verify examples/dayz.json
python telemetry_snapshot_replay.py replay examples/modern_warfare.json
```

Ubuntu

```sh
python3 telemetry_snapshot_replay.py verify examples/dayz.json
python3 telemetry_snapshot_replay.py replay examples/modern_warfare.json
```

## Snapshot contract

Supply an already sanitized UTF-8 JSON object with schema version 1, a supported program, a records array, and a `snapshot_sha256`. The SHA-256 covers compact, sorted-key, UTF-8 JSON for every field except the digest itself. It checks the recorded bytes under that canonicalization. Use a checksum obtained independently when you need to establish provenance.

The verifier keeps the original checks for banned raw record fields, pseudonymous actor and target values, and recognizable address, identifier, or secret patterns. Use fictional or previously sanitized input. Those pattern checks cover record fields according to the original contract. They do not redact the snapshot or verify the privacy of arbitrary metadata.

## Replay results

The example replays the saved records into a normalization report, descriptive actor statistics, and a training manifest. The manifest's `ready_for_training` flag reflects the original minimum record count. Review the other checks listed in `next_gates` separately. The tool starts no training, uses no model, GPU, or network, and leaves the input untouched.

Replay hashes the normalized events and actor features using the original canonical JSON rules. The CLI omits processing timestamps in the three reports so identical inputs give identical output. Input is limited to 2,000,000 bytes and 10,000 records. Errors return exit code 2.
