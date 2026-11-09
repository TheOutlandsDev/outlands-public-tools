# Forms and interaction review terms

These four tools inspect **supplied JSON records**. They do not open a browser,
read a DOM, run scripts, submit a form or change an application. Begin with a
fictional example and the [install guide](../integrations/forms-interaction/README.md).

| Term | Plain meaning | Exact meaning here |
| --- | --- | --- |
| Form definition | A stated set of fields and rules. | One ID and revision with 1..32 bounded string, integer or Boolean fields; declared visibility and requiredness conditions form an acyclic dependency graph. It is a custom JSON format, not HTML or JSON Schema. |
| Selected form snapshot | The exact form version used for a decision. | Form ID, revision and SHA-256 of the normalized declaration must agree. A hash match binds these declared bytes under the specified normalization; it does not prove who authored them. |
| Submission | Values asserted for a form. | A bounded map of exact scalar values, with an optional expected validity assertion. Missing, hidden, wrong-type and out-of-range values are distinguished. No value is sent to a service. |
| Field decision | Why a supplied field passes or fails. | One of `valid`, `optional_absent`, `missing_required`, `hidden_absent`, `hidden_value_refused`, `type_invalid`, `out_of_range`, `length_invalid` or `choice_invalid`. Raw values are omitted from the report, but the input and its hashes may still be sensitive. |
| Flow definition | Stated states and allowed actions. | An exact form-bound directed graph with an initial state, terminal states and unique `(from, action)` transitions. A transition may require no submission, a valid submission or an invalid submission. This is a declared validation branch, not a permission rule. |
| Interaction history | A claimed sequence of actions. | Ordered events with exact flow and submission references. The checker walks the declared graph; it never performs a transition. After the first invalid step, later steps stay unassessed. |
| Scenario comparison | Compare the same selected case under two versions. | Independently compile baseline and candidate declarations, require exact case identity and content except verified version pins, then compare sanitized field and history outcomes. Missing cases or changed supplied values are incomparable. |
| `PASS` | The selected declared check met its own contract. | A history can PASS through a declared invalid-submission branch. An equal expected-negative comparison can PASS while both submissions are invalid. Inspect individual validity and expectation fields. |
| `REVIEW_REQUIRED` | A finding needs a human decision or correction. | It may signal a logical failure, changed selected outcome, expectation mismatch, structural reference problem or coverage loss. It is a returned report, distinct from a refused input. |
| Qualified scope | The part the checker could assess under its rules. | `qualified_scope_sha256` is present only when the selected scope is coherent and has no issues. It is not browser coverage, accessibility proof or release approval. |

The fictional service request has a conditional filter-grade field, an integer
priority, and an optional urgent flag that can require a review note. Its
declared flow moves from draft through review to a terminal reviewed state.
The examples prove how the offline contracts compose; they are not observations
of an actual UI. A changed priority maximum can change a selected submission
decision and the history that depends on it. Equal negative outcomes can compare
successfully without turning invalid inputs into valid ones.

For a real project, specify a reviewed projection from its field controls,
state/action names, values and actual observations into these custom JSON
records. Keep the source observations and generated reports private. Validate
actual browser behavior, accessibility, permissions and application effects
separately. No adapter, capture hook or live integration is included.
