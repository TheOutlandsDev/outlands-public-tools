# OUTLANDS | Markdown Document Builder

Convert an explicitly selected local Markdown file into a new styled DOCX. The
supported subset includes three heading levels, plain paragraphs, simple lists
and rectangular pipe tables. The existing parser, layout, native file backends
and fictional example are preserved in this standalone source qualification.

Use the [usage guide](USAGE.md) for dependency setup and a fictional walkthrough.
Keep `markdown_docx.py` and `docx_windows.py` together. Windows x64 and Ubuntu
x86_64 qualification selects CPython 3.12, 3.13, 3.14 and 3.15.2; actual patch
versions, test results and named skips are recorded in the release's
`VALIDATION.json`. Other versions/platforms have no qualification claim here.

The source ZIP contains authored source, tests, documentation, hash locks and a
source manifest. It contains no interpreter, dependency implementation, wheel,
virtual environment, generated DOCX, real document or raw log. Obtain the
dependencies separately. [DEPENDENCIES.json](dependency-locks/DEPENDENCIES.json) and
[dependency locks](dependency-locks/README.md) bind the complete selected runtime
closure: `python-docx==1.2.0`, `lxml==6.1.3`, `typing_extensions==4.16.0`.
The installer wheel is separately pinned. Hashes identify selected artifacts;
they do not establish vulnerability clearance or authority to use real inputs.

## Run and inspect a fictional document

Install the matched dependency lock as described in [USAGE.md](USAGE.md). Choose
an existing trusted private parent outside the source checkout. Then run:

```text
python -B markdown_docx.py --input examples/fictional_request.md --output /absolute/private/new-fictional-request.docx --title "OUTLANDS Synthetic Example"
```

On Windows, supply an ordinary absolute local drive path for the output. The
placeholder above is a POSIX example. Existing outputs are refused; no overwrite
flag or parent-directory creation is offered. Success returns 0 and the fixed
message `Document created; review its content before sharing.` Handled errors
return 2 with a fixed `DOCUMENT_BUILD_FAILED:` category on stderr. `--help` is
static and works without the document dependency. There is no `--version` flag.

## Input and output boundaries

Input is a regular UTF-8 file, optionally with a BOM, limited to 256 KiB and
5,000 lines of at most 4,000 characters each. XML control characters are refused.
Tables must be rectangular, with no more than 16 columns and 1,000 body rows.
Escaped pipes, nested lists, code blocks, hyperlinks, inline formatting and full
Markdown/HTML syntax are not interpreted as a general converter would.

Inputs and existing outputs are preserved. Windows uses retained native ancestor
handles, single-link ordinary input files, reparse/stream/alias refusal and
exclusive native output creation, short-write retries, flushing and final
identity/size checks. A Windows failure after creation can leave an empty,
partial or complete but unconfirmed new file; retries refuse it. POSIX preserves
the original exclusive-create writer and attempts to unlink only its observed
same-identity newly created file after a write failure. These distinct cleanup
policies remain unchanged. See [the native contract](docs/WINDOWS.md).

Use stable, canonical, trusted local paths. The builder does not enforce a
repository-output exclusion: the usage guide keeps outputs private by explicit
selection. Sampled filesystem checks do not establish atomic snapshots,
hostile-filesystem isolation, universal alias protection or Windows ACL privacy.
Windows output permissions inherit from the selected parent. Network/virtual
storage, mount rebinding and every concurrent filesystem operation are outside
the qualification boundary.

## Document contents and validation

Markdown and the supplied title become document text. The tool does not anonymize
content. Configured core properties use neutral OUTLANDS fields and fixed
nonidentifying dates. The dependency's default-template application fields,
thumbnail, custom XML, styles and other package parts remain. ZIP member times
also remain; generated DOCX bytes can differ between equivalent builds. This is
not a metadata-free exporter. No remote images, templates or URLs are fetched;
literal Markdown links/images/scripts remain text.

Qualification preserves all 72 existing methods: 27 original regressions and
45 portable/native package and file-safety methods. Thirty additional tests run
the runtime pair copied outside the collection, inspect generated ZIP/XML and
core properties, and exercise CLI and file safeguards. The eight fresh lanes
select 102 methods each, 816 in total; platform and capability skips are reported
separately from passes. [Qualification](docs/QUALIFICATION.md) describes the
dependency, archive, native and privacy gates. `VALIDATION.json` provides actual
results rather than a promised pass count.

DOCX ZIP/XML inspection verifies fictional package contracts. Word/LibreOffice
visual rendering, business correctness, real documents and sharing rights require
their own acceptance. Wide tables and long content may need layout adjustment.

Selected original material is [MIT licensed](LICENSE). The owner reports personal
work created with AI assistance; the original builder adaptation retained its
parser/layout helpers while excluding operational covers, logos, fixed paths
and source records. This review is not independent proof of exclusive authorship.
See [provenance](docs/PROVENANCE.md) and
[third-party notices](THIRD-PARTY-NOTICES.md).
