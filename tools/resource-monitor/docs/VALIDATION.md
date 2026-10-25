# Validation — Resource Monitor 0.1.0

Local Windows / Python 3.12.7: **46 Python cases discovered, 45 passed and one
skipped**, with no failures or errors. The skip requires symlink-creation
permission this account lacks. **All 13 Node 24 presentation cases passed.**
The live psutil case ran; it was not skipped. A separate three-sample live CLI
sequence also passed without starting a server or saving a report.

The Python suite tests generated providers and real temporary loopback HTTP
exchanges. Cases cover first-sample warm-up, finite percentages/counters,
monotonic rates, counter resets, missing fields, explicit sampling error state,
bounded/defensive history, exclusive exports and socket/worker shutdown.

HTTP cases exercise actual token/Host/Origin checks, duplicate headers, malformed
or oversized requests, unsupported methods, static routing, strict query bounds,
JSON/CSV downloads and lack of token reflection. No test contacts an external
service. The fixture server performs no packet capture or process inspection.

The optional live case samples actual aggregate CPU, memory and network counters
via separately installed psutil. CI installs `psutil==7.2.1` and sets
`RESOURCE_MONITOR_REQUIRE_LIVE=1`, making missing native sampling support a
failure. It does not replace live data with generated values to force a pass.

Node's built-in test runner checks the real pure presentation module: numeric
formatting, unavailable values, UTC labels, binary byte units, chart scaling,
gaps and history shape guards. It uses no npm packages or browser mocks to claim
rendering acceptance. Actual browser checks are recorded separately by the
release reviewer, including demo connection, visible mode, history/chart
rendering, pause/resume, explicit download and stale/error behavior.

Current platform totals, skips and outcomes are available in the collection's
[Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions).
Source-manifest, JSON/AST and local-link checks are separate from runtime tests.

These are functional client/server tests, not calibrated measurements, a
performance benchmark, network-speed acceptance, a threat verdict or proof of
support on every operating system. Network counters can include loopback and
virtual adapters, counter/interface changes can affect derived rates, and CPU
or memory semantics vary by platform. First readings and unavailable/reset
values are intentionally not represented as valid zeros.

Exports/history contain operational metrics and timestamps. Validation fixtures
are fictional; real reports and capability URLs must be reviewed privately
before sharing. Normal shutdown is tested, but power-loss recovery, hostile
filesystem writers, compromised local software and exposed/proxied deployments
are outside this release's supported boundary.
