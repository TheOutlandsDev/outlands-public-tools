# Fictional browser, application and platform validation

The qualification suites discover **86 application/HTTP/lifecycle/native methods**
and **19 actual Chromium methods**. Required CI covers Windows/Ubuntu CPython
3.12/3.13. Every applicable method must pass; native-link fixture creation failures
are failures under `WORKBENCH_REQUIRE_LINKS=1`. Windows has one POSIX FIFO skip;
Ubuntu has Windows stream and junction skips. Local filesystem limitations are
recorded explicitly, and never counted as native proof.

The original 76 application methods and all public calculation engines,
schema, store guards, JSON parser and fictional input documents are unchanged.
Existing tests retain independent arithmetic, strict contracts, append-only history,
version conflicts, hashes, native boundaries and actual idle child termination.
Idle termination does not prove mid-transaction or power-loss recovery.

New HTTP tests exercise coherent snapshots, serialization of whole operations,
current-revision report pins, duplicate framing/headers/query refusal, nonce CSP,
and actual CLI server shutdown followed by lock release and reopen. A native
Windows junction test supplements original hard-link and symbolic-link fixtures.
Missing Origin/Content-Type remain compatible for explicit trusted local clients;
present cross-origin or non-JSON values are refused. Runtime storage guards stay
unchanged on both platforms.

Real Chromium checks cover fictional boards, JSON/template creation, validation
errors with draft retention, two-tab stale saves, explicit discard, report inventory
and hashes, backups, lost save/backup replies without replay, restart, literal markup
as text, keyboard navigation and 390-pixel containment. The first browser run found
revision-hash overflow; the layout was corrected without weakening its assertion.
Screenshots, browser profiles and local evidence are private, excluded from assets.

Planning browser workflows also append a fictional order revision, retain history,
exercise acknowledge/exception/note/resolve transitions, refuse stale action versions
and stale revisions, and clear review drafts when explicitly loading another state.
Baseline fictional quantities remain 160 demand = 25 dock + 85 covered + 50 uncovered;
the second demo revision has 170 demand and 60 uncovered. Proposals reserve no IDs.

Both source ZIPs are deterministic, new-only and checked against pinned source
inventories. Qualification verifies exact-commit CI results and cross-platform ZIP
digests before publication; focused assets and changed files get separate privacy
audits and public download byte verification. The pass uses existing public code
and new generic tests only; no original private system or real operating record is
read, copied or executed. Future instance data, notes, reports and backups stay private.

No live manufacturing, purchasing, shipping, mail delivery, identity reservation,
authenticated reviewer, useful real-world forecast, automatic physical execution,
process conformity, hostile SQLite/filesystem, network storage, multiuser hosting,
damaged-store restore, mid-commit crash or power-loss validation is claimed.
