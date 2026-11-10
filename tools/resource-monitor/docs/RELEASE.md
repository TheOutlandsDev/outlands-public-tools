# Resource Monitor 0.1.2

[Focused source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/resource-monitor-v0.1.2/resource-monitor-0.1.2.zip)

Extends checked Windows/Linux launchers to Python 3.12–3.15 and pins optional
psutil 7.2.2 binary-wheel hashes. The API, data formats and explicit demo/live
opt-in boundary are unchanged. Python is installed separately; the fictional
demo needs no pip packages. Follow the attached START-HERE.md or the
[first-run guide](../START-HERE.md), then the [download check](DOWNLOAD-CHECK.md).
Source, original fictional examples, tests, licenses and documentation only.
No runtime, psutil implementation, real metrics, reports or token is bundled.

SHA256SUMS.txt covers the ZIP, START-HERE.md, VALIDATION.json and release-matrix.json.
The matrix records the source revision and member count. downloads/build.py packages only
manifest-reviewed committed app blobs, with stable cross-platform ZIP bytes.
Eight Windows/Ubuntu × Python 3.12–3.15 lanes freshly extract the same ZIP and
use separate demo/live venvs. Each requires 49 demo tests without psutil, five
native-live tests, 13 frontend tests and the fictional HTTP/CLI download exercise.
Native links and live support are mandatory. Publication waits for all lanes;
existing releases are never overwritten. VALIDATION.json supplies actual patch
versions, per-mode results, exact ZIP hash and workflow.

JSON/CSV export endpoints, reopening bytes, bounded shutdown and token renewal
are exercised. Browser pause/export interaction is unverified in this patch;
Browser access was disabled during release review. History is memory-only,
exports require an explicit action and live sampling requires separate opt-in.
See [validation](VALIDATION.md) and [security](../SECURITY.md).
