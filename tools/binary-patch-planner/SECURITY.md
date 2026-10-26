# Security and privacy boundaries

Inspect files/plans you are authorized to use, under stable trusted parents you
control. Do not run this against live application files, devices, network shares
or concurrently edited input/output paths. The planner is bounded inspection and
optional new-file creation, not a filesystem sandbox against a hostile mutator.

Preview is default. Application is explicit, limited to equal-length edits,
and creates a new file exclusively. The full source hash/size and all expected
bytes must match. A valid plan or unsigned hash can still authorize harmful or
incorrect edits. There is no file-format, malware, compatibility, signature,
source ownership, runtime or power-loss durability proof.

The plan contains expected/replacement bytes. Reports omit those payloads and
local filenames, but their hashes/offsets/lengths can identify the source or
private change. Keep raw binaries, plans, reports and derivatives private until
separately reviewed. The report manifest covers JSON/HTML; a new candidate has
its separate receipt and caller-retained path mapping.

Failure can leave new partial files or a verified candidate without a complete
report. No source overwrite, automatic deletion or rollback is provided. Review
those files privately and use fresh destinations after resolving the failure.

For a vulnerability, initially describe only the impact and a fictional example
through the repository's reporting route. Do not publish private payloads,
credentials or identifying captures. Suggestions for stronger safeguards are welcome.
