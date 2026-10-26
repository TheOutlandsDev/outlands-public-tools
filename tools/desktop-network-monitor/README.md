# OUTLANDS Desktop Network Monitor

The local desktop packet-monitor application, cleaned up into an idle-start
Tk dashboard and CLI. Review bounded IPv4 packet metadata against simple local
port/length rules, try fictional traffic, replay selected metadata JSON and
optionally request one OTX reputation observation. Local rule matches and OTX
pulse counts are separate observations; neither establishes malware.

The owner's original source, these adaptations, tests and fictional examples
are [MIT licensed](LICENSE). Optional dependencies retain their own licenses:
Scapy is GPL-2.0-only, psutil BSD-3-Clause and Requests Apache-2.0. They are
installed separately; no dependency, driver or combined executable is bundled
or represented as entirely MIT. Read [notices](THIRD-PARTY-NOTICES.txt) and
[provenance](docs/PROVENANCE.md) before redistributing a combined installation.

## Start with fictional traffic

Use CPython 3.12 or 3.13. The no-network demo, replay and aggregate export use
the standard library. The optional desktop also needs Tk/Tcl. Download or clone
[outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/desktop-network-monitor`. Keep the complete folder together.

```text
python -B monitor.py --help
python -B monitor.py demo
python -B monitor.py gui
```

No arguments prints static help. Nothing captures traffic, contacts OTX or
creates a log/CSV/report automatically. In the desktop press **Fictional demo ·
no network**. It shows three invented packets and two packets matching local
rules, clearly marked FICTIONAL DEMO. No optional dependency is needed for that
demo. Ports and lengths are deliberately simple review hints, not signatures.

## Optional dependencies

Choose an existing external private workspace for the environment and outputs;
see the [workspace guide](../../docs/PRIVATE-WORKSPACE.md). Install optional
packages only for the features you intend to use. Windows PowerShell, after
setting `$privateWork` to an existing absolute directory you control:

```powershell
python -m venv "$privateWork/network-monitor-env"
& "$privateWork/network-monitor-env/Scripts/python.exe" -m pip install --only-binary=:all: -r requirements-live.txt
& "$privateWork/network-monitor-env/Scripts/python.exe" -B monitor.py gui
```

Linux equivalent, with `private_work` set to an existing absolute parent:

```sh
python3 -m venv "$private_work/network-monitor-env"
"$private_work/network-monitor-env/bin/python" -m pip install --only-binary=:all: -r requirements-live.txt
"$private_work/network-monitor-env/bin/python" -B monitor.py gui
```

Pinned direct dependencies are Scapy 2.8.0, psutil 7.2.2 and Requests 2.34.2.
These pins are not a complete transitive lock or dependency advisory audit.
Tk is supplied separately by your Python/OS distribution. Packet capture also
requires a suitable native capture backend and OS permission. Windows Scapy
normally needs separately supplied Npcap; follow [Scapy installation](https://scapy.readthedocs.io/en/stable/installation.html).
This application does not install drivers, elevate itself or change permissions.
Npcap has its own terms and is not included or granted MIT here.

## Desktop actions

1. **Fictional demo · no network** fills the local-rule table using invented
   IPv4 metadata. **Open metadata JSON…** reviews a selected supported JSON file.
2. **System snapshot · local** explicitly reads CPU/RAM and cumulative network
   byte counters using psutil. These are current host observations; network
   totals are not capture-session bytes or transfer rates. They are not added
   to the aggregate packet export.
3. For an authorized local capture, enter an exact interface identifier accepted
   by Scapy and duration from 1 to 600 seconds. Press **Start live capture…** and
   review its confirmation. No default interface is selected. Only IPv4 is in
   scope; Scapy's fixed `ip` capture filter is used.
4. **Stop** or closing the window requests cancellation. Only the app's owned
   child is terminated if cooperative shutdown stalls. Forced shutdown makes
   the retained last aggregate explicitly incomplete and review-required.
5. **Save aggregate report…** creates one new JSON file when explicitly chosen.
   Existing output is never replaced. Reports omit addresses and payloads.
6. To request reputation, manually enter one public unicast IPv4 address and
   press **Send one address to OTX…**. Review the destination/address confirmation.
   This sends that address to `https://otx.alienvault.com` using your private
   `OTX_API_KEY` environment value. No captured address is submitted automatically.

There is one background action at a time. Network requests and packet capture
run in owned child processes, so a blocked native call does not run on the Tk
thread. Active controls are disabled appropriately. OTX results remain separate
from the packet rule counts and aggregate report. A failed lookup is unknown;
it is never presented as zero pulses or a clean reputation verdict.

## CLI and fictional replay

Set `$privateWork` as above and generate invented inputs outside the checkout:

```powershell
python -B examples/generate.py --output "$privateWork/network-demo"
python -B monitor.py replay --file "$privateWork/network-demo/packets.json" --output "$privateWork/network-report.json"
```

Linux shell:

```sh
python3 -B examples/generate.py --output "$private_work/network-demo"
python3 -B monitor.py replay --file "$private_work/network-demo/packets.json" --output "$private_work/network-report.json"
```

Replay does not require Scapy, open capture files or contact a service. It uses
the [authored metadata schema](docs/FORMAT.md), not PCAP/PCAPNG/ETL or old CSV logs.
The generator refuses an existing directory and replay leaves inputs unchanged.
See [example expectations](examples/README.md).

Optional local system counters:

```text
python -B monitor.py system
```

Explicit capture, using the environment with Scapy and a known permitted
interface name. Replace `EXACT_INTERFACE` yourself:

```powershell
python -B monitor.py capture --live --interface EXACT_INTERFACE --seconds 30 --output "$privateWork/network-live-report.json"
```

The optional external lookup requires a separately supplied private environment
key and a deliberately entered public address. Do not paste keys into examples,
issues, screenshots or source files:

```powershell
$selectedAddress = Read-Host 'Public IPv4 address you intend to send to OTX'
python -B monitor.py lookup --allow-online --ip $selectedAddress
```

The CLI flag explicitly authorizes that one request; it can place the address
in shell history/process arguments. Private, loopback, link-local, multicast,
reserved/documentation and other nonglobal IPv4 addresses are refused before
the request. IPv6 is not supported. Requests do not follow redirects or discover
`.netrc` credentials/environment proxies. TLS verification remains enabled.
OTX response bodies are limited to 256 KiB; malformed/missing pulse counts and
HTTP failures remain errors. The owned lookup worker has a 12-second budget plus
cleanup. No real OTX lookup or API-key validation was used for release testing.

## Scope, bounds and privacy

Capture handles IPv4 and immediate TCP/UDP transport metadata. Nested ICMP
quotations and noninitial fragments do not contribute borrowed TCP/UDP ports.
Observed byte lengths depend on the decoded packet/link framing, not necessarily
the original on-wire size. The default local rules match ports 23, 135, 139,
445, 6667 and 6668, or observed length outside 40–2,000 bytes. Legitimate traffic
can match these rules; unflagged traffic can still be unsafe.

At most 5,000 accepted packets, 256 tracked hosts and the first 200 rule events
are retained. Host/event overflow is counted and requires review. There is no
payload recording, PCAP saving, automatic IP CSV, background persistence, automatic
reputation submission, blocking/firewall action, probing or traffic injection.
The native capture stack necessarily handles packet bytes in memory; this app
retains only selected metadata and does not promise a kernel-level payload scrub.

Aggregate exports contain counts, protocols, observed lengths and rule codes,
with no IP addresses, interface/host/user names, absolute timestamps, payloads,
paths or keys. Relative packet order and structure can still identify traffic.
Omission is not anonymization. The system snapshot and live interface/address
entries are private local information; captures, shell history and native-library
diagnostics may contain identifying details. Keep all real material outside the
source checkout and review it separately before sharing. Ordinary source/commit
metadata and required notices remain in GitHub.

Replay input and aggregate output are bounded to 1 MiB. Outputs need a new
portable ASCII `.json` filename under an existing trusted local parent. Links,
traversal, device/stream paths and replacement are refused. An I/O interruption
can leave a partial newly created file; no automatic deletion runs. File checks
are not a hostile-filesystem sandbox or an inherited-ACL/privacy guarantee.

## Validation and suggestions

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

See [validation](docs/VALIDATION.md) for actual generated packets, installed
Scapy decoding, owned-process shutdown, CLI, native Tk and local-counter checks.
Live interface capture, Npcap integration and the external OTX service remain
unqualified; the public source labels those acceptance gaps explicitly.

CLI exits: 0 completed/help/observation; 1 report requiring review; 2 refused,
unsupported or failed action; 130 keyboard interruption. OK means no coverage
gap in the selected model, not safe traffic or clean hardware/network state.

[Bug reports and suggestions](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)
are welcome. Choose this app's form and include your source commit, platform,
Python/Tk/dependency versions and a minimal invented example. Do not attach real
addresses, packet captures, logs, API keys or customer data. Read
[CONTRIBUTING.md](CONTRIBUTING.md) and [security boundaries](SECURITY.md).
