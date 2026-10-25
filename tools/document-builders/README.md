# OUTLANDS | Document Builders

`markdown_docx.py` turns an explicitly selected local Markdown file into a styled DOCX. It preserves headings, simple bullets/numbered lines, and rectangular pipe tables. Parser and layout helpers were adapted from the owner's document-builder project; operational covers, selected-section rules, logos, fixed paths, and source data were excluded.

## Runtime and usage

The staged code targets Python 3.10 or newer and declares `python-docx==1.2.0`. That dependency and its dependencies are not bundled. The requirement pins the direct package version only; it is not a complete transitive or hash-locked environment. Use an environment that already provides the declared dependency; this review did not install packages. Fresh validation used Python 3.12.14, python-docx 1.2.0, lxml 6.1.1 and typing_extensions 4.16.0 on Linux. These observed versions are not dependency vulnerability clearance.

Run from this directory, choosing a new output in an existing directory:

```text
python markdown_docx.py --input examples/fictional_request.md --output example-request.docx --title "OUTLANDS Synthetic Example"
```

The bundled input is fictional. No generated DOCX is included in the repository. Existing outputs are always refused; there is no overwrite flag. The tool does not create parent directories. Review an old output before removing or renaming it yourself.

## Boundaries

Input must be a regular UTF-8 file, at most 256 KiB and 5,000 lines, with at most 4,000 characters per line. Tables must be rectangular, with at most 16 columns and 1,000 body rows per table. Symlink paths and `..` components are rejected. Output is created exclusively with owner-only mode where supported. These filesystem checks are not a sandbox against hostile concurrent directory replacement; use trusted local paths and do not change them during a build.

Windows junctions and other reparse-point types have not been exhaustively controlled or tested. `is_symlink` does not cover every reparse type. Use trusted local directories; Windows reparse-point behavior requires separate validation.

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

The owner reports personal work created with AI assistance. The selected parser/layout helpers are retained from the owner-supplied builder; the privacy correction, export adaptation, documentation and synthetic tests were AI-assisted. No required copyright, license or attribution notice was removed from the selected helper source. This bounded review is not independent proof of exclusive authorship.

Selected original material is MIT licensed; see [LICENSING.md](../../LICENSING.md). Retain applicable notices for any dependencies distributed later. No third-party implementation, runtime, font, logo, operational source notes or generated DOCX is bundled in this source snapshot. Generated documents will contain default-template parts supplied by the installed dependency, as described above.
