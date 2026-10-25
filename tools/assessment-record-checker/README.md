# Offline Assessment Record Contract Checker

Check references, declared revisions and workflow consistency in an explicitly
selected JSON ledger. Python 3.12+, standard library only. The checker reads one
bounded file and writes JSON to stdout. It does not execute a test, contact a
target, collect evidence, modify records, create a database or create report
files.

This checks the consistency of operator-supplied records. A passing closure
claim does not prove a fix, a performed retest, authorization, isolation or
security. An open finding can be represented consistently. No outcome is
independently verified.

## Fictional examples

Run from the collection root:

```text
python -B tools/assessment-record-checker/assessment_check.py --records tools/assessment-record-checker/examples/consistent-records.json
```

Expected exit: **0**, `DECLARED_RECORDS_CONSISTENT`, with nine `PASS` checks:
three submissions, three findings and three retests. One finding is open,
another has a pending retest, and a third records a closure claim. Their records
are internally consistent; this does not establish that any vulnerability was
tested or resolved. The unrelated series has a higher revision number without
making selections in the first series stale.

```text
python -B tools/assessment-record-checker/assessment_check.py --records tools/assessment-record-checker/examples/inconsistent-records.json
```

Expected exit: **1**, `REVIEW_REQUIRED`, with five `PASS` and two `FAIL` checks.
One finding selects a retest against an older declared revision; the other
declares a pending retest whose outcome is already `still_present`.

```text
python -B tools/assessment-record-checker/assessment_check.py --records tools/assessment-record-checker/examples/blocked-records.json
```

Expected exit: **1**, `REVIEW_REQUIRED`, with two `PASS` and three `BLOCKED`
checks. A missing original submission blocks a finding and its retest. Another
finding cannot resolve its selected retest. Missing dependencies cannot become
passing closure claims.

All examples are newly authored fictional records. They include no actual
targets, findings, evidence, reviewers or source builds.

## Ledger format

The UTF-8 JSON root has exactly `schema_version`, `submissions`, `findings`
and `retests`. The schema version is the integer `1`. Declare 1 to 128
submissions, 0 to 128 findings and 0 to 128 retests, with at most 256 records
combined. Empty finding/retest lists are allowed.

Each record has exactly its listed fields:

| Collection | Fields |
| --- | --- |
| `submissions` | `id`, `series_id`, `revision` |
| `findings` | `id`, `submission_id`, `state`, `selected_retest_id` |
| `retests` | `id`, `finding_id`, `submission_id`, `outcome` |

Entity IDs are globally unique across the three collections. IDs, references
and series labels start with a lowercase ASCII letter, followed by lowercase
letters, digits, underscores or hyphens, at most 40 characters total. Series
labels use a separate namespace; repeated labels group submissions. Revisions
are actual JSON integers from 1 to 1000000000; booleans, strings and floats are
refused. Each `(series_id, revision)` pair is unique.

Finding state is exactly `open`, `retest_pending` or `closure_claimed`.
`selected_retest_id` is either null or a syntactically valid ID. Retest outcome
is exactly `not_run`, `still_present`, `not_observed` or `inconclusive`. A ledger
contains at most one retest summary per `(finding_id, submission_id)` pair.
This is a summary contract, not an execution-history store.

Unknown fields, duplicate JSON keys, duplicate record IDs, duplicate
series/revision or retest-summary pairs, wrong types and nonstandard JSON
numeric constants are refused as invalid inputs. Nothing is coerced, expanded
or inferred from filenames or array position.

## Relationship and workflow rules

Every finding references its original submission. Every retest references a
finding and a replacement submission. The original and replacement submissions
must exist, share the same series label, and have strictly increasing declared
revisions. Same-revision retests and cross-series replacements fail this
relationship check. Every historical retest is checked, including unselected
ones.

Workflow rules are:

- `open` requires a null selected retest. Historical outcomes can remain in the
  ledger without forcing closure.
- `retest_pending` requires an explicit valid selected retest for that finding
  with outcome `not_run`.
