# OUTLANDS | Dependency Lock Tools

Convert an explicitly supplied pip JSON report into sorted, hash-pinned requirements, then validate locks in that same narrow format. These small offline helpers use Python’s standard library. No actual report, lock, package artifact, private configuration, endpoint or runtime is bundled.

## What the checks establish

The converter takes package names, fixed versions and SHA-256 values from the report. **Hashes are supplied by the report and are not independently checked against artifacts.** The tools do not resolve dependencies, download or install packages, verify an installed environment, check advisories, prove artifact authenticity, or establish complete/reproducible dependency coverage across platforms. A report and its chosen artifacts must be reviewed separately before any installation workflow.

The validator checks syntax and pairing only. It does not invoke pip or accept general pip requirements syntax. Platform/artifact selection remains the report producer’s responsibility. Only names, versions and hashes are retained; report URLs, source constraints and other provenance fields are not carried into the lock. A hash pin does not establish where an artifact originated or that another index can supply it. Identical normalized duplicates in a report are deduplicated; conflicting versions or artifact hashes fail rather than being merged. Environment-specific service matching and package blocklists from the retained helper are excluded.

## Use

Use Python 3.12 on POSIX with no-follow and directory-relative file operations. The recorded reference runtime is Python 3.12.7. Windows file I/O is unsupported in this hardened version. No package installation is needed.

Choose an existing private output parent outside the source repository and a new filename:

```text
python report_to_lock.py --report INPUT_REPORT_JSON --output NEW_LOCK_FILE
python verify_locks.py LOCK_FILE [ANOTHER_LOCK_FILE ...]
```

Inputs must be regular files. Symlink paths and `..` components are refused. Existing outputs, including symlinks and directories, are never overwritten; parents are not created. A new output requests mode 0600. An output failure attempts to remove only the newly created file with its matching inode; a partial new file can remain if cleanup fails. Use trusted, unchanged input/output parents. These checks are not a sandbox or an atomic defense against hostile ancestor replacement.

Success returns 0 with counts-only JSON. Handled rejection returns 2 with a fixed code. Error messages omit raw report records, package values, input names and endpoints. Generated locks retain normalized package names, versions and report-supplied hashes; they can identify private projects and are not anonymous. Keep real locks and reports outside the repository and review sharing rights.

## Supported report and lock format

- The JSON report must have string `version` equal to `1` and a nonempty `install` list. Each record needs string metadata name/version and an archive SHA-256 in `download_info.archive_info.hashes.sha256` or legacy `archive_info.hash` with a `sha256=` prefix. If both representations exist, they must agree. Missing archive hashes, editable/VCS-only records and unsupported schemas fail.
- Names are 1–200 ASCII characters, begin/end with a letter or digit, and otherwise contain letters, digits, `.`, `_` or `-`. Normalization lowercases and collapses runs of `.`, `_` and `-` to a hyphen.
- The fixed-version subset has numeric release components, optionally a numeric epoch, lowercase `a`/`b`/`rc` prerelease, `.postN`, `.devN` and a lowercase alphanumeric local label. Maximum length is 128 characters. This is deliberately a subset, not a full PEP 440 parser or semantic comparison. Unsupported valid version spellings also fail; no silent normalization is attempted.
- A record is exactly `normalized-name==supported-version` followed by one space and a backslash, immediately followed by a line with four spaces and `--hash=sha256:` plus 64 hexadecimal characters. Records are sorted by normalized name with no duplicates. Empty lines and lines beginning with `#` are allowed between records. Unknown active lines, URLs/directives, extras, markers, wildcards, orphan/multiple hash lines and noncanonical names fail.

Bounds: reports at most 2 MiB; locks/output at most 1 MiB; at most 2,000 report records/packages; at most 32 explicit lock inputs and 8 MiB combined input; lock lines at most 512 characters and 6,000 lines. JSON nesting is limited to 64 levels and 50,000 decoded values; duplicate object keys and nonfinite JSON constants fail. File bounds are enforced before decoding.

## Provenance and tests

Adapted from two retained personal stdlib lock-generation/validation helpers. The owner reports personal creation with AI assistance; the adaptation and new tests were also AI-assisted. No per-file license/attribution notice was present in those selected sources and none was removed. No open-source license or exclusive-authorship claim is made by this source snapshot. Licensing remains unassigned; see [the licensing status](../../LICENSING.md). Required third-party obligations remain applicable to future additions and artifacts.

The unit tests construct fictional reports and fake hashes in disposable temporary directories. Their lock contents are test data, not installation recommendations. They cover deterministic conversion, normalization, version/hash rejection, strict pairing, limits, regular-file/link/FIFO checks, output preservation and private error handling. They perform no package/network/install operations. Run from this directory in an isolated private scratch environment:

```text
python -B -m unittest discover -s tests -v
```

Preparation validation: 32 synthetic unittest methods passed, with zero failures, errors or skips, under Python 3.12.7 using `-I -S -B`. A per-child network-denial guard passed its denied-socket selfcheck; resource limits and a finite parent timeout were applied. Only staged code and fictional temporary fixtures ran.

Synthetic success establishes checked software behavior only; it does not validate a real report, package artifact, real environment or installation plan.
