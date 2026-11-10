# Safe File Mover 0.2.1

A journaled file mover with SHA-256 verification, no-replace destination commits,
interrupted-operation recovery and retained original content by default. This
standalone wheel supports Python `>=3.12.7,<3.16` on Windows and Ubuntu. It has no
third-party Python runtime dependencies. Supply Python separately.

## Download and verify

Download `safe_file_mover-0.2.1-py3-none-any.whl` and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/safe-file-mover-v0.2.1).
The release also includes this guide and a machine-readable validation summary.
Checksums establish matching bytes, not independent publisher identity. The sums
file covers every other attached asset. Check the exact wheel filename/digest.

Windows PowerShell, from the download directory:

```powershell
Get-FileHash -Algorithm SHA256 .\safe_file_mover-0.2.1-py3-none-any.whl
Get-Content .\SHA256SUMS.txt
```

Ubuntu, from a directory containing only the downloaded release assets:

```sh
sha256sum --check SHA256SUMS.txt
```

## Install without activation

Use an existing Python 3.12.7 or later in the 3.12–3.15 series. Check
`python --version` first (`python3 --version` on Ubuntu). Use a fresh directory
you own with a trusted local parent. An ordinary account can create a venv there;
managed application controls may still prohibit execution. These commands require
no administrator session, policy changes, cloud account or model login.

Windows PowerShell:

```powershell
python -m venv .mover-venv
.\.mover-venv\Scripts\python.exe -m pip install --no-index --no-deps .\safe_file_mover-0.2.1-py3-none-any.whl
.\.mover-venv\Scripts\safe-move.exe --help
```

Ubuntu (the separately supplied Python must have `venv`/`ensurepip` available):

```sh
python3 -m venv .mover-venv
.mover-venv/bin/python -m pip install --no-index --no-deps ./safe_file_mover-0.2.1-py3-none-any.whl
.mover-venv/bin/safe-move --help
```

Activation is unnecessary, including when PowerShell script execution is
restricted. You can also invoke the installed venv interpreter with
`-m safe_file_mover`. The wheel contains Python source and the MIT notice; no
interpreter, installer, journal, recovery copy, third-party binary or user data.

## First use: fictional local data

Start with disposable files and an independent backup of anything important.
Keep the private journal outside the source tree being moved. Use the same state
directory for all commands referring to an operation. Output includes paths and
history; keep it private.

Windows PowerShell, from your trusted private scratch directory:

```powershell
# Fails if the example directory already exists. Do not substitute real data yet.
New-Item -ItemType Directory -Path .\mover-example -ErrorAction Stop | Out-Null
$example = (Resolve-Path .\mover-example).Path
New-Item -ItemType Directory -Path "$example\destination" | Out-Null
Set-Content -LiteralPath "$example\fictional.txt" -Value 'Fictional sample only'
$mover = (Resolve-Path .\.mover-venv\Scripts\safe-move.exe).Path
& $mover --state-dir "$example\state" plan "$example\fictional.txt" "$example\destination"
# Review the plan before running the next command.
& $mover --state-dir "$example\state" move "$example\fictional.txt" "$example\destination"
& $mover --state-dir "$example\state" list
```

Ubuntu, from your trusted private scratch directory:

```sh
example="$(mktemp -d "$PWD/mover-example.XXXXXX")"
mkdir "$example/destination"
printf '%s\n' 'Fictional sample only' > "$example/fictional.txt"
mover="$PWD/.mover-venv/bin/safe-move"
"$mover" --state-dir "$example/state" plan "$example/fictional.txt" "$example/destination"
# Review the plan before running the next command.
"$mover" --state-dir "$example/state" move "$example/fictional.txt" "$example/destination"
"$mover" --state-dir "$example/state" list
```

`plan` reads/hashes the source; it creates no state and moves no data. It is not a
snapshot or reservation. `move` copies to staging, verifies content, commits
without overwriting and renames the original to a managed retained recovery path.
The printed operation ID and state directory identify the transaction.

## Recovery, restore and deliberate deletion

Append these subcommands to the same executable and `--state-dir` prefix above;
replace `OPERATION_ID` with the ID from `list`:

| Subcommand | Behavior |
| --- | --- |
| `history OPERATION_ID` | Inspect the operation's journal events. |
| `recover --id OPERATION_ID` | Resume an interrupted operation where verification permits. |
| `recover --all` | Attempt pending operations; inspect every resulting status. |
| `restore OPERATION_ID` | Return verified retained content to its original path; keep the destination. |
| `abandon OPERATION_ID` | Discard uncommitted managed staging after source verification. |
| `purge OPERATION_ID` | Permanently delete the retained recovery copy after re-verification. |

Do not purge until you have independently reviewed both copies and your backup.
Do not manually rename/delete a managed recovery path or journal to suppress a
refusal. Destination mutation, corrupt retained content, unexpected links or
unsafe state can stop the operation and leave evidence for review. Purge checks
the destination again at the final deletion boundary; a matching hash does not
prove storage durability. `move --delete-recovery-copy` explicitly requests
automatic deletion locally; retaining recovery content is the default. Remote
automatic deletion is refused; later remote purge requires
`--acknowledge-remote-risk`, which does not establish server-side persistence.

## Qualification and limits

The release's `VALIDATION.json` records actual installed-wheel results and its
wheel digest. The repository's
[qualification workflow](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/.github/workflows/file-mover-checks.yml)
builds a text-only allowlist, checks reproducible bytes, creates fresh venvs,
installs without dependency/index access, confirms imports come from the venv,
then runs all 116 engine/CLI safeguard methods plus five installed-console tests
on Windows and Ubuntu with Python 3.12, 3.13, 3.14 and 3.15.2. Native Windows
link/junction and named-stream checks are required. Opposite-platform cases are
reported as skips, never passes. See the exact result, not workflow presence.

This is experimental software. Tests use generated disposable local files.
GUI/Tk, live SMB, arbitrary POSIX network mounts, employer deployment, hostile
concurrent ancestor replacement, hardware failure and power-loss durability are
not qualified. Stable trusted parents/state and quiescent data are required.
The mover is not an application-consistent backup or sandbox. Do not move live
databases or service state. ACLs, ownership, hard-link topology and sparse layout
are not fully preserved across volumes. Unsupported special/reparse types,
nested mount boundaries and detected POSIX extended attributes are refused.
Windows state inherits parent ACLs; no ACL confidentiality audit is supplied.
The optional GUI source is included but requires separately supplied Tk/Tcl.

## License and provenance

MIT, copyright 2026 TheOutlandsDev; the full notice is included in the wheel.
The public mover adapts owner-confirmed personally authored source with
AI-assisted corrections, tests and documentation. Private originals, operational
data, source Git history and logs are excluded. No required notice was removed.
Python, SQLite, OS APIs and optional Tk/Tcl retain their own terms.
