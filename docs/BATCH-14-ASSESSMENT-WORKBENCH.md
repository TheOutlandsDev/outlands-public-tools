# Offline Assessment Workbench review — 2026-10-25

This batch adds [Offline Assessment Workbench](../tools/assessment-workbench/README.md),
a fresh Python 3.12/3.13 standard-library CLI/Tk application over the public
neutral assessment-record format. It bundles the exact public MIT checker
from commit `2dff9246054e4ad6c9bf59b91d6d9fa3b2cbcf67`, with its digest and origin
recorded. No held original assessment application, private schema, actual
store, target, identity, narrative, evidence, credential or operational record
was selected, read, copied or executed. Earlier source/data holds remain.

## Behavior and data boundary

The app starts without a selected store. Operators explicitly create a new
empty private SQLite store, choose the fictional demo, or open an existing
compatible private store. Guided forms edit submission/finding/retest drafts;
Apply changes memory and Save commits the complete draft. IDs remain immutable
on edit, removals do not cascade, dangling references remain visible and
schema-valid `REVIEW_REQUIRED` drafts are retained unchanged. Empty workspaces
are explicitly unverified; the bundled public checker is unchanged.

Saves use an immediate transaction and expected-revision checks, append a
full canonical snapshot and update the head atomically. Head versions and
history are validated before use. CLI record helpers also check the loaded
base revision before deriving a draft. Stale saves retain the desktop draft
and require explicit refresh/reapplication, with no automatic merge or retry.

History is bounded and sequence-based. Its checksums detect internal
inconsistency, not authenticity or external rewrites made consistently.
Removing a current record retains its plaintext in earlier snapshots. There
is no pruning, migration, encryption, signed approval or authentication claim.

Import creates a new store; export writes a new private neutral JSON ledger.
Logical clone/recover reconstructs validated history through an explicitly
selected revision into a new initialized database. It never copies unknown
database pages, overwrites a source, repairs corruption or recovers a hot
journal. Failed new outputs are retained for inspection without cleanup.
After uncertain write failures, reopen before retrying.

Stores, journals, history, imports, exports, recovery copies and UI contents
remain private. The UI can display the selected store path and record data.
Public sharing requires a separate review. The strict schema has no targets,
endpoints, people, narratives, payloads, attachments, evidence paths/hashes,
authorization records, source builds or actual test timestamps. The app
executes no tests, commands, model or network operation and verifies no fix,
authorization, isolation or outcome.

## Storage and filesystem limits

The store is capped at 16 MiB with 4 KiB pages; canonical ledgers at 64 KiB;
history at 128 snapshots including revision 0. Exact schema, application/user
versions, rollback-journal format, quick-check, all historical snapshots,
contiguous sequences, canonical bytes and head/checksum links are validated.
Connections disable extension loading and trusted schema, use defensive/query
settings where supported, and bound SQLite operations. Read opens use `mode=ro`,
not immutable mode. Writes use parameter binding; no free SQL is accepted.

Adversarial review found that a readonly SQLite WAL refusal could create WAL
sidecars. The corrected code checks a bounded identity-verified SQLite header
before connecting, rejecting unsupported formats without SQLite artifact
creation. Public I/O APIs are serialized within the process and reject reentrant
store/JSON opens while an owned SQLite connection is live, avoiding raw-file
close interactions with its POSIX locks. Other SQLite access in that same
process is unsupported. Selected database names are normalized to Windows
long names; source artifact families and checkout aliases are protected.

Use stable trusted local files and parents. These checks do not form an atomic
filesystem sandbox or protect against hostile concurrent replacement. Arbitrary
mount aliases, network-storage behavior, power loss and Windows ACL privacy
remain unproven. SQLite busy/progress budgets are sampled limits and cannot
interrupt blocked OS I/O; desktop operations are synchronous.

## Validation and publication scope

The local Windows/Python 3.12.7 app suite discovered 62 cases: 60 passed and two
native-link operations were skipped. All 12 real Tk cases ran and passed.
Independent walkthroughs passed 15 Tk and 26 CLI scenarios. A separate review
passed 57 synthetic storage cases, including rollback preservation, history,
corruption refusal, native Windows aliases and API serialization. The corrected
WAL refusal was independently verified to preserve source bytes and create no
sidecars. Skips, simulations and native observations are separate evidence.

An exact 20-file standalone copy outside the collection also passed the source
gate before and after its full suite: 62 discovered, 60 passed, two native-link
skips and all 12 real Tk cases passed. Tests use the pinned bundled checker hash
and explicit fictional result vectors without sibling imports. Writer contention
is exercised in another process, with exact `STORE_BUSY` and unchanged saved
snapshot, history and database bytes.

The separate integrated collection regression discovered 384 methods: 365
passed and 19 were skipped, with no failures/errors. The 19-file source manifest
plus its manifest file matched before and after testing. Ruff checks/formatting
and 230 local documentation/JSON checks passed. Concurrent media/inventory and
developer-QA additions were preserved; this does not extend their source-clearance scope.

A private capture of only the app's fictional demo window was visually reviewed.
It is not included in the public source. Broader human usability/accessibility,
arbitrary databases and real assessment operations are outside this evidence.
The dedicated workflow requires real Tk on Windows/Ubuntu, Python 3.12/3.13;
consult exact-commit Actions results for executed platforms.

The fixed source gate inventories only declared text source/docs/tests/examples
and verifies the bundled public checker digest. It is not a secret scanner or
authenticity proof. The exact changed-file export receives a separate private
marker/pattern review. Private markers, audit output, source mappings and
publication receipts stay outside this repository. Review does not clear
unrelated imports, Git history, release assets or held source/data families.

Selected original source, tests, documentation and fictional examples use MIT
with TheOutlandsDev attribution. Python, SQLite and Tcl/Tk remain separately
supplied runtimes under their respective terms.
