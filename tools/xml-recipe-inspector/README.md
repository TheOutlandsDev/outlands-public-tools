# XML Recipe Inspector

OUTLANDS // BEYOND THE WALL  
XML Recipe Inspector | Public source showcase

Inspect the structure of an operator-supplied metrology recipe XML and export module, measurement and line-to-line midpoint summaries. The tool uses Python’s standard library. No recipes, images, generated summaries or credentials are bundled.

This is a structural inspector. It does not run a vendor application, detect image edges, fit measurement lines, validate a vendor algorithm or establish measurement accuracy. The original first-descendant `PixelSize/X` convention is retained; it uses that single X calibration for both midpoint axes. The first two `PointProperty` blocks contribute overlay midpoint differences only when each has exactly two user points. These conventions may not describe another recipe schema correctly.

## Run

Use Python 3.12/3.13 and the standard library. POSIX retains its `O_NOFOLLOW`, `O_DIRECTORY` and directory-relative output operations. Windows uses the sibling `xml_windows.py` native backend; keep both runtime files together. Unsupported APIs/filesystems fail closed. No installation is required. Read the [Windows input/output contract](docs/WINDOWS.md).

```text
python3 xml_recipe_inspector.py INPUT_XML --out-dir NEW_PRIVATE_OUTPUT_DIRECTORY
```

Choose an output directory outside the source repository. Its parent must already exist. The tool refuses existing output paths and never overwrites a report. POSIX keeps its original directory mode 0700/report mode 0600 requests and failure behavior. Windows permissions inherit from the selected parent: no equivalent mode or ACL confidentiality check is provided. Use a trusted private parent. An I/O failure can leave an empty, partial or fully written but unconfirmed new directory; inspect it and choose a different new destination when retrying. The Windows backend never removes a pathname as error recovery. It never deletes the input or an existing output directory.

Windows retains ancestor/output-directory handles and uses exclusive new-file creation for reports. Reparse points, multi-link inputs, ambiguous paths and observed native aliases/identity changes are refused. Native directory creation and subsequent handle acquisition have a gap; this is not atomic directory ownership against hostile replacement. Reports close sequentially and other child entries are not enumerated. Neither backend promises an immutable/atomic report set or hostile-filesystem containment. Read the [limits and fictional fixtures](docs/WINDOWS.md).

Output consists of `modules_summary.json`, `measurements_summary.json`, `overlay_line_line_summary.json` and, when overlay rows exist, `overlay_line_line_summary.csv`. Missing optional numeric fields become JSON `null`; nonfinite numbers and arithmetic overflow are rejected. Text CSV cells that could start spreadsheet formulas are prefixed with an apostrophe. JSON retains their original text.

Generated reports contain selected recipe identifiers, locations, geometry and calibration-derived values. Treat them as sensitive data and review sharing rights separately. This exporter does not anonymize the input or make it untraceable. Console success output contains counts; errors use fixed codes without recipe excerpts or paths.

## Input and output limits

- Regular input file only, at most 1 MiB. Symlink paths and parent traversal are refused.
- XML depth at most 64; at most 20,000 elements and 1,048,576 text characters; individual extracted fields at most 2,048 characters.
- DTDs, entity declarations, external entities and processing instructions are rejected by parser callbacks, including UTF-16 input. XML namespaces are unsupported. Ordinary XML character references remain supported.
- The tool does not fetch URLs, expand XInclude, open referenced images or execute commands from XML.
- Combined generated output is limited to 4 MiB before output-directory creation.

The resource limits bound normal operation; they do not provide an operating-system sandbox or a guarantee against a hostile process concurrently replacing filesystem ancestors. Use a trusted private working directory and inputs you are authorized to inspect.

## Development and provenance

Adapted from an owner-supplied small stdlib inspector. The owner reports creating the Programs projects personally with AI assistance. The surrounding source README contained conclusions and identifiers derived from supplied recipe/image data; that README and every dataset/output were excluded. No upstream license or attribution header was found in the selected script. Owner attestation is not independent proof of every surrounding input’s origin.

This is a selected public source showcase. Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). No vendor endorsement is asserted. No third-party runtime, application binary or original recipe is included.

## Tests

The unit tests construct synthetic XML in disposable temporary directories and use no original recipes, network access or external commands. They cover geometry, declaration rejection, resource limits, numeric handling, output permissions, CSV escaping, refusal to overwrite or follow symlinks, and CLI argument/help privacy. Invalid arguments return ARGUMENTS_INVALID without echoing their values; help uses a static program name.

Run the original POSIX suite from this directory in a private scratch environment:

```text
python3 -B -m unittest discover -s tests -p test_xml_recipe_inspector.py -v
```

Validation in this preparation: 34 synthetic tests passed with zero failures, errors or skips under the existing Python 3.12.7 runtime, using isolated mode, no site initialization and no bytecode writes. No original recipe or original program was executed.

Those 34 original methods/file remain unchanged and run on Ubuntu in the platform CI. New portable/native Windows fixtures run on Windows/Ubuntu with Python 3.12/3.13. Windows CI requires native hardlink/symlink/junction fixtures; unavailable short-name spellings remain explicit skips. Read the [Batch 21 review](../../docs/BATCH-21-XML-RECIPE-WINDOWS.md) and exact-commit Actions logs for executed pass/skip counts. Skips are not passes.

Run the new suite from the same tool directory on either platform:

```text
python -B -m unittest discover -s tests -p test_xml_windows.py -v
```

Local Windows/Python 3.12.7 discovered 50 new methods: 46 passed and four skipped (three unavailable native-link fixtures and one POSIX-only API probe). A separate two-file runtime copy passed 37 fresh-process fictional CLI scenarios; source/runtime/input bytes stayed unchanged and no bytecode appeared. This is separate from the original recorded POSIX suite.

Synthetic tests establish the checked software behavior only; they do not validate real recipes, vendor compatibility, arbitrary filesystem behavior or metrology accuracy.