- `closure_claimed` requires an explicit valid selected retest for that finding
  with outcome `not_observed`.
- Both pending and closure selections must target the highest **declared
  integer revision in the original series**, not just a later revision. A newer
  declared submission makes a selection against an older revision stale even
  if the newer submission has no retest record.

The highest revision is computed only from supplied records. It does not
establish the actual current build, chronology, source identity or latest test
execution. `not_observed` is a declared outcome, not proof of absence or a fix.

Missing references and invalid dependencies produce `BLOCKED`. Direct semantic
mismatches produce `FAIL`. Broken dependencies do not silently pass workflow
checks. A retest's relationship is evaluated from the finding's original
submission link, so a finding's state result does not create a circular
dependency with its selected retest.

## Results and privacy

Checks contain only `id`, `kind` (`submission`, `finding` or `retest`), `status`
(`PASS`, `FAIL` or `BLOCKED`) and a fixed evidence code. Output follows the
submission list, then the finding list, then the retest list, preserving each
list's declaration order. Referenced IDs, series labels, revision values, raw
states/outcomes, input paths and native errors are not echoed as result fields.
Only each checked record's own ID is copied.

Counts are `passed`, `failed`, `blocked`, `submissions`, `findings` and `retests`.
The scope is `DECLARED_ASSESSMENT_RECORDS_ONLY`. Flags `execution_performed`,
`network_probed`, `records_modified`, `authorization_verified`,
`isolation_verified` and `outcomes_verified` are always false. Exit `0` means
`DECLARED_RECORDS_CONSISTENT`, exit `1` means `REVIEW_REQUIRED`, and exit `2`
means `ERROR` for invalid inputs or arguments. Interruption returns `130`.
Consistency can coexist with open findings, missing runtime evidence or an
unperformed assessment.

Record IDs and result codes can still disclose a project or workflow. Keep real
ledgers and stdout private. This is not an anonymizer, secret scanner, evidence
clearance or approval to publish assessment records. Use the
[private workspace guide](../../docs/PRIVATE-WORKSPACE.md) for your own inputs,
and keep actual records outside the checkout.

Targets, endpoints, people/reviewer identities, narrative findings, reproduction
steps, hashes, filenames/paths, source builds, timestamps, evidence files,
authorization documents, commands and scoring are outside this schema. No
attachments are read. The tool neither enforces target isolation nor grants
authorization to test.

## Filesystem and validation limits

The selected input is limited to 64 KiB and must be a regular single-link file
with verifiable file and ancestor identities. Paths are limited to 4,096
characters and 64 parts; traversal, UNC paths, drive-relative paths and unsafe
stream/device forms are refused. Symlink/reparse paths, special nodes and
detected metadata changes are refused. These checks do not freeze a tree or
create an atomic or hostile-filesystem boundary. Use stable trusted local
storage. Although no socket/DNS probe is performed, reading a ledger on mapped
drives or mounted shares can involve the operating system's network storage
stack. Remote storage, arbitrary mounts and concurrent writers are not proven
safe. The size bound cannot interrupt a blocked filesystem operation.

The CLI accepts `--records FILE`, `--help` and `--version`; there is no report-file
option. Examples use Python's `-B` option to avoid generating bytecode files.

## Provenance and licensing

This is a fresh neutral implementation with fictional records and a reviewed
public input-reader pattern. No held assessment application, private schema,
operational record, evidence file or original application source is read or
copied. The private assessment application remains outside this public tool's
review scope. Selected original source and examples use the repository's
[MIT license](../../LICENSE), attributed to TheOutlandsDev; operator inputs and
third-party material are not relicensed.

See the [batch review](../../docs/BATCH-12-ASSESSMENT-RECORDS.md) for actual
validation results and remaining limits. CI targets Windows and Ubuntu with
Python 3.12 and 3.13. See also the [security assessment template](../../methodology/security-assessment.md)
and [Diagnostic Evidence Plan](../../methodology/diagnostic-evidence-plan.md)
for private recordkeeping boundaries.
