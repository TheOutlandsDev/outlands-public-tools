# OUTLANDS USB Connection Monitor

Track sampled presence for one explicitly selected Windows USB Plug and Play
instance. A readable desktop timeline shows present/absent changes and query
gaps. The CLI, fictional demos and offline sample replay use the same model.

This is original [MIT source](LICENSE). Startup is idle. Live scanning and
monitoring require explicit actions. It never opens camera or audio streams,
records media, resets devices, changes drivers/power settings, starts ETW
tracing, installs software or uploads results.

## Requirements and installation

Use **CPython 3.12 or newer**. No pip package is required. The optional desktop
needs Tk/Tcl and a working display. Windows live mode needs the system's
Windows PowerShell and `PnpDevice` module. Demo, replay and model tests also work
on Linux. macOS and live Linux USB enumeration are outside acceptance.

Download or clone [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools),
then enter `tools/usb-connection-monitor`. Keep the complete folder together,
including its MIT license. Use `python3` where that is your Python 3 command.
No arguments or `--help` prints static help without importing Tk or querying
hardware:

```text
python -B usb_monitor.py
python -B usb_monitor.py --help
```

Keep real reports, device lists and generated examples outside the source
checkout in a [private workspace](../../docs/PRIVATE-WORKSPACE.md). Nothing is
saved automatically. An explicitly selected new `.json` file is created without
replacing an existing file. A failed/interrupted write can leave a partial new
file; review it rather than treating it as a completed report.
Report filenames use at most 120 ASCII letters/digits/spaces/dots/underscores/
hyphens, start with a letter or digit and end in `.json`; Windows device names
are refused on every platform. Parent directories may have normal Unicode names.

## Try it without hardware

```text
python -B usb_monitor.py demo --scenario stable
python -B usb_monitor.py demo --scenario reconnect
python -B usb_monitor.py demo --scenario query-gap
python -B usb_monitor.py gui
```

In the desktop, choose a fictional scenario and press **Run demo · no hardware**.
The result is clearly marked **FICTIONAL DEMO**. No Windows query, camera,
microphone or connection change occurs. Reconnect shows initial presence, an
observed absence at 2 seconds and observed return at 4 seconds. Query-gap shows
an unknown period, then resumed absence; it does not invent a disconnect across
that gap. Stable/reconnect CLI examples exit 0; query-gap intentionally exits 1.

To generate standalone fictional replay files, set `$privateWork` to an existing
absolute private directory you control, then use Windows PowerShell:

```powershell
python -B examples/generate.py --output "$privateWork/usb-demo"
python -B usb_monitor.py replay --file "$privateWork/usb-demo/reconnect.json" --output "$privateWork/usb-reconnect-report.json"
python -B usb_monitor.py replay --file "$privateWork/usb-demo/query-gap.json"
```

Linux shell, after setting `private_work` to an existing absolute private parent:

```sh
python3 -B examples/generate.py --output "$private_work/usb-demo"
python3 -B usb_monitor.py replay --file "$private_work/usb-demo/reconnect.json" --output "$private_work/usb-reconnect-report.json"
python3 -B usb_monitor.py replay --file "$private_work/usb-demo/query-gap.json"
```

The generator refuses an existing destination. Replay does not query Windows or
resolve any device. See [worked expectations](examples/README.md) and the exact
[sample/report formats](docs/FORMAT.md).

## Desktop live workflow on Windows

1. Launch `python -B usb_monitor.py gui`. It starts idle.
2. Press **Scan present entries**. This reads the present USB PnP list once.
   Labels appear locally; no entry is automatically selected or monitored.
3. Choose the intended entry. **Show selected ID…** reveals its exact instance
   ID locally when needed to distinguish similar labels. Do not post this ID.
4. Set duration (1–3,600 seconds) and pause between queries (0.5–60 seconds).
   The default is 60 seconds with a 2-second pause.
5. Press **Start selected · live**. The app tracks that exact PnP instance in a
   background worker and shows relative-time observations. Query failure means
   **unknown**, never absent. **Stop** cancels the current query/session; closing
   waits for query cleanup. There is one worker at a time.
6. When finished, optionally choose **Save report as new JSON…**. Existing files
   are refused. Device names and instance IDs are not in the session report.

