# Diagnostic Evidence Plan

Plan the evidence needed to answer a narrow engineering question before
collecting anything. Copy this neutral template into a private project. A
completed plan records intent and observations; it does not authorize testing,
collect facts, prove isolation or assign a readiness score.

## Private working template

- Neutral claim ID and decision to support:
- Named acceptance criterion and explicit uncertainty:
- Authorized scope and excluded collection, with authorization retained privately:
- Permitted evidence class: static inspection, operator assertion, fictional fixture or direct runtime observation:
- Expected result, recorded before the observation:
- Actual observation label: not collected, operator-reported, synthetic-only, observed, inconclusive or contradicted:
- What the observation supports, and what it cannot establish:
- Opaque reference to retained private evidence and its handling restrictions:
- Remaining check, responsible reviewer and acceptance outcome, retained privately:

Do not turn an expected result into an observation. Use `observed` only for a
directly performed observation within its stated scope; it does not imply
independent verification or acceptance. Keep `operator-reported` and
`synthetic-only` explicit. Record contradictory and inconclusive outcomes.

## Fictional outcome examples

The following scenarios illustrate evidence labels. They are invented examples,
not records of tests performed on this collection or any real system.

| Claim | Evidence basis | Fictional outcome | Limit |
| --- | --- | --- | --- |
| `sample_presence` | Static metadata check of a fictional fixture | `synthetic-only`: an ordinary candidate was present | Presence does not establish execution, compatibility or version |
| `sample_assertion` | An operator supplies a boolean assertion | `operator-reported`: the operator supplied `true` | The assertion remains unverified; Environment Contract reports it as `UNKNOWN` |
| `sample_order` | Offline comparison of fictional settings | `synthetic-only`: the supplied lower value met the declared upper bound | This does not establish acceptance by a real application |
| `sample_runtime` | Direct runtime observation would be required | `not collected`: the plan contains no runtime evidence | Do not describe the feature as working or accepted |

An offline declaration check cannot substitute for a runtime observation. A
runtime observation does not automatically prove integration, recovery,
concurrency, sustained behavior or a named acceptance criterion.

## Handling and public boundary

Keep completed plans and real evidence private. IDs, relationships, statuses,
hashes and opaque references can still identify a project. Public examples
must be newly authored and fictional; removing obvious literals does not clear
an operational record for release.

Exclude original collector, launcher, reset and installation scripts; live-target
commands; host/account/hardware/process/service inventories; actual runtime
captures; names and device identifiers; private paths, endpoints and topology;
credentials, keys and tokens; logs, screenshots and operational timestamps;
backups, rollback records, approvals, findings and business records; source
mappings and uncleared vendor/runtime material. This template neither collects
nor sanitizes those materials.

Use the [Validation record](validation-record.md) for actual checks and retained
evidence, [Security assessment](security-assessment.md) for authorized scope,
and [Release review](release-review.md) before sharing a concrete export.
[Environment Contract Checker](../tools/environment-contract-checker/README.md),
[Connection Plan Checker](../tools/connection-plan-checker/README.md) and
[Offline Configuration Contract Checker](../tools/configuration-contract-checker/README.md)
have separate narrow validation boundaries. None proves production readiness.

This fresh neutral template uses the repository's [MIT license](../LICENSE),
attributed to TheOutlandsDev. No actual authorization, evidence or historical
operational record is included.
