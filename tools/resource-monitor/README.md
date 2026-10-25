# OUTLANDS | Resource Monitor

A local dashboard for CPU utilization, memory usage and aggregate network byte
counters. The application pairs an original Python HTTP API with an original
HTML/CSS/JavaScript interface. History is bounded in memory; exports happen only
when you request them. It captures no packets, addresses, process names or
command lines, and performs no external reputation lookup or outbound request.

Original client/server source, tests, documentation and fictional examples are
[MIT licensed](LICENSE). The separately installed Python runtime and optional
psutil live sampler retain their own terms; psutil's BSD 3-Clause notice is
retained in [third-party notices](THIRD-PARTY-NOTICES.txt).

This is a **fresh implementation** of a generic resource dashboard. The earlier
local monitoring drafts remain private with their unresolved provenance holds.
None of that implementation, its packet logic, credentials or collected records
is included or relicensed. See [provenance](docs/PROVENANCE.md).

## Try it without reading machine metrics

Use Python **3.12 or 3.13**, open a terminal in `tools/resource-monitor`, and run:

```text
python -m resource_monitor --help
python -m resource_monitor demo
python -m resource_monitor serve --demo --port 0
```

The first command displays help. The second prints deterministic fictional
samples without importing psutil, opening a socket or writing files. The third
explicitly starts a loopback server with fictional data. Open the complete local
URL printed by that server. It uses a random port when `--port 0` is selected.
The URL's fragment contains a new capability token for that server instance.

The dashboard visibly labels **FICTIONAL DEMO**. It is not measuring your
computer in this mode. CPU starts with a warm-up gap, and network rates require
two samples. Ctrl+C stops the server. A bounded demo is useful for a walkthrough:

```text
python -m resource_monitor serve --demo --port 0 --interval .2 --history 120 --duration 120
```

No arguments, help and the stdout demo initialize no sampler or HTTP listener.
The program does not install packages, open a browser or enable a startup task.

## Read live aggregate metrics

Live mode requires the separately installed **psutil 7.2.1** dependency. Its
implementation is not bundled. From the tool folder, use a virtual environment
in an existing private workspace outside this repository. Replace the fictional
workspace below with your own before running the commands.

PowerShell:

```powershell
$privateWork = 'D:\Private\OutlandsWork'
python -m venv "$privateWork\monitor-env"
& "$privateWork\monitor-env\Scripts\python.exe" -m pip install -r requirements-live.txt
& "$privateWork\monitor-env\Scripts\python.exe" -m resource_monitor serve --live --port 0
```

POSIX shell:

```sh
private_work='/absolute/private/workspace'
python3 -m venv "$private_work/monitor-env"
"$private_work/monitor-env/bin/python" -m pip install -r requirements-live.txt
"$private_work/monitor-env/bin/python" -m resource_monitor serve --live --port 0
```

The program remains a local source application; run module commands from this
folder. The dependency installation is a manual setup action. Once available,
live mode reads only aggregate CPU percentage, RAM counters/percentage, and
aggregate sent/received network byte counters through psutil.

For a short CLI sequence with no server:

```text
python -m resource_monitor sample --live --count 3 --interval .2
python -m resource_monitor sample --live --count 3 --interval .2 --format csv
```

The first CPU reading is deliberately unavailable. Rates use differences
between valid counters and **monotonic** sample time. Missing readings remain
`null`; a reset counter creates a rate gap and a fresh baseline. A sampler error
is explicitly reported rather than presenting old readings as a fresh success.

Network totals can include virtual adapters, loopback activity and this
dashboard's own local requests. Interface changes can reset or jump aggregate
counters. These are system counter estimates, not a measurement of Internet
speed, a billing total, packet contents or a threat-detection result. CPU and
memory semantics also depend on the operating system and psutil.

## Dashboard controls

- **Pause view** stops polling in this browser tab. The server continues sampling
  within its bounded in-memory history. **Resume view** requests current history.
- **Export JSON** and **Download CSV** explicitly download the server's current
  retained history. A paused display is not a frozen server export. Your browser
  controls the destination and filename handling.
- The mode badge distinguishes fictional data from live metrics. Charts show
  the latest 60 samples; missing readings create gaps rather than false zeros.
