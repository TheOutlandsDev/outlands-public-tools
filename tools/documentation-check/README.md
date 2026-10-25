# Documentation Check

Read-only, offline Markdown-link and JSON-syntax checks for Python 3.12+ with no third-party runtime dependency.

```text
python tools/documentation-check/docs_check.py --root DOCUMENTATION_DIRECTORY
```

Checks common inline/image links and reference definitions, skips fenced and simple inline code, and checks local link destinations. Missing links, root-escaping links and symlink/reparse targets fail. HTTP, HTTPS and mail links are skipped without fetching. Other schemes fail. JSON must parse and cannot use nonstandard NaN/infinity constants.

The scan excludes root Git metadata, hidden subdirectories, private/runtime directories, caches and dependency trees. It checks Markdown/JSON only, up to 10,000 encountered entries and 2 MiB per selected file. It does not implement all CommonMark grammar, match reference uses to definitions, validate anchors, inspect external sites, validate JSON schemas or attest to excluded files. Use a trusted stable tree.

Output contains relative filenames and line numbers; retain it privately. Exit codes are `0` for the documented checks passing, `1` for findings, and `2` for input/output errors. PASS is documentation hygiene, not security or application validation.

MIT licensed; see [licensing](../../LICENSING.md) and [validation](../../docs/BATCH-6-REVIEW.md).
