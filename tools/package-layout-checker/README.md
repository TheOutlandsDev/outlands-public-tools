# OUTLANDS | Package Layout Checker

Check required package files, optionally parse Python syntax without executing it, and reject caller-selected literal markers. The design adapts required-file checks, static AST parsing, case-insensitive marker scanning, and aggregate results from an owner-created project verifier. Project data validation, business schemas, fixed paths, and runtime checks were excluded.

## Use

Python 3.10 or newer with standard-library modules only. This edition requires POSIX directory descriptors, `O_NOFOLLOW`, `O_DIRECTORY`, and `O_NONBLOCK`; unsupported platforms fail closed. Windows is not supported by this edition.

From this directory, check the bundled fictional package:

```text
python layout_check.py --root examples/sample-package --manifest examples/layout.json
```

Both paths are required. There is no original-project root, data path, environment override, network connection, installation, or source execution. The checker writes JSON to stdout and does not write into the selected package.

## Expectations

The caller authors a UTF-8 JSON manifest:

```json
{"schema_version":1,"files":[{"path":"README.md"},{"path":"src/demo.py","python_syntax":true,"forbidden_literals":["DO_NOT_SHIP_EXAMPLE"]}]}
```

`path` is a canonical relative file path using `/`. `python_syntax` and `forbidden_literals` are optional. Syntax is checked with the running interpreter's AST parser, not imports or execution. Literal matching is case-insensitive and is not a regular-expression or secret-detection engine. Required files are aggregated into PASS/FAIL results. Missing, unreadable, unsafe, malformed-text, syntax, marker, and byte-limit findings make the check fail.

Output contains only relative declared filenames and fixed result codes. It omits matched literals, file contents, parser excerpts, root paths and raw errors. Relative filenames themselves can still identify a project. A private manifest may contain sensitive patterns; protect and review it separately rather than committing real secrets as test rules.

## Bounds and limits

The manifest is limited to 64 KiB and 100 files. Duplicate JSON keys, non-finite numbers, unknown fields, duplicate/case-colliding paths, absolute paths, traversal components and unsafe path characters are rejected. Selected files are limited to 256 KiB each. Content checks reserve at most 2 MiB of text reads per run; presence-only entries inspect metadata without reading contents. Each rule has at most 16 literals of 256 characters each.

All root/manifest/selected-file directory components are opened without following symlinks. Selected files and the manifest must be regular files with a single hard link. FIFOs, directories, symbolic links and hard-linked files are refused. Directory descriptors anchor path traversal, but these checks are not a filesystem snapshot or protection from every concurrent content modification, mount change, privilege, storage or OS behavior. Use stable local package trees.

Only declared files are checked. Unlisted files are never enumerated or read; PASS does not establish an exact export allowlist, absence of extra files, dependency safety, application correctness, data integrity, ownership, anonymity, or release readiness. Syntax compatibility is limited to the running Python parser. Do not use this utility to clear an entire project collection or to replace a separate release review.

Exit codes: `0` for passing declared checks, `1` for file findings, `2` for invalid control input or unsupported/failed root/manifest access, and `130` for an interrupted run.

## Verification and licensing

Run the synthetic tests with:

```text
python -B -m unittest discover -s tests -p "test_*.py"
```

Examples and test fixtures are fictional. Recorded synthetic validation passed 33 unittest methods on Python 3.12.14/Linux, with no skips, failures or errors; a separate example CLI run passed for the two declared fictional files. No real project data or original verifier was executed. The owner reports personal work created with AI assistance. This source snapshot grants no new open-source license; see [the licensing status](../../LICENSING.md). No third-party implementation or runtime is bundled, and required notices must be retained if dependencies are distributed later.
