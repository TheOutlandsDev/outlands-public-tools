# OUTLANDS Grouped Reports

Four independent MIT Python tools for checking declared report definitions, group membership and aggregate values, and comparing grouped outcomes across revisions. The tools work on supplied local JSON and use only the Python standard library.

Use Python 3.12 or 3.13 with pip. Choose an individual wheel or the collection from the [Grouped Reports wheel release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/grouped-reports-wheels-v1.0.0). Check the downloaded files against the release's SHA-256 checksums and the [pinned release manifest](release.json).

| Tool | Command after installation | Fictional demo |
| --- | --- | --- |
| [Grouped Report Contract Checker](../../tools/grouped-report-contract-checker/README.md) | `outlands-grouped-report-contract-checker` | `PASS` |
| [Group Membership Coverage Checker](../../tools/group-membership-coverage-checker/README.md) | `outlands-group-membership-coverage-checker` | `PASS` |
| [Grouped Aggregate Reconciler](../../tools/grouped-aggregate-reconciler/README.md) | `outlands-grouped-aggregate-reconciler` | `PASS` |
| [Grouped Report Scenario Comparator](../../tools/grouped-report-scenario-comparator/README.md) | `outlands-grouped-report-scenario-comparator` | `REVIEW_REQUIRED` with `GROUPED_OUTCOME_CHANGED` |

With your virtual environment active, install only the wheel you need and run its fictional demo.

```text
python -m pip install --no-index --find-links ./wheels outlands-grouped-report-contract-checker==1.0.0
outlands-grouped-report-contract-checker-demo
```

To install the collection, place the four individual wheels and the collection wheel in the same directory. The collection pins the four versions and provides a command that lists their entry points.

```text
python -m pip install --no-index --find-links ./wheels outlands-grouped-reports-collection==1.0.0
outlands-grouped-reports
```

Pass a JSON file with `--input FILE`. Add `--out FILE` if you want to create a separate report file. The CLI returns 0 for `PASS` and 1 for `REVIEW_REQUIRED`. The supplied scenario demo returns 1 because the changed definition affects the selected outcomes. Membership and aggregate checks also include separate review examples with an intentionally repeated contributor.

For Python callers, each `check` accepts raw JSON bytes and returns a report dictionary. The [component guide](components.json) gives exact imports, input and result formats, examples, expected findings, and limits.

```python
from importlib.resources import files
from outlands_grouped_report_contract_checker.contracts import check

sample = files("outlands_grouped_report_contract_checker").joinpath("examples", "input.json")
report = check(sample.read_bytes())
assert report["status"] == "PASS"
```

Use the membership check for row assignment and the aggregate check when a report also claims calculated values. Use the scenario comparator for a bounded check of two pinned definitions against the same supplied rows. Reports can include supplied identifiers and values. Keep real inputs and reports private. These checks do not execute SQL, access a database or network, or establish completeness of an external source.

## Rebuild and verify

The builder uses the exact public source ZIP SHA-256 from [Grouped Reports 4 v1.0.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/grouped-reports-4-v1.0.0). It reconstructs the ZIP from the pinned Git revision or accepts those same verified bytes through `--source-zip FILE`. In each wheel, the tool and its helper modules are isolated as package-relative imports. Original example bytes and MIT notices are preserved. Wheel entries have stable names, timestamps, modes, and hashes.

In a checkout with the pinned Git revision available, supply an empty directory outside the repository. Run the verifier with Python 3.12 or 3.13. It checks every pinned asset, each wheel's contents and metadata, and the commands and API after fresh offline installs.

```text
python -B integrations/grouped-reports/build_wheels.py --output EMPTY_EXTERNAL_DIRECTORY
python -B integrations/grouped-reports/verify_wheels.py --wheels THAT_DIRECTORY
```
