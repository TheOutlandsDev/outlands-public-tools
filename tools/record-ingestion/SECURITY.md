# Privacy boundary

The public source and built-in examples are fresh and generic. No historical
application implementation, business schema/query/formula, source mapping,
credential, endpoint, user record, database, operational log, runtime asset or
deployment configuration is included.

The CLI accepts only a demo flag and help. It reads no operator file, stdin,
URL or environment inventory, and invokes no process, service, model or email
transport. The library accepts text explicitly supplied by a caller; parsing
that text is not authorization to collect it or publish its contents.

Accepted records may identify people, projects or operations even when their
fields fit this neutral schema. Keep raw text, accepted records, issues,
rejected payloads and exports private. Diagnostics omit raw values and native
parser text, but counts/positions can still be operational information.
Validation is not anonymization, ownership proof or complete secret/IP review.

Always call `require_clean()` before downstream processing. Valid records can
be retained alongside issues for inspection. The module does not authorize
discarding failed rows or repairing conflicts. A caller's private adapter must
define its own retention, mapping, authorization and publication policy.

There is no filesystem sandbox, data-source adapter, durable store, scheduler,
quarantine service or production integration. Byte/record bounds do not provide
hard process-resource quotas. Trusted application code remains responsible for
safe I/O and integration behavior.

Use minimal fictional inputs in issue reports. Do not attach real rows, source
schemas/mappings, credentials, logs, private paths, screenshots or records from
an operational system. Review exact export contents and rights separately.
