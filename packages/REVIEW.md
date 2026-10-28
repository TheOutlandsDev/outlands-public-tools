# Toolkit packaging review

The source input is the previously public, fixed Git revision recorded in
catalog.json. The builder reads that Git object inventory, never local untracked
files or working application instances. It preserves each original source byte
and records packaging/example files separately in the archive manifest.

The packaging regression suite covers all 62 tool folders once, all six systems
in the complete archive, exact source preservation, archive tampering, missing
and undeclared members, output replacement refusal and actual fictional commands
run from fresh complete/release-QA extractions. The workflow repeats those checks
on Windows and Ubuntu and compares their download checksum lists before release.

The public release-audit scanner flagged one rooted-Windows-path literal in the
new tests: `C:/sample`, an intentional rejected input in `test_unsafe_paths_refused`.
It is invented test data, not a user path, host inventory or deployment location.
The finding is retained and dispositioned here; the scanner was not suppressed
or changed. Review findings from later edits independently.

No private source, marker list, original audit ledger, local runtime state or
new employer/user data is selected. Previously public images and fictional
fixtures retain their existing source and provenance records. Pattern scanning
and this review do not establish exclusive authorship or clear future inputs.

Exact reviewed rejection-test source SHA-256: `3b99aab3c1840f19a808dc4db909181184213c4a7bae2b08824b8f13c00bc4ec`.

Git export line-ending conversion was observed in the initial platform comparison.
The builder now reads and checks raw Git blob objects and preserves executable
mode bits. A regression forces Windows checkout conversion and requires identical
source objects; the platform archive comparison remains a publication gate.
