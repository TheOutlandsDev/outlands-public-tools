# UI Interaction Scenario Comparator

Compare identical supplied submissions and interactions under two declared contract versions.

Python 3.12/3.13; standard library; independent MIT source tool.

```text
python -B scenarios.py --input examples/input.json
python -B scenarios.py --input examples/needs-review.json
```

Library entry: `scenarios.check(raw_json_bytes)`. Optional `--out` selects
an absolute fresh private report outside source under an existing trusted parent.

## Tool contract

Input exactly `{format,baseline_forms,candidate_forms,baseline_flows,candidate_flows,baseline_submissions,candidate_submissions,baseline_histories,candidate_histories}`; format `outlands-ui-interaction-scenarios-v1`. Each side compiles independently with exact references. Baseline histories are nonempty; candidate histories may be empty to expose lost coverage. See comparison rules below. PASS is selected-observation outcome equality with matching expectations, including equal expected-negative cases; it is not valid traffic, whole-UI compatibility or browser proof.


## Custom form schema

Form exactly `{id,revision,fields}`. There are 1..32 fields, unique nested IDs, sorted
by ID for normalization. Field exactly
`{id,type,required,minimum,maximum,min_length,max_length,choices,visible_when,required_when}`.
All keys are required; unsupported keys/defaults are refused. type is string, integer
or boolean; required is exact bool. Integer minimum/maximum are null or exact integers
within +/-10^12, ordered when both supplied; string-length rules are null and choices
empty. Boolean has all four limits null and choices empty. String numeric limits are
null; min_length/max_length are null or integers 0..256, ordered when both supplied.
String choices are 0..16 distinct strings <=256 code points within length limits,
normalized in lexical order. Empty choices means unrestricted within length limits.
No HTML input types, HTML constraint-validation conformance, regexes or scripts.

visible_when and required_when are lists of 0..8 exact `{field,equals}` conditions.
Each list has unique referenced field IDs and is normalized by field ID. Every target
must exist; equals must satisfy the target's exact scalar type and value rules.
Dependencies across both rule lists must form a DAG; unknown targets, self references
and cycles reject the whole form. Deterministic topological evaluation uses lexical
ties. Conditions use AND; a condition matches only a visible, present, valid parent
value with exactly equal type/value. Invalid, absent or hidden parents never activate
children, including through hidden ancestors. No user-defined expressions are run.

Empty visible_when means visible. A visible field is required when base required is
true OR a nonempty required_when list matches. Empty required_when adds no requirement.
A hidden field is never required, including when base required=true. Supplied hidden
values are refused as findings, never silently discarded. Submitted values have no
implicit defaults, trimming, case folding, coercion or string/Boolean conversion.

## Submissions and decisions

Submission exactly `{id,revision,form,form_revision,form_sha256,values,expected_valid}`.
values is a map of 0..32 symbolic field IDs to strings <=256 code points, exact integers
within +/-10^12 or booleans. Nested maps/lists, null scalar values and floats are
unsupported. Missing keys represent absence. Well-represented values of the wrong
declared scalar type are logical findings. expected_valid is null or exact bool.
Bind the complete normalized selected form with its ID, revision and SHA-256.

Decision states: valid, optional_absent, missing_required, hidden_absent,
hidden_value_refused, type_invalid, out_of_range, length_invalid, choice_invalid.
Validity requires only valid/optional_absent/hidden_absent states and zero unknown
keys. Unknown keys and raw submitted values are omitted from reports; counts remain.
Expected validity is a caller assertion, compared separately from actual validity.

## Flow and ordered history schema

Flow exactly `{id,revision,form,form_revision,form_sha256,states,initial_state,terminal_states,transitions}`.
states has 2..16 unique symbolic IDs. terminal_states is a nonempty proper subset;
initial_state is nonterminal. Both sets normalize lexically. transitions has 1..64
unique nested IDs, sorted by ID. Transition exactly
`{id,from,to,action,submission_requirement}`. State references must exist; terminal
states cannot have outgoing edges. (from,action) slots are unique; there is no guard
precedence or automatic choice. All states must be reachable from initial_state and
have a graph path to a terminal state, ignoring submission guards for that structural
test. Review/revision loops and self transitions are allowed; histories stay bounded.
submission_requirement is none, valid or invalid. This is a declared validation branch,
not a permission, identity or access-control rule. The flow binds an exact form snapshot.

History exactly `{id,revision,flow,flow_revision,flow_sha256,events,expected_valid}`.
events is an ordered list of 0..128 exact
`{sequence,action,from,to,submission,submission_revision,submission_sha256}` records.
sequence is an integer 1..128. A null submission requires both reference partners null;
otherwise an exact selected submission ID/revision/hash is mandatory. Every referenced
submission must bind the same form snapshot as the selected flow. Structural bad
references withhold the entire scope, including references in later invalid steps.

