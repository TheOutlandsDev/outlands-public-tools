# Terms used by OUTLANDS tools

These meanings apply to the offline checkers in this collection. A tool's own
README defines its exact input schema and result fields.

| Term | Plain meaning | Precise meaning here |
| --- | --- | --- |
| Contract | A stated set of rules for data or a process. | A versioned input shape plus constraints that a checker evaluates. A passing contract check establishes consistency with those rules, not truth about the outside world. |
| Declaration | A claim supplied by the caller. | A value in input JSON, such as a model's supported task or capacity. Unless a tool says otherwise, the value is not measured or independently verified. |
| Receipt | A record of a claimed step or result. | A structured record whose fields can be compared with a plan and other records. A matching receipt does not authenticate the actor or prove that an operation happened. |
| Reconciliation | Compare related records for agreement. | Recompute expected relationships from supplied inputs and report missing, conflicting or mismatched rows. It does not repair source records. |
| Pin | A fingerprint for exact bytes or normalized data. | Usually a SHA-256 digest. A match links two representations under the stated encoding rules; it is not a signature or proof of origin. |
| `PASS` | The supplied data met the checked rules. | A successful result for the tool's stated scope. Read its limits before using the result to make a decision. |
| `REVIEW_REQUIRED` | A person needs to examine a reported issue. | A completed assessment with at least one rule failure or withheld conclusion. For the model-routing CLIs it exits with code 1. It is not permission to proceed. |
| Fixed refusal | The tool could not assess the input. | Invalid input or an unsafe file operation yields a fixed diagnostic and exit code 2 for the model-routing CLIs. Do not treat it as a negative assessment of the subject. |
| Source only | Code is supplied without a runtime. | Install a supported runtime separately. A source ZIP is an archive, not a package-manager installation. |
| Independent tool | One component can run on its own. | Its package includes its required code and declares runtime requirements. It may still require caller-supplied input and integration work. |
| Collection | A chosen set of components. | A versioned manifest or package that names exact members and dependencies. Installing the collection does not establish that its tools interoperate with a particular system. |

## Evidence levels

An example using fictional records shows how to operate a tool. A unit test checks
specified code behavior. A fresh installed-package check exercises the distributed
files. A live integration check needs the actual target system and separately
reviewed data. State which level a claim reached; do not silently promote one to
another.

For case contracts, run coverage, regression classifications and evidence roles,
use the [test and evidence definitions](TEST-EVIDENCE.md) and their installed
four-tool exercise. Complete evidence can describe an observed mismatch.

For observation freshness, incident histories, anchored alert windows and recovery
roles, use the [reliability and incident definitions](RELIABILITY-INCIDENT.md)
and the installed fictional workflow. Timeline integrity and resolution are distinct.

For metric kinds, disjoint histogram buckets, run clocks, span coverage and
explicit point/span links, use the [metrics and traces definitions](METRICS-TRACES.md).
Declared time/reference consistency does not establish causation.

For decoded document text pins, dependency graphs, code-point chunks, supplied
retrieval judgments and exact quote spans, use the [document and answer evidence
definitions](DOCUMENT-EVIDENCE.md). Citation integrity and factual truth are distinct.

For relational schema differences, typed keys, join multiplicity, explicit null
policies and supplied query-result checks, use the [relational review definitions](RELATIONAL-REVIEW.md).
Structural result consistency does not verify SQL output.

For intake mappings, explicit batch/receipt snapshots, advisory replay decisions,
ordinal checkpoint proposals and declared run totals, use the [ingestion control definitions](INGESTION-CONTROL.md).
Declared committed receipts do not verify target commits or authorize replay.

For work-item interfaces, symbolic metadata, half-open lease ownership, acknowledgement
accounting and result/commit declarations, use the [worker and queue definitions](WORKER-QUEUE.md).
Consistent declarations do not establish actual workers, enforced ownership or durable commits.

For fingerprint-only overlays, field-metadata differences, explicit component pair
rules and supplied migration chains, use the [configuration review definitions](CONFIGURATION-REVIEW.md).
Metadata consistency does not validate actual settings, runtime compatibility or adapter bytes.

For operation contracts, supplied requests/responses, exact revision pins and
selected-case version comparison, use the [API request-and-response definitions](API-EXCHANGE.md).
A valid error response and an invalid request can coexist; matching selected
outcomes do not prove whole-API compatibility or actual service behavior.

For declared form fields, conditional rules, supplied values, flow states and
selected-case interaction comparisons, use the [forms and interaction definitions](FORMS-INTERACTION.md).
These are offline records, not observations of a browser or proof of whole-UI behavior.

For declared image and taxonomy references, simple polygon criteria, exact box
conventions and annotation handoff counts, use the [annotation and geometry
definitions](ANNOTATION-GEOMETRY.md). A consistent declaration does not establish
image content, label truth, authenticated approval or an actual dataset export.

For supplied meter readings and reset boundaries, advisory due states, order
histories and completion declarations, use the [maintenance and service
definitions](MAINTENANCE-SERVICE.md). A consistent record does not establish
live meter provenance, actual scheduling, physical service or stock changes.

For selected stock balances, inventory positions, replenishment rules and
shipment declarations, use the [stock and fulfillment definitions](STOCK-FULFILLMENT.md).
A consistent declaration does not establish physical stock, procurement or delivery.
