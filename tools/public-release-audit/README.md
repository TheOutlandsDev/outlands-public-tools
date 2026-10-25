# Public Release Audit

Offline review of an explicitly selected stable text export. Python 3.12+, standard library only. Reads files without importing code, running builds, contacting services, or modifying selected inputs.

```text
python tools/public-release-audit/release_audit.py --root EXPORT_DIRECTORY --report NEW_PRIVATE_REPORT_JSON
python tools/public-release-audit/release_audit.py --root EXPORT_DIRECTORY --deny-file PRIVATE_MARKERS_JSON --report NEW_PRIVATE_REPORT_JSON
```

The optional private markers file is a JSON array of literal strings, kept outside the export. It can contain organization names, internal hostnames, identifiers, or private project names. Reports identify the rule and line; they do not repeat the marker or matched source value. Reports still contain relative filenames and hashes and need their own sharing review. Console summaries omit filenames.

Rules flag known credential forms, key headers, selected assignments, non-example email addresses, network addresses, internal hostnames, URL credentials, user-home/UNC paths, and private literals in content or relative names. Loopback and standard documentation address blocks are usable in fictional examples. Generic pattern rules can produce false positives and miss secrets or identifying information in unrecognized forms. Private marker checks are literal and case-insensitive, not semantic detection.

Selected text is bounded to 2 MiB per file, 64 MiB in total, and 20,000 encountered entries. Unknown formats, archives, binary content, non-UTF-8 text, linked/reparse entries, sensitive filenames, and private/runtime directories require review rather than silently passing. Root `.git` metadata is explicitly excluded. Git history, tags, branches, release assets, document/image metadata, archives, external links and software behavior are not scanned.

After reviewing the exact tree, record an inventory outside it:

```text
python tools/public-release-audit/release_audit.py --root EXPORT_DIRECTORY --write-manifest NEW_PRIVATE_MANIFEST_JSON
python tools/public-release-audit/release_audit.py --root EXPORT_DIRECTORY --manifest REVIEWED_PRIVATE_MANIFEST_JSON
```

The comparison checks the selected relative file list, byte lengths and SHA-256 values. Added or changed files fail comparison. A manifest created from unreviewed content is not approval or an independent trust baseline. A party able to replace both content and manifest can create a matching pair. Reports/manifests use new files and must be outside the selected root.

Exit codes: `0` means no findings in the documented checks, `1` means review is required, and `2` means input/output or configuration failure. `NO_PATTERN_FINDINGS` is not a statement of anonymity, intellectual-property clearance or software safety. Use trusted, stable files and directories; this tool is not a hostile-filesystem sandbox. Windows alternate data streams are outside this text-export inventory.

MIT licensed; see [licensing](../../LICENSING.md). See [validation](../../docs/BATCH-6-REVIEW.md).
