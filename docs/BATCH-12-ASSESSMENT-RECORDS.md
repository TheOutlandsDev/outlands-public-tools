# Offline Assessment Record Contract Checker review — 2026-10-25

This batch adds [Offline Assessment Record Contract Checker](../tools/assessment-record-checker/README.md),
a fresh Python 3.12+ standard-library implementation from a neutral public
specification. The private audit's assessment management family remains held.
No original application, private schema, target, identity, narrative, evidence,
credential or operational record was selected, read, copied or executed for
this addition. Bounded control-file input handling adapts the collection's
existing public MIT checker pattern.

## Declared-record boundary

The strict ledger has submissions with series labels and integer revisions,
findings with original-submission references and workflow states, and retest
summaries with replacement-submission references and fixed declared outcomes.
Entity IDs are globally unique; series labels are a separate namespace. A
series/revision pair identifies one submission, and a finding/submission pair
has one retest summary. This format is not a repeated-run history or general
assessment database.

Every retest, including unselected history, must refer to a known finding and
a later replacement revision in the same series as the finding's original.
Broken dependencies block dependent checks. Finding-state checks occur after
relationship checks, without recursively treating intentional cross-references
as dependency cycles. Open findings may retain valid historical summaries.

Pending and closure claims must explicitly select a retest belonging to that
finding, with valid relationships and a replacement on the highest declared
revision in its series. That maximum includes untested submissions and is a
defined ordinal rule, not an inference from array order or actual chronology.
Pending requires `not_run`; closure requires `not_observed`. These are supplied
labels. Consistency never proves testing, a fix, current installed identity,
authorization, isolation or evidence quality.

Results contain declared record IDs, kinds, fixed status/evidence and counts.
Unknown reference values, series labels, revisions, raw states/outcomes, paths
and native error text are omitted. IDs and outcomes can still disclose private
relationships. Keep real ledgers and stdout private. This is not anonymization,
a secret scanner or clearance to publish operator inputs.

Targets, ports, endpoints, people, narrative findings, payloads, filenames,
hashes, evidence/attachments/logs, authorization documents, source builds and
timestamps are outside the schema. There is no scanning, exploitation, target
execution, clock lookup, network probe, evidence-file ingestion, persistence,
approval UI, scoring or report-file writer. The CLI reads one explicitly
selected JSON control file and writes only to stdout.

## Bounds and validation

Input is limited to 64 KiB, each collection to 128 entries and the total to 256.
At least one submission is required; findings/retests can be empty. IDs and
links use neutral ASCII tokens; revisions are exact integers from 1 through
1,000,000,000. Exact key sets, duplicate-key/ID/pair checks and fixed enums reject
unsupported data rather than silently ignoring it.

The fictional suite covers referential integrity, same-series later revisions,
selected association/outcomes, stale selections, untested higher revisions,
historical retests, array-order independence, strict schemas/bounds, copied
inputs, redacted outputs, fixed errors and absence of target/network/process/
clock/mutation activity. The local Windows/Python 3.12.7 utility run discovered
44 methods: 42 passed and two unavailable native link operations were skipped.
The integrated collection run discovered 350 methods: 333 passed and 17 were
skipped, with no failures/errors. Skips are not passes.

Independent review passed 609 bounded fictional scenarios, including 500
generated ledgers checked against a separate consistency oracle and array-order
permutations. Thirty-two fictional CLI scenarios passed and shipped example
hashes remained unchanged. Ruff checks/formatting and 179 local document checks
passed. No actual targets, findings or evidence were used. The dedicated workflow runs on Windows and
Ubuntu with Python 3.12/3.13 and checks documentation/JSON syntax.

The control-file guard samples regular-file/single-link and file/ancestor
identities, with link/reparse checks before/after a bounded read. Use stable
trusted local files. This is not an atomic snapshot or hostile-filesystem
sandbox. Mapped/mounted storage can involve OS network I/O, and byte limits do
not interrupt blocked filesystem calls. Formatted reader errors suppress native
input detail while retaining Python source locations.

Selected original source, tests, documentation and fictional examples use MIT
with TheOutlandsDev attribution. No third-party implementation or runtime is
bundled. Private markers, audit output, source mappings, local evidence and
publication receipts stay outside the repository. Review covers this addition
and changed documentation, not held source families, unrelated imports, Git
history, release assets or the full private drive.

The exact 14-file publication set retains one conservative scanner finding:
an invented UNC path in a negative input test, required to fail before
filesystem access. It represents no discovered host or operational record.
The finding has a private file-hash-bound disposition. Scanner status remains
`REVIEW_REQUIRED`, with no detector disabled and zero unresolved findings after
review. There were no private-marker matches or scanner errors.
