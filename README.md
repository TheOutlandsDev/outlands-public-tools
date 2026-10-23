# OUTLANDS | Engineering Utilities

Focused Python utilities for dependency-lock review, static package checks, bounded source inventories, structural XML inspection and Markdown document generation. The first four tool groups use Python's standard library and documented POSIX file operations. Markdown Document Builder additionally requires python-docx; its Linux validation and filesystem limits are documented separately.

| Tool | Purpose | Documentation |
| --- | --- | --- |
| Dependency Lock Tools | Convert a supported pip JSON report to sorted name/version/SHA-256 requirements and validate that limited lock format offline. | [Usage, format and limits](tools/dependency-lock-tools/README.md) |
| Package Layout Checker | Check caller-declared files, optional Python syntax and case-insensitive literal markers without importing the selected package. | [Usage, examples and limits](tools/package-layout-checker/README.md) |
| Source Inventory | Hash an explicitly selected, bounded file tree and write private CSV/JSON reports with recorded exclusions. | [Usage, reports and limits](tools/source-inventory/README.md) |
| XML Recipe Inspector | Summarize operator-supplied unnamespaced recipe XML using retained schema conventions and bounded parsing. | [Usage, schema and limits](tools/xml-recipe-inspector/README.md) |
| Markdown Document Builder | Convert an explicitly selected Markdown subset into a fresh DOCX with styled headings/tables and neutral core properties. | [Usage, dependency and metadata limits](tools/document-builders/README.md) |

## Quick start

Use Python 3.12 on Linux/POSIX. The first four groups need no third-party package installation. Document Builder requires the declared python-docx dependency in an existing environment. Start with disposable fictional inputs and read the tool-specific limits.

```text
python tools/package-layout-checker/layout_check.py --root tools/package-layout-checker/examples/sample-package --manifest tools/package-layout-checker/examples/layout.json
```

To work with an existing report or lock, provide your own explicit private input/output paths:

```text
python tools/dependency-lock-tools/report_to_lock.py --report INPUT_REPORT_JSON --output NEW_LOCK_FILE
python tools/dependency-lock-tools/verify_locks.py LOCK_FILE
```

## Recorded validation

| Tool | Synthetic unittest methods | Runtime |
| --- | ---: | --- |
| Dependency Lock Tools | 32 passed | Python 3.12.7, Linux |
| Package Layout Checker | 33 passed | Python 3.12.14, Linux |
| Source Inventory | 18 passed | Python 3.12.7, Linux |
| XML Recipe Inspector | 34 passed | Python 3.12.7, Linux |
| Markdown Document Builder | 27 passed | Python 3.12.14, Linux; python-docx 1.2.0 |

All 144 recorded methods passed with no skips, failures or errors: 65 from the first publication review, 52 from the second review and 27 freshly run for Document Builder. These are separate recorded tool suites, not one integrated application acceptance test. A separate fictional layout CLI run passed for two declared files; it is not counted as additional unittest cases. Validation used bounded, isolated child processes with network system calls denied. A separate fictional Document Builder CLI run and package metadata inspection also passed. No real report, package artifact, business data or production environment was accepted by these tests.

## Scope

Lock validation checks syntax and hash pairing. Hashes come from the supplied report; the tools do not establish artifact origin, dependency resolution, installability, platform coverage or vulnerability status. Report URLs and source constraints are not carried into the generated format.

Layout checks cover only declared files. PASS does not enumerate extra files, prove an exact export list, find arbitrary secrets or establish application correctness. Syntax parsing is not execution. Source Inventory reports preserve relative names, hashes, sizes and timestamps; exclusions do not guarantee removal of every private file. XML summaries retain selected recipe identifiers and geometry. The XML schema assumptions are not vendor measurement validation or accuracy evidence. Read each tool's limits before selecting inputs. None of these tools is an anonymity mechanism, a universal filesystem sandbox or a complete snapshot. The first four groups require their documented POSIX primitives. Document Builder was validated on Linux; Windows junction/reparse behavior and Office rendering require separate validation. Its core-property settings do not remove copied input text, inherited template parts or ZIP timestamps, and its direct dependency pin is not a complete transitive lock or advisory audit.

Keep real reports, generated locks, private manifests, credentials, runtime outputs and identifying support material outside this repository. Use stable, trusted files and parents.

See [the second-batch review](docs/BATCH-2-REVIEW.md) for inventory/XML validation and [the Document Builder review](docs/BATCH-3-REVIEW.md) for the next selected tool, CLI privacy correction and validation scope.

## Provenance and licensing

The owner reports personal work created with AI assistance; the adaptations, documentation and synthetic tests were also AI-assisted. Only the selected generic mechanisms and fictional examples are included. No required license or attribution notice was removed from the selected sources. This statement is not independent proof of exclusive authorship.

**No open-source license has been assigned.** This is a publicly viewable source showcase; general reuse permission is not granted by this README. See [LICENSING.md](LICENSING.md) before redistributing or incorporating code.
