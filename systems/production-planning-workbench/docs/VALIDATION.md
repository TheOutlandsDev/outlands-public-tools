# Fictional validation and operational limits

The complete demo uses an invented two-product workshop, three orders, five WIP
lots, neutral seven-stage mappings and explicit dock/clearance declarations.
No original policy, customer source, record, workbook or database is opened.
The demo checks conservation, proposals, review, revision, reporting and backup.

The suite tests independent expected allocations and arithmetic, dock/WIP
conservation, deterministic/no-write plans, version/replay conflicts, order
history preservation, local action conflicts/transitions, readiness states,
sequence carry/exhaustion, distinct Decimal rounding rules, schema/version/
sidecar refusal, source/workspace boundaries, new-only outputs, report hashes,
CSV escaping, backup validity, strict JSON/types and an actual child-process
termination followed by stale-lock recovery. That termination occurs while idle;
it does not prove recovery from a mid-transaction crash or power loss.

The real loopback HTTP handlers are tested for initial page, token/Host/Origin,
project saving/planning, unexpected fields and fixed errors. The selected UI
uses text-only DOM rendering for caller data. A local interactive browser attempt
could not start because the automation sandbox failed to initialize; interactive
browser acceptance remains unverified. API checks are not a browser walkthrough.

CI runs CPython 3.12/3.13 on Windows x64 and Ubuntu x86_64. Each job installs only
hash-pinned wheels in the checked requirement set, requires native hard-link
file/store and symbolic-link file/ancestor rejection fixtures, runs the full
fictional workflow, checks the source manifest, packages deterministic source
and validates Markdown/JSON. Local fixture-creation limitations remain explicit
unittest skips; `WORKBENCH_REQUIRE_LINKS=1` makes them failures in CI.

A fresh local Windows environment installed all five pinned dependencies. The
local suite discovers 76 methods, with 71 passing, four unavailable native-link
fixtures skipped and one POSIX-only FIFO skipped. Exact publication-commit CI
must be verified before merging; focused ZIP digests must agree across all jobs.

No live integration, external identity lookup, real manufacturing acceptance,
shipping verification, automatic physical execution, full-browser acceptance,
hostile database, network filesystem, multiuser use, damaged-store repair,
restoration or power-loss validation is claimed. Caller-provided clearances,
shipping quantities, provenance and reviewer aliases remain unverified assertions.
The package's privacy review covers selected source and focused assets, not
future inputs/outputs or every historical program/repository file.
