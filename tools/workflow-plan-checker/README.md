# Offline Workflow Plan Checker

Review a bounded JSON declaration of task dependencies and states. Python 3.12+,
standard library only. The checker reads one explicitly selected control file
and prints JSON to stdout. It creates no report files and executes no tasks.

`DECLARED_PLAN_CONSISTENT` describes this format's declarations. It does not
prove task execution, prerequisite success, authorization or a safe operational
schedule. No command, path, host, credential, identity, log, evidence, timing or
resource field exists. Keep actual plans and results private: IDs and dependency
order can disclose a workflow even when raw prerequisites and states are omitted.

## Fictional walkthrough

Run from the collection root:

```text
python -B tools/workflow-plan-checker/workflow_check.py --plan tools/workflow-plan-checker/examples/valid-plan.json
```

Exit **0**, `DECLARED_PLAN_CONSISTENT`. `sample_prepare` is declared completed;
`sample_check` is pending and eligible by the supplied prerequisites;
`sample_package` is pending and waiting. The declared order is `sample_prepare`,
`sample_check`, `sample_package`. These are invented IDs, not executable steps.

```text
python -B tools/workflow-plan-checker/workflow_check.py --plan tools/workflow-plan-checker/examples/missing-prerequisite.json
python -B tools/workflow-plan-checker/workflow_check.py --plan tools/workflow-plan-checker/examples/cycle.json
python -B tools/workflow-plan-checker/workflow_check.py --plan tools/workflow-plan-checker/examples/invalid-completion.json
```

Each returns exit **1**, `REVIEW_REQUIRED`. Respectively these declare a missing
prerequisite, a dependency cycle, and a completed task whose prerequisite remains
pending. All order, eligible and waiting lists are withheld as empty. No task or
state is repaired, inferred or advanced. The examples contain fictional metadata
only; no real project, worker, service, server or runbook is needed.

## Exact contract

```json
{
  "schema_version": 1,
  "tasks": [
    {"id": "sample_prepare", "requires": [], "state": "completed"},
    {"id": "sample_check", "requires": ["sample_prepare"], "state": "pending"},
    {"id": "sample_package", "requires": ["sample_check", "sample_prepare"], "state": "pending"}
  ]
}
```

All shown field sets are exact. Schema version is integer `1`; there are 1 to
128 tasks. Task and prerequisite IDs match `[a-z][a-z0-9_-]{0,39}`. Task IDs are
globally unique. `requires` is a list of 0 to 32 distinct prerequisite IDs; every
referenced task must be declared. Multiple prerequisites and branches are
supported. Self references and every cycle member require review.

`state` is exactly `pending`, `in_progress` or `completed`:

- Pending tasks can wait for incomplete prerequisites without an issue.
- An in-progress task requires every direct prerequisite to be declared
  completed; otherwise its active claim requires review.
- A completed task also requires every direct prerequisite to be declared
  completed. A missing prerequisite never satisfies either claim.

Root tasks can have any of the three states. Completion is a declaration, not
verified success or evidence. Completed prerequisites are checked themselves;
an inconsistent ancestor cannot unlock descendants. No failure, skipped-task,
optional-dependency, retry, historical-state or transition semantics are implied.

Unknown fields, duplicate JSON keys/task IDs/prerequisite IDs, unsupported states,
invalid tokens and wrong types are input errors. Values are not coerced, expanded
or ignored. This is a fresh neutral convention, not an importer for private
worker contracts, shell scripts, CI YAML or another workflow product's schema.

## Issues and deterministic output

Task result rows are sorted by ID. Their local `issues` use this fixed order:

| Code | Meaning |
| --- | --- |
| `PREREQUISITE_NOT_FOUND` | At least one referenced task is absent |
| `SELF_DEPENDENCY` | The task requires itself |
| `DEPENDENCY_CYCLE` | The task belongs to a directed dependency cycle |
| `COMPLETED_PREREQUISITES_UNSATISFIED` | A completed task has missing or noncompleted prerequisites |
| `ACTIVE_PREREQUISITES_UNSATISFIED` | An in-progress task has missing or noncompleted prerequisites |

