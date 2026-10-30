# OUTLANDS | Fallback Chain Contract Checker

Check explicit bounded fallback ordering, failure conditions and attempt limits without choosing models or dispatching requests. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and plan-only.

Run from this complete tool directory:

```text
python -B fallbacks.py --input examples/input.json
python -B fallbacks.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No private program, prompt, payload, model, provider, account or credentials needed.

## Contract and interpretation

Library `fallbacks.check(raw_json_bytes)`. Input exactly `{format,models,request,policy,
chain}`, format `outlands-fallback-chain-v1`. Models, the single request and policy use
the shared schemas. Malformed single-request/policy/chain headers are fixed refusals.

Chain is exactly `{id,revision,request_sha256,policy_sha256,start,maximum_attempts,steps}`.
Its two pins must match the actual normalized request and policy. Maximum_attempts is
integer 1..32. Steps is at most 32 raw rows and must select at least one step. Each row
is `{id,model,model_revision,model_sha256,next_step,on_failures}`. Model/revision/pin must
match the actual selected catalog. Next_step is a declared step ID or null. On_failures
is a unique sorted subset of timeout/unavailable/rate-limited/invalid-output. It must be
nonempty exactly when next_step is nonnull; terminal steps have no transition conditions.

Follow explicit next_step pointers from start. Unknown references, cycles, unreachable
steps, conflicting/rejected rows, inconsistent models or scope pins withhold the whole
assessment and all qualified pins. List order is not execution order. No unreachable
nodes are pruned, duplicate identities do not add attempts and no latest step is chosen.

For qualified structure, check every step's model eligibility against the same request
and policy using the routing criteria. The complete chain length must fit the declared
attempt cap. Repeating a model in distinct steps is a MODEL_REPEATED_IN_CHAIN review
finding, not an implicit retry. Any such criterion failure retains all ordered steps
and declared scope pins but makes plan_sha256 null. A cap never truncates the plan.

Only complete eligible plans receive plan_sha256 = hash of `{models_sha256,
request_sha256,policy_sha256,chain_sha256}`. Chain_sha256 hashes its full normalized
object with deduplicated selected steps sorted by ID and failure classes sorted;
pointers preserve actual ordering. One step means at most one declared attempt. Extra
cap headroom does not authorize repeated steps or execution. No dispatch, provider
health checks, sleeping/backoff, credentials, endpoints or model loading.

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
