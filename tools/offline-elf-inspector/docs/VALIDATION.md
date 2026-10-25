# Validation — 2026-10-25

Local Windows / Python 3.12: 50 discovered unittest cases, 48 passed, two skipped.
The skips are native symlink creation (privilege unavailable) and the Linux-only
GCC/readelf oracle. Source checks and a generated mixed/clean CLI walkthrough
are separate checks. Check the collection's linked CI for Windows/Ubuntu Python
3.12/3.13 outcomes; Linux CI requires the independent native compiler oracle.

Coverage includes ELF32/ELF64 and both byte orders; virtual-to-file string-table
mapping; bounded dynamic/string/program headers; malformed offsets, counts,
terminators, text and duplicate tags; no-dynamic metadata; interpreter/search
strings; case-sensitive SONAME/basename candidate lookup; architecture and object
type mismatches; ambiguity; transitive cycles; selected-file scope; partial file,
depth, metadata/hash/time budgets; optional SHA-256; HTML escaping; new-only output;
report member lengths/hashes; original-byte retention; controlled CLI errors and
150 deterministic one-byte metadata mutations.

A local Windows finding showed that path stat and handle fstat can report ctime
with different semantics after rewriting a fixture. The corrected code compares
device/inode/size/mtime across APIs and compares ctime before/after within each
API. It retains observed source-change rejection; no failed check is converted
into a pass. The changed-input test and the complete suite were rerun afterward.

The independent Linux check compiles two tiny original shared objects with GCC,
compares a declared dependency with readelf, and checks the tool's parsed graph.
Those libraries are never imported, loaded or executed. This provides a check
beyond the authored metadata generator; it is not loader/runtime acceptance.

No actual phone, firmware, proprietary game/library, real customer data, native
input execution, flashing, extraction or system reconfiguration was used. Tests
do not certify a complete ELF validator, operating-system loader emulation,
malicious-filesystem sandbox, all processor ABIs, power-loss behavior or every
compiler/linker format. Symlink/permission skips are not passes. Reports are
private metadata and require a separate review before public sharing.

[GitHub checks](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
