# Offline Configuration Contract Checker

Check explicitly selected flat JSON settings against an explicitly selected
JSON contract. Python 3.12+, standard library only. The checker reads those two
bounded inputs and writes JSON to stdout. It does not contact a host, inspect
running software, execute programs, install packages, modify configuration or
create report files.

## Standalone source release 0.1.0

Download the reviewed source ZIP from
[configuration-contract-checker-v0.1.0](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/configuration-contract-checker-v0.1.0).
The ZIP contains source, tests, fictional examples and the full [MIT license](LICENSE).
Supply Python separately; no installer, pip distribution, interpreter,
runtime/dependency binary, actual configuration/result, private source or raw
log is bundled. The CLI needs only `config_check.py` and the standard library,
without a sibling tool, donor, network, model or account.

Fresh qualification selects Windows/Ubuntu with Python **3.12, 3.13, 3.14 and
3.15.2**, in new no-pip environments with zero installed distributions. It
selects all **44 original methods and 129 total assertion calls**, twelve local/shared
helper ASTs and 26 copied single-script CLI methods: **70 per lane, 560 across
eight lanes**. These are selected counts; actual versions, outcomes and named
skips belong to release `VALIDATION.json`. Historical evidence below is separate.
The runtime and four original controls retain exact baseline Git bytes; no new
scalar/rule, result, default application or input-path repair is introduced.
The assertion total is 128 inside test methods plus one in the preserved
`ContractFixture.reader_failure_traceback` helper.

Only a preserved ROOT-relative subprocess test needs an owned temporary runtime
mirror, copying the actual extracted script into its fixture hierarchy with
exact pre/post hashes. In-process tests load the actual extraction; independent
CLI consumers use one copied script. No duplicate runtime or unrelated shared
application is shipped. See [qualification](docs/QUALIFICATION.md),
[USAGE.md](USAGE.md), [private workspace](docs/PRIVATE-WORKSPACE.md) and
[provenance](docs/PROVENANCE.md).

Select the standalone original-method adapter explicitly:

```text
python -B -m unittest discover -s tests -p test_original_configuration.py -v
```

Passing means the supplied values meet the declared constraints. It does not
prove that a real application accepts the configuration, that dependencies work,
or that the configuration is secure or ready for runtime use.

## Fictional examples

Run from the extracted module directory:

```text
python -B config_check.py --contract examples/contract.json --settings examples/valid-settings.json
```

Expected exit: **0**, `NO_DECLARED_VIOLATIONS`, with five `PASS` checks. The
contract declares four fields and an integer ordering rule. Its sample keys,
values and constraints are fictional.

```text
python -B config_check.py --contract examples/contract.json --settings examples/invalid-settings.json
```

Expected exit: **1**, `REVIEW_REQUIRED`. Two fields pass, the mode choice and
boolean type fail, and the integer ordering rule fails. One unexpected settings
key is counted without naming it; `issues` contains `SETTINGS_KEYS_UNDECLARED`.

```text
python -B config_check.py --contract examples/contract.json --settings examples/incomplete-settings.json
```

Expected exit: **1**, `REVIEW_REQUIRED`: two fields pass, two optional fields are
`NOT_SUPPLIED`, and the ordering rule is `BLOCKED` because one operand was not
supplied. Optional absence is not a passing field value or an implicit default.

These commands read only the selected fictional JSON files. No fixture service,
installation or runnable configuration is needed.

## Contract format

The UTF-8 JSON object has exactly `schema_version`, `fields` and `rules`:

```json
{
  "schema_version": 1,
  "fields": [
    {"id": "sample_lower", "key": "lower_limit", "type": "integer", "required": true, "minimum": 1, "maximum": 16},
    {"id": "sample_upper", "key": "upper_limit", "type": "integer", "required": false, "minimum": 1, "maximum": 16}
  ],
  "rules": [
    {"id": "sample_order", "op": "less_or_equal", "left": "sample_lower", "right": "sample_upper"}
  ]
}
```

The schema version is the integer `1`. Declare 1 to 128 fields and 0 to 128
rules. Each field requires exactly `id`, `key`, `type` and `required`, plus only
the optional constraints allowed for its type:

| Type | Optional constraints |
| --- | --- |
| `boolean` | None; values must be actual JSON booleans |
| `integer` | Inclusive `minimum` and `maximum`, each a signed 64-bit integer |
| `string` | Inclusive `min_length` and `max_length`, each an integer from 0 to 4096; `choices`, a list of 1 to 32 unique strings, each at most 128 Unicode code points |

`required` must be an actual boolean. Minimum bounds cannot exceed maximum
bounds. Choices must satisfy any declared string length bounds. A JSON boolean
is not accepted as an integer, including in bounds or the schema version.

Field and rule IDs share one unique namespace: a lowercase ASCII letter,
followed by lowercase letters, digits, underscores or hyphens, at most 40
characters total. Keys are unique and case-sensitive: an ASCII letter or
underscore, then ASCII letters, digits, underscores or hyphens, at most 64
characters total.

Every rule has exactly `id`, `op`, `left` and `right`. The only operation is
`less_or_equal`. Its operands reference two distinct declared integer **field
IDs**, rather than settings keys or other rules. Repeated ordered operand pairs
are refused. There is no expression language, regular-expression constraint,
script or arbitrary validator.

