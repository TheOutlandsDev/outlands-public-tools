# Management contract

The instance format is `outlands-assessment-evidence-workbench-v1`; managed documents
use `outlands-assessment-management-v1`. Creation declares assessment ID, title,
owner, scope, authorization reference and optional handling notes, plus actor/reason.
The assessment header stays fixed; create a separate assessment for changed scope.

`submission` adds a globally unique record ID, series ID, positive integer revision,
title, package kind (`source`, `build`, `installer`, `container`, `evidence`) and
canonical base64 opaque bytes. Hash/size are computed internally. Same-series
revision duplicates fail. IDs use lowercase letters, digits, underscores/hyphens,
starting with a letter, at most 40 characters. They are labels, never filesystem
paths. Output filenames are app-generated tokens; original names are not inferred.

`finding` declares submission ID, title, severity (`Informational`, `Low`, `Medium`,
`High`, `Critical`), description, impact, reproduction, evidence reference and
remediation. Submission bytes are pinned. New findings start at `New`, revision 1.
`amend` changes the narrative/severity fields of an open finding at an exact finding
revision. It preserves the received submission and increments the finding revision.

`transition` includes finding ID, expected revision, state, duplicate reference,
risk owner and review condition. Unused disposition fields must be empty strings.
`New`/`Triaged`/`Needs more info`/`Retesting` can move through the documented triage
dispositions. Direct resolution/retesting is unavailable. Terminal dispositions
can only reopen through `Triaged`. Duplicates point within the same assessment to
a different nonduplicate finding that is not already needed as a canonical target
by the finding being duplicated. Risk acceptance requires both owner and condition.

`retest` includes a unique ID, finding/replacement IDs, expected finding revision,
outcome (`Fixed`, `Not fixed`, `Inconclusive`, `Not performed`), reproduction notes,
positive-control notes, evidence reference and limitations. Original and replacement
receipt hashes are recorded. A retest increments the finding revision and moves it
to `Retesting`. One pending retest per current finding revision is allowed.
Changing the finding invalidates that pending review without deleting its record.
`review` accepts/rejects an unreviewed current retest with the expected finding
revision. Accepted `Fixed` becomes `Resolved`; all other reviews become `Triaged`.
The command actor/reason become the reviewer/review reason. These assertions have
no independently authenticated identity or evidence verification.

`legacy` imports one unchanged old neutral record collection per assessment. The
original parser and relationship checker are vendored unchanged. Structurally
valid inconsistent drafts are retained for review. They never create managed
findings or resolve them. Legacy exports roundtrip the parsed neutral object;
whitespace and JSON key order are not retained.

Every request rejects extra fields, malformed UTF-8, duplicate JSON keys, nonfinite
numbers, invalid scalar types and excessive nesting. See the README for storage
caps. A new public release contains no real scope, evidence or assessment records.
