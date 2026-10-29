# Validation and evidence boundaries

The application suite discovers **101 methods**, preserving all 65 original methods, covering strict configuration,
canonical state, complete CSV/JSONL jobs, input/forecast rejection gates,
idempotent runs, job replacement/history, persisted retry/exhaustion/acceptance,
matching unverified delivery reports, callback restrictions and minimized status.

Persistence tests cover new-only initialization, exclusive sessions, stopped
assertions, retained partial generations, committed corruption, malformed markers,
limits, poisoned sessions, failed claims before transport, acceptance followed by
failed outcome persistence, and committed state with a lost acknowledgment.
Three real child-process exit cases cover run start, durable claim before callback,
and a fake external acceptance side effect followed by termination. Recovery
retains review state and does not replay those uncertain attempts.

Filesystem cases exercise ordinary-file writes, source-output boundaries,
no-overwrite output, symlink leaf/ancestor/workspace refusal, hardlink refusal,
Windows junction/stream rejection and POSIX FIFO refusal. Link fixtures may be
skipped on a local volume lacking support. CI sets `STACK_REQUIRE_LINKS=1` and
refuses such skips; the sole expected platform skip is POSIX FIFO on Windows or
Windows junction/stream checks on Ubuntu. These are sampled stable-local-storage
checks, not hostile filesystem or universal volume/ACL acceptance.

CLI/package cases run actual commands across process restarts, verify error/path
omission, source manifests, deterministic ZIP metadata/member selection, output
refusal and an extracted standalone package's source-check/demo. Source fixtures
and all test inputs are invented. No network/provider, original application,
business formula/schema, operational record or real message is read or sent.

From this application directory:

```text
python -B -W error run_checks.py
python -B stack.py source-check
```

Windows/Ubuntu Python 3.12/3.13 CI runs these 65 application methods and the
original public 21 ingestion, 38 forecast and 45 outbox methods in separate
processes. It requires the actual fictional demo, source-check and ZIP package.
All four generated source ZIP digests are reviewed for byte agreement before
publication. Actual findings, skips and logs are recorded in the private batch
ledger; fictional runtime workspaces and failure traces are not publication files.

This establishes the selected bounded local application behavior. It does not
establish real provider delivery, useful real-data forecast accuracy, business
authorization, arbitrary database/store repair, threading/distributed use,
power-loss guarantees, private adapter safety or whole-repository confidentiality.
No runtime test grants rights in held original source or actual inputs.


## Browser workbench qualification

The 36 additional core methods cover nonmutating exact previews, configuration
and result pins, idempotent runs, immutable historical job settings, fake retry/
uncertain/interrupted outcomes, explicit caller assertions, private report pins,
review checks, readback hashes, retained partial outputs, report-root guards,
strict request shapes, finite/depth-bounded JSON, authenticated real HTTP, nonce
script policy, framing rejection and competing requests. An actual CLI child
starts the UI, stops through its authenticated endpoint and reopens the unlocked
journal. The original three process-exit recovery tests remain unchanged.

The 25 separate real Chromium methods cover configuration, CSV/JSONL previews,
forecast tables/graph and independent numeric expectations, reports, repeated
keys, invalid/stale drafts, job replacement, fake queue transitions and due ticks,
caller assertions, lost write replies, refresh/restart without replay, literal
markup, busy actions and wide/390-pixel keyboard layouts. Test dependencies and
Chromium install separately; no binary or private test workspace is packaged.

Publication requires Windows/Ubuntu Python 3.12/3.13 each to pass 100 core methods,
25 browser methods and the original public 21 ingestion, 38 forecast and 45 outbox
methods. One opposite-platform core case remains skipped. Five applicable native
boundary methods must pass with STACK_REQUIRE_LINKS=1, including the new linked
report-root refusal. A controlled local Windows run passed 95 core methods with
six visible native/platform skips; those local skips do not count as CI proof.

A clean source ZIP walkthrough checks all selected bytes, the unchanged CLI demo,
actual standalone browser startup and independent report-file lengths/hashes.
Wide/narrow UI screenshots are inspected privately. Outputs and reports remain
private; a passed review assertion does not sanitize content or authorize release.
No real provider, meaningful real-data forecast accuracy, full journal restore,
hostile storage, distributed service or power-loss durability is validated.