Assessment begins at initial_state and expects sequence 1,2,..., exact current from,
a declared (current,action), exact to and the declared submission guard. none forbids
an attached submission; valid/invalid require the corresponding recomputed submission
validity. No transition is executed. After the first invalid step, later steps are
UNASSESSED_AFTER_INVALID_STEP and state never advances. last_confirmed_state records
only the valid prefix. A history is valid only when every step validates and it ends
at a terminal state; an empty/partial history cannot invent completion. Failed expected
validity is separately review-required. History PASS does not certify submission validity,
actual approval, human review, browser activity, identity or permissions.

## Exact scenario comparison

Same form or flow ID/revision with changed normalized definition is a structural
identity conflict. Declare a new revision for definition changes. Compare complete
selected submission cohorts, including unused submissions, by exact typed canonical
content; only form_revision/form_sha256 may differ to bind selected contract versions.
They are still verified on each side. Different values, expectations, IDs, revisions,
form IDs or missing/added submissions are scope changes, not equal observations.
Boolean true and integer 1 are distinct observations.

Pair histories by ID; exact identity/revision/flow ID, expected validity and ordered
events must match. Only flow_revision/flow_sha256 and event submission_sha256 may differ
for verified version binding. Event submission ID/revision must still be identical.
Missing/added histories, changed interactions and any changed submission cohort produce
incomparable history rows with null outcome details. Missing references are structural
findings, not guessed repairs. No candidate case disappears silently.

Comparable submissions compare full sanitized decisions, including visibility and
requiredness even if validity is unchanged. Histories compare sanitized ordered outcomes,
last confirmed state, terminal reachability and outcomes of referenced submissions.
Changed unused submission outcomes still require review globally. Failed expectations
require review even when both outcomes are equal. Equal expected-negative cases can
PASS comparison without valid submissions or valid histories. Matching declared cases
does not establish whole-UI compatibility or behavior for untested cases.

## Accounting, limits and privacy boundary

Each identity cohort has <=1,000 raw rows, with tighter caps of 64 forms, 64 flows
and 256 histories per side. Identical normalized top-level identities count once;
conflicting groups exclude every member. Accepted/duplicate/conflict/rejected accounting
is complete. Duplicate nested fields/transitions reject their entire parent even when
identical; malformed nested events likewise reject the history. Forms and flows are
complete declarations, not original app schemas. IDs match `[a-z][a-z0-9_-]{0,47}`;
revisions are integers 1..1,000,000; hashes are 64 lowercase hexadecimal characters.

Each side has <=8,192 selected field assessments and <=4,096 selected history events.
Scenario comparison additionally caps combined field assessments at 8,192. Larger
scopes are fixed refusals, never samples or truncation. Form/flow/submission fingerprints
and form dependency orders are cached per selected cohort. No automatic latest selection.
Structural findings withhold all assessments and cohort/scope pins; logical findings
retain sanitized diagnostics and cohort pins, but no qualified scope.

Normalize before binding snapshots. Cohorts hash normalized records sorted by ID;
canonical bytes are sorted-key compact escaped ASCII JSON plus LF. Fields, conditions,
choices, state sets and transitions normalize; event order remains significant.
input_sha256 binds raw bytes separately. qualified_scope_sha256 exists only without
findings. Hashes are consistency receipts, not signatures, authentication or anonymization.
Reports expose declared IDs and hashes; low-entropy values may be guessed. Actual
inputs/reports remain private. These tools do not sanitize or detect all private data.

No HTML/CSS/DOM inspection, rendering, browser startup, scripts, network requests,
authentication, permissions changes, live form submissions, application writes or model
calls. browser_started, dom_inspected, scripts_executed, network_requests_performed,
authentication_performed, records_changed, raw_values_emitted, accessibility_verified,
whole_ui_compatibility_verified and target_changes_performed remain false. Raw values
means submitted scalars/condition literals, not bounded declared IDs or hashes. These
custom models do not establish HTML/browser conformance, accessibility, security,
privacy, rights or production readiness. Live browser validation remains separate.

One explicit JSON input <=4 MiB; strict parsing rejects duplicate keys, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 or integers outside
+/-10^18. Escaped ASCII report <=8 MiB. Default stdout JSON; --out requires an absolute
fresh external filename under an existing trusted parent outside source. No overwrite,
mkdir or traversal. Ordinary single-link inputs and trusted quiescent storage required.
[Windows/POSIX I/O protections](IO-SAFETY.md) retain POSIX parent descriptors/no-follow
checks and native Windows reparse/hardlink/change checks. They do not sandbox hostile
concurrent writers or guarantee inherited parent ACL confidentiality. Failed writes may
leave partial/unconfirmed output: inspect privately and choose a fresh name. Shell
redirection lacks these output guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal,
130 interruption; fixed errors omit supplied values/paths.

Each complete directory uses Python 3.12/3.13 standard library without sibling runtime
imports. Fresh generic code and invented HVAC/video-game/AI/software examples only.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
