# USB Connection Monitor source review — 2026-10-26

The local webcam USB troubleshooting use case has a new original reusable
implementation: selected-instance present-only Windows PnP polling, bounded
child queries, a neutral sampled-observation model, CLI and idle-start Tk
desktop. The historical wrapper remains unchanged and privately fingerprinted.
Its fixed paths, ETW setup, camera probe and original body are not copied.
This package includes original MIT source, first-party MIT helpers, authored
guides/tests and fictional sample generators only. No actual device list,
instance ID, native log, real session, media, credential, held source or external
implementation/runtime is bundled or relicensed.

Local Windows CPython 3.12.7 / Tk 8.6.13 qualification discovered 74 methods:
**70 passed and 4 platform/environment skips**, no failures/errors.
The read-only native PnP test was explicitly required and passed. The initial
restricted sandbox denied CIM access; the same authored query succeeded in the
normal local user context. No identifiers/raw output are in this public package.
Configured Windows/Ubuntu CI has four Python 3.12/3.13/3.14 jobs with required Tk,
and required read-only PnP qualification on Windows. Consult Actions for actual
remote outcomes. Skips are distinct from passes.

Native qualification records cold-start timeouts and permits at most three
calls under the application's unchanged five-second per-query deadline. It
still requires a complete native query; persistent timeout or another query
error fails. An initial Windows/Python 3.14 CI call hit the deadline while the
other three module jobs passed. Timeout is unknown, not a successful observation.

Tests cover observed/unknown state transitions, initial absence, exact-ID
comparison, strict replay and bounds, validated schema-only fresh exports,
actual CLI processes, optimized-Python refusals, real disposable child output
limits/timeout/cancellation and native hidden Tk widgets. The Stop-button test
caught and corrected a stale-event binding during development. A generated
worker/model workflow is not a physical USB disconnect test. Shared helper
checks repeat existing safeguards and are not separate application features.

A separate seven-command fictional walkthrough ran all three built-in demos,
generated two replay files, replayed/saved a reconnect report, replayed an
unknown gap and refused replacement of an existing output. Both input fixture
files remained byte-identical. This is separate from unittest method counts.

Detailed instructions cover Windows/Linux installation, fictional demos,
desktop scanning/selection/monitoring, private live CLI selection, outputs,
schema, limits, cancellation, permissions, privacy and suggestions. Two
dedicated issue forms welcome fictional bug reports and improvements.
PowerShell queries are fixed read-only source; selected IDs never enter them.
The app does not elevate, open camera/audio streams, reset/unplug devices,
change drivers/security/power settings, start ETW tracing or upload data.

Session reports use a constant alias and relative observation times, with no
device name/ID, host identity, wall-clock date or raw native output. Private
selection lists intentionally contain local names/IDs and must remain private.
Source/commit metadata and required notices remain. Field omission is not
anonymization; timing/patterns still require a separate review before sharing.

Polling misses between-query changes. Unknown query gaps break transition
inference, and initial absence is not a disconnect. An observed present PnP
entry does not prove electrical state, port power, driver/stream health,
physical identity or a failure's cause. No controlled unplug/replug, port
relocation, sleep/resume, long-term hardware or streaming acceptance occurred.
Live Linux/macOS support and arbitrary hostile filesystem/process behavior are
outside acceptance. Fresh write failures can leave partial output; no automatic
deletion or replacement occurs.

Publication review uses an explicit source allowlist, SHA-256 source manifests,
private provenance fingerprints, privacy-pattern scanning with manual scope
review, and canonical Git-blob readback. These do not prove exclusive historical
authorship or absence of every possible secret. Windows, PowerShell/PnpDevice,
Python and Tk remain separately supplied under their applicable terms.
