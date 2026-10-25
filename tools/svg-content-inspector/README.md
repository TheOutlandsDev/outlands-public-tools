# SVG Content & Reference Inspector

Review a supported static subset of an SVG file without rendering it or opening
any references. This original Python utility reports declared dimensions,
selected interactive/active markup, literal reference observations, duplicate
IDs and missing/ambiguous simple fragment targets. It does not edit the SVG.

The source, tests, documentation and fictional examples use the [MIT license](LICENSE).
Python and its XML parser keep their own licenses. No artwork, browser engine,
vendor parser or dependency implementation is bundled.

## Runtime and quick start

Use **Python 3.12 or newer with Expat 2.7.2 or newer**. CI selects Python 3.12/3.13
on Ubuntu and 3.13/3.14 on Windows. The module checks the Expat
version before its public parsing API runs. Update Python if the check reports
`EXPAT_SECURITY_UPDATE_REQUIRED`; do not remove the check. Expat may come from
Python or the host system, so a Python version alone does not establish its version.

```text
python -B -c "import sys; from xml.parsers import expat; print(sys.version); print(expat.EXPAT_VERSION)"
python -B svg_inspector.py --help
```

Clone/download [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and run commands from `tools/svg-content-inspector`. Choose an existing private
work directory outside the checkout; the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md)
explains the pattern. Every generated destination must be new.

```text
python -B examples/make_demo.py --destination ABS_PRIVATE_DEMO_DIR
python -B svg_inspector.py --svg ABS_PRIVATE_DEMO_DIR/clean.svg --output ABS_NEW_CLEAN_REPORT
python -B svg_inspector.py --svg ABS_PRIVATE_DEMO_DIR/review.svg --output ABS_NEW_REVIEW_REPORT
```

Replace the `ABS_...` placeholders with quoted absolute local paths. The clean
example returns exit **0** and `NO_SCOPE_FINDINGS`. The review example returns
exit **1** and `REVIEW_REQUIRED`; this is the expected result. Both write
`report.json`, a static `report.html` and `MANIFEST.json` with report byte lengths
and SHA-256 hashes. Open only the **generated HTML report** to review its table.
It contains escaped text, no SVG markup, active links, scripts or external assets.
Do not render `review.svg` or arbitrary inspection inputs as part of this workflow.
The review fixture's script declaration and event value are intentionally empty
and inert, but the inspector still records those marker types.

## What the report covers

| Evidence | Supported initial behavior |
| --- | --- |
| XML | UTF-8 XML 1.0, exact SVG namespace/root, bounded parser callbacks; DTDs/entity declarations refused. |
| Dimensions | Literal `width`, `height` and four-number `viewBox`; exact decimal strings, explicit supported units, no conversion or viewport evaluation. |
| Markup | Selected script, event-handler, foreign-object, animation, link and image markers; unknown/foreign markup produces review coverage. |
| References | `href`, XLink `href`, supported presentation `url()` values, literal inline/stylesheet `url()` and quoted `@import`. |
| IDs | Duplicate declarations and exact simple ASCII `#fragment` target existence, with opaque node IDs. |
| CSS uncertainty | Stylesheets/inline styles always need review. Escapes, unknown functions, at-rules, malformed/unsupported tokens and non-ASCII CSS produce explicit coverage issues. |

The [format reference](docs/FORMAT.md) defines the subset and its exclusions.
`resolved_unique` means one declared ID matched; it does not prove that the target
type is allowed, that a reference cycle is absent, or that a browser will render it.
External, relative, file, data and unknown-scheme references are classified as
text only. They are never fetched, decoded as media, opened or resolved on disk.

## Meaning of the result

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | Supported inspection completed without listed findings or coverage issues. |
| 1 | `REVIEW_REQUIRED` | Supported inspection completed with findings or explicit uncertainty. |
| 2 | `INCOMPLETE` | Invalid/unsupported input, exceeded limit, missing parser security update or output failure. |

**No status is a safe-rendering, sanitization, malware, full SVG/CSS validity,
accessibility, copyright or visual-quality verdict.** The tool does not perform
CSS cascade/layout, browser execution, font loading, animation timing, media
decoding or reference-target semantics. Complex or unusual files need additional
review. An old parser is refused rather than treated as a passing inspection.

## Privacy and inputs

Inputs must be completed ordinary local files in trusted directories. Existing
symbolic links/reparse points, UNC/device paths and nonregular inputs are refused
where checked. Path/handle observations detect some changes; they are not a
hostile-filesystem sandbox or an atomic filesystem snapshot. A path can be raced
by an adversarial writer, and native filesystem calls have no hard time bound.
Use a quiescent private copy. Parser limits reduce supported work; current Expat
and DTD rejection do not establish that every future parser defect is excluded.

Default reports omit raw SVG text, reference payloads, ID strings, namespace
URIs, input paths and upstream exceptions. They retain source hashes, dimensions,
source line numbers and structural counts, which can still identify a document.
For a separately reviewed **private** report, add `--include-details` to include
raw reference and ID strings. This can reveal private filenames, URLs or data
payloads. Neither mode is an anonymizer. Do not post actual artwork or unredacted
reports in public issues.

Outputs use fresh-only creation with private POSIX modes where supported. Their
parent must already exist. A failed write can leave a new partial directory; a
failure is never reported as a completed inspection. Existing outputs and source
files are not replaced. Windows access controls depend on the existing parent.

## Test and contribute

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

The source gate is an exact reviewed-source inventory, separate from the runtime
SVG inspection. Read [validation](docs/VALIDATION.md) for platform skips and
[provenance](docs/PROVENANCE.md) for scope and primary format references.

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=svg_content_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=svg_content_suggestion.yml).
Useful contributions include small fictional reproductions, clearer coverage
messages and carefully tested additional syntax. See [CONTRIBUTING.md](CONTRIBUTING.md).
