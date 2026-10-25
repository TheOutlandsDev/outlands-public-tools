# Offline Workflow Plan Checker review — 2026-10-25

This batch adds [Offline Workflow Plan Checker](../tools/workflow-plan-checker/README.md),
a fresh Python 3.12+ standard-library implementation of a neutral task dependency
and state contract. The private audit's lifecycle/worker-contract area supplied
the candidate boundary. No held original application, worker contract, source,
configuration, actual workflow, private record, credential or operational log
was selected, read, copied or executed. Existing source-family holds remain.
Only the existing public MIT control-file guard and reader-test pattern is
adapted. Reserved superscript device-name characters use explicit Unicode escapes.

## Declaration and output boundary

One bounded JSON control file declares 1 to 128 task IDs, each with 0 to 32
distinct prerequisite IDs and a state of `pending`, `in_progress` or `completed`.
Field sets and types are exact. Duplicate keys/task IDs/prerequisite IDs,
unsupported states, invalid ASCII tokens and extra fields are input errors.
No commands, executable paths, hosts, credentials, identities, logs, evidence,
timings, resources, private worker schema or application payload is accepted.

Every missing prerequisite, self reference and cycle member requires review.
Pending tasks can wait normally. Active and completed tasks require all direct
prerequisites to be declared completed; missing prerequisites never satisfy the
claim. All declarations are checked, so inconsistent ancestors cannot unlock
descendants. Cycle members are distinct from tails that depend on a cycle.

Any issue anywhere in the plan returns `REVIEW_REQUIRED` and withholds all
declared-order, eligible and waiting lists. This includes unrelated broken
branches; no apparently actionable partial result is offered. Local issue-free
rows do not imply valid ancestry. No missing record or state is silently repaired.

For a consistent plan the order includes every task with prerequisites first,
choosing the lexicographically smallest currently available ID at each step.
Eligible IDs are pending tasks with all prerequisites declared completed;
other pending tasks wait. Completed/active tasks are never eligible again.
These are declarations, not an execution history, authorization or scheduler.
No resource/concurrency/timing constraints, success, environment acceptance or
containment are modeled or independently verified.

Results retain IDs, counts, issue codes and inferred order/eligibility. Raw
state/requirement fields, input paths and native exceptions are omitted, but
the remaining relationships can still disclose a design. Actual plans/results
remain private; the format is not anonymization or publication clearance. No
task execution, command generation, plan mutation, scan or network probe occurs.
All action/authorization/state-verification flags remain false.

## Fictional validation

The local Windows/Python 3.12.7 utility suite discovered 46 methods: 44 passed
and two unavailable native-link operations were skipped. Skips are not passes.
Checks include strict fields/types, state claims, branching dependencies,
missing/self/cyclic links, global withholding, ancestor blocking, permutation
invariance, maximum depth, input preservation and no-side-effect behavior.

Reference checks use different algorithms: all 512 three-node dependency graphs
are checked with path-based cycle detection; acyclic cases use brute-force
topological permutations. All 216 ordered three-node DAG/state combinations
check literal completion/eligibility rules. Three hundred seeded valid plans
also check eligibility; the first 100 use brute-force order comparisons.
These are metadata-model fixtures, not proof of real task execution or success.

A separate fresh-process walkthrough passed 32 scenarios using a single-script
copy outside the collection and fictional records only. It exercised shipped
examples, active/completed/missing claims, branches, duplicate/unknown fields,
unsupported values, malformed JSON, BOM/encoding/byte limits, arguments, missing
input and static help/version. Input/script bytes were preserved; review cases
withheld every order/next-step list. No bytecode or extra runtime source appeared.

The collection regression discovered 473 methods: 450 passed and 23 were skipped,
with no failures/errors. Ruff checks/formatting and 269 local Markdown/JSON checks
passed. Dedicated CI targets Windows/Ubuntu with Python 3.12/3.13; exact-commit
Actions results record executed jobs and native skips. Synthetic metadata checks
and native filesystem observations are separate evidence.

## Filesystem and publication limits

The selected UTF-8 control file is limited to 64 KiB, with an optional BOM.
Sampled ordinary-file/single-link/ancestor and descriptor/path identities are
checked before, during and after reading. Link/reparse forms, reserved/ambiguous
paths and original trailing dots/spaces are refused. Original path parts are
validated before Windows absolute normalization can erase a trailing suffix.

Use stable trusted local control files. Sampled checks are not an atomic
snapshot, hostile-filesystem sandbox, mount-alias guarantee or blocked-I/O
deadline. OS storage can involve a network filesystem without a probe in this
program. Fixed CLI errors omit supplied/native values; formatted library
tracebacks can retain Python source locations. No future record is sanitized
or cleared merely because this checker accepts its declarations.

The exact changed-file export receives a separate pattern/private-marker review
and byte inventory. Private markers, scanner findings, test runtime outputs,
source mappings, publication receipts and the private audit ledger stay outside
the public repository. This batch does not clear unrelated imports, Git history,
held applications or source/data families. Existing v0.1.0 release assets remain
unchanged by this addition. Selected original code, tests, documentation and
fictional examples use MIT with TheOutlandsDev attribution; no third-party
implementation or runtime is bundled.

Concurrent configuration-review additions were preserved when rebasing onto
current main. This batch does not extend their source-clearance or validation
scope; its publication inventory contains only the 15 workflow-related changes.
