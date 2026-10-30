# OUTLANDS | Prompt Contract Diff

Compare declared prompt messages, variables and output interfaces without rendering prompts or calling a model. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and newly invented HVAC or game-development examples.

Run from this complete tool directory:

```text
python -B prompts.py --input examples/input.json
python -B prompts.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No private application, original prompts, real records, weights or accounts needed.

## Contract and interpretation

Library `prompts.check(raw_json_bytes)`. Input exactly `{format,before,after}`,
format `outlands-prompt-contract-diff-v1`. Each contract is exactly
`{id,revision,messages,variables,output_contract}`; revision integer 1..1,000,000.
IDs must match and revisions cannot regress. Content changes require a newer prompt
revision. A top-level version-only increase with identical normalized payload is
PASS with version_only=true; valid semantic changes return REVIEW_REQUIRED and
retain qualified changes. Identity/version violations withhold changes.

Messages has 1..16 exact `{id,role,template}` rows with unique IDs and meaningful
list order. Role is system, user or assistant. Template is literal text <=4,096
characters. Only `{{lowercase_id}}` double-brace placeholders are recognized;
malformed double-brace constructs are refused. Variables is 0..32 unique IDs;
its set must exactly equal all placeholders used across messages. Repeated uses
are allowed. No values are supplied, rendered, evaluated or expanded.

Output_contract is exactly `{taxonomy,fields}`. Taxonomy is the shared label
contract below. Fields has 1..16 exact `{id,type,required}` entries with unique
IDs, type label/text/integer/boolean, and actual boolean required. Exactly one
label field is required and must be required=true. Field order is normalized;
message order and literal whitespace are not. No arbitrary JSON Schema, remote
references, tools/functions, nested types or actual response validation.

Selected taxonomy IDs must match across versions; its revision cannot regress and
changed label sets require its own revision increase. A changed taxonomy revision
also changes the prompt payload. Reports include normalized before/after pins,
taxonomy pins, message/order-change flags, variable additions/removals and output
field additions/removals/changes. Literal prompt bodies are omitted from reports.
Pins hash the complete normalized contract with sorted keys, compact ASCII JSON
plus LF; only fields/variables/labels normalize ordering, not messages.

The positive example compares an invented HVAC classifier contract with itself;
the review example changes its request wording and renames an invented label with
proper revisions. This is syntax/interface comparison, not semantic behavior,
instruction safety, privacy clearance or proof of a model obeying the contract.

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
