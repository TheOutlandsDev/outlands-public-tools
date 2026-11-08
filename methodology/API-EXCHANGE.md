# API request-and-response review

Use these four tools to review supplied examples of an interface before connecting
it to an application. An interface describes how a caller asks for work and how a
service answers. These tools assess a small custom declaration format offline;
they do not call a service or interpret arbitrary HTTP, OpenAPI or JSON Schema.

## Terms and exact meanings

| Term | Plain meaning | Technical meaning in this tool group |
| --- | --- | --- |
| Operation contract | A written definition of one kind of interaction. | An exact ID/revision, uppercase method, ordered symbolic route segments, scalar request-field rules and explicit response variants. |
| Request | The proposed question or work item sent to an interface. | A supplied structured record selecting one exact operation revision and normalized SHA-256, with method, symbolic path, decoded query, custom headers and absent or flat scalar body. Nothing is transmitted. |
| Response observation | A supplied description of an answer. | An asserted record selecting an exact request ID/revision and normalized SHA-256, status, media type, custom headers and body. The tool does not independently observe the answer. |
| Response variant | One allowed form of answer. | An explicit numeric status, null or JSON media type, caller-declared request-validity condition and field rules. There are no automatic status ranges or inferred error responses. |
| Revision | Which version of a definition or record is selected. | An integer from 1 through 1,000,000. A fingerprint pins the selected normalized content separately; a version number alone is insufficient. |
| Fingerprint or pin | A way to detect different content. | SHA-256 of normalized sorted-key compact escaped-ASCII JSON plus LF. Field/variant/cohort IDs and string choices are sorted; route order remains meaningful. Raw input has a separate exact-byte hash. Pins are not signatures or privacy protection. |
| Expected validity | The caller's prediction of the result. | An exact boolean, or null for no prediction. It does not override calculated validity. A mismatch requires review. |
| Scenario | One case to compare across definitions. | The same request identity, payload and expectation plus the same response observation and expectation on both sides. Only the documented operation-revision/pin and dependent request-pin differences are allowed. |
| Qualified scope | A clean consistency receipt for this selected input. | A report fingerprint emitted only when there are no findings. It says nothing about unselected cases, actual traffic or deployment permission. |
| Review required | A finding needs a decision or correction. | Exit 1 and status REVIEW_REQUIRED. Structural problems withhold assessment and scope pins; logical findings retain diagnostic results without a qualified-scope receipt. |

All operation, request and response records are caller assertions. Exact selection
prevents silently choosing a newer revision. Conflicting identities, missing cases,
changed assumptions and stale pins remain visible rather than being repaired.

## Four different meanings of PASS

1. **Operation checker:** the selected declarations satisfy this bounded format
   and contain no ambiguous operation routes. This does not certify API design.
2. **Request checker:** every selected request meets its declared rules and any
   stated expectations. An invalid request still requires review even when its
   `expected_valid` is false.
3. **Response checker:** complete supplied response coverage and variants satisfy
   the selected declarations and expectations. A correctly declared error answer
   can PASS while its underlying request is invalid. Inspect request validity
   separately; no successful service action is established.
4. **Scenario comparator:** the same selected cases have equal request/response
   validity outcomes and matching expectations under both definitions. Equal
   expected-negative cases can PASS. This is selected-case equality, not whole-API
   compatibility; missing or changed observations are incomparable and need review.

Refused input returns exit 2 with a fixed diagnostic code; it is not an ordinary
negative assessment. The Python API raises the package's `toolkit.Rejected`.

## A repeatable method

Start with fictional declarations. Review their shape, bind each request to an
exact normalized operation, bind each response to its exact normalized request,
and compare matching cases under two independently checked definitions. Retain
failing cases as well as passing ones. Inspect `assessment`, `issues`, expectations
and the selected scope before using the result in a separate project decision.

For example, an invented service proposal allows integer priority 1 through 5.
Priority 2 passes request review. Priority 6 requires request review; an explicitly
declared 400 error response may still pass response review. Tightening the maximum
to 1 changes how the unchanged priority-2 observation is assessed and requires
scenario review. Replacing the candidate payload with priority 1 changes the case,
so it cannot establish unchanged behavior for the original priority-2 request.

## Supported scope and privacy

Fields are bounded strings, integers or booleans. There is no nesting, array or
floating-point payload support. Query/path/custom-header fields are strings;
headers are restricted lowercase `x-` names with printable-ASCII values. Routes
are symbolic segments, not URLs. Only null or `application/json` media types are
supported. The [source contract](../tools/api-operation-contract-checker/README.md)
documents row, byte, route, field and representation limits precisely.

The tools do not verify wire encoding, cookies, redirects, framing, host/origin
checks, authentication, credentials, authorization, service behavior or production
readiness. Reports omit supplied path/query/header/body values but retain supplied
IDs and hashes. Low-entropy data may be guessed from fingerprints. These reports
are not anonymized or a substitute for a separate public-release audit. Keep real
requests, records, response assertions and reports private.

Use the [install guide and worked exercise](../integrations/api-exchange/README.md)
for independently installed commands and Python APIs.
