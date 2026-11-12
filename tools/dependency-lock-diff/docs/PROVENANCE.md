# Provenance and license scope

Offline Dependency Lock Diff compares two explicitly supplied locks in the
collection's deliberately narrow name/version/SHA-256 grammar. Its strict
parser and sampled input reader adapt public MIT mechanisms at collection
commit `c08b51509fa44629fbd0f50e1719f82fdde155ca`. Runtime, parser, CLI and result
contract remain preserved for the initial standalone release; its displayed
version was already 0.1.0.

Selected original source, tests, examples and docs retain the full
[MIT license](../LICENSE) and TheOutlandsDev identity. Standalone preparation,
qualification, documentation and authored fictional consumers used AI
assistance, without exclusive-authorship claims. Python/standard-library and
OS APIs retain their own terms and are not bundled as binaries.

All 41 original test method bodies and the `ReferenceTests.legacy_validator`
helper remain preserved. Standalone fixture resolution selects exact public
`lock_common.py` and `verify_locks.py` sources from baseline
`fd98a06f3b1d5a409f7ae3c308f96fa7d6a11116`, under
`tests/validator-fixture/tools/dependency-lock-tools/`. They support the original
pure parser-parity tests; their separate converter/validator file-I/O contract
is not newly qualified by this comparator release. Neither is a CLI/runtime
dependency or installed distribution. The original shared suite remains intact.

Original `.gitattributes`, example README and four fictional lock controls retain
their exact bytes, including BOM/line endings. Only authored fictional package
labels, version declarations and hashes ship here. No held original environment,
dependency configuration, private package name, credential, index endpoint,
package artifact, actual lock/result or operational record was selected, read,
copied or executed. Unrelated historical rights remain uncleared.

Version strings are compared as text rather than ranked or semantically
normalized. Declared hashes are not verified against package artifacts. Matching
or changed declarations do not establish installed state, authentication,
reproducibility, availability, platform coverage, licensing, vulnerability
status, compatibility or safe installation. A difference grants no permission
to replace, upgrade, downgrade or delete anything.

See the historical
[lock-diff review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-18-LOCK-DIFF.md),
[public validator contract](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/tools/dependency-lock-tools/README.md)
and [collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md).
Historical evidence is separate from actual standalone versions/counts/outcomes/
skips in release `VALIDATION.json`.
