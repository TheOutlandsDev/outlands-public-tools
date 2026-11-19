# Use the Offline Game Server Status Response Parser

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-server-status-response-parser-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\game-server-status-response-parser-0.1.0.zip -Algorithm SHA256
Expand-Archive .\game-server-status-response-parser-0.1.0.zip .\status-demo
Set-Location .\status-demo\game-server-status-response-parser-0.1.0
```

On Ubuntu, run

```bash
sha256sum game-server-status-response-parser-0.1.0.zip
unzip game-server-status-response-parser-0.1.0.zip -d status-demo
cd status-demo/game-server-status-response-parser-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` if needed.

## Read the fictional responses

Run the Quake 3 preview directly from the extracted directory.

```text
python -B -m game_server_status --format quake3-status --input examples/quake3-status.txt
```

The report shows the Fictional Quake Server, map `fictional_courtyard`,
2 players, and capacity 18. The `bots` value is null.

The A2S_INFO example is stored as hex text. Decode it to a new file
before passing the binary response to the parser.

```text
python -B -c "from pathlib import Path; data=bytes.fromhex(Path('examples/a2s-info.hex').read_text(encoding='ascii')); out=open('a2s-example.bin','xb'); out.write(data); out.close()"
python -B -m game_server_status --format a2s-info --input a2s-example.bin
```

The example reports the Fictional A2S Server, map `fictional_station`,
4 players, capacity 20, and 2 bots.

## Read your own saved file

Select the matching `--format` and supply a regular file up to 64 KiB.
Use the saved binary bytes for A2S_INFO. A Quake 3 file may include the
original response prefix or start with the text header `statusResponse`.

Both formats report `server_name`, `map`, `players`, `max_players`, and
`bots`. A2S_INFO also reports `protocol`, `folder`, `game`, and `app_id`.
Quake 3 counts nonempty player rows and returns null for missing or invalid
capacity. Player rows are represented by the aggregate player count.
Server and map labels come from the input. Use fictional files when
sharing examples publicly.

A successful parse prints JSON to stdout and returns exit status 0.
Invalid arguments, an unreadable or oversized file, an invalid header,
or truncated A2S fields return exit status 2 with a diagnostic on stderr.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh source extraction and copied CLI checks
on Windows and Ubuntu with Python 3.12.16 and 3.15.2.
