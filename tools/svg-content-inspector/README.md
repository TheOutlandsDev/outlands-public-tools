# SVG Content & Reference Inspector

Inspect a bounded static subset of SVG text without rendering it, editing it or opening its references. Reports describe declared dimensions, selected active markup, literal references, duplicate IDs and missing or ambiguous simple fragment targets. No result is a safe-rendering, sanitization, malware, complete SVG/CSS validity, accessibility, copyright or visual-quality verdict.

Download the [0.1.0 standalone source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/svg-content-inspector-v0.1.0), verify SHA256SUMS and follow the [fictional walkthrough](USAGE.md). Supply ordinary CPython 3.12–3.15 with **actual Expat 2.10.0 or newer**. A Python version alone does not establish its parser version. The source download includes no interpreter, parser library, compiler, third-party Python distribution, artwork or generated report.

## Parser prerequisite

Check the interpreter you will actually run:

```text
python -I -B -c "import sys,pyexpat; from xml.parsers import expat; print(sys.version); print(expat.EXPAT_VERSION); print(pyexpat.__file__)"
```

The runtime refuses a lower Expat version with exit 2 and `EXPAT_SECURITY_UPDATE_REQUIRED` before parsing. Preserve that gate. This release raises the former 2.7.2 floor to 2.10.0 following the upstream [2.10.0 release](https://github.com/libexpat/libexpat/releases/tag/R_2_10_0) and [security-fix changelog](https://github.com/libexpat/libexpat/blob/R_2_10_0/expat/Changes). A required version floor and DTD refusal do not certify that all parser vulnerabilities are fixed or that SVG is safe to render.

Qualification records the actual CPython executable, pyexpat extension/parser build, loaded version and source/binary hashes in each Windows/Ubuntu lane. A standalone Python archive can still bundle an older Expat; it must not be called passing merely because its Python minor matches. The maintained runtime preparation/build method is separate from this source-only tool. Follow applicable tool/build permissions; this guide requests no administrator privilege or policy change.

## Optional runtime preparation

Use an already approved interpreter whose actual parser meets the floor, or review the separate [pinned preparation recipe](packaging/prepare_runtime.py). Invoke it with an approved existing Python 3.12+ used only for provisioning:

```text
python -I -B packaging/prepare_runtime.py --minor 3.15 --out ABS_NEW_EXTERNAL_RUNTIME --report ABS_NEW_EXTERNAL_JSON
```

Preparation requires an existing CMake version supporting the selected compiler generator and a compiler toolchain: Visual Studio 2022 or Visual Studio 2026 with x64 C tools on Windows, or GCC and make on Linux. It downloads hash-pinned standalone Python, matching CPython source and Expat source into the new owned runtime directory, builds a matching native pyexpat extension with static Expat 2.10.0, preserves the original module backup and verifies the actual updated import. The receipt records original archive pins, original executable/module hashes, updated module hash and build metadata. Compiler output hashes can vary with build paths/toolchains; identical native binaries are not promised. It installs no missing toolchain or system runtime and changes no system Python. Follow applicable build/network policy. Prepared interpreters, source archives, native libraries, backups and raw build logs stay outside the source ZIP; this preparation is separate from the eleven-case usage exercise.

## Inspect fictional text first

```text
python -I -B examples/make_demo.py --destination ABS_NEW_PRIVATE_DEMO
python -I -B svg_inspector.py --svg ABS_NEW_PRIVATE_DEMO/clean.svg --output ABS_NEW_CLEAN_REPORT
python -I -B svg_inspector.py --svg ABS_NEW_PRIVATE_DEMO/review.svg --output ABS_NEW_REVIEW_REPORT
```

Use quoted absolute paths, an existing trusted private parent and new destinations. The generator authors inert fictional text; it does not copy artwork. Never render the input SVG as part of this workflow. Generated `report.html` contains escaped static text and does not embed SVG, scripts, active links or external assets; the guide checks its markup programmatically.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | Inspection completed without listed findings or coverage issues in the supported subset. |
| 1 | `REVIEW_REQUIRED` | Inspection completed with findings or explicit uncertainty; this is an expected result for the review example. |
| 2 | `INCOMPLETE` | Input/parser/format/limit/output failure; no complete inspection is claimed. |

Completed inspections exclusively create `report.json`, `report.html` and `MANIFEST.json`, with exact report byte lengths and SHA-256 hashes. Existing destinations/files are not replaced. The parent must exist. An I/O failure can retain a new partial private output, returns failure and is never claimed as complete. Retain it privately and choose a different new destination for a retry; no rollback or cleanup feature is provided.

## Scope and privacy

The supported subset includes UTF-8 XML 1.0 with the exact SVG namespace/root, literal dimensions, selected active/foreign/unknown markup, href/XLink references, a conservative CSS URL/import subset and simple fragment target observations. DTDs/entity declarations are refused. CSS escapes, unsupported syntax, base URLs and other uncertainty produce explicit coverage issues. `resolved_unique` means one declared ID matched; it does not validate target type, cycles or browser behavior. External/file/data/unknown-scheme references remain text: they are never fetched, decoded as media, opened or resolved on disk.

Default reports omit raw SVG text, reference payloads, ID strings, namespace URIs, input paths and upstream exception text. They retain hashes, dimensions, line numbers and structural counts, which can identify a document. `--include-details` adds raw reference/ID strings to a separately reviewed private report and can expose URLs, filenames or embedded payload text. Neither mode is anonymization. Keep actual artwork, reports and diagnostics private.

Use stable ordinary local files and trusted directories with one operator. Existing links/reparse paths, device/UNC paths and nonregular inputs are refused where checked. Sampled path/handle identities and parser limits are not atomic snapshots, hostile-filesystem isolation, hard native I/O deadlines or a parser-security guarantee. Network/cloud storage, adversarial mutation and real artwork acceptance are outside qualification.

The [current qualification contract](docs/QUALIFICATION.md) preserves all 59 original tests and adds 30 copied-runtime methods per lane across Python 3.12–3.15 on Windows/Ubuntu. Actual outcomes and parser/runtime/archive pins belong to release VALIDATION.json. The preserved [format](docs/FORMAT.md), [earlier validation](docs/VALIDATION.md) and [example notes](examples/README.md) retain their historical 2.7.2 floor and earlier outcomes; this release requires 2.10.0. See [provenance](docs/PROVENANCE.md), [private workspace guidance](docs/PRIVATE-WORKSPACE.md), [changes](CHANGELOG.md), [contributing](CONTRIBUTING.md) and [license](LICENSE).
