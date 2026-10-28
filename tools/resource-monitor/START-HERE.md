# Download to a first dashboard

**Resource Monitor 0.1.1 · Python 3.12 or 3.13 · Windows / Linux.**
The fictional demo needs **no pip packages, account, model or live data**.
Python itself is installed separately. This source ZIP includes no runtime,
real machine metrics, private history or capability token.

1. Download the ZIP and `SHA256SUMS.txt` from the same release. Compare the ZIP
   SHA-256 with PowerShell `Get-FileHash ZIP_PATH -Algorithm SHA256` or Linux
   `sha256sum ZIP_PATH`. Extract the complete ZIP into a new local folder.
2. Install Python **3.12 or 3.13** from <https://www.python.org/downloads/> if
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

Follow [the separate virtual-environment instructions](README.md#read-live-aggregate-metrics)
to install pinned `psutil==7.2.1`. Then explicitly use the documented
`python -m resource_monitor serve --live --port 0` command. Live metrics and
timestamps are private operational data. Do not publish exports or token URLs.

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
