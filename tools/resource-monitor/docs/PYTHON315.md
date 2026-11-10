# Python 3.12–3.15 download qualification

Resource Monitor 0.1.2 extends the checked launcher to regular CPython 3.12,
3.13, 3.14 and 3.15. The metrics schema, demo/live opt-in boundary, loopback
capability API, in-memory history and exclusive exports are unchanged. The
optional sampler is pinned to psutil 7.2.2 with official Windows x64 and Linux
x86_64 binary-wheel SHA-256 hashes. The retained BSD-3-Clause notice matches
the installed 7.2.2 license. No dependency implementation is bundled.

The [focused download workflow](https://github.com/TheOutlandsDev/outlands-public-tools/actions/workflows/download-handoff.yml)
builds manifest-reviewed committed source on Windows and Ubuntu and compares
stable ZIP/checksum bytes. It then tests the same extracted ZIP in eight lanes:
Windows/Ubuntu × Python 3.12, 3.13, 3.14 and 3.15.2. Publication depends on every
lane succeeding. The release's VALIDATION.json records actual patch versions,
source revision, ZIP hash and per-mode results.

Each lane uses two new venvs and imports from the extracted app. Demo has no pip
or psutil installation: 49 non-native methods run, and psutil must remain absent
and unimported. The fictional download exercise also checks the real wrapper,
bounded HTTP history, JSON/CSV exports, refusal to overwrite, normal stop,
restart and rejection of the old capability token.

Live separately installs only the hash-pinned binary dependency and runs five
native methods: provider sampling, bounded JSON/CSV CLI output, explicit fresh
export/overwrite refusal, live HTTP history/exports and live CLI server stop/
restart/token renewal. Raw readings and token URLs stay in captured output or
private workspace files. Missing live support fails. Native symlink fixtures
are required in CI. Thirteen Node presentation tests run in every lane.

From a complete repository checkout, commit reviewed app files and refresh the
explicit SOURCE-MANIFEST.json before packaging:

```text
python -B downloads/build.py --output NEW_ABSOLUTE_PACKAGE_DIRECTORY
python -B tools/resource-monitor/qualify_download.py --packages ABSOLUTE_PACKAGE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY --report NEW_ABSOLUTE_REPORT_JSON
```

Supply the selected Python and Node 24 separately. Qualification creates venvs,
installs the declared live dependency, briefly samples native aggregate metrics
and starts bounded loopback servers. No Python installation, policy changes,
service, packet capture or process-list inspection is performed. Scratch paths
must be outside the app under trusted local parents. Failed private workspaces
remain available for review; public reports contain no readings or tokens.

The ZIP contains source, static assets, launchers, notices, tests and methods.
No runtime, dependency implementation, telemetry, credential or private original
is included. The older Windows runtime-bundled download retains its frozen
source/runtime. This source ZIP does not update that separate release.

Browser rendering/export interaction, other architectures, free-threaded Python,
calibrated measurements, performance benchmarking, isolation from compromised
local software and packet/network diagnosis remain unqualified.
