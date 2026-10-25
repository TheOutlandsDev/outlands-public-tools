# Report format — version 1

`report.json` declares `schema: outlands-offline-elf-dependencies/1` and a tool
version. Unknown future schemas should be reviewed before processing them.

- `status`: NO_SCOPE_FINDINGS or REVIEW_REQUIRED; this is a limited-scope finding,
  never a runtime/loader/security verdict.
- `interpretation`: concise fixed boundary statement.
- `limits`: requested file/entry/depth/time budgets.
- `summary`: inspected/ignored/parsed/visited counts, dependency status counts,
  detailed plus omitted issue count, metadata bytes and optional hash bytes read.
- `roots`: neutral ordinal labels without original absolute folder names.
- `entry_files`: unique graph starting IDs. With no selected files, all supported
  inspected ELF files are entries.
- `files`: sorted metadata rows. `id` is a relative label, `name` a basename.
  `class` is 32/64; `endian` little/big; `machine` is the numeric e_machine value.
  `machine_name` labels a small known set or unlisted. `osabi`, `abi_version`,
  `flags`, `type`, `bytes`, interpreter, SONAME, ordered declared NEEDED names,
  RPATH/RUNPATH and metadata kind are reported. `sha256` exists only when requested
  and completed. No code sections or binary contents are serialized.
- `dependencies`: sorted edges with consumer ID, declared name, finding,
  `candidate` (ID only for a unique metadata match), candidate count, displayed
  candidate IDs and omitted count. Counts describe the compatibility-filtered
  set when one exists, otherwise the same-name alternatives. At most 16 IDs are
  displayed. See README for resolution and compatibility limits.
- `issues`: relative location label and fixed public code. Native exception
  values, full source roots and binary contents are omitted. Additional issues
  above 500 are counted in `summary.issues_omitted`.

Filename labels and embedded ELF strings are still private metadata. The IDs are
unique within one report, not stable database identities or cross-report file
identities. A selected file can retain its selected-N label when also discovered
under a root. Hard-link aliases are not content-deduplicated and can yield
ambiguous providers. Matching is case-sensitive and does not use root priority.

`MANIFEST.json` declares `outlands-elf-report-files/1` and hashes/sizes the exact
report.json, index.html and README.txt bytes. It does not hash itself or authenticate
the producer. It is distinct from the module's source-only SOURCE-MANIFEST.json.
