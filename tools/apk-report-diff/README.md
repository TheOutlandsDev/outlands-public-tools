# APK Metadata Report Diff

Explain supported metadata changes between two **saved `aapt2 dump badging`
text reports**. Compare declared package version strings, minimum/target/maximum
SDK values, required/optional library declarations and common-library relative
order. Python 3.12 or newer, standard library only, original MIT source.

Useful for reviewing an Android app build's recorded manifest metadata before
and after a change. This tool reads text reports; it does not open APKs, invoke
AAPT2, install apps, inspect bytecode/signatures or evaluate device compatibility.
Missing, duplicate and unsupported declarations remain explicit review items.

## Install and try fictional examples

Clone or download [Outlands Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and open a terminal in `tools/apk-report-diff`. No `pip install` is needed. Keep
private inputs/reports outside the checkout, using the collection's
[private workspace guidance](../../docs/PRIVATE-WORKSPACE.md). Commands below
use fictional paths. Create the parent directory yourself; every generated
output directory must be new.

Windows PowerShell, after setting `$privateWork` to an existing absolute private
directory you control:

```powershell
python -B examples/generate.py --output "$privateWork/apk-demo"
python -B apk_report_diff.py --before "$privateWork/apk-demo/before.txt" --after "$privateWork/apk-demo/same.txt" --output "$privateWork/apk-equal-report"
python -B apk_report_diff.py --before "$privateWork/apk-demo/before.txt" --after "$privateWork/apk-demo/after.txt" --output "$privateWork/apk-change-report" --include-details
```

Linux, with an existing `/tmp/apk-review` directory you control:

```sh
python3 -B examples/generate.py --output /tmp/apk-review/demo
python3 -B apk_report_diff.py --before /tmp/apk-review/demo/before.txt --after /tmp/apk-review/demo/same.txt --output /tmp/apk-review/equal-report
python3 -B apk_report_diff.py --before /tmp/apk-review/demo/before.txt --after /tmp/apk-review/demo/after.txt --output /tmp/apk-review/change-report --include-details
```

The equal comparison exits **0**, `NO_SCOPE_FINDINGS`. The changed comparison
exits **1**, `REVIEW_REQUIRED`, with **six field/declaration changes**: version
code, version name, target SDK, one removed library declaration, one added
library declaration and one required/optional change. This is an observation of
the selected text, not an upgrade or runtime compatibility conclusion.

Replace `after.txt` with `unsupported.txt` to see incomplete-coverage holds, or
with `duplicate.txt` to see an ambiguous library identity held from comparison.
See [examples](examples/README.md), [exact grammar/report format](docs/FORMAT.md)
and [validation](docs/VALIDATION.md).

## Command and outputs

```text
python -B apk_report_diff.py --before ABSOLUTE_TEXT_FILE --after ABSOLUTE_TEXT_FILE --output NEW_ABSOLUTE_DIRECTORY [--include-details]
```

Exactly one file is selected for each side. Inputs must be distinct stable
regular local files with absolute paths and no linked/reparse path component.
UNC/device paths, alternate data streams, traversal components, special files
and same-file/hardlink aliases are rejected. No automatic discovery occurs.

Each input is limited to 1 MiB of UTF-8 text, optional UTF-8 BOM, LF or CRLF;
20,000 physical lines including a final empty line, 8,192 characters per line.
Bare CR, NUL and unsupported Unicode controls are refused. Parsed collections
are capped at 4,000 records. See [format](docs/FORMAT.md) for exact limits.

The output parent must already exist. Existing destinations are refused. A
successful inspection creates `report.json`, escaped static `report.html` and
`MANIFEST.json` containing SHA-256 hashes of those two report files. Reports
are bounded to 8 MiB each. Partial outputs may remain after an I/O interruption;
select a new destination for a retry. The manifest is unsigned, not an
authenticity certificate. Report source hashes describe the selected text bytes,
not an APK or the quality/completeness of the capture.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No supported change or coverage issue observed. |
| 1 | `REVIEW_REQUIRED` | Changes, unsupported declarations or ambiguity need review. |
| 2 | `INCOMPLETE` | Invalid input/path, exceeded limit, argument or I/O failure. |

Stdout contains fixed status/codes and counts, without input filenames or raw
values. An incomplete run does not produce a successful report. A pre-existing
directory is never overwritten.

## Comparison and privacy boundaries

- Require exactly one supported package declaration per report. Different
  package names are reported as an identity change and remaining comparison is
  held; neither a rename nor an upgrade is inferred.
- Preserve version and numeric SDK strings exactly. No integer precision loss,
  semantic version ordering or default SDK inheritance is inferred. SDK
  codenames, split-package attributes and unknown package fields are unsupported.
- Duplicate package/SDK/library declarations are ambiguous even when identical.
  No first/last declaration wins. Unknown rows hold unmatched candidate fields
  and libraries rather than inventing removals/additions; supported matched
  declarations may still be compared with coverage issues visible.
- Required/optional library declarations are compared by exact case-sensitive
  name. Relative order among common unique libraries is separately observed.
  This is not an Android class-loader resolution or dependency validator.
- Recognized labels, icons, permissions, features, ABIs and other explicitly
  documented out-of-scope rows are counted and discarded. Unknown/implied/static
  library rows trigger coverage. No permission-risk, malware, installability,
  signing, compatibility or full-manifest claim is made.

Default reports omit literal package, version, SDK and library values, using
opaque IDs/counts and field names. `--include-details` includes supported values
and package/library identities. Raw unsupported rows and application labels are
never included. **Omission is not anonymization**: hashes, counts, order and
field-presence patterns can identify source material. Review all outputs before
sharing and keep raw APKs, real captures and identifying reports private.

## Capture your own reports

AAPT2 is a separate Android tool under its own terms. Its official documentation
describes [`dump badging`](https://developer.android.com/tools/aapt2#dump) as
manifest information. Use an authorized local APK and an existing trusted SDK
installation; no SDK binary or APK is bundled here. The optional manual commands
in [capture guidance](docs/CAPTURE.md) are not run by this inspector or its tests.
Text formats vary by producer/version; unfamiliar syntax is a coverage item.

## Tests, license and suggestions

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

Tests generate fictional text and invoke the actual CLI. Platform-only link and
FIFO cases may skip; skips are distinct from passes. No live APK capture,
installation, device or firmware operation is part of validation. Read
[validation evidence](docs/VALIDATION.md) and [provenance](docs/PROVENANCE.md).

MIT covers original source/docs/tests and fictional examples; inspected inputs
and separately installed runtimes/tools retain their rights. See [LICENSE](LICENSE)
and [notices](THIRD-PARTY-NOTICES.txt). Improvements and feature requests are
welcome through [GitHub issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Provide a minimal fictional text example, expected behavior and environment.
Read [contributing](CONTRIBUTING.md) and [security](SECURITY.md) before posting.
