# OUTLANDS | Inference Receipt Reconciler

Reconcile declared attempts and results against a recomputed pinned fallback plan without inference or proof that inference occurred. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and plan-only.

Run from this complete tool directory:

```text
python -B receipts.py --input examples/input.json
python -B receipts.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No private program, prompt, payload, model, provider, account or credentials needed.

## Contract and interpretation

Library `receipts.check(raw_json_bytes)`. Input exactly `{format,models,request,policy,
chain,attempts,result}`, format `outlands-inference-receipts-v1`. Recompute and require
an eligible fallback plan using the actual embedded declarations and the exact rules
above. Ineligible/invalid plans withhold receipt assessment. A structurally qualified
but ineligible plan retains its plan_assessment findings and has no plan pin.

Attempt rows are exactly `{id,ordinal,step,model,model_revision,model_sha256,
request_sha256,plan_sha256,status,failure_class,output_sha256,output_units}`. Ordinal is
integer 1..32. Request and plan pins must match the recomputed scopes; step and complete
model binding must match that exact chain step. Different IDs sharing an ordinal are
ambiguous even if otherwise equal. Rows may be supplied out of order; ordinals govern.

Status is succeeded/failed/unknown. Succeeded requires null failure_class, a valid
declared output hash and integer output_units 0..1,000,000,000. Failed requires one
of the four supported failure classes and null output hash/units. Unknown requires
null failure class/output hash/output units. These are receipt assertions, not verified
provider facts. An output hash is never opened or authenticated.

Require contiguous ordinals starting at 1, attempt count under the chain cap and first
step equal to start. Each later attempt must be the preceding step's explicit next_step,
with the preceding status failed and its failure class explicitly permitted by that
transition. No attempt after success or uncertainty. Invalid rows, binding/ordinal/
transition issues withhold the complete receipt assessment and attempts_sha256.
The independently checked plan assessment and pins remain visible where valid.

For structurally reconciled attempts, derive terminal status from the last receipt.
A last failed receipt with a permitted unrecorded fallback means unknown, with
FALLBACK_RECEIPT_MISSING. No attempts or an unknown terminal receipt also requires review.
A terminal failed outcome with no permitted next transition can PASS consistency;
it is not renamed success. Early success needs no later fallback receipts.

Result is exactly `{status,attempts,final_attempt,output_sha256}`. Status has the same
three values, attempts is integer 0..32, final_attempt is an ID or null. Succeeded
requires a nonnull final ID and output hash; other statuses require null output hash.
Compare every declaration against observed terminal status, selected attempt count,
last attempt ID and last succeeded output hash. Mismatches, uncertainty or output_units
over the request's declared output_budget return REVIEW_REQUIRED with computed summary
retained. A policy-excess success receipt remains labeled observed succeeded but is
ineligible for manual receipt review; no content correctness is inferred.

Report ordered IDs, count, observed terminal status, last ID/output pin, all failed
criteria and manual-review eligibility. attempts_sha256 hashes full normalized selected
receipt rows sorted by ID, not raw list order. No inference is performed and receipt
consistency never proves occurrence, output truth, authentic delivery or execution rights.

## Shared schemas, bounds and privacy

IDs match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000. SHA-256 strings
are exactly 64 lowercase hexadecimal characters. Hashes are declarations/consistency
receipts, not signatures or authenticated artifact bytes. Tasks and input/output type
names are caller-defined IDs; even a name such as label-json does not validate content.

Model is `{id,revision,tasks,input_types,output_types,max_input_units,max_output_units,
context_units}`. Each capability list has 1..32 unique IDs normalized by sorting.
All three limits are integers 1..1,000,000,000.

Request is `{id,revision,task,input_type,output_type,input_sha256,prompt_sha256,
input_units,output_budget}`. Input_units is integer 0..1,000,000,000; output_budget is
integer 1..1,000,000,000. No payload, prompt text, URI, file path or credentials.

Policy is `{id,revision,allowed_models,allowed_tasks,allowed_input_types,
allowed_output_types,max_input_units,max_output_units,max_total_units}`. Each allowed
list has 1..32 unique IDs normalized by sorting; allowed_models must reference the
selected catalog. Limits are integers 1..1,000,000,000. All units are declared generic
counts in an assumed common convention, not tokenization, pricing, throughput or time.

Identity lists have at most 1,000 rows, except steps at most 32 raw rows. Identical
normalized snapshots under one ID count once plus duplicate_rows. Conflicting groups
withhold every member, including repeated identical members in the conflict. Each list
satisfies `input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Semantic slot/coverage issues are separate from structural row counts. Fixed diagnostics
use one-based logical positions, with row 0 for a cohort issue; rejected values are
omitted. No implicit latest revision, proposal, step, retry or result selection.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Collections sort by ID and
declared capability/allowed/failure sets sort lexically. Explicit pointers/ordinals
preserve ordering. input_sha256 in the report hashes exact raw input bytes; the nested
request input_sha256 is an unverified supplied payload pin.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Integers reject booleans/coercion. Output is escaped ASCII
JSON <=8 MiB. Malformed outer schemas, headers and list bounds are fixed refusals;
malformed identity rows return REVIEW_REQUIRED with qualified results withheld.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default output is private stdout JSON. Optional
--out takes an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output: inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths/values. These guards do not sandbox hostile concurrent processes.

No network/provider/model calls, provider selection, payload/prompt reading, weights,
hardware probes, credentials, endpoints, clock, backoff, command execution, URI/include
following, environment expansion or target updates. Only invented HVAC/game metadata.
Keep actual inputs/reports private. These tools do not anonymize data, authenticate
receipts, measure capabilities/units, verify outputs or grant dispatch/publication rights.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
