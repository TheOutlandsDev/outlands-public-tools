# Use the Offline Socket Table Parser

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/socket-table-parser-v0.1.0).
Compare the calculated ZIP hash with its entry in `SHA256SUMS.txt` before
extracting into a fresh directory.

PowerShell

```powershell
Get-FileHash .\socket-table-parser-0.1.0.zip -Algorithm SHA256
Expand-Archive .\socket-table-parser-0.1.0.zip .\socket-table-demo
Set-Location .\socket-table-demo\socket-table-parser-0.1.0
```

Ubuntu shell

```sh
sha256sum socket-table-parser-0.1.0.zip
unzip socket-table-parser-0.1.0.zip -d socket-table-demo
cd socket-table-demo/socket-table-parser-0.1.0
```

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
if that is the name of your interpreter.

## Try the fictional tables

```text
python -B -m opskit ports --format windows-netstat --input examples/windows-netstat.txt
python -B -m opskit ports --format linux-tcp6 --input examples/linux-tcp6.txt --include-connections
python -B -m opskit ports --format linux-udp --input examples/linux-udp.txt
```

The Windows example shows TCP listeners and UDP rows. The Linux TCP example
includes an IPv6 listener, an established connection, and a malformed line
that the parser skips. All examples work on both platforms.

## Parse a saved table

Select one file with `--input` and identify its format with `--format`.

| Format | Input text |
| --- | --- |
| `windows-netstat` | Saved Windows netstat table with numeric endpoint and PID columns |
| `linux-tcp`, `linux-tcp6` | Saved Linux x64 TCP or TCP6 table |
| `linux-udp`, `linux-udp6` | Saved Linux x64 UDP or UDP6 table |

The input limit is 4 MiB. The CLI accepts UTF-8, optionally with a byte order
mark, and UTF-16 with a byte order mark. Each JSON row contains the protocol,
local address and port, remote address and port, socket state, and PID.
Windows records carry the PID from the saved table. Linux records use
`null` for the PID.

The default result contains TCP listeners and UDP rows. Add
`--include-connections` to include other TCP states and show remote endpoints.
The remote fields are `null` by default. Malformed rows are skipped, so the
result can still contain valid records from the rest of the table.

Exit status `0` means the file was parsed. A table with no matching records
produces an empty JSON `rows` array. Exit status `2` means the input or command
could not be read or accepted.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes fresh-extraction validation records for Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