Unknown contract fields, duplicate JSON keys/IDs/settings-key declarations,
invalid references, contradictory bounds and wrong types are refused. The
checker applies no defaults, coercion, case folding, Unicode normalization,
environment expansion or home-directory expansion.

## Settings and result semantics

Settings must be one flat JSON object containing at most 128 keys using the
same ASCII key syntax. Values may only be actual booleans, signed 64-bit
integers, or strings of at most 4096
Unicode code points. Arrays, nested objects, nulls, floating-point numbers and
nonstandard JSON numeric constants are outside this input format. String
lengths count code points, not encoded bytes or user-perceived characters.
String choices use exact equality.

Missing required fields fail. Missing optional fields are `NOT_SUPPLIED`, never
`PASS`. A cross-field rule is evaluated only when both operands are present,
correctly typed and individually constraint-valid. Missing operands produce
`BLOCKED` with `DEPENDENCY_NOT_SUPPLIED`; invalid present operands produce
`BLOCKED` with `DEPENDENCY_INVALID`. A blocked comparison cannot silently pass.
If one operand is missing and the other is present but invalid, missing-operand
`DEPENDENCY_NOT_SUPPLIED` takes precedence. No comparison is performed until
both operands are present and independently valid.
Unexpected settings keys create the fixed issue `SETTINGS_KEYS_UNDECLARED`
without echoing names or values.

Result checks contain only `id`, `kind` (`field` or `rule`), `status` (`PASS`,
`FAIL`, `NOT_SUPPLIED` or `BLOCKED`) and fixed `evidence`. Fields appear in
declaration order, followed by rules in declaration order. Counts are `passed`,
`failed`, `not_supplied`, `blocked` and `unexpected_settings`. Results omit
settings key names, raw values, bounds, choices, input paths and native errors.

The result scope is `DECLARED_FLAT_SETTINGS_ONLY`. Flags `network_probed`,
`programs_executed`, `configuration_modified` and `runtime_verified` are always
false. Exit `0` means `NO_DECLARED_VIOLATIONS`; exit `1` means `REVIEW_REQUIRED`
because a check failed, a rule was blocked, or settings keys were undeclared.
Optional fields can remain `NOT_SUPPLIED` without requiring review when no rule
needs them. Exit `2` means `ERROR` for invalid inputs, contracts or arguments;
interruption returns `130`. None establishes runtime readiness.

## Privacy and filesystem limits

IDs, statuses and relationships can disclose a design. Contracts also contain
settings key names, bounds and choices, which may themselves be sensitive.
Keep real contracts, settings and stdout private. The checker is not a secret
scanner, anonymizer, IP review or approval to publish operator inputs. Store
your own inputs outside the checkout using the
[private workspace guide](docs/PRIVATE-WORKSPACE.md); do not replace the
shipped fictional examples with real configurations.

Each selected input is limited to 64 KiB and must be a regular single-link file
with verifiable file/ancestor identities. Paths are bounded to 4,096 characters
and 64 parts; traversal, UNC paths, drive-relative paths and unsafe stream/device
forms are refused. Symlink/reparse paths, special nodes and detected metadata
changes are refused. These checks do not freeze a tree or create a
hostile-filesystem sandbox. Use stable trusted local storage. Although no
socket/DNS API is used, mapped-drive or mounted-share reads can involve the
operating system's network storage stack. Remote storage, arbitrary mount
aliases and concurrent writers are not proven safe. The size bound cannot
interrupt a blocked filesystem operation.

The two files are read sequentially; sampled identities do not establish an
atomic, coherent two-input snapshot. Path-component checks occur only after
absolute-path normalization. Use fully spelled canonical trusted paths and do
not assume original leaf/parent trailing-dot or trailing-space spellings are
refused. Actual fictional Windows probes on Python 3.12.7/3.15.2 tested both
contract and settings roles: canonical, leaf-dot, leaf-space and parent-dot
forms returned 0/`NO_DECLARED_VIOLATIONS`; parent-space returned
2/`INPUT_PATH_INVALID`. Input/runtime bytes were preserved. These mixed measured
observations do not establish blanket suffix refusal or universal alias safety.

The CLI accepts `--contract FILE`, `--settings FILE`, `--help` and `--version`.
It has no report-file option. Examples use Python's `-B` option to avoid
generating bytecode files.

## Provenance, licensing and historical validation

This is fresh neutral code and fictional data. No held operational source,
private configuration, source mapping, user record, credential, endpoint list
or third-party runtime payload is copied or executed. Selected original source
and examples use the full [MIT license](LICENSE), attributed to
TheOutlandsDev; this does not relicense operator inputs or third-party material.

See the historical
[batch review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-10-CONFIGURATION-CONTRACT.md).
The original local Windows/Python 3.12.7 suite discovered 44 methods: 42 passed
and two unavailable native-link operations were skipped. The collection run,
111 independent probes and 24 separate fictional CLI scenarios are historical
evidence; skips are not passes. Historical CI selects Windows/Ubuntu Python
3.12/3.13. Fresh standalone outcomes belong to release validation; neither
establishes application behavior. The
[Diagnostic Evidence Plan](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/methodology/diagnostic-evidence-plan.md)
separates declarations, assertions, synthetic tests and runtime evidence.
Standalone preparation used AI assistance without exclusive-authorship claims;
see [provenance](docs/PROVENANCE.md) and [notices](THIRD-PARTY-NOTICES.md).
