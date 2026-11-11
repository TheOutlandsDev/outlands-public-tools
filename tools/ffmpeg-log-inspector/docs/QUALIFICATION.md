# Standalone source qualification

Version 0.1.0 adds source packaging and fresh extracted-download qualification
around the original offline inspector. The retained
[validation record](VALIDATION.md) reports the earlier local Windows /
PowerShell 7.6.5 baseline: 55 generated CLI cases and one additional native
symbolic-link case explicitly skipped because privilege was unavailable. That
historical result is not a standalone matrix result. The release VALIDATION.json
records the new baseline rerun and final runtime/helper lane outcomes, exact
counts and skips; no outcome is inferred from a configured workflow.

## Selected prerequisites

The official [PowerShell 7.6.10 LTS release](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.10)
and [7.7.0 stable release](https://github.com/PowerShell/PowerShell/releases/tag/v7.7.0)
provide the Windows x64 / Linux x64 portable archives selected for Windows x64
and Ubuntu x86-64 qualification. Their URLs, SHA-256 digests and lengths are
recorded in [RUNTIMES.json](RUNTIMES.json). The helper verifies the selected
archive's digest and length before extraction or execution. PowerShell/.NET
remain separately obtained prerequisites with their own licenses and notices;
no runtime is included in the source ZIP.

Archive verification checks the downloaded archive bytes against those recorded
values; it is not an integrity or security attestation of an extracted runtime
tree, its host, or code executed later.

The inspector needs only PowerShell. Python 3.12, 3.13, 3.14 and 3.15.2 are
maintainer source/build/qualification prerequisites, tested in eight separate
Windows/Ubuntu helper lanes. Neither Python nor a .NET SDK, module installation,
Pester, FFmpeg installation or administrator privilege is inherently needed by
the CLI. Corporate execution policy may restrict it. The script's runtime floor
(`#requires 7.2`) is not evidence of qualification on every older patch.
Other architectures and Windows PowerShell 5.1 are outside these lanes.

## Repeatable maintainer commands

Run from this source folder using a selected Python version. Every generated
target is a new absolute private directory outside the source. The runtime
helper explicitly downloads its selected official prerequisite; the inspector,
demo generator and fixture suites do not access the network.

Optimized Python (`-O`, `-OO` or optimization enabled via `PYTHONOPTIMIZE`) is
unsupported: the build/runtime/qualification helpers depend on assertions and
reject that mode before performing their work.

```text
python -B source_check.py
python -B packaging/build.py --out NEW_PACKAGE_DIRECTORY
python -B packaging/runtime.py --version 7.6.10 --out NEW_RUNTIME_DIRECTORY
python -B packaging/qualify.py --packages PACKAGE_DIRECTORY --runtime RUNTIME_DIRECTORY --workspace NEW_PRIVATE_DIRECTORY --report NEW_JSON_FILE
```

Repeat runtime qualification for 7.7.0 and each selected operating system.
Commit reviewed source before building. The source gate verifies an explicit
source allowlist, text/link/privacy checks and exact manifest hashes. The
deterministic source ZIP uses committed Git blobs and fixed metadata. It
contains no runtime, real log, media, generated fixture/report or private
payload. Each of the eight helper lanes runs source/build checks and compares
exact generated ZIP bytes, rather than only comparing member names.
Those lanes also verify that optimized Python is refused.

Four fresh runtime lanes cover both selected PowerShell releases on Windows x64
and Ubuntu x86-64. Each verifies the source package, extracts it into a new
private workspace, uses the selected hash-verified portable runtime and runs
the existing generated PowerShell harness. Each lane also creates a fresh Python
venv without pip or installed distributions, then runs independent stdlib
unittest cases against a copy of only `Inspect-FFmpegLog.ps1`. The copied runtime
is invoked in real child PowerShell processes; CLI results are not mocked.

The added cases exercise authored progress/stderr/review text, report/hash
readback and privacy omissions, incomplete blocks and end-marker limits,
malformed/unsupported text, unchanged inputs, fresh-only outputs, help, and
actual native linked-path refusal. Native symlink fixture creation is mandatory
in hosted CI; a missing privilege must fail that gate rather than silently pass.
A Windows junction-ancestor case runs on Windows and is explicitly skipped on
POSIX. Any local privilege-related native-link skip must be recorded and is not
a pass. Qualification does not change privileges or execution policy to make a
test succeed. Exact method/case counts and every actual skip belong in the
release VALIDATION.json.

Successful standalone qualification requires all four runtime lanes and all
eight helper lanes. Sanitized receipts record source revision, ZIP hash,
runtime/.NET/Python versions, prerequisite digests, case counts and skips.
Generated logs, reports and failure evidence stay in the explicit private
workspace. Read the release's receipts before claiming a particular lane passed.

These checks establish only the recorded authored-fixture behavior. They do not
validate arbitrary logs, all FFmpeg formats, secret removal, malware safety,
media quality, playback, capture-device health or process completion. An observed
final `progress=end` is text, not a process-exit or capture-success receipt.
Path checks and parsing bounds do not establish filesystem-race immunity, native
I/O timeouts, special-file safety, an operating-system sandbox or a hard process
RAM limit. Preserve the [format boundaries](FORMAT.md),
[privacy guidance](PRIVATE-WORKSPACE.md) and [provenance](PROVENANCE.md).
