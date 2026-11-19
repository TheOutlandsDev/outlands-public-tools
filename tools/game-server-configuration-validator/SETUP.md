# Use the Offline Game Server Configuration Validator

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-server-configuration-validator-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\game-server-configuration-validator-0.1.0.zip -Algorithm SHA256
Expand-Archive .\game-server-configuration-validator-0.1.0.zip .\config-demo
Set-Location .\config-demo\game-server-configuration-validator-0.1.0
```

On Ubuntu, run

```bash
sha256sum game-server-configuration-validator-0.1.0.zip
unzip game-server-configuration-validator-0.1.0.zip -d config-demo
cd config-demo/game-server-configuration-validator-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` if needed.

## Check the fictional configuration

```text
python -B -m game_server_config --input examples/server-config.json
```

The example prints `"status": "valid"` and `"server_count": 4`. Its
declarations exercise each of the four supported probe types.

## Check your own saved declarations

Use a UTF-8 JSON object up to 4 MiB with integer `schema_version` set
to `1` and a `servers` array. A UTF-8 BOM is accepted. Keys must be
unique and JSON numbers must be finite.

| Server field | Meaning |
| --- | --- |
| `id` | Required nonempty unique text identifier |
| `root` | Required absolute Windows or POSIX path |
| `expected_state` | `online` or `planned_off`, defaulting to `online` |
| `health_urls` | Optional array of HTTP or HTTPS URLs on `127.0.0.1`, `localhost`, or `[::1]` |
| `player_probe` | Optional declaration with type `a2s`, `quake3`, `tcp_sessions`, or `jsonl_population` |

Keep credentials out of health URLs. For an IPv6 health URL, enclose
`::1` in square brackets. For an IPv6 probe host, use the plain `::1`
string. Protocol probes accept the same loopback hosts and ports from
1 through 65535. If a probe host is omitted, it defaults to
`127.0.0.1`. A `jsonl_population` probe instead needs an absolute
`path`. The validator checks path syntax and reads only the selected
configuration. Validation covers the saved declarations.

Valid input returns exit status 0 and prints a server count to stdout.
Invalid input or arguments return exit status 2 with a diagnostic on
stderr. Diagnostics omit supplied URLs, credentials, hosts, and paths.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh extraction and CLI checks on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
