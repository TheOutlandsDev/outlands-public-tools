# APK Metadata Report Diff

Compare selected declarations between two saved `aapt2 dump badging` text reports. The supported subset includes package version strings, declared minimum/target/maximum SDK strings, required/optional library declarations and relative order among common unique libraries. Unknown, missing or duplicate declarations remain explicit review/hold items.

## Download and start

Download the [0.1.0 standalone source ZIP and checksums](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/apk-report-diff-v0.1.0), keep its folder intact and supply ordinary CPython 3.12-3.15 separately. The runtime uses only Python's standard library. No pip package, AAPT2, SDK, administrator account or device connection is required. The ZIP includes no interpreter, APK, producer binary, capture or generated report.

Follow the [complete fictional saved-text walkthrough](USAGE.md). It covers equal and six-change comparisons, default/opt-in details, unknown/duplicate/order/identity holds, escaped HTML, independent text/report hashes and controlled refusals. All inputs are authored text, not real APK captures. Each output uses a new directory under an existing private parent outside the source.

For distinct stable saved reports you are authorized to compare, run from this module folder:

```text
python -E -s -B apk_report_diff.py --before ABSOLUTE_BEFORE_TEXT --after ABSOLUTE_AFTER_TEXT --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Use `python3` where appropriate. Keep `apk_report_diff.py`, `inspection_support.py` and `examples/generate.py` in their existing layout. Every output directory must be new and its parent must exist. Add `--include-details` only when a private report needs supported literal values. Read [the exact grammar and limits](docs/FORMAT.md) first.

## Declared comparison and uncertainty

A comparison requires one supported package declaration on each side. Different package names produce an identity change and hold the remaining comparison; no rename or upgrade is inferred. Duplicate package declarations leave identity unresolved. Version and numeric SDK values remain exact strings: no semantic version ordering, integer rounding or default SDK inheritance is applied. Missing SDK rows mean unspecified in the saved text. Codenames, split attributes and unsupported package fields cause coverage/holds.

Library identities are exact case-sensitive names. Required/optional declarations and relative order among common unique names are observations, not library availability or class-loader resolution. Duplicate identities are held even when repeated text agrees. Unknown rows hold unmatched claims and order rather than inventing additions/removals; supported matched values can still be compared with coverage visible. Holds do not prove unchanged metadata.

Recognized labels, icons, permissions, features, ABIs and other documented out-of-scope rows are counted and discarded. Raw unknown rows and labels never become report details. The inspector treats selected inputs as saved UTF-8 text. It does not parse an APK, invoke AAPT2, install software, inspect bytecode/signatures, query a device or establish capture authenticity/completeness, permission risk, malware absence, signing, installability or runtime compatibility. Filename extensions do not prove input format; select the correct saved text.

## Reports and status

A completed report has exactly:

- `report.json`: selected declarations, opaque entities, changes, holds, findings and coverage.
- `report.html`: escaped static JSON with a restrictive CSP, no scripts or remote assets.
- `MANIFEST.json`: SHA-256 and lengths for the two report files.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported change or explicit coverage issue observed. |
| 1 | `REVIEW_REQUIRED` | Selected changes, unsupported declarations or ambiguity need review. |
| 2 | `INCOMPLETE` | Arguments, paths, bounds, changed inputs or I/O prevented a normal result. |

Stdout is one fixed JSON status/count/error line, without filenames or raw values. Existing destinations are refused. A write error may leave partial new output; resolve the cause and choose a fresh directory. The unsigned report manifest checks consistency, not authenticity.

Default reports omit literal package/version/SDK/library values. `--include-details` enables supported values and package/library identities; `details_included` reflects the requested mode. It does not expose raw unknown rows or ignored labels. Omission is not anonymization: hashes, counts, order and field-presence patterns can identify source material. Source hashes identify saved text bytes, not APKs or capture quality. Review every report privately before sharing; an inspection result grants no redistribution or deployment rights.

## Local files and limits

Exactly one input per side is selected explicitly. Inputs must be distinct stable regular local files with absolute paths. Same-file/hardlink aliases, linked/reparse routes, parent traversal, unsupported UNC/device routes, Windows streams and detected input changes are refused. Inputs are read-only; fresh private reports are the inspector's only outputs. Use trusted stable files and a report parent you control. Sampled path/descriptor checks and cooperative bounds are not an OS sandbox, atomic snapshot or hard native I/O deadline.

Each file is at most 1 MiB of UTF-8, with optional BOM and LF/CRLF. Limits include 20,000 physical lines including a final empty line, 8192 characters per line, 4000 parsed/result records and 8 MiB per JSON/HTML report. Bare CR, NUL and unsupported Unicode controls are refused. Values use the documented strict quoted subset without backslash escaping, shell substitution or inferred quote repair. A bound fails the run rather than silently truncating a result.

## Qualification and source verification

The [standalone qualification contract](docs/QUALIFICATION.md) requires eight Windows/Ubuntu lanes on pinned CPython 3.12, 3.13, 3.14 and 3.15 builds. Each selects all 61 original methods plus copied-runtime CLI/safeguard methods in a fresh no-pip environment with zero distributions and exact extracted-source affinity. ZIP/build-manifest rebuilds must match. Applicable native links/hardlinks are mandatory; exact opposite-platform and actual local Windows error 1314 limits are recorded separately from passes. The [release validation record](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/apk-report-diff-v0.1.0) supplies accepted results.

The parser/comparison runtime, shared support, generator and both original test files retain exact bytes. Historical [validation](docs/VALIDATION.md), [format](docs/FORMAT.md), [provenance](docs/PROVENANCE.md), [capture guidance](docs/CAPTURE.md) and [examples](examples/README.md) retain their source/evidence boundary. Optional manual capture is separate and unexecuted; no live producer, SDK, APK or device acceptance is claimed.

From this module folder, check the explicit source inventory:

```text
python -E -s -B source_check.py
```

Archive qualification invokes the original-test adapter in a bound fresh environment using measured interpreter version/hash evidence. Plain unittest discovery also selects copied-runtime methods and does not replace strict native rules, source affinity or fresh archived-package acceptance. Deliberately review changes before regenerating `SOURCE-MANIFEST.json`; its unsigned hashes are not trusted provenance or a universal privacy guarantee.

## License and feedback

[MIT](LICENSE) covers original source, authored documentation/tests and fictional generators. Python and external tools retain their own terms, as do inspected inputs. No third-party producer implementation or APK content is vendored. See [third-party notices](THIRD-PARTY-NOTICES.txt), [security guidance](SECURITY.md) and [CONTRIBUTING](CONTRIBUTING.md).

Use the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose) with a small fictional text reproduction, source commit, expected behavior and OS/Python version. Keep raw APKs, real captures, customer paths, device identifiers, raw logs and unredacted reports private.
