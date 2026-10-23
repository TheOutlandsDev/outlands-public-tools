# XML Recipe Inspector

OUTLANDS // BEYOND THE WALL  
XML Recipe Inspector | Public source showcase

Inspect the structure of an operator-supplied metrology recipe XML and export module, measurement and line-to-line midpoint summaries. The tool uses Python’s standard library. No recipes, images, generated summaries or credentials are bundled.

This is a structural inspector. It does not run a vendor application, detect image edges, fit measurement lines, validate a vendor algorithm or establish measurement accuracy. The original first-descendant `PixelSize/X` convention is retained; it uses that single X calibration for both midpoint axes. The first two `PointProperty` blocks contribute overlay midpoint differences only when each has exactly two user points. These conventions may not describe another recipe schema correctly.

## Run

Use Python 3.12.7 on POSIX with `O_NOFOLLOW`, `O_DIRECTORY` and directory-relative file operations. Windows file I/O is explicitly unsupported in this hardened version. No installation is required.

```text
python3 xml_recipe_inspector.py INPUT_XML --out-dir NEW_PRIVATE_OUTPUT_DIRECTORY
```

Choose an output directory outside the source repository. Its parent must already exist. The tool refuses every existing output path and creates a new directory with mode 0700 and reports with mode 0600. It never overwrites a report. An I/O failure can leave a partial private output directory; inspect it and choose a different new destination when retrying. It never deletes the input or an existing output directory.

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

This is a selected public source showcase. Licensing remains unassigned; see [LICENSING.md](../../LICENSING.md). No vendor endorsement is asserted. No third-party runtime, application binary or original recipe is included.

## Tests

The unit tests construct synthetic XML in disposable temporary directories and use no original recipes, network access or external commands. They cover geometry, declaration rejection, resource limits, numeric handling, output permissions, CSV escaping, refusal to overwrite or follow symlinks, and CLI argument/help privacy. Invalid arguments return ARGUMENTS_INVALID without echoing their values; help uses a static program name.

Run the tests from this directory in a private scratch environment:

```text
python3 -B -m unittest discover -s tests -v
```

Validation in this preparation: 34 synthetic tests passed with zero failures, errors or skips under the existing Python 3.12.7 runtime, using isolated mode, no site initialization and no bytecode writes. No original recipe or original program was executed.

Synthetic tests establish the checked software behavior only; they do not validate real recipes, vendor compatibility, Windows support or metrology accuracy.
