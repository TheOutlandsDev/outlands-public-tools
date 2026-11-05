# Review and change-management terms

Use these definitions with the [general terms](TERMS.md) and each tool's exact schema.
Examples contain fictional HVAC/game declarations. Real records and reports stay private.

| Term | Plain meaning | Precise meaning here |
| --- | --- | --- |
| Selected snapshot | The exact version being examined. | An item/node ID, integer revision and declared artifact SHA-256. A full-snapshot pin covers all fields; artifact bytes are not opened. |
| Review queue | Items awaiting a stated review step. | Explicit item-to-entry bindings with a stage ID, role coverage and blockers. A stage name does not establish completion. |
| Required role | A type of review the policy calls for. | A unique opaque role ID in the selected policy. Coverage is supplied or derived by a separately defined adapter; identities and authority are unverified. |
| Blocker | A declared reason an item is not ready. | A nonempty blocker list requires review even if every role is covered. The tool does not discover missing blockers. |
| Correction lineage | The stated chain of a record's revisions. | Start at revision 1 and bind every consecutive successor through an exact before/after edge with changed artifact declarations. No forks, merges or implicit latest revision. |
| Approval scope | Which exact item and policy a grant claim concerns. | Bind item revision/full snapshot, policy pin, reviewer ID, role and supplied event ordinal. This is declaration consistency, without real authorization. |
| Grant | A supplied claim that one review role approved. | An approve event with its own ID. It is active at as_of when effective and not revoked by a valid effective revocation of that exact grant. |
| Revocation | A claim that withdraws one specific grant. | Reference the exact earlier grant with matching item, policy, reviewer and role. Later reapproval remains a separate grant. Equality at as_of is effective. |
| As-of ordinal | The caller's chosen point in a declared sequence. | An explicit nonnegative integer using one common convention. Tools do not read clocks or infer dates/time zones. |
| Dependency edge | A stated relationship between two snapshots. | Direction is upstream to downstream: downstream depends on upstream. Every endpoint binds an exact selected snapshot. |
| Change impact | Which supplied nodes should be rechecked. | The union of explicitly changed roots and reachable downstream nodes, retaining every root cause. An acyclic supplied graph is required. |
| Unaffected node | A supplied node outside that propagation. | Outside the closure in the supplied graph only. It does not establish that a real asset is safe or that all dependencies were supplied. |

`PASS` means the supplied declarations meet the checked rules. Read the tool's
assessment and qualified scope pin. Missing roles, blockers or incomplete declared
history can retain diagnostics while withholding the scope pin; invalid graph or
snapshot scope can withhold the entire assessment. CLI exits are 0 for pass, 1 for
`REVIEW_REQUIRED` and 2 for fixed refusal. Hash consistency does not authenticate
reviewers, establish publication rights or authorize changes to a system.
