# Batch 23: Safe File Mover Windows CLI and engine

This addition adapts only the existing public MIT mover and native file guards.
No original operational source, actual journal, log, recovery copy, private path,
credential, game asset or real input was selected/read/copied/run or published.
All destructive fixtures use generated disposable data outside the checkout.
The GUI source and Python `>=3.12.7,<3.13` declaration remain unchanged.

## Changes and preservation

Windows paths receive lexical checks before normalization, native no-follow
ancestor/name observations and native-volume topology comparisons. This avoids
depending on DOS mount-name resolution and detects observed reparse, unsupported
tag and alias paths. Symlink leaves retain their link/tag/name representation;
directory-link recreation does not probe the target. Ordinary data hard-link
topology is still not preserved, and the known managed same-file recovery case
remains supported. Sensitive journal/lock/reservation storage must be single-link.

Windows journal checks cover raw state paths, database/rollback/lock objects,
named streams, WAL/SHM sidecars and supported database headers before SQLite
opens them. Failed Windows connection setup closes its newly created connection.
The schema, normal recovery model and Linux ownership/mode/privacy checks remain.
SQLite still opens by pathname after sampled guards; the journal is trusted
operational state, not an authenticated untrusted-input format.

ADS enumeration failures/unsupported providers are no longer treated as an empty
stream set. Stream names and sizes are checked; hash/copy loops reject observed
growth before hashing/writing excess data. Source, staging and destination paths
are rechecked around copy/commit callbacks. Windows retains native no-replace
rename without replacement flags. Purge retains the final destination check and
adds observed-tree preflight. No automatic chmod, unsafe rollback or deletion of
refused state is used to force success.

The original 66 methods remain. One hard-link recovery method adds a Windows-only
availability probe that becomes a required feature in CI; its Linux body and all
other original methods are preserved. GUI, CLI command shape, packaging runtime
range and no-replace platform primitives remain. Shared stream validation is
stricter; existing Linux file/state protections are not weakened.

## Local fictional execution

The fresh Windows/Python 3.12.7 original suite discovered 66 methods: 51 passed,
15 skipped, zero failures/errors. Skips were 12 POSIX-specific methods, a POSIX
extended-attribute case and locally unavailable symlink/hardlink operations.
All 11 original named-stream methods ran and passed. A separate new suite has
49 methods: 40 passed, nine explicit local link-availability skips. The new suite
comprises five portable methods and 44 native Windows methods. Skips are not
passes. Windows CI requires hardlink/symlink/junction fixtures and rejects skips
in any original named-stream case; Ubuntu runs the preserved Linux regressions.

New fixtures cover plan without state mutation, verified copy/commit/retention,
recovery/restore/abandon/purge, no overwrite, actual file/directory ADS,
late mutation refusals, Unicode CLI and cross-process locking. Targeted cases
cover malformed device/UNC spelling before API calls, synthetic cross-drive
ancestry, stream growth before excess writes, dangling directory links,
unsafe reservations, enumeration/close errors and SQLite setup cleanup. These
are local generated cases, not live-share, GUI or damaged-storage acceptance.

A separate seven-file package copy passed 43 fresh processes: 40 direct module
CLI cases and three controlled engine-fault processes. It checked plan, move,
Unicode/ADS/tree data, conflict rename, list/history, restore/collisions, verified
purge/refusal, interruption recovery, abandon and state/sidecar/header refusals.
One optional local symlink probe was unavailable and is recorded separately,
not as a successful case. Source/runtime bytes were preserved and no bytecode
appeared. Expected fixture moves/deletions and retained bytes were hash-checked;
input files are intentionally not all immutable in these tests. Every journal,
log and recovery copy stays private.

The collection regression discovered 559 methods: 532 passed, 27 skipped, no
failures/errors. Ruff checks and workflow YAML/context checks passed. Local
documentation/JSON checks and exact-commit CI outcomes are recorded separately.
Independent static review identified the gaps above and reviewed their fixes.
Only Windows/Ubuntu Python 3.12 is targeted, matching the declared runtime range.

## Privacy and remaining scope

Valid CLI output, errors, history, manifests and journals retain paths and other
operational data. They are not anonymized exports. Windows state and staging
permissions inherit from chosen parents; no POSIX 0700/0600 equivalent or full
ACL confidentiality audit is provided. Select a trusted private local state
directory, keep real captures outside GitHub and retain refused state for review.

Windows path and identity guards are sampled. SQLite pathname reopening,
namespace mutations, stream writers and recursive deletion still require stable
trusted parents and quiescent data. File sharing is per stream; primary handles
do not freeze every ADS writer. Matching bytes and flush requests do not prove
directory-entry/hardware/server durability, power-loss recovery or an
application-consistent backup. No GUI, macOS, live SMB/provider, production data
or hostile-filesystem acceptance is claimed. Read the
[Windows contract](../tools/safe-file-mover/docs/WINDOWS.md) for exact bounds.

The earlier licensing note now reflects selected MIT scope under TheOutlandsDev;
required notices remain. Exact selected publication bytes receive a hash
inventory and unchanged-detector/private-marker review. Scanner outputs,
private markers, mappings, receipts and the audit ledger remain outside the
repository. This addition does not clear unrelated imports, Git history, held
source/rights families or existing v0.1.0 assets.

Seven pattern flags remain with exact-line/file-hash-bound private dispositions:
standard Python thread-local/home APIs and Windows unnamed-stream syntax. They
are not concrete hostnames, user paths or configured network addresses. Scanner
status remains `REVIEW_REQUIRED`; there are zero unresolved findings, private
literal matches or errors. No detector or scanner allowlist was weakened.
