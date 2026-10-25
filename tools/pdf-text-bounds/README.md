# PDF Text Bounds Inspector

Inspect character boxes in a **trusted, completed local PDF** and report which
extend beyond the selected page boundary. This helps review machine-generated
reports before sharing them. Original CLI, reports, documentation and fictional
fixtures are [MIT licensed](LICENSE); separately installed dependencies retain
their licenses and notices.

The result concerns observed text geometry. It does **not** establish visual
quality, all clipping, image or shape placement, correct fonts, print output,
document integrity or malware safety. No OCR, rendering or document modification
is performed. Read [the exact format and limits](docs/FORMAT.md).

## Install in a separate private environment

Use Python **3.12, 3.13 or 3.14** with the exact pinned dependencies below.
Clone/download this repository and open a terminal in
`tools/pdf-text-bounds`. Keep inputs, environments and reports outside the
checkout, following the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md).
Set `$privateWork` or `PRIVATE_WORK` to an existing absolute directory you control.

PowerShell:

```powershell
python -m venv "$privateWork/pdf-bounds-venv"
$pdfPython = "$privateWork/pdf-bounds-venv/Scripts/python.exe"
& $pdfPython -m pip install --only-binary=:all: -r requirements.txt
& $pdfPython -B pdf_bounds.py --help
```

POSIX shell:

```sh
python3 -m venv "$PRIVATE_WORK/pdf-bounds-venv"
PDF_PYTHON="$PRIVATE_WORK/pdf-bounds-venv/bin/python"
"$PDF_PYTHON" -m pip install --only-binary=:all: -r requirements.txt
"$PDF_PYTHON" -B pdf_bounds.py --help
```

Installation explicitly downloads the pinned packages from the configured pip
index. **PDF inspection itself makes no network requests.** There are no bundled
PDF libraries, binaries, fonts or original portfolio documents. The inspector
requires the eight exact tested runtime versions in `requirements.txt`; a
missing/different version fails visibly. See [dependency records](docs/DEPENDENCIES.json)
and [third-party notices](THIRD-PARTY-NOTICES.txt).

## Try authored PDFs

Every demo destination and report directory must be new. The generator uses
original minimal PDF source and a standard Helvetica font declaration, with no
real document content or document-library dependency.

```powershell
& $pdfPython -B examples/make_demo.py --destination "$privateWork/pdf-demo"
& $pdfPython -B pdf_bounds.py --pdf "$privateWork/pdf-demo/inside.pdf" --output "$privateWork/pdf-inside-report"
& $pdfPython -B pdf_bounds.py --pdf "$privateWork/pdf-demo/outside.pdf" --output "$privateWork/pdf-outside-report"
```

The first inspection returns **0**, with 16 observed characters and no geometry
findings. The second intentionally returns **1**, with four characters beyond
the right boundary. That is an expected negative fixture. In a POSIX shell,
replace `& $pdfPython` with `"$PDF_PYTHON"`.

Each completed inspection writes `report.json`, a static `report.html`, and
`MANIFEST.json` containing the two report hashes/lengths. Open the HTML locally;
it has no scripts, external assets, document links or extracted character text.
Existing paths are never replaced. A write failure can leave a new partial
directory; exit 2 means the result is incomplete even if some files exist.

## Select a boundary and tolerance

```powershell
& $pdfPython -B pdf_bounds.py --pdf "$privateWork/pdf-demo/crop.pdf" --box crop --tolerance 0 --output "$privateWork/pdf-crop-report"
```

`--box media` is the default. `--box crop` uses the intersection of the declared
CropBox and MediaBox. Character boxes are compared in the pinned pdfplumber
rotated `(x0, top, x1, bottom)` coordinate space. Actual nonzero box origins are
retained; the tool does not assume every page starts at `(0, 0)`. The default
tolerance is **1 point** per side; equality at the allowed boundary passes.
Supported page rotations are 0, 90, 180 and 270 degrees. See [FORMAT.md](docs/FORMAT.md)
for coordinate details and exclusions.

| Exit | Meaning |
| --- | --- |
| 0 | Supported character geometry completed with no findings or coverage issues. |
| 1 | Bounds findings or pages with no text observed; review the completed report. |
| 2 | Input, dependency, parser, limit, timeout or output failure; no complete result. |

No observed text on a page does not prove a blank page: scanned images and paths
can remain. Invisible or occluded text may still produce character boxes. This
tool neither removes findings nor repairs a PDF. Reports omit text, source paths,
document metadata and font identifiers but retain the PDF hash, geometry and page
counts, which can still identify a private document. Review reports before sharing.

## Trust and processing boundaries

Use only ordinary, stopped local document files under trusted directories. Do
not supply arbitrary downloaded PDFs, hostile filesystem paths, devices, FIFOs,
live files or remote mounts. Existing symbolic links/reparse points and UNC paths
are refused, but these checks are not an adversarial-filesystem sandbox.

The CLI reads one bounded snapshot, then invokes a child copy of this source
with Python isolated mode. The child uses bytes in memory, never the input path.
The parent limits child time and output; the child does not render or start tools.
A best-effort Python audit hook refuses network/process/write operations. This
is **not an OS sandbox** and cannot make vulnerable parser/native code safe.

Limits include 8 MiB input, at most 500 pages, 500,000 observed characters and
5,000 findings. Defaults are 100 pages, 100,000 characters and a 20-second child
timeout. Parsing a single page may allocate character/layout objects before its
count is known; there is **no hard process RAM limit**. Timeout/byte limits do not
bound native filesystem operations or guarantee recovery from every parser bug.
The supported envelope begins with `%PDF-` and ends with `%%EOF` plus optional
whitespace. Encrypted PDFs, including empty-user-password encryption, are refused.

## Test, inspect and suggest improvements

Install test dependencies into the same separate environment:

```powershell
& $pdfPython -m pip install --only-binary=:all: -r requirements-dev.txt
& $pdfPython -B -W error -m unittest discover -s tests -v
```

Tests use original generated PDFs and actual pinned library parsing, plus
controlled process/IO fixtures. Read [validation evidence](docs/VALIDATION.md),
[source provenance](docs/PROVENANCE.md) and the [contribution guide](CONTRIBUTING.md).

Maintainers/CI may **explicitly** run `python -B check_advisories.py` after
installing `requirements-dev.txt`. That separate command queries fixed PyPI
version endpoints and fails on reported advisories or unavailable records. It
is never invoked by the inspector and is not exhaustive security clearance.

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=pdf_bounds_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=pdf_bounds_suggestion.yml).
Share a tiny generated reproduction, OS/runtime versions, selected options and
expected geometry. Do not upload confidential PDFs, real extracted text,
unredacted geometry reports, credentials or artwork you cannot distribute.
