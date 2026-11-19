# Use the Offline Process and Listener Evidence Checker

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/process-listener-evidence-v0.1.0).
Calculate the ZIP's SHA-256 and compare it with the corresponding entry in
`SHA256SUMS.txt` before extracting.

PowerShell

```powershell
Get-FileHash .\process-listener-evidence-0.1.0.zip -Algorithm SHA256
Expand-Archive .\process-listener-evidence-0.1.0.zip .\process-evidence-demo
Set-Location .\process-evidence-demo\process-listener-evidence-0.1.0
```

Ubuntu shell

```sh
sha256sum process-listener-evidence-0.1.0.zip
unzip process-listener-evidence-0.1.0.zip -d process-evidence-demo
cd process-evidence-demo/process-listener-evidence-0.1.0
```

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
for `python` if that is the name of your interpreter.

## Run the fictional examples

```text
python -B -m process_listener_evidence --input examples/proven-windows.json
python -B -m process_listener_evidence --input examples/unavailable-posix.json
```

The first example reports `proven`. One process matches the Windows
release directory and owns both specified listeners. The second reports
`unavailable` because the named process has no saved executable path.
The evidence files are the same on Windows and Ubuntu.

## Supply your own saved evidence

The input is a UTF-8 JSON object with the following fields.

| Field | Records |
| --- | --- |
| `identity` | An object with `mode` set to `exact` or `rooted`, a process `name`, an absolute `path`, and `path_style` set to `windows` or `posix` |
| `processes` | Objects with `pid` and `name`. Optional fields are `ppid` and `created_utc`. Use `null` or omit `executable` when its value is unavailable. |
| `expected_listeners` | Objects with `protocol` and `port` for all listeners the process is expected to own |
| `listener_owners` | Objects with `protocol`, `port`, and a `pids` array of the observed owners |

Use `tcp` or `udp` and an integer port from 1 through 65535. An owner
record contains all observed PIDs for its protocol and port. Collect
the process and listener observations together so PID comparisons make
sense for a single point in time.

Input is limited to 4 MiB, with up to 10,000 records per array and
100,000 owner PIDs in total. Reject duplicate process IDs and repeat
records for the same protocol and port within a listener array.

The checker compares process names without regard to case. In `exact`
mode it compares the saved executable with the expected path. In
`rooted` mode it checks the path against the expected release directory
using path components. Windows paths compare without regard to case.
POSIX paths compare case-sensitively. Use an absolute POSIX path or an
absolute Windows drive or UNC path. Path comparisons operate on saved
text using the declared path style.

## Read the result

| Exit code | Result |
| --- | --- |
| `0` | `proven`. Exactly one process matches, and every required listener is recorded with that process as its owner. |
| `1` | `failed` or `unavailable`. A match or ownership check failed, or a named process lacks the path evidence needed for a match. |
| `2` | Invalid input. The CLI prints a generic diagnostic to stderr. |

For valid input, the JSON report contains an overall `status`, the
identity's `state`, `pids`, and `created_utc`, and a `listener_state`.
Multiple executable matches fail the identity check. Missing ownership,
an empty expected list, and an unexpected owner fail the listener check.
The result describes the supplied records at the time they were collected.
The CLI reads the saved input and prints its result to stdout.

## Check the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes fresh-extraction validation records for Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
