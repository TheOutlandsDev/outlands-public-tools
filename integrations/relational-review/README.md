# Install and use the relational review tools

Review declared table structures, supplied typed rows, join multiplicity and
explicit query-result records. Start with the [definitions and method](../../methodology/RELATIONAL-REVIEW.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel provides a CLI, embedded fictional demo and actual documented Python API.
Supply Python 3.12 or 3.13; runtime code uses only the standard library.

| Tool | When to use it | Fictional input and expected output | What the result establishes |
| --- | --- | --- | --- |
| [Relational Schema Diff](../../tools/relational-schema-diff/README.md) | Explain selected table/column/key declaration changes. | Identical schemas PASS; one label changing to nullable returns REVIEW_REQUIRED with that change retained. | Descriptive differences between valid declarations. |
| [Key & Reference Checker](../../tools/key-reference-checker/README.md) | Review declared IDs and relationships against supplied rows. | Two entry references resolve and one nullable reference is explicitly skipped; a duplicate item ID withholds the whole summary. | Key/reference integrity within the selected typed rows and declared constraints. |
| [Join Cardinality Analyzer](../../tools/join-cardinality-analyzer/README.md) | Explain why repeated matches multiply a report. | Left a,a,b,null and right a,a,a,c,null gives inner=6/full_outer=10 with never_match; match gives 7/9. | Exact supplied equality-join counts under the selected null policy. |
| [Query Result Checker](../../tools/query-result-contract-checker/README.md) | Check supplied report shape and exact input bindings. | One correctly typed result row with matching actual input pins passes; required-complete plus truncated=true withholds the summary. | Column/type/row-bound consistency, actual embedded input pins and declared truncation policy. |

No database is opened, SQL executed, migration applied or joined rows created.
Query text is opaque; placeholder correspondence and returned values against SQL
are unverified. A structurally valid unrelated result can PASS. Source guides
define the bounded type system, full schemas, row accounting, refusal and I/O limits.

## Install one tool or the four-tool collection

Download the selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/relational-review-wheels-v1.0.0).
Verify SHA-256. One tool needs only its own wheel; the collection needs all five
wheels in one directory outside source. Create a fresh environment using
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_relational_schema_diff-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-relational-review-collection==1.0.0
```

On PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`; on Ubuntu use
`./ENV/bin/python`. Commands are in that environment's Scripts or bin directory.
Run `outlands-relational-schema-diff-demo` for the embedded fictional example or
`outlands-relational-schema-diff --input PRIVATE_JSON` for selected input.
Use literal wheel/command names in components.json for the other tools.
`outlands-relational-review` lists all four commands. Wheels are downloadable
assets; no package-index registration is implied. Actual schemas and reports stay private.

## Call a tool from another project or AI workflow

This literal example calls the schema comparison API with its embedded fixture:

```python
from importlib.resources import files
from outlands_relational_schema_diff.schema_diff import compare
raw = files("outlands_relational_schema_diff").joinpath("examples", "input.json").read_bytes()
report = compare(raw)
assert report["status"] == "PASS"
assert report["changes"] == []
assert report["sql_executed"] is False
```

The four operations are `schema_diff.compare`, `keys.check`, `joins.analyze`
and `results.check` under the packages listed in components.json. AI callers can
read exact formats, imports, examples, result fields and limits there. Pass raw
JSON bytes; inspect status, issues, counts and derived fields together. Schema Diff
retains valid differences on REVIEW_REQUIRED; the other tools withhold their whole
summary after findings. CLI exits are 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal.
Malformed outer API input raises a fixed refusal. Keep schema order, typed rows,
explicit null policy and hash domains intact; never treat join PASS as key integrity.

## Worked workflow and project connection

With the collection installed, run
`python -B integrations/relational-review/exercise.py` from the repository root.
It uses one invented inventory snapshot for schema/key review, join counting and
a supplied one-row result. It compares schema pins and independently recomputed
input pins, then demonstrates a retained schema difference, duplicate-key failure
with increased join multiplicity, required versus permitted truncation, matching
false pins that still fail, and an unrelated result that passes only structure.
The separate null-policy case checks inner/full-outer counts 6/10 versus 7/9.

The [SQL & Report Workbench](../../systems/sql-report-workbench/README.md) is a
related local application that materializes selected SQLite snapshots and executes
explicit saved queries. A caller-owned adapter must map its dataset/table/column
types, order, nullability, keys and physical rows into these bounded declarations,
preserving unsupported-type refusals and explicit scope limits. Map exact saved
query text, bindings, result column order and truncation separately. The Workbench
caps returned rows at 200; these tools' maximum is a separate declared bound,
not permission to silently discard or invent rows. Recompute these raw-input pins;
Workbench snapshot, revision and artifact hashes use different domains and cannot
be substituted. SQLite behavior, parameter binding and execution provenance require
their own evidence. No adapter or live Workbench integration is implemented or
qualified. Source databases, query text, credentials, bindings, results, journals
and exports stay private. A consistency report does not authorize database changes
or publication.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/relational-review/build_wheels.py --output DIRECTORY` and
`python -B integrations/relational-review/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Fixed synthetic archive metadata retains public MIT attribution and required package
metadata. Windows/Ubuntu Python 3.12/3.13 checks fresh-install each tool and the
collection, run CLI/demo/API/review cases, execute the worked workflow and literal
API example, and compare exact bytes. Anonymous public-download installs repeat
after publication. Qualification covers fictional declarations and package behavior.
