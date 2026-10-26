# Fictional examples

Built-in demo needs no hardware, Windows query, file or dependency installation:

```text
python -B usb_monitor.py demo --scenario stable
python -B usb_monitor.py demo --scenario reconnect
python -B usb_monitor.py demo --scenario query-gap
```

Stable: four present samples and one initial-present event, exit 0. Reconnect:
six samples (four present, two absent), initial-present at 0 ms, observed absence
at 2000 ms and observed return at 4000 ms, exit 0. Query-gap: five samples (two
present, two absent, one unknown), exit 1; resumed absence is not labelled a
disconnect across an unknown gap. Every demo report has mode demo and the GUI
explicitly says FICTIONAL DEMO.

The [README](../README.md) gives Windows/Linux generator and replay commands.
The generator creates a new selected directory with reconnect.json (three
samples: present/absent/present) and query-gap.json (four samples:
present/unknown/absent/present). It refuses an existing directory. Generated
files and reports belong outside the source checkout. Replay uses no device ID,
does not query the OS and leaves its selected input unchanged. It is a neutral
authored sample format, not an importer for native Windows logs.

The reconnect replay has three transition/initial events and exits 0. The gap
replay has four events, including unknown and resumed-absence, and exits 1.
An optional --output must name a new absolute .json file in an existing private
parent. The saved JSON equals the console report; no sidecar or identifier is
added. Existing files are refused without replacement.
