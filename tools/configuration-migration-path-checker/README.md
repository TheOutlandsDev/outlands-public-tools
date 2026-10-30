# OUTLANDS | Configuration Migration Path Checker

Validate one explicit pinned migration path without opening adapters or running checks. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B migrations.py --input examples/input.json
python -B migrations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `migrations.check(raw_json_bytes)`.

## Contract

Input exactly `{format,contracts,source,target,steps}`; format
`outlands-config-migration-path-v1`. `contracts` is a nonempty cohort of field-metadata
contracts below. One selected revision per contract ID: model separately selected
snapshots with distinct IDs. Any invalid nested field rejects its whole contract row.
Selectors source and target are exactly `{id,revision,sha256}` bound to selected full
normalized contract definitions. Steps are
`{id,ordinal,from_contract,from_contract_revision,from_contract_sha256,to_contract,to_contract_revision,to_contract_sha256,adapter_sha256,required_checks}`.
Ordinal 1..1000 must be unique and contiguous from 1. Every from/to reference binds
the selected full contract. adapter_sha256 is an opaque declared fingerprint, never
opened or verified. required_checks is 0..32 distinct sorted symbolic IDs, never run.
Selected contracts have at most 4,096 fields in total and selected steps at most 4,096
check references in total; larger scopes are fixed refusals, not truncated reports.

The exact supplied chain must start at source and remain continuous with no repeated
contract ID/cycle. Gaps, ambiguity, stale/unknown references and cycles withhold the
complete assessment and all scope pins. A structurally valid chain ending short of
target retains target_reached false with REVIEW_REQUIRED. Empty steps is a valid
explicit no-op only when source equals target. No route search or shortest/best path.
The report includes ordered contract_ids/step_ids, union required_check_ids and false
checks_executed/adapters_opened. contracts_sha256, steps_sha256, source_sha256 and
target_sha256 pin normalized cohorts/selectors. A valid path establishes declaration
consistency, not value validity, adapter correctness, successful migration or readiness.

## Shared metadata, identity and safety rules

A field-metadata contract is exactly `{id,revision,fields}`. Fields, at most 128,
are `{id,type,required,default_sha256,constraint_sha256}`. Type is boolean, integer or
string; required is an exact boolean. default_sha256 is null or a fingerprint;
constraint_sha256 is a fingerprint. No raw defaults, constraints or values are accepted.
These metadata contracts are intentionally distinct from the value-checker's schema.
The connected acceptance test supplies an explicit fictional adapter, not automatic conversion.

IDs match `[a-z][a-z0-9_-]{0,47}`, revisions are integers 1..1,000,000, SHA-256 values
are 64 lowercase hex characters. Booleans never substitute for integers. Except the
128-field limit, identity cohorts have at most 1,000 rows. Identical normalized IDs
count once; conflicting groups exclude every member. Rejected/conflicting/duplicate
row accounting is complete. No last/latest/best selection. Hashes use ASCII JSON with
sorted keys, compact separators and a trailing LF; field/cohort rows are sorted by ID,
set-like check IDs sorted and matrix endpoints normalized. Raw input_sha256 hashes
the exact supplied file bytes. qualified_scope_sha256 exists only with no findings.

Structural ambiguity/malformed rows withhold complete assessment and scope pins;
well-formed logical findings retain diagnostics/pins but never a qualified scope.
Fixed shape/size/parser/selector refusals are errors, not partial assessments. Header
IDs and hashes are caller assertions. PASS verifies these limited declarations only,
not authenticity, privacy, rights, complete configuration, runtime behavior or authority.
All reports carry false settings_values_validated, runtime_compatibility_verified,
adapter_bytes_verified, migration_executed, configuration_changed, installation_performed,
execution_performed and target_changes_performed flags. No targets are modified.

Fingerprints do not anonymize or encrypt data: low-entropy values can be guessed.
Reports expose supplied IDs, aggregate hashes and diagnostics. Keep actual inputs and
reports private. These tools are not sanitizers, secret scanners or confidentiality controls.

One explicit input <=4 MiB. Strict JSON rejects duplicate keys, floats/nonfinite numbers,
invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside +/-10^18.
Escaped ASCII output <=8 MiB. Default stdout JSON; `--out` requires an absolute fresh
external file under an existing trusted parent outside source. No overwrite, traversal
or mkdir. Ordinary single-link inputs and trusted quiescent storage required. The
public [Windows/POSIX I/O guards](IO-SAFETY.md) retain POSIX parent descriptors/no-follow
checks and native Windows reparse/hardlink/change checks. They do not sandbox hostile
concurrent processes or guarantee parent ACL confidentiality. Failed writes can leave
partial/unconfirmed output: inspect privately and choose a fresh filename. Shell
redirection does not provide these output guards. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption. Error messages omit supplied paths/values.

Independent directories have no sibling runtime imports or third-party runtime packages.
No environment discovery, clock collection, network/provider access, original document
opening, includes, commands, installs, adapters, migrations or configuration updates.
Only fictional HVAC/game metadata is included; original private code, schemas, policies,
user/customer data, paths, credentials, addresses and operating configuration were not
consulted or selected. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
