# OUTLANDS | Request Routing Plan Checker

Check exact proposed request/model assignments against pinned capability declarations and caller-supplied rules without dispatch. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and plan-only.

Run from this complete tool directory:

```text
python -B routes.py --input examples/input.json
python -B routes.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No private program, prompt, payload, model, provider, account or credentials needed.

## Contract and interpretation

Library `routes.check(raw_json_bytes)`. Input exactly `{format,models,requests,policy,
proposals}`, format `outlands-request-routing-v1`. Models, requests and policy use the
shared schemas below. All three identity lists are nonempty. Proposed assignments are
exactly `{id,request,request_revision,request_sha256,model,model_revision,model_sha256,
policy_sha256}`. Every selected request needs exactly one proposed assignment. Different
proposal IDs for one request are ambiguous even when equal; missing requests are not
implicit abstentions. Model/request pins hash complete normalized rows, including
request prompt/input hashes and budgets. All references/revisions/pins must match.

Invalid/conflicting rows, coverage/slot ambiguity, unknown/stale references, inconsistent
model declarations or unknown policy model references withhold the complete assessment
and all qualified scope pins. All models are checked, including unused declarations.
Malformed policy schema is a fixed refusal. There is no auto-selection, ranking,
default model, implicit policy or inferred supported modality.

For qualified scope, evaluate every explicit proposal against: model permitted by policy;
task/input/output types supported by the model and permitted by policy; input and output
budget under their separate model and policy maxima; input_units+output_budget within
both model context_units and policy max_total_units. Equality passes. Zero declared
input units are allowed; output budget is positive. Units are supplied generic counts,
not independently measured tokens, bytes, cost or latency.

Criterion failures return REVIEW_REQUIRED with all per-proposal diagnostics and scope
pins retained, but route_plan_sha256 null. Only if all proposals pass is eligibility
for manual routing review true and route_plan_sha256 issued: it hashes the object
`{models_sha256,requests_sha256,policy_sha256,proposals_sha256}`. These collection pins
cover full normalized rows sorted by ID. A routing plan pin differs intentionally from
the separate fallback plan pin. No request payload, prompt body, provider call or output
content is read or sent. The game-routing.json example uses an invented NPC request.

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
