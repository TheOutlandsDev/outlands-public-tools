# Offline Dependency Lock Diff

Compare two explicitly selected locks in the collection's narrow name/version/
SHA-256 format. Python 3.12+, standard library only. This standalone script needs
no sibling module and creates no report files: it reads the two locks and prints
ASCII-escaped JSON to stdout. It downloads/installs nothing, invokes no package
manager, resolves no dependencies and does not inspect an installed environment.

Real locks and results remain private. Package names, versions, hashes and change
relationships can identify a project. This is declaration comparison, not
anonymization, artifact authentication, a vulnerability audit or installation advice.

## Fictional walkthrough

Run from the collection root:

```text
python -B tools/dependency-lock-diff/lock_diff.py --before tools/dependency-lock-diff/examples/before.lock --after tools/dependency-lock-diff/examples/after.lock
```

Exit **1**, `LOCK_DIFFERENCES_REPORTED`. Four before and four after records yield
one only in before, one only in after, one version-text change, one hash-only
change and one unchanged record. The version-change row also records whether
its hash changed. These are invented package declarations and fake artifact
hashes, not packages to install or real artifact recommendations.

```text
python -B tools/dependency-lock-diff/lock_diff.py --before tools/dependency-lock-diff/examples/before.lock --after tools/dependency-lock-diff/examples/hash-only.lock
python -B tools/dependency-lock-diff/lock_diff.py --before tools/dependency-lock-diff/examples/before.lock --after tools/dependency-lock-diff/examples/equivalent.lock
```

The first returns exit **1** with one hash-only change and three unchanged rows.
The second returns exit **0**, `MATCHING_LOCK_RECORDS`, despite different comments,
a UTF-8 BOM and hash-letter case. Exact raw input hashes still differ. See the
[fictional examples](examples/README.md). A file can also be compared with itself.

For actual work use two explicit lock files in an
[external private workspace](../../docs/PRIVATE-WORKSPACE.md). Absolute or ordinary
relative paths are accepted without environment expansion. Keep inputs, stdout
and privately saved results outside the checkout. There is no output-file option.

## Supported lock grammar

This parser preserves the narrow grammar of the existing public
[Dependency Lock Tools](../dependency-lock-tools/README.md). It is not general pip
requirements, a full PEP 440 parser, or a lock adapter for another ecosystem.

A package record is exactly `canonical-name==supported-version`, one space and
a backslash, immediately followed by a line with four spaces,
`--hash=sha256:` and 64 hexadecimal characters. See the fixture files for exact
bytes. There is one adjacent hash line per package. Records must be sorted by
canonical name and globally unique. Empty/comment lines are allowed between
records, not between a package and its hash. At least one package is required.

Names are 1–200 ASCII characters, start/end with a letter or digit and otherwise
contain letters, digits, dots, underscores or hyphens. Normalization lowercases
and collapses punctuation runs to a hyphen, but **lock input must already be
canonical**. Noncanonical names fail instead of being silently normalized/merged.

The fixed-version subset permits numeric release components, an optional numeric
epoch, lowercase numeric `a`/`b`/`rc` prerelease, `.postN`, `.devN` and a lowercase
alphanumeric local label. Version length is at most 128 characters. Valid
spellings outside this deliberate subset also fail. Version text is preserved;
it is never semantically ranked or normalized.

UTF-8 with an optional leading BOM is accepted. The existing parser's line-split
semantics are retained; normal LF, CRLF and CR locks are tested. Control characters
below ASCII 32 other than CR/LF fail, including tabs and terminal escapes.
Unsupported active lines, URLs/index directives, includes, extras, markers,
wildcards, editable/VCS forms, orphan/multiple hashes, duplicate packages and
unsorted entries fail. Comments are ignored, not copied into result records;
their raw bytes still affect the input digest and can fingerprint a private lock.

## Comparison semantics and output

Records match by canonical package name and appear sorted by that name.
SHA-256 text is normalized to lowercase before comparison. The classifications
are mutually exclusive:

| Classification | Meaning within supplied locks |
| --- | --- |
| `ONLY_IN_BEFORE` | No package declaration with that name in after |
| `ONLY_IN_AFTER` | No package declaration with that name in before |
| `VERSION_TEXT_CHANGED` | Both exist but version strings differ, regardless of hash |
| `HASH_ONLY_CHANGED` | Version text matches but declared hash differs |
| `UNCHANGED` | Name, version text and normalized hash match |

