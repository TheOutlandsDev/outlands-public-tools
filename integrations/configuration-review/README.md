# Install and use the configuration review tools

Review selected configuration metadata, ordered overlays, component-pair rules
and migration paths. Start with the [definitions and method](../../methodology/CONFIGURATION-REVIEW.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel provides a CLI, an embedded fictional demo and its actual Python API.
Supply Python 3.12 or 3.13; runtime dependencies are standard library only.

| Tool | When to use it | Fictional input and expected output | What the result establishes |
| --- | --- | --- | --- |
| [Configuration Overlay Planner](../../tools/configuration-overlay-planner/README.md) | Explain ordered set/delete proposals and explicit replacement permission. | Two invented layers set three keys and explicitly replace queue_limit: PASS with three effective-field descriptors. Deny that replacement: REVIEW_REQUIRED with no effective fingerprint. | A consistent metadata proposal, not valid values or a generated settings file. |
| [Configuration Contract Diff](../../tools/configuration-contract-diff/README.md) | Describe field type, requirement, default-pin and constraint-pin changes. | Different contract headers with equal field metadata PASS and header_changed true. A field-metadata change requires review. | Exact descriptive metadata differences, not breaking-change or runtime compatibility inference. |
| [Compatibility Matrix Checker](../../tools/compatibility-matrix-checker/README.md) | Review explicit requested pairs against exact supplied rules. | One UI/worker pair with allowed true PASS; false is unsupported, and a missing rule is unlisted. | Requested-pair declaration coverage, not actual software compatibility or all pair combinations. |
| [Configuration Migration Path Checker](../../tools/configuration-migration-path-checker/README.md) | Review one supplied sequence of pinned contract references. | One declared source-to-target step PASS with target_reached true. A short chain remains review-required; a gap/cycle withholds assessment. | Exact path-declaration consistency, not adapter bytes, completed checks or a safe/executed migration. |

All inputs are assertions. No real setting values, configuration files, software
inventory or adapter bytes are read. PASS does not authorize applying settings,
installing software or running a migration. Reports can disclose supplied IDs and
hashes; keep actual inputs/reports private.

## Install one tool or all four

Download selected wheels and SHA256SUMS.txt from the immutable
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/configuration-review-wheels-v1.0.0).
Verify SHA-256 values before installation. Choose a fresh ENV outside the checkout,
then use `py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python and scripts directory, then choose one install:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_configuration_overlay_planner-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-configuration-review-collection==1.0.0
```

For the collection, place all five release wheels in WHEEL_DIRECTORY; exact-version
dependencies resolve offline. `outlands-configuration-review` lists the four commands.
Run `outlands-configuration-overlay-planner-demo` for embedded invented input or
`outlands-configuration-overlay-planner --input PRIVATE_JSON` for selected input.
Substitute the individual filename/command from components.json for another tool.
These are downloadable wheels; package-index registration is not implied. Earlier
source downloads remain available through each tool's catalog entry.

## Call a tool from another project

The operations are `overlays.check`, `contracts.check`, `matrix.check` and
`migrations.check` inside their distinct outlands_TOOL packages. Each takes raw
JSON bytes and returns a report dictionary, without sibling repository imports.
This complete example runs an installed tool with its embedded fictional input:

```python
from importlib.resources import files
from outlands_configuration_overlay_planner.overlays import check

raw = files("outlands_configuration_overlay_planner").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert len(report["assessment"]["effective_fields"]) == 3
assert report["settings_values_validated"] is False
assert report["configuration_changed"] is False
```

CLI exits are 0 PASS, 1 REVIEW_REQUIRED and 2 fixed refusal. Library refusals raise
the package's `toolkit.Rejected` exception. Structural findings withhold assessment
and scope pins. Logical findings retain diagnostics/pins without qualified scope;
overlay findings also withhold all effective fields and their fingerprint.

## Worked workflow and separate value validation

After installing all four, run
`python -B integrations/configuration-review/exercise.py` from the repository root.
Shared invented contract pins connect overlay review, header/field comparison,
requested pair decisions and one migration path. Identical declarations count once.
The exercise preserves denied overrides, absent defaults, stale references, ambiguous
identities and incomplete paths. It also shows that a changed adapter fingerprint
can remain a syntactically valid assertion without verifying any adapter bytes.

The separate [Configuration Contract Checker](../../tools/configuration-contract-checker/README.md)
validates explicitly supplied values against its own value-checker schema. It is
not included in these four wheels. Existing source CLI acceptance supplies invented
settings and an explicit schema mapping, checks the selected value fingerprints,
then demonstrates an out-of-range value requiring review. No fingerprints are
decoded into values and no automatic metadata-to-schema translation is claimed.

## Relationship to Environment & Setup Workbench

[Environment & Setup Workbench](../../systems/environment-setup-workbench/README.md)
uses versioned profiles, supplied observations, value checks, dependency planning
and reviewed private handoffs. Its profile configuration uses the value-checker
format `{schema_version,fields,rules}`, distinct from these metadata contracts
`{id,revision,fields}`. The workbench remains plan-only, with manual verification
NOT_PERFORMED and runtime_verified false; a reviewed plan can retain blockers.

A caller-reviewed adapter would need explicit field/key and profile/contract
identity/revision mappings; boolean/integer/string rules and optional/default
semantics; constraint/value fingerprint domains; layer precedence and replacement
permission; selected component/version/pair-rule evidence; and migration steps,
adapter provenance and independently supplied check evidence. Workbench profile
IDs, local case/length rules and journal hashes are not interchangeable with these
symbolic IDs or normalized contract pins. Its canonical JSON preserves list order;
these tools sort field/cohort IDs, check sets and symmetric endpoints. An effective
metadata fingerprint is not a workbench profile, evaluation or settings-file hash.

The workbench provides no automatic overlay import, pair-matrix evaluation or
migration runner for these formats. No adapter or live integration is included or
qualified by this release. Actual profiles, settings, notes, file lists, journals
and exported handoffs stay private; value-free summaries do not anonymize them.

## Build and qualification

Use Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute output
directories outside the checkout, then run:

```text
python -B integrations/configuration-review/build_wheels.py --output OUTPUT_DIRECTORY
python -B integrations/configuration-review/verify_wheels.py --wheels OUTPUT_DIRECTORY
```

Build verifies exact public SOURCE-MANIFEST pins for each selected entry,
toolkit.py, native_windows.py, decision_core.py, config_core.py, fictional examples,
README and MIT license. Relative imports isolate each wheel. Original tool source
is unchanged. ZIP headers use fixed synthetic metadata; standard package/license
metadata remains. SHA256SUMS.txt and release.json pin exact outputs.

Qualification runs the existing 12 standalone/cross-tool acceptance tests, two
byte-identical builds, fresh individual/collection CLI/demo/API/review cases, the
installed worked exercise and the literal API snippet above. Windows/Ubuntu
Python 3.12/3.13 builds compare exact bytes; anonymous public-download installs
repeat after release. This verifies package behavior on invented metadata, not
actual settings, runtime compatibility, adapters or real migrations.
