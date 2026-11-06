# Install and use the reliability and incident tools

Start with the [plain-language methodology](../../methodology/RELIABILITY-INCIDENT.md)
and [machine-readable component guide](components.json). Each independent MIT
Python wheel has a CLI, an embedded fictional demo and check(raw_json_bytes) API.
Supply Python 3.12 or 3.13; runtime code uses only the standard library.

| Tool | When to use it | Fictional input and output | What the result establishes |
| --- | --- | --- | --- |
| [Component Health Snapshot Checker](../../tools/component-health-snapshot-checker/README.md) | Review explicitly selected component observations. | A controller is declared healthy at ordinal 20, as_of=25, maximum_age=10: healthy/fresh. Equality at age 10 is fresh; age 11 requires review. | Consistency of selected health/freshness declarations. |
| [Incident Timeline Checker](../../tools/incident-timeline-checker/README.md) | Validate history and inspect state at a chosen point. | Open at 10, acknowledge at 15, resolve at 20, as_of=25: resolved_as_of=true. Removing resolution still yields a valid timeline, with resolved_as_of=false. | Ordered, correctly bound history under the transition rules. |
| [Alert Correlation Planner](../../tools/alert-correlation-planner/README.md) | Group supplied alerts with an explicit key and window. | Three same-partition alerts at 0,10,20 with window 10 produce two anchored groups; zero alerts are suppressed. | Grouping consistency, including inclusive non-sliding boundaries. |
| [Recovery Readiness Planner](../../tools/recovery-readiness-planner/README.md) | Review required roles and selected evidence. | Fresh declared health, resolution and restore-drill passes permit manual review; a failed resolution declaration blocks it. | Required declared evidence coverage for exact incident/check snapshots. |

The source guides define all required fields, row accounting, pins, refusals and
limits. Health is not measured, alerts are not sent, and recovery is not performed.
Timeline PASS does not establish resolution; a critical alert group may PASS its
grouping rules. Actual observation, evidence and authority remain unverified.

## Install one tool or the four-tool collection

Download the selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/reliability-incident-wheels-v1.0.0).
Verify SHA-256. One tool needs only its own wheel; the collection needs all five
wheels in one directory outside the source checkout. Create a fresh environment
with `py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_component_health_snapshot_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-reliability-incident-collection==1.0.0
```

On Windows PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`;
on Ubuntu use `./ENV/bin/python`. Commands live in the environment's Scripts or bin
directory. Run `outlands-component-health-snapshot-checker-demo` for its embedded
fictional fixture, or `outlands-component-health-snapshot-checker --input PRIVATE_JSON`
for a selected input. Substitute the literal wheel/command names in components.json.
`outlands-reliability-incident` lists the four commands. These are downloadable wheels;
no package-index registration is implied.

## Call a tool from another project

This literal example reads an embedded fictional fixture without probing anything:

```python
from importlib.resources import files
from outlands_component_health_snapshot_checker.health import check
raw = files("outlands_component_health_snapshot_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["all_declared_healthy_and_fresh"] is True
assert report["actual_health_verified"] is False
```

For a project input, explicitly map exact snapshots, revisions, policies, identities
and the ordinal time scale. Inspect status, assessment, issues and scope pins together.
REVIEW_REQUIRED exits 1; malformed outer API input raises a fixed refusal and the
CLI returns exit 2. A structural binding error withholds assessment/cohort pins;
logical findings retain diagnostic assessments but withhold the qualified scope pin.

## Worked methodology and system connection

Run `python -B integrations/reliability-incident/exercise.py` from the repository
root using the collection environment's Python. It checks a common fictional
controller snapshot across all four tools, groups three alerts into two anchored
windows, and explicitly maps health and incident-resolution reports into recovery
evidence while retaining an invented restore-drill declaration. A second case
demonstrates timeline PASS with an unresolved incident and blocked recovery review.
It also checks age equality/staleness, missing evidence and a stale component pin.
No automatic adapter or operational action is installed.

The [Reliability & Incident Workbench](../../systems/reliability-incident-workbench/README.md)
is a related offline recording application with services/signals, UTC snapshots,
maintenance windows, episodes, acknowledgements and private review/export records.
A caller-owned adapter must define service/signal aggregation into components,
convert exact UTC seconds into the explicit ordinal scale, preserve missing and
unknown states, and map revisions, incident episodes, alert keys and evidence roles.
Workbench maintenance windows are half-open; these age/window rules are inclusive.
Do not silently substitute one boundary rule for another. Workbench transition and
escalation semantics differ from these narrow declaration contracts; its existing
hashes and events are not interchangeable. No adapter or live integration is
implemented or qualified here. Workbench data, labels, notes, histories and exports
stay private. Neither a passing receipt nor a review flag authorizes publication.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/reliability-incident/build_wheels.py --output DIRECTORY`
and `python -B integrations/reliability-incident/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Fixed synthetic ZIP metadata retains public MIT attribution and required package
metadata. Hosted Windows/Ubuntu Python 3.12/3.13 checks fresh-install each tool and
the collection, run CLI/demo/API/review cases, the installed exercise and literal
API example, and compare wheel/manifest bytes. Anonymous public-download checks
repeat after release. Qualification covers fictional declarations and package
behavior, not independently measured health or actual recovery.
