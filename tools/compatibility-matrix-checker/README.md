# OUTLANDS | Compatibility Matrix Checker

Check explicitly requested symmetric component pairs against caller-declared exact rules. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B matrix.py --input examples/input.json
python -B matrix.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `matrix.check(raw_json_bytes)`.

## Contract

Input exactly `{format,components,rules,requirements}`; format
`outlands-compatibility-matrix-v1`. Component rows are
`{id,revision,version,contract_sha256}`; version is a symbolic ID with no range or
semantic-version ordering. contract_sha256 is opaque caller-supplied metadata.
Requirements are `{id,left,left_revision,left_sha256,right,right_revision,right_sha256}`;
rules have the same fields plus exact boolean `allowed`. Each endpoint binds the
full normalized component, including version and contract fingerprint. Self pairs
are rejected. Pairs are symmetric: ascending endpoint IDs normalize left/right with
their revisions/digests. Reversed identical rows with the same ID count as duplicates.
Different IDs claiming the same pair are ambiguous, even with the same decision.

Components and requirements must be nonempty. Rules may be empty. Every rule, including
unrequested pairs, must bind known exact components. Only explicit requirements are
assessed, not all component combinations. A missing rule produces unlisted, false
produces unsupported, and true produces supported. Unlisted/unsupported retain pair
diagnostics with REVIEW_REQUIRED and no qualified scope. All requested pairs declared
supported is not actual runtime compatibility. Unrequested_pairs_checked is false.
components_sha256, rules_sha256 and requirements_sha256 bind normalized cohorts.
No dependency resolution, version-range expansion, software discovery or execution.

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
