# OUTLANDS | Configuration Contract Diff

Compare exact field metadata without inferring breaking changes or runtime compatibility. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B contracts.py --input examples/input.json
python -B contracts.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `contracts.check(raw_json_bytes)`.

## Contract

Input exactly `{format,baseline,candidate}`; format `outlands-config-contract-diff-v1`.
Both sides are field-metadata contracts below; either field list may be empty.
The same (id,revision) with different normalized definitions is an identity conflict
and withholds the entire assessment and both scope pins. Identical definitions at
the same identity are valid. A changed header with equal field metadata can pass.

For the sorted union of field IDs, assessment.fields records state added, removed,
changed or unchanged and changed_attributes from type, required, default_sha256 and
constraint_sha256. Every addition/removal/attribute difference is REVIEW_REQUIRED;
header-only changes set header_changed without claiming incompatibility. The report
emits attribute names, not supplied default/constraint digests or underlying values.
all_field_metadata_equal refers only to these declarations; breaking_change_inferred
is false. baseline_sha256 and candidate_sha256 bind normalized complete definitions.
Constraint fingerprints are opaque: no widening/narrowing, schema translation,
default validation, semantic version ordering or runtime compatibility is inferred.

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
