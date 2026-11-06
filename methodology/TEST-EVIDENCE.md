# Test and evidence methodology

Use these terms to describe what a check actually establishes. The tools inspect
supplied JSON declarations offline; they do not execute the declared tests.

| Term | Plain-language meaning | Technical meaning in these tools |
| --- | --- | --- |
| Case | One planned check | An exact ID/revision plus definition, input and derived expected-result SHA-256 declarations. |
| Contract | What a result is expected to look like | Expected exit code and stdout/stderr hashes; all required schema fields are explicit. |
| Run | One selected observation scope | A distinct ID/revision, subject hash and full case/expectation cohort pins. |
| Observation | A claim about what happened | A result bound to an exact run and case, with state, observed exit, output hashes and completeness. |
| Coverage | Whether the planned cases have usable observations | Planned, completed and matched case counts within the supplied cohort; this is not line or branch coverage. |
| Match | The declared complete output agrees with its contract | Exact exit/stdout/stderr-hash equality. An expected nonzero exit can match. |
| Regression | A formerly matching case now mismatches | Equal full case pins and complete observations, baseline matched and candidate did not. Changed case contracts are incomparable. |
| Evidence role | A required kind of supporting material | A policy role bound to an artifact declaration for an exact result snapshot. Artifact bytes are never opened. |
| Pin | A reproducible identifier for a declaration | SHA-256 of normalized compact sorted-key escaped ASCII JSON plus LF; cohorts sort records by ID. |
| Receipt | A report of this consistency check | Report format, exact raw-input hash, diagnostics, assessments and scope pins; not a signature or proof of execution. |
| PASS | This tool's declared conditions were satisfied | Exit 0; evidence PASS may describe a complete test failure, and regression PASS may include an improvement. |
| REVIEW_REQUIRED | Findings need interpretation | Exit 1; logical findings retain assessments but withhold qualified scope. Structural binding problems withhold assessment and cohort pins. |
| Refusal | Input cannot be assessed under this contract | CLI exit 2 with fixed diagnostics; malformed outer API input raises a fixed refusal. |
| Source-only distribution | Code without private runtime material | Python must be supplied separately; wheels include public source, invented fixtures and required package/license metadata. |

## Apply the method

1. Select complete exact case snapshots and explicit expectations. Derive the
   expected-result hash before the case hash, then pin the full cohorts and run.
2. Supply one selected observation per case. Reconcile attempts explicitly;
   the checker does not select the newest or best result.
3. Compare distinct baseline/candidate runs. Preserve changed contracts, absent
   cases and incomplete captures as findings rather than claiming compatibility.
4. Select an evidence-role policy and bind every artifact to its exact result.
   Complete failure evidence remains failure evidence; review is separate.

The [installed exercise](../integrations/test-evidence/exercise.py) constructs a
fictional HVAC case, checks a baseline, identifies a candidate regression, and
shows that complete evidence can accompany that mismatch. It also checks a missing
evidence role, a changed contract and a stale run binding. No check script runs.
The [component guide](../integrations/test-evidence/components.json) gives AI and
human callers literal APIs, schema identifiers, result fields and limitations.

Keep actual definitions, observations, evidence, policies and reports private.
Opaque identifiers and hashes can disclose relationships; these tools do not
anonymize data. Apply a separate exact-file privacy/rights review before sharing.
