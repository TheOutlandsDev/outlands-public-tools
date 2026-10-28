# Complete local application architecture

Fresh standard-library implementations cover five pure calculation areas.
`contracts.py` checks exact fields/types/bounds; `engines` contains capacity,
process, inventory, dispatch and completion/snapshot calculations. No engine
opens an operating database, contacts a service or performs physical actions.
`application.py` supplies immutable revisions, event identity persistence,
comparison, local review, reports and backup. `planning_report.py` implements the
explicit checked handoff. The CLI and loopback UI use these same functions.

## Calculation meanings

Capacity floors aggregate declared productive minutes divided by cycle minutes.
The algebraic headcount result ceilings required minutes divided by per-person
productive time. Neither result solves a constrained workforce/scheduling problem.
OEE components preserve declared definitions and undefined denominators rather
than clamping inconsistent inputs. The application does not certify conformance
to a process standard. Cycle statistics include an explicitly named P90 method.

Inventory position is available on-hand plus asserted usable inbound. A declared
usage/lead/safety policy gives reorder/target levels; proposals round up to whole
order multiples. There is no purchasing authority. Dispatch checks prerequisite,
hold and downstream-capacity assertions before calculating bounded age/urgency
contributions. A transparent declared score is not a trained prediction.

Active-lot states describe a snapshot; completions describe a chosen time window.
UTC-normalized source/event identities are unique. The dashboard totals by family
and headline use the same selected events. Saved scenarios pin those events so
later ingest cannot rewrite historical results.

## State and recovery

SQLite stores canonical scenario JSON, sequence, parent hash and a digest binding
the complete revision. Saving requires the expected current hash. Identical
canonical content is a no-op. Event keys are scoped by scenario project; existing
identity content cannot change. Invalid/conflicting batches roll back all their
inserts. A later snapshot may select a smaller event set without deleting the
earlier accepted ledger or older scenarios.

A page-count budget is checked inside the database transaction before commit.
Exceeding the 64 MiB store budget rolls back both event and revision inserts.

Comparison reports common numeric differences, undefined changes, added/removed
cases, dispatch-eligibility changes, policy IDs and reporting windows. Different
assumptions remain visible; deltas are not an optimization or causal estimate.
Local reviews bind domain/case/current revision and optimistic review version.
Revision/event/review tables have append-only triggers. Database-owner access
can bypass local controls; hashes are neither signatures nor external anchors.

One session lock and process-level database lock support a single local operator.
The exact schema, metadata version, rollback-journal header and absence of
sidecars are checked before operations; SQLite extensions are disabled. Backups
use the SQLite backup API and checked new-only destinations. An idle-process
restart test does not establish mid-transaction/power-loss recovery.

## Boundaries and integration

The unchanged first-party native helper snapshots preserve the public Windows
identity/reparse/hard-link checks and POSIX guarded/no-follow opens, with checked
ancestors and exclusive output creation. New instances cannot live inside the
source/Git tree. These checks assume stable trusted local storage, not a hostile
filesystem or network/distributed locking model.

Planning-report import requires exactly five named files, checks all four payload
hashes/sizes and validates the report's identities, advisory flags and conservation
totals. It stores totals plus a manifest digest, without a source path or automatic
stage/eligibility mapping. It does not authenticate the report producer. Reports
and copied inputs are private and should remain stable during separate reads.

The UI offers real editable forms and a full JSON editor. Untrusted content uses
DOM textContent/value, not interpolated HTML. API reads/writes require a session
token; requests check Host and writes check Origin. Bodies and collections are
bounded, responses are no-store and error text is fixed. Trusted inline scripts
and styles remain in the local CSP. Shutdown waits for active handler threads.
The standard-library HTTP server is for local use, not multiuser/public hosting.

Reports use fresh directories, exclusive writes and hash manifests. Mail output
is a deterministic local draft with reserved example addresses; no transport is
included. Output text and archives may still contain operator-provided private
information. CSV escaping is limited to common leading formula characters and
does not anonymize data or guarantee spreadsheet behavior in every reader.
