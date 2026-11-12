# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for Python/venvs, fictional work, actual declarations,
stdout captures and qualification receipts:

```text
source/workflow-plan-checker-0.1.0/  selected source only
private/workflow-plan/
  venv312/                           separately created no-pip environment
  fictional_walkthrough.py           private copy of the usage driver
  fictional-demo/                    new owned task metadata only
  actual-plan.json                   real declaration, private
  captures/                          caller-selected stdout/diagnostics
  qualification/                     extraction, environments and receipts
```

Select the intended interpreter and `workflow_check.py` explicitly. Provide
`--plan FILE`; no default/environment plan, output writer, installer, command
runner, scheduler or task-state write exists. Only the selected JSON control
is read. The checker prints JSON stdout; shell redirection/caller code controls
captures and may overwrite them. Select new private capture paths deliberately.

The model accepts 1–128 tasks with 0–32 distinct prerequisites each and exactly
`pending`, `in_progress` or `completed` states. Completion is supplied metadata,
not verified success. Do not drop fields, invent prerequisite completion or
strip a private vendor format to force an actual workflow into this schema.

Any issue anywhere withholds all declared-order, eligible and waiting lists,
including unrelated apparently clean branches. A locally issue-free row does
not establish valid ancestry. For a consistent declaration, prerequisites
precede dependents, lexicographically smallest available IDs break order ties,
and only pending tasks with declared-completed prerequisites are eligible.
Completed/in-progress tasks are never offered as eligible again. None of this
grants execution rights or verifies resources, timing, concurrency or success.

Outputs omit raw states/prerequisites, selected paths and native details but
retain IDs/counts/issues/order/eligibility. Those fields can disclose a design.
Fixed errors do not anonymize caller logs/captures or formatted tracebacks.
Keep actual controls/results private and review a separate export before sharing.

Use fully spelled trusted canonical paths and stable ordinary files. Original
components are checked before absolute-path normalization and checked again
afterward. Input requires supported ordinary single-link/type/ancestor identities.
Observed links/reparse/special/multi-link inputs and sampled changes are refused.
Checks do not retain an immutable/atomic snapshot, deny all writers or establish
a hostile-filesystem boundary. Arbitrary mount/drive aliases, rebinding, remote/
cloud/virtual/live storage, blocked OS I/O, power loss and ACL privacy remain
outside acceptance. OS reads can involve network storage without a socket/DNS
probe. Reads can affect access metadata; Python caches are separate.

The selected control is at most 64 KiB, with bounded task/prerequisite counts
and tokens. These are not total CPU/memory/JSON-depth/deadline or storage quotas.
Require complete JSON and the actual exit/status; interruption or stdout failure
may leave partial captures. There is no checker-owned output tree to roll back.
Fictional walkthrough work is retained for inspection without automatic cleanup.
Requested modes depend on OS/Python/ACL behavior and are not a confidentiality
guarantee.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. No pip distribution,
network, model or account is needed; interpreters remain separately licensed.
Build/qualification outputs must be new private paths outside source with
existing parents. Publish reviewed source and sanitized actual validation only,
excluding operational plans/results, IDs/dependencies, personal paths,
credentials, private source, interpreter/dependency binaries and raw logs.
See [USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
