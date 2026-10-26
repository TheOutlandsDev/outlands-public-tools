# Provenance and license scope

The owner's local `reconstruct-super.sh` helper called an external sparse-image
conversion tool over a fixed numbered image set. This publication takes the
generic preflight use case and supplies a fresh reusable **metadata inspector**.
It does not copy the original device paths, numbered reconstruction recipe,
firmware, AOSP conversion implementation or external executable.

The original helper remains intact and fingerprinted in the private batch
review. The owner identified these workshop helpers as personal work; that
selected-source review is not independent proof of exclusive historical
authorship. Newly authored parser, tests, docs and fictional example generator
are original MIT work. The bounded reader design and shared file/report helpers
reuse first-party MIT code from this collection's GPT/event inspectors.

The field-layout background was checked against the official
[Android sparse-format header](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/sparse_format.h)
on 2026-10-26. The official
[sparse reader](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/sparse_read.cpp)
was consulted to check CRC/chunk behavior. Those references retain their own
licenses; no upstream source implementation, binary or fixture is copied,
distributed or granted MIT by this project. The implementation intentionally
documents a smaller, metadata-only scope.

MIT covers this original source, tests, guides and generated fictional examples.
Python remains a separately installed runtime under its applicable terms.
Inspected image files retain their own rights. Inspection never grants rights
to redistribute firmware, vendor code or report contents derived from it.

Validation uses generated files only. No live device, real firmware conversion,
partition operation or deployment is part of publication evidence.
