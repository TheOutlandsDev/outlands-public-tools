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

Exact reviewed rejection-test source SHA-256: `5089f9ae371f53e4ac2452c68c2c39714580abee943c2967546fe59e02497090`.

Toolkit 0.2.1 adds the shared public registry, deterministic projections and eight authored family workshops. New examples use only invented inputs and owned external scratch directories. Native/GUI/model/game acceptance remains separate. The publisher preserves existing release assets. Registry source-only labels prevent a newly merged component from being represented as part of an older download.

Canonical Git blobs and executable mode bits remain preserved across platforms; matching platform archives are still required.

The ML workbench merged during this pass. The registry check reported its missing entry before registration. Its already public source and focused evidence are now selected by the 0.2.1 snapshot pin; 0.2.0 remains unchanged. Windows generated catalogs use explicit LF attributes rather than relaxing byte comparisons.
