# Supplied-profile contract

All JSON is UTF-8 (optional BOM), bounded and strict: duplicate keys, nonfinite numbers, excessive depth, unexpected schema fields and boolean-as-integer inputs are refused. Object order is canonicalized for SHA-256 pins; list order is preserved. Integer setting comparison remains exact and uses the public Configuration Contract Checker's rules.

## Profile

See the complete [fictional profile](../examples/profile.json). The exact fields are:

| Field | Meaning |
| --- | --- |
| `format` | Exactly `outlands-setup-profile-v1` |
| `label` | Nonempty literal text, at most 120 UTF-8 bytes |
| `prerequisites` | 0–32 exact `{id,kind,required}` declarations; kind `file`, `program` or `manual`; required is boolean |
| `configuration` | Unchanged public contract `{schema_version:1,fields,rules}` |
| `layout` | 0–32 exact `{id,path}` required relative-name declarations |
| `connections` | Unchanged public loopback declaration plan `{schema_version:1,bindings}` |
| `steps` | 1–32 exact `{id,label,depends_on,checks,verification}` objects |

Local prerequisite/layout/step IDs match `[A-Za-z][A-Za-z0-9_]{0,31}` with case-insensitive uniqueness within their collection. The public configuration/connection cores preserve their existing lowercase ID rules and stricter schemas. Relative names have 1–8 slash-separated segments, at most 240 UTF-8 bytes total, alphanumeric/underscore initial characters, then alphanumeric/underscore/dot/hyphen. No absolute names, traversal, backslashes, drive/stream syntax, trailing dots or Windows device names. Observed names are compared **exactly and case-sensitively on both platforms**. This compares declarations, not filesystem case behavior. Case-colliding supplied names are refused. File/directory name relationships are not inferred or checked.

Configuration fields support required/optional boolean, signed 64-bit integer with optional minimum/maximum, or string with optional min/max length and exact choices. Rules use `{id,op:"less_or_equal",left,right}` and reference two distinct integer fields. At least one configuration field is required by this format; up to 128 fields/rules/settings retain the original core bounds. Unknown setting names produce only an unexpected-count issue and require review; their names and values are absent from evaluation results. Optional absent configuration fields remain `NOT_SUPPLIED`; they block steps only if explicitly referenced.

Connections require 1–128 exact `{id,transport,address,port}` bindings. Transport is `tcp` or `udp`, address exactly `127.0.0.1` or `::1`, port an integer 1–65535. Only equal transport/address/port tuples conflict. IPv4/IPv6 and TCP/UDP remain distinct declarations; operating-system dual-stack behavior, actual availability and conflicts outside the supplied plan are not modeled. Repeated bindings make their individual checks `CONFLICT`.

Steps reference check IDs using `prerequisite:ID`, `configuration:ID` (field or rule), `layout:ID` or `connection:ID`. Each step has 1–128 unique check references and up to 32 unique predecessor IDs. Unknown/self dependencies and cycles are refused. A stable topological order uses declaration order among ready siblings. Labels (120 bytes) and verification notes (400 bytes) remain literal. There are no command, script, action, installation or connection fields that can be executed.

## Observations

The exact fields are `prerequisites`, `settings` and `files`; see [fictional observations](../examples/observations.json). Prerequisite keys must be declared, with values `PRESENT`, `MISSING`, `UNKNOWN` or `UNSAFE`. An omitted prerequisite becomes `UNKNOWN`. `PRESENT` maps to a declaration `PASS`; it never proves file existence, executable validity, compatible versions, permissions or manual verification. Observed files are a list of up to 128 portable names, not paths to read. Extra portable filenames are retained privately but do not create failing checks; absent required names become `MISSING`.

An evaluation includes input hashes, check IDs/status/evidence, summaries and ordered steps. It excludes actual setting values and supplied file lists, but includes literal step labels/verification text. Required unresolved checks and unexpected settings count as blocking. Each step is `BLOCKED` if any referenced check is not `PASS` or any predecessor is blocked; otherwise it is `READY_FOR_MANUAL_REVIEW`. A required unresolved check blocks overall status even if no step references it. Optional unresolved checks are counted separately. Overall status is `REVIEW_REQUIRED` when a required issue or blocked step remains, otherwise `DECLARATIONS_SATISFIED`. Every manual verification remains `NOT_PERFORMED`; `runtime_verified` is always false.

## Requests and pinned artifacts

`save-profile`, `evaluate` and `make-plan` take exact `{expected_head,actor,reason,request}` envelopes. `expected_head` is the current lowercase 64-character SHA-256 journal head (64 zeroes initially). Actor (160 bytes) and reason (400 bytes) are local literal assertions, not authenticated identity. Requests are:

```json
{"parent_id":null,"profile":{"format":"outlands-setup-profile-v1"}}
```

The abbreviated profile above must be replaced with a complete profile. Parent IDs are null or a registered profile's 32-character lowercase hexadecimal ID. Evaluation and plan requests are:

```json
{"profile_id":"PROFILE_ID","profile_sha256":"PROFILE_SHA256","observations":{"prerequisites":{},"settings":{},"files":[]}}
```

```json
{"evaluation_id":"EVALUATION_ID","evaluation_sha256":"EVALUATION_SHA256","checks":{"quality":true,"privacy":true,"rights":true,"context":true}}
```

Replace uppercase placeholders with returned lowercase IDs/hashes. Plan review requires four exact true booleans. Reviewing blockers never changes their status. Historical registered evaluations remain usable with their original upstream pins. Each explicit operation gets a fresh identity; no automatic retry/idempotency is claimed. Typed journal replay recomputes evaluation and plan results and verifies exact canonical bytes/types.

Export takes exact `{expected_head,actor,reason,plan_id,checks}` without an inner `request`. It verifies the registered plan and all upstream artifacts before writing a fresh private directory. The five pinned files are `profile.json`, `evaluation.json`, `plan.json`, `review.json` and `journal.json`; `manifest.json` is written last. The manifest explicitly denies execution and public-release authorization. Its own hash is not self-contained in its file map. A failed export may retain a partial directory, with no automatic adoption or resumption.

## Limits

Profile 64 KiB, observations 128 KiB, rendered evaluation/plan 256 KiB, guarded request/output file 4 MiB, JSON depth 64, journal 64 jobs/256 events, index 64 MiB. Text caps count UTF-8 bytes. New jobs reserve a terminal event slot; ordinary three-kind jobs use two events each. There is no retention/purge feature. Near capacity, full-journal handoffs can exceed the 4 MiB output limit and be refused while files remain private. Snapshot backups omit artifact files. Start a separate fresh instance when capacity is exhausted; no import/restore or schema migration is provided.