Each row includes before/after `{version, sha256}` records or null, plus separate
`version_text_changed` and `hash_changed` flags. Those flags are null for one-sided
declarations because no pair exists. A version change can have either a changed
or unchanged hash; hash-only counts never double-count version changes.

`1.0` and `1.0.0` are different text, even if another version system would treat
them as equivalent. No greater/less comparison, upgrade/downgrade direction,
compatibility or release chronology is inferred. A hash-only difference can
reflect artifact/platform selection or an edited declaration; it is not a
malware or vulnerability finding. Equal hashes are not independently checked
against artifacts, and even unchanged locks do not prove reproducibility,
platform coverage, source-index availability, licensing or safe installation.

`MATCHING_LOCK_RECORDS` means all compared declarations match. Any record
difference gives `LOCK_DIFFERENCES_REPORTED`. Neither describes installed
packages, authorized changes or an actual environment. Exact input file digests
are included separately; comments/BOM/newlines/hash-letter case can change them
without changing record classifications. Results omit raw comments, input paths
and native exceptions, but retained names/versions/hashes remain private metadata.

All filesystem-scan, package download/install, environment-inspection,
artifact-verification, resolution, advisory, direction-inference, lock-mutation
and network-probe flags are false. The code has no command runner, installer,
index query, artifact reader or environment collector.

## CLI, bounds and reader limits

`--before FILE --after FILE` are required. `--help` and `--version` are static.
Exit **0** means matching supported records, **1** differences, **2** a fixed-code
input/output/argument error, **130** interruption. Supplied package values,
selected paths and native error details are not echoed on rejection.

Each file is limited to 1 MiB, 6,000 lines, 512 characters/line and 2,000 packages.
Exactly two inputs are selected, so combined lock input is at most 2 MiB.
Serialized JSON is capped at 4 MiB before printing, plus the final newline.
An output-bound failure emits a fixed error rather than a partial comparison;
OS output failure/interruption can still leave partial captured output.

The reader requires ordinary single-link files and ordinary ancestors with
usable identities. It samples path/descriptor metadata before/during/after a
bounded read and rechecks both snapshots after comparison. Link/reparse forms,
UNC/device forms, parent traversal, drive-relative paths, Windows reserved names
and trailing dots/spaces are refused. Original path parts are checked before
Windows normalization can erase suffixes. No input is overwritten or repaired.

Use stable trusted local files. These sampled sequential reads are not an atomic
two-file transaction, hostile-filesystem sandbox or mount-alias guarantee. OS
storage can involve a network filesystem without a probe in this program; byte
bounds cannot interrupt blocked OS I/O. Library tracebacks can retain Python
source locations even though the CLI uses fixed errors. Future inputs/results
need their own privacy review. The older converter/validator's POSIX-only file
I/O contract is unchanged; this new diff has its own Windows/Ubuntu reader tests.

## Validation and provenance

```text
python -B -m unittest discover -s tests -p test_lock_diff.py -v
```

The local Windows/Python 3.12.7 suite discovered 41 methods: 39 passed, two native
link operations unavailable in that environment were skipped. It includes 100
seeded valid locks and 20 malformed variants compared with the existing public
validator, 300 comparisons checked against separate list-search logic, maximum
package/byte boundaries, fixed errors, input preservation, no-side-effect checks
and single-script standalone execution. Skips are not passes. CI targets Windows/
Ubuntu with Python 3.12/3.13; consult exact-commit Actions results for executed jobs.
Collection-parity tests require the full checkout; standalone refers to runtime.

The strict parser and sampled file guard adapt existing public MIT mechanisms
at `c08b51509fa44629fbd0f50e1719f82fdde155ca`. No held original environment,
dependency configuration, real lock, private package name, credential, index
endpoint, package artifact or operational record was selected, read, copied or
executed. Only newly authored fictional locks ship here. Selected original
code/docs/tests/examples use [MIT](../../LICENSE) under TheOutlandsDev; no
third-party implementation/runtime is bundled. See the
[batch review](../../docs/BATCH-18-LOCK-DIFF.md) for publication scope and evidence.
