# Offline Configuration Contract Checker

Check explicitly selected flat JSON settings against an explicitly selected
JSON contract. Python 3.12+, standard library only. The checker reads those two
bounded inputs and writes JSON to stdout. It does not contact a host, inspect
running software, execute programs, install packages, modify configuration or
create report files.

Passing means the supplied values meet the declared constraints. It does not
prove that a real application accepts the configuration, that dependencies work,
or that the configuration is secure or ready for runtime use.

## Fictional examples

Run from the collection root:

```text
python -B tools/configuration-contract-checker/config_check.py --contract tools/configuration-contract-checker/examples/contract.json --settings tools/configuration-contract-checker/examples/valid-settings.json
```

Expected exit: **0**, `NO_DECLARED_VIOLATIONS`, with five `PASS` checks. The
contract declares four fields and an integer ordering rule. Its sample keys,
values and constraints are fictional.

```text
python -B tools/configuration-contract-checker/config_check.py --contract tools/configuration-contract-checker/examples/contract.json --settings tools/configuration-contract-checker/examples/invalid-settings.json
```

Expected exit: **1**, `REVIEW_REQUIRED`. Two fields pass, the mode choice and
boolean type fail, and the integer ordering rule fails. One unexpected settings
key is counted without naming it; `issues` contains `SETTINGS_KEYS_UNDECLARED`.

```text
python -B tools/configuration-contract-checker/config_check.py --contract tools/configuration-contract-checker/examples/contract.json --settings tools/configuration-contract-checker/examples/incomplete-settings.json
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
[private workspace guide](../../docs/PRIVATE-WORKSPACE.md); do not replace the
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

The CLI accepts `--contract FILE`, `--settings FILE`, `--help` and `--version`.
It has no report-file option. Examples use Python's `-B` option to avoid
generating bytecode files.

## Provenance, licensing and validation

This is fresh neutral code and fictional data. No held operational source,
private configuration, source mapping, user record, credential, endpoint list
or third-party runtime payload is copied or executed. Selected original source
and examples use the repository's [MIT license](../../LICENSE), attributed to
TheOutlandsDev; this does not relicense operator inputs or third-party material.

See the [batch review](../../docs/BATCH-10-CONFIGURATION-CONTRACT.md) for actual
validation results and limitations. CI targets Windows and Ubuntu with Python
3.12 and 3.13. Offline fixture checks do not establish application behavior.
The [Diagnostic Evidence Plan](../../methodology/diagnostic-evidence-plan.md)
helps separate declarations, assertions, synthetic tests and runtime evidence.
