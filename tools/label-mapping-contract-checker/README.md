# OUTLANDS | Label Mapping Contract Checker

Check explicit taxonomy changes and ambiguous record-level mappings without relabeling data. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and newly invented HVAC or game-development examples.

Run from this complete tool directory:

```text
python -B labels.py --input examples/input.json
python -B labels.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No private application, original prompts, real records, weights or accounts needed.

## Contract and interpretation

Library `labels.check(raw_json_bytes)`. Input exactly `{format,before,after,mappings}`,
format `outlands-label-mapping-v1`. Before/after are shared taxonomy contracts.
Their IDs must match and revisions cannot regress. Any label-set or nonidentity
mapping change requires a newer after revision, even if label names stay the same.

Mapping is exactly `{id,source,targets}` with 0..32 unique target label IDs. Every
old source label requires exactly one selected mapping, with all sources/targets
in their respective contracts. No implicit identity mapping, inferred rename or
latest mapping. Different mapping IDs for one source are ambiguous even if equal.
Missing/conflicting/rejected rows, references or version mismatches withhold the
whole assessment. Exact normalized snapshots under one ID count once.

Empty targets explicitly records retirement; one target is one_to_one; multiple
targets are a split. Reverse target groups with multiple sources are merges.
New after labels with no incoming mapping are reported as introduced_labels.
Valid splits/merges retain the complete assessment but return REVIEW_REQUIRED:
record-level rules are still needed; target lists do not choose where real records
belong. Explicit retirement/introduction or one-to-one changes may PASS as complete
mapping declarations, without authorizing deletion, migration or semantic equivalence.

The HVAC example explicitly maps filter-service to filter-check and retains two
other invented labels. The review example splits needs-review and creates a merge
at noise-check. Before/after pins hash normalized taxonomy contracts. The checker
never loads, modifies, relabels or discards data; records_relabelled and
retirement_authorized remain false. Label names and mappings are caller assertions.

## Shared declarations, CLI and privacy limits

IDs and labels match `[a-z][a-z0-9_-]{0,47}`. Taxonomy is exactly
`{id,revision,labels}`, with revision integer 1..1,000,000 and 1..32 unique labels,
normalized by sorting. There is no inferred label meaning. Every pin uses normalized
compact sorted-key escaped ASCII JSON plus LF, except input_sha256 which covers
the exact raw input bytes. Pins are consistency receipts, not signatures or truth.

Identity-snapshot lists (mappings, cases, cohort and predictions) have at most 1,000
rows. Identical normalized snapshots count once plus duplicate_rows. Conflicting groups withhold every member, including
repeated identical members within that group. Each record list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Other structured lists use their explicit schema bounds/uniqueness rules above.
Source references do not reclassify structurally accepted rows. Fixed diagnostics
use 1-based logical positions; row 0 denotes a cohort/contract issue. Rejected values
are omitted. No latest version, prediction, prompt or mapping is selected implicitly.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Integer fields reject booleans/numeric strings; decimal
values are accepted only in their stated string schemas. Output is escaped ASCII
JSON <=8 MiB. Malformed outer contracts, prompt/policy schemas and list bounds refuse
entirely. Valid scoped findings retain or withhold results as documented above.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage; no hostile-process filesystem sandbox or OS
quota. Default output is private stdout JSON. Optional --out takes an absolute fresh
report destination under an existing trusted external parent outside the source tree.
No overwrite, parent traversal or mkdir. Failed writes may retain partial/unconfirmed
output; inspect privately and choose a fresh path. Windows inherits parent ACLs without
a confidentiality guarantee. Shell redirection lacks --out protections. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption; errors omit supplied paths/values.

No network/provider/model calls, weights, corpus collection, database, live clock,
command execution, URI/include following, environment expansion or directory discovery.
Actual prompts, labels, scores, judgments, hashes and reports can be private. These
tools are not anonymizers, prompt-safety checks, rights checks or independent authority/
quality verifiers. Keep actual inputs/reports private. Only newly invented HVAC and
game-event fixtures are included. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
