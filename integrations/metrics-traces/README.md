# Install and use the metrics and traces tools

Use these tools to review supplied metric definitions, recorded snapshots, span
graphs and explicit links. Start with the [definitions and method](../../methodology/METRICS-TRACES.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel includes a CLI, embedded fictional demo and check(raw_json_bytes) Python API.
Supply Python 3.12 or 3.13; runtime code uses only the standard library.

| Tool | When to use it | Fictional input and expected output | Result meaning |
| --- | --- | --- | --- |
| [Metric Definition Contract Checker](../../tools/metric-definition-contract-checker/README.md) | Validate selected measurements and label combinations. | Jobs counter, queue gauge and latency histogram with stage=preview: PASS with three bound series. Wrong label keys withhold assessment. | Declared kinds, limits, labels and revision/hash references agree. |
| [Metric Snapshot Reconciler](../../tools/metric-snapshot-reconciler/README.md) | Review one selected value per series/run. | Counter=2, queue=4 and latency buckets [1,1,0], count=2, sum=12: PASS; count=3 requires review. | Required coverage, scalar bounds and disjoint bucket accounting meet the rules. |
| [Trace Structure Checker](../../tools/trace-structure-checker/README.md) | Review declared operations and expected spans. | One report root with input and preview children: PASS; omit an expected child and coverage requires review. | Selected graph, interval and explicit coverage consistency. |
| [Metric-to-Trace Correlation Checker](../../tools/metric-trace-correlation-checker/README.md) | Check caller-selected point/span links. | Latency point at 15 linked to preview span [12,18): PASS; at 18 requires review. | Source records pass their contracts and required pinned links share a run and match time boundaries. |

No measurements are collected and no instrumentation is installed. Units and clocks
are caller declarations. A consistent link does not establish causation, semantic
relevance, actual latency or production health. Source guides define all required
fields, refusal limits, row accounting and structural/logical finding behavior.

## Install one tool or the four-tool collection

Download your selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/metrics-traces-wheels-v1.0.0).
Verify SHA-256. One tool needs only its own wheel; the collection needs all five
wheels in one directory outside source. Create a fresh environment with
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_metric_definition_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-metrics-traces-collection==1.0.0
```

In PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`; on Ubuntu use
`./ENV/bin/python`. Commands are in that environment's Scripts or bin directory.
Run `outlands-metric-definition-contract-checker-demo` for its embedded fictional
fixture, or `outlands-metric-definition-contract-checker --input PRIVATE_JSON` for
your selected input. Substitute literal wheel and command names from components.json.
`outlands-metrics-traces` lists the four commands. Wheels are downloadable assets;
no package-index registration is implied. Real inputs and reports stay private.

## Call a tool from another project or AI workflow

This literal example reads an embedded fictional fixture:

```python
from importlib.resources import files
from outlands_metric_definition_contract_checker.definitions import check
raw = files("outlands_metric_definition_contract_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert len(report["assessment"]["series"]) == 3
assert report["telemetry_collected"] is False
```

An AI caller can read components.json for exact format names, API imports, input
examples, review cases and result fields. Explicitly select complete snapshots and
preserve exact revisions, normalized hashes, symbolic units and the run clock basis.
Inspect status, assessment, issues and qualified_scope_sha256 together. CLI exits
are 0 PASS, 1 REVIEW_REQUIRED and 2 fixed refusal; malformed outer API input raises
a fixed refusal. Never turn missing measurements into zeros or accept a supplied
PASS field as evidence. The correlation checker recomputes the source contracts.

## Worked workflow and project connection

With the collection installed, run
`python -B integrations/metrics-traces/exercise.py` from the repository root.
The exercise selects the shared fictional HVAC report-run records from an embedded
fixture, verifies cross-tool pins, then demonstrates missing points/spans, a bucket
count mismatch, a stale link and the included-start/excluded-end boundary. Its
passing output retains causation_inferred=false; diagnostics remain declarations.

The [Data & Services Stack](../../systems/data-services-stack/README.md) is a
related application with configurable jobs, previews and saved run history. A
caller-owned adapter could define job counters, queue gauges and preview-latency
histograms for explicitly selected runs. It must define the unit and label mapping,
map saved run IDs/revisions to this exact contract, and supply span records and
their clock basis separately. Existing run history is not a trace and does not
supply missing timings. Its hashes are not interchangeable with these normalized
record pins. Counter snapshots do not calculate rates; histogram buckets here are
disjoint rather than cumulative. No adapter, collector, exporter or integration
is implemented or qualified. Private job inputs, journal data and reports stay private.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/metrics-traces/build_wheels.py --output DIRECTORY` and
`python -B integrations/metrics-traces/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates imports per package.
Fixed synthetic archive metadata retains public MIT attribution and required wheel
metadata. Windows/Ubuntu Python 3.12/3.13 checks fresh-install each tool and the
collection, exercise CLI/demo/API/review cases, run the installed workflow and literal
API example, and compare exact bytes. Anonymous public-download checks repeat after
release. Qualification covers fictional declarations and package behavior.
