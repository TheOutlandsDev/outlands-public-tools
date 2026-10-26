# OUTLANDS | Document Builders

`markdown_docx.py` turns an explicitly selected local Markdown file into a styled DOCX. It preserves headings, simple bullets/numbered lines, and rectangular pipe tables. Parser and layout helpers were adapted from the owner's document-builder project; operational covers, selected-section rules, logos, fixed paths, and source data were excluded.

## Runtime and usage

The code targets Python 3.10 or newer and declares `python-docx==1.2.0`; Windows/Ubuntu CI targets Python 3.12/3.13. Keep `docx_windows.py` beside `markdown_docx.py` for the Windows native backend. Dependencies are not bundled. The direct package pin is not a complete transitive or hash-locked environment. Local Windows validation used an existing Python 3.12.7 environment with python-docx 1.2.0, lxml 6.0.2 and typing_extensions 4.15.0; no packages were installed locally. The earlier Linux observation used Python 3.12.14, python-docx 1.2.0, lxml 6.1.1 and typing_extensions 4.16.0. CI installs the declared direct requirement and reports its actual transitive versions. None of these observations is dependency vulnerability clearance.

Run from this directory. First create an absolute `$privateWork` outside the
checkout using the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md).
Choose a new output whose private parent already exists:

```text
python markdown_docx.py --input examples/fictional_request.md --output "$privateWork/example-request.docx" --title "OUTLANDS Synthetic Example"
```

The bundled input is fictional. No generated DOCX is included in the repository. Existing outputs are always refused; there is no overwrite flag. The tool does not create parent directories. Review an old output before removing or renaming it yourself.

## Boundaries

Input must be a regular UTF-8 file, at most 256 KiB and 5,000 lines, with at most 4,000 characters per line. Tables must be rectangular, with at most 16 columns and 1,000 body rows per table. Symlink paths and `..` components are rejected. Output is created exclusively with owner-only mode where supported. These filesystem checks are not a sandbox against hostile concurrent directory replacement; use trusted local paths and do not change them during a build.

Windows uses retained native ancestor handles, regular single-link input checks, reparse-point refusal and normalized native name/identity observations. Ambiguous paths and observed short-name aliases are refused before reading/writing. Outputs use native exclusive creation, no sharing while writing, short-write handling, file flushing and final identity/size checks. Existing outputs are preserved. Permissions inherit from the selected parent: no mode 0600 equivalent or ACL confidentiality check is provided. Failures after creation retain a partial or fully written but unconfirmed file; Windows recovery never deletes a pathname. Use stable trusted local paths. Read the [Windows contract and remaining limits](docs/WINDOWS.md).

This is a small Markdown subset, not a general Markdown, HTML, PDF, template, or spreadsheet converter. Escaped pipes, nested lists, code blocks, links, and inline formatting are not fully interpreted. No logos, external images, URLs, or remote templates are fetched. Wide or long tables may need manual layout adjustment. The tool provides no financial calculation, procurement, availability, or document-authenticity assurance.

Input text is copied into the document. The tool does not anonymize user content. Review names, figures, links, identifiers, and document text before sharing. Core properties use neutral OUTLANDS fields and fixed nonidentifying timestamps rather than workstation identity or a source pathname. Other parts from python-docx's default template remain, including application/template fields, a thumbnail and custom XML; ZIP member timestamps also remain. Those inherited fields do not reliably identify the machine that generated a document. This is not a metadata-free exporter or an anonymity guarantee.

Success returns `0`; handled input/output, argument or dependency rejection returns `2`. Malformed arguments return `DOCUMENT_BUILD_FAILED:ARGUMENTS_INVALID` without echoing supplied values. Help uses the static name `markdown_docx.py`. An unavailable python-docx import returns `DOCUMENT_BUILD_FAILED:DEPENDENCY_UNAVAILABLE` without an import traceback; static help still works. Handled errors use fixed categories without input contents or absolute host paths. Unexpected interpreter/runtime failures are outside this guarantee. Success means a DOCX was written, not that its facts or rendering were accepted.

## Verification and licensing

**27 synthetic unittest methods passed**, with zero failures/errors/skips on the recorded Linux runtime. A separate fictional CLI build and DOCX package inspection also passed; those checks are not counted as extra unittest methods. The seven new methods cover argument/help privacy, missing-dependency CLI behavior and literal markup without external relationships/media. Existing content/property tests now check additional neutral core fields. No real source data, network service, Word/LibreOffice rendering, or financial workflow was accepted by this review.

Run the bundled synthetic tests from this directory with the declared dependency available:

```text
python -B -m unittest discover -s tests -p "test_*.py"
```

The tests create temporary fictional inputs and outputs. They do not read existing business documents or use remote services. Platform facilities such as symlink and FIFO creation can cause explicit skips when unavailable.

The original 27-test file is unchanged and runs on Windows/Ubuntu in CI. New portable/native tests separately cover Windows I/O failure paths and generated DOCX contents, core properties and relationships. Windows CI requires native hardlink/symlink/junction fixtures; unavailable short-name spellings remain explicit skips. Skips are not passes. See the [Batch 22 review](../../docs/BATCH-22-DOCUMENT-BUILDER-WINDOWS.md) and exact-commit Actions logs for actual counts. These are filesystem/package checks; Word/LibreOffice visual rendering remains unverified.

Local Windows/Python 3.12.7: the original suite discovered 27 methods, with 23 passed/four skipped; the new suite discovered 45, with 41 passed/four skipped. A separate runtime-pair copy passed 40 fresh-process scenarios (37 direct CLI, two missing-dependency and one controlled-interruption case) and inspected nine fictional DOCX packages. Runtime/input bytes were preserved; no bytecode appeared. The local skips are explicit unavailable filesystem/platform operations and are not counted as passes.

The owner reports personal work created with AI assistance. The selected parser/layout helpers are retained from the owner-supplied builder; the privacy correction, export adaptation, documentation and synthetic tests were AI-assisted. No required copyright, license or attribution notice was removed from the selected helper source. This bounded review is not independent proof of exclusive authorship.

Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). Retain applicable notices for any dependencies distributed later. No third-party implementation, runtime, font, logo, operational source notes or generated DOCX is bundled in this source snapshot. Generated documents will contain default-template parts supplied by the installed dependency, as described above.
