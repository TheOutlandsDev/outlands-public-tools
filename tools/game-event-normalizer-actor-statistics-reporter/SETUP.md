# Run the Offline Game Event Normalizer and Actor Statistics Reporter

Download the source ZIP and `SHA256SUMS.txt`. Compare the ZIP's SHA-256 with `Get-FileHash .\game-event-normalizer-actor-statistics-reporter-0.1.0.zip -Algorithm SHA256` in PowerShell, or run `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal there. The CLI uses the standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python game_event_statistics.py normalize fika examples/events.json
python game_event_statistics.py statistics iw4x examples/match.json
```

Ubuntu

```sh
python3 game_event_statistics.py normalize fika examples/events.json
python3 game_event_statistics.py statistics iw4x examples/match.json
```

The first example produces `kill`, `extract`, and `other` events. The second reports actor-scoped kills, deaths, assists, and damage along with session and event totals.

Supply a local JSON object with a `records` array of up to 10,000 event objects. The input is limited to 2,000,000 bytes. Supported profile IDs are `rust`, `dayz`, `main_spt`, `modern_warfare`, and `zomboid`. The last three also accept aliases such as `fika`, `iw4x`, and `pz`. The tool reads only the supplied JSON, calculates descriptive statistics, and prints a report to stdout. Invalid inputs return exit code 2.

Use fictional or already sanitized data. Normalization omits raw message fields while retaining supplied labels such as actor, target, session, and event names. The job ID and result SHA-256 use the original canonical JSON hashing rules. CLI reports omit the processing timestamp so repeated runs on the same input produce identical output.
