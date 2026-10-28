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
