# OUTLANDS | API Request Contract Checker

Validate supplied structured requests against exact selected operation revisions without network requests. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/video-game/AI/software declarations; offline and advisory.

From this complete tool directory:

```text
python -B requests.py --input examples/input.json
python -B requests.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `requests.check(raw_json_bytes)`.

## Contract

Input exactly `{format,operations,requests}`; format `outlands-api-requests-v1`.
Request exactly
`{id,revision,operation,operation_revision,operation_sha256,method,path,media_type,query,headers,body,expected_valid}`.
operation_sha256 binds the entire normalized selected operation, including every
request field and response variant. All selection revisions/hashes are exact. The
request cohort must be nonempty. Unknown/stale operation references, malformed decoded
representations or rejected/conflicting identity rows withhold complete assessment
and all scope pins. A request explicitly selects an operation; no automatic routing.

method must be one of the supported uppercase methods. path is 1..8 symbolic ID values,
with no slash parsing, decoding, normalization or URL fetching. Match method, route
length and literal segments; capture parameter values only when the complete route
shape matches. Unavailable path-field checks remain route_unavailable rather than
receiving invented values. query is a map of <=32 symbolic names to decoded strings.
headers is a map of <=32 lowercase x- custom names to printable ASCII string values.
body is null (absent content) or a flat map of <=32 symbolic keys to supported scalars.
media_type is null or application/json, selected separately from custom headers.

Compare exact media type and body presence; JSON requires an object, even when empty.
An absent-content operation refuses an object, even an empty one. Check requiredness,
exact scalar type, declared limits/choices and undeclared fields separately by location.
No defaults/coercion. expected_valid is null or an exact boolean, describing a caller
expectation without changing computed validity. Every invalid request requires review,
even when expected_valid is false; an expectation mismatch also requires review.

assessment.requests includes valid, fixed failed_criteria, per-declared-field IDs/states,
unknown-field counts and expectation_met. It never echoes supplied path, query, header
or body values, or unknown field names. Logical findings retain diagnostics/pins with
qualified scope null. operations_sha256 and requests_sha256 pin normalized declarations.
PASS checks this custom input contract, not an actual service, authorization or transport.

## Shared custom contract and limits

These are bounded structured declarations, with custom decoding assumptions and
explicit support limits. HTTP wire/OpenAPI/JSON Schema compatibility is unvalidated.
No raw HTTP messages, URLs, sockets, query strings, encodings or transport streams
are parsed, rendered or sent. Authentication/framing/redirect/cookie semantics are
outside the supported custom-header model. Use only supplied fictional observations
for public examples; keep actual inputs/reports private.

Operation exactly
`{id,revision,method,route,request_media_type,request_fields,responses}`.
Supported methods: GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS (uppercase, exact).
route is an ordered list of 1..8 literal symbolic IDs or `{parameter}` segments.
Parameter names are unique. Exactly one required string path field must declare
each parameter, with no extra path fields. There is no route precedence or URL
normalization, percent decoding, slash/path traversal or host/origin interpretation.
GET/HEAD/OPTIONS request bodies are unsupported in this subset. A null request media
type requires no body fields; request_media_type otherwise is application/json.

Field exactly
`{id,location,name,type,required,minimum,maximum,min_length,max_length,choices}`.
All fields required. Request locations: path/query/header/body; response: header/body.
Each field list has 0..32 components, unique IDs and unique (location,name) slots,
normalized by field ID. type is string, integer or boolean; required is an exact boolean.
Integer limits are null or integers within +/-10^12, ordered when both supplied;
min_length/max_length must be null and choices empty. Boolean has null limits and
empty choices. String minimum/maximum are null, min_length/max_length are null or
integers 0..256, ordered when both supplied. choices is 0..16 distinct strings <=256
Unicode code points, sorted; choices must fit declared length limits. No defaults.

Path/query/header fields are strings. Path choices must be symbolic IDs. Header names
must be lowercase symbolic IDs beginning x- with a nonempty suffix; header choices
and values are printable ASCII (32..126), excluding controls/CR/LF. Built-in/protocol
and authentication headers are not accepted as custom fields; media type is separate.
Query values are already-decoded strings and are not numerically coerced. Body values
are exactly bounded strings, integers +/-10^12 or booleans; null values, nested maps,
arrays, floats and other representations are unsupported scalar payloads. Only body
itself may be null to represent absence. Body/header/query maps have <=32 entries and
symbolic keys. Body/query strings have <=256 code points; the parser rejects invalid
Unicode. Unknown supported-map names produce counts, never echoes or inferred rules.

Response variant exactly `{id,status,media_type,request_valid,fields}`. An operation has
1..16 variants with unique IDs/status slots, normalized by ID. status is an integer
200..599, not a verification of standardized status assignment. request_valid is an
exact caller-declared boolean condition. media_type is null or application/json.
Statuses 204/205/304 and all HEAD responses require null media type. Null media type
requires no body fields. Non-null observed content is forbidden for an absent-body
variant even if the object is empty. No status ranges, automatic variants or redirects.

Each top-level request/response identity cohort has <=1,000 raw rows. IDs match
`[a-z][a-z0-9_-]{0,47}`, revisions are integers 1..1,000,000 and SHA-256 values are 64
lowercase hex. Booleans never substitute for integers. Identical normalized top-level
IDs count once; conflicting groups exclude all members. Accepted/duplicate/conflict/
rejected-row accounting is complete at those cohorts. Invalid nested components reject
their entire operation row; nested duplicates never silently disappear. All field names,
schema strings and values remain caller declarations, not real application state.

At most 128 raw operations, 4,096 selected nested field components and 32,768 selected
field assessments per exchange side. Larger scopes are fixed refusals. Operation and
request fingerprints are computed once per selected cohort, avoiding repeated hashing
of large schemas for every binding. No truncation, automatic latest selection or partial
repair. Selected operation/request reference mismatches and structural ambiguity withhold
the entire assessment/scope pins. Record-validation findings retain diagnostic IDs,
field states and aggregate unknown-field counts. No payload values are emitted.

Normalize nested fields/variants by ID and string choices by value; route order remains
significant. Cohorts hash normalized rows sorted by ID, using sorted-key compact
escaped ASCII JSON plus LF. Normalize before binding full snapshots. input_sha256
hashes exact input bytes separately. qualified_scope_sha256 exists only with no findings.
These hashes are consistency receipts, not signatures, authorization or confidentiality.
Reports expose declared record/field IDs and hashes; low-entropy values can be guessed.
These tools do not anonymize, sanitize or detect all private/credential data.

No endpoint contact, server/framework execution, requests, authentication, credential
verification, actual response observation, application behavior proof, installs, model
calls or target updates. network_requests_performed, servers_started,
authentication_performed, credentials_verified, service_behavior_verified,
wire_protocol_verified, records_changed, raw_values_emitted and target_changes_performed
are false. raw_values_emitted concerns supplied path/query/header/body values, not
declared record/field IDs or hashes. No real compatibility, security, privacy, rights
or production readiness is established. See each tool's meaning of PASS above.

One explicit JSON input <=4 MiB. Strict parsing rejects duplicate keys, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18. Escaped ASCII report <=8 MiB. Default stdout JSON; --out requires an absolute
fresh external destination under an existing trusted parent outside source. No overwrite,
traversal or mkdir. Ordinary single-link input and trusted quiescent storage required.
[Public Windows/POSIX I/O guards](IO-SAFETY.md) preserve POSIX retained parent descriptors/
no-follow checks and native Windows reparse/hardlink/change checks. They do not sandbox
hostile concurrent writers or guarantee inherited parent ACL confidentiality. Failed
writes may leave partial/unconfirmed output: inspect privately and select a fresh
filename. Shell redirection lacks these output guards. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption. Error messages omit supplied values/paths.

Each complete directory is Python 3.12/3.13 standard library, with no sibling runtime
imports. Fresh generic code, invented HVAC/video-game/AI/software declarations and
reviewed public MIT helpers only. Original private code, schemas, routes, business
policies, real traffic, user/customer data, paths, credentials, endpoint addresses and
deployment details were not consulted or selected. See [origins](ORIGINS.md) and
[validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
