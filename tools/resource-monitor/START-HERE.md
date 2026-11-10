# Download to a first dashboard

**Resource Monitor 0.1.2 · Python 3.12 through 3.15 · Windows / Linux.**
The fictional demo needs **no pip packages, account, model or live data**.
Python itself is installed separately. This source ZIP includes no runtime,
real machine metrics, private history or capability token.

1. Download the ZIP and `SHA256SUMS.txt` from the same release. Compare the ZIP
   SHA-256 with PowerShell `Get-FileHash ZIP_PATH -Algorithm SHA256` or Linux
   `sha256sum ZIP_PATH`. Extract the complete ZIP into a new local folder.
2. Install Python **3.12 through 3.15** from <https://www.python.org/downloads/> if
   needed, and reopen your terminal. Open it in the extracted application folder.
3. On Windows run `start-demo.cmd --check`, then `start-demo.cmd`.
   On Linux run `sh start-demo.sh --check`, then `sh start-demo.sh`.
   Alternatively: `python -B launch.py --check`, then `python -B launch.py`.
4. Open the **complete local URL** printed by the server, including its fragment.
   The dashboard says **FICTIONAL DEMO**. It is not reading your computer.
   A missing first CPU/rate value is warm-up, not a valid zero.
5. Wait for several samples. Pause display, resume, and use JSON or CSV export
   if you want a private copy. Pause stops display polling, not server sampling.
   The API export contains bounded server history, which may include new samples.
6. Stop with Ctrl+C. Restart with the same launcher and use the **new** printed
   URL: the old token is invalid. History is intentionally memory-only. It is
   empty/new after restart, while explicitly downloaded exports remain your files.

For a bounded demonstration that stops itself:

```text
python -B launch.py --interval .2 --history 120 --duration 120
```

The launcher never installs dependencies, opens a browser, reads live metrics,
creates a startup task or automatically saves history. A free random loopback
port is chosen. It accepts the documented `serve` options; do not add `--live`.

## Optional live mode

Live mode uses separately installed `psutil==7.2.2`. Its hash-pinned binary
requirements cover Windows x64 and Ubuntu x86_64 regular CPython 3.12–3.15.
From the extracted app directory, create a fresh user-owned venv outside the
app. Activation, administrator rights, policy changes and cloud login are not
needed. Managed application controls can still prohibit execution.

Windows PowerShell (choose another fresh path if this already exists):

```powershell
$liveEnv = Join-Path $env:LOCALAPPDATA 'OutlandsResourceMonitorLive012'
python -m venv "$liveEnv"
& "$liveEnv\Scripts\python.exe" -m pip install --require-hashes --only-binary=:all: -r requirements-live.txt
& "$liveEnv\Scripts\python.exe" -B -m resource_monitor sample --live --count 3 --interval .2
& "$liveEnv\Scripts\python.exe" -B -m resource_monitor serve --live --port 0 --duration 30
```

Ubuntu (supply Python with `venv`/`ensurepip` available):

```sh
live_env="$HOME/.local/share/outlands-resource-monitor-live-012"
python3 -m venv "$live_env"
"$live_env/bin/python" -m pip install --require-hashes --only-binary=:all: -r requirements-live.txt
"$live_env/bin/python" -B -m resource_monitor sample --live --count 3 --interval .2
"$live_env/bin/python" -B -m resource_monitor serve --live --port 0 --duration 30
```

Only explicit `--live` commands collect native aggregate readings. First CPU
and network-rate values are warm-up gaps. The server uses loopback only; it
starts no service, firewall rule or startup task. Keep readings, timestamps,
exports and full capability URLs private. The demo launchers cannot enable live.

To choose a particular Python, invoke it directly or set the process-local
`RESOURCE_MONITOR_PYTHON` path before using a wrapper. Windows checks `python`
on PATH, then `py` 3.15 down to 3.12; Ubuntu checks `python3` on PATH, then
versioned candidates. `--check` prints the selected Python series. Qualification
uses the explicit override to prevent accidentally testing another interpreter.

The attached VALIDATION.json records separate fresh demo/live environments and
actual patch versions for all eight lanes. SHA256SUMS.txt covers the ZIP, this
guide, that receipt and release-matrix.json. See the
[qualification method](docs/PYTHON315.md) for checks and limits.

## Failure and recovery

- Missing/wrong Python: install a supported version, reopen terminal, run check.
- Missing files: extract a new complete ZIP; do not merge old/new app folders.
- Disconnected after restart: open the new printed token URL. Do not reuse the old one.
- Lost unsaved history: intentional; export explicitly before stopping if needed.
- Existing CLI export path: choose a new absolute private file; it is never overwritten.

See [the actual download check](docs/DOWNLOAD-CHECK.md),
[API and export formats](docs/API.md), [validation boundaries](docs/VALIDATION.md),
and [design/provenance](docs/PROVENANCE.md). Interface export/pause acceptance
is separate from HTTP/CLI checks; no browser check is implied by a server starting.
