# Use the Offline TOML Game Install Profile Checker

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-install-profile-checker-v0.1.0).
Compare the calculated ZIP hash with its entry in `SHA256SUMS.txt` before
extracting into a fresh directory.

PowerShell

```powershell
Get-FileHash .\game-install-profile-checker-0.1.0.zip -Algorithm SHA256
Expand-Archive .\game-install-profile-checker-0.1.0.zip .\profile-demo
Set-Location .\profile-demo\game-install-profile-checker-0.1.0
```

Ubuntu shell

```sh
sha256sum game-install-profile-checker-0.1.0.zip
unzip game-install-profile-checker-0.1.0.zip -d profile-demo
cd profile-demo/game-install-profile-checker-0.1.0
```

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
if that is the name of your interpreter.

## Try the fictional installation

PowerShell

```powershell
$demo = Join-Path (Split-Path -Parent (Get-Location).Path) 'fictional-game-install'
python -B examples/create_sample.py "$demo"
python -B -m opskit --home "$demo" game list
python -B -m opskit --home "$demo" game check --all
python -B -m opskit --home "$demo" game check demo --json
```

Ubuntu shell

```sh
demo="$(dirname "$PWD")/fictional-game-install"
python -B examples/create_sample.py "$demo"
python -B -m opskit --home "$demo" game list
python -B -m opskit --home "$demo" game check --all
python -B -m opskit --home "$demo" game check demo --json
```

The generator creates a fresh example with one profile named `demo`.
The list shows its game and engine. The check verifies the declared paths
and prints a passing result. The example executable is a text fixture.

## Supply a profile

Pass your installation root explicitly with `--home`. The checker reads
`config/game-profiles/*.toml` beneath that root by default. Use
`game list --profiles-dir DIR` or `game check --profiles-dir DIR` to
select another profile directory beneath the same root.

```toml
name = "demo"
game = "Demo Server"
engine = "standalone"
enabled = true
platform = "any"
install_dir = "servers/demo"
executable = "server.bin"
required_files = ["required.txt"]
save_paths = ["saves"]
ports = [27015]
expect_running = false
```

An installation directory is relative to the selected root. The executable,
required files, and save paths are relative to that installation directory.
Use `standalone`, `steamcmd`, or `spt` for the engine and `any`, `windows`,
or `linux` for the platform. Use unique integer port numbers from 1 through
65535.

The checker reports missing executables and required files for enabled
profiles that apply on the host. It reports missing save paths as warnings.
Disabled profiles and profiles targeting another platform may be skipped.
Invalid declarations and paths that escape the selected root are rejected.
Paths through symlinks or Windows junctions are rejected.

Port checks validate the saved declarations. If a profile requests a running
check, the report marks it as skipped because this CLI checks saved profiles
and files. The checker prints its result and leaves the installation tree
untouched.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes fresh-extraction validation records for Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
