# Use Offline Windows Event Cursor Replay

Download the source ZIP and `SHA256SUMS.txt` from the [GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/windows-event-cursor-replay-v0.1.0). Compare the SHA-256 before extracting. On Windows, use PowerShell.

```powershell
Get-FileHash .\windows-event-cursor-replay-0.1.0.zip -Algorithm SHA256
Expand-Archive .\windows-event-cursor-replay-0.1.0.zip .\cursor-demo
Set-Location .\cursor-demo\windows-event-cursor-replay-0.1.0
python -B windows_event_cursor_replay.py --cursor examples/cursor.json --events examples/events.json --observed-at 2020-01-02T08:00:00Z
```

On Ubuntu, use a shell.

```sh
sha256sum -c SHA256SUMS.txt
unzip windows-event-cursor-replay-0.1.0.zip
cd windows-event-cursor-replay-0.1.0
python3 -B windows_event_cursor_replay.py --cursor examples/cursor.json --events examples/events.json --observed-at 2020-01-02T08:00:00Z
```

The example skips System record 101 and reports Application record 101 and System record 102 in `timestamp` order. The report includes the restored cutoff, the query start with its two-second overlap, the new event identities, and the next cursor. To replay another batch, save only the `next_cursor` object as a separate JSON file and pass that file as `--cursor`.

## Input and behavior

- Provide a saved event batch as a JSON array with up to 10,000 objects. Each needs a nonblank `channel` of at most 256 characters, a nonnegative integer `record_id` up to 2^63 − 1, and an ISO 8601 `timestamp` with a UTC offset. The batch should contain the records already returned by a collection. The CLI reports the historical query start and applies `timestamp` ordering and identity deduplication to the supplied batch.
- Provide a saved cursor object with `last_query` and an optional `seen` array of `channel` and `record_id` objects. A legacy `last_query` without an offset uses the observation time’s offset. Missing or invalid cursor state falls back to the bounded startup lookback. A cursor up to five minutes ahead is accepted. The history retains the most recent 5,000 keys.
- Set `--observed-at` explicitly. The `--startup-lookback-seconds` option defaults to 10 and clamps to 2–300 seconds. Output timestamps use UTC.
- Each input file has a 2,000,000-byte limit and accepts UTF-8 with an optional BOM. An invalid event batch or unreadable input reports an error on stderr and exits 2. A missing cursor is treated as startup. The CLI reads saved files and prints JSON to stdout using only the Python standard library.

The release validation records cover both original cursor tests with fictional data and seven copied-CLI check groups on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
