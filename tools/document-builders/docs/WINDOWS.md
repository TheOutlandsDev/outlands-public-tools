# Windows Markdown input, DOCX output and metadata contract

Keep `markdown_docx.py` and `docx_windows.py` together. The Windows backend adapts
only this public MIT toolkit's native file mechanisms. It calls OS-provided APIs
through the standard library; no DLL, implementation or runtime is bundled.
The separate `python-docx==1.2.0` dependency remains required for document
generation; static help and fixed missing-dependency errors remain available.

## Inputs and preservation

Raw Windows CLI path spelling is validated before normalization. Ordinary
relative and drive-absolute paths are limited to 4,096 characters, 64 components
and 255 characters/component. UNC/device/extended user paths, parent traversal,
drive-relative forms, alternate streams, reserved device names, control
characters and trailing dots/spaces are refused. No environment expansion occurs.

Existing ancestors remain open through selected-file checking/closure. Input
opens request read sharing only, reparse-point opening and directory support.
Native queries require ordinary disk files, single links, nonreparse attributes,
usable file identities and supported normalized local HarddiskVolume names.
Each child name must match its retained parent's native name plus the requested
component; observed ancestry changes and alternate short-name spellings fail.

A noninheritable binary CRT descriptor owns a transferred input handle. Reads
are bounded at the existing 256 KiB limit, with size/timestamp and native
identity/name observations checked around reading. Empty Markdown remains
supported. The original UTF-8/BOM, line/character, control-character and table
rules remain; Windows uses the same decode checks as the original read tail.
Some filesystem categories differ by backend, such as `INPUT_SIZE_LIMIT` on
Windows versus the original `INPUT_TOO_LARGE` on Linux. Both return handled
rejection; callers should not assume identical native error categories.

Original Linux path/read/write bodies remain after Windows-only dispatch.
Pure Markdown parsing, table validation, style/layout helpers, document creation
and neutral core-property definitions are unchanged. The original 27-test file
is preserved; CI executes it on both Windows and Ubuntu. This preserves program
behavior, not a claim that different Office versions render identically.

## Exclusive new DOCX output

The complete document is rendered in memory before file creation. The Windows
writer requires an explicit `.docx` filename, bytes and an existing parent; none
is created. Its low-level byte writer preserves empty bytes and introduces no
new DOCX size limit. The CLI still supplies a generated DOCX rather than
arbitrary caller bytes.

The CLI retains its early existence rejection, but native
[`CreateFileW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
with `CREATE_NEW` makes the final no-replacement decision. There is no fallback
to overwriting an existing file/directory/link. The newly created ordinary
single-link disk file must match its retained parent's normalized native name
before any body write. No sharing is requested during writing.

Synchronous writes use at most 64 KiB per call, retry short writes and reject
zero/failed writes. The file is flushed, then stable identity/name and exact
final size are checked before close. Ancestor handles remain through closure.
Conflicting ordinary data writers/deleters and observed changes cause refusal.
Sharing restrictions do not freeze all metadata, mapped-view or filesystem
operations; file flushing does not establish directory-entry or power-loss
durability.

Permissions inherit from the chosen parent's Windows ACL. There is no POSIX
0600 equivalent, ACL confidentiality check, encryption or administrator-access
restriction. Select a trusted private parent outside the public checkout.
On any failure after creation, retain and inspect the new file: it may be empty,
partial or fully written but unconfirmed. It is not a successful document.
Windows recovery never unlinks a pathname; retry with a different new filename.
OS close failures can leave handles open until process exit.

## DOCX contents and privacy

[`Document()`](https://python-docx.readthedocs.io/en/latest/api/document.html)
starts from python-docx's built-in default template. The builder's core title,
subject, author/last-modified-by, empty identifying fields, revision and fixed
created/modified values remain as documented. No supplied source/output path
is added to those properties. Copied Markdown and the caller's title remain
document contents; they are not anonymized.

Default-template application fields, a thumbnail, custom XML, relationships,
styles and other package parts remain. ZIP member timestamps also remain.
Generated documents are not metadata-free or anonymous, and package inspection
does not grant sharing rights. Real input text, names, figures, links and
identifiers need their own private review. No operational document, logo,
personal profile or generated DOCX is included in this publication.

Fictional package checks inspect all relationship parts for external targets,
uncompressed XML/content and configured core fields, and record inherited
template parts. Literal Markdown links/images/scripts stay text and are not
fetched, executed or embedded as remote media. There is no new OOXML scrubber
or guarantee about every future dependency/template version. Compare content
parts for fixture checks; ZIP timestamps mean whole-DOCX bytes need not match.

## Results and validation boundary

Success remains the existing fixed message and code 0; handled errors use
`DOCUMENT_BUILD_FAILED:` plus a fixed category on stderr and code 2. Static help,
missing-dependency handling and argument privacy remain; interruption now has a
fixed category. The Windows script entry point emits fixed errors with LF line
endings so fresh-process error bytes match the documented CLI form. Native
paths/IDs and OS errors are suppressed. Library tracebacks
or unexpected runtime failures can retain source locations.

Use stable trusted local files and parents. Network/virtual storage, drive/mount
rebinding, hostile concurrent mutation, mapped views, ACL privacy and exhaustive
filesystem behavior are not certified. The program is not an atomic snapshot,
hostile-filesystem sandbox, document-authenticity check or public-release gate.
Office/LibreOffice visual rendering and future real documents remain unverified.

The [Batch 22 review](../../../docs/BATCH-22-DOCUMENT-BUILDER-WINDOWS.md) and
exact-commit Actions logs record separate original/new fixture results and the
standalone fictional CLI/DOCX inspection. Native link creation is required in
Windows CI; local unavailability and absent alternate short spellings are
explicit skips. The direct dependency pin is not a complete transitive lock or
advisory audit. No dependency implementation/runtime is bundled or relicensed.
