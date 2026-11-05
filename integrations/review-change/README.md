# Install and use the review and change-management tools

Start with the [plain-language definitions](../../methodology/REVIEW-CHANGE.md)
and [machine-readable component guide](components.json). Each of these four MIT
Python packages runs independently, with a command, an embedded fictional demo and
`check(raw_json_bytes)` API. Supply Python 3.12 or 3.13; runtime code uses only the
standard library.

| Tool | When to use it | Fictional input and result | What the result establishes |
| --- | --- | --- | --- |
| [Review Queue Checker](../../tools/review-queue-contract-checker/README.md) | Examine selected items, required roles and declared blockers. | One HVAC service-specification revision has quality/service coverage and no blockers: ready for manual review. A game fixture covers a quest review. | Queue declaration coverage for exact item snapshots. |
| [Correction Lineage Checker](../../tools/correction-lineage-checker/README.md) | Check a declared revision chain before reviewing a newer record. | service-v1 to service-v2 has one exact successor edge and changed artifact pins: complete declared history. | Consistent complete-history declarations under the chosen schema. |
| [Approval Scope Checker](../../tools/approval-scope-checker/README.md) | Reconcile grant and revocation claims for a chosen policy and as-of point. | Two grants at ordinal 10 cover quality/service at 20. Revoking quality at 20 makes quality missing at that same as-of point. | Coverage of declared roles from effective, exactly scoped claims. |
| [Change Impact Planner](../../tools/change-impact-planner/README.md) | Plan rechecks from selected changes and supplied dependency edges. | One changed service specification reaches its plan and summary: three recheck nodes; one disconnected demo node stays outside the closure. | Propagation within the supplied acyclic graph. |

The original tool guides define complete schemas, exact pin encodings, row accounting,
refusals and limits. `components.json` names every API, input/result format, example
and result field for human or AI-assisted discovery. `PASS` never authenticates a
reviewer, proves a correction occurred or authorizes publication or target changes.

## Install one tool or the four-tool collection

Download the selected wheel(s), `MANIFEST.json` and `SHA256SUMS.txt` from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/review-change-wheels-v1.0.0).
Verify each wheel's SHA-256. One tool needs only its own wheel; the collection needs
all five wheels together in a directory outside the source checkout. Create a fresh
virtual environment with `py -3.12 -m venv ENV` on Windows or
`python3.12 -m venv ENV` on Ubuntu, then use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_review_queue_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-review-change-collection==1.0.0
```

On Windows PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`;
on Ubuntu use `./ENV/bin/python`. Commands are in the environment's Scripts or bin
directory. Run `outlands-review-queue-contract-checker-demo` for its embedded
fictional fixture, or `outlands-review-queue-contract-checker --input PRIVATE_JSON`
for a selected private input. Substitute any other wheel/command from the component
guide. `outlands-review-change` lists the four group commands. No package-index
registration is implied.

## Call a tool from another project

This literal example reads only an embedded fictional revocation fixture. It
creates no approval events, records or output files.

```python
from importlib.resources import files
from outlands_approval_scope_checker.approvals import check
raw = files("outlands_approval_scope_checker").joinpath("examples", "needs-review.json").read_bytes()
report = check(raw)
assert report["status"] == "REVIEW_REQUIRED"
assert report["assessment"]["items"][0]["missing_roles"] == ["quality"]
assert report["review_scope_sha256"] is None
assert report["approval_authority_verified"] is False
```

For actual project data, map complete selected snapshots, policies and event claims
explicitly. Inspect status, assessment and scope pins together. Invalid outer input
raises a fixed refusal in the API; the CLI translates it to exit 2. A missing scope
pin withholds qualification. An impact result is a set of rechecks, not an execution
schedule, and undisclosed real dependencies remain unknown.

## Worked methodology and system connection

Run the [installed exercise](exercise.py) with the collection environment's Python.
It validates a two-revision fictional correction chain, explicitly maps its second
snapshot to a selected item, checks quality/service grant claims, and derives queue
coverage from the active grants. It then checks three recheck nodes from one changed
root. A second case revokes quality, recomputes queue coverage and requires review.
A stale dependency fixture withholds the impact assessment rather than producing a
partial plan. These are explicit teaching mappings; installing the group does not
connect the tools into an automatic pipeline.

The [Assessment & Evidence Workbench](../../systems/assessment-evidence-workbench/README.md)
records immutable snapshots, retests, review decisions and private exports. A future
caller-owned adapter could map selected assessment/finding revisions to item snapshots,
replacement histories to correction edges and review assertions to explicit policy,
role, reviewer and ordinal claims. It must define those mappings, preserve revocations,
select the exact revision under review, distinguish snapshot IDs from record IDs and
supply a reviewed dependency graph. Workbench review commands do not automatically
match these schemas, and hash-linked history does not establish reviewer authority.
No adapter or live integration is included or qualified here. Actual assessments,
reviewer identifiers, notes, evidence bytes and export records stay private.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/review-change/build_wheels.py --output DIRECTORY` and
`python -B integrations/review-change/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Fixed synthetic wheel metadata retains public MIT attribution. Hosted Windows/Ubuntu
Python 3.12/3.13 qualification fresh-installs individual wheels and the collection,
runs demos, APIs, review fixtures, the worked exercise and this literal API example,
and compares all five wheels and two manifest bytes. Anonymous public-download
checks repeat after release. These checks establish package behavior on fictional
inputs, without authenticating approval, applying corrections or updating targets.
