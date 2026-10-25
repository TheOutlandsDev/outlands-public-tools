# Offline Dependency Lock Diff review — 2026-10-25

This batch adds [Offline Dependency Lock Diff](../tools/dependency-lock-diff/README.md),
a standalone Python 3.12+ standard-library comparison of two explicitly selected
locks in the collection's published narrow format. No sibling module or package
installation is needed. The dependency/release-review area supplied the candidate
boundary. No held original environment, dependency configuration, real lock,
private package name, credential, index endpoint, package artifact or operational
record was selected, read, copied or executed. Existing source-family holds remain.
Strict parser and sampled file guards adapt existing public MIT mechanisms.

## Grammar and comparison boundary

Both inputs must pass the existing narrow lock grammar before comparison. A
record has a canonical normalized package name, fixed-version subset string and
exactly one adjacent SHA-256 line. Records are unique and name-sorted. Comments
and empty lines between records are allowed; noncanonical names, unsupported
active lines/URLs/directives, extras, markers, wildcards, duplicate/unsorted names,
orphan/multiple hashes, invalid encoding and control characters fail.

The parser retains names, version text and normalized hash text. It does not
silently normalize unsupported package declarations or guess missing values.
Version text is not semantically ranked: even `1.0` and `1.0.0` differ here.
No greater/less, upgrade/downgrade, compatibility or release chronology claim is
made. The older converter/validator's POSIX-only file I/O is unchanged; the new
diff uses separately tested Windows/Ubuntu sampled input handling.

Exact package names match records. Classifications are only in before, only in
after, version text changed, hash only changed, or unchanged. Version-text changes
take precedence over hash-only classification, with separate row flags showing
whether the hash also changed. One-sided comparison flags are null. Rows are
deterministically name-sorted; counts do not double-count version/hash changes.
Comments, BOM, line endings and hash-letter case can change raw input digests
while leaving compared records unchanged.

Output retains package names, version/hash records, input digests and change
relationships. It omits comments, selected paths and native exceptions. Actual
inputs/results remain private because even these retained fields identify a
project. Internal hash agreement is not artifact authenticity, source-index
availability, dependency resolution, installability, reproducibility, platform
coverage, licensing or vulnerability status. A hash-only change is descriptive,
not a finding of malware or an instruction to replace anything.

No package manager, download/install, artifact access, environment collector,
advisory service, network probe or lock mutation is implemented. All such action/
verification flags remain false. Exit 0 means matching supported records, exit 1
record differences, exit 2 fixed-code error and exit 130 interruption. Neither
matching nor changed declarations describe installed packages or authorize action.

## Fictional validation

The local Windows/Python 3.12.7 suite discovered 41 methods: 39 passed and two
unavailable native-link operations were skipped. Skips are not passes. Tests
cover strict schemas/grammar, canonical names, fixed-version subset preservation,
hash adjacency, unsupported general requirements, duplicate/order rejection,
byte/line/package boundaries, comparison precedence, nullable one-sided flags,
reverse behavior, fixed errors and no file/process/network/clock side effects.

One hundred seeded valid locks and 20 malformed variants were compared against
the existing public validator's pure parser, without invoking its POSIX file I/O.
Three hundred seeded comparisons used separate list-search reference logic.
Maximum cases cover a valid 1 MiB lock, 2,000 packages per input and 4,000 union
rows. Tests do not consult any registry, real environment or package artifact.

A separate standalone CLI walkthrough passed 35 fresh-process fictional
scenarios. It covered shipped locks, matching/comment/BOM/newline/hash-case
equivalence, name/version/hash changes, invalid syntax/ordering/encoding/bounds,
unsupported active requirements and static help/version. Script/input bytes were
preserved; no bytecode appeared. The collection regression discovered 559
methods: 532 passed and 27 skipped, no failures/errors. Ruff checks/formatting and
306 local Markdown/JSON checks passed. Dedicated CI targets Windows/Ubuntu with
Python 3.12/3.13; consult exact-commit Actions results for executed native jobs.

The full-checkout tests use existing public parser code as a reference. The
standalone claim concerns runtime only and is tested with a copy of the single
script outside the collection. Native filesystem skips and synthetic metadata
checks are separate evidence; declarations never prove real package behavior.

## Bounds, publication and remaining limits

Each lock is bounded at 1 MiB, 6,000 lines, 512 characters/line and 2,000 packages;
two inputs give at most 2 MiB of lock bytes. Serialized stdout JSON is capped
at 4 MiB before printing, plus its final newline. Output-bound errors produce
fixed JSON instead of a partial comparison; OS stdout failure/interruption can
still leave partial captured output, which is not a completed report.

The sampled reader checks ordinary single-link files, ancestors and descriptor/
path identities before/during/after reads and rechecks both snapshots. Link/
reparse, reserved/ambiguous and original trailing-suffix paths are refused. Use
stable trusted local inputs: this is not an atomic two-file transaction, hostile
filesystem sandbox, mount-alias guarantee or blocked-I/O deadline. OS storage can
be network-backed without an explicit probe here. Formatted library tracebacks
can retain Python source locations even though CLI errors suppress input/native
values. Future locks/results need their own privacy and sharing-rights review.

The exact selected publication set receives a separate private pattern/marker
review and byte inventory. Private markers, runtime locks, scanner output,
source mappings, publication receipts and the audit ledger stay outside the
repository. Local attributes preserve exact fictional fixture bytes through
checkout. This addition does not clear unrelated imports, Git history, held
source/rights families or existing v0.1.0 release assets. Selected original
code/docs/tests and invented locks use MIT under TheOutlandsDev; no third-party
implementation/runtime or actual package artifact is bundled.

The 17-file publication inventory includes 13 scanner-recognized text files and
four plain UTF-8 lock fixtures requiring manual extension review. All four passed
the strict lock parser and the same text/private-marker detectors on their exact
bytes; names and marker-derived hashes were checked as fictional. Four format
review flags remain with private file-hash-bound dispositions. Scanner status is
`REVIEW_REQUIRED`, with zero unresolved findings, text/private-marker matches or
errors. No scanner allowlist or detector was weakened or disabled.
