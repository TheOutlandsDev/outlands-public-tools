# Offline Backup Chain Checker review — 2026-10-25

This batch adds [Offline Backup Chain Checker](../tools/backup-chain-checker/README.md),
a fresh Python 3.12+ standard-library implementation of a neutral dependency
contract. The private audit identified reusable backup/lifecycle methods as a
candidate area. No held original server/backup source, private inventory,
configuration, operational record or actual backup was selected, read, copied
or executed. Earlier source-family holds remain. Only the existing public MIT
control-file reader pattern was adapted, with original-path validation added.

## Declared model and result boundary

One explicitly selected JSON file declares a restore-point ID and 1 to 256
snapshot IDs, series IDs, full/incremental kinds, nullable parent IDs and bounded
integer sequences. Field sets and types are exact. Unknown fields, duplicate
keys/IDs, invalid tokens, unsupported kinds and nonstandard numeric constants
are input errors. No path, address, identity, credential, timestamp, evidence,
content hash, size, application-specific configuration or command field exists.

Full snapshots require null parents. Incrementals require an existing parent in
the same series with an earlier sequence. Sequences are unique within a series;
gaps, branches and multiple full roots with different sequences are supported.
All parent-reference cycle members are flagged without recursive traversal.
The model does not describe differential, deduplicated or multi-parent backups.
It is a new convention, not a vendor-format import or a claim about a real set.

Every snapshot is reviewed, not just the selected ancestry. Output local issues
are sorted by snapshot ID with fixed code ordering. A missing selected ID gives
`RESTORE_POINT_NOT_FOUND`. An issue anywhere on its ancestry gives
`TARGET_CHAIN_BLOCKED` and an empty declared order. Otherwise the order runs
from its full root through the selected incremental. A clean selected chain can
coexist with overall `REVIEW_REQUIRED` for an unrelated broken branch. Local
issue-free rows do not imply issue-free ancestry. No link or state is repaired.

Output retains IDs, counts, issue codes and selected dependency order. It omits
input paths, native errors, sequence values, series labels and raw parent fields.
Real plans/results remain private because IDs and relationships can reveal a
design. A consistent declaration proves no backup existence, integrity,
completeness, ownership, application consistency, compatibility or restorability.
All action and verification flags remain false. No clock, scan, backup-content
access, restore, deletion, command generation or network probe is performed.

This tool does not authorize deletion or extend the separate independent-full
Retention Planner to dependent sets. Actual restore acceptance is a separate
private test with its own evidence.

## Validation

The local Windows/Python 3.12.7 utility suite discovered 43 test methods:
41 passed and two unavailable native link operations were skipped. Skips are
not passes. Coverage includes exact schemas, duplicate IDs/keys, missing parents,
cross-series links, sequence reuse/order, self/multinode cycles, descendant
blocking, unrelated branch isolation, all input permutations and maximum depth.

Two reference checks use different algorithms: all 1,296 four-node parent graphs
are compared with a transitive-closure cycle oracle and an independent selected
route calculation; 300 seeded valid forests use generation-order ancestor
selection. These are generated metadata checks, not execution or storage proof.

A separate fresh-process walkthrough passed 28 scenarios using a copy of the
single script outside the collection. It exercised the four shipped examples,
schema and relationship errors, malformed/duplicate-key/nonstandard JSON,
encoding/BOM/byte boundaries, invalid arguments, missing input and static help/
version. Input/script bytes remained unchanged; no runtime source files were
created. The walkthrough used only fictional control records.

The collection regression discovered 427 methods: 406 passed and 21 were skipped,
with no failures/errors. Ruff checks and formatting passed. Local Markdown/JSON
checks covered 236 documents without findings. Dedicated CI targets Windows/
Ubuntu and Python 3.12/3.13; consult exact-commit Actions results for executed
jobs. Local filesystem skips and synthetic link metadata are separate evidence.

## Reader and publication limits

The control file is bounded at 64 KiB and requires sampled ordinary-file,
single-link, ancestor and descriptor/path identity checks. Link/reparse forms,
reserved/ambiguous paths and original trailing dots/spaces are refused. A Windows
test caught suffix removal during absolute-path normalization; validation now
checks original parts before normalization as well as the resulting path.

Use stable trusted local files. This is not an atomic filesystem snapshot,
hostile-filesystem sandbox, mount-alias guarantee or blocked-I/O deadline. OS
storage access can involve a mounted network filesystem. Fixed CLI errors omit
supplied/native values; a caller formatting library exceptions can still expose
Python source locations. Future inputs/results are not sanitized by this suite.

The exact changed-file export receives a separate private pattern/marker review
and byte inventory. Private marker lists, scanner output, original-source
mappings, test runtime outputs, publication receipts and the private audit
ledger stay outside the public repository. No detector is disabled to publish
a fixture. This batch does not clear unrelated source, Git history, held source
families or release assets. Existing v0.1.0 assets are unchanged by this addition.

The 15-file publication set retained 14 conservative `INTERNAL_HOSTNAME` hits
on Python test-helper method calls. These are code attributes, not
hostnames. Each has a private exact-file-hash disposition; scanner status stays
`REVIEW_REQUIRED`, with zero unresolved findings, private-marker matches or
scanner errors. The scanner and its rules are unchanged.

Selected original code, tests, documentation and fictional examples use MIT with
TheOutlandsDev attribution. No third-party implementation or runtime is bundled.
