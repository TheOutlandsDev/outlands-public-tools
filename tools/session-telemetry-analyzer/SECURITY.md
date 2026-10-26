# Security and private-data boundaries

This is an offline saved-file inspector with no network, upload, live capture,
game launch, device action or subprocess in production code. It reads explicit
stable regular files and creates only fresh reports. It does not collect files
automatically, modify inputs or follow linked paths. Use private local folders
you control; regular-file and change guards are not an OS sandbox against a
hostile concurrent writer or directory replacement.

Input bytes/lines, JSON structure/tokens, records, visibility entries and report
sizes are bounded. Malformed selected rows remain explicit coverage; resource
failures stop inspection. Unknown raw fields and upstream exceptions are never
reflected into reports. Static HTML escapes the report and uses no scripts or
external assets. It is a rendering of observations, not a security finding.

Omitted names/identifiers do not anonymize hashes, sizes, times or statistical
structure. Keep raw telemetry and identifying reports private. Before sharing,
replace actual captures with a small invented fixture. Use the repository's
security reporting route if available for a suspected vulnerability; otherwise
open a minimal issue without secrets or exploit-sensitive personal data.

No finding, checksum or successful parse proves capture completeness,
authenticity, authorship, runtime health, multiplayer correctness or safe game
configuration. Inspected inputs retain their own rights and publication limits.
