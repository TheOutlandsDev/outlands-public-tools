# Supported input, geometry and report format

## Trusted PDF subset

The CLI accepts an explicit canonical local `.pdf` file path. Inputs must be
ordinary stable files under trusted parents, UTF-independent binary PDF data,
1 byte through 8 MiB. Existing link/reparse ancestors, UNC/device/stream paths,
relative paths and traversal components are refused. File handles use no-follow
and nonblocking flags where available, then confirm regular-file identity,
size/mtime and descriptor change time. These are observations, not an atomic
snapshot or hostile-filesystem guarantee. The hash covers the same byte snapshot
sent to the worker. Original bytes are not rewritten.

The supported envelope begins `%PDF-` and ends `%%EOF` plus optional whitespace.
This excludes prepended/trailing data and incomplete exports that a tolerant
reader might recover. Envelope checks are not a complete PDF validity check.
The pinned pdfplumber/pdfminer parser decides whether it can process the object
structure. Any parser error fails the complete operation. Passwords are never
accepted; every encrypted PDF is unsupported, including an empty user password.

## Coordinates

The pinned pdfplumber page implementation normalizes MediaBox, declared CropBox
and character geometry into rotated `(x0, top, x1, bottom)` point coordinates.
`media` compares against `page.mediabox`; `crop` compares against the intersection
of `page.cropbox` and `page.mediabox`. The original page is never cropped first,
because cropping can truncate or remove character boxes and conceal findings.
Nonzero origins are retained. An offset example has MediaBox `[10, -20, 210, 80]`
in this normalized space; substituting `(0, 0, width, height)` would be wrong.

Only page rotations 0, 90, 180 and 270 are supported. Unsupported/nonfinite,
reversed, empty page/crop geometry or coordinates exceeding absolute 1e9 points
cause an incomplete result. Character boxes may have zero width or height but
must be ordered and finite. A nonintersecting CropBox is rejected.

A character is outside when at least one condition is true:

```text
x0 < boundary.x0 - tolerance
top < boundary.top - tolerance
x1 > boundary.x1 + tolerance
bottom > boundary.bottom + tolerance
```

Tolerance is a finite number from 0 through 72 points; default 1. Equality is
inside. Bounds describe parser-observed boxes, not actual ink pixels or clipping
paths. Invisible, duplicate or occluded text is still counted if the parser
emits characters. Character order/index is the library's object order, not a
reading-order or Unicode code-point guarantee. Glyphs outside the boundary may
be intentional; glyphs inside can still look wrong. Shapes, images, annotations,
fonts, clipping paths, text semantics and raster quality are not inspected.

## Caps and child process

| Limit | Value |
| --- | --- |
| PDF snapshot | 8 MiB |
| Pages | Default 100, user ceiling 500 |
| Observed characters across pages | Default 100,000, user ceiling 500,000 |
| Findings retained | 5,000; exceeding it fails instead of truncating success |
| Child time | Default 20 seconds; accepted 0.1 through 120 |
| Worker stdout | 4 MiB |
| Worker stderr | 64 KiB; any stderr invalidates the result |
| Each final JSON/HTML payload | 8 MiB |
| Geometry magnitude | At most 1e9 points |

Page enumeration is incremental through `PDFPage.create_pages`. Each explicit
pdfplumber Page is closed after inspection. The code owns the external BytesIO
stream instead of calling the pinned `PDF.close()`, whose implementation eagerly
rebuilds `.pages`. Tests ensure that eager page collection is never accessed.
Exact dependency pins make this lifecycle assumption visible and testable.

`page.chars` can allocate one page's full layout before its count is checked.
PDF object traversal/decompression/font work can likewise allocate before the
tool sees a result. There is no hard memory, decompressed-stream or native CPU
sandbox. Use trusted inputs only. The parent uses bounded pipe readers and a
timeout; on failure it kills its owned worker. Python's audit hook is defense in
depth for ordinary Python network/process/write operations, not an OS security
boundary. The child is not designed to launch other processes.

The timeout excludes parent file reads/report writes and normal process cleanup.
Underlying filesystem/native operations can block despite byte bounds. Failures
and exceeded caps never produce a successful partial inspection.

## Reports and exits

`report.json` has `schema_version: 1`, `tool: "pdf-text-bounds"`, the input SHA256
and byte count, selected box/tolerance, exact runtime versions, page/character
counts, coverage issues, per-page boxes/rotation/counts, and findings containing
only 1-based page and character indices, the observed box and outside sides.
It contains no extracted text, font identifiers, metadata values or source path.
Hashes and geometry still identify some documents, so reports remain private
until reviewed. `report.html` is a static escaped view with no active resources.

- `NO_GEOMETRY_FINDINGS`, exit 0: supported character geometry completed without
  outside boxes or text-absence coverage issues. No rendering/safety verdict.
- `BOUNDS_FINDINGS`, exit 1: one or more observed characters were outside.
- `REVIEW_REQUIRED`, exit 1: no outside boxes, but at least one page had no text
  observed. This may be an image, shape-only or deliberately empty page.
- `INCOMPLETE`, exit 2: fixed error code, no completed result. Raw library errors
  and input names are never printed by the CLI.

Outputs require an existing trusted parent and a new directory, with exclusive
file creation. `MANIFEST.json` records byte lengths/SHA256 for JSON and HTML;
it does not establish authenticity. A write error may leave a newly created
partial directory. Never treat leftover files or a manifest alone as exit 0/1.

`inspect_snapshot()` is an internal trusted-byte core without process isolation;
the public `inspect()`/CLI provide the child-process boundary. The hidden worker
entry and `run_worker(command=...)` test injection are implementation/testing
mechanisms, not supported alternate user commands or security APIs.
