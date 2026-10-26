# Saved event metadata format

Choose --format json or xml explicitly; all selected files in one run use that
format. 32 files total, 1 MiB each, 4 MiB aggregate, 4,000 accepted events and
bounded report collections. Native EVTX/EVT files are not decoded.

## Normalized JSON

Root has exactly schema_version (integer 1) and events (array). Each event needs
provider (nonempty string <=256), event_id (integer 0–65535), time_created (string).
Optional nullable fields: provider_guid (UUID text), channel/computer (nonempty
strings <=256), record_id (integer 0..2^64-1), level/version (integer 0–255),
qualifiers (integer 0–65535). Booleans are not integers. Unknown fields require
coverage but are not embedded. Duplicate JSON keys, floats/NaN, invalid encoding,
depth >8, >40,000 nodes, keys >256 or strings >8,192/control-bearing strings fail.
UTF-8 BOM is accepted. JSON does not inherit the text format's line-length cap.

## Restricted XML

UTF-8 with optional BOM, LF/CRLF, <=20,000 physical lines and 8,192 characters per
line. Original restricted reader: balanced ASCII names/quoted attributes,
comments, literal XML 1.0 declaration first, and predefined/numeric references
decoded once. DTD/entity declarations, CDATA and other unsupported markup fail.
Limits before accepting extra tree data: 8,000 elements/file, depth 32, 16
attributes/element, names <=256, values <=1,024 and text/tail nodes <=8,192.
Encoded CR is permitted as XML text; identifying metadata validators still reject
controls. There is no native XML parser or external resource behavior.

Root is Event or Events with direct Event children. Supported default namespace
is http://schemas.microsoft.com/win/2004/08/events/event, or unnamespaced text.
Prefixed event/System metadata and namespace resets on inspected fields require
coverage. This is not a full namespace/schema validator for discarded payloads.
Each event requires one System, one Provider with Name, one numeric EventID and
one TimeCreated with SystemTime. Optional Provider Guid, EventID Qualifiers,
Channel, EventRecordID, Level, Version and Computer map to normalized fields.
Duplicate/nested required metadata or unknown inspected namespace makes that
record unsupported. Known payload/security/execution/rendering fields are
intentionally outside scope and omitted; unknown fields/modifiers/mixed content
require coverage. Invalid metadata is counted as coverage rather than silently
accepted. Malformed/refused XML fails the entire run.

## Time, grouping and identity

Accepted timestamps use YYYY-MM-DDTHH:MM:SS[.1_to_7_digits]Z or an explicit
plus/minus HH:MM offset bounded to 14 hours. Unknown -00:00, naive times, leap
seconds, unsupported precision or UTC conversion beyond year 1..9999 require
review. Arithmetic uses exact 100 ns integer ticks, not floats or local timezone
guessing. Output canonical UTC strings always retain seven fractional digits.
Elapsed/delta/gap ticks and detailed record IDs are decimal strings for exact JSON
consumption. Parse them as integers/BigInt where needed, not binary floats.

Timeline sorts by declared UTC ticks with stable input order on ties. Group keys
are exact provider name, normalized optional GUID, channel, event ID, optional
version and optional qualifiers; unspecified values are not assumed to be zero.
Groups report counts/levels; repetitions alone are not errors. Counts retain all
accepted occurrences, including duplicates.

Record-ID comparison is scoped to individual selected source plus declared
computer/channel/record ID, only when all identity fields exist. Same identity
with equal normalized inspected fields is duplicate; differing fields conflict.
No cross-file deduplication, actual host identity or payload equivalence is
inferred. Computer strings remain internal and are never serialized in reports.

Gap findings use strictly greater than --gap-seconds (default 300; 0 disables;
maximum 31,536,000). Gaps are between adjacent selected sorted events, not proof
of event loss, downtime, failure or causation. Clock accuracy/completeness is
unverified, especially when mixing sources or computers.

Schema version 1 includes inputs, timeline, groups, gaps, repeated_groups,
input-order observation, findings, coverage_issues, duplicate_scope and status.
Record indexes are JSON array positions / XML Events-child positions (or 1 for
a single Event), not source line numbers. Opaque IDs depend on input order.
