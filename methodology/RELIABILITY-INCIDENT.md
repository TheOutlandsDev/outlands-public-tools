# Reliability and incident methodology

These offline checkers compare supplied declarations. Their terms describe the
selected records, rather than measurements of a running service.

| Term | Plain-language meaning | Technical meaning here |
| --- | --- | --- |
| Component snapshot | The exact component contract being reviewed | An ID/revision and maximum_age; references pin its complete normalized JSON. |
| Observation | A supplied claim about component state | An exact component reference, declared state and observed_at ordinal. No probe runs. |
| Ordinal and as-of | A caller-selected order/time scale and decision point | Explicit bounded integers. They are not collected clock values or automatically parsed UTC timestamps. |
| Freshness | A claim falls within the allowed age | At or before as_of, age=as_of-observed_at and age<=maximum_age. Equality is fresh; future observations are not fresh. |
| Incident timeline | An ordered account of incident actions | Exact incident pins, contiguous ordinals, nondecreasing at values and valid state transitions. The entire history is checked, including future events. |
| Resolution | The declared incident state is resolved at the chosen point | Replay of valid events through as_of. Timeline PASS can still describe an open or acknowledged incident. |
| Correlation key | The caller's label for related alerts | An opaque ID partitioned with component ID, not a key inferred from alert text. |
| Anchored window | A group starts at its first alert | Include alerts through anchor+window; the end never slides. Times 0,10,20 with window 10 give [0,10] and [20]. |
| Recovery role | A required category of declared recovery evidence | A caller-defined policy role with one exact check and selected evidence record per incident. Roles have no built-in operational meaning. |
| Readiness | Required declarations are present, fresh and passing | Ready for manual recovery review; artifact bytes and actual recovery are not verified. |
| Pin and receipt | A reproducible declaration identifier and its consistency report | SHA-256 of normalized compact sorted-key escaped ASCII JSON plus LF; cohorts sort records by ID. A receipt is not a signature. |
| PASS | This tool's rules were met | Health PASS means declared healthy/fresh; timeline PASS means history integrity; correlation PASS means grouping consistency; readiness PASS means declared evidence coverage. |
| REVIEW_REQUIRED | Findings or withheld conclusions need interpretation | CLI exit 1. Logical findings retain assessment/cohort pins but withhold qualified_scope_sha256; structural binding/protocol errors withhold the assessment and cohort pins. |
| Fixed refusal | The input cannot be assessed | CLI exit 2; the API raises a fixed refusal for malformed outer input. No supplied sensitive values are echoed. |
| Independent package | One tool can be installed and called alone | Its own versioned wheel, CLI, embedded fictional demo and check(raw_json_bytes) API, with standard-library runtime code. |

## Apply the method

1. Select complete component snapshots and one observation per component. Define
   the ordinal scale and as-of point explicitly; preserve missing/unknown states.
2. Validate the full declared incident history, then inspect resolved_as_of rather
   than treating timeline PASS as a resolution claim.
3. Group alerts by explicit component/key and anchored windows. A critical group
   can PASS correlation without being healthy or approved for notification.
4. Define recovery roles and map evidence explicitly. The installed exercise maps
   health and resolution report declarations into evidence and retains a fictional
   restore-drill claim. The planner does not authenticate those reports or the drill.

The [installed exercise](../integrations/reliability-incident/exercise.py) tests
inclusive age boundaries, non-sliding alert windows, an unresolved valid timeline,
missing recovery evidence and a stale snapshot binding. The
[component guide](../integrations/reliability-incident/components.json) gives exact
APIs, formats, example paths, result fields and boundaries for human and AI callers.

All four tools expose supplied opaque IDs and hashes. Keep actual observations,
incident history, evidence, policies and reports private. Perform a separate exact
privacy/rights review before sharing; these checks do not anonymize records.