The program queries identifiers beginning with `USB\`, including USB parent,
composite and interface entries where Windows exposes them that way. Other
logical endpoints may use different enumerators and are not included. Moving a
device to another port can create another instance ID; the monitor continues
tracking the selected old ID. It does not automatically merge interfaces,
recognize the same physical device or switch selections after a rescan.

## Live CLI on Windows

```powershell
python -B usb_monitor.py devices --live
$selectedId = Read-Host 'Paste the exact USB instance ID from the private list'
python -B usb_monitor.py watch --live --device-id $selectedId --seconds 60 --interval 2 --output "$privateWork/usb-live-report.json"
```

`devices --live` prints a **private selection list**, including friendly names
and instance IDs. Keep it local. A watch argument can also appear in your shell
history/process inspection. The desktop avoids placing the selected ID in a
child command line: all PowerShell queries use the same fixed command and the
exact selected-instance comparison happens in Python.

`--interval` is the wait **after a query completes**, not a promised sample rate.
Query startup/runtime also contributes to the time between samples. No new query
starts after the requested session duration; one already running can finish
after it. Each query has a 5-second processing deadline plus bounded child/pipe
cleanup waits. Scheduling, OS suspension and termination delays are not hard
real-time guarantees. CLI Ctrl+C stops without automatically exporting a report.

## Interpretation and limits

Present means the selected exact ID appeared in a successful present-only PnP
query. Absent means it did not appear in that successful bounded query. It does
not establish electrical state, video/audio health, port power, driver health,
physical disconnection or the cause of a failure. The application cannot prove
that a webcam streams merely because its PnP entry is present.

Polling can miss short changes, and each query is an observation rather than an
atomic physical-bus snapshot. Initial absence is not a disconnect. A transition
across an unavailable query is reported as **observation resumed**, not a
confirmed disconnect/reconnect. Related USB interfaces can appear separately.
Counts are sample counts, not time-weighted uptime or a count of every USB event.

| Bound | Limit |
| --- | --- |
| Duration | 1–3,600 seconds |
| Pause after query | 0.5–60 seconds |
| One query | 512 USB entries; 256 KiB UTF-8 output |
| Query processing deadline | 5 seconds plus cleanup |
| Session/replay samples | 7,201 |
| Recorded elapsed time | 0–3,620,000 ms, nondecreasing |
| Replay input | 1 MiB; exact schema, integer elapsed time |
| Report | 2 MiB; exact generated schema |

An over-limit or malformed query is unknown, not a partial successful list.
Unsupported/over-limit replay is refused. Missing permissions, unavailable PnP
services/modules, query timeout and suspension can prevent useful observations.
This is a troubleshooting aid, not a repair tool or causal diagnosis.

## Privacy and licensing

Public source and fixtures contain no actual device list, instance ID, native
log, personal path, customer data, credentials or real session. Session reports
use the constant alias `selected-device`, relative elapsed times and a fixed
allowlist of observation/error codes. They omit names, instance IDs, wall-clock
timestamps, machine details and raw native output. Exports are validated against
the generated schema and event/count model before creation.

Patterns and relative times can still identify a session. Field omission is not
anonymization. Local device lists, selected IDs, screen content and shell history
remain private operational information. This program is not a general metadata
scrubber. GitHub retains ordinary source/commit metadata, and MIT/third-party
notices remain. Review any real report separately before sharing it.

MIT covers the original app, tests, authored guides and fictional fixtures.
Windows, Python, Tk and their separately installed components keep their own
terms; no runtime, driver or external implementation is bundled. See
[provenance](docs/PROVENANCE.md) and [security boundaries](SECURITY.md).

## Validation and suggestions

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

The [validation guide](docs/VALIDATION.md) separates generated observations,
actual child-process cancellation/limits, native Tk widgets, read-only Windows
enumeration and untested physical disconnect behavior. Configured CI requires Tk
and performs an explicit read-only PnP query on Windows; Linux exercises replay,
demo and platform refusal. Skips are not passes.

[Bug reports and suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)
are welcome. Choose this app's form and provide a minimal fictional example,
OS/Python/Tk version, source commit, steps and expected behavior. Do not attach
real device lists, IDs, native logs or unreviewed session data. See
[CONTRIBUTING.md](CONTRIBUTING.md).

CLI exits: **0** successful/help, **1** completed observations needing review,
**2** refused/invalid/incomplete action, **130** keyboard interruption. An
explicitly cancelled desktop session records `outcome: cancelled`; an empty or
failed session requires review. `status: OK` describes the report's completeness
within this narrow model, not healthy hardware.
