# Observation and report contract

The neutral replay format is UTF-8 JSON with exactly two root fields:

```json
{"schema":"outlands-usb-samples/1","samples":[
  {"elapsed_ms":0,"present":true,"code":null},
  {"elapsed_ms":1000,"present":null,"code":"QUERY_FAILED"},
  {"elapsed_ms":2000,"present":false,"code":null}
]}
```

Each row has exactly `elapsed_ms`, `present` and `code`. Elapsed time is an
integer, never a boolean, between 0 and 3,620,000 inclusive and must be
nondecreasing. Equal times are allowed and preserve input order; they do not
imply causal ordering. Presence is true, false or null. Known presence requires
code null. Unknown presence requires a supported fixed code: QUERY_FAILED,
QUERY_TIMEOUT, QUERY_OUTPUT_LIMIT, QUERY_INVALID, WINDOWS_REQUIRED,
POWERSHELL_UNAVAILABLE or CANCELLED. The live runner normally represents
cancellation as a session outcome rather than adding a cancellation sample.

Input is limited to 1 MiB, 7,201 samples, eight JSON nesting levels, 40,000
nodes and 1,024-character strings. Duplicate keys, floating-point JSON numbers,
nonfinite values, extra fields, control characters, unsupported types and empty
sample arrays are refused. Names/IDs/device details are not supported replay
fields. This is an authored sample format, not native ETL/EVTX, a USB packet
capture, a Windows event-log export or a timestamped hardware ground truth.

## Session report

Reports have exactly these keys: `schema`, `mode`, `status`, `outcome`,
`requested_seconds`, `interval_seconds`, `selected_device`, `sample_counts`,
`samples`, `events`, `scope` and `privacy`. Schema is `outlands-usb-presence/1`.
Mode is demo, replay or live. Outcome is completed, cancelled or failed. Status
is REVIEW_REQUIRED if the session failed, has no samples or includes unknown
observations; otherwise OK. Cancellation is retained explicitly in outcome.
No physical-health conclusion is implied by OK.

The selected-device value is the constant alias `selected-device`. Sample counts
have exactly present, absent and unknown integer totals. Output samples have
elapsed_ms, state (present/absent/unknown), and code. Event rows have elapsed_ms
and kind. Privacy flags instance_ids, device_names, wall_clock, machine_identity
and raw_native_output are all false. Scope is fixed explanatory text.

Exports reconstruct the model from the report samples and compare the entire
result before writing; extra identifying fields, altered event summaries and
changed fixed privacy/scope values are refused. This protects this app's own
schema, not arbitrary third-party reports. Output is at most 2 MiB, stored as
UTF-8 JSON with ASCII escapes. Output needs a new .json file in an existing
absolute local parent; no links, traversal, UNC/device/ADS paths or existing
file replacement. Trusted, stable parents are required. It is not a hostile
filesystem sandbox and does not guarantee owner-private inherited Windows ACLs.
A write failure can leave a partial newly created file; no cleanup deletes it.

Replay uses default request settings (60 seconds, 2-second interval) only as
model fields; supplied elapsed samples define replay observations. It does not
claim to recover the original acquisition settings. Demo request fields are
explicit fictional settings. Live interval is a pause after query completion;
actual elapsed sample gaps also include query/runtime/scheduling overhead.

## Events and uncertainty

The first successful observation is initial_present or initial_absent. A first
unknown is observation_unavailable. Repeated states add samples/counts, not
repeated transition events. A known present-to-absent change is
disconnected_observed; known absent-to-present is reconnected_observed. Any
unknown state breaks this transition chain. A subsequent known state becomes
observation_resumed_present or observation_resumed_absent. It does not invent a
physical transition or exact transition time across a gap.

The elapsed event time is the observation time, not the actual disconnect time.
Counts are not uptime percentages or complete bus-event counts. Data are
sampled; between-query changes can be missed. No absolute date/time, source
filename, host ID, stable device fingerprint or raw exception text is included.
Relative timing/patterns remain potentially identifying and require review.

## Windows query boundary

The fixed Windows PowerShell command uses the built-in PnpDevice Get-PnpDevice
PresentOnly projection, selecting only instance IDs with the USB enumerator
prefix. At most 512 rows, 512 characters per ID, 256 characters per name and
256 KiB output are accepted. Duplicate IDs under case folding, unknown fields,
malformed output, process failure, timeout or over-limit output invalidate the
whole query. Only a fully accepted query can produce an absent observation.

Names and IDs exist in private process memory for local selection. Nothing is
automatically saved. The private `devices --live` selection output intentionally
contains IDs/names. Normal watch reports do not. A selected ID is compared
case-insensitively in Python; it is never inserted into PowerShell source.
The executable is selected from the Windows system directory, not PATH. User
profiles are not loaded, shell execution is disabled and no elevation is asked
by the app. Platform/module/permission support can still be unavailable.

One query has a 5-second processing deadline; cancellation/deadline/output
overflow terminates the app-owned query child. Cleanup has separate bounded
waits. No hard real-time guarantee covers process creation, a suspended OS or
termination failures. A long scheduling gap beyond supported elapsed bounds
ends the session as failed; it is not silently converted into a disconnect.
