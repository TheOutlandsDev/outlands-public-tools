# Orchard source release: inventory before packaging

**Intake.** Deliver a small fictional source handoff that another developer can
inspect without discovering the author's working environment. Include two text
inputs, an explicit source revision and an exact package inventory. Exclude real
settings, histories, credentials and operational data.

**Decision.** Preserve the selected baseline and compare a second inventory after
one edited file and one addition. Do not infer a verified rename, authorship,
atomic snapshot or deployment from reported hashes. Preserve the repository
layout so sibling helpers, dependency notices and fixtures travel with code.

**Validation procedure.** Run the three-example runner. Its first four commands
create two inventories, compare the baseline with itself, and compare it with the
edited tree. Expected statuses: `MATCHING_SELECTED_RECORDS`, then
`REVIEW_REQUIRED`. The package test independently checks every extracted member
against `PACKAGE-MANIFEST.json`, refuses undeclared/missing files and rejects a
changed file even when ZIP CRCs have been recomputed.

**Handoff.** Deliver the source ZIP, SHA256SUMS, source and packaging revisions,
requirements, expected outputs and platform-specific validation notes. Verify
the digest before extraction and retain the original download. The manifest
checks consistency; obtain its checksum through a separately trusted channel.

**Recovery.** A failed build can leave a new partial output directory. Preserve
it for inspection and choose another new destination for a retry. The builder
never replaces an existing output. No release snapshot is repaired in place.

**Evidence boundary.** The example is static/source and fictional command-line
evidence. Each included app keeps its own runtime and acceptance record.