- If the server goes away, previous readings remain visibly stale. The browser
  retries while the view is active. A missing/expired token opens reconnect help.

The browser reads the fragment token into memory and removes the fragment from
the address bar. It uses no cookies, localStorage or sessionStorage. Reloading
the cleaned URL requires opening the full current server URL again or entering
its token in the reconnect form. A restarted server has a different token.

## Bounds and HTTP interface

| Setting | Supported behavior |
| --- | --- |
| Python | 3.12/3.13; standard library plus optional pinned psutil for live mode. |
| `--port` | 0–65,535; default 8,765. Listener is always `127.0.0.1`. Port 0 chooses an available port. |
| `--interval` | Finite 0.2–60 seconds; default 1. |
| `--history` | 1–600 retained samples; default 120. No database or automatic history file. |
| `--duration` | Optional finite server lifetime of 0.2–3,600 seconds. Without it, stop with Ctrl+C. |
| `sample --count` | 1–300; the selected sample sequence may span at most one hour. |
| HTTP | Read-only API, exact Host/Origin checks, capability header, no CORS grant or redirects. Static files have an exact allowlist. |
| Request bounds | Target at most 2,048 characters; header budget 8 KiB; at most 16 concurrent handlers; socket operation timeout 2 seconds. This is not a hard total-request deadline. |
| Exports | At most 1 MiB, strict JSON or CSV. Browser export requires the current token. |

The API is documented with response examples in [API.md](docs/API.md). The
server closes active connections and stops its sampler during normal shutdown;
tests exercise a partially sent request as well. There is no API to stop other
programs, change system settings, capture packets, run commands or shut down the
computer. Treat the local server, source files and computer as trusted.

## Explicit CLI exports and privacy

CLI output goes to stdout by default. To save an export, explicitly provide a
new file in an existing private directory outside the repository:

```text
python -m resource_monitor sample --live --count 3 --interval .2 --output ABSOLUTE_NEW_PRIVATE_REPORT_JSON
python -m resource_monitor sample --live --count 3 --interval .2 --format csv --output ABSOLUTE_NEW_PRIVATE_REPORT_CSV
```

Replace each uppercase placeholder with an absolute private filename. Relative
output paths are refused, so copying a placeholder does not write into the source
folder. Existing files are refused. The program creates no parent directories. Linked
export targets/parents are refused, but hostile concurrent filesystem changes
are outside the supported boundary. POSIX creation requests mode 0600; Windows
uses inherited filesystem permissions. A failed write can leave a partial new
file, so an error does not certify its contents.

Metrics and timestamps can reveal activity and hardware characteristics even
though no hostname, username, address or process list is collected. Capability
URLs are local access secrets. Keep real URLs, reports, terminal output and
downloads private and review them before sharing. Local software with the token
can read the aggregate API; this is not isolation from a compromised computer.
See [security and privacy](SECURITY.md).

## Tests and limitations

```text
python -B -m unittest discover -s tests -v
node --test tests/frontend.test.mjs
```

Node **24** is needed only for the built-in JavaScript test runner; there are no
npm packages or frontend build step. Python tests use generated samples and an
actual temporary loopback HTTP fixture. The live sampling case requires psutil;
CI installs the pinned dependency and sets `RESOURCE_MONITOR_REQUIRE_LIVE=1`, so
missing native sampling support is a failure instead of a silent skip.

The [validation record](docs/VALIDATION.md) distinguishes fake/provider checks,
HTTP integration, live system sampling, JavaScript unit tests and browser checks.
These do not establish a performance benchmark, network diagnosis, security
verdict, calibrated hardware telemetry or universal platform support.

Exit code 0 means the requested operation completed; code 2 means a fixed
validation/dependency/bind/export failure. Ctrl+C uses 130 and saves no automatic
history file. Check the selected port, explicit bounds or dependency when a
command is refused. Use a fresh server URL after restarting it.

## Suggestions

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=resource_monitor_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=resource_monitor_bug.yml).
Share fictional examples and redacted results with OS, Python, psutil and source
versions. Do not attach real capability URLs, network logs, private reports or
identifying screenshots. Contributions are welcome under the [contribution
guide](CONTRIBUTING.md).
