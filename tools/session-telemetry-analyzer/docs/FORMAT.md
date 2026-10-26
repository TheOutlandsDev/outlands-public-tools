# Supported saved telemetry and report format

Schema version 1 supports a bounded JSONL-like telemetry subset. It requires
one JSON object per nonblank record line, with exact case-sensitive `type` and
object-valued `payload` fields. This schema is original to the public tool's
documented subset; it is not a complete producer compatibility contract.

## Encoding, lines and strict decoding

Inputs are UTF-8. LF and CRLF are supported; bare CR, NUL, unsupported Unicode
control categories and Unicode line/paragraph separators in physical input are
refused. A file-start UTF-8 BOM is accepted as an explicit compatibility
extension with `UTF8_BOM_EXTENSION` coverage. Interior blank/space/tab-only lines
are counted with `BLANK_RECORD_LINE` coverage rather than treated as events.
The [JSON Lines specification](https://jsonlines.org/) disallows a BOM and blank
values; this tool deliberately reports these extensions and is not a general
JSON Lines conformance validator.

One final newline is a terminator, not an additional record. For example, one
object followed by LF has `physical_lines: 1`; two LFs after the object mean two
physical lines, the second blank. An empty or BOM-only file has zero physical
lines. The lower-level file guard still bounds its split-line list, including a
terminal empty split element, before this normalization: at most 20,000 elements
and 8,192 characters each.

JSON duplicate keys at any nesting level are rejected per record, even when
values match. Nonstandard NaN/Infinity constants, invalid JSON and decoded
control characters cause malformed-record coverage; their raw text is omitted.
A partial final record follows the same rule. Other selected valid records can
still be analyzed, without claiming the capture was complete. Invalid UTF-8,
physical controls or resource-bound failure stops the run with exit 2.

JSON structure is bounded to depth eight, 1,000 value nodes per record, keys of
256 characters and values of 1,024 characters. Integer tokens have at most 24
characters including a minus sign. Decimal/exponent tokens have at most 64
characters and absolute exponent at most 1,000. Decimal numbers are decoded as
`Decimal`, never a binary float; these resource bounds also apply to discarded
payload data. A resource limit produces `INCOMPLETE`, not a malformed-row skip.

## Supported fields

```json
{"type":"snapshot","payload":{"map":"FictionalOrchard","raid_seconds":1.25,"player_count":2,"bot_count":4,"tracking":{"active_count":3},"line_of_sight":[{"main_can_see_bot":true},{"main_can_see_bot":false}]}}
```

Recognized type names are `raid_start`, `snapshot`, `tracking_assigned` and
`raid_end`. Missing/nonstring/empty types, nonobject roots and missing/nonobject
payloads are invalid envelopes. Other nonempty strings count as unsupported
event rows. No raw unknown type name appears in the report.

Only `type` and `payload` are supported root keys. Extra root fields receive
`ENVELOPE_FIELDS_UNSUPPORTED`. Their values are discarded; accepted known
metrics can still contribute. Root timestamps, IDs, sequence numbers and session
names are not interpreted or authenticated.

Every supported event may carry `map` and `raid_seconds`. Map values are
discarded without semantic validation and never emitted. All JSON decoder bounds
still apply. `raid_seconds` is optional: an actual JSON integer/decimal from zero
through 315,360,000. Booleans, strings and null are invalid. Its latest accepted
value in physical input order is reported as a decimal string, with no clock
conversion, ordering repair or inferred duration. A decrease records
`DECLARED_TIME_DECREASE`; invalid declarations do not replace the last valid one.

Snapshot-only selected fields:

| Field | Supported declaration | Observation |
| --- | --- | --- |
| `player_count` | Actual JSON integer, 0–1,000,000,000 | Player population sample. |
| `bot_count` | Same integer bounds | Bot population sample. |
| `tracking.active_count` | `tracking` object, optional integer of the same bounds | Tracked-active sample. |
| `line_of_sight` | List of at most 256 objects | Selected boolean observations. |
| `line_of_sight[].main_can_see_bot` | Actual JSON boolean | Visible/observed sample. |

Counts reject booleans, null, strings, decimal/exponent tokens and negatives.
Even `2.0` is a decimal declaration rather than a population integer. Missing
fields contribute to missing counts, not to valid sample denominators. An
invalid tracking container contributes one invalid tracked-active sample;
missing tracking or an object without `active_count` contributes one missing
sample. Unknown tracking fields receive coverage without invalidating a valid
supported active count.

Missing line-of-sight lists, invalid list containers, present lists, declared
entries, missing entry values, invalid entries/values and valid booleans have
separate counters. An empty list is present with zero boolean samples. Unknown
entry fields receive coverage; valid selected booleans can still contribute.
Only the exact `main_can_see_bot` field is interpreted.

Only `raid_end` supports `dropped_lines`: an actual JSON integer from zero through
1,000,000,000,000. With exactly one supported end row and one valid declaration,
the value is emitted as a decimal string; positive values create
`DECLARED_DROPPED_LINES`. Multiple supported end rows make the value
`ambiguous_multiple_end_rows`, even if equal or only one has a valid value. The
result is null; no first/last winner or cumulative sum is invented. An invalid
single declaration has state `invalid`; absent declarations remain `unspecified`.
Multiple start rows also create coverage. Marker counts describe rows, not
verified sessions or lifecycle completion.

Other payload fields receive `PAYLOAD_FIELDS_UNSUPPORTED`. Known valid fields
remain usable, but coverage is visible. Fields supported only for another event
type are also outside the selected row's scope. `tracking_assigned` is counted;
assignment identities and arbitrary payload details are not interpreted.

## Statistics and report contract

Each selected file receives a separate capture object. There is no cross-file
population mean, deduplication, entity identity or session segmentation.
Identical files selected under different actual regular-file identities are
separate observations. The CLI rejects repeated same-file paths/hardlink aliases.

For each population, `samples` counts valid-present values; `missing_samples`
and `invalid_samples` are separate. `sum` is an exact decimal string and
`maximum` is a valid integer or null. `sample_mean` is null without valid samples;
otherwise it is `{"numerator":"6","denominator":2}`. It intentionally retains
the unreduced denominator so the valid sample count remains visible. It is
equal-weighted by sample, not time-weighted or a distinct-entity count.

Line-of-sight `visible_fraction` has the same unreduced ratio shape, with visible
true booleans over valid boolean samples. It is null with no valid booleans.
Neither value is a statistical estimate of a population, probability, rate,
correctness, difficulty or performance.

Top-level output includes `schema_version`, `tool`, `scope`, `status`,
`selected_files`, `nonblank_records_observed`, `sources`, `captures`, `findings`
and `coverage_issues`. Source rows contain opaque source IDs, exact input byte
sizes and SHA-256. Capture counters distinguish nonblank, decoded, accepted,
malformed JSON, invalid envelope and unsupported type rows. Counts do not add
arbitrary discarded data to metrics.

Coverage/finding rows carry only fixed codes, opaque `source`, physical `line`
and an optional static metric `field`. Line zero denotes a capture-level
observation. No filenames, map values, identifiers, unknown names, raw records
or upstream exception text is emitted. All reports still require private review:
hashes, sizes, declarations and statistical structure can identify an input.

The CLI accepts at most 32 distinct regular files, 1 MiB each and 4 MiB total.
Across them at most 4,000 nonblank records are analyzed. Bounded report/finding
collections have at most 4,000 rows. Empty/unsupported-only captures create
`NO_SUPPORTED_EVENTS` coverage. Report JSON/HTML are each at most 8 MiB and
written exclusively into a fresh directory under an existing local parent.
The unsigned `MANIFEST.json` covers the report files, not capture authenticity.
