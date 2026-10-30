# OUTLANDS | Access Decision Evaluator

Reproduce literal allow/deny decisions for supplied symbolic requests with default deny and deny precedence. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/video-game/AI/software declarations; offline and advisory.

From this complete tool directory:

```text
python -B decisions.py --input examples/input.json
python -B decisions.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `decisions.check(raw_json_bytes)`.

## Contract

Input exactly `{format,policy,requests}`; format `outlands-access-decisions-v1`.
Requests are `{id,revision,actor,action,resource,expected}`. expected is allow, deny or
null; all fields are required. The request cohort must be nonempty. Action/resource
IDs must exist in the selected policy. Unknown actions/resources withhold the entire
assessment instead of producing an apparently safe default denial. An actor without
a selected assignment has no declared roles in this closed-world model and defaults
to deny; no real identity/assignment lookup or completeness claim is made.

For each request, match literal action/resource rules whose roles occur in the actor's
effective roles. Any matching deny wins over every allow, including inherited rules.
Otherwise a matching allow gives allow; no match gives default_deny. All matching
allow/deny rule IDs remain visible, with assignment_present and reason explicit_deny,
explicit_allow or default_deny. List order never controls precedence. No wildcard,
pattern, group discovery, attribute expression, time condition or implicit administrator.

The assessment includes decision/reason and expectation_met (null when expected is
null). A mismatch is REVIEW_REQUIRED with assessment/pins retained and no qualified
scope. A deny matching the declared expectation can PASS: status describes consistency
with this limited input contract, not approval to perform an action. Unrequested cases
and request completeness remain unverified. policy_sha256 and requests_sha256 bind
normalized declarations. Identity, credentials and real permissions are never verified.

## Shared policy, limits and interpretation

Policy exactly `{id,revision,roles,actions,resources,assignments,rules}`. All fields
required. Role rows `{id,inherits}` have 0..32 distinct parent IDs. Action/resource rows
are `{id}` only, with no values or paths. Assignment rows `{id,actor,roles}` contain
0..32 distinct role IDs; one identity per actor. Rule rows
`{id,role,action,resource,effect}` bind known role/action/resource IDs with effect allow
or deny. One rule identity per triple; equal-effect aliases and opposing-effect aliases
are both structural ambiguity. Allow/deny precedence across different matching roles
is explicit in the evaluator, not a repair of conflicting rule identities.

IDs match `[a-z][a-z0-9_-]{0,47}`, revisions are integers 1..1,000,000, SHA-256 values
are 64 lowercase hex. Booleans never substitute for integers. Every identity list has
<=1,000 raw rows. Identical normalized IDs count once; conflicting payload groups
exclude every member. ID-only declarations have no valid distinct payload; unknown
fields are rejected rows. Accounting always records accepted, duplicate, conflict and
rejected rows. No latest/best selection or silently omitted invalid records.

Inheritance is resolved iteratively, with <=16,384 total self-plus-ancestor role
memberships across the policy, and <=16,384 total effective actor-role memberships.
Each evaluator/comparison side permits selected requests * selected rules <=50,000.
Duty scope permits role constraints * declared actors + workflow constraints *
max(1,selected events) <=20,000. Larger scopes are fixed refusals, not sampled or
truncated results. These bounds complement the parser and output-size limits.

Normalize all policy cohorts by ID and set-like inherits/roles by sorting. Policies
must be normalized before their full snapshot hash is used in events. Workflow action
pairs normalize ascending; role pairs sort. Cohort pins hash selected rows sorted by ID.
All declaration pins use sorted-key compact escaped ASCII JSON plus a trailing LF.
input_sha256 hashes the exact input bytes. qualified_scope_sha256 is present only with
no findings. Structural ambiguity withholds the entire assessment and scope pins;
logical findings retain diagnostics/pins. Fixed outer-schema/parser/size/expansion
refusals return errors. Pins are consistency receipts, not signatures or capabilities.

Actors, assignments, resources and events are unverified caller declarations. No
authentication, credential parsing, user lookup, directory discovery, signatures,
permission enforcement, grant/revoke operations, real action history, API probing,
commands or target/database/account changes occur. identity_authenticated,
authorization_verified, access_enforced, permissions_changed, accounts_changed,
network_accessed, actions_executed, records_changed and target_changes_performed are
false. No real security certification, production suitability, privacy, rights,
complete history or authority is established by PASS. Overall REVIEW_REQUIRED remains
visible even when individual answers are unchanged or some claims are consistent.

Reports expose supplied symbolic actor/role/resource IDs, rule IDs, event IDs and
hashes. Keep actual inputs/reports private. Hashes do not anonymize/encrypt data and
low-entropy declarations can be guessed. These are not sanitizers or secret scanners.

One explicit JSON input <=4 MiB. Strict parsing rejects duplicate keys, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18. Escaped ASCII output <=8 MiB. Default stdout JSON; --out requires an absolute
fresh external file under an existing trusted parent outside source. No overwrite,
traversal or mkdir. Ordinary single-link inputs and trusted quiescent storage required.
The [public Windows/POSIX I/O guards](IO-SAFETY.md) preserve POSIX parent descriptors/
no-follow checks and native Windows reparse/hardlink/change checks. They do not sandbox
hostile concurrent writers or guarantee inherited ACL confidentiality. Failed writes
can leave partial/unconfirmed output: inspect privately and choose a fresh filename.
Shell redirection lacks these output guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed
refusal, 130 interruption. Errors omit supplied values/paths.

Independent standard-library directories have no sibling runtime imports. Only fresh
generic policy logic, fictional HVAC/video-game/AI/software declarations and reviewed
public MIT helpers are included. Original private implementations, schemas, policies,
records, identities, paths, credentials, endpoints and deployment details were not
consulted or selected. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
