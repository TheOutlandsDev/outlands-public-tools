# Run the Offline Game Server TCP Session Counter

Download the source ZIP and `SHA256SUMS.txt`. Compare the ZIP's SHA-256 with `Get-FileHash .\game-server-tcp-session-counter-0.1.0.zip -Algorithm SHA256` in PowerShell, or use `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the archive and open a terminal in that folder. The CLI uses Python's standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python game_tcp_sessions.py examples/selection.json examples/socket-table.json
```

Ubuntu

```sh
python3 game_tcp_sessions.py examples/selection.json examples/socket-table.json
```

The fictional inputs report three external sessions from two distinct peers, and one separately counted local session.

Provide a selection with `process_ids`, `configured_ports`, `listener_ports`, `exclude_local_peers`, and `local_addresses`. Use an empty list for a port category you don't have. The tool matches the union of configured and observed listener ports. When exclusion is enabled, it also treats `127.0.0.1` and `::1` as local and ignores IPv6 scope suffixes when comparing local addresses. With exclusion disabled, local sessions are included in the session count and the separate local counter is zero.

Provide a table with a `rows` list shaped like the example. A row needs the protocol, state, PID, local port, and remote address. Rows with unknown owner PID do not match. The Windows output of the [Offline Socket Table Parser](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/socket-table-parser) with `--include-connections` supplies these fields. Its Linux proc output leaves PIDs unknown. For Linux, use saved rows that include owner PIDs from your capture.

The output includes no addresses or process IDs. One peer can hold several sessions, and a session with an unknown remote address contributes no distinct peer. The report describes connections only. Each input is limited to 1 MiB of UTF-8 JSON. The CLI prints to stdout, leaves both files unchanged, and returns exit code 2 for invalid input.
