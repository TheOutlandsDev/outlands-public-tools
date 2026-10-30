# OUTLANDS | Regression Comparison Reporter

Compare compatible declared baseline/candidate results while retaining gaps and contract changes. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B regressions.py --input examples/input.json
python -B regressions.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `regressions.check(raw_json_bytes)`.

## Contract

Input exactly `{format,baseline,candidate}`, format `outlands-regression-comparison-v1`.
Both sides are full selected run bundles, without a format field. Each must have a
nonempty case cohort and valid exact bindings. Run IDs must differ; reusing a run ID
with any revision is refused as an ambiguous comparison scope. Subject hashes may
differ: they are opaque declarations of baseline/candidate subjects, never opened.
Structural errors on either side withhold the entire comparison and both sides' pins.

Compare the union of case IDs. Cases only in candidate are added; only in baseline are
removed. A shared ID with a different full normalized case pin is incomparable_contract,
including definition, input, expectation or revision changes. There is no alias mapping
or automatic compatibility claim. Equal case pins with missing/noncompleted/incomplete
observations or missing expectation contracts are incomplete_comparison.

For compatible complete observations, exact expected-result matches classify as:
true/true unchanged_match; true/false regression; false/true improvement; false/false
persisting_mismatch. Changes between two mismatches do not imply improvement. The
report retains both per-case observations and classification counts. Only unchanged_match
and improvement avoid review; added/removed/incomparable/incomplete/regression/persisting
mismatch cases withhold qualified_scope_sha256 but retain diagnostics and full pins.
PASS means no declared regressions or gaps under these rules, not both runs passed,
authenticated execution, performance significance or candidate release authorization.

## Shared declarations and limits

Case exactly `{id,revision,definition_sha256,input_sha256,expectation_sha256}`.
Definition/input hashes are opaque metadata, not source or input content. Expectation
exactly `{id,case,case_revision,case_sha256,expected_exit,stdout_sha256,stderr_sha256}`.
Expected_exit is integer 0..255. Derive expectation_sha256 from the normalized object
`{exit_code: expected_exit, stdout_sha256, stderr_sha256}`. Then case_sha256 pins the
entire normalized case. This dependency order avoids circular hashes. Hash equality
checks byte declarations only; no expected stdout/stderr content is supplied or read.

A selected run bundle exactly `{cases,expectations,run,results}`. Run exactly
`{id,revision,subject_sha256,cases_sha256,expectations_sha256}`. Both cohort pins must
match the actual full normalized cohorts. Result exactly `{id,run,run_revision,
run_sha256,case,case_revision,case_sha256,state,observed_exit,stdout_sha256,
stderr_sha256,output_complete}`. Cases must be nonempty; expectations/results may be
empty. Every result binds the selected full run and exact case. Different result IDs
for one case are ambiguous; duplicate normalized rows with the same ID count once.

State is completed, timeout, cancelled, refused, not-run, output-limited or unknown.
Completed requires observed_exit integer -128..255, two declared hashes and a boolean
output_complete. A completed false-completeness declaration remains incomplete, even
with matching hashes. Every noncompleted state requires null observed_exit/stdout/stderr
and output_complete false; partial captures are outside this narrow schema. Unknown
or impossible combinations are rejected rows. No pass/fail flag is trusted from input.

IDs everywhere match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000.
Booleans are never integers. All hashes are exactly 64 lowercase hexadecimal characters.
Every schema is exact: all fields required, no unknown fields or inferred defaults.
Each identity list has <=1,000 raw rows. Identical normalized snapshots for one ID count
once; conflicting groups exclude every member. Complete accounting per list is input_rows
= accepted_records + duplicate_rows + conflict_rows + rejected_rows. Malformed row
diagnostics use side/row/fixed code without echoing rejected values. Structural errors
withhold the entire assessment and cohort pins; logical findings retain diagnostics as
documented. Malformed outer schemas, run headers, policies and list bounds are fixed errors.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Cohorts hash normalized selected
records sorted by ID. input_sha256 hashes exact raw input bytes. Qualified_scope_sha256
binds the report format and every named cohort/run/policy pin in the report. Reports are
consistency receipts, not signatures, authenticated test execution, artifact verification,
actual coverage, privacy or rights. Reports expose supplied opaque IDs/hashes: keep real
inputs/reports private. These tools do not anonymize records or prove that fixtures are safe.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid Unicode,
depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18 are refused.
Output is escaped ASCII JSON <=8 MiB. Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md)
require ordinary single-link inputs and trusted quiescent storage. Default output is
stdout JSON; --out requires an absolute fresh destination under an existing trusted
external parent outside source. No overwrite, parent traversal or mkdir. Failed writes
may retain partial/unconfirmed output; inspect privately and choose a fresh path.
Windows inherits parent ACLs without a confidentiality guarantee. Shell redirection
lacks these guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption.
Errors omit supplied paths/values. Guards do not sandbox hostile concurrent processes.

No test/source execution, script imports, subprocesses, live collectors, discovery,
clock, URI/include following, environment expansion, file/artifact dereferencing,
database/provider access, automatic retries, approvals, exports or target changes.
Independent directories have no sibling runtime imports. Only invented HVAC/game
metadata is included. Original private implementations, cases, results, records,
policies, paths, credentials and opsec details were not consulted or selected.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
