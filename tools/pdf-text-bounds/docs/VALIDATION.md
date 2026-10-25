# Validation record - 2026-10-25

Local Windows / Python 3.12.7, with the exact pinned dependencies installed in a
separate private environment: **56 unittest methods discovered, 54 passed and
two skipped**, with warnings treated as errors. The skips require native
symbolic-link permission (unavailable to this Windows account) and POSIX FIFO
semantics. Linux requires applicable native cases; check the collection's
[GitHub Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for Ubuntu Python 3.12/3.13 and Windows Python 3.13/3.14 outcomes.
Skips are not passes.

The suite uses actual pinned pdfplumber/pdfminer parsing of original generated
PDFs, not only mocked geometry. Cases cover inside/outside boxes on every side;
default/zero tolerance; effective CropBox intersection; a declared CropBox larger
than MediaBox; rotated crop evidence; nonzero origins; all four supported page
rotations; invalid rotations/boxes; textless and multiple pages; page/character/
finding limits; nonfinite/invalid options and geometry; encrypted documents with
nonempty and empty user passwords; malformed/truncated/envelope inputs; exact
dependency contracts; actual isolated workers; worker timeout, output/stderr
limits and protocol errors; best-effort audit refusal; exclusive and partial
outputs; independent output-manifest hash readback; source-byte preservation;
safe errors/count-only stdout; static HTML escaping and no active resources;
input/link/nonregular/size guards; source-identity changes; and generated demos.

An explicit lifecycle regression refuses any access to the dependency's eager
`PDF.pages` collection, including on page-limit failure. This caught a potential
cap bypass in ordinary PDF context-manager cleanup: the pinned `PDF.close()`
rebuilds its page collection. The implementation now owns the external byte
stream and closes each constructed Page itself. The encrypted-PDF test also
identified that pdfplumber wraps pdfminer's password error; the public code now
returns the stable encryption-refusal code rather than raw library output.

The actual demo CLI independently reported 16 characters / zero findings for
`inside.pdf` and four characters / four right-side findings for `outside.pdf`.
Poppler rendered both original fixtures for separate visual review. The inside
text is legible within the page; the outside fixture shows the intended clipped
sliver at the right edge. Poppler warned about unavailable Symbol/ArialUnicode
display fonts even though these examples declare Helvetica. No fonts were
installed or actual user documents rendered. This validates only the recorded
fixture view; it is not a general renderer/font or document-layout acceptance.

The separate explicit `check_advisories.py` command checked all nine selected
runtime/test version records on PyPI and found no current listed advisories.
Its endpoint/response-size/pin/advisory-failure behavior is also tested with
fictional responses. A clean PyPI record is not exhaustive vulnerability or
malicious-input safety certification. The PDF inspection path never calls this
network helper.

All fixtures, PDF outputs, PNGs, environments and geometry reports remain in
private audit/temp directories outside the source export. No original portfolio,
customer/employer document, proprietary image, actual password, remote document
or private repository data was used. Process/byte caps do not establish a hard
RAM bound, atomic filesystem snapshot, OS sandbox or complete PDF validator.