Only actual cycle members receive the cycle code. Descendants can have no local
issues while their ancestry is invalid. **Any issue anywhere in the plan** makes
the overall status `REVIEW_REQUIRED` and withholds all three lists, including
unrelated apparently eligible branches. No partial order or next-step advice is
returned for an inconsistent declaration.

For a consistent plan:

- `declared_order` contains every task, including completed/in-progress tasks,
  with prerequisites before dependents. At each step, the lexicographically
  smallest currently available ID is selected. It is a dependency ordering,
  not an instruction to rerun completed tasks or start in-progress tasks again.
- `eligible_next_ids` contains pending tasks whose direct prerequisites are all
  declared completed. Completed/in-progress tasks are never eligible again.
- `waiting_ids` contains the other pending tasks. Both ID lists are sorted.

Counts summarize tasks, declared edges, each state, tasks with issues and cycle
members. Raw state/requirement fields, input paths and native exceptions are not
echoed. IDs, counts and order still reveal design information; output is private
metadata, not anonymization. Use the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md)
for real inputs, captured stdout and operational records.

Eligibility is a static consistency result, not execution authorization or a
scheduler. Resource conflicts, concurrency limits, time windows, operator rights,
environment state, task success and containment are not modeled or verified.
All execution, authorization, state-verification, command-generation, scan,
mutation and network-probe flags remain false. The checker has no command runner,
service control, background watcher, network integration or task-state write.

## CLI and reader limits

`--plan CONTROL_JSON` is required; `--help` and `--version` are static. Exit `0`
means consistent declarations, `1` means review, `2` means input/argument error,
and `130` means interrupted. Fixed errors omit supplied values and native detail.

The selected control file is UTF-8, up to 64 KiB; an optional UTF-8 BOM is accepted.
Task/edge bounds and the byte bound all apply. Nonstandard numeric constants are
refused. Ordinary single-link files and ordinary ancestors with usable sampled
identities are required. Metadata is checked before/during/after a bounded read.
Link/reparse forms, UNC/device paths, traversal, drive-relative paths, reserved
Windows names and trailing dots/spaces are refused. Original path parts are
checked before absolute-path normalization can erase a trailing suffix.

Use stable trusted local control files. These sampled checks are not an atomic
snapshot, hostile-filesystem sandbox or mount-alias guarantee. Underlying OS
storage can involve a network filesystem even without an explicit network probe.
A byte limit cannot interrupt blocked OS I/O. A library caller formatting an
exception can still expose Python source locations; fixed CLI errors are not a
traceback anonymizer or publication clearance for future records.

## Tests and provenance

```text
python -B -m unittest discover -s tests -p test_workflow_plans.py -v
```

The local Windows/Python 3.12.7 suite discovered 46 methods: 44 passed and two
unavailable native-link operations were skipped. It covers all 512 three-node
graphs with an independent path-cycle oracle, 216 acyclic graph/state
combinations, 300 seeded valid plans and 100 brute-force ordering comparisons.
It also exercises malformed contracts/JSON, input preservation, bounded deep
graphs, output privacy and a standalone single-script child process. Skips are
not passes. CI targets Windows/Ubuntu with Python 3.12/3.13; consult the exact
commit's Actions results for executed platforms.

See the [batch review](../../docs/BATCH-16-WORKFLOW-PLANS.md) for publication
scope and evidence. No held application, worker contract, source, configuration,
actual plan, private record, credential or operational log was selected, read,
copied or executed. The control-file guard and reader tests adapt this
collection's existing public MIT checker pattern from commit
`dfe7479baa11a402b6e273de29ff770a0e5c7176`; reserved superscript device-name characters
are expressed with explicit Unicode escapes. No third-party runtime or
implementation is bundled. Selected original code/docs/tests and fictional
examples use [MIT](../../LICENSE), attributed to TheOutlandsDev.
